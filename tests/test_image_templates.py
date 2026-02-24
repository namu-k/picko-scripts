"""Tests for image HTML templates."""

import pytest

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

    def test_render_data_template(self):
        """Render data template with number and label."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="data",
            context={
                "value": "200%",
                "unit": "증가",
                "label": "월간 사용자 성장률",
                "description": "지난 분기 대비",
                "background_color": "#ffffff",
            },
        )

        assert "200%" in result
        assert "월간 사용자 성장률" in result

    def test_render_carousel_template(self):
        """Render carousel template with slide content."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="carousel",
            context={
                "slide_number": 1,
                "total_slides": 5,
                "title": "5가지 성장 전략",
                "content": "첫 번째 전략: 고객 피드백 적극 수용",
                "cta": "다음 슬라이드 보기 →",
                "background_color": "#1a1a2e",
            },
        )

        assert "5가지 성장 전략" in result

    def test_invalid_template_raises(self):
        """Invalid template name should raise ValueError."""
        renderer = get_image_renderer()

        with pytest.raises(ValueError, match="Invalid template"):
            renderer.render_image(
                template="nonexistent",
                context={"title": "test"},
            )
