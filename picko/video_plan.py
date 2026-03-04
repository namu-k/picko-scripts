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

# ──────────────────────────────────────────────
# 서비스별 파라미터 dataclasses
# ──────────────────────────────────────────────


@dataclass
class ServiceParams:
    """모든 서비스의 공통 기반"""

    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"
    duration_sec: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "aspect_ratio": self.aspect_ratio,
            "duration_sec": self.duration_sec,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ServiceParams":
        return cls(
            prompt=d.get("prompt", ""),
            negative_prompt=d.get("negative_prompt", ""),
            aspect_ratio=d.get("aspect_ratio", "9:16"),
            duration_sec=d.get("duration_sec", 5),
        )


@dataclass
class LumaParams(ServiceParams):
    """Luma Dream Machine 전용 파라미터"""

    camera_motion: str = ""  # static | slow_pan | tilt_up | zoom_in | orbit
    motion_intensity: int = 3  # 1-5
    style_preset: str = ""  # cinematic | natural | artistic | minimal
    start_image_url: str = ""
    end_image_url: str = ""
    loop: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "camera_motion": self.camera_motion,
                "motion_intensity": self.motion_intensity,
                "style_preset": self.style_preset,
                "start_image_url": self.start_image_url,
                "end_image_url": self.end_image_url,
                "loop": self.loop,
            }
        )
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LumaParams":
        base = super().from_dict(d)
        return cls(
            prompt=base.prompt,
            negative_prompt=base.negative_prompt,
            aspect_ratio=base.aspect_ratio,
            duration_sec=base.duration_sec,
            camera_motion=d.get("camera_motion", ""),
            motion_intensity=d.get("motion_intensity", 3),
            style_preset=d.get("style_preset", ""),
            start_image_url=d.get("start_image_url", ""),
            end_image_url=d.get("end_image_url", ""),
            loop=d.get("loop", False),
        )


@dataclass
class RunwayParams(ServiceParams):
    """Runway Gen-3/Gen-4 전용 파라미터"""

    motion: int = 5  # 1-10
    camera_move: str = ""  # static | zoom_in | pan_left | tilt_up | orbit
    seed: int = 0
    upscale: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "motion": self.motion,
                "camera_move": self.camera_move,
                "seed": self.seed,
                "upscale": self.upscale,
            }
        )
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunwayParams":
        base = super().from_dict(d)
        return cls(
            prompt=base.prompt,
            negative_prompt=base.negative_prompt,
            aspect_ratio=base.aspect_ratio,
            duration_sec=base.duration_sec,
            motion=d.get("motion", 5),
            camera_move=d.get("camera_move", ""),
            seed=d.get("seed", 0),
            upscale=d.get("upscale", False),
        )


@dataclass
class PikaParams(ServiceParams):
    """Pika 2.x 전용 파라미터"""

    pikaffect: str = ""  # Levitate | Explode | Slice | Melt
    style_preset: str = ""  # 3D | Anime | Realistic
    motion_intensity: int = 3

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "pikaffect": self.pikaffect,
                "style_preset": self.style_preset,
                "motion_intensity": self.motion_intensity,
            }
        )
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PikaParams":
        base = super().from_dict(d)
        return cls(
            prompt=base.prompt,
            negative_prompt=base.negative_prompt,
            aspect_ratio=base.aspect_ratio,
            duration_sec=base.duration_sec,
            pikaffect=d.get("pikaffect", ""),
            style_preset=d.get("style_preset", ""),
            motion_intensity=d.get("motion_intensity", 3),
        )


@dataclass
class KlingParams(ServiceParams):
    """Kling 3.0 전용 파라미터"""

    camera_motion: str = ""
    motion_intensity: int = 3
    style: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "camera_motion": self.camera_motion,
                "motion_intensity": self.motion_intensity,
                "style": self.style,
            }
        )
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KlingParams":
        base = super().from_dict(d)
        return cls(
            prompt=base.prompt,
            negative_prompt=base.negative_prompt,
            aspect_ratio=base.aspect_ratio,
            duration_sec=base.duration_sec,
            camera_motion=d.get("camera_motion", ""),
            motion_intensity=d.get("motion_intensity", 3),
            style=d.get("style", ""),
        )


@dataclass
class VeoParams(ServiceParams):
    """Google Veo 3.x 전용 파라미터"""

    generate_audio: bool = True
    audio_mood: str = ""  # calm | energetic | dramatic
    style_preset: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "generate_audio": self.generate_audio,
                "audio_mood": self.audio_mood,
                "style_preset": self.style_preset,
            }
        )
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VeoParams":
        base = super().from_dict(d)
        return cls(
            prompt=base.prompt,
            negative_prompt=base.negative_prompt,
            aspect_ratio=base.aspect_ratio,
            duration_sec=base.duration_sec,
            generate_audio=d.get("generate_audio", True),
            audio_mood=d.get("audio_mood", ""),
            style_preset=d.get("style_preset", ""),
        )


# ──────────────────────────────────────────────
# 오디오/텍스트 사양
# ──────────────────────────────────────────────


@dataclass
class AudioSpec:
    """오디오 사양"""

    mood: str = ""  # calm | energetic | dramatic | romantic
    genre: str = ""  # ambient | lofi | orchestral | electronic
    bpm: int = 0
    voiceover_text: str = ""
    voiceover_gender: str = ""  # male | female
    voiceover_tone: str = ""  # warm | professional | casual
    sfx: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mood": self.mood,
            "genre": self.genre,
            "bpm": self.bpm,
            "voiceover_text": self.voiceover_text,
            "voiceover_gender": self.voiceover_gender,
            "voiceover_tone": self.voiceover_tone,
            "sfx": self.sfx,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AudioSpec":
        return cls(
            mood=d.get("mood", ""),
            genre=d.get("genre", ""),
            bpm=d.get("bpm", 0),
            voiceover_text=d.get("voiceover_text", ""),
            voiceover_gender=d.get("voiceover_gender", ""),
            voiceover_tone=d.get("voiceover_tone", ""),
            sfx=d.get("sfx", []),
        )


@dataclass
class TextOverlay:
    """텍스트 오버레이 사양"""

    text: str
    position: str = "center"  # top | center | bottom
    font_size: str = "medium"  # small | medium | large
    font_color: str = "#FFFFFF"
    background: str = ""
    animation: str = ""  # fade_in | slide_up | typewriter | pulse
    start_sec: float = 0.0
    end_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "position": self.position,
            "font_size": self.font_size,
            "font_color": self.font_color,
            "background": self.background,
            "animation": self.animation,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TextOverlay":
        return cls(
            text=d.get("text", ""),
            position=d.get("position", "center"),
            font_size=d.get("font_size", "medium"),
            font_color=d.get("font_color", "#FFFFFF"),
            background=d.get("background", ""),
            animation=d.get("animation", ""),
            start_sec=d.get("start_sec", 0.0),
            end_sec=d.get("end_sec", 0.0),
        )


# 지원 플랫폼
VideoPlatform = Literal[
    "instagram_reel",
    "youtube_short",
    "tiktok",
    "twitter_video",
    "linkedin_video",
]

# 영상 의도 (3축 중 하나 — why)
VideoIntent = Literal["ad", "explainer", "brand", "trend"]

# 입력 소스 타입 (3축 중 하나 — what)
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
    shot_type: str  # "intro" | "main" | "cta" | "background" | "transition" | 자유 기입
    script: str  # 장면 설명 또는 나레이션 텍스트
    caption: str  # 화면에 표시할 자막/텍스트
    background_prompt: str = ""  # 텍스트→비디오 프롬프트 (영문 권장)
    # 서비스별 세부 힌트 (자유 딕셔너리)
    notes: dict[str, str] = field(default_factory=dict)

    # 서비스별 파라미터 (NEW)
    luma: LumaParams | None = None
    runway: RunwayParams | None = None
    pika: PikaParams | None = None
    kling: KlingParams | None = None
    veo: VeoParams | None = None

    # 오디오/텍스트 (NEW)
    audio: AudioSpec | None = None
    text_overlays: list[TextOverlay] = field(default_factory=list)

    # 전환 효과 (NEW)
    transition_in: str = ""
    transition_out: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = {
            "index": self.index,
            "duration_sec": self.duration_sec,
            "shot_type": self.shot_type,
            "script": self.script,
            "caption": self.caption,
            "background_prompt": self.background_prompt,
            "notes": self.notes,
        }
        # 서비스별 파라미터
        if self.luma:
            result["luma"] = self.luma.to_dict()
        if self.runway:
            result["runway"] = self.runway.to_dict()
        if self.pika:
            result["pika"] = self.pika.to_dict()
        if self.kling:
            result["kling"] = self.kling.to_dict()
        if self.veo:
            result["veo"] = self.veo.to_dict()
        # 오디오/텍스트
        if self.audio:
            result["audio"] = self.audio.to_dict()
        if self.text_overlays:
            result["text_overlays"] = [t.to_dict() for t in self.text_overlays]
        # 전환 효과
        if self.transition_in:
            result["transition_in"] = self.transition_in
        if self.transition_out:
            result["transition_out"] = self.transition_out
        return result

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VideoShot:
        # 서비스별 파라미터 로드
        luma = LumaParams.from_dict(d["luma"]) if "luma" in d else None
        runway = RunwayParams.from_dict(d["runway"]) if "runway" in d else None
        pika = PikaParams.from_dict(d["pika"]) if "pika" in d else None
        kling = KlingParams.from_dict(d["kling"]) if "kling" in d else None
        veo = VeoParams.from_dict(d["veo"]) if "veo" in d else None

        # 오디오/텍스트 로드
        audio = AudioSpec.from_dict(d["audio"]) if "audio" in d else None
        text_overlays = [TextOverlay.from_dict(t) for t in d.get("text_overlays", [])]

        return cls(
            index=d["index"],
            duration_sec=d["duration_sec"],
            shot_type=d.get("shot_type", "main"),
            script=d.get("script", ""),
            caption=d.get("caption", ""),
            background_prompt=d.get("background_prompt", ""),
            notes=d.get("notes", {}),
            luma=luma,
            runway=runway,
            pika=pika,
            kling=kling,
            veo=veo,
            audio=audio,
            text_overlays=text_overlays,
            transition_in=d.get("transition_in", ""),
            transition_out=d.get("transition_out", ""),
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

    3축 유형 결정:
    - source (what): account_only | longform | pack | digest
    - intent (why): ad | explainer | brand | trend
    - weekly_context (when): WeeklySlot에서 주입 (별도 필드 없이 generator에서 처리)
    """

    id: str
    account: str
    intent: VideoIntent  # 3축 중 의도 (why)
    goal: str
    source: VideoSource
    brand_style: BrandStyle
    shots: list[VideoShot]
    target_services: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    duration_sec: int = 0  # 전체 목표 길이 (샷 합산으로 계산 가능)
    created_at: str = ""  # ISO 날짜 문자열

    # NEW: 품질 정보
    quality_score: float | None = None
    quality_issues: list[str] = field(default_factory=list)
    quality_suggestions: list[str] = field(default_factory=list)
    quality_warning: bool = False  # 최대 재시도 초과 시 True

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d")
        if self.duration_sec == 0 and self.shots:
            self.duration_sec = sum(s.duration_sec for s in self.shots)

    # ──────────────────────────────────────────────
    # 직렬화
    # ──────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "account": self.account,
            "intent": self.intent,
            "goal": self.goal,
            "source": self.source.to_dict(),
            "brand_style": self.brand_style.to_dict(),
            "target_services": self.target_services,
            "platforms": self.platforms,
            "duration_sec": self.duration_sec,
            "created_at": self.created_at,
            "shots": [s.to_dict() for s in self.shots],
        }
        # 품질 정보 (값이 있을 때만)
        if self.quality_score is not None:
            result["quality_score"] = self.quality_score
        if self.quality_issues:
            result["quality_issues"] = self.quality_issues
        if self.quality_suggestions:
            result["quality_suggestions"] = self.quality_suggestions
        if self.quality_warning:
            result["quality_warning"] = self.quality_warning
        return result

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VideoPlan:
        return cls(
            id=d["id"],
            account=d["account"],
            intent=d.get("intent", "ad"),  # 기본값: ad
            goal=d["goal"],
            source=VideoSource.from_dict(d.get("source", {"type": "account_only"})),
            brand_style=BrandStyle.from_dict(d.get("brand_style", {})),
            shots=[VideoShot.from_dict(s) for s in d.get("shots", [])],
            target_services=d.get("target_services", []),
            platforms=d.get("platforms", []),
            duration_sec=d.get("duration_sec", 0),
            created_at=d.get("created_at", ""),
            quality_score=d.get("quality_score"),
            quality_issues=d.get("quality_issues", []),
            quality_suggestions=d.get("quality_suggestions", []),
            quality_warning=d.get("quality_warning", False),
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
            f"**의도**: {self.intent}",
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
