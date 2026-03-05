"""
Video Prompt Benchmark CLI

Usage:
    python -m scripts.video_prompt_benchmark --use-stub-llm
    python -m scripts.video_prompt_benchmark --services runway sora --scenario-id ad_dawn_call
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

import picko.video.generator as generator_module
from picko.logger import get_logger
from picko.video.generator import VideoGenerator
from picko.video.quality_scorer import VideoPlanScorer
from picko.video_plan import VideoIntent, VideoPlan

logger = get_logger("video_prompt_benchmark")

SUPPORTED_SERVICES: tuple[str, ...] = ("luma", "runway", "pika", "kling", "veo", "sora")
SUPPORTED_INTENTS: tuple[VideoIntent, ...] = ("ad", "explainer", "brand", "trend")


@dataclass
class BenchmarkScenario:
    id: str
    intent: VideoIntent
    title: str
    goal: str
    summary: str
    scene: str


class ScenarioVideoGenerator(VideoGenerator):
    """Scenario summary를 content source로 주입하는 VideoGenerator"""

    def __init__(self, scenario_summary: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._scenario_summary = scenario_summary

    def _load_content(self) -> str | None:
        return self._scenario_summary


def _parse_intent(raw: str, scenario_id: str) -> VideoIntent:
    if raw not in SUPPORTED_INTENTS:
        raise ValueError(
            f"Invalid intent in scenario '{scenario_id}': {raw}. " f"Supported: {', '.join(SUPPORTED_INTENTS)}"
        )
    return cast(VideoIntent, raw)


def load_scenarios(config_path: Path, scenario_ids: set[str] | None = None) -> list[BenchmarkScenario]:
    """YAML 시나리오 파일 로드"""
    if not config_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Scenario YAML must be a mapping: {config_path}")

    scenario_items = raw.get("scenarios", [])
    if not isinstance(scenario_items, list):
        raise ValueError(f"'scenarios' must be a list in: {config_path}")

    scenarios: list[BenchmarkScenario] = []
    for idx, item in enumerate(scenario_items):
        if not isinstance(item, dict):
            raise ValueError(f"Scenario index {idx} is not an object")

        scenario_id = str(item.get("id", "")).strip()
        if not scenario_id:
            raise ValueError(f"Scenario index {idx} missing 'id'")

        if scenario_ids and scenario_id not in scenario_ids:
            continue

        intent = _parse_intent(str(item.get("intent", "ad")), scenario_id)
        title = str(item.get("title", "")).strip()
        goal = str(item.get("goal", "")).strip()
        summary = str(item.get("summary", "")).strip()
        scene = str(item.get("scene", "")).strip()

        if not title:
            raise ValueError(f"Scenario '{scenario_id}' missing 'title'")
        if not goal:
            raise ValueError(f"Scenario '{scenario_id}' missing 'goal'")
        if not summary:
            raise ValueError(f"Scenario '{scenario_id}' missing 'summary'")
        if not scene:
            raise ValueError(f"Scenario '{scenario_id}' missing 'scene'")

        scenarios.append(
            BenchmarkScenario(
                id=scenario_id,
                intent=intent,
                title=title,
                goal=goal,
                summary=summary,
                scene=scene,
            )
        )

    return scenarios


def _build_service_params(service: str, base_scene: str, shot_type: str, shot_index: int) -> dict[str, Any]:
    scene = f"{base_scene}, shot {shot_index}, {shot_type}"

    if service == "luma":
        return {
            "prompt": f"{scene}, soft lighting, gentle shadows, camera slow push in, cinematic mood, 9:16 vertical",
            "negative_prompt": "watermark, logo, subtitle, blurry, distorted, low quality",
            "camera_motion": "slow_push_in" if shot_type != "cta" else "slow_zoom_in",
            "motion_intensity": 3,
            "style_preset": "cinematic",
        }

    if service == "runway":
        return {
            "prompt": (
                f"{scene}, professional commercial style, clear camera movement, " "detailed lighting, 9:16 vertical"
            ),
            "negative_prompt": "watermark, blur, noise, distortion",
            "motion": 6 if shot_type == "main" else 4,
            "camera_move": "orbit" if shot_type == "main" else "zoom_in",
            "seed": 42,
            "upscale": True,
        }

    if service == "pika":
        action_word = "floating" if shot_type == "intro" else "running"
        return {
            "prompt": f"{scene}, subject {action_word} dynamically, detailed action, clean composition, 9:16 vertical",
            "negative_prompt": "watermark, blurry, low resolution",
            "pikaffect": "Levitate" if shot_type == "intro" else "",
            "style_preset": "Realistic",
            "motion_intensity": 3,
        }

    if service == "kling":
        return {
            "prompt": f"{scene}, cinematic documentary style, camera pan right, 8 seconds feeling, 9:16 vertical",
            "negative_prompt": "watermark, blurry, distortion",
            "camera_motion": "pan_right" if shot_type != "cta" else "slow_push_in",
            "motion_intensity": 3,
            "style": "cinematic",
        }

    if service == "veo":
        return {
            "prompt": f"{scene}, visual detail with soft color contrast and calm atmosphere, 9:16 vertical",
            "negative_prompt": "watermark, low quality",
            "generate_audio": True,
            "audio_mood": "calm" if shot_type != "cta" else "dramatic",
            "style_preset": "cinematic",
        }

    if service == "sora":
        return {
            "prompt": (
                f"{scene}, golden hour lighting, contemplative mood, "
                "camera tracking shot, cinematic photorealistic, 9:16 vertical"
            ),
            "negative_prompt": "watermark, logo, subtitle, blurry, distorted",
            "style": "cinematic",
            "camera_motion": "tracking" if shot_type != "cta" else "slow_pan",
        }

    return {
        "prompt": f"{scene}, detailed cinematic visual, 9:16",
        "negative_prompt": "watermark, blurry",
    }


def _build_shots(intent: VideoIntent, service: str, base_scene: str) -> list[dict[str, Any]]:
    if intent == "explainer":
        shot_types = ["intro", "main", "main", "main", "cta"]
    else:
        shot_types = ["intro", "main", "cta"]

    shots: list[dict[str, Any]] = []
    for idx, shot_type in enumerate(shot_types, start=1):
        if intent == "explainer":
            duration = 5 if service == "luma" else 8
        else:
            duration = 5

        shots.append(
            {
                "index": idx,
                "duration_sec": duration,
                "shot_type": shot_type,
                "script": f"{shot_type} scene for {intent}",
                "caption": "지금 시작해" if shot_type == "cta" else "",
                "services": {
                    service: _build_service_params(service, base_scene, shot_type, idx),
                },
            }
        )
    return shots


class StubWriterClient:
    """외부 API 없이 벤치마크 재현성을 위한 스텁 LLM"""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def generate(self, prompt: str, **kwargs) -> str:
        del prompt, kwargs

        scenario: BenchmarkScenario = self._state["scenario"]
        service: str = self._state["service"]

        payload = {
            "goal": scenario.goal,
            "shots": _build_shots(scenario.intent, service, scenario.scene),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def _extract_first_prompt(plan: VideoPlan, service: str) -> tuple[str, str]:
    if not plan.shots:
        return "", ""

    params = getattr(plan.shots[0], service, None)
    if params is None:
        return "", ""

    prompt = getattr(params, "prompt", "")
    negative = getattr(params, "negative_prompt", "")
    return str(prompt), str(negative)


def run_benchmark(
    scenarios: list[BenchmarkScenario],
    services: list[str],
    account_id: str,
    platform: str,
    use_stub_llm: bool,
    include_plan: bool,
) -> dict[str, Any]:
    scorer = VideoPlanScorer()
    rows: list[dict[str, Any]] = []

    stub_state: dict[str, Any] = {"scenario": None, "service": None}
    original_get_writer_client = generator_module.get_writer_client

    if use_stub_llm:
        generator_module.get_writer_client = lambda: StubWriterClient(stub_state)

    try:
        for scenario in scenarios:
            for service in services:
                try:
                    if use_stub_llm:
                        stub_state["scenario"] = scenario
                        stub_state["service"] = service

                    generator = ScenarioVideoGenerator(
                        scenario_summary=scenario.summary,
                        account_id=account_id,
                        services=[service],
                        platforms=[platform],
                        intent=scenario.intent,
                        content_id=scenario.id,
                    )
                    plan = generator.generate(validate=True)
                    score = scorer.score(plan, [service])
                    first_prompt, first_negative = _extract_first_prompt(plan, service)

                    row: dict[str, Any] = {
                        "scenario_id": scenario.id,
                        "intent": scenario.intent,
                        "scenario_title": scenario.title,
                        "service": service,
                        "overall": score.overall,
                        "prompt_quality": score.dimensions.get("prompt_quality", 0),
                        "service_fit": score.dimensions.get("service_fit", 0),
                        "actionability": score.dimensions.get("actionability", 0),
                        "quality_warning": plan.quality_warning,
                        "issues_count": len(score.issues),
                        "issues": score.issues,
                        "suggestions": score.suggestions,
                        "first_shot_prompt": first_prompt,
                        "first_shot_negative_prompt": first_negative,
                        "final_verdict": (plan.final_evaluation.get("verdict", "") if plan.final_evaluation else ""),
                        "final_overall_score": (
                            plan.final_evaluation.get("overall_score") if plan.final_evaluation else None
                        ),
                        "final_issues": (plan.final_evaluation.get("issues", []) if plan.final_evaluation else []),
                    }
                    if include_plan:
                        row["plan"] = plan.to_dict()

                    rows.append(row)
                except Exception as exc:
                    logger.exception(f"Benchmark failed: scenario={scenario.id}, service={service}, error={exc}")
                    rows.append(
                        {
                            "scenario_id": scenario.id,
                            "intent": scenario.intent,
                            "scenario_title": scenario.title,
                            "service": service,
                            "error": str(exc),
                        }
                    )
    finally:
        generator_module.get_writer_client = original_get_writer_client

    service_averages: list[dict[str, Any]] = []
    for service in services:
        scores = [
            float(row["overall"]) for row in rows if row.get("service") == service and row.get("overall") is not None
        ]
        if scores:
            service_averages.append(
                {
                    "service": service,
                    "average_overall": round(statistics.fmean(scores), 1),
                    "sample_count": len(scores),
                }
            )

    service_averages.sort(key=lambda x: float(x["average_overall"]), reverse=True)

    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "scenario_count": len(scenarios),
            "service_count": len(services),
            "use_stub_llm": use_stub_llm,
            "account_id": account_id,
            "platform": platform,
        },
        "service_averages": service_averages,
        "rows": rows,
    }


def print_table(results: dict[str, Any]) -> None:
    rows = results.get("rows", [])
    print("| scenario | intent | service | overall | prompt_quality | service_fit | actionability | issues |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        if "error" in row:
            print(
                f"| {row.get('scenario_id', '')} | {row.get('intent', '')} | "
                f"{row.get('service', '')} | ERROR | - | - | - | - |"
            )
            continue

        print(
            f"| {row['scenario_id']} | {row['intent']} | {row['service']} | {float(row['overall']):.1f} | "
            f"{float(row['prompt_quality']):.1f} | {float(row['service_fit']):.1f} | "
            f"{float(row['actionability']):.1f} | {int(row['issues_count'])} |"
        )


def _resolve_output_path(output_arg: str) -> Path:
    output_path = Path(output_arg)
    if output_path.suffix.lower() == ".json":
        return output_path
    return output_path / "video_prompt_benchmark.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Video Prompt Benchmark - 서비스별 프롬프트 품질 비교")
    parser.add_argument(
        "--scenarios",
        "-c",
        type=str,
        default="config/benchmarks/video_prompt_scenarios.yml",
        help="시나리오 YAML 경로",
    )
    parser.add_argument(
        "--scenario-id",
        nargs="+",
        default=None,
        help="특정 scenario_id만 실행 (복수 가능)",
    )
    parser.add_argument(
        "--services",
        "-s",
        nargs="+",
        choices=list(SUPPORTED_SERVICES),
        default=list(SUPPORTED_SERVICES),
        help="대상 동영상 서비스 목록",
    )
    parser.add_argument("--account", "-a", default="socialbuilders", help="계정 ID")
    parser.add_argument("--platform", "-p", default="instagram_reel", help="대상 플랫폼")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="artifacts/video_prompt_benchmark.json",
        help="결과 JSON 파일 또는 출력 디렉토리",
    )
    parser.add_argument(
        "--use-stub-llm",
        action="store_true",
        help="외부 API 대신 재현 가능한 스텁 LLM 사용",
    )
    parser.add_argument(
        "--include-plan",
        action="store_true",
        help="결과 JSON에 plan 전체 구조 포함",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장 없이 콘솔 출력만 수행",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    scenario_ids = set(args.scenario_id) if args.scenario_id else None
    scenario_path = Path(args.scenarios)
    scenarios = load_scenarios(scenario_path, scenario_ids)

    if not scenarios:
        logger.error("No scenarios to run. Check --scenarios / --scenario-id")
        return 1

    logger.info(
        f"Running benchmark: scenarios={len(scenarios)}, services={len(args.services)}, "
        f"stub_llm={args.use_stub_llm}"
    )

    results = run_benchmark(
        scenarios=scenarios,
        services=args.services,
        account_id=args.account,
        platform=args.platform,
        use_stub_llm=args.use_stub_llm,
        include_plan=args.include_plan,
    )

    print_table(results)

    output_path = _resolve_output_path(args.output)
    if args.dry_run:
        logger.info(f"[DRY RUN] Skip writing output: {output_path}")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Saved benchmark results: {output_path}")

    error_count = sum(1 for row in results.get("rows", []) if row.get("error"))
    if error_count:
        logger.error(f"Benchmark completed with errors: {error_count}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
