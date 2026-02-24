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
            concept="PMF 달성 전략",
            overlay_text="",
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
