"""Tests for proposal generator."""

from picko.multimedia_io import MultimediaInput
from picko.proposal_generator import Proposal, generate_proposal


class TestProposalGenerator:
    """Test proposal generation."""

    def test_proposal_dataclass(self):
        """Proposal dataclass holds all required fields."""
        proposal = Proposal(
            input_id="mm_001",
            content_type="quote",
            template="quote.html",
            background_prompt="minimal gradient",
            overlay_text="Test quote",
            style_preset="minimal_infographic",
            channels=["linkedin"],
        )

        assert proposal.content_type == "quote"
        assert proposal.template == "quote.html"

    def test_determine_content_type_quote(self):
        """Determine quote type for short text."""
        input_data = MultimediaInput(
            id="mm_001",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="Test",
            overlay_text="짧은 문구 하나",
            created="2026-02-24",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "quote"

    def test_determine_content_type_list(self):
        """Determine list type for list-like content."""
        input_data = MultimediaInput(
            id="mm_002",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="창업자를 위한 5가지 방법",
            overlay_text="",
            created="2026-02-24",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "list"

    def test_determine_content_type_data(self):
        """Determine data type for data-like content."""
        input_data = MultimediaInput(
            id="mm_003",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="성장률 200% 증가",
            overlay_text="",
            created="2026-02-24",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "data"

    def test_determine_content_type_card_default(self):
        """Default to card when no clear type indicator."""
        input_data = MultimediaInput(
            id="mm_004",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="스타트업 소개",  # No list/data/quote indicators
            overlay_text="",  # Empty overlay → no quote detection
            created="2026-02-24",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "card"

    def test_proposal_has_correct_template(self):
        """Proposal maps content type to correct template."""
        input_data = MultimediaInput(
            id="mm_005",
            account="test",
            source_type="standalone",
            channels=["twitter"],
            content_types=["image"],
            concept="Test",
            overlay_text="짧은 문구",
            created="2026-02-24",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.template == "quote.html"
        assert proposal.channels == ["twitter"]

    def test_list_priority_over_quote(self):
        """List indicators in concept should override short overlay text."""
        input_data = MultimediaInput(
            id="mm_006",
            account="test",
            source_type="standalone",
            channels=["instagram"],
            content_types=["image"],
            concept="창업자가 피해야 할 5가지 실수",
            overlay_text="이것은 짧은 문구입니다",  # Short but concept has list indicator
            created="2026-02-25",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "list"

    def test_data_priority_over_quote(self):
        """Data indicators should override short overlay text."""
        input_data = MultimediaInput(
            id="mm_007",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="월간 사용자 성장률 200% 증가",
            overlay_text="지난 분기 대비",  # Short but concept has data indicator
            created="2026-02-25",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "data"

    def test_list_priority_over_data(self):
        """List indicators should be detected before data indicators."""
        input_data = MultimediaInput(
            id="mm_008",
            account="test",
            source_type="standalone",
            channels=["linkedin"],
            content_types=["image"],
            concept="성장률 200% 달성을 위한 5단계 전략",
            overlay_text="",
            created="2026-02-25",
        )

        proposal = generate_proposal(input_data, account_config={}, references=[])
        assert proposal.content_type == "list"  # List takes priority

    def test_extended_list_indicators(self):
        """Extended list indicators work correctly."""
        test_cases = [
            ("창업자를 위한 3단계 가이드", "list"),
            ("성공하는 7가지 습관", "list"),
            ("마케팅 방법 총정리", "list"),
            ("실수 방지 체크리스트", "list"),
            ("투자 유치 전략", "list"),
            ("일하는 원칙", "list"),
        ]

        for concept, expected_type in test_cases:
            input_data = MultimediaInput(
                id=f"mm_{concept[:5]}",
                account="test",
                source_type="standalone",
                channels=["linkedin"],
                content_types=["image"],
                concept=concept,
                overlay_text="",
                created="2026-02-25",
            )
            proposal = generate_proposal(input_data, account_config={}, references=[])
            assert proposal.content_type == expected_type, f"Failed for: {concept}"

    def test_extended_data_indicators(self):
        """Extended data indicators work correctly."""
        test_cases = [
            ("매출 300% 달성", "data"),
            ("사용자 2배 증가", "data"),
            ("이탈률 50% 감소", "data"),
            ("월간 수치 분석", "data"),
            ("목표 기록 달성", "data"),
        ]

        for concept, expected_type in test_cases:
            input_data = MultimediaInput(
                id=f"mm_{concept[:5]}",
                account="test",
                source_type="standalone",
                channels=["linkedin"],
                content_types=["image"],
                concept=concept,
                overlay_text="",
                created="2026-02-25",
            )
            proposal = generate_proposal(input_data, account_config={}, references=[])
            assert proposal.content_type == expected_type, f"Failed for: {concept}"
