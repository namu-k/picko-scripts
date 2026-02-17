"""
Engagement Sync 스크립트
플랫폼 API에서 성과 메트릭을 수집하고 발행 로그를 자동 업데이트
"""

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from picko.config import get_config
from picko.logger import setup_logger
from picko.vault_io import VaultIO

# Optional dependency: tweepy (Twitter API)
try:
    import tweepy  # type: ignore[import-not-found,import-untyped]
except ImportError:
    tweepy = None  # type: ignore[misc,assignment]

logger = setup_logger("engagement_sync")


@dataclass
class EngagementMetrics:
    """성과 메트릭"""

    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    impressions: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "clicks": self.clicks,
            "impressions": self.impressions,
        }


@dataclass
class SyncResult:
    """동기화 결과"""

    log_path: str
    platform: str
    success: bool
    metrics: EngagementMetrics | None = None
    error: str = ""
    synced_at: str = ""


class EngagementSyncer:
    """성과 메트릭 동기화 관리자"""

    SUPPORTED_PLATFORMS = [
        "twitter",
        "linkedin",
        "newsletter",
        "blog",
        "instagram",
        "youtube",
    ]

    def __init__(self):
        self.config = get_config()
        self.vault = VaultIO()
        self.logs_path = "Logs/Publish"

        # Twitter API 클라이언트 (lazy initialization)
        self._twitter_client = None

        logger.info("EngagementSyncer initialized")

    def sync_all(self, days: int = 7, platforms: list[str] | None = None, dry_run: bool = False) -> list[SyncResult]:
        """
        모든 발행 로그의 성과 메트릭 동기화

        Args:
            days: 최근 N일의 로그만 동기화
            platforms: 대상 플랫폼 (None이면 전체)
            dry_run: 실제 업데이트 없이 시뮬레이션

        Returns:
            동기화 결과 리스트
        """
        logger.info(f"Starting engagement sync (last {days} days)")

        if platforms:
            platforms = [p for p in platforms if p in self.SUPPORTED_PLATFORMS]
        else:
            platforms = self.SUPPORTED_PLATFORMS

        results = []
        cutoff_date = datetime.now() - timedelta(days=days)

        # 발행 로그 목록 조회
        logs = self._get_published_logs(cutoff_date)

        for log_entry in logs:
            log_path = log_entry["path"]
            platform = log_entry.get("platform", "unknown")

            if platform not in platforms:
                continue

            try:
                metrics = self._fetch_metrics(log_entry, platform)

                result = SyncResult(
                    log_path=str(log_path),
                    platform=platform,
                    success=metrics is not None,
                    metrics=metrics,
                    synced_at=datetime.now().isoformat(),
                )

                if metrics and not dry_run:
                    self._update_log_metrics(log_path, metrics)
                    logger.info(f"Updated metrics: {log_path}")

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to sync {log_path}: {e}")
                results.append(
                    SyncResult(
                        log_path=str(log_path),
                        platform=platform,
                        success=False,
                        error=str(e),
                        synced_at=datetime.now().isoformat(),
                    )
                )

        return results

    def sync_single(self, log_path: str, dry_run: bool = False) -> SyncResult:
        """
        단일 발행 로그 동기화

        Args:
            log_path: 발행 로그 경로
            dry_run: 실제 업데이트 없이 시뮬레이션

        Returns:
            동기화 결과
        """
        logger.info(f"Syncing single log: {log_path}")

        try:
            meta, _ = self.vault.read_note(log_path)
            platform = meta.get("platform", "unknown")

            if platform not in self.SUPPORTED_PLATFORMS:
                return SyncResult(
                    log_path=log_path,
                    platform=platform,
                    success=False,
                    error=f"Unsupported platform: {platform}",
                )

            metrics = self._fetch_metrics(meta, platform)

            if metrics and not dry_run:
                self._update_log_metrics(log_path, metrics)

            return SyncResult(
                log_path=log_path,
                platform=platform,
                success=metrics is not None,
                metrics=metrics,
                synced_at=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(f"Failed to sync {log_path}: {e}")
            return SyncResult(log_path=log_path, platform="unknown", success=False, error=str(e))

    def _get_published_logs(self, since: datetime) -> list[dict[str, Any]]:
        """발행 완료된 로그 조회"""
        logs = []
        notes = self.vault.list_notes(self.logs_path)

        for note_path in notes:
            try:
                meta = self.vault.read_frontmatter(note_path)

                if meta.get("status") != "published":
                    continue

                published_at = meta.get("published_at")
                if published_at:
                    pub_date = datetime.fromisoformat(published_at)
                    if pub_date >= since:
                        logs.append({"path": str(note_path), **meta})

            except Exception as e:
                logger.warning(f"Error reading {note_path}: {e}")

        return logs

    def _fetch_metrics(self, log_entry: dict[str, Any], platform: str) -> EngagementMetrics | None:
        """
        플랫폼 API에서 메트릭 가져오기

        Args:
            log_entry: 발행 로그 정보 (content_id, published_url 등)
            platform: 플랫폼명 (twitter, linkedin 등)

        Returns:
            EngagementMetrics 또는 None (API 미지원/실패 시)
        """
        content_id = log_entry.get("content_id", "")
        published_url = log_entry.get("published_url", "")

        logger.debug(f"Fetching metrics for {platform}: {content_id}")

        # 플랫폼별 API 호출
        if platform == "twitter":
            return self._fetch_twitter_metrics(content_id, published_url)
        elif platform == "linkedin":
            return self._fetch_linkedin_metrics(content_id, published_url)
        else:
            # 미구현 플랫폼은 빈 메트릭 반환
            logger.warning(f"Platform {platform} not yet implemented")
            return EngagementMetrics()

    def _get_twitter_client(self):
        """
        Twitter API 클라이언트 초기화 (lazy)

        Returns:
            tweepy.Client 또는 None (API 키 없거나 tweepy 미설치 시)
        """
        if self._twitter_client is not None:
            return self._twitter_client

        # tweepy가 설치되지 않은 경우
        if tweepy is None:
            logger.warning("tweepy not installed - run: pip install tweepy")
            return None

        try:
            # 환경변수에서 API 키 로드
            bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
            api_key = os.environ.get("TWITTER_API_KEY")
            api_secret = os.environ.get("TWITTER_API_SECRET")
            access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
            access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

            if not bearer_token:
                logger.warning("TWITTER_BEARER_TOKEN not set - Twitter metrics unavailable")
                return None

            # Twitter API v2 클라이언트 생성
            self._twitter_client = tweepy.Client(  # type: ignore[union-attr]
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )

            logger.info("Twitter API client initialized")
            return self._twitter_client

        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            return None

    def _fetch_twitter_metrics(self, content_id: str, url: str) -> EngagementMetrics:
        """
        Twitter API로 메트릭 수집

        Args:
            content_id: 트윗 ID (숫자 형태)
            url: 트윗 URL (백업용)

        Returns:
            EngagementMetrics (API 실패 시 빈 메트릭)
        """
        client = self._get_twitter_client()
        if not client:
            logger.warning("Twitter client not available")
            return EngagementMetrics()

        try:
            # URL에서 트윗 ID 추출 (없으면 content_id 사용)
            tweet_id = self._extract_tweet_id(url) or content_id

            if not tweet_id:
                logger.warning(f"No tweet ID found for {url}")
                return EngagementMetrics()

            # Twitter API v2로 트윗 메트릭 조회
            response = client.get_tweet(
                tweet_id,
                tweet_fields=["public_metrics", "non_public_metrics"],
            )

            if not response.data:
                logger.warning(f"No data returned for tweet {tweet_id}")
                return EngagementMetrics()

            metrics = response.data.public_metrics

            return EngagementMetrics(
                views=getattr(metrics, "impression_count", 0) or 0,
                likes=getattr(metrics, "like_count", 0) or 0,
                comments=getattr(metrics, "reply_count", 0) or 0,
                shares=(getattr(metrics, "retweet_count", 0) or 0) + (getattr(metrics, "quote_count", 0) or 0),
                clicks=0,  # Twitter API에서 제공하지 않음
                impressions=getattr(metrics, "impression_count", 0) or 0,
            )

        except Exception as e:
            logger.error(f"Failed to fetch Twitter metrics: {e}")
            return EngagementMetrics()

    def _extract_tweet_id(self, url: str) -> str | None:
        """
        트윗 URL에서 ID 추출

        Args:
            url: 트윗 URL (예: https://twitter.com/user/status/1234567890)

        Returns:
            트윗 ID 또는 None
        """
        import re

        if not url:
            return None

        # Twitter/X URL 패턴 매칭
        patterns = [
            r"twitter\.com/\w+/status/(\d+)",
            r"x\.com/\w+/status/(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _fetch_linkedin_metrics(self, content_id: str, url: str) -> EngagementMetrics:
        """
        LinkedIn API 메트릭 수집

        Args:
            content_id: LinkedIn 게시물 ID
            url: 게시물 URL

        Returns:
            EngagementMetrics (미구현 시 빈 메트릭)
        """
        # TODO: LinkedIn API 구현 필요
        # LinkedIn API는 OAuth 2.0 인증 필요
        logger.warning("LinkedIn API not yet implemented")
        return EngagementMetrics()

    def _update_log_metrics(self, log_path: str, metrics: EngagementMetrics):
        """발행 로그의 메트릭 업데이트"""
        updates = {
            "metrics": metrics.to_dict(),
            "metrics_synced_at": datetime.now().isoformat(),
        }
        self.vault.update_frontmatter(log_path, updates)


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="Engagement Sync - 플랫폼 성과 메트릭 동기화")

    parser.add_argument("--log", "-l", help="단일 로그 파일 동기화")
    parser.add_argument("--days", "-d", type=int, default=7, help="최근 N일의 로그 동기화 (기본: 7)")
    parser.add_argument(
        "--platforms",
        "-p",
        nargs="+",
        choices=EngagementSyncer.SUPPORTED_PLATFORMS,
        help="대상 플랫폼",
    )
    parser.add_argument("--dry-run", action="store_true", help="실제 업데이트 없이 시뮬레이션")

    args = parser.parse_args()

    syncer = EngagementSyncer()

    if args.log:
        # 단일 로그 동기화
        result = syncer.sync_single(args.log, dry_run=args.dry_run)

        if result.success:
            print(f"\n✅ 동기화 완료: {result.log_path}")
            if result.metrics:
                print(f"   Views: {result.metrics.views}")
                print(f"   Likes: {result.metrics.likes}")
                print(f"   Comments: {result.metrics.comments}")
        else:
            print(f"\n❌ 동기화 실패: {result.error}")

    else:
        # 전체 동기화
        results = syncer.sync_all(days=args.days, platforms=args.platforms, dry_run=args.dry_run)

        print(f"\n{'=' * 60}")
        print(f"Engagement Sync Results (Last {args.days} days)")
        print(f"{'=' * 60}\n")

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        for result in results:
            status = "✅" if result.success else "❌"
            print(f"{status} [{result.platform}] {Path(result.log_path).name}")
            if result.success and result.metrics:
                print(f"   V:{result.metrics.views} L:{result.metrics.likes} C:{result.metrics.comments}")
            elif not result.success:
                print(f"   Error: {result.error}")

        print(f"\n{'=' * 60}")
        print(f"Summary: {successful} succeeded, {failed} failed")
        if args.dry_run:
            print("(DRY RUN - No actual updates made)")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
