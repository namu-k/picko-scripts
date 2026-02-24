"""Tests for multimedia input/output module."""

from pathlib import Path

import pytest

from picko.multimedia_io import parse_multimedia_input


class TestMultimediaInput:
    """Test multimedia input parsing."""

    def test_parse_standalone_input(self, tmp_path: Path):
        """Parse standalone multimedia input template."""
        input_file = tmp_path / "mm_20260224_001.md"
        input_file.write_text(
            """---
id: mm_20260224_001
account: socialbuilders
source_type: standalone
channels: [linkedin, twitter]
content_types: [image]
created: 2026-02-24
status: draft
---

## 주제/컨셉
창업자를 위한 시간 관리

## 포함할 텍스트
시간은 창업자의 가장 귀한 자산이다
""",
            encoding="utf-8",
        )
        result = parse_multimedia_input(input_file)

        assert result.id == "mm_20260224_001"
        assert result.account == "socialbuilders"
        assert result.source_type == "standalone"
        assert result.channels == ["linkedin", "twitter"]
        assert result.concept == "창업자를 위한 시간 관리"
        assert result.overlay_text == "시간은 창업자의 가장 귀한 자산이다"

    def test_parse_with_refs(self, tmp_path: Path):
        """Parse input with reference documents."""
        input_file = tmp_path / "mm_20260224_002.md"
        input_file.write_text(
            """---
id: mm_20260224_002
account: socialbuilders
source_type: from_longform
longform_ref: "Content/Longform/long_input_xxx.md"
refs:
  - type: reference_style
    id: founder_tech_brief
created: 2026-02-24
---

## 주제/컨셉
PMF 달성 전략
""",
            encoding="utf-8",
        )
        result = parse_multimedia_input(input_file)

        assert result.source_type == "from_longform"
        assert result.longform_ref == "Content/Longform/long_input_xxx.md"
        assert len(result.refs) == 1
        assert result.refs[0]["type"] == "reference_style"

    def test_missing_required_field_raises(self, tmp_path: Path):
        """Missing required fields should raise ValueError."""
        input_file = tmp_path / "mm_invalid.md"
        input_file.write_text(
            """---
id: mm_20260224_003
account: socialbuilders
---
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="주제/컨셉"):
            parse_multimedia_input(input_file)
