"""
서비스/플랫폼 제약 정의

AI 동영상 서비스별 하드 제약과 플랫폼별 요구사항을 정의한다.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceConstraints:
    """서비스별 제약 사항"""

    max_duration_sec: int
    min_duration_sec: int
    supported_ratios: list[str]
    max_prompt_length: int
    supports_audio: bool
    supports_start_image: bool
    supports_end_image: bool


SERVICE_CONSTRAINTS = {
    "luma": ServiceConstraints(
        max_duration_sec=5,
        min_duration_sec=1,
        supported_ratios=["16:9", "9:16", "1:1"],
        max_prompt_length=500,
        supports_audio=False,
        supports_start_image=True,
        supports_end_image=True,
    ),
    "runway": ServiceConstraints(
        max_duration_sec=10,
        min_duration_sec=1,
        supported_ratios=["16:9", "9:16", "1:1", "4:3"],
        max_prompt_length=200,
        supports_audio=False,
        supports_start_image=True,
        supports_end_image=False,
    ),
    "pika": ServiceConstraints(
        max_duration_sec=5,
        min_duration_sec=1,
        supported_ratios=["16:9", "9:16", "1:1"],
        max_prompt_length=300,
        supports_audio=False,
        supports_start_image=True,
        supports_end_image=False,
    ),
    "kling": ServiceConstraints(
        max_duration_sec=15,
        min_duration_sec=1,
        supported_ratios=["16:9", "9:16"],
        max_prompt_length=400,
        supports_audio=False,
        supports_start_image=True,
        supports_end_image=True,
    ),
    "veo": ServiceConstraints(
        max_duration_sec=8,
        min_duration_sec=1,
        supported_ratios=["16:9", "9:16"],
        max_prompt_length=500,
        supports_audio=True,
        supports_start_image=True,
        supports_end_image=False,
    ),
}


@dataclass
class PlatformConstraints:
    """플랫폼별 제약 사항"""

    max_duration_sec: int
    recommended_duration_sec: int
    required_ratio: str
    max_file_size_mb: int


PLATFORM_CONSTRAINTS = {
    "instagram_reel": PlatformConstraints(
        max_duration_sec=90,
        recommended_duration_sec=30,
        required_ratio="9:16",
        max_file_size_mb=500,
    ),
    "youtube_short": PlatformConstraints(
        max_duration_sec=60,
        recommended_duration_sec=30,
        required_ratio="9:16",
        max_file_size_mb=256,
    ),
    "tiktok": PlatformConstraints(
        max_duration_sec=60,
        recommended_duration_sec=30,
        required_ratio="9:16",
        max_file_size_mb=287,
    ),
    "twitter_video": PlatformConstraints(
        max_duration_sec=140,
        recommended_duration_sec=45,
        required_ratio="16:9",
        max_file_size_mb=512,
    ),
    "linkedin_video": PlatformConstraints(
        max_duration_sec=600,
        recommended_duration_sec=60,
        required_ratio="16:9",
        max_file_size_mb=200,
    ),
}


# Intent별 필수 구조
INTENT_STRUCTURES: dict[str, dict[str, Any]] = {
    "ad": {
        "requires_cta": True,
        "recommended_shots": (3, 5),
        "recommended_duration": (15, 30),
    },
    "explainer": {
        "requires_intro": True,
        "recommended_shots": (5, 8),
        "recommended_duration": (45, 120),
    },
    "brand": {
        "recommended_shots": (3, 5),
        "recommended_duration": (15, 60),
    },
    "trend": {
        "recommended_shots": (3, 4),
        "recommended_duration": (15, 30),
    },
}


def get_service_constraints(service: str) -> ServiceConstraints | None:
    """서비스 제약 조회"""
    return SERVICE_CONSTRAINTS.get(service)


def get_platform_constraints(platform: str) -> PlatformConstraints | None:
    """플랫폼 제약 조회"""
    return PLATFORM_CONSTRAINTS.get(platform)


def get_intent_structure(intent: str) -> dict[str, Any] | None:
    """Intent 구조 조회"""
    return INTENT_STRUCTURES.get(intent)


def validate_service_ratio(service: str, ratio: str) -> bool:
    """서비스가 해당 비율을 지원하는지 확인"""
    constraints = get_service_constraints(service)
    if not constraints:
        return False
    return ratio in constraints.supported_ratios


def validate_platform_duration(platform: str, duration_sec: int) -> bool:
    """플랫폼 최대 길이 내인지 확인"""
    constraints = get_platform_constraints(platform)
    if not constraints:
        return True  # 알 수 없는 플랫폼은 통과
    return duration_sec <= constraints.max_duration_sec
