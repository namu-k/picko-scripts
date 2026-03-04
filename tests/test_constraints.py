"""
Tests for video/constraints.py
"""

from typing import Any

from picko.video.constraints import (
    INTENT_STRUCTURES,
    PLATFORM_CONSTRAINTS,
    SERVICE_CONSTRAINTS,
    get_intent_structure,
    get_platform_constraints,
    get_service_constraints,
    validate_platform_duration,
    validate_service_ratio,
)


class TestServiceConstraints:
    """ServiceConstraints dataclass 테스트"""

    def test_service_constraints_luma(self):
        c = SERVICE_CONSTRAINTS["luma"]
        assert c.max_duration_sec == 5
        assert c.min_duration_sec == 1
        assert "9:16" in c.supported_ratios
        assert "16:9" in c.supported_ratios
        assert c.supports_audio is False
        assert c.supports_start_image is True
        assert c.supports_end_image is True

    def test_service_constraints_runway(self):
        c = SERVICE_CONSTRAINTS["runway"]
        assert c.max_duration_sec == 10
        assert c.supports_end_image is False

    def test_service_constraints_pika(self):
        c = SERVICE_CONSTRAINTS["pika"]
        assert c.max_duration_sec == 5
        assert c.max_prompt_length == 300

    def test_service_constraints_kling(self):
        c = SERVICE_CONSTRAINTS["kling"]
        assert c.max_duration_sec == 15
        assert c.supports_end_image is True

    def test_service_constraints_veo(self):
        c = SERVICE_CONSTRAINTS["veo"]
        assert c.supports_audio is True
        assert c.max_duration_sec == 8

    def test_all_services_have_constraints(self):
        expected_services = ["luma", "runway", "pika", "kling", "veo"]
        for service in expected_services:
            assert service in SERVICE_CONSTRAINTS


class TestPlatformConstraints:
    """PlatformConstraints dataclass 테스트"""

    def test_platform_constraints_instagram_reel(self):
        c = PLATFORM_CONSTRAINTS["instagram_reel"]
        assert c.max_duration_sec == 90
        assert c.required_ratio == "9:16"
        assert c.max_file_size_mb == 500

    def test_platform_constraints_youtube_short(self):
        c = PLATFORM_CONSTRAINTS["youtube_short"]
        assert c.max_duration_sec == 60
        assert c.required_ratio == "9:16"

    def test_platform_constraints_tiktok(self):
        c = PLATFORM_CONSTRAINTS["tiktok"]
        assert c.max_duration_sec == 60
        assert c.required_ratio == "9:16"

    def test_platform_constraints_twitter_video(self):
        c = PLATFORM_CONSTRAINTS["twitter_video"]
        assert c.max_duration_sec == 140
        assert c.required_ratio == "16:9"

    def test_all_platforms_have_constraints(self):
        expected_platforms = ["instagram_reel", "youtube_short", "tiktok", "twitter_video", "linkedin_video"]
        for platform in expected_platforms:
            assert platform in PLATFORM_CONSTRAINTS


class TestIntentStructures:
    """INTENT_STRUCTURES 테스트"""

    def test_intent_structure_ad(self):
        s: dict[str, Any] = INTENT_STRUCTURES["ad"]
        assert s["requires_cta"] is True
        assert s["recommended_shots"] == (3, 5)
        assert s["recommended_duration"] == (15, 30)

    def test_intent_structure_explainer(self):
        s: dict[str, Any] = INTENT_STRUCTURES["explainer"]
        assert s["requires_intro"] is True
        assert s["recommended_shots"] == (5, 8)

    def test_intent_structure_brand(self):
        s: dict[str, Any] = INTENT_STRUCTURES["brand"]
        assert "recommended_shots" in s

    def test_intent_structure_trend(self):
        s: dict[str, Any] = INTENT_STRUCTURES["trend"]
        assert s["recommended_shots"] == (3, 4)

    def test_all_intents_have_structures(self):
        expected_intents = ["ad", "explainer", "brand", "trend"]
        for intent in expected_intents:
            assert intent in INTENT_STRUCTURES


class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_get_service_constraints_existing(self):
        c = get_service_constraints("luma")
        assert c is not None
        assert c.max_duration_sec == 5

    def test_get_service_constraints_nonexisting(self):
        c = get_service_constraints("unknown_service")
        assert c is None

    def test_get_platform_constraints_existing(self):
        c = get_platform_constraints("instagram_reel")
        assert c is not None
        assert c.required_ratio == "9:16"

    def test_get_platform_constraints_nonexisting(self):
        c = get_platform_constraints("unknown_platform")
        assert c is None

    def test_get_intent_structure_existing(self):
        s = get_intent_structure("ad")
        assert s is not None
        assert s["requires_cta"] is True

    def test_get_intent_structure_nonexisting(self):
        s = get_intent_structure("unknown_intent")
        assert s is None


class TestValidateFunctions:
    """검증 함수 테스트"""

    def test_validate_service_ratio_supported(self):
        assert validate_service_ratio("luma", "9:16") is True
        assert validate_service_ratio("luma", "16:9") is True
        assert validate_service_ratio("runway", "4:3") is True

    def test_validate_service_ratio_unsupported(self):
        assert validate_service_ratio("luma", "4:3") is False
        assert validate_service_ratio("kling", "1:1") is False

    def test_validate_service_ratio_unknown_service(self):
        assert validate_service_ratio("unknown", "9:16") is False

    def test_validate_platform_duration_within_limit(self):
        assert validate_platform_duration("instagram_reel", 30) is True
        assert validate_platform_duration("instagram_reel", 90) is True
        assert validate_platform_duration("youtube_short", 60) is True

    def test_validate_platform_duration_exceeds_limit(self):
        assert validate_platform_duration("instagram_reel", 91) is False
        assert validate_platform_duration("youtube_short", 61) is False
        assert validate_platform_duration("tiktok", 120) is False

    def test_validate_platform_duration_unknown_platform(self):
        # 알 수 없는 플랫폼은 통과
        assert validate_platform_duration("unknown", 1000) is True
