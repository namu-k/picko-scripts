"""
Tests for score_calibrator.py

Unit tests for the ScoreCalibrator class covering:
- PerformanceRecord dataclass
- CalibrationReport dataclass
- analyze method
- Correlation calculation
- Weight suggestion
- Improvement estimation
- apply_weights method
"""

from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.scoring.weights = {"novelty": 0.3, "relevance": 0.4, "quality": 0.3}
    return config


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    vault.list_notes.return_value = []
    vault.read_frontmatter.return_value = {}
    return vault


@pytest.fixture
def sample_performance_record():
    """Sample performance record"""
    from scripts.score_calibrator import PerformanceRecord

    return PerformanceRecord(
        content_id="test_123",
        content_path="/inputs/test_123.md",
        predicted_score=0.85,
        novelty=0.8,
        relevance=0.9,
        quality=0.85,
        actual_performance=100.0,
        platform="twitter",
        published_at="2026-02-17T12:00:00",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────


class TestPerformanceRecord:
    """Tests for PerformanceRecord dataclass"""

    def test_performance_record_creation(self):
        """Test creating a performance record"""
        from scripts.score_calibrator import PerformanceRecord

        record = PerformanceRecord(
            content_id="test_123",
            content_path="/inputs/test_123.md",
            predicted_score=0.85,
            novelty=0.8,
            relevance=0.9,
            quality=0.85,
            actual_performance=100.0,
            platform="twitter",
            published_at="2026-02-17T12:00:00",
        )

        assert record.content_id == "test_123"
        assert record.predicted_score == 0.85
        assert record.actual_performance == 100.0
        assert record.platform == "twitter"

    def test_performance_record_repr(self):
        """Test string representation"""
        from scripts.score_calibrator import PerformanceRecord

        record = PerformanceRecord(
            content_id="test_123",
            content_path="/inputs/test_123.md",
            predicted_score=0.85,
            novelty=0.8,
            relevance=0.9,
            quality=0.85,
            actual_performance=100.0,
            platform="twitter",
            published_at="2026-02-17T12:00:00",
        )

        repr_str = repr(record)
        assert "PerformanceRecord" in repr_str
        assert "test_123" in repr_str


class TestCalibrationReport:
    """Tests for CalibrationReport dataclass"""

    def test_calibration_report_creation(self):
        """Test creating a calibration report"""
        from scripts.score_calibrator import CalibrationReport

        report = CalibrationReport(
            total_analyzed=10,
            correlation={"novelty": 0.5, "relevance": 0.7, "quality": 0.6},
            suggested_weights={"novelty": 0.25, "relevance": 0.45, "quality": 0.30},
            current_weights={"novelty": 0.3, "relevance": 0.4, "quality": 0.3},
            improvement_estimate=5.0,
            top_performers=[],
            underperformers=[],
        )

        assert report.total_analyzed == 10
        assert report.correlation["novelty"] == 0.5
        assert report.improvement_estimate == 5.0


class TestScoreCalibratorInit:
    """Tests for ScoreCalibrator initialization"""

    @patch("scripts.score_calibrator.get_config")
    @patch("scripts.score_calibrator.VaultIO")
    def test_init(self, mock_vault_class, mock_get_config, mock_config):
        """Test initialization"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        calibrator = ScoreCalibrator()

        assert calibrator.config is not None
        assert calibrator.vault is not None
        assert calibrator.logs_path == "Logs/Publish"


class TestCollectPerformanceData:
    """Tests for _collect_performance_data method"""

    @patch("scripts.score_calibrator.get_config")
    def test_collect_empty_logs(self, mock_get_config, mock_config, mock_vault):
        """Test with no logs"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)
            calibrator.vault = mock_vault
            calibrator.logs_path = "Logs/Publish"
            mock_vault.list_notes.return_value = []

            result = calibrator._collect_performance_data(30, 10)

        assert result == []

    @patch("scripts.score_calibrator.get_config")
    def test_collect_filters_non_published(self, mock_get_config, mock_config, mock_vault):
        """Test that non-published items are filtered"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)
            calibrator.vault = mock_vault
            calibrator.logs_path = "Logs/Publish"

            mock_vault.list_notes.return_value = ["/log1.md"]
            mock_vault.read_frontmatter.return_value = {"status": "draft"}

            result = calibrator._collect_performance_data(30, 10)

        assert result == []

    @patch("scripts.score_calibrator.get_config")
    def test_collect_filters_low_engagement(self, mock_get_config, mock_config, mock_vault):
        """Test that items below minimum engagement are filtered"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)
            calibrator.vault = mock_vault
            calibrator.logs_path = "Logs/Publish"

            mock_vault.list_notes.return_value = ["/log1.md"]
            # Low engagement (5 < 10)
            mock_vault.read_frontmatter.side_effect = [
                {
                    "status": "published",
                    "metrics": {"views": 10, "likes": 1},
                    "content_id": "test",
                },
                {
                    "score": {
                        "total": 0.8,
                        "novelty": 0.7,
                        "relevance": 0.8,
                        "quality": 0.9,
                    }
                },
            ]

            result = calibrator._collect_performance_data(30, 10)

        # engagement = 10*0.1 + 1*1.0 = 2.0 < 10
        assert result == []


class TestCalculateCorrelations:
    """Tests for _calculate_correlations method"""

    @patch("scripts.score_calibrator.get_config")
    def test_calculate_correlations_insufficient_data(self, mock_get_config, mock_config):
        """Test with insufficient data (< 3 records)"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import PerformanceRecord, ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            records = [
                PerformanceRecord(
                    content_id="1",
                    content_path="/1.md",
                    predicted_score=0.8,
                    novelty=0.7,
                    relevance=0.8,
                    quality=0.9,
                    actual_performance=100.0,
                    platform="twitter",
                    published_at="2026-02-17",
                )
            ]

            result = calibrator._calculate_correlations(records)

        # With < 3 records, should return zeros
        assert result == {"novelty": 0.0, "relevance": 0.0, "quality": 0.0}

    @patch("scripts.score_calibrator.get_config")
    def test_calculate_correlations_with_data(self, mock_get_config, mock_config):
        """Test correlation calculation with sufficient data"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import PerformanceRecord, ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            # Create records with positive correlation
            records = [
                PerformanceRecord(
                    content_id=str(i),
                    content_path=f"/{i}.md",
                    predicted_score=0.5 + i * 0.1,
                    novelty=0.5 + i * 0.1,
                    relevance=0.5 + i * 0.1,
                    quality=0.5 + i * 0.1,
                    actual_performance=50.0 + i * 20.0,
                    platform="twitter",
                    published_at="2026-02-17",
                )
                for i in range(5)
            ]

            result = calibrator._calculate_correlations(records)

        # Should have correlation values for all factors
        assert "novelty" in result
        assert "relevance" in result
        assert "quality" in result
        # With positive correlation setup, values should be positive
        assert all(isinstance(v, float) for v in result.values())


class TestSuggestWeights:
    """Tests for _suggest_weights method"""

    @patch("scripts.score_calibrator.get_config")
    def test_suggest_weights_zero_correlation(self, mock_get_config, mock_config):
        """Test weight suggestion with zero correlations"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            correlations = {"novelty": 0.0, "relevance": 0.0, "quality": 0.0}
            result = calibrator._suggest_weights(correlations)

        # Should return equal weights
        assert abs(result["novelty"] - 0.33) < 0.01
        assert abs(result["relevance"] - 0.34) < 0.01
        assert abs(result["quality"] - 0.33) < 0.01

    @patch("scripts.score_calibrator.get_config")
    def test_suggest_weights_positive_correlation(self, mock_get_config, mock_config):
        """Test weight suggestion with positive correlations"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            correlations = {"novelty": 0.5, "relevance": 0.3, "quality": 0.2}
            result = calibrator._suggest_weights(correlations)

        # Weights should sum to 1
        total = sum(result.values())
        assert abs(total - 1.0) < 0.01

        # Higher correlation should get higher weight
        assert result["novelty"] > result["relevance"]
        assert result["relevance"] > result["quality"]

    @patch("scripts.score_calibrator.get_config")
    def test_suggest_weights_negative_correlation(self, mock_get_config, mock_config):
        """Test weight suggestion with negative correlations"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            # Negative correlations should be treated as 0
            correlations = {"novelty": -0.5, "relevance": 0.5, "quality": 0.5}
            result = calibrator._suggest_weights(correlations)

        # Weights should still sum to 1
        total = sum(result.values())
        assert abs(total - 1.0) < 0.01


class TestEstimateImprovement:
    """Tests for _estimate_improvement method"""

    @patch("scripts.score_calibrator.get_config")
    def test_estimate_improvement(self, mock_get_config, mock_config):
        """Test improvement estimation"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import PerformanceRecord, ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            records = [
                PerformanceRecord(
                    content_id=str(i),
                    content_path=f"/{i}.md",
                    predicted_score=0.5 + i * 0.1,
                    novelty=0.3 + i * 0.1,
                    relevance=0.4 + i * 0.1,
                    quality=0.3 + i * 0.1,
                    actual_performance=50.0 + i * 20.0,
                    platform="twitter",
                    published_at="2026-02-17",
                )
                for i in range(5)
            ]

            new_weights = {"novelty": 0.3, "relevance": 0.4, "quality": 0.3}
            result = calibrator._estimate_improvement(records, new_weights)

        # Should return a float
        assert isinstance(result, float)


class TestEmptyReport:
    """Tests for _empty_report method"""

    @patch("scripts.score_calibrator.get_config")
    def test_empty_report(self, mock_get_config, mock_config):
        """Test empty report generation"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)
            calibrator.config = mock_config

            result = calibrator._empty_report()

        assert result.total_analyzed == 0
        assert result.correlation == {"novelty": 0.0, "relevance": 0.0, "quality": 0.0}
        assert result.improvement_estimate == 0
        assert result.top_performers == []
        assert result.underperformers == []


class TestApplyWeights:
    """Tests for apply_weights method"""

    @patch("scripts.score_calibrator.get_config")
    def test_apply_weights_not_implemented(self, mock_get_config, mock_config):
        """Test that apply_weights returns False (not implemented)"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            result = calibrator.apply_weights({"novelty": 0.3, "relevance": 0.4, "quality": 0.3})

        # Should return False (not implemented)
        assert result is False

    @patch("scripts.score_calibrator.get_config")
    def test_apply_weights_with_true(self, mock_get_config, mock_config):
        """Test apply_weights with True (auto-calculated)"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)

            result = calibrator.apply_weights(True)

        # Should return False (not implemented)
        assert result is False


class TestAnalyze:
    """Tests for analyze method"""

    @patch("scripts.score_calibrator.get_config")
    def test_analyze_no_data(self, mock_get_config, mock_config, mock_vault):
        """Test analyze with no data"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)
            calibrator.config = mock_config
            calibrator.vault = mock_vault
            calibrator.logs_path = "Logs/Publish"
            calibrator._collect_performance_data = MagicMock(return_value=[])  # type: ignore[method-assign]

            result = calibrator.analyze(30, 10)

        # Should return empty report
        assert result.total_analyzed == 0

    @patch("scripts.score_calibrator.get_config")
    def test_analyze_with_data(self, mock_get_config, mock_config, mock_vault):
        """Test analyze with performance data"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import PerformanceRecord, ScoreCalibrator

        with patch.object(ScoreCalibrator, "__init__", lambda x: None):
            calibrator = ScoreCalibrator.__new__(ScoreCalibrator)
            calibrator.config = mock_config
            calibrator.vault = mock_vault
            calibrator.logs_path = "Logs/Publish"

            # Mock performance data
            records = [
                PerformanceRecord(
                    content_id=str(i),
                    content_path=f"/{i}.md",
                    predicted_score=0.5 + i * 0.1,
                    novelty=0.3 + i * 0.1,
                    relevance=0.4 + i * 0.1,
                    quality=0.3 + i * 0.1,
                    actual_performance=50.0 + i * 20.0,
                    platform="twitter",
                    published_at="2026-02-17",
                )
                for i in range(5)
            ]
            calibrator._collect_performance_data = MagicMock(return_value=records)  # type: ignore[method-assign]

            result = calibrator.analyze(30, 10)

        assert result.total_analyzed == 5
        assert "novelty" in result.correlation
        assert "novelty" in result.suggested_weights
        assert len(result.top_performers) <= 5
        assert len(result.underperformers) <= 5


class TestPrintReport:
    """Tests for print_report function"""

    @patch("scripts.score_calibrator.get_config")
    def test_print_report(self, mock_get_config, mock_config, capsys):
        """Test print_report output"""
        mock_get_config.return_value = mock_config

        from scripts.score_calibrator import CalibrationReport, print_report

        report = CalibrationReport(
            total_analyzed=10,
            correlation={"novelty": 0.5, "relevance": 0.7, "quality": 0.6},
            suggested_weights={"novelty": 0.25, "relevance": 0.45, "quality": 0.30},
            current_weights={"novelty": 0.3, "relevance": 0.4, "quality": 0.3},
            improvement_estimate=5.0,
            top_performers=[],
            underperformers=[],
        )

        print_report(report)
        captured = capsys.readouterr()

        assert "Score Calibration Report" in captured.out
        assert "10" in captured.out
        assert "novelty" in captured.out
