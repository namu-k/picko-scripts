"""
계정 컨텍스트 로더 모듈
계정 정체성, 주간 슬롯, 스타일 프로필 로드 및 파싱
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import get_config
from .logger import get_logger

logger = get_logger("account_context")

# ─────────────────────────────────────────────────────────────────────────────
# 데이터클래스 정의
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AccountIdentity:
    """계정 정체성 정보"""

    account_id: str
    one_liner: str
    target_audience: list[str]
    value_proposition: str
    pillars: list[str]  # P1~P4
    tone_voice: dict
    boundaries: list[str]
    bio: str = ""
    bio_secondary: str = ""
    link_purpose: str = ""

    def __repr__(self) -> str:
        return f"AccountIdentity(account_id={self.account_id})"


@dataclass
class DailySlot:
    """일일 슬롯 정보"""

    day: int  # 1-7
    pillar: str  # P1, P2, P3, P4
    topic: str = ""
    notes: str = ""

    def __repr__(self) -> str:
        return f"DailySlot(day={self.day}, pillar={self.pillar})"


@dataclass
class WeeklySlot:
    """주간 슬롯 프리셋 정보"""

    week_of: str
    account_id: str
    customer_outcome: str
    operator_kpi: str
    cta: str
    pillar_distribution: dict  # {"P1": 2, "P2": 2, "P3": 2, "P4": 1}
    daily_slots: list[DailySlot] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"WeeklySlot(week_of={self.week_of}, account_id={self.account_id})"


@dataclass
class StyleProfile:
    """스타일 프로필 정보"""

    name: str
    source_urls: list[str]
    analyzed_at: str
    sample_count: int
    characteristics: dict

    def __repr__(self) -> str:
        return f"StyleProfile(name={self.name})"


# ─────────────────────────────────────────────────────────────────────────────
# 파서 함수
# ─────────────────────────────────────────────────────────────────────────────


def parse_identity(md_content: str, account_id: str = "unknown") -> AccountIdentity | None:  # noqa: C901
    """
    마크다운 내용에서 계정 정체성 파싱

    Args:
        md_content: 마크다운 파일 내용
        account_id: 계정 ID (파일명 등에서 추출)

    Returns:
        AccountIdentity 인스턴스 또는 None (파싱 실패 시)
    """
    try:
        # 기본값 초기화
        one_liner = ""
        target_audience: list[str] = []
        value_proposition = ""
        pillars: list[str] = []
        tone_voice: dict = {}
        boundaries: list[str] = []
        bio = ""
        bio_secondary = ""
        link_purpose = ""

        # 섹션별로 내용을 파싱하기 위해 섹션 구분
        sections: dict[str, str] = {}
        current_section = ""
        current_content: list[str] = []

        for line in md_content.split("\n"):
            line = line.rstrip()
            if line.startswith("## "):
                # 이전 섹션 저장
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # 마지막 섹션 저장
        if current_section:
            sections[current_section] = "\n".join(current_content)

        # 1) 한 문장 정의
        for key, content in sections.items():
            if "한 문장 정의" in key or "one_liner" in key.lower():
                # ^one_liner 애노테이션으로 추출
                for line in content.split("\n"):
                    if "^one_liner" in line:
                        one_liner = line.split("^one_liner")[0].replace("-", "").strip()
                        one_liner = re.sub(r"\*\*(.*?)\*\*", r"\1", one_liner)
                        one_liner = one_liner.strip()
                        break

        # 2) 타깃(구체화)
        for key, content in sections.items():
            if "타깃" in key:
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        item = line[2:].strip()
                        # 타깃 헤더("1차 타깃:") 제외, 키워드/표현도 수집
                        if item and ":" not in item and not item.startswith('"'):
                            target_audience.append(item)
                        elif "차 타깃" in item or "예비" in item or "초기" in item:
                            # 타깃 정의 라인도 포함
                            if ":" in item:
                                target_audience.append(item)

        # 3) 약속 (Value Proposition)
        for key, content in sections.items():
            if "약속" in key or "Value Proposition" in key:
                for line in content.split("\n"):
                    if line.strip().startswith("- "):
                        value_proposition = line.strip()[2:]
                        break

        # 4) 필러 (Pillars)
        for key, content in sections.items():
            if "필러" in key or "콘텐츠 범위" in key:
                for line in content.split("\n"):
                    pillar_match = re.search(r"필러 (\d):", line)
                    if pillar_match:
                        pillar_name = pillar_match.group(1)
                        # 전체 라인에서 설명 부분 추출
                        desc_match = re.search(r": (.+)", line)
                        if desc_match:
                            pillar_desc = f"P{pillar_name}: {desc_match.group(1).strip()}"
                            pillars.append(pillar_desc)

        # 5) 톤&보이스
        for key, content in sections.items():
            if "톤" in key or "보이스" in key:
                for line in content.split("\n"):
                    if "말투:" in line:
                        tone_desc = line.split("말투:")[1].strip()
                        tone_voice["tone"] = tone_desc
                    elif "금칙어" in line or "피해야 할" in line:
                        forbidden = line.split(":")[-1].strip() if ":" in line else ""
                        tone_voice["forbidden"] = forbidden
                    elif "CTA 스타일:" in line:
                        cta_style = line.split("CTA 스타일:")[-1].strip()
                        tone_voice["cta_style"] = cta_style

        # 6) 경계
        for key, content in sections.items():
            if "경계" in key:
                for line in content.split("\n"):
                    if line.strip().startswith("- ") and "하지 않을 것" not in line:
                        boundaries.append(line.strip()[2:])

        # 7) 바이오/프로필
        for key, content in sections.items():
            if "바이오" in key or "프로필" in key:
                for line in content.split("\n"):
                    if "바이오 1줄" in line:
                        bio = line.split(":")[-1].strip() if ":" in line else ""
                    elif "보조 1줄" in line:
                        bio_secondary = line.split(":")[-1].strip() if ":" in line else ""
                    elif "링크 목적" in line:
                        link_purpose = line.split(":")[-1].strip() if ":" in line else ""

        # 유효성 검사 - 최소한의 필드 확인
        if not one_liner and not target_audience:
            logger.warning("Failed to parse AccountIdentity: insufficient data")
            return None

        return AccountIdentity(
            account_id=account_id,
            one_liner=one_liner,
            target_audience=target_audience,
            value_proposition=value_proposition,
            pillars=pillars,
            tone_voice=tone_voice,
            boundaries=boundaries,
            bio=bio,
            bio_secondary=bio_secondary,
            link_purpose=link_purpose,
        )

    except Exception as e:
        logger.error(f"Error parsing identity: {e}")
        return None


def parse_weekly_slot(md_content: str, week_of: str = "") -> WeeklySlot | None:
    """
    마크다운 내용에서 주간 슬롯 파싱

    Args:
        md_content: 마크다운 파일 내용
        week_of: 주간 시작일 (YYYY-MM-DD)

    Returns:
        WeeklySlot 인스턴스 또는 None (파싱 실패 시)
    """
    try:
        account_id = ""
        customer_outcome = ""
        operator_kpi = ""
        cta = ""
        pillar_distribution: dict[str, int] = {}

        # 메타데이터 파싱 (account_id, outcome, kpi, cta)
        for line in md_content.split("\n"):
            line = line.strip()
            if line.startswith("- account_id:"):
                account_id = line.split(":")[1].strip()
            elif line.startswith("- 고객 Outcome:"):
                customer_outcome = line.split(":", 1)[1].strip()
            elif line.startswith("- 운영자 KPI"):
                operator_kpi = line.split(":", 1)[1].strip()
            elif line.startswith("- CTA"):
                cta = line.split(":", 1)[1].strip()

        # 필러 배분 파싱
        pillar_pattern = r"- P(\d) \((\d+)개\):"
        for match in re.finditer(pillar_pattern, md_content):
            pillar_num = match.group(1)
            count = int(match.group(2))
            pillar_distribution[f"P{pillar_num}"] = count

        # 대체 패턴 (배분이 다른 형식으로 표시된 경우)
        if not pillar_distribution:
            alt_pattern = r"- P(\d) \((\d+)개\):"
            for match in re.finditer(alt_pattern, md_content):
                pillar_num = match.group(1)
                count = int(match.group(2))
                pillar_distribution[f"P{pillar_num}"] = count

        # 슬롯은 템플릿을 복사해서 사용하므로, 기본 daily_slots는 빈 리스트
        daily_slots: list[DailySlot] = []

        # 유효성 검사
        if not account_id:
            logger.warning("Failed to parse WeeklySlot: account_id not found")
            return None

        return WeeklySlot(
            week_of=week_of,
            account_id=account_id,
            customer_outcome=customer_outcome,
            operator_kpi=operator_kpi,
            cta=cta,
            pillar_distribution=pillar_distribution,
            daily_slots=daily_slots,
        )

    except Exception as e:
        logger.error(f"Error parsing weekly slot: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 로더 클래스
# ─────────────────────────────────────────────────────────────────────────────


class AccountContextLoader:
    """
    계정 컨텍스트 로더
    파일 시스템에서 계정 정체성, 주간 슬롯, 스타일 프로필 로드
    """

    def __init__(self, vault_root: str | Path | None = None):
        """
        Args:
            vault_root: Vault 루트 경로 (기본: config에서 로드)
        """
        if vault_root is None:
            config = get_config()
            vault_root = config.vault.root

        self.root = Path(vault_root)
        self._identity_cache: dict[str, AccountIdentity] = {}
        self._weekly_slot_cache: dict[str, WeeklySlot] = {}
        self._style_cache: dict[str, StyleProfile] = {}

        logger.debug(f"AccountContextLoader initialized with root: {self.root}")

    # ─────────────────────────────────────────────────────────────────────
    # 계정 정체성 로드
    # ─────────────────────────────────────────────────────────────────────

    def load_identity(
        self,
        account_id: str,
        relative_path: str | None = None,
    ) -> AccountIdentity | None:
        """
        계정 정체성 로드

        Args:
            account_id: 계정 ID
            relative_path: 정체성 파일 상대 경로
                          (기본: config/Folders_to_operate_social-media_copied_from_Vault/
                                  aa. 소셜빌더스/빌더스소셜클럽 — 계정 정체성.md)

        Returns:
            AccountIdentity 또는 None
        """
        # 캐시 확인
        if account_id in self._identity_cache:
            return self._identity_cache[account_id]

        # 기본 경로 (한글 폴더명)
        if relative_path is None:
            relative_path = (
                "config/Folders_to_operate_social-media_copied_from_Vault/"
                "aa. 소셜빌더스/빌더스소셜클럽 — 계정 정체성.md"
            )

        file_path = self.root / relative_path

        if not file_path.exists():
            logger.warning(f"Identity file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            identity = parse_identity(content, account_id)
            if identity:
                self._identity_cache[account_id] = identity
                logger.info(f"Loaded identity for account: {account_id}")

            return identity

        except Exception as e:
            logger.error(f"Error loading identity for {account_id}: {e}")
            return None

    def load_identity_from_file(self, file_path: str | Path) -> AccountIdentity | None:
        """
        파일 경로에서 계정 정체성 직접 로드

        Args:
            file_path: 마크다운 파일 경로

        Returns:
            AccountIdentity 또는 None
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"Identity file not found: {file_path}")
            return None

        # 파일명에서 account_id 추출
        account_id = file_path.stem

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            identity = parse_identity(content, account_id)
            if identity:
                self._identity_cache[account_id] = identity

            return identity

        except Exception as e:
            logger.error(f"Error loading identity from {file_path}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # 주간 슬롯 로드
    # ─────────────────────────────────────────────────────────────────────

    def load_weekly_slot(
        self,
        week_of: str,
        relative_path: str | None = None,
    ) -> WeeklySlot | None:
        """
        주간 슬롯 로드

        Args:
            week_of: 주간 시작일 (YYYY-MM-DD)
            relative_path: 슬롯 파일 상대 경로
                          (기본: config/Folders_to_operate_social-media_copied_from_Vault/
                                  aa. 소셜빌더스/빌더스소셜클럽 — 주간 7개 주제 슬롯 프리셋(2-2-2-1).md)

        Returns:
            WeeklySlot 또는 None
        """
        # 캐시 확인
        cache_key = f"{week_of}"
        if cache_key in self._weekly_slot_cache:
            return self._weekly_slot_cache[cache_key]

        # 기본 경로
        if relative_path is None:
            relative_path = (
                "config/Folders_to_operate_social-media_copied_from_Vault/"
                "aa. 소셜빌더스/빌더스소셜클럽 — 주간 7개 주제 슬롯 프리셋(2-2-2-1).md"
            )

        file_path = self.root / relative_path

        if not file_path.exists():
            logger.warning(f"Weekly slot file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            weekly_slot = parse_weekly_slot(content, week_of)
            if weekly_slot:
                self._weekly_slot_cache[cache_key] = weekly_slot
                logger.info(f"Loaded weekly slot for week: {week_of}")

            return weekly_slot

        except Exception as e:
            logger.error(f"Error loading weekly slot for {week_of}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # 스타일 프로필 로드
    # ─────────────────────────────────────────────────────────────────────

    def load_style_profile(self, style_name: str) -> StyleProfile | None:
        """
        스타일 프로필 로드

        Args:
            style_name: 스타일 이름 (예: founder_tech_brief)

        Returns:
            StyleProfile 또는 None
        """
        # 캐시 확인
        if style_name in self._style_cache:
            return self._style_cache[style_name]

        # 기본 경로
        relative_path = f"config/reference_styles/{style_name}/profile.yml"
        file_path = self.root / relative_path

        if not file_path.exists():
            logger.warning(f"Style profile not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty style profile: {style_name}")
                return None

            style_profile = StyleProfile(
                name=data.get("name", style_name),
                source_urls=data.get("source_urls", []),
                analyzed_at=data.get("analyzed_at", ""),
                sample_count=data.get("sample_count", 0),
                characteristics=data.get("characteristics", {}),
            )

            self._style_cache[style_name] = style_profile
            logger.info(f"Loaded style profile: {style_name}")

            return style_profile

        except Exception as e:
            logger.error(f"Error loading style profile {style_name}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────────────────────────────

    def clear_cache(self) -> None:
        """캐시 비우기"""
        self._identity_cache.clear()
        self._weekly_slot_cache.clear()
        self._style_cache.clear()
        logger.debug("Cleared all caches")

    def reload_identity(self, account_id: str) -> AccountIdentity | None:
        """계정 정체성 캐시 비우고 다시 로드"""
        if account_id in self._identity_cache:
            del self._identity_cache[account_id]
        return self.load_identity(account_id)

    def reload_weekly_slot(self, week_of: str) -> WeeklySlot | None:
        """주간 슬롯 캐시 비우고 다시 로드"""
        cache_key = f"{week_of}"
        if cache_key in self._weekly_slot_cache:
            del self._weekly_slot_cache[cache_key]
        return self.load_weekly_slot(week_of)

    def reload_style_profile(self, style_name: str) -> StyleProfile | None:
        """스타일 프로필 캐시 비우고 다시 로드"""
        if style_name in self._style_cache:
            del self._style_cache[style_name]
        return self.load_style_profile(style_name)


# ─────────────────────────────────────────────────────────────────────────────
# 편의 함수
# ─────────────────────────────────────────────────────────────────────────────

# 싱글톤 로더 인스턴스
_loader: AccountContextLoader | None = None


def get_loader(vault_root: str | Path | None = None) -> AccountContextLoader:
    """
    싱글톤 AccountContextLoader 인스턴스 반환

    Args:
        vault_root: Vault 루트 경로 (최초 호출 시에만 사용)

    Returns:
        AccountContextLoader 인스턴스
    """
    global _loader
    if _loader is None:
        _loader = AccountContextLoader(vault_root)
    return _loader


def get_identity(account_id: str, relative_path: str | None = None) -> AccountIdentity | None:
    """
    계정 정체성 로드 (편의 함수)

    Args:
        account_id: 계정 ID
        relative_path: 정체성 파일 상대 경로

    Returns:
        AccountIdentity 또는 None
    """
    loader = get_loader()
    return loader.load_identity(account_id, relative_path)


def get_weekly_slot(week_of: str, relative_path: str | None = None) -> WeeklySlot | None:
    """
    주간 슬롯 로드 (편의 함수)

    Args:
        week_of: 주간 시작일 (YYYY-MM-DD)
        relative_path: 슬롯 파일 상대 경로

    Returns:
        WeeklySlot 또는 None
    """
    loader = get_loader()
    return loader.load_weekly_slot(week_of, relative_path)


def get_style_for_account(account_id: str) -> dict[str, Any] | None:
    """
    계정에 연결된 스타일 프로필 로드

    Args:
        account_id: 계정 ID

    Returns:
        스타일 특성 딕셔너리 또는 None

    Note:
        실제 계정-스타일 매핑은 계정 설정 파일이나
        config/accounts/{account_id}.yml에서 style_name을 확인하여 로드합니다.
    """
    try:
        # 기존 config.py의 계정 프로필에서 style_name 확인
        config = get_config()
        account_profile = config.get_account(account_id)

        if not account_profile:
            logger.warning(f"Account profile not found: {account_id}")
            return None

        style_name = account_profile.get("style_name", "default")
        loader = get_loader()
        style_profile = loader.load_style_profile(style_name)

        if style_profile:
            return style_profile.characteristics

        return None

    except Exception as e:
        logger.error(f"Error loading style for account {account_id}: {e}")
        return None
