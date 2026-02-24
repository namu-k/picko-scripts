"""Multimedia input/output handling."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .logger import get_logger

logger = get_logger("multimedia_io")


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
