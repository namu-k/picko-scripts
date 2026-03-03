"""
VideoPlan 데이터 모델
Picko가 생성하는 표준 영상 기획 포맷.

외부 AI 동영상 서비스(Runway, Pika, Kling, Luma, Veo 등)에 넘기기 전
모든 기획 정보를 담는 중간 표현.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

# 지원 서비스 목록
VideoService = Literal["runway", "pika", "kling", "luma", "veo", "sora"]

# 지원 플랫폼
VideoPlatform = Literal[
    "instagram_reel",
    "youtube_short",
    "tiktok",
    "twitter_video",
    "linkedin_video",
]

# 입력 소스 타입
SourceType = Literal[
    "account_only",  # 계정 설정만으로 아이디어 기획 (서비스 기반)
    "longform",  # 기존 longform 결과물 기반
    "pack",  # 기존 pack 결과물 기반
    "digest",  # digest 항목 기반
]


@dataclass
class VideoShot:
    """단일 클립/샷 정보"""

    index: int
    duration_sec: int
    shot_type: str  # "intro" | "main" | "cta" | "background" | 자유 기입
    script: str  # 장면 설명 또는 나레이션 텍스트
    caption: str  # 화면에 표시할 자막/텍스트
    background_prompt: str  # 텍스트→비디오 프롬프트 (영문 권장)
    # 서비스별 세부 힌트 (자유 딕셔너리)
    notes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "duration_sec": self.duration_sec,
            "shot_type": self.shot_type,
            "script": self.script,
            "caption": self.caption,
            "background_prompt": self.background_prompt,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VideoShot:
        return cls(
            index=d["index"],
            duration_sec=d["duration_sec"],
            shot_type=d.get("shot_type", "main"),
            script=d.get("script", ""),
            caption=d.get("caption", ""),
            background_prompt=d.get("background_prompt", ""),
            notes=d.get("notes", {}),
        )


@dataclass
class BrandStyle:
    """영상에 적용할 브랜드/스타일 정보"""

    tone: str  # 예: "감성/몽환적", "친근하지만 전문적"
    theme: str = ""  # 계정명 또는 테마 식별자
    colors: dict[str, str] = field(default_factory=dict)
    fonts: dict[str, str] = field(default_factory=dict)
    aspect_ratio: str = "9:16"  # 기본 세로형

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "tone": self.tone,
            "colors": self.colors,
            "fonts": self.fonts,
            "aspect_ratio": self.aspect_ratio,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BrandStyle:
        return cls(
            tone=d.get("tone", ""),
            theme=d.get("theme", ""),
            colors=d.get("colors", {}),
            fonts=d.get("fonts", {}),
            aspect_ratio=d.get("aspect_ratio", "9:16"),
        )


@dataclass
class VideoSource:
    """영상 기획의 입력 소스"""

    type: SourceType
    id: str = ""  # 참조 소스 ID (없으면 account_only)
    summary: str = ""  # 소스 내용 요약 (프롬프트 생성에 활용)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "id": self.id, "summary": self.summary}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VideoSource:
        return cls(
            type=d.get("type", "account_only"),
            id=d.get("id", ""),
            summary=d.get("summary", ""),
        )


@dataclass
class VideoPlan:
    """
    Picko 표준 영상 기획 포맷.

    이 객체 하나가 하나의 영상(또는 영상 시리즈)에 대한
    완전한 기획서를 담는다.
    """

    id: str
    account: str
    goal: str
    source: VideoSource
    brand_style: BrandStyle
    shots: list[VideoShot]
    target_services: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    duration_sec: int = 0  # 전체 목표 길이 (샷 합산으로 계산 가능)
    created_at: str = ""  # ISO 날짜 문자열

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d")
        if self.duration_sec == 0 and self.shots:
            self.duration_sec = sum(s.duration_sec for s in self.shots)

    # ──────────────────────────────────────────────
    # 직렬화
    # ──────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "account": self.account,
            "goal": self.goal,
            "source": self.source.to_dict(),
            "brand_style": self.brand_style.to_dict(),
            "target_services": self.target_services,
            "platforms": self.platforms,
            "duration_sec": self.duration_sec,
            "created_at": self.created_at,
            "shots": [s.to_dict() for s in self.shots],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VideoPlan:
        return cls(
            id=d["id"],
            account=d["account"],
            goal=d["goal"],
            source=VideoSource.from_dict(d.get("source", {"type": "account_only"})),
            brand_style=BrandStyle.from_dict(d.get("brand_style", {})),
            shots=[VideoShot.from_dict(s) for s in d.get("shots", [])],
            target_services=d.get("target_services", []),
            platforms=d.get("platforms", []),
            duration_sec=d.get("duration_sec", 0),
            created_at=d.get("created_at", ""),
        )

    @classmethod
    def from_json(cls, text: str) -> VideoPlan:
        return cls.from_dict(json.loads(text))

    # ──────────────────────────────────────────────
    # 마크다운 출력 (Vault 저장용)
    # ──────────────────────────────────────────────

    def to_markdown(self) -> str:
        lines = [
            f"# VideoPlan: {self.id}",
            "",
            f"**계정**: {self.account}",
            f"**목표**: {self.goal}",
            f"**플랫폼**: {', '.join(self.platforms)}",
            f"**대상 서비스**: {', '.join(self.target_services)}",
            f"**총 길이**: {self.duration_sec}초",
            f"**생성일**: {self.created_at}",
            "",
            "## 브랜드 스타일",
            "",
            f"- 톤: {self.brand_style.tone}",
            f"- 비율: {self.brand_style.aspect_ratio}",
            "",
            "## 샷 리스트",
            "",
        ]
        for shot in self.shots:
            lines += [
                f"### 샷 {shot.index} — {shot.shot_type} ({shot.duration_sec}초)",
                "",
                f"**스크립트**: {shot.script}",
                f"**자막**: {shot.caption}",
                f"**배경 프롬프트**: `{shot.background_prompt}`",
            ]
            if shot.notes:
                lines.append("")
                lines.append("**서비스별 노트**:")
                for svc, note in shot.notes.items():
                    lines.append(f"- `{svc}`: {note}")
            lines.append("")
        return "\n".join(lines)

    # ──────────────────────────────────────────────
    # 파일 저장/로드
    # ──────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """JSON으로 저장"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> VideoPlan:
        """JSON 파일에서 로드"""
        return cls.from_json(path.read_text(encoding="utf-8"))
