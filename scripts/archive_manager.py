"""
Archive Manager 스크립트
오래된 미승인 콘텐츠 아카이브 처리
"""

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from picko.config import get_config
from picko.vault_io import VaultIO
from picko.logger import setup_logger

logger = setup_logger("archive_manager")


class ArchiveManager:
    """아카이브 관리자"""
    
    def __init__(self):
        self.config = get_config()
        self.vault = VaultIO()
        
        # 아카이브 경로 설정
        self.archive_path = self.config.vault.archive or "Archive"
        
        logger.info("ArchiveManager initialized")
    
    def run(
        self,
        days: int = 30,
        clean_cache: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        아카이브 처리 실행
        
        Args:
            days: N일 이상 지난 항목 대상
            clean_cache: 관련 캐시도 삭제
            dry_run: 저장 없이 시뮬레이션
        
        Returns:
            실행 결과 요약
        """
        logger.info(f"Starting archive (days: {days}, clean_cache: {clean_cache})")
        
        results = {
            "threshold_days": days,
            "scanned": 0,
            "archived": 0,
            "cache_cleaned": 0,
            "errors": []
        }
        
        try:
            # 기준 날짜 계산
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Inbox에서 오래된 항목 검색
            inbox_path = self.config.vault.inbox
            notes = self.vault.list_notes(inbox_path)
            
            results["scanned"] = len(notes)
            
            for note_path in notes:
                try:
                    meta = self.vault.read_frontmatter(note_path)
                    
                    # 승인되지 않은 항목만 (status: inbox)
                    if meta.get("status") != "inbox":
                        continue
                    
                    # 수집일 확인
                    collected_at = meta.get("collected_at")
                    if collected_at:
                        if isinstance(collected_at, str):
                            try:
                                collected_dt = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
                            except ValueError:
                                collected_dt = datetime.strptime(collected_at[:10], "%Y-%m-%d")
                        else:
                            collected_dt = collected_at
                        
                        if collected_dt.replace(tzinfo=None) > cutoff_date:
                            continue  # 아직 기한 안 됨
                    else:
                        # 수집일 없으면 파일 수정일 사용
                        file_mtime = datetime.fromtimestamp(note_path.stat().st_mtime)
                        if file_mtime > cutoff_date:
                            continue
                    
                    # 아카이브 처리
                    if dry_run:
                        logger.info(f"[DRY RUN] Would archive: {note_path.name}")
                        results["archived"] += 1
                    else:
                        if self._archive_note(note_path, meta):
                            results["archived"] += 1
                            
                            # 캐시 정리
                            if clean_cache:
                                cache_cleaned = self._clean_cache(meta.get("id"))
                                results["cache_cleaned"] += cache_cleaned
                
                except Exception as e:
                    logger.warning(f"Error processing {note_path}: {e}")
                    results["errors"].append(str(e))
        
        except Exception as e:
            logger.error(f"Archive process failed: {e}")
            results["errors"].append(str(e))
        
        logger.info(f"Archive complete: {results}")
        return results
    
    def _archive_note(self, note_path: Path, meta: dict) -> bool:
        """노트를 아카이브로 이동"""
        try:
            # 아카이브 대상 경로 생성
            archive_inputs = self.vault.get_path(f"{self.archive_path}/Inputs")
            archive_inputs.mkdir(parents=True, exist_ok=True)
            
            dest_path = archive_inputs / note_path.name
            
            # 상태 업데이트 후 이동
            self.vault.update_frontmatter(
                note_path,
                {
                    "status": "archived",
                    "archived_at": datetime.now().isoformat()
                }
            )
            
            # 파일 이동
            self.vault.move_note(note_path, dest_path)
            
            logger.info(f"Archived: {note_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive {note_path}: {e}")
            return False
    
    def _clean_cache(self, item_id: str) -> int:
        """관련 캐시 정리"""
        if not item_id:
            return 0
        
        cleaned = 0
        
        # 임베딩 캐시 정리
        cache_dir = Path(self.config.embedding.cache_dir)
        if cache_dir.exists():
            for cache_file in cache_dir.glob(f"*{item_id}*"):
                try:
                    cache_file.unlink()
                    cleaned += 1
                    logger.debug(f"Deleted cache: {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete cache {cache_file}: {e}")
        
        return cleaned
    
    def list_archivable(self, days: int = 30) -> list[dict]:
        """아카이브 대상 항목 목록"""
        cutoff_date = datetime.now() - timedelta(days=days)
        archivable = []
        
        inbox_path = self.config.vault.inbox
        notes = self.vault.list_notes(inbox_path)
        
        for note_path in notes:
            try:
                meta = self.vault.read_frontmatter(note_path)
                
                if meta.get("status") != "inbox":
                    continue
                
                collected_at = meta.get("collected_at")
                if collected_at:
                    if isinstance(collected_at, str):
                        try:
                            collected_dt = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
                        except ValueError:
                            collected_dt = datetime.strptime(collected_at[:10], "%Y-%m-%d")
                    else:
                        collected_dt = collected_at
                    
                    if collected_dt.replace(tzinfo=None) <= cutoff_date:
                        archivable.append({
                            "path": str(note_path),
                            "id": meta.get("id"),
                            "title": meta.get("title"),
                            "collected_at": str(collected_at)
                        })
            except Exception as e:
                logger.warning(f"Error reading {note_path}: {e}")
        
        return archivable


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Archive Manager - 오래된 미승인 콘텐츠 아카이브"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="N일 이상 지난 항목 대상 (기본: 30)"
    )
    parser.add_argument(
        "--clean-cache",
        action="store_true",
        help="관련 임베딩 캐시도 삭제"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="아카이브 대상 목록만 출력"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 시뮬레이션"
    )
    
    args = parser.parse_args()
    
    manager = ArchiveManager()
    
    if args.list:
        items = manager.list_archivable(days=args.days)
        print(f"\n{'='*50}")
        print(f"Archivable Items ({args.days}+ days old)")
        print(f"{'='*50}")
        for item in items:
            print(f"  - {item['title'][:40]}... ({item['collected_at'][:10]})")
        print(f"\nTotal: {len(items)} items")
    else:
        results = manager.run(
            days=args.days,
            clean_cache=args.clean_cache,
            dry_run=args.dry_run
        )
        
        print(f"\n{'='*50}")
        print(f"Archive Results")
        print(f"{'='*50}")
        print(f"Scanned:       {results['scanned']}")
        print(f"Archived:      {results['archived']}")
        print(f"Cache Cleaned: {results['cache_cleaned']}")
        if results['errors']:
            print(f"Errors:        {len(results['errors'])}")


if __name__ == "__main__":
    main()
