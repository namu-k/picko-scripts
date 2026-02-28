"""
Tests for DuplicateChecker - 임베딩 기반 중복 콘텐츠 탐지
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from scripts.duplicate_checker import CheckResult, DuplicateChecker, DuplicateMatch, print_result

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_vault():
    """Mock VaultIO"""
    vault = MagicMock()
    return vault


@pytest.fixture
def mock_embedding_manager():
    """Mock EmbeddingManager"""
    manager = MagicMock()
    # Default: return unit vector
    manager.embed.return_value = [1.0, 0.0, 0.0]
    manager.cosine_similarity.return_value = 0.5
    return manager


@pytest.fixture
def mock_config():
    """Mock Config"""
    config = MagicMock()
    return config


@pytest.fixture
def sample_note_meta():
    """샘플 노트 메타데이터"""
    return {
        "id": "test_content_001",
        "title": "AI Trends 2026",
        "source": "TechCrunch",
        "publish_date": "2026-02-27",
    }


@pytest.fixture
def sample_note_content():
    """샘플 노트 내용"""
    return """# AI Trends 2026

## 요약
AI 기술이 빠르게 발전하고 있습니다. 특히 LLM 모델의 성능이 크게 향상되었습니다.

## 핵심 포인트
- LLM 모델의 성능 향상
- 멀티모달 AI의 등장
- 에너지 효율성 개선
"""


@pytest.fixture
def checker_with_mocks(mock_vault, mock_embedding_manager, mock_config):
    """Mock이 주입된 DuplicateChecker"""
    with (
        patch("scripts.duplicate_checker.VaultIO", return_value=mock_vault),
        patch(
            "scripts.duplicate_checker.get_embedding_manager",
            return_value=mock_embedding_manager,
        ),
        patch("scripts.duplicate_checker.get_config", return_value=mock_config),
    ):
        checker = DuplicateChecker(threshold=0.85)
        yield checker


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestDuplicateMatch:
    """DuplicateMatch 데이터클래스 테스트"""

    def test_duplicate_match_creation(self):
        """DuplicateMatch 생성 테스트"""
        match = DuplicateMatch(
            content_id="test_001",
            content_path="/path/to/content.md",
            similarity=0.95,
            title="Test Title",
            source="TechCrunch",
        )

        assert match.content_id == "test_001"
        assert match.content_path == "/path/to/content.md"
        assert match.similarity == 0.95
        assert match.title == "Test Title"
        assert match.source == "TechCrunch"

    def test_duplicate_match_defaults(self):
        """DuplicateMatch 기본값 테스트"""
        match = DuplicateMatch(content_id="test", content_path="/path", similarity=0.5, title="", source="")

        assert match.title == ""
        assert match.source == ""


class TestCheckResult:
    """CheckResult 데이터클래스 테스트"""

    def test_check_result_with_duplicates(self):
        """중복이 있는 결과 테스트"""
        dup = DuplicateMatch(
            content_id="dup_001",
            content_path="/path/dup.md",
            similarity=0.95,
            title="Duplicate",
            source="Source",
        )

        result = CheckResult(
            content_id="test_001",
            has_duplicates=True,
            duplicates=[dup],
            max_similarity=0.95,
            checked_at="2026-02-27T12:00:00",
        )

        assert result.has_duplicates is True
        assert len(result.duplicates) == 1
        assert result.max_similarity == 0.95
        assert result.duplicates[0].content_id == "dup_001"

    def test_check_result_no_duplicates(self):
        """중복이 없는 결과 테스트"""
        result = CheckResult(
            content_id="unique_001",
            has_duplicates=False,
            duplicates=[],
            max_similarity=0.0,
            checked_at="2026-02-27T12:00:00",
        )

        assert result.has_duplicates is False
        assert len(result.duplicates) == 0
        assert result.max_similarity == 0.0


# ============================================================================
# DuplicateChecker Initialization Tests
# ============================================================================


class TestDuplicateCheckerInit:
    """DuplicateChecker 초기화 테스트"""

    def test_init_with_default_threshold(self, mock_vault, mock_embedding_manager, mock_config, temp_vault_dir):
        """기본 임계값으로 초기화"""
        with (
            patch("scripts.duplicate_checker.VaultIO", return_value=mock_vault),
            patch(
                "scripts.duplicate_checker.get_embedding_manager",
                return_value=mock_embedding_manager,
            ),
            patch("scripts.duplicate_checker.get_config", return_value=mock_config),
        ):
            checker = DuplicateChecker()

            assert checker.threshold == DuplicateChecker.DEFAULT_THRESHOLD
            assert checker._cache == {}

    def test_init_with_custom_threshold(self, mock_vault, mock_embedding_manager, mock_config, temp_vault_dir):
        """커스텀 임계값으로 초기화"""
        with (
            patch("scripts.duplicate_checker.VaultIO", return_value=mock_vault),
            patch(
                "scripts.duplicate_checker.get_embedding_manager",
                return_value=mock_embedding_manager,
            ),
            patch("scripts.duplicate_checker.get_config", return_value=mock_config),
        ):
            checker = DuplicateChecker(threshold=0.9)

            assert checker.threshold == 0.9


# ============================================================================
# _extract_text Tests
# ============================================================================


class TestExtractText:
    """_extract_text 메서드 테스트"""

    def test_extract_text_with_all_sections(self, checker_with_mocks):
        """모든 섹션이 있는 경우 텍스트 추출"""
        meta = {"title": "Test Title"}
        content = """# Test

## 요약
This is a summary.

## 핵심 포인트
- Point 1
- Point 2
"""

        text = checker_with_mocks._extract_text(meta, content)

        assert "Test Title" in text
        assert "This is a summary" in text
        assert "Point 1" in text

    def test_extract_text_with_title_only(self, checker_with_mocks):
        """제목만 있는 경우"""
        meta = {"title": "Title Only"}
        content = "No sections here"

        text = checker_with_mocks._extract_text(meta, content)

        assert "Title Only" in text

    def test_extract_text_with_summary_only(self, checker_with_mocks):
        """요약 섹션만 있는 경우"""
        meta: Dict[str, Any] = {}
        content = """## 요약
Summary content here.
"""

        text = checker_with_mocks._extract_text(meta, content)

        assert "Summary content here" in text

    def test_extract_text_empty_meta_and_content(self, checker_with_mocks):
        """빈 메타데이터와 내용"""
        meta: Dict[str, Any] = {}
        content = ""

        text = checker_with_mocks._extract_text(meta, content)

        # Should return empty or minimal string
        assert isinstance(text, str)


# ============================================================================
# check_content Tests
# ============================================================================


class TestCheckContent:
    """check_content 메서드 테스트"""

    def test_check_content_no_duplicates(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """중복이 없는 콘텐츠 검사"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_vault.list_notes.return_value = []  # 비교 대상 없음
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]

        result = checker_with_mocks.check_content("/path/to/content.md")

        assert result.content_id == "test_content_001"
        assert result.has_duplicates is False
        assert len(result.duplicates) == 0
        assert result.max_similarity == 0.0

    def test_check_content_with_duplicates(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """중복이 있는 콘텐츠 검사"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_vault.list_notes.return_value = [Path("/path/to/other.md")]
        mock_vault.read_frontmatter.return_value = {
            "id": "dup_001",
            "title": "Similar Content",
            "source": "TechCrunch",
        }

        # 첫 번째 호출: 타겟 콘텐츠, 두 번째 호출: 비교 대상
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]
        mock_embedding_manager.cosine_similarity.return_value = 0.95  # 높은 유사도

        # _get_embedding 캐시 설정
        checker_with_mocks._cache["/path/to/other.md"] = [0.95, 0.1, 0.05]

        result = checker_with_mocks.check_content("/path/to/content.md", compare_paths=["/path/to/other.md"])

        assert result.has_duplicates is True
        assert len(result.duplicates) == 1
        assert result.duplicates[0].similarity >= checker_with_mocks.threshold

    def test_check_content_with_custom_compare_paths(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """커스텀 비교 경로 지정"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]
        mock_embedding_manager.cosine_similarity.return_value = 0.5  # 낮은 유사도

        custom_paths = ["/custom/path1.md", "/custom/path2.md"]
        checker_with_mocks._cache["/custom/path1.md"] = [0.5, 0.5, 0.0]
        checker_with_mocks._cache["/custom/path2.md"] = [0.3, 0.3, 0.3]

        result = checker_with_mocks.check_content("/path/to/content.md", compare_paths=custom_paths)

        # _get_comparison_targets가 호출되지 않아야 함
        assert isinstance(result, CheckResult)

    def test_check_content_handles_exception(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """예외 발생 시 안전하게 처리"""
        mock_vault.read_note.side_effect = FileNotFoundError("File not found")

        result = checker_with_mocks.check_content("/nonexistent/path.md")

        assert result.has_duplicates is False
        assert len(result.duplicates) == 0
        assert result.max_similarity == 0.0


# ============================================================================
# check_pair Tests
# ============================================================================


class TestCheckPair:
    """check_pair 메서드 테스트"""

    def test_check_pair_returns_similarity(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """두 콘텐츠 간 유사도 반환"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]
        mock_embedding_manager.cosine_similarity.return_value = 0.75

        similarity = checker_with_mocks.check_pair("/path1.md", "/path2.md")

        assert similarity == 0.75
        mock_embedding_manager.cosine_similarity.assert_called_once()

    def test_check_pair_with_identical_content(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """동일한 콘텐츠 간 비교 (유사도 1.0)"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]
        mock_embedding_manager.cosine_similarity.return_value = 1.0

        similarity = checker_with_mocks.check_pair("/path1.md", "/path2.md")

        assert similarity == 1.0

    def test_check_pair_with_embedding_failure(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """임베딩 생성 실패 시 0.0 반환"""
        mock_vault.read_note.side_effect = Exception("Embedding failed")

        similarity = checker_with_mocks.check_pair("/path1.md", "/path2.md")

        assert similarity == 0.0

    def test_check_pair_uses_cache(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
    ):
        """캐시 활용 테스트"""
        # 캐시에 임베딩 미리 저장
        checker_with_mocks._cache["/path1.md"] = [1.0, 0.0, 0.0]
        checker_with_mocks._cache["/path2.md"] = [0.0, 1.0, 0.0]
        mock_embedding_manager.cosine_similarity.return_value = 0.5

        similarity = checker_with_mocks.check_pair("/path1.md", "/path2.md")

        # read_note가 호출되지 않아야 함 (캐시 사용)
        mock_vault.read_note.assert_not_called()
        assert similarity == 0.5


# ============================================================================
# _find_duplicates Tests
# ============================================================================


class TestFindDuplicates:
    """_find_duplicates 메서드 테스트"""

    def test_find_duplicates_below_threshold(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
    ):
        """임계값 미만 유사도 - 중복 없음"""
        mock_embedding_manager.cosine_similarity.return_value = 0.5  # 임계값 0.85 미만

        duplicates = checker_with_mocks._find_duplicates(
            content_id="test_001",
            embedding=[1.0, 0.0, 0.0],
            compare_paths=["/path1.md"],
        )

        assert len(duplicates) == 0

    def test_find_duplicates_above_threshold(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
    ):
        """임계값 이상 유사도 - 중복 있음"""
        mock_vault.read_frontmatter.return_value = {
            "id": "dup_001",
            "title": "Duplicate Content",
            "source": "TechCrunch",
        }
        mock_embedding_manager.cosine_similarity.return_value = 0.95

        # 캐시 설정
        checker_with_mocks._cache["/path1.md"] = [0.95, 0.1, 0.05]

        duplicates = checker_with_mocks._find_duplicates(
            content_id="test_001",
            embedding=[1.0, 0.0, 0.0],
            compare_paths=["/path1.md"],
        )

        assert len(duplicates) == 1
        assert duplicates[0].content_id == "dup_001"
        assert duplicates[0].similarity == 0.95

    def test_find_duplicates_sorted_by_similarity(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
    ):
        """유사도 내림차순 정렬"""
        mock_vault.read_frontmatter.side_effect = [
            {"id": "dup_001", "title": "First", "source": "A"},
            {"id": "dup_002", "title": "Second", "source": "B"},
            {"id": "dup_003", "title": "Third", "source": "C"},
        ]

        # 다양한 유사도
        mock_embedding_manager.cosine_similarity.side_effect = [0.90, 0.95, 0.88]

        # 캐시 설정
        for path in ["/path1.md", "/path2.md", "/path3.md"]:
            checker_with_mocks._cache[path] = [0.5, 0.5, 0.0]

        duplicates = checker_with_mocks._find_duplicates(
            content_id="test_001",
            embedding=[1.0, 0.0, 0.0],
            compare_paths=["/path1.md", "/path2.md", "/path3.md"],
        )

        assert len(duplicates) == 3
        # 내림차순 정렬 확인
        assert duplicates[0].similarity >= duplicates[1].similarity
        assert duplicates[1].similarity >= duplicates[2].similarity

    def test_find_duplicates_handles_embedding_failure(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """임베딩 실패 시 해당 경로 스킵"""
        # _get_embedding이 None 반환하도록 설정
        checker_with_mocks._get_embedding = lambda path: None

        duplicates = checker_with_mocks._find_duplicates(
            content_id="test_001",
            embedding=[1.0, 0.0, 0.0],
            compare_paths=["/path1.md", "/path2.md"],
        )

        assert len(duplicates) == 0


# ============================================================================
# check_directory Tests
# ============================================================================


class TestCheckDirectory:
    """check_directory 메서드 테스트"""

    def test_check_directory_empty(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """빈 디렉토리 검사"""
        mock_vault.list_notes.return_value = []

        results = checker_with_mocks.check_directory("/empty/dir")

        assert len(results) == 0

    def test_check_directory_multiple_files(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """여러 파일 디렉토리 검사"""
        mock_vault.list_notes.return_value = [
            Path("/dir/file1.md"),
            Path("/dir/file2.md"),
        ]
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]
        mock_embedding_manager.cosine_similarity.return_value = 0.5

        results = checker_with_mocks.check_directory("/dir")

        assert len(results) == 2

    def test_check_directory_recursive_flag(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """recursive 플래그 전달"""
        mock_vault.list_notes.return_value = []

        checker_with_mocks.check_directory("/dir", recursive=True)

        mock_vault.list_notes.assert_called_with("/dir", recursive=True)


# ============================================================================
# _get_comparison_targets Tests
# ============================================================================


class TestGetComparisonTargets:
    """_get_comparison_targets 메서드 테스트"""

    def test_get_targets_excludes_self(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """자기 자신은 제외"""
        # _get_comparison_targets calls list_notes twice:
        # 1. Inbox/Inputs -> returns content1, content2
        # 2. Content/Longform -> returns empty list
        mock_vault.list_notes.side_effect = [
            [
                Path("/vault/Inbox/Inputs/content1.md"),
                Path("/vault/Inbox/Inputs/content2.md"),
            ],
            [],  # No longform notes
        ]

        targets = checker_with_mocks._get_comparison_targets(str(Path("/vault/Inbox/Inputs/content1.md")))

        # Windows path normalization
        targets_normalized = [str(Path(t)) for t in targets]
        assert str(Path("/vault/Inbox/Inputs/content1.md")) not in targets_normalized
        assert str(Path("/vault/Inbox/Inputs/content2.md")) in targets_normalized

    def test_get_targets_includes_longform(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """Longform 콘텐츠도 포함"""
        mock_vault.list_notes.side_effect = [
            [Path("/vault/Inbox/Inputs/input1.md")],  # Inbox/Inputs
            [Path("/vault/Content/Longform/long1.md")],  # Content/Longform
        ]

        targets = checker_with_mocks._get_comparison_targets("/vault/test.md")

        assert any("Longform" in t for t in targets)


# ============================================================================
# _get_embedding Tests
# ============================================================================


class TestGetEmbedding:
    """_get_embedding 메서드 테스트"""

    def test_get_embedding_uses_cache(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """캐시된 임베딩 사용"""
        cached_embedding = [0.5, 0.5, 0.5]
        checker_with_mocks._cache["/cached/path.md"] = cached_embedding

        result = checker_with_mocks._get_embedding("/cached/path.md")

        assert result == cached_embedding
        # read_note가 호출되지 않아야 함
        mock_vault.read_note.assert_not_called()

    def test_get_embedding_creates_and_caches(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """새 임베딩 생성 후 캐시"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        expected_embedding = [0.7, 0.8, 0.9]
        mock_embedding_manager.embed.return_value = expected_embedding

        result = checker_with_mocks._get_embedding("/new/path.md")

        assert result == expected_embedding
        assert checker_with_mocks._cache["/new/path.md"] == expected_embedding

    def test_get_embedding_handles_error(
        self,
        checker_with_mocks,
        mock_vault,
    ):
        """에러 발생 시 None 반환"""
        mock_vault.read_note.side_effect = Exception("Read error")

        result = checker_with_mocks._get_embedding("/error/path.md")

        assert result is None


# ============================================================================
# _preload_embeddings Tests
# ============================================================================


class TestPreloadEmbeddings:
    """_preload_embeddings 메서드 테스트"""

    def test_preload_populates_cache(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """캐시 미리 로드"""
        mock_vault.list_notes.return_value = [
            Path("/dir/file1.md"),
            Path("/dir/file2.md"),
        ]
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_embedding_manager.embed.return_value = [0.5, 0.5, 0.5]

        checker_with_mocks._preload_embeddings("/dir", recursive=False)

        # Windows path normalization - use Path objects for comparison
        cache_keys_normalized = {str(Path(k)) for k in checker_with_mocks._cache.keys()}
        assert len(checker_with_mocks._cache) == 2
        assert str(Path("/dir/file1.md")) in cache_keys_normalized
        assert str(Path("/dir/file2.md")) in cache_keys_normalized


# ============================================================================
# print_result Tests
# ============================================================================


class TestPrintResult:
    """print_result 함수 테스트"""

    def test_print_result_with_duplicates(self, capsys):
        """중복 있는 결과 출력"""
        dup = DuplicateMatch(
            content_id="dup_001",
            content_path="/path/dup.md",
            similarity=0.95,
            title="Duplicate Title Here",
            source="TechCrunch",
        )
        result = CheckResult(
            content_id="test_001",
            has_duplicates=True,
            duplicates=[dup],
            max_similarity=0.95,
            checked_at="2026-02-27T12:00:00",
        )

        print_result(result, verbose=False)

        captured = capsys.readouterr()
        assert "Found 1 duplicate" in captured.out
        # Format is "95.0%" not "95%" or "0.95"
        assert "95.0%" in captured.out

    def test_print_result_no_duplicates(self, capsys):
        """중복 없는 결과 출력"""
        result = CheckResult(
            content_id="unique_001",
            has_duplicates=False,
            duplicates=[],
            max_similarity=0.3,
            checked_at="2026-02-27T12:00:00",
        )

        print_result(result, verbose=False)

        captured = capsys.readouterr()
        assert "No duplicates" in captured.out

    def test_print_result_verbose(self, capsys):
        """상세 출력 모드"""
        dup = DuplicateMatch(
            content_id="dup_001",
            content_path="/path/to/duplicate.md",
            similarity=0.95,
            title="Duplicate Title",
            source="TechCrunch",
        )
        result = CheckResult(
            content_id="test_001",
            has_duplicates=True,
            duplicates=[dup],
            max_similarity=0.95,
            checked_at="2026-02-27T12:00:00",
        )

        print_result(result, verbose=True)

        captured = capsys.readouterr()
        assert "/path/to/duplicate.md" in captured.out
        assert "TechCrunch" in captured.out


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_threshold_boundary(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
    ):
        """임계값 경계 테스트"""
        checker_with_mocks.threshold = 0.85
        mock_vault.read_frontmatter.return_value = {
            "id": "dup_001",
            "title": "Boundary Test",
            "source": "Test",
        }

        # 정확히 임계값
        mock_embedding_manager.cosine_similarity.return_value = 0.85
        checker_with_mocks._cache["/path1.md"] = [0.85, 0.1, 0.05]

        duplicates = checker_with_mocks._find_duplicates(
            content_id="test_001",
            embedding=[1.0, 0.0, 0.0],
            compare_paths=["/path1.md"],
        )

        # 임계값 이상이면 중복으로 간주 (>=)
        assert len(duplicates) == 1

    def test_empty_compare_paths(
        self,
        checker_with_mocks,
    ):
        """빈 비교 경로 리스트"""
        duplicates = checker_with_mocks._find_duplicates(
            content_id="test_001",
            embedding=[1.0, 0.0, 0.0],
            compare_paths=[],
        )

        assert len(duplicates) == 0

    def test_content_without_id_uses_filename(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
    ):
        """ID 없는 콘텐츠는 파일명 사용"""
        meta_without_id = {"title": "No ID Content"}
        content = "Some content"
        mock_vault.read_note.return_value = (meta_without_id, content)
        mock_vault.list_notes.return_value = []
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]

        result = checker_with_mocks.check_content("/path/to/myfile.md")

        assert result.content_id == "myfile"

    def test_max_similarity_with_empty_duplicates(
        self,
        checker_with_mocks,
        mock_vault,
        mock_embedding_manager,
        sample_note_meta,
        sample_note_content,
    ):
        """중복 없을 때 max_similarity는 0.0"""
        mock_vault.read_note.return_value = (sample_note_meta, sample_note_content)
        mock_vault.list_notes.return_value = []
        mock_embedding_manager.embed.return_value = [1.0, 0.0, 0.0]

        result = checker_with_mocks.check_content("/path/to/content.md")

        assert result.max_similarity == 0.0
