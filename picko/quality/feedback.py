"""
Feedback Loop - Record and analyze human review decisions.

Records human review results to improve quality criteria over time.
Stores feedback in JSONL format for analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from picko.logger import get_logger

logger = get_logger("quality.feedback")


class FeedbackLoop:
    """
    Record and analyze human review decisions.

    Stores feedback in JSONL format at vault_root/Logs/quality_feedback.jsonl
    Provides metrics on AI accuracy over time.
    """

    def __init__(self, vault_root: str | Path | None = None):
        """
        Initialize FeedbackLoop.

        Args:
            vault_root: Path to Obsidian vault root. If None, uses config.
        """
        if vault_root is None:
            from picko.config import get_config

            vault_root = get_config().vault.root

        self.vault_root = Path(vault_root)
        self.feedback_log = self.vault_root / "Logs" / "quality_feedback.jsonl"
        self.feedback_log.parent.mkdir(parents=True, exist_ok=True)

    def record_feedback(
        self,
        item_id: str,
        ai_verdict: str,
        human_verdict: str,
        ai_confidence: float = 0.0,
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record human review result.

        Args:
            item_id: Unique identifier for the reviewed item
            ai_verdict: AI's verdict (approved/rejected/needs_review)
            human_verdict: Human's final verdict
            ai_confidence: AI's confidence score
            notes: Optional notes from reviewer
            metadata: Optional additional metadata
        """
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "item_id": item_id,
            "ai_verdict": ai_verdict,
            "human_verdict": human_verdict,
            "ai_confidence": ai_confidence,
            "agreement": ai_verdict == human_verdict,
            "notes": notes,
        }

        if metadata:
            feedback["metadata"] = metadata

        # Append to JSONL file
        try:
            with open(self.feedback_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(feedback, ensure_ascii=False) + "\n")

            logger.info(
                f"Recorded feedback: item={item_id}, "
                f"ai={ai_verdict}, human={human_verdict}, "
                f"agreement={feedback['agreement']}"
            )
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")

    def get_accuracy_metrics(self, days: int = 30) -> dict[str, Any]:
        """
        Calculate AI accuracy metrics over the specified period.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Dict containing:
                - total_reviews: Total number of human reviews
                - agreements: Number of AI-human agreements
                - accuracy: Overall agreement rate
                - by_verdict: Breakdown by verdict type
                - avg_confidence_correct: Avg AI confidence when correct
                - avg_confidence_incorrect: Avg AI confidence when wrong
        """
        if not self.feedback_log.exists():
            logger.info("No feedback log found")
            return {
                "total_reviews": 0,
                "agreements": 0,
                "accuracy": 0.0,
                "by_verdict": {},
                "avg_confidence_correct": 0.0,
                "avg_confidence_incorrect": 0.0,
            }

        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        total = 0
        agreements = 0
        by_verdict: dict[str, dict[str, int | float]] = {}
        confidences_correct: list[float] = []
        confidences_incorrect: list[float] = []
        try:
            with open(self.feedback_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())

                        # Check timestamp
                        entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        if entry_time < cutoff:
                            continue

                        total += 1

                        if entry.get("agreement", False):
                            agreements += 1
                            if entry.get("ai_confidence"):
                                confidences_correct.append(entry["ai_confidence"])
                        else:
                            if entry.get("ai_confidence"):
                                confidences_incorrect.append(entry["ai_confidence"])

                        # Track by verdict
                        ai_verdict = entry.get("ai_verdict", "unknown")
                        if ai_verdict not in by_verdict:
                            by_verdict[ai_verdict] = {"total": 0, "correct": 0}
                        by_verdict[ai_verdict]["total"] += 1
                        if entry.get("agreement"):
                            by_verdict[ai_verdict]["correct"] += 1

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        except Exception as e:
            logger.error(f"Failed to read feedback log: {e}")

        # Calculate metrics
        accuracy = agreements / total if total > 0 else 0.0

        avg_conf_correct = sum(confidences_correct) / len(confidences_correct) if confidences_correct else 0.0
        avg_conf_incorrect = sum(confidences_incorrect) / len(confidences_incorrect) if confidences_incorrect else 0.0

        # Calculate per-verdict accuracy
        for verdict in by_verdict:
            v_total = by_verdict[verdict]["total"]
            v_correct = by_verdict[verdict]["correct"]
            by_verdict[verdict]["accuracy"] = v_correct / v_total if v_total > 0 else 0.0

        return {
            "total_reviews": total,
            "agreements": agreements,
            "accuracy": accuracy,
            "by_verdict": by_verdict,
            "avg_confidence_correct": avg_conf_correct,
            "avg_confidence_incorrect": avg_conf_incorrect,
        }

    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent AI errors (disagreements) for analysis.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error entries, most recent first
        """
        if not self.feedback_log.exists():
            return []

        errors = []

        try:
            with open(self.feedback_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if not entry.get("agreement", True):
                            errors.append(entry)
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error(f"Failed to read feedback log: {e}")

        # Return most recent first
        errors.reverse()
        return errors[:limit]

    def get_feedback_for_item(self, item_id: str) -> dict[str, Any] | None:
        """
        Get the most recent feedback for a specific item.

        Args:
            item_id: Item identifier to look up

        Returns:
            Most recent feedback entry or None if not found
        """
        if not self.feedback_log.exists():
            return None

        try:
            with open(self.feedback_log, "r", encoding="utf-8") as f:
                for line in reversed(list(f)):
                    try:
                        entry: dict[str, Any] = json.loads(line.strip())
                        if entry.get("item_id") == item_id:
                            return entry
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error(f"Failed to read feedback log: {e}")

        return None
