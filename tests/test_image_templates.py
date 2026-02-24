"""Tests for image HTML templates."""

from picko.templates import get_image_renderer


class TestImageTemplates:
    """Test image template rendering."""

    def test_render_quote_template(self):
        """Render quote template with text."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="quote",
            context={
                "quote": "시간은 창업자의 가장 귀한 자산이다",
                "author": "",
                "background_color": "#1a1a2e",
            },
        )

        assert "시간은 창업자의 가장 귀한 자산이다" in result
        assert "<html" in result
        assert "</html>" in result

    def test_render_quote_with_author(self):
        """Render quote template with author."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="quote",
            context={
                "quote": "실패는 성공의 어머니다",
                "author": "속담",
                "background_color": "#1a1a2e",
            },
        )

        assert "실패는 성공의 어머니다" in result
        assert "속담" in result

    def test_render_card_template(self):
        """Render card template with title and summary."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="card",
            context={
                "title": "PMF 달성 전략",
                "summary": "제품 시장 적합성을 찾는 5단계 가이드",
                "background_color": "#ffffff",
            },
        )

        assert "PMF 달성 전략" in result
        assert "5단계" in result

    def test_render_list_template(self):
        """Render list template with items."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="list",
            context={
                "title": "창업자 체크리스트",
                "items": ["아이디어 검증", "MVP 개발", "고객 인터뷰"],
                "background_color": "#f5f5f5",
            },
        )

        assert "창업자 체크리스트" in result
        assert "아이디어 검증" in result
