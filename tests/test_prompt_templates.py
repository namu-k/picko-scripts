"""
Tests for video/prompt_templates.py
"""

from picko.video.prompt_templates import (
    DEFAULT_NEGATIVE_PROMPTS,
    SERVICE_PROMPT_RULES,
    SERVICE_PROMPT_TEMPLATES,
    get_default_negative_prompt,
    get_prompt_rules,
    get_prompt_template,
    merge_service_templates,
)


class TestServicePromptTemplates:
    """SERVICE_PROMPT_TEMPLATES 테스트"""

    def test_luma_template_exists(self):
        template = get_prompt_template("luma")
        assert template != ""
        assert "Luma" in template
        assert "Few-shot" in template

    def test_runway_template_exists(self):
        template = get_prompt_template("runway")
        assert template != ""
        assert "Runway" in template
        assert "가이드" in template

    def test_pika_template_exists(self):
        template = get_prompt_template("pika")
        assert template != ""
        assert "Pika" in template
        assert "Pikaffect" in template

    def test_kling_template_exists(self):
        template = get_prompt_template("kling")
        assert template != ""
        assert "Kling" in template

    def test_veo_template_exists(self):
        template = get_prompt_template("veo")
        assert template != ""
        assert "Veo" in template
        assert "audio" in template.lower()

    def test_unknown_service_returns_empty(self):
        template = get_prompt_template("unknown_service")
        assert template == ""

    def test_all_services_have_templates(self):
        expected_services = ["luma", "runway", "pika", "kling", "veo"]
        for service in expected_services:
            assert service in SERVICE_PROMPT_TEMPLATES
            assert SERVICE_PROMPT_TEMPLATES[service] != ""


class TestDefaultNegativePrompts:
    """DEFAULT_NEGATIVE_PROMPTS 테스트"""

    def test_negative_prompt_luma(self):
        neg = get_default_negative_prompt("luma")
        assert "watermark" in neg
        assert "text" in neg
        assert "blurry" in neg

    def test_negative_prompt_runway(self):
        neg = get_default_negative_prompt("runway")
        assert "watermark" in neg
        assert "distortion" in neg

    def test_negative_prompt_pika(self):
        neg = get_default_negative_prompt("pika")
        assert "watermark" in neg
        assert "low resolution" in neg

    def test_negative_prompt_kling(self):
        neg = get_default_negative_prompt("kling")
        assert "watermark" in neg

    def test_negative_prompt_veo(self):
        neg = get_default_negative_prompt("veo")
        assert "watermark" in neg
        assert "low quality" in neg

    def test_unknown_service_returns_empty(self):
        neg = get_default_negative_prompt("unknown")
        assert neg == ""

    def test_all_services_have_negative_prompts(self):
        expected_services = ["luma", "runway", "pika", "kling", "veo"]
        for service in expected_services:
            assert service in DEFAULT_NEGATIVE_PROMPTS


class TestServicePromptRules:
    """SERVICE_PROMPT_RULES 테스트"""

    def test_luma_rules_exist(self):
        rules = get_prompt_rules("luma")
        assert "must" in rules
        assert "must_not" in rules
        assert "camera" in rules["must"]

    def test_runway_rules_exist(self):
        rules = get_prompt_rules("runway")
        assert "must" in rules
        assert "must_not" in rules
        assert "add a" in rules["must_not"]

    def test_pika_rules_exist(self):
        rules = get_prompt_rules("pika")
        assert "must" in rules
        assert "subject" in rules["must"]

    def test_kling_rules_exist(self):
        rules = get_prompt_rules("kling")
        assert "camera" in rules["must"]

    def test_veo_rules_exist(self):
        rules = get_prompt_rules("veo")
        assert "audio mood" in rules["must"]

    def test_unknown_service_returns_empty(self):
        rules = get_prompt_rules("unknown")
        assert rules == {"must": [], "must_not": []}

    def test_all_services_have_rules(self):
        expected_services = ["luma", "runway", "pika", "kling", "veo"]
        for service in expected_services:
            assert service in SERVICE_PROMPT_RULES
            rules = SERVICE_PROMPT_RULES[service]
            assert "must" in rules
            assert "must_not" in rules


class TestMergeServiceTemplates:
    """merge_service_templates 테스트"""

    def test_merge_single_service(self):
        merged = merge_service_templates(["luma"])
        assert "Luma" in merged

    def test_merge_multiple_services(self):
        merged = merge_service_templates(["luma", "runway"])
        assert "Luma" in merged
        assert "Runway" in merged

    def test_merge_all_services(self):
        merged = merge_service_templates(["luma", "runway", "pika", "kling", "veo"])
        assert "Luma" in merged
        assert "Runway" in merged
        assert "Pika" in merged
        assert "Kling" in merged
        assert "Veo" in merged

    def test_merge_empty_list(self):
        merged = merge_service_templates([])
        assert merged == ""

    def test_merge_unknown_service_ignored(self):
        merged = merge_service_templates(["luma", "unknown"])
        assert "Luma" in merged
        # unknown은 빈 문자열이므로 포함되지 않음


class TestTemplateContent:
    """템플릿 내용 검증"""

    def test_luma_template_has_camera_motion_guidance(self):
        template = get_prompt_template("luma")
        assert "카메라" in template.lower() or "camera" in template.lower()

    def test_runway_template_has_positive_instruction_guidance(self):
        template = get_prompt_template("runway")
        assert "negative prompt" in template.lower()

    def test_pika_template_has_pikaffect_examples(self):
        template = get_prompt_template("pika")
        assert "Levitate" in template

    def test_veo_template_has_audio_guidance(self):
        template = get_prompt_template("veo")
        assert "오디오" in template or "audio" in template.lower()

    def test_runway_template_includes_reference_image_url_field(self):
        template = get_prompt_template("runway")
        assert "reference_image_url" in template
