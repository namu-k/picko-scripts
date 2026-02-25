"""Tests for layout configuration system."""

import pytest

from picko.layout_config import (
    ColorConfig,
    LayoutConfig,
    LayoutConfigLoader,
    SpacingConfig,
    TypographyConfig,
    get_layout_for_template,
)


class TestTypographyConfig:
    """Tests for TypographyConfig dataclass."""

    def test_default_values(self):
        """Test default typography values."""
        config = TypographyConfig()
        assert config.title_size == 52
        assert config.body_size == 28
        assert config.title_weight == 700
        assert "Noto Sans KR" in config.font_family

    def test_custom_values(self):
        """Test custom typography values."""
        config = TypographyConfig(
            title_size=64,
            body_size=32,
            font_family="Arial",
        )
        assert config.title_size == 64
        assert config.body_size == 32
        assert config.font_family == "Arial"


class TestColorConfig:
    """Tests for ColorConfig dataclass."""

    def test_default_values(self):
        """Test default color values."""
        config = ColorConfig()
        assert config.primary == "#667eea"
        assert config.background == "#0f0f23"
        assert "gradient" in config.gradient.lower()

    def test_custom_values(self):
        """Test custom color values."""
        config = ColorConfig(
            primary="#ff0000",
            background="#ffffff",
        )
        assert config.primary == "#ff0000"
        assert config.background == "#ffffff"


class TestSpacingConfig:
    """Tests for SpacingConfig dataclass."""

    def test_default_values(self):
        """Test default spacing values."""
        config = SpacingConfig()
        assert config.body_padding == 80
        assert config.gap == 24
        assert config.border_radius == 16

    def test_custom_values(self):
        """Test custom spacing values."""
        config = SpacingConfig(
            body_padding=100,
            gap=32,
        )
        assert config.body_padding == 100
        assert config.gap == 32


class TestLayoutConfig:
    """Tests for LayoutConfig dataclass."""

    def test_default_config(self):
        """Test default layout configuration."""
        config = LayoutConfig.default()
        assert config.name == "default"
        assert config.typography.title_size == 52
        assert config.colors.primary == "#667eea"
        assert config.spacing.body_padding == 80

    def test_to_css_vars(self):
        """Test CSS variable generation."""
        config = LayoutConfig.default()
        css_vars = config.to_css_vars()

        assert "--title-size" in css_vars
        assert "--color-primary" in css_vars
        assert "--body-padding" in css_vars
        assert "52px" in css_vars["--title-size"]

    def test_get_template_config(self):
        """Test template-specific config retrieval."""
        config = LayoutConfig(
            name="test",
            template_overrides={
                "quote": {"typography": {"title_size": 60}},
                "card": {"colors": {"primary": "#ff0000"}},
            },
        )

        quote_config = config.get_template_config("quote")
        assert quote_config == {"typography": {"title_size": 60}}

        card_config = config.get_template_config("card")
        assert card_config == {"colors": {"primary": "#ff0000"}}

        unknown_config = config.get_template_config("unknown")
        assert unknown_config == {}


class TestLayoutConfigLoader:
    """Tests for LayoutConfigLoader."""

    def test_load_defaults(self):
        """Test loading default configuration."""
        config = LayoutConfigLoader.load_defaults()
        assert config is not None
        assert config.name == "default"

    def test_load_preset(self):
        """Test loading a preset configuration."""
        config = LayoutConfigLoader.load_preset("minimal_dark")
        assert config.name == "minimal_dark"
        assert config.colors.background == "#0f0f23"

    def test_load_preset_not_found(self):
        """Test loading non-existent preset."""
        with pytest.raises(FileNotFoundError):
            LayoutConfigLoader.load_preset("nonexistent_preset")

    def test_load_theme(self):
        """Test loading a theme configuration."""
        config = LayoutConfigLoader.load_theme("socialbuilders")
        assert config.name == "socialbuilders"
        # Theme should override base preset colors
        assert config.colors.primary == "#3b82f6"

    def test_load_theme_not_found(self):
        """Test loading non-existent theme."""
        with pytest.raises(FileNotFoundError):
            LayoutConfigLoader.load_theme("nonexistent_theme")

    def test_merge_configs(self):
        """Test merging configurations."""
        base = LayoutConfig.default()
        override = {
            "typography": {"title_size": 100},
            "colors": {"primary": "#ff0000"},
        }

        merged = LayoutConfigLoader.merge_configs(base, override)
        assert merged.typography.title_size == 100
        assert merged.colors.primary == "#ff0000"
        # Other values should remain from base
        assert merged.typography.body_size == 28

    def test_apply_overrides(self):
        """Test applying CLI-style overrides."""
        config = LayoutConfig.default()
        overrides = [
            "colors.primary=#ff0000",
            "typography.title_size=80",
        ]

        result = LayoutConfigLoader.apply_overrides(config, overrides)
        assert result.colors.primary == "#ff0000"
        assert result.typography.title_size == 80

    def test_parse_override_value_boolean(self):
        """Test parsing boolean override values."""
        assert LayoutConfigLoader._parse_override_value("true") is True
        assert LayoutConfigLoader._parse_override_value("false") is False

    def test_parse_override_value_number(self):
        """Test parsing numeric override values."""
        assert LayoutConfigLoader._parse_override_value("42") == 42
        assert LayoutConfigLoader._parse_override_value("3.14") == 3.14

    def test_parse_override_value_string(self):
        """Test parsing string override values."""
        assert LayoutConfigLoader._parse_override_value("#ff0000") == "#ff0000"
        assert LayoutConfigLoader._parse_override_value("Arial") == "Arial"

    def test_clear_cache(self):
        """Test cache clearing."""
        LayoutConfigLoader.load_defaults()
        assert "defaults" in LayoutConfigLoader._cache

        LayoutConfigLoader.clear_cache()
        assert "defaults" not in LayoutConfigLoader._cache


class TestGetLayoutForTemplate:
    """Tests for get_layout_for_template convenience function."""

    def test_no_options(self):
        """Test with no options specified."""
        config = get_layout_for_template()
        assert config is not None
        assert config.name == "default"

    def test_with_preset(self):
        """Test with preset specified."""
        config = get_layout_for_template(preset="minimal_dark")
        assert config.name == "minimal_dark"

    def test_with_theme(self):
        """Test with theme specified."""
        config = get_layout_for_template(theme="socialbuilders")
        assert config.name == "socialbuilders"

    def test_with_overrides(self):
        """Test with overrides specified."""
        config = get_layout_for_template(
            preset="minimal_dark",
            overrides=["colors.primary=#ff0000"],
        )
        assert config.colors.primary == "#ff0000"

    def test_with_template_name(self):
        """Test with template name for template-specific overrides."""
        # minimal_dark has template overrides for quote
        config = get_layout_for_template(
            preset="minimal_dark",
            template_name="quote",
        )
        # Quote template should have title_size override
        assert config.typography.title_size == 56
