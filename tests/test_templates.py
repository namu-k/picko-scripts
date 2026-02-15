"""
Unit tests for picko.templates module
"""

import pytest

from picko.templates import TemplateRenderer


class TestTemplateRenderer:
    """TemplateRenderer tests"""

    @pytest.fixture
    def renderer(self):
        """TemplateRenderer 인스턴스"""
        return TemplateRenderer()

    def test_render_string_basic(self, renderer):
        """기본 문자열 렌더링"""
        result = renderer.render_string("Hello {{ name }}!", name="World")
        assert result == "Hello World!"

    def test_render_string_with_dict(self, renderer):
        """딕셔너리로 렌더링"""
        context = {"title": "Test", "body": "Content"}
        result = renderer.render_string("# {{ title }}\n\n{{ body }}", **context)
        assert result == "# Test\n\nContent"

    def test_render_string_date_filter(self, renderer):
        """format_date 필터 테스트"""
        date_str = "2026-02-15T10:30:00"
        result = renderer.render_string("{{ date | format_date }}", date=date_str)
        assert "2026-02-15" in result

    def test_render_string_truncate_filter(self, renderer):
        """truncate_smart 필터 테스트"""
        long_text = "This is a very long text that should be truncated"
        result = renderer.render_string("{{ text | truncate_smart(20) }}", text=long_text)
        assert len(result) < len(long_text)
        assert "..." in result

    def test_render_input_note(self, renderer):
        """Input 노트 렌더링"""
        content = {
            "id": "test_123",
            "title": "Test Content",
            "source": "TechCrunch",
            "source_url": "https://techcrunch.com/test",
            "publish_date": "2026-02-15",
            "collected_at": "2026-02-15T10:00:00",
            "score": {"novelty": 0.8, "relevance": 0.7, "quality": 0.6, "total": 0.69},
            "tags": ["AI", "tech"],
            "summary": "This is a test summary",
            "key_points": ["Point 1", "Point 2"],
            "excerpt": "This is an excerpt",
        }
        result = renderer.render_input_note(content)
        assert "---" in result
        assert "id: test_123" in result
        assert "# Test Content" in result
        assert "This is a test summary" in result
        assert "- Point 1" in result

    def test_render_digest(self, renderer):
        """Digest 노트 렌더링"""
        items = [
            {
                "id": "test_123",
                "title": "Test Article",
                "writing_status": "pending",
                "score": {"total": 0.85, "novelty": 0.9, "relevance": 0.8, "quality": 0.85},
                "source": "TechCrunch",
                "source_url": "https://techcrunch.com/test",
                "summary": "Test summary content",
            }
        ]
        result = renderer.render_digest("2026-02-15", items)
        assert "# Daily Digest: 2026-02-15" in result
        assert "## [ ] Test Article" in result
        assert "test_123" in result

    def test_render_longform(self, renderer):
        """Longform 콘텐츠 렌더링"""
        content = {
            "id": "longform_123",
            "source_input_id": "test_123",
            "title": "Longform Article Title",
            "intro": "Introduction paragraph",
            "main_content": "Main content here",
            "takeaways": "Key takeaways",
            "cta": "Call to action",
            "tags": ["AI", "technology"],
        }
        result = renderer.render_longform(content)
        assert "# Longform Article Title" in result
        assert "## 핵심 내용" in result
        assert "## 주요 시사점" in result

    def test_render_pack(self, renderer):
        """Pack 콘텐츠 렌더링"""
        content = {
            "id": "pack_123",
            "source_longform_id": "longform_123",
            "text": "This is a social media post content",
            "hashtags": ["#AI", "#tech"],
        }
        channel_config = {"max_length": 280, "tone": "casual", "hashtags": True}
        result = renderer.render_pack(content, "twitter", channel_config)
        assert "# Twitter Pack" in result  # Template capitalizes channel name
        assert "This is a social media post content" in result

    def test_render_image_prompt(self, renderer):
        """이미지 프롬프트 렌더링"""
        content = {
            "id": "img_123",
            "source_content_id": "longform_123",
            "prompt": "A futuristic AI interface",
            "style": "cyberpunk",
            "mood": "dramatic",
            "colors": "neon blue and pink",
            "negative_prompt": "text, blurry",
            "reference_images": ["ref1.jpg", "ref2.jpg"],
        }
        result = renderer.render_image_prompt(content)
        assert "# Image Prompt" in result
        assert "## 메인 프롬프트" in result
        assert "A futuristic AI interface" in result
