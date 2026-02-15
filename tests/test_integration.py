"""
Integration tests for Picko modules
"""

import pytest

from picko.templates import get_renderer
from picko.vault_io import VaultIO


@pytest.mark.integration
class TestVaultIOIntegration:
    """VaultIO 통합 테스트"""

    def test_write_and_read_note(self, temp_vault_dir):
        """노트 작성 후 읽기"""
        vault = VaultIO(str(temp_vault_dir))

        metadata = {"id": "test_123", "title": "Test Content", "type": "input"}
        content = "# Test Content\n\nThis is test content."
        path = "Inbox/Inputs/test_123.md"

        # 작성
        vault.write_note(path, content, metadata=metadata)

        # 읽기
        read_meta, read_content = vault.read_note(path)

        assert read_meta["id"] == "test_123"
        assert read_meta["title"] == "Test Content"
        assert "# Test Content" in read_content

    def test_list_notes(self, temp_vault_dir):
        """노트 목록 조회"""
        vault = VaultIO(str(temp_vault_dir))

        # 여러 노트 작성
        for i in range(3):
            vault.write_note(f"Inbox/Inputs/test_{i}.md", f"Content {i}", metadata={"id": f"test_{i}"})

        # 목록 조회
        notes = vault.list_notes("Inbox/Inputs")
        assert len(notes) == 3

    def test_update_frontmatter(self, temp_vault_dir):
        """프론트매터 업데이트"""
        vault = VaultIO(str(temp_vault_dir))

        # 노트 작성
        path = "Inbox/Inputs/test.md"
        vault.write_note(path, "Content", metadata={"id": "test", "status": "pending"})

        # 업데이트
        vault.update_frontmatter(path, {"status": "completed"})

        # 확인
        meta, _ = vault.read_note(path)
        assert meta["status"] == "completed"

    def test_ensure_dir(self, temp_vault_dir):
        """디렉토리 자동 생성"""
        vault = VaultIO(str(temp_vault_dir))

        new_dir = temp_vault_dir / "new" / "nested" / "dir"
        vault.ensure_dir("new/nested/dir")

        assert new_dir.exists()
        assert new_dir.is_dir()


@pytest.mark.integration
class TestTemplateIntegration:
    """템플릿 렌더링 통합 테스트"""

    def test_full_input_note_render(self, sample_input_data):
        """전체 Input 노트 렌더링"""
        renderer = get_renderer()
        result = renderer.render_input_note(sample_input_data)

        # 필수 요소 확인
        assert "---" in result
        assert "id: input_test123" in result
        assert "# AI와 머신러닝의 최신 트렌드" in result
        assert "## 요약" in result
        assert "## 핵심 포인트" in result
        assert "- LLM 모델의 성능 향상" in result

    def test_full_digest_render(self, sample_input_data):
        """전체 Digest 렌더링"""
        renderer = get_renderer()
        items = [sample_input_data]
        result = renderer.render_digest("2026-02-15", items)

        assert "# Daily Digest: 2026-02-15" in result
        assert "## [ ] AI와 머신러닝의 최신 트렌드" in result
        assert "input_test123" in result
