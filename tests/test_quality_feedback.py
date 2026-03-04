"""
Tests for Quality Feedback Loop.

Tests feedback recording, metrics calculation, and error analysis.
"""

import json
from datetime import datetime, timedelta

import pytest

from picko.quality.feedback import FeedbackLoop


class TestFeedbackLoop:
    """Tests for FeedbackLoop class."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create temporary vault directory."""
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    @pytest.fixture
    def feedback(self, temp_vault):
        """Create FeedbackLoop with temporary vault."""
        return FeedbackLoop(vault_root=temp_vault)

    def test_init_creates_logs_directory(self, temp_vault):
        """FeedbackLoop should create Logs directory if not exists."""
        FeedbackLoop(vault_root=temp_vault)

        logs_dir = temp_vault / "Logs"
        assert logs_dir.exists()

    def test_record_feedback_creates_file(self, feedback, temp_vault):
        """record_feedback should create JSONL file."""
        feedback.record_feedback(
            item_id="test-001",
            ai_verdict="approved",
            human_verdict="approved",
            ai_confidence=0.9,
        )

        log_file = temp_vault / "Logs" / "quality_feedback.jsonl"
        assert log_file.exists()

    def test_record_feedback_appends_to_file(self, feedback):
        """record_feedback should append entries to file."""
        feedback.record_feedback(
            item_id="test-001",
            ai_verdict="approved",
            human_verdict="approved",
        )
        feedback.record_feedback(
            item_id="test-002",
            ai_verdict="rejected",
            human_verdict="rejected",
        )

        log_file = feedback.feedback_log
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2

    def test_record_feedback_stores_all_fields(self, feedback):
        """record_feedback should store all provided fields."""
        feedback.record_feedback(
            item_id="test-001",
            ai_verdict="approved",
            human_verdict="rejected",
            ai_confidence=0.85,
            notes="Human disagreed due to bias",
            metadata={"source": "test"},
        )

        log_file = feedback.feedback_log
        with open(log_file, "r") as f:
            entry = json.loads(f.readline())

        assert entry["item_id"] == "test-001"
        assert entry["ai_verdict"] == "approved"
        assert entry["human_verdict"] == "rejected"
        assert entry["ai_confidence"] == 0.85
        assert entry["notes"] == "Human disagreed due to bias"
        assert entry["metadata"]["source"] == "test"
        assert entry["agreement"] is False
        assert "timestamp" in entry

    def test_record_feedback_calculates_agreement(self, feedback):
        """record_feedback should calculate agreement."""
        feedback.record_feedback(
            item_id="test-agree",
            ai_verdict="approved",
            human_verdict="approved",
        )
        feedback.record_feedback(
            item_id="test-disagree",
            ai_verdict="approved",
            human_verdict="rejected",
        )

        log_file = feedback.feedback_log
        with open(log_file, "r") as f:
            lines = f.readlines()

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])

        assert entry1["agreement"] is True
        assert entry2["agreement"] is False


class TestGetAccuracyMetrics:
    """Tests for accuracy metrics calculation."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create temporary vault directory."""
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    @pytest.fixture
    def feedback(self, temp_vault):
        """Create FeedbackLoop with temporary vault."""
        return FeedbackLoop(vault_root=temp_vault)

    def test_empty_log_returns_zero_metrics(self, feedback):
        """Empty log should return zero metrics."""
        metrics = feedback.get_accuracy_metrics()

        assert metrics["total_reviews"] == 0
        assert metrics["accuracy"] == 0.0

    def test_calculates_overall_accuracy(self, feedback):
        """Should calculate overall agreement rate."""
        # Add 4 entries: 3 agreements, 1 disagreement
        for i, agree in enumerate([True, True, True, False]):
            feedback.record_feedback(
                item_id=f"test-{i}",
                ai_verdict="approved",
                human_verdict="approved" if agree else "rejected",
            )

        metrics = feedback.get_accuracy_metrics()

        assert metrics["total_reviews"] == 4
        assert metrics["agreements"] == 3
        assert metrics["accuracy"] == 0.75

    def test_filters_by_days(self, feedback):
        """Should only include entries within specified days."""
        # Create old entry
        old_entry = {
            "timestamp": (datetime.now() - timedelta(days=60)).isoformat(),
            "item_id": "old",
            "ai_verdict": "approved",
            "human_verdict": "approved",
            "agreement": True,
        }

        # Write old entry directly
        with open(feedback.feedback_log, "w") as f:
            f.write(json.dumps(old_entry) + "\n")

        # Add new entry
        feedback.record_feedback(
            item_id="new",
            ai_verdict="approved",
            human_verdict="approved",
        )

        # Get metrics for 30 days
        metrics = feedback.get_accuracy_metrics(days=30)

        # Should only include new entry
        assert metrics["total_reviews"] == 1

    def test_calculates_by_verdict_breakdown(self, feedback):
        """Should calculate accuracy by verdict type."""
        feedback.record_feedback(item_id="1", ai_verdict="approved", human_verdict="approved")
        feedback.record_feedback(item_id="2", ai_verdict="approved", human_verdict="rejected")
        feedback.record_feedback(item_id="3", ai_verdict="rejected", human_verdict="rejected")

        metrics = feedback.get_accuracy_metrics()

        assert "approved" in metrics["by_verdict"]
        assert "rejected" in metrics["by_verdict"]
        assert metrics["by_verdict"]["approved"]["total"] == 2
        assert metrics["by_verdict"]["approved"]["correct"] == 1
        assert metrics["by_verdict"]["approved"]["accuracy"] == 0.5

    def test_calculates_avg_confidence_correct_vs_incorrect(self, feedback):
        """Should calculate average confidence for correct vs incorrect."""
        feedback.record_feedback(
            item_id="1",
            ai_verdict="approved",
            human_verdict="approved",
            ai_confidence=0.9,
        )
        feedback.record_feedback(
            item_id="2",
            ai_verdict="approved",
            human_verdict="rejected",
            ai_confidence=0.7,
        )

        metrics = feedback.get_accuracy_metrics()

        assert metrics["avg_confidence_correct"] == 0.9
        assert metrics["avg_confidence_incorrect"] == 0.7


class TestGetRecentErrors:
    """Tests for recent error retrieval."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create temporary vault directory."""
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    @pytest.fixture
    def feedback(self, temp_vault):
        """Create FeedbackLoop with temporary vault."""
        return FeedbackLoop(vault_root=temp_vault)

    def test_returns_disagreements_only(self, feedback):
        """Should only return entries where AI was wrong."""
        feedback.record_feedback(
            item_id="correct",
            ai_verdict="approved",
            human_verdict="approved",
        )
        feedback.record_feedback(
            item_id="wrong",
            ai_verdict="approved",
            human_verdict="rejected",
        )

        errors = feedback.get_recent_errors()

        assert len(errors) == 1
        assert errors[0]["item_id"] == "wrong"

    def test_respects_limit(self, feedback):
        """Should respect the limit parameter."""
        for i in range(5):
            feedback.record_feedback(
                item_id=f"wrong-{i}",
                ai_verdict="approved",
                human_verdict="rejected",
            )

        errors = feedback.get_recent_errors(limit=3)

        assert len(errors) == 3

    def test_returns_most_recent_first(self, feedback):
        """Should return errors in reverse chronological order."""
        for i in range(3):
            feedback.record_feedback(
                item_id=f"wrong-{i}",
                ai_verdict="approved",
                human_verdict="rejected",
            )

        errors = feedback.get_recent_errors()

        # Most recent should be first
        assert errors[0]["item_id"] == "wrong-2"
        assert errors[2]["item_id"] == "wrong-0"


class TestGetFeedbackForItem:
    """Tests for item-specific feedback lookup."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create temporary vault directory."""
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    @pytest.fixture
    def feedback(self, temp_vault):
        """Create FeedbackLoop with temporary vault."""
        return FeedbackLoop(vault_root=temp_vault)

    def test_returns_entry_for_item(self, feedback):
        """Should return feedback entry for specific item."""
        feedback.record_feedback(
            item_id="target-item",
            ai_verdict="approved",
            human_verdict="approved",
        )

        result = feedback.get_feedback_for_item("target-item")

        assert result is not None
        assert result["item_id"] == "target-item"

    def test_returns_none_for_unknown_item(self, feedback):
        """Should return None for unknown item."""
        feedback.record_feedback(
            item_id="known-item",
            ai_verdict="approved",
            human_verdict="approved",
        )

        result = feedback.get_feedback_for_item("unknown-item")

        assert result is None

    def test_returns_most_recent_for_item(self, feedback):
        """Should return most recent feedback for item with multiple entries."""
        feedback.record_feedback(
            item_id="item-1",
            ai_verdict="approved",
            human_verdict="approved",
            notes="First review",
        )
        feedback.record_feedback(
            item_id="item-1",
            ai_verdict="needs_review",
            human_verdict="approved",
            notes="Second review",
        )

        result = feedback.get_feedback_for_item("item-1")

        assert result["notes"] == "Second review"
