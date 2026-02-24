"""Multimedia input/output handling."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .logger import get_logger

logger = get_logger("multimedia_io")

# Project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent

# Reference type to path mapping
REFERENCE_PATHS = {
    "longform": "Content/Longform/{id}.md",
    "reference_style": "Assets/References/{id}.md",
    "exploration": "Inbox/Explorations/{id}.md",
    "image_style": "mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0. 프레임워크/이미지 스타일 프리셋 라이브러리.md",
}


@dataclass
class MultimediaInput:
    """Multimedia input template data."""

    id: str
    account: str
    source_type: str  # standalone | from_longform
    channels: list[str]
    content_types: list[str]
    concept: str
    created: str
    status: str = "draft"
    longform_ref: str = ""
    overlay_text: str = ""
    refs: list[dict[str, str]] = field(default_factory=list)
    notes: str = ""


def parse_multimedia_input(file_path: Path) -> MultimediaInput:
    """Parse multimedia input template file."""
    content = file_path.read_text(encoding="utf-8")

    # Parse frontmatter
    if not content.startswith("---"):
        raise ValueError(f"No frontmatter found in {file_path}")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter format in {file_path}")

    meta = yaml.safe_load(parts[1])
    body = parts[2].strip()

    # Extract body sections
    sections = _parse_body_sections(body)

    # Validate required fields
    if "주제/컨셉" not in sections:
        raise ValueError("필수 필드 누락: 주제/컨셉")

    return MultimediaInput(
        id=meta.get("id", ""),
        account=meta.get("account", ""),
        source_type=meta.get("source_type", "standalone"),
        channels=meta.get("channels", []),
        content_types=meta.get("content_types", ["image"]),
        concept=sections.get("주제/컨셉", ""),
        created=meta.get("created", ""),
        status=meta.get("status", "draft"),
        longform_ref=meta.get("longform_ref", ""),
        overlay_text=sections.get("포함할 텍스트", ""),
        refs=meta.get("refs", []),
        notes=sections.get("비고", ""),
    )


def _parse_body_sections(body: str) -> dict[str, str]:
    """Parse markdown body into sections."""
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_content: list[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_header:
                sections[current_header] = "\n".join(current_content).strip()
            current_header = line[3:].strip()
            current_content = []
        elif current_header:
            current_content.append(line)

    if current_header:
        sections[current_header] = "\n".join(current_content).strip()

    return sections


def load_account_config(account_id: str) -> dict[str, Any]:
    """Load account configuration by account_id.

    Args:
        account_id: The account identifier (e.g., 'socialbuilders')

    Returns:
        Account configuration dictionary, or minimal dict with account_id if not found.
    """
    config_path = PROJECT_ROOT / "config" / "accounts" / f"{account_id}.yml"

    if not config_path.exists():
        logger.warning(f"Account config not found: {config_path}")
        return {"account_id": account_id}

    with open(config_path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f) or {}
        return config


def load_reference(ref_type: str, ref_id: str) -> str:
    """Load reference document by type and ID.

    Args:
        ref_type: Type of reference (e.g., 'reference_style', 'exploration', 'longform')
        ref_id: Identifier for the reference document

    Returns:
        Content of the reference document, or empty string if not found.

    Raises:
        ValueError: If ref_type is unknown.
    """
    if ref_type not in REFERENCE_PATHS:
        raise ValueError(f"Unknown reference type: {ref_type}")

    path_pattern = REFERENCE_PATHS[ref_type]
    ref_path = PROJECT_ROOT / path_pattern.format(id=ref_id)

    if not ref_path.exists():
        logger.warning(f"Reference not found: {ref_path}")
        return ""

    return ref_path.read_text(encoding="utf-8")


def resolve_all_refs(input_data: MultimediaInput) -> list[str]:
    """Resolve all references from input data.

    Args:
        input_data: MultimediaInput containing refs to resolve

    Returns:
        List of resolved reference contents (empty strings excluded).
    """
    resolved = []

    for ref in input_data.refs:
        ref_type = ref.get("type")
        ref_id = ref.get("id")
        if ref_type and ref_id:
            content = load_reference(ref_type, ref_id)
            if content:
                resolved.append(content)

    return resolved
