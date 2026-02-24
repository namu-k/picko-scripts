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

    def test_render_data_template_with_trend_up(self):
        """Render data template with upward trend indicator."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="data",
            context={
                "value": "150%",
                "label": "성장률",
                "trend": "up",
                "trend_value": "+50%",
                "background_color": "#ffffff",
            },
        )

        assert "▲" in result
        assert "+50%" in result

    def test_render_data_template_with_trend_down(self):
        """Render data template with downward trend indicator."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="data",
            context={
                "value": "75%",
                "label": "달성률",
                "trend": "down",
                "trend_value": "-25%",
                "background_color": "#ffffff",
            },
        )

        assert "▼" in result
        assert "-25%" in result

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

    def test_render_quote_with_dynamic_dimensions(self):
        """Render quote template with custom width/height."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="quote",
            context={
                "quote": "테스트 문구",
                "background_color": "#1a1a2e",
                "width": 1200,
                "height": 627,
            },
        )

        assert "width: 1200px" in result
        assert "height: 627px" in result

    def test_render_uses_default_dimensions_when_not_specified(self):
        """Render template with default 1080x1080 when dimensions not provided."""
        renderer = get_image_renderer()

        result = renderer.render_image(
            template="card",
            context={
                "title": "테스트",
                "summary": "요약",
                "background_color": "#ffffff",
            },
        )

        assert "width: 1080px" in result
        assert "height: 1080px" in result


class TestPlatformDimensions:
    """Test platform-specific image dimensions."""

    def test_get_dimensions_for_linkedin(self):
        """LinkedIn uses landscape format 1200x627."""
        from picko.html_renderer import get_dimensions_for_channel

        width, height = get_dimensions_for_channel("linkedin")
        assert width == 1200
        assert height == 627

    def test_get_dimensions_for_twitter(self):
        """Twitter uses landscape format 1200x675."""
        from picko.html_renderer import get_dimensions_for_channel

        width, height = get_dimensions_for_channel("twitter")
        assert width == 1200
        assert height == 675

    def test_get_dimensions_for_instagram(self):
        """Instagram feed uses square format 1080x1080."""
        from picko.html_renderer import get_dimensions_for_channel

        width, height = get_dimensions_for_channel("instagram")
        assert width == 1080
        assert height == 1080

    def test_get_dimensions_for_instagram_story(self):
        """Instagram story uses portrait format 1080x1920."""
        from picko.html_renderer import get_dimensions_for_channel

        width, height = get_dimensions_for_channel("instagram_story")
        assert width == 1080
        assert height == 1920

    def test_get_dimensions_for_threads(self):
        """Threads uses portrait format 1080x1350."""
        from picko.html_renderer import get_dimensions_for_channel

        width, height = get_dimensions_for_channel("threads")
        assert width == 1080
        assert height == 1350

    def test_get_dimensions_for_unknown_channel(self):
        """Unknown channel returns default 1080x1080."""
        from picko.html_renderer import get_dimensions_for_channel

        width, height = get_dimensions_for_channel("unknown_platform")
        assert width == 1080
        assert height == 1080

    def test_get_dimensions_case_insensitive(self):
        """Channel names are case insensitive."""
        from picko.html_renderer import get_dimensions_for_channel

        width1, height1 = get_dimensions_for_channel("LinkedIn")
        width2, height2 = get_dimensions_for_channel("LINKEDIN")
        width3, height3 = get_dimensions_for_channel("linkedin")

        assert (width1, height1) == (width2, height2) == (width3, height3)

    def test_get_dimensions_with_alias(self):
        """Aliases like 'ig' and 'x' work correctly."""
        from picko.html_renderer import get_dimensions_for_channel

        # 'ig' should map to instagram_feed
        width_ig, height_ig = get_dimensions_for_channel("ig")
        width_insta, height_insta = get_dimensions_for_channel("instagram")
        assert (width_ig, height_ig) == (width_insta, height_insta)

        # 'x' should map to twitter
        width_x, height_x = get_dimensions_for_channel("x")
        width_tw, height_tw = get_dimensions_for_channel("twitter")
        assert (width_x, height_x) == (width_tw, height_tw)
