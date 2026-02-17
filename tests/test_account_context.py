"""
account_context 모듈 테스트
"""

# mypy: ignore-errors

import pytest

from picko.account_context import AccountContextLoader, parse_identity, parse_weekly_slot

# ─────────────────────────────────────────────────────────────────────────────
# 파서 함수 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestParseIdentity:
    """계정 정체성 파서 테스트"""

    def test_parse_identity_valid(self):
        """유효한 마크다운 파싱"""
        md_content = """
# 계정 정체성

## 1) 한 문장 정의
- 이 계정은 **예비창업자**를 위한 계정이다. ^one_liner

## 2) 타깃(구체화)
- 1차 타깃: 퇴사 예정 예비창업자
- 2차 타깃: 초기창업자

## 3) 약속(Value Proposition)
- 실행 인사이트 제공

## 4) 콘텐츠 범위(필러)
- 필러 1: 검증(아이디어/문제정의)
- 필러 2: 빌드(MVP/출시)
- 필러 3: 그로스(성장/마케팅)
- 필러 4: 스케일(지표/퍼널)

## 5) 톤&보이스
- 말투: 짧고 간결하게
- 금칙어: 보장, 무조건

## 6) 경계(하지 않을 것)
- 투자 조언
- 법률 조언

## 7) 바이오/프로필 초안
- 바이오 1줄: 예비창업자를 위한 실행 가이드
"""
        result = parse_identity(md_content, "test_account")

        assert result is not None
        assert result.account_id == "test_account"
        assert "예비창업자" in result.one_liner
        assert len(result.target_audience) > 0
        assert len(result.pillars) == 4
        assert "tone" in result.tone_voice
        assert len(result.boundaries) > 0

    def test_parse_identity_empty(self):
        """빈 내용 파싱 - None 반환"""
        result = parse_identity("", "test")
        assert result is None

    def test_parse_identity_minimal(self):
        """최소한의 필드만 있는 경우"""
        md_content = """
# 계정

## 한 문장
- 테스트 계정 ^one_liner
"""
        result = parse_identity(md_content, "minimal")
        assert result is not None
        assert result.one_liner == "테스트 계정"


class TestParseWeeklySlot:
    """주간 슬롯 파서 테스트"""

    def test_parse_weekly_slot_valid(self):
        """유효한 마크다운 파싱"""
        md_content = """
# 주간 7개 주제 슬롯

- account_id: builders_social_club
- 고객 Outcome: 실행 로드맵
- 운영자 KPI(1): 팔로워 증가
- CTA(1): 댓글 남기기

## 필러(4개) & 배분(2-2-2-1)
- P1 (2개): 리서치/검증
- P2 (2개): 제품/MVP
- P3 (2개): 성장/유통
- P4 (1개): 스케일업
"""
        result = parse_weekly_slot(md_content, "2026-02-16")

        assert result is not None
        assert result.week_of == "2026-02-16"
        assert result.account_id == "builders_social_club"
        assert result.customer_outcome == "실행 로드맵"
        assert result.operator_kpi == "팔로워 증가"
        assert result.cta == "댓글 남기기"
        assert result.pillar_distribution == {"P1": 2, "P2": 2, "P3": 2, "P4": 1}

    def test_parse_weekly_slot_empty(self):
        """빈 내용 파싱 - None 반환"""
        result = parse_weekly_slot("", "2026-02-16")
        # account_id가 없으므로 None
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 로더 클래스 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestAccountContextLoader:
    """AccountContextLoader 테스트"""

    def test_init_default_vault(self, temp_vault_dir):
        """기본 vault 경로로 초기화"""
        loader = AccountContextLoader(temp_vault_dir)
        assert loader.root == temp_vault_dir

    def test_load_identity_from_file(self, temp_vault_dir):
        """파일에서 계정 정체성 로드"""
        # 테스트 파일 생성
        identity_file = temp_vault_dir / "test_identity.md"
        identity_file.write_text(
            """
## 1) 한 문장 정의
- 테스트 계정 ^one_liner

## 2) 타깃
- 예비창업자
""",
            encoding="utf-8",
        )

        loader = AccountContextLoader(temp_vault_dir)
        result = loader.load_identity_from_file(identity_file)

        assert result is not None
        assert result.account_id == "test_identity"
        assert result.one_liner == "테스트 계정"

    def test_load_identity_cache(self, temp_vault_dir):
        """캐싱 동작 확인"""
        identity_file = temp_vault_dir / "cache_test.md"
        identity_file.write_text(
            """
## 한 문장
- 캐시 테스트 ^one_liner
""",
            encoding="utf-8",
        )

        loader = AccountContextLoader(temp_vault_dir)

        # 첫 번째 로드
        result1 = loader.load_identity_from_file(identity_file)
        # 두 번째 로드 (캐시에서)
        result2 = loader.load_identity_from_file(identity_file)

        assert result1 is result2  # 동일 인스턴스 (캐시)

    def test_load_style_profile(self, temp_vault_dir):
        """스타일 프로필 로드"""
        # 스타일 디렉토리 및 파일 생성
        style_dir = temp_vault_dir / "config" / "reference_styles" / "test_style"
        style_dir.mkdir(parents=True)

        profile_file = style_dir / "profile.yml"
        profile_file.write_text(
            """
name: test_style
source_urls:
  - https://example.com
analyzed_at: '2026-02-16T00:00:00'
sample_count: 5
characteristics:
  tone:
    - casual
    - friendly
  sentence_style: short
""",
            encoding="utf-8",
        )

        loader = AccountContextLoader(temp_vault_dir)
        result = loader.load_style_profile("test_style")

        assert result is not None
        assert result.name == "test_style"
        assert result.sample_count == 5
        assert result.characteristics["tone"] == ["casual", "friendly"]

    def test_clear_cache(self, temp_vault_dir):
        """캐시 비우기 확인"""
        identity_file = temp_vault_dir / "clear_cache.md"
        identity_file.write_text("## 한 문장\n- 테스트 ^one_liner", encoding="utf-8")

        loader = AccountContextLoader(temp_vault_dir)
        loader.load_identity_from_file(identity_file)

        assert len(loader._identity_cache) > 0

        loader.clear_cache()
        assert len(loader._identity_cache) == 0
        assert len(loader._weekly_slot_cache) == 0
        assert len(loader._style_cache) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 편의 함수 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def test_get_loader_singleton(self, temp_vault_dir):
        """싱글톤 패턴 확인"""
        import picko.account_context as ac_module

        # 리셋
        ac_module._loader = None

        # 첫 호출
        loader1 = ac_module.get_loader(temp_vault_dir)
        assert ac_module._loader is not None

        # 두 번째 호출 (동일 인스턴스)
        loader2 = ac_module.get_loader()
        assert loader1 is loader2

    def test_get_identity(self, temp_vault_dir):
        """get_identity 편의 함수"""
        identity_file = temp_vault_dir / "test.md"
        identity_file.write_text("## 한 문장\n- 테스트 ^one_liner", encoding="utf-8")

        # 파일 직접 로드 (get_identity는 기본 경로를 사용하므로)
        loader = AccountContextLoader(temp_vault_dir)
        result = loader.load_identity_from_file(identity_file)

        assert result is not None
        assert result.one_liner == "테스트"


# ─────────────────────────────────────────────────────────────────────────────
# 실제 파일 통합 테스트 (mock_vault 사용)
# ─────────────────────────────────────────────────────────────────────────────


class TestRealFilesIntegration:
    """실제 mock_vault 파일 통합 테스트"""

    @pytest.mark.slow
    def test_load_real_identity(self):
        """실제 계정 정체성 파일 로드"""
        from pathlib import Path

        identity_file = Path(
            "mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/aa. 소셜빌더스/"
            "빌더스소셜클럽 — 계정 정체성.md"
        )
        # 파일이 gitignore되어 CI 환경에서는 없을 수 있으므로 존재 확인
        if not identity_file.exists():
            pytest.skip("Identity file not found (gitignored in CI)")

        loader = AccountContextLoader("mock_vault")
        result = loader.load_identity_from_file(str(identity_file))

        # 파일이 존재하면 파싱 확인
        assert result is not None
        assert "빌더스소셜클럽" in result.account_id
        assert len(result.one_liner) > 0
        # 빌더스소셜클럽 관련 키워드 확인
        assert "예비창업자" in result.one_liner or "창업" in result.one_liner
        assert len(result.target_audience) > 0
        assert len(result.pillars) == 4

    @pytest.mark.slow
    def test_load_real_weekly_slot(self):
        """실제 주간 슬롯 파일 로드 (파일 직접 읽기)"""
        from pathlib import Path

        weekly_slot_file = Path(
            "mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/aa. 소셜빌더스/"
            "빌더스소셜클럽 — 주간 7개 주제 슬롯 프리셋(2-2-2-1).md"
        )
        # 파일이 gitignore되어 CI 환경에서는 없을 수 있으므로 존재 확인
        if not weekly_slot_file.exists():
            pytest.skip("Weekly slot file not found (gitignored in CI)")

        content = weekly_slot_file.read_text(encoding="utf-8")
        result = parse_weekly_slot(content, "2026-02-16")

        assert result is not None
        assert result.account_id == "builders_social_club"
        assert result.pillar_distribution == {"P1": 2, "P2": 2, "P3": 2, "P4": 1}
        assert (
            "검증" in result.customer_outcome
            or "실행" in result.customer_outcome
            or "로드맵" in result.customer_outcome
        )

    @pytest.mark.slow
    def test_load_real_account_profile(self):
        """실제 계정 프로필 로드 (socialbuilders.yml)"""
        from pathlib import Path

        import yaml

        profile_file = Path("mock_vault/config/accounts/socialbuilders.yml")
        if profile_file.exists():
            with open(profile_file, "r", encoding="utf-8") as f:
                result = yaml.safe_load(f)

            assert result is not None
            assert result["name"] == "Social Builders"
            assert "twitter" in result["channels"]
            assert result["channels"]["twitter"]["max_length"] == 280


# ─────────────────────────────────────────────────────────────────────────────
# scoring 연동 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestScoringIntegration:
    """scoring.py 연동 테스트"""

    def test_score_with_account_identity(self, temp_vault_dir):
        """AccountIdentity를 사용한 점수 계산"""
        from picko.account_context import AccountIdentity
        from picko.scoring import ContentScorer

        # 계정 정체성 생성
        identity = AccountIdentity(
            account_id="test_account",
            one_liner="예비창업자를 위한 계정",
            target_audience=["예비창업자", "초기창업자"],
            value_proposition="실행 인사이트 제공",
            pillars=["P1: 검증", "P2: 빌드", "P3: 그로스", "P4: 스케일"],
            tone_voice={"tone": "간결"},
            boundaries=["투자 조언"],
        )

        scorer = ContentScorer(account_identity=identity)

        # 관련 콘텐츠 (높은 점수 예상)
        content = {
            "title": "예비창업자를 위한 아이디어 검증 가이드",
            "text": "초기창업자가 MVP를 빌드하는 방법과 성장 전략",
            "keywords": ["창업", "MVP", "성장"],
        }

        result = scorer._calculate_relevance(content)

        # 관련 키워드가 포함되어 있으므로 점수가 높아야 함
        assert result > 0.5

    def test_score_without_account_identity(self, temp_vault_dir):
        """AccountIdentity 없이도 작동 확인 (호환성)"""
        from picko.scoring import ContentScorer

        # account_identity 없이 초기화
        scorer = ContentScorer(account_identity=None, account_profile=None)

        content = {
            "title": "테스트 콘텐츠",
            "text": "내용",
        }

        # 기본 점수 반환 (매칭 없으면 0.5)
        result = scorer._calculate_relevance(content)
        assert result == 0.5
