"""
prompt_composer 모듈 테스트
"""

# mypy: ignore-errors

from picko.account_context import AccountIdentity, StyleProfile, WeeklySlot
from picko.prompt_composer import PromptComposer, PromptLayer, clear_composer_cache, get_composer


class TestPromptLayer:
    """PromptLayer 테스트"""

    def test_prompt_layer_creation(self):
        """레이어 생성"""
        layer = PromptLayer(name="test", content="Test content", enabled=True)
        assert layer.name == "test"
        assert layer.content == "Test content"
        assert layer.enabled is True

    def test_prompt_layer_disabled(self):
        """비활성화된 레이어"""
        layer = PromptLayer(name="disabled", content="Content", enabled=False)
        assert layer.enabled is False


class TestPromptComposer:
    """PromptComposer 테스트"""

    def setup_method(self):
        """각 테스트 전 캐시 비우기"""
        clear_composer_cache()

    def test_composer_initialization(self):
        """컴포저 초기화"""
        composer = PromptComposer("test_account")
        assert composer.account_id == "test_account"
        assert composer.layers == []

    def test_reset(self):
        """리셋 테스트"""
        composer = PromptComposer("test_account")
        composer.layers = [PromptLayer(name="test")]
        composer.variables = {"key": "value"}

        composer.reset()

        assert composer.layers == []
        assert composer.variables == {}

    def test_set_variables(self):
        """변수 설정"""
        composer = PromptComposer("test_account")
        composer.set_variables(title="Test", content="Content")

        assert composer.variables["title"] == "Test"
        assert composer.variables["content"] == "Content"

    def test_apply_identity(self):
        """정체성 적용"""
        composer = PromptComposer("test_account")
        identity = AccountIdentity(
            account_id="test_account",
            one_liner="테스트 계정입니다",
            target_audience=["개발자", "창업자"],
            value_proposition="테스트 제공",
            pillars=["P1: 테스트"],
            tone_voice={"tone": "캐주얼"},
            boundaries=[],
        )

        composer.apply_identity(identity)

        assert len(composer.layers) == 1
        assert composer.layers[0].name == "identity"
        assert "타겟 독자" in composer.layers[0].content

    def test_apply_context(self):
        """주간 컨텍스트 적용"""
        composer = PromptComposer("test_account")
        slot = WeeklySlot(
            week_of="2026-02-16",
            account_id="test_account",
            customer_outcome="테스트 목표",
            operator_kpi="테스트 KPI",
            cta="테스트 CTA",
            pillar_distribution={"P1": 2},
        )

        composer.apply_context(slot)

        assert composer.variables["cta"] == "테스트 CTA"
        assert composer.variables["customer_outcome"] == "테스트 목표"

    def test_compose_empty(self):
        """빈 상태로 합성"""
        composer = PromptComposer("test_account")
        result = composer.compose("longform")

        assert result.content == ""
        assert result.account_id == "test_account"

    def test_compose_with_layers(self):
        """레이어와 함께 합성"""
        composer = PromptComposer("test_account")
        composer.layers = [
            PromptLayer(name="base", content="기본 프롬프트"),
            PromptLayer(name="style", content="스타일 가이드"),
        ]

        result = composer.compose("longform")

        assert "기본 프롬프트" in result.content
        assert "작성 스타일 가이드" in result.content


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def setup_method(self):
        clear_composer_cache()

    def test_get_composer_singleton(self):
        """싱글톤 패턴"""
        composer1 = get_composer("test_account")
        composer2 = get_composer("test_account")

        assert composer1 is composer2

    def test_get_composer_different_accounts(self):
        """다른 계정은 다른 컴포저"""
        composer1 = get_composer("account1")
        composer2 = get_composer("account2")

        assert composer1 is not composer2


class TestStyleSection:
    """스타일 섹션 생성 테스트"""

    def test_build_style_section(self):
        """스타일 섹션 생성"""
        composer = PromptComposer("test_account")
        style = StyleProfile(
            name="test_style",
            source_urls=["https://example.com"],
            analyzed_at="2026-02-16",
            sample_count=5,
            characteristics={
                "tone": ["casual", "friendly"],
                "sentence_style": "short",
                "vocabulary": ["simple", "clear"],
            },
        )

        section = composer._build_style_section(style)

        assert "어조" in section
        assert "casual" in section
        assert "문장 스타일" in section

    def test_build_style_section_with_extended_fields(self):
        """스타일 섹션 생성 (신 필드: signatures, formatting, content_themes)"""
        composer = PromptComposer("test_account")
        style = StyleProfile(
            name="test_style",
            source_urls=["https://example.com"],
            analyzed_at="2026-02-16",
            sample_count=5,
            characteristics={
                "tone": ["casual", "friendly"],
                "signatures": ["latest news", "in brief"],
                "formatting": ["headlines", "bulleted lists"],
                "content_themes": ["AI", "tech"],
            },
        )

        section = composer._build_style_section(style)

        assert "시그니처 표현" in section
        assert "latest news" in section
        assert "포매팅 방식" in section
        assert "headlines" in section
        assert "콘텐츠 주제" in section
        assert "AI" in section

    def test_build_identity_section(self):
        """정체성 섹션 생성"""
        composer = PromptComposer("test_account")
        identity = AccountIdentity(
            account_id="test_account",
            one_liner="테스트 계정",
            target_audience=["개발자"],
            value_proposition="가치 제안",
            pillars=["P1: 테스트"],
            tone_voice={"tone": "캐주얼", "forbidden": "금칙어"},
            boundaries=[],
        )

        section = composer._build_identity_section(identity)

        assert "계정 정체성" in section
        assert "타겟 독자" in section
        assert "톤&보이스" in section
        assert "금칙어" in section

    def test_build_identity_section_with_extended_fields(self):
        """정체성 섹션 생성 (신 필드: value_proposition, boundaries)"""
        composer = PromptComposer("test_account")
        identity = AccountIdentity(
            account_id="test_account",
            one_liner="테스트 계정",
            target_audience=["개발자"],
            value_proposition="명확한 가치 제안",
            pillars=["P1: 테스트"],
            tone_voice={"tone": "캐주얼", "forbidden": "금칙어"},
            boundaries=["부정적인 내용", "낙말"],
        )

        section = composer._build_identity_section(identity)

        assert "가치 제안" in section
        assert "명확한 가치 제안" in section
        assert "하지 말 것/경계" in section
        assert "부정적인 내용" in section
        assert "낙말" in section


class TestIntegration:
    """통합 테스트"""

    def setup_method(self):
        clear_composer_cache()

    def test_full_composition_flow(self):
        """전체 합성 플로우"""
        identity = AccountIdentity(
            account_id="test_account",
            one_liner="테스트 계정",
            target_audience=["개발자"],
            value_proposition="가치 제안",
            pillars=["P1: 테스트"],
            tone_voice={"tone": "캐주얼"},
            boundaries=[],
        )

        slot = WeeklySlot(
            week_of="2026-02-16",
            account_id="test_account",
            customer_outcome="학습",
            operator_kpi="참여",
            cta="댓글 달기",
            pillar_distribution={"P1": 1},
        )

        composer = PromptComposer("test_account")
        composer.apply_identity(identity)
        composer.apply_context(slot)
        composer.set_variables(title="테스트 제목")

        result = composer.compose("longform")

        assert result.account_id == "test_account"
        assert result.variables["cta"] == "댓글 달기"
        assert result.variables["title"] == "테스트 제목"
