"""
Unit tests for SourceMeta extended fields
Phase 1.4 implementation tests
"""

from picko.source_manager import SourceMeta


class TestSourceMetaExtended:
    """SourceMeta Subsystem B 필드 테스트"""

    def test_default_extended_fields(self):
        """확장 필드 기본값"""
        source = SourceMeta(
            id="test_source",
            type="rss",
            url="https://example.com/feed",
            category="tech",
        )

        assert source.human_review_required is False
        assert source.api_provider is None
        assert source.account_handle is None
        assert source.last_api_sync is None
        assert source.enhanced_verification is None

    def test_set_human_review_required(self):
        """사람 검토 필요 설정"""
        source = SourceMeta(
            id="test_source",
            type="social",
            url="https://threads.net/@ai_news",
            category="discovered",
            human_review_required=True,
        )

        assert source.human_review_required is True

    def test_set_api_provider(self):
        """API 제공자 설정"""
        source = SourceMeta(
            id="threads_ai_news",
            type="social",
            url="https://threads.net/@ai_news",
            category="discovered",
            api_provider="threads_api",
        )

        assert source.api_provider == "threads_api"

    def test_set_account_handle(self):
        """계정 핸들 설정"""
        source = SourceMeta(
            id="threads_ai_news",
            type="social",
            url="https://threads.net/@ai_news",
            category="discovered",
            account_handle="@ai_news",
        )

        assert source.account_handle == "@ai_news"

    def test_set_enhanced_verification(self):
        """강화 검증 설정"""
        source = SourceMeta(
            id="new_source",
            type="social",
            url="https://threads.net/@new_ai",
            category="discovered",
            enhanced_verification={
                "enabled": True,
                "collections_remaining": 5,
                "elevated_threshold": 0.92,
            },
        )

        assert source.enhanced_verification is not None
        assert source.enhanced_verification["enabled"] is True
        assert source.enhanced_verification["collections_remaining"] == 5

    def test_to_dict_includes_extended_fields(self):
        """to_dict()에 확장 필드 포함"""
        source = SourceMeta(
            id="test_source",
            type="social",
            url="https://threads.net/@ai_news",
            category="discovered",
            human_review_required=True,
            api_provider="threads_api",
            account_handle="@ai_news",
            last_api_sync="2026-03-01T10:00:00",
            enhanced_verification={"enabled": True, "collections_remaining": 5},
        )

        result = source.to_dict(include_v2=True)

        assert result["human_review_required"] is True
        assert result["api_provider"] == "threads_api"
        assert result["account_handle"] == "@ai_news"
        assert result["last_api_sync"] == "2026-03-01T10:00:00"
        assert result["enhanced_verification"]["enabled"] is True

    def test_to_dict_excludes_default_values(self):
        """기본값은 to_dict()에서 제외"""
        source = SourceMeta(
            id="test_source",
            type="rss",
            url="https://example.com/feed",
            category="tech",
        )

        result = source.to_dict(include_v2=True)

        # 기본값인 False/None은 포함되지 않음
        assert "human_review_required" not in result
        assert "api_provider" not in result
        assert "account_handle" not in result

    def test_from_dict_with_extended_fields(self):
        """from_dict()로 확장 필드 로드"""
        data = {
            "id": "test_source",
            "type": "social",
            "url": "https://threads.net/@ai_news",
            "category": "discovered",
            "human_review_required": True,
            "api_provider": "threads_api",
            "account_handle": "@ai_news",
            "last_api_sync": "2026-03-01T10:00:00",
            "enhanced_verification": {"enabled": True, "collections_remaining": 5},
        }

        source = SourceMeta.from_dict(data)

        assert source.human_review_required is True
        assert source.api_provider == "threads_api"
        assert source.account_handle == "@ai_news"
        assert source.last_api_sync == "2026-03-01T10:00:00"
        assert source.enhanced_verification is not None
        assert source.enhanced_verification["collections_remaining"] == 5

    def test_from_dict_without_extended_fields(self):
        """확장 필드 없는 데이터도 로드 가능"""
        data = {
            "id": "legacy_source",
            "type": "rss",
            "url": "https://example.com/feed",
            "category": "tech",
        }

        source = SourceMeta.from_dict(data)

        # 기본값 사용
        assert source.human_review_required is False
        assert source.api_provider is None

    def test_roundtrip_to_dict_from_dict(self):
        """to_dict() → from_dict() 라운드트립"""
        original = SourceMeta(
            id="test_source",
            type="social",
            url="https://threads.net/@ai_news",
            category="discovered",
            enabled=False,
            auto_discovered=True,
            status="pending",
            human_review_required=True,
            api_provider="threads_api",
            account_handle="@ai_news",
            enhanced_verification={"enabled": True, "collections_remaining": 5},
        )

        # to_dict → from_dict
        data = original.to_dict(include_v2=True)
        restored = SourceMeta.from_dict(data)

        assert restored.id == original.id
        assert restored.human_review_required == original.human_review_required
        assert restored.api_provider == original.api_provider
        assert restored.account_handle == original.account_handle
        assert restored.enhanced_verification == original.enhanced_verification


class TestSourceMetaV2Compatibility:
    """V2 필드와의 호환성 테스트"""

    def test_v2_fields_preserved(self):
        """V2 필드가 보존됨"""
        source = SourceMeta(
            id="test_source",
            type="rss",
            url="https://example.com/feed",
            category="tech",
            auto_discovered=True,
            status="pending",
            discovered_at="2026-03-01T10:00:00",
            discovered_by="subsystem_b",
            quality_score=0.87,
        )

        data = source.to_dict(include_v2=True)

        assert data["auto_discovered"] is True
        assert data["status"] == "pending"
        assert data["discovered_at"] == "2026-03-01T10:00:00"

    def test_platform_field_not_confused(self):
        """platform 필드 (뉴스레터용)와 api_provider 구분"""
        source = SourceMeta(
            id="substack_source",
            type="newsletter",
            url="https://newsletter.example.com",
            category="newsletter",
            platform="substack",  # 뉴스레터 플랫폼
            api_provider="threads_api",  # 소셜 API 제공자
        )

        assert source.platform == "substack"
        assert source.api_provider == "threads_api"

        data = source.to_dict(include_v2=True)

        assert data["platform"] == "substack"
        assert data["api_provider"] == "threads_api"


class TestEnhancedVerification:
    """강화 검증 필드 테스트"""

    def test_enhanced_verification_structure(self):
        """강화 검증 구조"""
        ev = {
            "enabled": True,
            "collections_remaining": 5,
            "elevated_threshold": 0.92,
        }

        source = SourceMeta(
            id="new_source",
            type="social",
            url="https://threads.net/@new_ai",
            category="discovered",
            enhanced_verification=ev,
        )

        assert source.enhanced_verification == ev

    def test_decrement_collections_remaining(self):
        """수집 횟수 감소"""
        source = SourceMeta(
            id="new_source",
            type="social",
            url="https://threads.net/@new_ai",
            category="discovered",
            enhanced_verification={
                "enabled": True,
                "collections_remaining": 5,
                "elevated_threshold": 0.92,
            },
        )

        # 수집 후 감소
        if source.enhanced_verification:
            source.enhanced_verification["collections_remaining"] -= 1

        assert source.enhanced_verification is not None
        assert source.enhanced_verification["collections_remaining"] == 4

    def test_disable_enhanced_verification_after_n_collections(self):
        """N회 수집 후 강화 검증 비활성화"""
        source = SourceMeta(
            id="new_source",
            type="social",
            url="https://threads.net/@new_ai",
            category="discovered",
            enhanced_verification={
                "enabled": True,
                "collections_remaining": 1,
                "elevated_threshold": 0.92,
            },
        )

        # 마지막 수집
        if source.enhanced_verification:
            source.enhanced_verification["collections_remaining"] -= 1
            if source.enhanced_verification["collections_remaining"] <= 0:
                source.enhanced_verification["enabled"] = False

        assert source.enhanced_verification is not None
        assert source.enhanced_verification["enabled"] is False
