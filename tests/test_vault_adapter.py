# tests/test_vault_adapter.py
"""VaultAdapter 필터 파싱 및 Vault 쿼리 테스트"""

from picko.orchestrator.vault_adapter import VaultAdapter


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
