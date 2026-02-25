"""
소스 자동 발견 스크립트
계정 프로필 기반으로 새로운 콘텐츠 소스 자동 발견
"""

import argparse
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx
import yaml

from picko.config import get_config
from picko.logger import setup_logger
from picko.source_manager import SourceManager, SourceMeta

logger = setup_logger("source_discovery")


@dataclass
class SourceCandidate:
    """발견된 소스 후보"""

    url: str
    title: str
    source_type: str  # "rss" | "newsletter"
    discovery_method: str  # "google_news" | "tavily" | "substack"
    keyword: str
    rss_url: str | None = None
    description: str = ""
    relevance_score: float = 0.0
    platform: str | None = None  # "substack" | "buttondown" | etc


@dataclass
class DiscoveryResult:
    """발견 실행 결과"""

    run_id: str
    account: str
    timestamp: str
    keywords_used: list[str] = field(default_factory=list)
    discovered: int = 0
    added_as_pending: int = 0
    already_known: int = 0
    below_threshold: int = 0
    errors: list[str] = field(default_factory=list)


class SourceDiscovery:
    """
    계정 프로필 기반 소스 자동 발견.
    발견 → 평가 → pending 후보로 sources.yml에 추가.
    """

    def __init__(self, account_id: str, source_manager: SourceManager | None = None):
        self.account_id = account_id
        self.config = get_config()

        # 소스 매니저 초기화
        if source_manager is None:
            sources_path = Path(self.config.sources_file)
            source_manager = SourceManager(sources_path)
        self.source_manager = source_manager

        # 계정 프로필 로드
        self.account_profile = self._load_account_profile()

        # Tavily API 설정
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        self.tavily_daily_count = 0
        self.tavily_daily_limit = 1000

        # 캐시
        self._google_news_cache: dict[str, list[SourceCandidate]] = {}

        # 로그 디렉토리
        self.discovery_dir = Path("data/discovery")
        self.discovery_dir.mkdir(parents=True, exist_ok=True)
        (self.discovery_dir / "logs").mkdir(parents=True, exist_ok=True)

        logger.info(f"SourceDiscovery initialized for account: {account_id}")

    def _load_account_profile(self) -> dict[str, Any]:
        """계정 프로필 로드"""
        accounts_dir = Path(self.config.accounts_dir)
        profile_path = accounts_dir / f"{self.account_id}.yml"

        if not profile_path.exists():
            logger.warning(f"Account profile not found: {profile_path}")
            return {}

        with open(profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _extract_keywords(self) -> list[str]:
        """계정 프로필에서 키워드 추출"""
        keywords = []

        # interests.primary
        interests = self.account_profile.get("interests", {})
        keywords.extend(interests.get("primary", []))

        # keywords.high_relevance
        account_keywords = self.account_profile.get("keywords", {})
        keywords.extend(account_keywords.get("high_relevance", []))

        # 중복 제거
        return list(set(keywords))

    def run(self, dry_run: bool = False, keywords: list[str] | None = None) -> DiscoveryResult:
        """
        전체 발견 파이프라인 실행

        Args:
            dry_run: 실제 저장 없이 시뮬레이션
            keywords: 특정 키워드만 사용 (기본: 전체)

        Returns:
            발견 결과
        """
        run_id = f"dr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = DiscoveryResult(
            run_id=run_id,
            account=self.account_id,
            timestamp=datetime.now().isoformat(),
        )

        # 키워드 추출
        if keywords:
            result.keywords_used = keywords
        else:
            result.keywords_used = self._extract_keywords()

        logger.info(f"Starting discovery with {len(result.keywords_used)} keywords")

        # 기존 소스 URL 수집 (중복 체크용)
        existing_urls = self.source_manager.get_urls()

        all_candidates: list[SourceCandidate] = []

        # 각 키워드로 검색
        for keyword in result.keywords_used:
            try:
                # Google News RSS
                google_candidates = self._search_google_news_rss(keyword)
                all_candidates.extend(google_candidates)
                logger.info(f"[Google News] {keyword}: {len(google_candidates)} candidates")

                # Tavily
                tavily_candidates = self._search_tavily(keyword)
                all_candidates.extend(tavily_candidates)
                logger.info(f"[Tavily] {keyword}: {len(tavily_candidates)} candidates")

                # Substack
                try:
                    substack_candidates = self._search_substack(keyword)
                    all_candidates.extend(substack_candidates)
                    logger.info(f"[Substack] {keyword}: {len(substack_candidates)} candidates")
                except Exception as e:
                    logger.warning(f"Substack search skipped for '{keyword}': {e}")

            except Exception as e:
                logger.warning(f"Discovery failed for keyword '{keyword}': {e}")
                result.errors.append(f"{keyword}: {str(e)}")

        # 중복 제거 (URL 기준)
        unique_candidates = self._dedupe_candidates(all_candidates, existing_urls)
        result.discovered = len(unique_candidates)
        result.already_known = len(all_candidates) - len(unique_candidates)

        logger.info(f"Found {result.discovered} unique candidates")

        # LLM 평가 (간소화된 버전 - 실제로는 LLM 호출)
        scored_candidates = self._evaluate_candidates(unique_candidates)

        # 임계값 필터링
        threshold = 0.6
        passed_candidates = [c for c in scored_candidates if c.relevance_score >= threshold]
        result.below_threshold = len(scored_candidates) - len(passed_candidates)

        # pending 상태로 추가
        if not dry_run:
            for candidate in passed_candidates:
                source = SourceMeta(
                    id=self._generate_source_id(candidate),
                    type=candidate.source_type,
                    url=candidate.url,
                    category="discovered",
                    enabled=False,
                    auto_discovered=True,
                    status="pending",
                    discovered_at=datetime.now().strftime("%Y-%m-%d"),
                    discovered_by="source_discovery",
                    discovery_keyword=candidate.keyword,
                    rss_url=candidate.rss_url,
                    platform=candidate.platform,
                )
                self.source_manager.add_candidate(source, status="pending")
                result.added_as_pending += 1
        else:
            result.added_as_pending = len(passed_candidates)
            logger.info(f"[DRY RUN] Would add {len(passed_candidates)} candidates")

        # 결과 저장
        self._save_result(result)

        logger.info(f"Discovery complete: {result}")
        return result

    def _search_google_news_rss(self, keyword: str) -> list[SourceCandidate]:
        """Google News RSS에서 키워드 관련 소스 도메인 추출"""
        # 캐시 확인
        if keyword in self._google_news_cache:
            return self._google_news_cache[keyword]

        candidates = []
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR"

        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            # 도메인 추출
            domains: set[str] = set()
            for entry in feed.entries[:20]:
                if entry.get("link"):
                    domain = urlparse(entry.link).netloc
                    if domain and not domain.endswith("google.com"):
                        domains.add(domain)

            # 각 도메인에서 RSS 피드 탐지
            for domain in domains:
                rss_url = self._probe_rss_url(domain)
                if rss_url:
                    candidates.append(
                        SourceCandidate(
                            url=f"https://{domain}",
                            title=domain,
                            source_type="rss",
                            discovery_method="google_news",
                            keyword=keyword,
                            rss_url=rss_url,
                        )
                    )

            # 캐시 저장
            self._google_news_cache[keyword] = candidates

        except Exception as e:
            logger.warning(f"Google News search failed for '{keyword}': {e}")

        return candidates

    def _search_tavily(self, keyword: str) -> list[SourceCandidate]:
        """Tavily API로 RSS 피드 검색"""
        if not self.tavily_api_key:
            logger.debug("Tavily API key not set, skipping")
            return []

        # 일일 한도 확인
        if self.tavily_daily_count >= self.tavily_daily_limit:
            logger.warning("Tavily daily limit reached")
            return []

        candidates = []
        url = "https://api.tavily.com/search"

        try:
            # 레이트 리밋
            time.sleep(1)

            with httpx.Client(timeout=10) as client:
                response = client.post(
                    url,
                    json={
                        "api_key": self.tavily_api_key,
                        "query": f"{keyword} RSS feed blog",
                        "max_results": 10,
                    },
                )
                response.raise_for_status()
                self.tavily_daily_count += 1

            data = response.json()
            results = data.get("results", [])

            for item in results:
                item_url = item.get("url", "")
                if not item_url:
                    continue

                domain = urlparse(item_url).netloc
                rss_url = self._probe_rss_url(domain)

                if rss_url:
                    candidates.append(
                        SourceCandidate(
                            url=item_url,
                            title=item.get("title", domain),
                            source_type="rss",
                            discovery_method="tavily",
                            keyword=keyword,
                            rss_url=rss_url,
                            description=item.get("content", ""),
                        )
                    )

        except Exception as e:
            logger.warning(f"Tavily search failed for '{keyword}': {e}")

        return candidates

    def _search_substack(self, keyword: str) -> list[SourceCandidate]:
        """Substack 뉴스레터 검색 (비공식 스크래핑)"""
        candidates = []
        url = f"https://substack.com/search/{keyword}"

        try:
            # 레이트 리밋: 5초 간격
            time.sleep(5)

            with httpx.Client(timeout=10) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()

            # 검색 결과에서 Substack 도메인 추출
            # 패턴: href="https://[username].substack.com"
            substack_pattern = r'href=["\']https://([a-zA-Z0-9-]+)\.substack\.com["\']'
            matches = re.findall(substack_pattern, response.text)

            # 중복 제거
            unique_substacks = set(matches)

            for username in unique_substacks:
                substack_url = f"https://{username}.substack.com"
                rss_url = f"https://{username}.substack.com/feed"

                # RSS 피드 존재 확인
                try:
                    with httpx.Client(timeout=5) as client:
                        rss_response = client.head(rss_url)
                        if rss_response.status_code == 200:
                            candidates.append(
                                SourceCandidate(
                                    url=substack_url,
                                    title=f"{username}.substack.com",
                                    source_type="newsletter",
                                    discovery_method="substack",
                                    keyword=keyword,
                                    rss_url=rss_url,
                                    platform="substack",
                                )
                            )
                except Exception:
                    pass

            logger.info(f"[Substack] Found {len(candidates)} newsletters for '{keyword}'")

        except Exception as e:
            logger.warning(f"Substack search failed for '{keyword}': {e}")

        return candidates

    def _probe_rss_url(self, domain: str) -> str | None:
        """도메인에서 RSS 피드 URL 자동 탐지"""
        # 일반적인 RSS 경로
        common_paths = ["/feed", "/rss", "/atom.xml", "/feed.xml", "/rss.xml"]

        base_url = f"https://{domain}"

        try:
            with httpx.Client(timeout=5) as client:
                # 먼저 HTML에서 RSS 링크 찾기
                try:
                    response = client.get(base_url)
                    if response.status_code == 200:
                        # link[type=application/rss+xml] 찾기
                        rss_match = re.search(
                            r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']',
                            response.text,
                            re.IGNORECASE,
                        )
                        if rss_match:
                            href = rss_match.group(1)
                            if href.startswith("/"):
                                return f"{base_url}{href}"
                            return href

                        # 대체 패턴
                        alt_match = re.search(
                            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/rss\+xml["\']',
                            response.text,
                            re.IGNORECASE,
                        )
                        if alt_match:
                            href = alt_match.group(1)
                            if href.startswith("/"):
                                return f"{base_url}{href}"
                            return href
                except Exception:
                    pass

                # 일반 경로 프로빙
                for path in common_paths:
                    try:
                        probe_url = f"{base_url}{path}"
                        probe_response = client.head(probe_url)
                        if probe_response.status_code == 200:
                            content_type = probe_response.headers.get("content-type", "")
                            if "xml" in content_type or "rss" in content_type:
                                return probe_url
                    except Exception:
                        continue

        except Exception as e:
            logger.debug(f"RSS probe failed for {domain}: {e}")

        return None

    def _dedupe_candidates(self, candidates: list[SourceCandidate], existing_urls: set[str]) -> list[SourceCandidate]:
        """중복 후보 제거"""
        unique = []
        seen_urls: set[str] = set()

        for candidate in candidates:
            url = candidate.rss_url or candidate.url

            # 이미 발견된 URL
            if url in seen_urls:
                continue

            # 기존 소스에 이미 있는 URL
            if url in existing_urls:
                continue

            seen_urls.add(url)
            unique.append(candidate)

        return unique

    def _evaluate_candidates(self, candidates: list[SourceCandidate]) -> list[SourceCandidate]:
        """후보 평가 (간소화된 버전)"""
        # 실제로는 LLM으로 관련성 평가
        # 여기서는 휴리스틱으로 기본 점수 부여

        for candidate in candidates:
            # 기본 점수
            score = 0.5

            # 키워드 매칭 보너스
            keyword = candidate.keyword.lower()
            title = candidate.title.lower()
            if keyword in title:
                score += 0.2

            # 신뢰 소스 보너스
            trusted_sources = self.account_profile.get("trusted_sources", [])
            for trusted in trusted_sources:
                if trusted.lower() in candidate.url.lower():
                    score += 0.3
                    break

            candidate.relevance_score = min(1.0, score)

        # 점수순 정렬
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        return candidates

    def _generate_source_id(self, candidate: SourceCandidate) -> str:
        """소스 ID 생성"""
        domain = urlparse(candidate.url).netloc
        # 특수문자 제거
        clean_domain = re.sub(r"[^a-zA-Z0-9]", "_", domain)
        return f"discovered_{clean_domain}"

    def _save_result(self, result: DiscoveryResult) -> None:
        """발견 결과 저장"""
        # latest_run.yml 저장
        latest_path = self.discovery_dir / "latest_run.yml"
        with open(latest_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "run_id": result.run_id,
                    "account": result.account,
                    "timestamp": result.timestamp,
                    "keywords_used": result.keywords_used,
                    "discovered": result.discovered,
                    "added_as_pending": result.added_as_pending,
                    "already_known": result.already_known,
                    "below_threshold": result.below_threshold,
                },
                f,
                allow_unicode=True,
                default_flow_style=False,
            )

        # 날짜별 로그 저장
        log_path = self.discovery_dir / "logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {result.timestamp} ---\n")
            f.write(f"Run ID: {result.run_id}\n")
            f.write(f"Keywords: {', '.join(result.keywords_used)}\n")
            f.write(f"Discovered: {result.discovered}\n")
            f.write(f"Added as pending: {result.added_as_pending}\n")
            if result.errors:
                f.write(f"Errors: {result.errors}\n")

        # 30일 이전 로그 삭제
        self._cleanup_old_logs()

    def _cleanup_old_logs(self) -> None:
        """30일 이전 로그 파일 삭제"""
        logs_dir = self.discovery_dir / "logs"
        cutoff = datetime.now() - timedelta(days=30)

        for log_file in logs_dir.glob("*.log"):
            try:
                # 파일명에서 날짜 추출
                date_str = log_file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    log_file.unlink()
                    logger.debug(f"Deleted old log: {log_file}")
            except Exception:
                pass

    def review_pending(self) -> list[SourceMeta]:
        """pending 상태 소스 목록 반환"""
        return self.source_manager.get_pending()

    def approve(self, source_ids: list[str]) -> int:
        """소스 승인"""
        count = 0
        for source_id in source_ids:
            if self.source_manager.approve(source_id):
                count += 1
        return count

    def reject(self, source_ids: list[str]) -> int:
        """소스 거부"""
        count = 0
        for source_id in source_ids:
            if self.source_manager.reject(source_id):
                count += 1
        return count


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="소스 자동 발견")
    parser.add_argument("--account", "-a", required=True, help="계정 ID")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장 없이 시뮬레이션")
    parser.add_argument("--keywords", "-k", help="특정 키워드만 검색 (쉼표 구분)")
    parser.add_argument("--review", action="store_true", help="pending 후보 목록 출력")
    parser.add_argument("--approve", nargs="+", metavar="SOURCE_ID", help="소스 승인")
    parser.add_argument("--reject", nargs="+", metavar="SOURCE_ID", help="소스 거부")

    args = parser.parse_args()

    discovery = SourceDiscovery(account_id=args.account)

    # 승인/거부 처리
    if args.approve:
        count = discovery.approve(args.approve)
        print(f"Approved {count} sources")
        return

    if args.reject:
        count = discovery.reject(args.reject)
        print(f"Rejected {count} sources")
        return

    # pending 목록 조회
    if args.review:
        pending = discovery.review_pending()
        if not pending:
            print("No pending sources")
            return

        print(f"\nPending Sources ({len(pending)}):")
        print("-" * 60)
        for source in pending:
            print(f"  ID: {source.id}")
            print(f"  URL: {source.url}")
            print(f"  RSS: {source.rss_url or 'N/A'}")
            print(f"  Keyword: {source.discovery_keyword or 'N/A'}")
            print(f"  Discovered: {source.discovered_at or 'N/A'}")
            print("-" * 60)
        return

    # 발견 실행
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]

    result = discovery.run(dry_run=args.dry_run, keywords=keywords)

    print(f"\n{'=' * 50}")
    print("Discovery Results")
    print(f"{'=' * 50}")
    print(f"Account: {result.account}")
    print(f"Keywords: {len(result.keywords_used)}")
    print(f"Discovered: {result.discovered}")
    print(f"Added as pending: {result.added_as_pending}")
    print(f"Already known: {result.already_known}")
    print(f"Below threshold: {result.below_threshold}")
    if result.errors:
        print(f"Errors: {len(result.errors)}")


if __name__ == "__main__":
    main()
