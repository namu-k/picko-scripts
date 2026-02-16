"""
Unit tests for picko/prompt_loader.py
"""

from unittest.mock import patch

import pytest

from picko.prompt_loader import PromptLoader, get_prompt_loader, load_prompt, render_prompt


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create temporary prompts directory with sample prompts"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create longform prompts
    longform_dir = prompts_dir / "longform"
    longform_dir.mkdir()
    (longform_dir / "default.md").write_text("---\n# Longform Prompt\n\nTitle: {{ title }}\nSummary: {{ summary }}\n")
    (longform_dir / "with_exploration.md").write_text(
        "Title: {{ title }}\nExploration: {{ exploration.topic_expansion | default('') }}\n"
    )
    (longform_dir / "with_reference.md").write_text("Title: {{ title }}\nStyle: {{ style_analysis }}\n")

    # Create pack prompts
    packs_dir = prompts_dir / "packs"
    packs_dir.mkdir()
    (packs_dir / "twitter.md").write_text("Channel: {{ channel }}\nMax: {{ max_length }}\nTitle: {{ title }}\n")
    (packs_dir / "linkedin.md").write_text("LinkedIn: {{ title }}\nTone: {{ tone }}\n")

    # Create image prompts
    image_dir = prompts_dir / "image"
    image_dir.mkdir()
    (image_dir / "default.md").write_text("Image for: {{ title }}\nTags: {% for tag in tags %}{{ tag }} {% endfor %}\n")
    (image_dir / "twitter.md").write_text("Twitter Image: {{ title }}\nSpecs: {{ image_specs.aspect_ratio }}\n")
    (image_dir / "linkedin.md").write_text("LinkedIn Image: {{ title }}\n")
    (image_dir / "newsletter.md").write_text("Newsletter Image: {{ title }}\n")

    # Create exploration prompts
    exploration_dir = prompts_dir / "exploration"
    exploration_dir.mkdir()
    (exploration_dir / "default.md").write_text(
        "Explore: {{ title }}\nKey Points:\n{% for point in key_points %}- {{ point }}\n{% endfor %}\n"
    )

    # Create reference prompts
    reference_dir = prompts_dir / "reference"
    reference_dir.mkdir()
    (reference_dir / "analyze.md").write_text("Analyze style:\n{{ reference_content }}\n")

    return prompts_dir


@pytest.fixture
def temp_accounts_dir(tmp_path):
    """Create temporary accounts directory with override prompts"""
    accounts_dir = tmp_path / "accounts"
    accounts_dir.mkdir()

    # Create account-specific override
    account_prompts = accounts_dir / "test_account" / "prompts" / "longform"
    account_prompts.mkdir(parents=True)
    (account_prompts / "default.md").write_text("Account Override: {{ title }}\n")

    return accounts_dir


@pytest.fixture
def temp_references_dir(tmp_path):
    """Create temporary references directory"""
    references_dir = tmp_path / "references"
    references_dir.mkdir()

    # Create longform references
    longform_ref = references_dir / "longform"
    longform_ref.mkdir()
    (longform_ref / "sample-001.md").write_text("# Sample Longform\n\nContent here...")

    # Create packs references
    twitter_ref = references_dir / "packs" / "twitter"
    twitter_ref.mkdir(parents=True)
    (twitter_ref / "sample-001.md").write_text("Sample tweet content")

    return references_dir


@pytest.fixture
def sample_input_content():
    """Sample input content for prompts"""
    return {
        "title": "AI Trends 2026",
        "summary": "Latest developments in AI",
        "key_points": ["LLMs", "Multimodal", "Efficiency"],
        "excerpt": "AI is evolving rapidly...",
        "tags": ["AI", "ML", "Tech"],
    }


class TestPromptLoaderInit:
    """Test PromptLoader initialization"""

    def test_init_default_prompts_dir(self, temp_prompts_dir):
        """Test initialization with default prompts directory"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert loader.prompts_dir == temp_prompts_dir
        assert loader.account_overrides_dir is None

    def test_init_with_account_overrides(self, temp_prompts_dir, temp_accounts_dir):
        """Test initialization with account overrides directory"""
        loader = PromptLoader(
            prompts_dir=temp_prompts_dir,
            account_overrides_dir=temp_accounts_dir,
        )
        assert loader.prompts_dir == temp_prompts_dir
        assert loader.account_overrides_dir == temp_accounts_dir

    def test_init_with_string_path(self, temp_prompts_dir):
        """Test initialization with string path instead of Path"""
        loader = PromptLoader(prompts_dir=str(temp_prompts_dir))
        assert loader.prompts_dir == temp_prompts_dir


class TestPromptLoaderLoad:
    """Test PromptLoader.load method"""

    def test_load_default_longform(self, temp_prompts_dir):
        """Test loading default longform prompt"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        content = loader.load("longform", "default")
        assert "Title: {{ title }}" in content
        assert "Summary: {{ summary }}" in content

    def test_load_pack_prompt(self, temp_prompts_dir):
        """Test loading pack prompts"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        twitter = loader.load("packs", "twitter")
        assert "Channel: {{ channel }}" in twitter

        linkedin = loader.load("packs", "linkedin")
        assert "LinkedIn: {{ title }}" in linkedin

    def test_load_nonexistent_prompt_raises(self, temp_prompts_dir):
        """Test loading nonexistent prompt raises FileNotFoundError"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        with pytest.raises(FileNotFoundError, match="Prompt not found"):
            loader.load("longform", "nonexistent")

    def test_load_with_account_override(self, temp_prompts_dir, temp_accounts_dir):
        """Test loading prompt with account-specific override"""
        loader = PromptLoader(
            prompts_dir=temp_prompts_dir,
            account_overrides_dir=temp_accounts_dir,
        )

        # Without account - uses default
        default = loader.load("longform", "default")
        assert "Longform Prompt" in default

        # With account - uses override
        override = loader.load("longform", "default", account_id="test_account")
        assert "Account Override" in override

    def test_load_with_nonexistent_account_uses_default(self, temp_prompts_dir, temp_accounts_dir):
        """Test loading with nonexistent account falls back to default"""
        loader = PromptLoader(
            prompts_dir=temp_prompts_dir,
            account_overrides_dir=temp_accounts_dir,
        )

        content = loader.load("longform", "default", account_id="nonexistent_account")
        assert "Longform Prompt" in content


class TestPromptLoaderRender:
    """Test PromptLoader.render method"""

    def test_render_with_variables(self, temp_prompts_dir, sample_input_content):
        """Test rendering prompt with template variables"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.render(
            "longform",
            "default",
            title=sample_input_content["title"],
            summary=sample_input_content["summary"],
        )

        assert "AI Trends 2026" in result
        assert "Latest developments in AI" in result
        assert "{{ title }}" not in result  # Variables should be replaced

    def test_render_with_list_variables(self, temp_prompts_dir, sample_input_content):
        """Test rendering prompt with list variables"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.render(
            "exploration",
            "default",
            title=sample_input_content["title"],
            key_points=sample_input_content["key_points"],
        )

        assert "LLMs" in result
        assert "Multimodal" in result
        assert "Efficiency" in result

    def test_render_template_string(self, temp_prompts_dir):
        """Test rendering template string directly"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.render_template("Hello {{ name }}!", name="World")
        assert result == "Hello World!"


class TestPromptLoaderConvenienceMethods:
    """Test convenience methods for specific prompt types"""

    def test_get_longform_prompt(self, temp_prompts_dir, sample_input_content):
        """Test get_longform_prompt method"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.get_longform_prompt(sample_input_content)
        assert "AI Trends 2026" in result
        assert "Latest developments in AI" in result

    def test_get_longform_prompt_with_exploration(self, temp_prompts_dir, sample_input_content):
        """Test get_longform_prompt with exploration data"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        exploration = {"topic_expansion": "Extended topic analysis"}
        result = loader.get_longform_prompt(sample_input_content, exploration=exploration)

        # Should use with_exploration template
        assert "Extended topic analysis" in result

    def test_get_pack_prompt_twitter(self, temp_prompts_dir, sample_input_content):
        """Test get_pack_prompt for Twitter"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        channel_config = {"max_length": 280, "tone": "casual", "hashtags": True}
        result = loader.get_pack_prompt(
            "twitter",
            sample_input_content,
            channel_config=channel_config,
        )

        assert "twitter" in result.lower() or "280" in result
        assert "AI Trends 2026" in result

    def test_get_pack_prompt_linkedin(self, temp_prompts_dir, sample_input_content):
        """Test get_pack_prompt for LinkedIn"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        channel_config = {"max_length": 3000, "tone": "professional"}
        result = loader.get_pack_prompt(
            "linkedin",
            sample_input_content,
            channel_config=channel_config,
        )

        assert "professional" in result or "LinkedIn" in result

    def test_get_image_prompt(self, temp_prompts_dir, sample_input_content):
        """Test get_image_prompt method"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.get_image_prompt(sample_input_content)
        assert "AI Trends 2026" in result
        assert "AI" in result
        assert "ML" in result

    def test_get_channel_image_prompt(self, temp_prompts_dir, sample_input_content):
        """Test get_channel_image_prompt method"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        image_specs = {
            "aspect_ratio": "1:1",
            "style": "minimal",
            "layout_hints": ["centered", "clean"],
        }
        result = loader.get_channel_image_prompt(
            "twitter",
            sample_input_content,
            image_specs=image_specs,
        )

        assert "AI Trends 2026" in result

    def test_get_channel_image_prompt_defaults(self, temp_prompts_dir, sample_input_content):
        """Test get_channel_image_prompt with default specs"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        # Should not raise with None image_specs
        result = loader.get_channel_image_prompt("twitter", sample_input_content)
        assert "AI Trends 2026" in result

    def test_get_exploration_prompt(self, temp_prompts_dir, sample_input_content):
        """Test get_exploration_prompt method"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.get_exploration_prompt(sample_input_content)
        assert "AI Trends 2026" in result
        assert "LLMs" in result


class TestPromptLoaderListPrompts:
    """Test PromptLoader.list_prompts method"""

    def test_list_longform_prompts(self, temp_prompts_dir):
        """Test listing longform prompts"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        prompts = loader.list_prompts("longform")
        assert "default" in prompts
        assert "with_exploration" in prompts

    def test_list_pack_prompts(self, temp_prompts_dir):
        """Test listing pack prompts"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        prompts = loader.list_prompts("packs")
        assert "twitter" in prompts
        assert "linkedin" in prompts

    def test_list_nonexistent_type_returns_empty(self, temp_prompts_dir):
        """Test listing nonexistent prompt type returns empty list"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        prompts = loader.list_prompts("nonexistent")
        assert prompts == []


class TestPromptLoaderReferences:
    """Test reference-related methods"""

    def test_load_reference_by_name(self, temp_prompts_dir, temp_references_dir):
        """Test loading reference by name"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.load_reference(temp_references_dir, "longform", "sample-001")
        assert result is not None
        assert "Sample Longform" in result

    def test_load_reference_first_sample(self, temp_prompts_dir, temp_references_dir):
        """Test loading first sample when name not specified"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.load_reference(temp_references_dir, "longform")
        assert result is not None
        assert "Sample Longform" in result

    def test_load_reference_nonexistent_name(self, temp_prompts_dir, temp_references_dir):
        """Test loading nonexistent reference returns None"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.load_reference(temp_references_dir, "longform", "nonexistent")
        assert result is None

    def test_load_reference_nonexistent_category(self, temp_prompts_dir, temp_references_dir):
        """Test loading from nonexistent category returns None"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.load_reference(temp_references_dir, "nonexistent")
        assert result is None

    def test_get_reference_style_analysis(self, temp_prompts_dir):
        """Test get_reference_style_analysis method"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.get_reference_style_analysis("Sample reference content")
        assert "Sample reference content" in result

    def test_get_longform_with_reference_prompt(self, temp_prompts_dir, sample_input_content):
        """Test get_longform_with_reference_prompt method"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.get_longform_with_reference_prompt(
            sample_input_content,
            style_analysis="Style: formal, concise",
        )
        assert "AI Trends 2026" in result


class TestPromptLoaderSingleton:
    """Test singleton functions"""

    def test_get_prompt_loader_returns_instance(self):
        """Test get_prompt_loader returns PromptLoader instance"""
        loader = get_prompt_loader()
        assert isinstance(loader, PromptLoader)

    def test_get_prompt_loader_singleton(self):
        """Test get_prompt_loader returns same instance"""
        import picko.prompt_loader as module

        module._default_loader = None  # Reset singleton

        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        assert loader1 is loader2

    def test_load_prompt_convenience_function(self):
        """Test load_prompt convenience function"""
        import picko.prompt_loader as module

        module._default_loader = None  # Reset singleton

        with patch.object(module.get_prompt_loader(), "load") as mock_load:
            mock_load.return_value = "prompt content"
            result = load_prompt("longform", "default")
            mock_load.assert_called_once_with("longform", "default", None)
            assert result == "prompt content"

    def test_render_prompt_convenience_function(self):
        """Test render_prompt convenience function"""
        import picko.prompt_loader as module

        module._default_loader = None  # Reset singleton

        with patch.object(module.get_prompt_loader(), "render") as mock_render:
            mock_render.return_value = "rendered content"
            result = render_prompt("longform", "default", title="Test")
            mock_render.assert_called_once_with("longform", "default", None, title="Test")
            assert result == "rendered content"


class TestPromptLoaderEdgeCases:
    """Test edge cases and error handling"""

    def test_render_with_missing_variable(self, temp_prompts_dir):
        """Test rendering with missing variable (Jinja2 leaves as empty)"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        # Missing variables should not raise, just render empty
        result = loader.render("longform", "default")
        # The template has {{ title }} and {{ summary }} which should be empty strings
        assert isinstance(result, str)

    def test_render_with_none_values(self, temp_prompts_dir):
        """Test rendering with None values"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.render(
            "longform",
            "default",
            title=None,
            summary=None,
        )
        assert isinstance(result, str)

    def test_render_with_special_characters(self, temp_prompts_dir):
        """Test rendering with special characters in variables"""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)

        result = loader.render(
            "longform",
            "default",
            title='Title with <special> & "quotes"',
            summary="Summary with\nnewlines\nand\ttabs",
        )
        assert "Title with" in result
