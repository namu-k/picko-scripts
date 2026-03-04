"""
Quality State Machine using LangGraph

Multi-step quality verification with confidence scoring.
"""

from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph

from picko.logger import get_logger

logger = get_logger("quality.graph")


class QualityState(TypedDict):
    """State for quality verification graph"""

    # Input
    item_id: str
    content: str
    title: str

    # Primary validation
    primary_verdict: str  # "approved", "rejected", "needs_review"
    primary_confidence: float  # 0.0 - 1.0
    primary_scores: dict[str, int]  # {factual, source_credibility, bias, value}
    primary_reasoning: str
    primary_flags: list[str]

    # Cross-check (optional)
    cross_check_verdict: str | None
    cross_check_confidence: float | None
    cross_check_agreement: bool | None

    # External check (optional)
    external_check: dict[str, Any] | None

    # Final result
    final_verdict: str
    final_confidence: float

    # Enhanced verification mode
    enhanced_verification: bool  # True for new sources

    # Feedback
    feedback_notes: list[str]


def primary_validation_node(state: QualityState) -> dict[str, Any]:
    """
    1차 LLM 검증 노드

    Returns partial state update for primary validation fields.
    """
    from picko.quality.validators import PrimaryValidator

    validator = PrimaryValidator()
    result = validator.validate(
        title=state["title"],
        content=state["content"],
    )

    logger.info(f"Primary validation: {state['item_id']} -> " f"{result['verdict']} ({result['confidence']:.2f})")

    return {
        "primary_verdict": result["verdict"],
        "primary_confidence": result["confidence"],
        "primary_scores": result.get("scores", {}),
        "primary_reasoning": result.get("reasoning", ""),
        "primary_flags": result.get("flags", []),
    }


def cross_check_node(state: QualityState) -> dict[str, Any]:
    """
    2차 교차 검증 노드

    Uses different LLM model for independent verification.
    """
    from picko.quality.validators import CrossCheckValidator

    validator = CrossCheckValidator()
    result = validator.validate(
        title=state["title"],
        content=state["content"],
        primary_verdict=state["primary_verdict"],
        primary_confidence=state["primary_confidence"],
    )

    agreement = result["verdict"] == state["primary_verdict"]

    logger.info(
        f"Cross-check: {state['item_id']} -> "
        f"{result['verdict']} ({result['confidence']:.2f}), "
        f"agreement={agreement}"
    )

    return {
        "cross_check_verdict": result["verdict"],
        "cross_check_confidence": result["confidence"],
        "cross_check_agreement": agreement,
    }


def confidence_calc_node(state: QualityState) -> dict[str, Any]:
    """
    최종 신뢰도 계산 노드

    Combines primary, cross-check, and optional external scores.
    """
    from picko.quality.confidence import calculate_final_confidence, determine_verdict

    final_confidence = calculate_final_confidence(
        primary={
            "verdict": state["primary_verdict"],
            "confidence": state["primary_confidence"],
        },
        cross_check=(
            {
                "verdict": state["cross_check_verdict"],
                "confidence": state["cross_check_confidence"],
                "agreement": state["cross_check_agreement"],
            }
            if state.get("cross_check_verdict")
            else None
        ),
        external=state.get("external_check"),
        enhanced_mode=state.get("enhanced_verification", False),
    )

    final_verdict = determine_verdict(
        final_confidence,
        enhanced_mode=state.get("enhanced_verification", False),
    )

    logger.info(f"Final confidence: {state['item_id']} -> " f"{final_verdict} ({final_confidence:.2f})")

    return {
        "final_confidence": final_confidence,
        "final_verdict": final_verdict,
    }


def route_by_confidence(state: QualityState) -> str:
    """
    1차 검증 후 라우팅

    Returns:
        - "approved": confidence >= 0.9 (enhanced) or >= 0.9 (normal)
        - "cross_check": 0.7 <= confidence < 0.9
        - "rejected": confidence < 0.7
    """
    confidence = state["primary_confidence"]
    enhanced = state.get("enhanced_verification", False)

    # Enhanced mode: always do cross_check
    if enhanced:
        if confidence >= 0.92:
            return "approved"
        elif confidence < 0.3:
            return "rejected"
        return "cross_check"

    # Normal mode
    if confidence >= 0.9:
        return "approved"
    elif confidence >= 0.7:
        return "cross_check"
    else:
        return "rejected"


def route_by_cross_result(state: QualityState) -> str:
    """
    2차 검증 후 라우팅

    Returns:
        - "confidence_calc": always proceed to final calculation
    """
    return "confidence_calc"


def build_quality_graph():
    """
    Build the quality verification state machine

    Flow:
    START -> primary_validation -> [approved | cross_check | rejected]
    cross_check -> confidence_calc -> END
    approved -> END
    rejected -> END
    """
    builder = StateGraph(QualityState)

    # Add nodes
    builder.add_node("primary_validation", primary_validation_node)
    builder.add_node("cross_check", cross_check_node)
    builder.add_node("confidence_calc", confidence_calc_node)

    # Add edges
    builder.set_entry_point("primary_validation")

    # Conditional routing after primary
    builder.add_conditional_edges(
        "primary_validation",
        route_by_confidence,
        {
            "approved": END,
            "cross_check": "cross_check",
            "rejected": END,
        },
    )

    # Cross-check always goes to confidence calc
    builder.add_edge("cross_check", "confidence_calc")
    builder.add_edge("confidence_calc", END)

    return builder


class QualityGraph:
    """
    Quality verification graph wrapper

    Provides compiled graph and checkpointing support.
    """

    def __init__(self, checkpoint_path: str | None = None):
        """
        Initialize QualityGraph

        Args:
            checkpoint_path: Path to SQLite checkpoint DB (optional)
        """
        self.checkpoint_path = checkpoint_path
        self.graph = build_quality_graph()

        # Compile with optional checkpointing (requires langgraph-checkpoint-sqlite)
        if checkpoint_path:
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver

                self.checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
                self.compiled = self.graph.compile(checkpointer=cast(Any, self.checkpointer))
                logger.info(f"Quality graph compiled with checkpointing: {checkpoint_path}")
            except (ImportError, AttributeError):
                logger.warning(
                    "SqliteSaver not available, running without checkpointing "
                    "(install optional deps: pip install .[agentic])"
                )
                self.compiled = self.graph.compile()
        else:
            self.compiled = self.graph.compile()
            logger.info("Quality graph compiled without checkpointing")

    def verify(
        self,
        item_id: str,
        title: str,
        content: str,
        enhanced_verification: bool = False,
        thread_id: str | None = None,
    ) -> QualityState:
        """
        Run quality verification

        Args:
            item_id: Item identifier
            title: Content title
            content: Full content text
            enhanced_verification: Enable enhanced mode for new sources
            thread_id: Thread ID for checkpointing (optional)

        Returns:
            Final QualityState with verdict and confidence
        """
        initial_state: QualityState = {
            "item_id": item_id,
            "title": title,
            "content": content,
            "primary_verdict": "",
            "primary_confidence": 0.0,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": enhanced_verification,
            "feedback_notes": [],
        }

        invoke_config: Any = None
        if thread_id and self.checkpoint_path:
            invoke_config = {"configurable": {"thread_id": thread_id}}

        result = self.compiled.invoke(initial_state, invoke_config)

        return cast(QualityState, result)
