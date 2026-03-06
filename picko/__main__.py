"""Picko CLI dispatcher."""

import argparse
import json
import logging
from pathlib import Path

from picko.account_config_loader import load_account_config
from picko.config import PROJECT_ROOT, get_config
from picko.video.generator import VideoGenerator

logger = logging.getLogger(__name__)


def prompt(message: str) -> str:
    """Prompt helper for interactive account commands."""
    return input(f"{message}: ").strip()


def multiselect(message: str, options: list[str]) -> list[str]:
    """Simple comma-separated multi-select helper."""
    print(message)
    print(f"Options: {', '.join(options)}")
    response = input("Enter selections (comma-separated): ").strip()
    selected = [item.strip() for item in response.split(",") if item.strip()]
    return [item for item in selected if item in options]


def cmd_account_init(dry_run: bool = False) -> None:
    """Create a new account profile interactively."""
    from picko.account_inferrer import AccountInferrer, AccountSeed
    from picko.llm_client import get_writer_client

    print("\n=== New Account Setup ===\n")

    account_id = prompt("Account ID (english, underscore)")
    name = prompt("Account name")
    description = prompt("Description")
    target_audience_str = prompt("Target audience (comma-separated)")
    one_liner = prompt("One-liner (optional)")
    target_audience = [item.strip() for item in target_audience_str.split(",") if item.strip()]

    channels = multiselect(
        "Select channels",
        ["instagram", "tiktok", "twitter", "linkedin", "threads", "newsletter"],
    )

    if not channels:
        print("At least one channel is required.")
        return

    seed = AccountSeed(
        account_id=account_id,
        name=name,
        description=description,
        one_liner=one_liner,
        target_audience=target_audience,
        channels=channels,
    )

    output_dir = PROJECT_ROOT / "config" / "accounts" / account_id
    if dry_run:
        print("\n[DRY RUN] Would create:")
        print(f"  {output_dir / '_index.yml'}")
        print(f"  {output_dir / 'channels.yml'}")
        print(f"  {output_dir / 'identity.yml'}")
        print(f"  {output_dir / 'content.yml'} (AI inferred)")
        print(f"  {output_dir / 'scoring.yml'} (AI inferred)")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    print("\nInferring scoring/style config via AI...")
    inferrer = AccountInferrer(get_writer_client())
    inferrer.generate_account_files(seed, output_dir)

    print("\nDone!")
    print(f"  {output_dir / '_index.yml'}")
    print(f"  {output_dir / 'channels.yml'}")
    print(f"  {output_dir / 'identity.yml'}")
    print(f"  {output_dir / 'content.yml'}")
    print(f"  {output_dir / 'scoring.yml'}")
    print(f"\nRegenerate later: picko account regen all {account_id}")


def cmd_account_import(from_file: str | None, from_url: str | None, dry_run: bool = False) -> None:
    """Placeholder: import account from external source."""
    _ = (from_file, from_url, dry_run)
    print("Import is not implemented yet.")


def cmd_account_regen(what: str, account_id: str) -> None:
    """Regenerate AI-derived account files."""
    from picko.account_inferrer import AccountInferrer, AccountSeed
    from picko.llm_client import get_writer_client

    account_dir = PROJECT_ROOT / "config" / "accounts" / account_id
    config = get_config()
    loaded = config.get_account(account_id)
    if not loaded:
        print(f"Account not found: {account_id}")
        return

    channels_raw = loaded.get("channels", {})
    if isinstance(channels_raw, dict):
        channels = list(channels_raw.keys())
    elif isinstance(channels_raw, list):
        channels = [str(item) for item in channels_raw]
    else:
        channels = []

    seed = AccountSeed(
        account_id=str(loaded.get("account_id", account_id)),
        name=str(loaded.get("name", "")),
        description=str(loaded.get("description", "")),
        one_liner=str(loaded.get("one_liner", "")),
        target_audience=(
            loaded.get("target_audience", []) if isinstance(loaded.get("target_audience", []), list) else []
        ),
        channels=channels,
    )

    inferrer = AccountInferrer(get_writer_client())
    if what in ("scoring", "all"):
        scoring = inferrer.infer_scoring(seed)
        inferrer._write_yaml(account_dir / "scoring.yml", scoring)
        print("Regenerated scoring.yml")

    if what in ("style", "all"):
        style = inferrer.infer_style(seed)
        content = inferrer._build_content_yml(style)
        inferrer._write_yaml(account_dir / "content.yml", content)
        print("Regenerated content.yml from style inference")


def cmd_account_list() -> None:
    """List registered accounts."""
    accounts_dir = PROJECT_ROOT / "config" / "accounts"
    if not accounts_dir.exists():
        print("No accounts directory found.")
        return

    config = get_config()
    print("\nRegistered accounts:")

    for account_dir in sorted(accounts_dir.iterdir()):
        if account_dir.is_dir():
            loaded = config.get_account(account_dir.name)
            if loaded:
                print(f"  {account_dir.name}: {loaded.get('name', 'Unknown')} (dir)")

    for account_file in sorted(accounts_dir.glob("*.yml")):
        if account_file.name.endswith(".bak"):
            continue
        loaded = load_account_config(accounts_dir, account_file.stem)
        if loaded:
            print(f"  {account_file.stem}: {loaded.get('name', 'Unknown')} (legacy file)")


def cmd_account_show(account_id: str) -> None:
    """Show merged account profile summary."""
    config = get_config()
    account = config.get_account(account_id)
    if not account:
        print(f"Account not found: {account_id}")
        return

    print(f"\n=== {account_id} ===")
    print(f"Name: {account.get('name', 'N/A')}")
    print(f"Description: {account.get('description', 'N/A')}")

    audience = account.get("target_audience", [])
    if isinstance(audience, list):
        print(f"Audience: {', '.join(str(a) for a in audience)}")

    channels = account.get("channels", {})
    if isinstance(channels, dict):
        print(f"Channels: {', '.join(channels.keys())}")
    elif isinstance(channels, list):
        print(f"Channels: {', '.join(str(ch) for ch in channels)}")

    interests = account.get("interests", {})
    if isinstance(interests, dict):
        primary = interests.get("primary", [])
        if isinstance(primary, list):
            print(f"Primary interests: {', '.join(str(item) for item in primary)}")

    visual = account.get("visual_settings", {})
    if isinstance(visual, dict):
        preset = visual.get("default_layout_preset")
        if preset:
            print(f"Layout preset: {preset}")


def _run_account(args: argparse.Namespace) -> None:
    """Run account subcommands."""
    if args.account_command == "init":
        cmd_account_init(dry_run=args.dry_run)
    elif args.account_command == "import":
        cmd_account_import(args.from_file, args.from_url, args.dry_run)
    elif args.account_command == "regen":
        cmd_account_regen(args.what, args.account_id)
    elif args.account_command == "list":
        cmd_account_list()
    elif args.account_command == "show":
        cmd_account_show(args.account_id)


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="picko", description="Picko CLI")
    sub = parser.add_subparsers(dest="command", required=True)

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
    vp.add_argument("-c", "--content", default=None, help="콘텐츠 ID")
    vp.add_argument("-w", "--week-of", default=None, help="주간 슬롯 시작일 (YYYY-MM-DD)")
    vp.add_argument("-s", "--service", nargs="+", default=["luma"], help="대상 서비스 (복수 가능)")
    vp.add_argument(
        "-p",
        "--platform",
        nargs="+",
        default=["instagram_reel"],
        help="대상 플랫폼폼 (복수 가능)",
    )
    vp.add_argument("-l", "--lang", default="ko", help="출력 언어 (default: ko)")
    vp.add_argument("--dry-run", action="store_true", help="저장 없이 stdout 출력")
    vp.add_argument("--no-validate", action="store_true", help="품질 검증 건너뛰기")
    vp.add_argument(
        "-o",
        "--output",
        default=None,
        help="출력 디렉토리 (default: <vault>/Content/Video/)",
    )

    ap = sub.add_parser("account", help="계정 관리")
    account_sub = ap.add_subparsers(dest="account_command", required=True)

    init_p = account_sub.add_parser("init", help="새 계정 생성 (interactive)")
    init_p.add_argument("--dry-run", action="store_true", help="저장 없이 미리보기")

    import_p = account_sub.add_parser("import", help="기존 문서/URL에서 계정 생성")
    import_p.add_argument("--from-file", help="분석할 파일 경로")
    import_p.add_argument("--from-url", help="분석할 URL")
    import_p.add_argument("--dry-run", action="store_true")

    regen_p = account_sub.add_parser("regen", help="AI 생성 파일 재생성")
    regen_p.add_argument("what", choices=["scoring", "style", "all"], help="재생성 대상")
    regen_p.add_argument("account_id", help="계정 ID")

    account_sub.add_parser("list", help="등록된 계정 목록")

    show_p = account_sub.add_parser("show", help="계정 정보 표시")
    show_p.add_argument("account_id", help="계정 ID")

    return parser


def _run_video(args: argparse.Namespace) -> None:
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

    if output_dir is None:
        vault_root = getattr(config, "vault_root", Path("mock_vault"))
        output_dir = Path(vault_root) / "Content" / "Video"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{plan.id}.json"
    plan.save(json_path)
    logger.info(f"저장 완료: {plan.id}")

    md_content = plan.to_markdown()
    md_path = output_dir / f"{plan.id}.md"
    md_path.write_text(md_content, encoding="utf-8")
    logger.info(f"마크다운 저장 완료: {md_path}")

    print(f"\n[picko video] 저장 완료: {plan.id}")
    print(f"  품질 점수: {plan.quality_score}")
    final_evaluation = getattr(plan, "final_evaluation", None)
    if isinstance(final_evaluation, dict) and final_evaluation:
        print(f"  최종 평가: {final_evaluation.get('verdict')} " f"({final_evaluation.get('overall_score')})")
    if plan.quality_issues:
        print(f"  이슈: {plan.quality_issues}")
    if plan.quality_suggestions:
        print(f"  제안: {plan.quality_suggestions}")


def main(argv: list[str] | None = None) -> None:
    parser = _make_parser()
    args = parser.parse_args(argv)
    if args.command == "video":
        _run_video(args)
    elif args.command == "account":
        _run_account(args)


if __name__ == "__main__":
    main()
