# tests/test_vault_adapter.py
"""VaultAdapter 필터 파싱 및 Vault 쿼리 테스트"""

import frontmatter  # noqa: F401

from picko.orchestrator.vault_adapter import VaultAdapter
from picko.vault_io import VaultIO  # noqa: F401


class TestParseFilter:
    """필터 문자열 파싱 테스트"""

    def test_equal_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("writing_status=auto_ready")
        assert conditions == [("writing_status", "==", "auto_ready")]

    def test_not_equal_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("writing_status!=completed")
        assert conditions == [("writing_status", "!=", "completed")]

    def test_greater_than_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("score>0.8")
        assert conditions == [("score", ">", "0.8")]

    def test_multiple_filters(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("writing_status=auto_ready,score>0.5")
        assert len(conditions) == 2
        assert conditions[0] == ("writing_status", "==", "auto_ready")
        assert conditions[1] == ("score", ">", "0.5")

    def test_empty_filter(self):
        adapter = VaultAdapter.__new__(VaultAdapter)
        conditions = adapter._parse_filter("")
        assert conditions == []


class TestVaultQuery:
    """VaultAdapter의 count/list/field 테스트"""

    def _write_note(self, vault_dir, rel_path, metadata, content=""):
        """헬퍼: frontmatter가 있는 마크다운 파일 생성"""
        full_path = vault_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        post = frontmatter.Post(content)
        post.metadata = metadata
        full_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return full_path

    def test_count_with_filter(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready", "score": 0.9},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note2.md",
            {"writing_status": "pending", "score": 0.5},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note3.md",
            {"writing_status": "auto_ready", "score": 0.7},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.count("Inbox/Inputs", "writing_status=auto_ready") == 2
        assert adapter.count("Inbox/Inputs", "score>0.8") == 1
        assert adapter.count("Inbox/Inputs", "") == 3

    def test_list_returns_paths(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready"},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note2.md",
            {"writing_status": "pending"},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        result = adapter.list("Inbox/Inputs", "writing_status=auto_ready")
        assert len(result) == 1
        assert result[0].name == "note1.md"

    def test_field_returns_value(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready", "title": "Test Note"},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.field("Inbox/Inputs/note1.md", "writing_status") == "auto_ready"
        assert adapter.field("Inbox/Inputs/note1.md", "title") == "Test Note"
        assert adapter.field("Inbox/Inputs/note1.md", "nonexistent") is None

    def test_count_empty_directory(self, temp_vault_dir):
        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.count("Inbox/Inputs", "writing_status=auto_ready") == 0

    def test_multiple_conditions_and(self, temp_vault_dir):
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note1.md",
            {"writing_status": "auto_ready", "score": 0.9},
        )
        self._write_note(
            temp_vault_dir,
            "Inbox/Inputs/note2.md",
            {"writing_status": "auto_ready", "score": 0.3},
        )

        vault = VaultIO(vault_root=temp_vault_dir)
        adapter = VaultAdapter(vault)

        assert adapter.count("Inbox/Inputs", "writing_status=auto_ready,score>0.5") == 1
