"""Picko CLI dispatcher"""

import argparse
import json
import logging
from pathlib import Path

from picko.config import get_config
from picko.video.generator import VideoGenerator

logger = logging.getLogger(__name__)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="picko", description="Picko CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # video 서브커맨드
    vp = sub.add_parser("video", help="AI 영상 기획서 생성")
    vp.add_argument(
        "-a",
        "--account",
        default=None,
        help="계정 ID (default: config.yml의 default_account)",
    )
    vp.add_argument(
        "-i",
        "--intent",
        default="ad",
        choices=["ad", "explainer", "brand", "trend"],
        help="영상 목적 (default: ad)",
    )
    vp.add_argument(
        "-c",
        "--content",
        default=None,
        help="콘텐츠 ID (longform 파일명에서 lf_ 접두어 제 content_id)",
    )
    vp.add_argument(
        "-w",
        "--week-of",
        default=None,
        help="주간 슬롯 시작일 (YYYY-MM-DD)",
    )
    vp.add_argument(
        "-s",
        "--service",
        nargs="+",
        default=["luma"],
        help="대상 서비스 (복수 가능)",
    )
    vp.add_argument(
        "-p",
        "--platform",
        nargs="+",
        default=["instagram_reel"],
        help="대상 플랫폼폼 (복수 가능)",
    )
    vp.add_argument(
        "-l",
        "--lang",
        default="ko",
        help="출력 언어 (default: ko)",
    )
    vp.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 stdout 출력",
    )
    vp.add_argument(
        "--no-validate",
        action="store_true",
        help="품질 검증 건너뛰기",
    )
    vp.add_argument(
        "-o",
        "--output",
        default=None,
        help="출력 디렉토리 (default: <vault>/Content/Video/)",
    )
    return parser


def _run_video(args) -> None:
    """video 서브커맨드 실행"""
    config = get_config()
    account = args.account or getattr(config, "default_account", "socialbuilders")
    output_dir = Path(args.output) if args.output else None

    gen = VideoGenerator(
        account_id=account,
        services=args.service,
        platforms=args.platform,
        intent=args.intent,
        content_id=args.content or "",
        week_of=args.week_of or "",
        lang=args.lang,
    )
    plan = gen.generate(validate=not args.no_validate)
    if args.dry_run:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        return
    # 저장 로직
    if output_dir is None:
        # 기본 저장 경로: vault/Content/Video/
        vault_root = getattr(config, "vault_root", Path("mock_vault"))
        output_dir = Path(vault_root) / "Content" / "Video"
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON 저장
    json_path = output_dir / f"{plan.id}.json"
    plan.save(json_path)
    logger.info(f"저장 완료: {plan.id}")

    # 마크다운 저장 (Vault용)
    md_content = plan.to_markdown()
    md_path = output_dir / f"{plan.id}.md"
    md_path.write_text(md_content, encoding="utf-8")
    logger.info(f"마크다운 저장 완료: {md_path}")

    print(f"\n[picko video] 저장 완료: {plan.id}")
    print(f"  품질 점수: {plan.quality_score}")
    if plan.quality_issues:
        print(f"  이슈: {plan.quality_issues}")
    if plan.quality_suggestions:
        print(f"  제안: {plan.quality_suggestions}")


def main(argv: list[str] | None = None):
    parser = _make_parser()
    args = parser.parse_args(argv)
    if args.command == "video":
        _run_video(args)


if __name__ == "__main__":
    main()
