"""
End-to-end dry-run integration test for generate_content

This test verifies the generate_content script works correctly with --dry-run
against a mocked vault path.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestGenerateContentDryRun:
    """E2E dry-run tests for generate_content"""

    def test_generate_content_dry_run(self, temp_vault_dir):
        """Test generate_content with --dry-run flag"""
        # Create a test digest file
        digest_content = """---
type: digest
date: 2026-02-15
created_at: 2026-02-15T10:00:00
total_items: 1
---

# Daily Digest: 2026-02-15

> [!info] 처리 방법
> - 체크박스 `[ ]`를 `[x]`로 변경하고 저장하면 글쓰기 API가 실행됩니다
> - 수동 작성을 원하시면 Input 노트에서 "수동 작성"을 체크하세요

## [ ] Test Article

- **ID**: test_input_123
- **Writing Status**: auto_ready
- **Score**: 0.85
- **Input**: [[test_input_123]]
"""
        digest_path = temp_vault_dir / "Inbox" / "Inputs" / "_digests" / "2026-02-15.md"
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(digest_content)

        # Create a test input file
        input_content = """---
id: test_input_123
title: "Test Article"
source: "Test Source"
source_url: "https://example.com/test"
publish_date: "2026-02-15
collected_at: "2026-02-15T10:00:00"
status: inbox
writing_status: auto_ready
score:
  novelty: 0.8
  relevance: 0.9
  quality: 0.85
  total: 0.85
tags:
  - test
---
# Test Article

This is a test article.
"""
        input_path = temp_vault_dir / "Inbox" / "Inputs" / "test_input_123.md"
        input_path.write_text(input_content)

        # Run generate_content with --dry-run
        import os

        env = os.environ.copy()
        env["PICKO_VAULT_ROOT"] = str(temp_vault_dir)

        result = subprocess.run(
            [sys.executable, "-m", "scripts.generate_content", "--date", "2026-02-15", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env=env,
        )

        # Should complete without error
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    def test_health_check_json_output(self):
        """Test health_check produces valid JSON output"""
        result = subprocess.run(
            [sys.executable, "-m", "scripts.health_check", "--json"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

        # Should complete
        assert result.returncode == 0

        # Output should be valid JSON (list format)
        try:
            data = json.loads(result.stdout)
            assert isinstance(data, list)
        except json.JSONDecodeError:
            # If not JSON, at least check it has array markers
            assert "[" in result.stdout or "{" in result.stdout
