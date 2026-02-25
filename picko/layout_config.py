"""
Layout configuration system for image templates.

Provides YAML-based layout presets and themes for customizable image rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TypographyConfig:
    """Typography settings for layout."""

    font_family: str = "'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif"
    title_size: int = 52
    body_size: int = 28
    caption_size: int = 20
    title_weight: int = 700
    body_weight: int = 400
    line_height: float = 1.4


@dataclass
class ColorConfig:
    """Color palette for layout."""

    primary: str = "#667eea"
    secondary: str = "#764ba2"
    background: str = "#0f0f23"
    surface: str = "#1a1a2e"
    text_primary: str = "#ffffff"
    text_secondary: str = "#a0aec0"
    text_muted: str = "#718096"
    accent: str = "#f093fb"
    gradient: str = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    overlay_color: str = "rgba(0, 0, 0, 0.6)"


@dataclass
class SpacingConfig:
    """Spacing values for layout."""

    body_padding: int = 80
    gap: int = 24
    section_gap: int = 40
    element_gap: int = 16
    border_radius: int = 16
    card_padding: int = 32


@dataclass
class LayoutConfig:
    """Complete layout configuration for image templates."""

    name: str = "default"
    typography: TypographyConfig = field(default_factory=TypographyConfig)
    colors: ColorConfig = field(default_factory=ColorConfig)
    spacing: SpacingConfig = field(default_factory=SpacingConfig)
    template_overrides: dict[str, dict] = field(default_factory=dict)

    def to_css_vars(self) -> dict[str, str]:
        """Convert config to CSS variable dictionary."""
        vars_dict = {}

        # Typography
        for key, value in asdict(self.typography).items():
            if key in ("font_family",):
                vars_dict[f"--{key.replace('_', '-')}"] = str(value)
            elif "weight" in key:
                vars_dict[f"--{key.replace('_', '-')}"] = str(value)
            else:
                vars_dict[f"--{key.replace('_', '-')}"] = f"{value}px" if isinstance(value, (int, float)) else str(value)

        # Colors (no units)
        for key, value in asdict(self.colors).items():
            vars_dict[f"--color-{key.replace('_', '-')}"] = str(value)

        # Spacing (with px units)
        for key, value in asdict(self.spacing).items():
            vars_dict[f"--{key.replace('_', '-')}"] = f"{value}px"

        return vars_dict

    @classmethod
    def default(cls) -> LayoutConfig:
        """Create default layout configuration."""
        return cls(name="default")

    def get_template_config(self, template_name: str) -> dict[str, Any]:
        """Get configuration overrides for a specific template."""
        return self.template_overrides.get(template_name, {})


class LayoutConfigLoader:
    """Loader for layout presets and themes."""

    DEFAULTS_PATH = Path("config/layouts/_defaults.yml")
    PRESETS_DIR = Path("config/layouts/presets")
    THEMES_DIR = Path("config/layouts/themes")

    _cache: dict[str, LayoutConfig] = {}

    @classmethod
    def load_preset(cls, name: str) -> LayoutConfig:
        """
        Load a layout preset by name.

        Args:
            name: Preset name (e.g., "minimal_dark", "minimal_light")

        Returns:
            LayoutConfig with preset values merged over defaults
        """
        if name in cls._cache:
            return cls._cache[name]

        # Start with defaults
        defaults = cls.load_defaults()

        # Load preset file
        preset_path = cls.PRESETS_DIR / f"{name}.yml"
        if not preset_path.exists():
            raise FileNotFoundError(f"Layout preset not found: {name}")

        with open(preset_path, encoding="utf-8") as f:
            preset_data = yaml.safe_load(f)

        # Merge preset over defaults
        config = cls._merge_config(asdict(defaults), preset_data)
        config["name"] = name

        result = cls._dict_to_config(config)
        cls._cache[name] = result
        return result

    @classmethod
    def load_theme(cls, name: str, base_preset: str | None = None) -> LayoutConfig:
        """
        Load a theme that extends a preset.

        Args:
            name: Theme name (e.g., "socialbuilders")
            base_preset: Optional preset to extend (theme can specify its own)

        Returns:
            LayoutConfig with theme values merged over preset
        """
        theme_path = cls.THEMES_DIR / f"{name}.yml"
        if not theme_path.exists():
            raise FileNotFoundError(f"Layout theme not found: {name}")

        with open(theme_path, encoding="utf-8") as f:
            theme_data = yaml.safe_load(f)

        # Get base preset
        preset_name = base_preset or theme_data.get("extends", "minimal_dark")
        base_config = cls.load_preset(preset_name)

        # Merge theme over preset
        config = cls._merge_config(asdict(base_config), theme_data)
        config["name"] = name

        result = cls._dict_to_config(config)
        cls._cache[f"theme:{name}"] = result
        return result

    @classmethod
    def load_defaults(cls) -> LayoutConfig:
        """Load default layout configuration."""
        if "defaults" in cls._cache:
            return cls._cache["defaults"]

        if cls.DEFAULTS_PATH.exists():
            with open(cls.DEFAULTS_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            config = cls._dict_to_config(data)
        else:
            config = LayoutConfig.default()

        cls._cache["defaults"] = config
        return config

    @classmethod
    def merge_configs(
        cls,
        base: LayoutConfig,
        override: dict[str, Any],
    ) -> LayoutConfig:
        """
        Merge override values into a base LayoutConfig.

        Args:
            base: Base LayoutConfig
            override: Dictionary with override values

        Returns:
            New LayoutConfig with merged values
        """
        merged = cls._merge_config(asdict(base), override)
        return cls._dict_to_config(merged)

    @classmethod
    def apply_overrides(
        cls,
        config: LayoutConfig,
        overrides: list[str],
    ) -> LayoutConfig:
        """
        Apply CLI-style overrides to a config.

        Args:
            config: Base LayoutConfig
            overrides: List of "key=value" strings (e.g., "colors.primary=#ff0000")

        Returns:
            New LayoutConfig with overrides applied
        """
        override_dict: dict[str, Any] = {}

        for override in overrides:
            if "=" not in override:
                continue

            key, value = override.split("=", 1)
            keys = key.split(".")

            # Navigate to nested dict
            current = override_dict
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            # Try to parse value
            current[keys[-1]] = cls._parse_override_value(value)

        return cls.merge_configs(config, override_dict)

    @staticmethod
    def _parse_override_value(value: str) -> Any:
        """Parse an override value string."""
        # Boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Number
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String (as-is)
        return value

    @classmethod
    def _merge_config(cls, base: dict, override: dict) -> dict:
        """Deep merge override into base dict."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    @classmethod
    def _dict_to_config(cls, data: dict) -> LayoutConfig:
        """Convert dictionary to LayoutConfig dataclass."""
        return LayoutConfig(
            name=data.get("name", "unknown"),
            typography=TypographyConfig(**data.get("typography", {})),
            colors=ColorConfig(**data.get("colors", {})),
            spacing=SpacingConfig(**data.get("spacing", {})),
            template_overrides=data.get("template_overrides", {}),
        )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the config cache."""
        cls._cache.clear()


def get_layout_for_template(
    preset: str | None = None,
    theme: str | None = None,
    template_name: str | None = None,
    overrides: list[str] | None = None,
) -> LayoutConfig:
    """
    Get layout configuration with optional preset, theme, and overrides.

    Args:
        preset: Preset name (e.g., "minimal_dark")
        theme: Theme name (e.g., "socialbuilders")
        template_name: Template name for template-specific overrides
        overrides: CLI-style override strings

    Returns:
        Final merged LayoutConfig
    """
    # Start with defaults or preset
    if theme:
        config = LayoutConfigLoader.load_theme(theme)
    elif preset:
        config = LayoutConfigLoader.load_preset(preset)
    else:
        config = LayoutConfigLoader.load_defaults()

    # Apply overrides
    if overrides:
        config = LayoutConfigLoader.apply_overrides(config, overrides)

    # Apply template-specific overrides
    if template_name:
        template_override = config.get_template_config(template_name)
        if template_override:
            config = LayoutConfigLoader.merge_configs(config, template_override)

    return config
