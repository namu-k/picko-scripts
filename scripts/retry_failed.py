"""
Retry Failed 스크립트
실패한 수집 항목 재시도
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from picko.config import get_config
from picko.vault_io import VaultIO
from picko.llm_client import get_llm_client
from picko.embedding import get_embedding_manager
from picko.logger import setup_logger

logger = setup_logger("retry_failed")


class RetryManager:
    """실패 항목 재시도 관리자"""
    
    # 재시도 가능한 단계들
    STAGES = ["fetch", "nlp", "embed", "score", "export"]
    
    def __init__(self, max_attempts: int = 3):
        self.config = get_config()
        self.vault = VaultIO()
        self.llm = get_llm_client()
        self.embedder = get_embedding_manager()
        self.max_attempts = max_attempts
        self.logs_dir = Path(self.config.logging.dir)
        
        logger.info(f"RetryManager initialized (max_attempts: {max_attempts})")
    
    def run(
        self,
        date: str = None,
        stage: str = None,
        dry_run: bool = False
    ) -> dict:
        """
        실패 항목 재시도 실행
        
        Args:
            date: 대상 날짜 (YYYY-MM-DD)
            stage: 특정 단계만 재시도 (fetch/nlp/embed/score/export)
            dry_run: 저장 없이 시뮬레이션
        
        Returns:
            실행 결과 요약
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Starting retry for date: {date}, stage: {stage or 'all'}")
        
        results = {
            "date": date,
            "failed_found": 0,
            "retried": 0,
            "succeeded": 0,
            "still_failed": 0,
            "errors": []
        }
        
        try:
            # 1. 실패 항목 로드
            failed_items = self._load_failed_items(date, stage)
            results["failed_found"] = len(failed_items)
            
            if not failed_items:
                logger.info("No failed items found")
                return results
            
            logger.info(f"Found {len(failed_items)} failed items")
            
            # 2. 각 항목 재시도
            for item in failed_items:
                if item.get("retry_count", 0) >= self.max_attempts:
                    logger.warning(f"Max retries exceeded for {item.get('id')}")
                    results["still_failed"] += 1
                    continue
                
                results["retried"] += 1
                
                try:
                    success = self._retry_item(item, dry_run)
                    if success:
                        results["succeeded"] += 1
                        logger.info(f"Retry succeeded: {item.get('id')}")
                    else:
                        results["still_failed"] += 1
                except Exception as e:
                    logger.error(f"Retry failed for {item.get('id')}: {e}")
                    results["still_failed"] += 1
                    results["errors"].append(str(e))
            
            # 3. 결과 로그 저장
            if not dry_run:
                self._save_retry_log(date, results)
        
        except Exception as e:
            logger.error(f"Retry process failed: {e}")
            results["errors"].append(str(e))
        
        logger.info(f"Retry complete: {results}")
        return results
    
    def _load_failed_items(self, date: str, stage: str = None) -> list[dict]:
        """실패 항목 로드"""
        failed_items = []
        
        # logs/{date}/ 디렉토리에서 실패 로그 검색
        date_log_dir = self.logs_dir / date
        
        if not date_log_dir.exists():
            # Inbox에서 status: failed 인 항목 검색
            inbox_path = self.config.vault.inbox
            notes = self.vault.list_notes(inbox_path)
            
            for note_path in notes:
                try:
                    meta = self.vault.read_frontmatter(note_path)
                    if meta.get("status") == "failed":
                        item = {
                            "id": meta.get("id"),
                            "path": str(note_path),
                            "stage": meta.get("failed_stage", "unknown"),
                            "error": meta.get("error_message", ""),
                            "retry_count": meta.get("retry_count", 0)
                        }
                        
                        if stage is None or item["stage"] == stage:
                            failed_items.append(item)
                except Exception as e:
                    logger.warning(f"Error reading {note_path}: {e}")
        else:
            # 로그 파일에서 실패 항목 파싱
            for log_file in date_log_dir.glob("*.json"):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        log_data = json.load(f)
                    
                    if log_data.get("status") == "failed":
                        item = {
                            "id": log_data.get("id"),
                            "url": log_data.get("url"),
                            "stage": log_data.get("stage"),
                            "error": log_data.get("error"),
                            "retry_count": log_data.get("retry_count", 0),
                            "data": log_data.get("data", {})
                        }
                        
                        if stage is None or item["stage"] == stage:
                            failed_items.append(item)
                except Exception as e:
                    logger.warning(f"Error reading log {log_file}: {e}")
        
        return failed_items
    
    def _retry_item(self, item: dict, dry_run: bool) -> bool:
        """개별 항목 재시도"""
        stage = item.get("stage", "unknown")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would retry {item.get('id')} at stage: {stage}")
            return True
        
        # 단계별 재시도 로직
        if stage == "fetch":
            return self._retry_fetch(item)
        elif stage == "nlp":
            return self._retry_nlp(item)
        elif stage == "embed":
            return self._retry_embed(item)
        elif stage == "score":
            return self._retry_score(item)
        elif stage == "export":
            return self._retry_export(item)
        else:
            logger.warning(f"Unknown stage: {stage}")
            return False
    
    def _retry_fetch(self, item: dict) -> bool:
        """본문 추출 재시도"""
        import httpx
        from bs4 import BeautifulSoup
        
        url = item.get("url")
        if not url:
            return False
        
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 기본 본문 추출
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            
            # 성공 시 상태 업데이트
            if item.get("path"):
                self.vault.update_frontmatter(
                    item["path"],
                    {"status": "inbox", "text": text[:3000]}
                )
            
            return True
        except Exception as e:
            logger.error(f"Fetch retry failed: {e}")
            return False
    
    def _retry_nlp(self, item: dict) -> bool:
        """NLP 처리 재시도"""
        if not item.get("path"):
            return False
        
        try:
            meta, content = self.vault.read_note(item["path"])
            text = meta.get("text", "")
            
            if not text:
                return False
            
            # 요약 생성
            summary = self.llm.summarize(text, max_length=200)
            
            # 태그 생성
            tags = self.llm.generate_tags(text, max_tags=5)
            
            # 업데이트
            self.vault.update_frontmatter(
                item["path"],
                {
                    "status": "inbox",
                    "summary": summary,
                    "tags": tags,
                    "failed_stage": None,
                    "error_message": None
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"NLP retry failed: {e}")
            return False
    
    def _retry_embed(self, item: dict) -> bool:
        """임베딩 생성 재시도"""
        if not item.get("path"):
            return False
        
        try:
            meta, content = self.vault.read_note(item["path"])
            text = meta.get("title", "") + " " + meta.get("summary", "")
            
            embedding = self.embedder.embed(text)
            
            # 임베딩은 별도 캐시에 저장되므로 상태만 업데이트
            self.vault.update_frontmatter(
                item["path"],
                {
                    "status": "inbox",
                    "embedded": True,
                    "failed_stage": None,
                    "error_message": None
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Embed retry failed: {e}")
            return False
    
    def _retry_score(self, item: dict) -> bool:
        """점수 계산 재시도"""
        from picko.scoring import ContentScorer
        
        if not item.get("path"):
            return False
        
        try:
            meta, content = self.vault.read_note(item["path"])
            
            scorer = ContentScorer()
            score = scorer.score({
                "title": meta.get("title", ""),
                "text": meta.get("summary", ""),
                "keywords": meta.get("tags", [])
            })
            
            self.vault.update_frontmatter(
                item["path"],
                {
                    "status": "inbox",
                    "score": score.to_dict(),
                    "failed_stage": None,
                    "error_message": None
                }
            )
            
            return True
        except Exception as e:
            logger.error(f"Score retry failed: {e}")
            return False
    
    def _retry_export(self, item: dict) -> bool:
        """Export 재시도 (추후 구현)"""
        logger.info("Export retry not yet implemented")
        return False
    
    def _save_retry_log(self, date: str, results: dict) -> None:
        """재시도 결과 로그 저장"""
        log_dir = self.logs_dir / date
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"retry_{datetime.now().strftime('%H%M%S')}.json"
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved retry log: {log_file}")


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Retry Failed - 실패한 수집 항목 재시도"
    )
    parser.add_argument(
        "--date", "-d",
        help="대상 날짜 (YYYY-MM-DD, 기본: 오늘)"
    )
    parser.add_argument(
        "--stage", "-s",
        choices=RetryManager.STAGES,
        help="특정 단계만 재시도"
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="최대 재시도 횟수 (기본: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 시뮬레이션"
    )
    
    args = parser.parse_args()
    
    manager = RetryManager(max_attempts=args.max_attempts)
    
    results = manager.run(
        date=args.date,
        stage=args.stage,
        dry_run=args.dry_run
    )
    
    print(f"\n{'='*50}")
    print(f"Retry Results for {results['date']}")
    print(f"{'='*50}")
    print(f"Failed Found:  {results['failed_found']}")
    print(f"Retried:       {results['retried']}")
    print(f"Succeeded:     {results['succeeded']}")
    print(f"Still Failed:  {results['still_failed']}")
    if results['errors']:
        print(f"Errors:        {len(results['errors'])}")


if __name__ == "__main__":
    main()
