"""
Daily Collector 스크립트
RSS/크롤링에서 콘텐츠 수집 → 점수 → Vault Export → Digest 생성
"""

import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from picko.config import get_config
from picko.embedding import get_embedding_manager
from picko.llm_client import get_summary_client
from picko.logger import setup_logger
from picko.scoring import ContentScore, ContentScorer
from picko.templates import get_renderer
from picko.vault_io import VaultIO

logger = setup_logger("daily_collector")


class DailyCollector:
    """일일 콘텐츠 수집기"""

    def __init__(self, account_id: str | None = None, dry_run: bool = False):
        self.config = get_config()
        self.vault = VaultIO()
        # 요약/태깅용 로컬 LLM 사용
        self.llm = get_summary_client()
        self.embedder = get_embedding_manager()
        self.renderer = get_renderer()
        self.dry_run = dry_run

        # 계정 프로필 로드
        self.account_id = account_id or "socialbuilders"
        self.account_profile = self.config.get_account(self.account_id)

        # 스코어러 초기화
        self.scorer = ContentScorer(account_profile=self.account_profile)

        # 기존 임베딩 (novelty 계산용)
        self._existing_embeddings = None

        logger.info(f"DailyCollector initialized for account: {self.account_id}")

    def run(
        self,
        date: str | None = None,
        sources: list[str] | None = None,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        """
        수집 파이프라인 실행

        Args:
            date: 대상 날짜 (기본: 오늘)
            sources: 특정 소스만 처리 (기본: 전체)
            max_items: 처리할 최대 항목 수 (기본: 제한 없음)

        Returns:
            실행 결과 요약
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Starting collection for date: {date}")

        results: dict[str, Any] = {
            "date": date,
            "collected": 0,
            "processed": 0,
            "exported": 0,
            "errors": [],
        }

        try:
            # 1. 소스에서 URL 수집
            raw_items = self._ingest(sources)
            results["collected"] = len(raw_items)
            logger.info(f"Collected {len(raw_items)} items from sources")

            # 2. 중복 제거
            unique_items = self._dedupe(raw_items)
            logger.info(f"After dedupe: {len(unique_items)} unique items")

            # 3. 본문 추출
            fetched_items = self._fetch(unique_items)
            logger.info(f"Fetched content for {len(fetched_items)} items")

            # 4. NLP 처리 (요약/키워드/태깅)
            nlp_items = self._nlp_process(fetched_items)

            # 5. 임베딩 생성
            embedded_items = self._embed(nlp_items)

            # 6. 점수 계산
            scored_items = self._score(embedded_items)

            # max_items 적용 (상위 N개만 처리)
            if max_items is not None and max_items > 0:
                scored_items = scored_items[:max_items]
                logger.info(f"Limited to {len(scored_items)} items (max_items={max_items})")

            results["processed"] = len(scored_items)

            # 7. Input 노트 Export
            if not self.dry_run:
                exported = self._export(scored_items, date)
                results["exported"] = len(exported)

                # 8. Digest 생성
                self._create_digest(scored_items, date)
                logger.info(f"Created digest for {date}")
            else:
                logger.info("[DRY RUN] Skipping export and digest creation")

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            results["errors"].append(str(e))

        logger.info(f"Collection complete: {results}")
        return results

    # ─────────────────────────────────────────────────────────────
    # 파이프라인 단계
    # ─────────────────────────────────────────────────────────────

    def _ingest(self, source_filter: list[str] | None = None) -> list[dict[str, Any]]:
        """소스에서 URL 수집"""
        items = []
        sources_config = self.config.sources.get("sources", [])

        for source in sources_config:
            if not source.get("enabled", True):
                continue

            if source_filter and source["id"] not in source_filter:
                continue

            source_type = source.get("type", "rss")

            try:
                if source_type == "rss":
                    source_items = self._fetch_rss(source)
                    items.extend(source_items)
                # elif source_type == "crawler":
                #     source_items = self._crawl(source)
                #     items.extend(source_items)
            except Exception as e:
                logger.warning(f"Failed to fetch source {source['id']}: {e}")

        return items

    def _fetch_rss(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        """RSS 피드 파싱"""
        feed = feedparser.parse(source["url"])
        items = []

        for entry in feed.entries[:20]:  # 최대 20개
            item = {
                "source_id": source["id"],
                "source": source.get("id", "unknown"),
                "source_url": entry.get("link", ""),
                "title": entry.get("title", ""),
                "text": entry.get("summary", ""),
                "publish_date": self._parse_date(entry.get("published")),
                "category": source.get("category", "general"),
            }
            items.append(item)

        return items

    def _dedupe(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """URL 정규화 + 중복 제거"""
        seen_hashes = set()
        unique = []

        # 기존 Input 노트에서 해시 수집
        inbox_path = self.config.vault.inbox
        existing_notes = self.vault.list_notes(inbox_path, recursive=True)

        for note in existing_notes:
            try:
                meta = self.vault.read_frontmatter(note)
                if "url_hash" in meta:
                    seen_hashes.add(meta["url_hash"])
            except Exception:
                pass

        for item in items:
            url = self._canonicalize_url(item.get("source_url", ""))
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            if url_hash not in seen_hashes:
                item["url_hash"] = url_hash
                item["canonical_url"] = url
                seen_hashes.add(url_hash)
                unique.append(item)

        return unique

    def _canonicalize_url(self, url: str) -> str:
        """URL 정규화"""
        parsed = urlparse(url)
        # 쿼리 파라미터 제거 (utm 등)
        canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return canonical.rstrip("/")

    def _fetch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """본문/제목/발행일 추출"""
        fetched = []

        with httpx.Client(timeout=30) as client:
            for item in items:
                try:
                    url = item.get("source_url", "")
                    if not url:
                        continue

                    response = client.get(url, follow_redirects=True)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "lxml")

                        # 제목 추출
                        if not item.get("title"):
                            title_tag = soup.find("title")
                            item["title"] = title_tag.text.strip() if title_tag else ""

                        # 본문 추출 (간단한 휴리스틱)
                        article = soup.find("article") or soup.find("main") or soup.body
                        if article:
                            # 스크립트/스타일 제거
                            for tag in article.find_all(["script", "style", "nav", "footer"]):
                                tag.decompose()

                            text = article.get_text(separator="\n", strip=True)
                            item["full_text"] = text[:5000]  # 최대 5000자

                        fetched.append(item)

                except Exception as e:
                    logger.warning(f"Failed to fetch {item.get('source_url')}: {e}")

        return fetched

    def _nlp_process(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """LLM으로 요약/핵심/태깅"""
        processed = []

        for item in items:
            try:
                text = item.get("full_text") or item.get("text", "")
                title = item.get("title", "")

                if not text:
                    continue

                # 요약 생성
                summary = self.llm.summarize(f"{title}\n\n{text}", max_length=200)
                item["summary"] = summary

                # 핵심 포인트 추출
                key_points_prompt = f"""다음 콘텐츠에서 핵심 포인트 3가지를 추출하세요.
각 포인트는 한 문장으로 간결하게 작성하세요.

제목: {title}

내용:
{text[:2000]}

핵심 포인트 (각 줄에 하나씩):"""

                key_points_raw = self.llm.generate(key_points_prompt)
                item["key_points"] = [p.strip().lstrip("-•").strip() for p in key_points_raw.split("\n") if p.strip()][
                    :3
                ]

                # 태그 생성
                item["tags"] = self.llm.generate_tags(f"{title} {summary}")

                # 원문 발췌
                item["excerpt"] = text[:500] + "..." if len(text) > 500 else text

                processed.append(item)

            except Exception as e:
                logger.warning(f"NLP processing failed for {item.get('title')}: {e}")

        return processed

    def _embed(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """임베딩 생성"""
        for item in items:
            try:
                text = f"{item.get('title', '')} {item.get('summary', '')}"
                item["embedding"] = self.embedder.embed(text)
            except Exception as e:
                logger.warning(f"Embedding failed for {item.get('title')}: {e}")
                item["embedding"] = None

        return items

    def _score(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """점수 계산"""
        # 기존 임베딩 로드 (novelty 계산용)
        existing_embeddings = self._load_existing_embeddings()

        for item in items:
            score = self.scorer.score(item, existing_embeddings)
            item["score"] = score.to_dict()
            item["score_obj"] = score

            # 새 임베딩을 기존 목록에 추가 (이후 항목 novelty 계산에 반영)
            if item.get("embedding"):
                existing_embeddings.append(item["embedding"])

        # 점수순 정렬
        items.sort(key=lambda x: x.get("score", {}).get("total", 0), reverse=True)

        return items

    def _load_existing_embeddings(self) -> list[list[float]]:
        """기존 콘텐츠 임베딩 로드"""
        if self._existing_embeddings is not None:
            return self._existing_embeddings

        embeddings = []
        # TODO: 실제로는 캐시된 임베딩을 로드하거나 DB에서 조회
        # 현재는 빈 리스트 반환 (모든 콘텐츠가 새로운 것으로 간주)

        self._existing_embeddings = embeddings
        return embeddings

    def _export(self, items: list[dict[str, Any]], date: str) -> list[Path]:
        """Input 노트 Export"""
        exported = []
        inbox_path = self.config.vault.inbox

        for item in items:
            # 표시 임계값 확인
            if not self.scorer.should_display(item.get("score_obj", ContentScore())):
                continue

            # 노트 ID 생성
            note_id = f"input_{item['url_hash']}"
            item["id"] = note_id
            item["account_id"] = self.account_id
            item["collected_at"] = datetime.now().isoformat()

            # 템플릿 렌더링
            content = self.renderer.render_input_note(item)

            # 파일 저장
            note_path = f"{inbox_path}/{note_id}.md"
            try:
                saved = self.vault.write_note(
                    note_path,
                    content.split("---", 2)[2].strip(),
                    metadata=self._parse_frontmatter(content),
                )
                exported.append(saved)
                logger.debug(f"Exported: {note_path}")
            except FileExistsError:
                logger.debug(f"Note already exists: {note_path}")

        return exported

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """frontmatter 파싱"""
        import yaml

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1]) or {}
        return {}

    def _create_digest(self, items: list[dict[str, Any]], date: str) -> Path:
        """Digest 노트 생성"""
        # 표시할 항목만 필터링
        display_items = []
        for item in items:
            if not self.scorer.should_display(item.get("score_obj", ContentScore())):
                continue

            # writing_status 추가 (기본값: pending)
            if "writing_status" not in item:
                item["writing_status"] = "pending"

            display_items.append(item)

        # Digest 렌더링
        content = self.renderer.render_digest(date, display_items)

        # 저장
        digest_path = f"{self.config.vault.digests}/{date}.md"

        try:
            metadata = self._parse_frontmatter(content)
            body = content.split("---", 2)[2].strip() if content.startswith("---") else content
            return self.vault.write_note(digest_path, body, metadata=metadata, overwrite=True)
        except Exception as e:
            logger.error(f"Failed to create digest: {e}")
            raise

    def _parse_date(self, date_str: Any) -> str:
        """날짜 문자열 파싱"""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")

        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="Daily Collector - RSS/크롤링에서 콘텐츠 수집")
    parser.add_argument("--date", "-d", help="대상 날짜 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument("--account", "-a", default="socialbuilders", help="계정 프로필 ID")
    parser.add_argument("--sources", "-s", nargs="+", help="특정 소스만 처리")
    parser.add_argument(
        "--max-items",
        "-m",
        type=int,
        default=None,
        help="처리할 최대 항목 수 (기본: 제한 없음)",
    )
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 시뮬레이션")

    args = parser.parse_args()

    collector = DailyCollector(account_id=args.account, dry_run=args.dry_run)

    results = collector.run(date=args.date, sources=args.sources, max_items=args.max_items)

    print(f"\n{'=' * 50}")
    print(f"Collection Results for {results['date']}")
    print(f"{'=' * 50}")
    print(f"Collected: {results['collected']}")
    print(f"Processed: {results['processed']}")
    print(f"Exported:  {results['exported']}")
    if results["errors"]:
        print(f"Errors:    {len(results['errors'])}")
        for err in results["errors"]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
