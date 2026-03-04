"""
Tests for picko/__main__.py CLI dispatcher
"""

from unittest.mock import patch

import pytest

from picko.__main__ import main
from picko.video_plan import BrandStyle, LumaParams, VideoPlan, VideoShot, VideoSource


def make_mock_plan():
    """테스트용 VideoPlan 생성"""
    plan = VideoPlan(
        id="video_test_001",
        account="test_account",
        intent="ad",
        goal="테스트 목표",
        source=VideoSource(type="account_only"),
        brand_style=BrandStyle(tone="test"),
        shots=[
            VideoShot(
                index=1,
                duration_sec=5,
                shot_type="intro",
                script="인트로",
                caption="",
                luma=LumaParams(
                    prompt="test prompt",
                    aspect_ratio="9:16",
                ),
            ),
        ],
        target_services=["luma"],
        platforms=["instagram_reel"],
    )
    plan.quality_score = 85
    return plan


class TestMainCLI:
    """__main__.py CLI 테스트"""

    def test_video_dry_run(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out
        assert "test_account" in captured.out

    def test_video_with_account(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--account", "socialbuilders", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out

    def test_video_with_intent(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--intent", "explainer", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out

        # VideoGenerator에 intent이 explainer로 전달되었는지 확인
        call_kwargs = MockGen.call_args
        assert call_kwargs[1]["intent"] == "explainer"

    def test_video_with_content(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--content", "lf_2026-03-01_001", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out
        # content_id가 전달되었는지 확인
        call_kwargs = MockGen.call_args
        assert call_kwargs[1]["content_id"] == "lf_2026-03-01_001"

    def test_video_with_week_of(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--week-of", "2026-03-03", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out
        # week_of가 전달되었는지 확인
        call_kwargs = MockGen.call_args
        assert call_kwargs[1]["week_of"] == "2026-03-03"

    def test_video_with_service(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--service", "runway", "pika", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out
        # services가 전달되었는지 확인
        call_kwargs = MockGen.call_args
        assert "runway" in call_kwargs[1]["services"]
        assert "pika" in call_kwargs[1]["services"]

    def test_video_with_platform(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--platform", "youtube_short", "tiktok", "--dry-run"])

        captured = capsys.readouterr()
        assert "video_" in captured.out
        # platforms가 전달되었는지 확인
        call_kwargs = MockGen.call_args
        assert "youtube_short" in call_kwargs[1]["platforms"]
        assert "tiktok" in call_kwargs[1]["platforms"]

    def test_video_help(self, capsys):
        with pytest.raises(SystemExit):
            main(["video", "--help"])
        captured = capsys.readouterr()
        # help text should contain relevant keywords
        assert "video" in captured.out.lower()

    def test_no_validate_flag(self, capsys):
        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = make_mock_plan()

            main(["video", "--dry-run", "--no-validate"])

        # generate() 호출 시 validate=False로 전달되었는지 확인
        gen_call_args = instance.generate.call_args
        assert gen_call_args.kwargs["validate"] is False

    def test_video_output_shows_quality_info(self, capsys):
        plan = make_mock_plan()
        plan.quality_score = 75
        plan.quality_issues = ["테스트 이슈"]
        plan.quality_suggestions = ["테스트 제안"]

        with patch("picko.__main__.VideoGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate.return_value = plan

            main(["video", "--dry-run"])

        captured = capsys.readouterr()
        assert "75" in captured.out

        assert "테스트 이슈" in captured.out
        assert "테스트 제안" in captured.out
