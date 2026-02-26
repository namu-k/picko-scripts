import argparse
from datetime import datetime

from picko.publisher import PublishResult, TwitterPublisher
from picko.vault_io import VaultIO


def _extract_text(meta: dict[str, object], content: str) -> str:
    tweet_text = meta.get("tweet_text")
    if isinstance(tweet_text, str) and tweet_text.strip():
        return tweet_text.strip()
    return content.strip()


def _upsert_log(vault: VaultIO, log_path: str, text: str, result: PublishResult, dry_run: bool) -> None:
    now = datetime.now().isoformat()
    status = "dry_run" if dry_run else ("published" if result.success else "failed")

    updates = {
        "platform": "twitter",
        "status": status,
        "updated_at": now,
        "tweet_id": result.tweet_id,
        "published_url": result.tweet_url,
        "error": result.error,
    }
    if result.success:
        updates["published_at"] = now

    full_path = vault.get_path(log_path)
    if full_path.exists():
        vault.update_frontmatter(log_path, updates)
        return

    metadata = {
        "id": f"pub_twitter_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "type": "publish_log",
        "created_at": now,
        **updates,
    }
    body = f"# Twitter Publish Log\n\n## Text\n\n{text}\n"
    vault.write_note(log_path, body, metadata=metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish content to Twitter/X")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--content", help="Path to vault note for tweet content")
    source_group.add_argument("--text", help="Direct tweet text")
    parser.add_argument("--dry-run", action="store_true", help="Print tweet text without posting")
    parser.add_argument("--log", help="Publish log note path")
    parser.add_argument("--username", default="user", help="Twitter username for URL building")
    args = parser.parse_args(argv)

    if args.text:
        text = args.text.strip()
    else:
        vault = VaultIO()
        meta, content = vault.read_note(args.content)
        text = _extract_text(meta, content)

    if not text:
        print("No text to publish")
        return 1

    if args.dry_run:
        print("DRY RUN - tweet would be posted:")
        print(text)
        if args.log:
            vault = VaultIO()
            _upsert_log(vault, args.log, text, PublishResult(success=True), dry_run=True)
        return 0

    publisher = TwitterPublisher(username=args.username)
    result = publisher.publish(text)

    if args.log:
        vault = VaultIO()
        _upsert_log(vault, args.log, text, result, dry_run=False)

    if result.success:
        print(f"Published tweet: {result.tweet_id}")
        if result.tweet_url:
            print(f"URL: {result.tweet_url}")
        return 0

    print(f"Publish failed: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
