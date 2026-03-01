"""
Tests for Quality Graph - LangGraph state machine.

Tests state transitions, routing logic, and graph compilation.
"""

import sys
from unittest.mock import MagicMock, patch

from picko.quality.graph import (
    QualityGraph,
    QualityState,
    build_quality_graph,
    confidence_calc_node,
    cross_check_node,
    primary_validation_node,
    route_by_confidence,
    route_by_cross_result,
)


class TestQualityState:
    """Tests for QualityState TypedDict."""

    def test_quality_state_has_required_fields(self):
        """QualityState should have all required fields."""
        state: QualityState = {
            "item_id": "test-001",
            "content": "Test content",
            "title": "Test Title",
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
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        assert state["item_id"] == "test-001"
        assert state["title"] == "Test Title"
        assert state["enhanced_verification"] is False


class TestRouteByConfidence:
    """Tests for routing after primary validation."""

    def test_high_confidence_approved(self):
        """High confidence (>= 0.9) should route to approved."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "approved",
            "primary_confidence": 0.92,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        assert route_by_confidence(state) == "approved"

    def test_medium_confidence_cross_check(self):
        """Medium confidence (0.7-0.9) should route to cross_check."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "needs_review",
            "primary_confidence": 0.75,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        assert route_by_confidence(state) == "cross_check"

    def test_low_confidence_rejected(self):
        """Low confidence (< 0.7) should route to rejected."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "rejected",
            "primary_confidence": 0.65,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        assert route_by_confidence(state) == "rejected"

    def test_enhanced_mode_higher_threshold(self):
        """Enhanced mode should require >= 0.92 for approved."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "approved",
            "primary_confidence": 0.90,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": True,  # Enhanced mode
            "feedback_notes": [],
        }

        # 0.90 should go to cross_check in enhanced mode
        assert route_by_confidence(state) == "cross_check"

    def test_enhanced_mode_approved_at_92(self):
        """Enhanced mode should approve at >= 0.92."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "approved",
            "primary_confidence": 0.92,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": True,
            "feedback_notes": [],
        }

        assert route_by_confidence(state) == "approved"

    def test_enhanced_mode_rejects_low(self):
        """Enhanced mode should reject very low confidence."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "rejected",
            "primary_confidence": 0.25,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": True,
            "feedback_notes": [],
        }

        assert route_by_confidence(state) == "rejected"


class TestRouteByCrossResult:
    """Tests for routing after cross-check."""

    def test_always_goes_to_confidence_calc(self):
        """Cross-check should always route to confidence_calc."""
        state: QualityState = {
            "item_id": "test",
            "content": "",
            "title": "",
            "primary_verdict": "needs_review",
            "primary_confidence": 0.75,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": "approved",
            "cross_check_confidence": 0.85,
            "cross_check_agreement": False,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        assert route_by_cross_result(state) == "confidence_calc"


class TestBuildQualityGraph:
    """Tests for graph builder."""

    def test_build_graph_returns_state_graph(self):
        """build_quality_graph should return a StateGraph."""
        from langgraph.graph import StateGraph

        graph = build_quality_graph()

        assert isinstance(graph, StateGraph)

    def test_graph_has_required_nodes(self):
        """Graph should have all required nodes."""
        graph = build_quality_graph()

        # Get node names from graph
        node_names = set(graph.nodes.keys())

        assert "primary_validation" in node_names
        assert "cross_check" in node_names
        assert "confidence_calc" in node_names


class TestQualityGraph:
    """Tests for QualityGraph wrapper class."""

    def test_init_without_checkpoint(self):
        """QualityGraph should initialize without checkpointing."""
        qg = QualityGraph()

        assert qg.checkpoint_path is None
        assert qg.compiled is not None

    def test_init_with_checkpoint(self):
        """QualityGraph should initialize with checkpointing if path provided."""
        from langgraph.checkpoint.memory import MemorySaver

        # sqlite 서브모듈이 없을 수 있으므로(sys.modules) fake 모듈로 주입
        fake_sqlite = MagicMock()
        fake_sqlite.SqliteSaver = MagicMock()
        fake_sqlite.SqliteSaver.from_conn_string = MagicMock(return_value=MemorySaver())

        with patch.dict(sys.modules, {"langgraph.checkpoint.sqlite": fake_sqlite}):
            qg = QualityGraph(checkpoint_path="cache/test.db")

        assert qg.checkpoint_path == "cache/test.db"
        assert qg.compiled is not None
        fake_sqlite.SqliteSaver.from_conn_string.assert_called_once_with("cache/test.db")

    @patch("picko.quality.validators.primary.PrimaryValidator.validate")
    def test_verify_returns_state(self, mock_validate):
        """verify() should return QualityState."""
        mock_validate.return_value = {
            "verdict": "approved",
            "confidence": 0.95,
            "scores": {"factual": 9, "source_credibility": 8, "bias": 9, "value": 8},
            "reasoning": "Test reasoning",
            "flags": [],
        }

        qg = QualityGraph()
        result = qg.verify(
            item_id="test-001",
            title="Test Title",
            content="Test content for validation",
        )

        assert result["item_id"] == "test-001"
        assert result["title"] == "Test Title"
        assert "primary_verdict" in result
        assert "final_verdict" in result


class TestPrimaryValidationNode:
    """Tests for primary_validation_node."""

    @patch("picko.quality.validators.primary.PrimaryValidator.validate")
    def test_node_returns_partial_state(self, mock_validate):
        """primary_validation_node should return partial state update."""
        mock_validate.return_value = {
            "verdict": "approved",
            "confidence": 0.9,
            "scores": {"factual": 9, "source_credibility": 9, "bias": 8, "value": 9},
            "reasoning": "High quality content",
            "flags": [],
        }

        state: QualityState = {
            "item_id": "test",
            "content": "Test content",
            "title": "Test",
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
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        result = primary_validation_node(state)

        assert result["primary_verdict"] == "approved"
        assert result["primary_confidence"] == 0.9
        assert "primary_scores" in result  # Fixed: check primary_scores not scores


class TestCrossCheckNode:
    """Tests for cross_check_node."""

    @patch("picko.quality.validators.cross_check.CrossCheckValidator.validate")
    def test_node_returns_agreement(self, mock_validate):
        """cross_check_node should calculate agreement."""
        mock_validate.return_value = {
            "verdict": "approved",
            "confidence": 0.85,
            "reasoning": "Agrees with primary",
            "agreement": True,
        }

        state: QualityState = {
            "item_id": "test",
            "content": "Test content",
            "title": "Test",
            "primary_verdict": "approved",
            "primary_confidence": 0.9,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": None,
            "cross_check_confidence": None,
            "cross_check_agreement": None,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        result = cross_check_node(state)

        assert result["cross_check_verdict"] == "approved"
        assert result["cross_check_agreement"] is True


class TestConfidenceCalcNode:
    """Tests for confidence_calc_node."""

    @patch("picko.quality.confidence.calculate_final_confidence")
    @patch("picko.quality.confidence.determine_verdict")
    def test_node_calculates_final(self, mock_determine, mock_calculate):
        """confidence_calc_node should calculate final confidence and verdict."""
        mock_calculate.return_value = 0.88
        mock_determine.return_value = "approved"

        state: QualityState = {
            "item_id": "test",
            "content": "Test content",
            "title": "Test",
            "primary_verdict": "approved",
            "primary_confidence": 0.9,
            "primary_scores": {},
            "primary_reasoning": "",
            "primary_flags": [],
            "cross_check_verdict": "approved",
            "cross_check_confidence": 0.85,
            "cross_check_agreement": True,
            "external_check": None,
            "final_verdict": "",
            "final_confidence": 0.0,
            "enhanced_verification": False,
            "feedback_notes": [],
        }

        result = confidence_calc_node(state)

        assert result["final_confidence"] == 0.88
        assert result["final_verdict"] == "approved"
