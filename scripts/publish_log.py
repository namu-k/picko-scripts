"""
Publish Log 스크립트
발행 로그 생성 및 관리
"""

import argparse
from datetime import datetime
from pathlib import Path

from picko.config import get_config
from picko.logger import setup_logger
from picko.templates import get_renderer
from picko.vault_io import VaultIO

logger = setup_logger("publish_log")


class PublishLogManager:
    """발행 로그 관리자"""

    PLATFORMS = ["twitter", "linkedin", "newsletter", "blog", "instagram", "youtube"]

    def __init__(self):
        self.config = get_config()
        self.vault = VaultIO()
        self.renderer = get_renderer()

        # 발행 로그 디렉토리
        self.logs_path = "Logs/Publish"

        logger.info("PublishLogManager initialized")

    def create(self, content_path: str, platform: str = None, scheduled_at: str = None, notes: str = None) -> dict:
        """
        발행 로그 생성

        Args:
            content_path: 발행할 콘텐츠 경로
            platform: 발행 플랫폼
            scheduled_at: 예정 발행 일시
            notes: 추가 메모

        Returns:
            생성 결과
        """
        logger.info(f"Creating publish log for: {content_path}")

        result = {"content_path": content_path, "log_path": None, "success": False, "error": None}

        try:
            # 콘텐츠 노트 로드
            meta, content = self.vault.read_note(content_path)

            # 로그 ID 생성
            content_id = meta.get("id", Path(content_path).stem)
            log_id = f"pub_{content_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # 로그 데이터 구성
            log_data = {
                "id": log_id,
                "content_id": content_id,
                "content_path": content_path,
                "content_title": meta.get("title", "Untitled"),
                "content_type": meta.get("type", "unknown"),
                "platform": platform or "unspecified",
                "scheduled_at": scheduled_at,
                "status": "draft",
                "created_at": datetime.now().isoformat(),
                "notes": notes,
            }

            # 템플릿 렌더링
            log_content = self._render_publish_log(log_data)

            # 저장
            self.vault.ensure_dir(self.logs_path)
            log_path = f"{self.logs_path}/{log_id}.md"

            log_meta = {
                "id": log_id,
                "type": "publish_log",
                "content_id": content_id,
                "platform": platform or "unspecified",
                "status": "draft",
                "scheduled_at": scheduled_at,
                "created_at": datetime.now().isoformat(),
            }

            self.vault.write_note(log_path, log_content, metadata=log_meta)

            result["log_path"] = log_path
            result["success"] = True

            logger.info(f"Created publish log: {log_path}")

        except Exception as e:
            logger.error(f"Failed to create publish log: {e}")
            result["error"] = str(e)

        return result

    def _render_publish_log(self, data: dict) -> str:
        """발행 로그 렌더링"""
        template = """# Publish Log: {{ content_title }}

## 콘텐츠 정보

| 항목 | 값 |
|------|-----|
| **콘텐츠 ID** | {{ content_id }} |
| **콘텐츠 경로** | [[{{ content_path }}]] |
| **콘텐츠 타입** | {{ content_type }} |

---

## 발행 정보

| 항목 | 값 |
|------|-----|
| **플랫폼** | {{ platform }} |
| **예정 일시** | {{ scheduled_at or "미정" }} |
| **상태** | {{ status }} |

---

## 체크리스트

- [ ] 콘텐츠 최종 검토
- [ ] 이미지/미디어 준비
- [ ] 해시태그 확인
- [ ] 발행 시간 확정
- [ ] 발행 완료

---

## 성과 메트릭

| 지표 | 값 |
|------|-----|
| 조회수 | - |
| 좋아요 | - |
| 댓글 | - |
| 공유 | - |

---

## 메모

{{ notes or "발행 관련 메모를 여기에 작성하세요." }}
"""
        return self.renderer.render_string(template, **data)

    def update_status(self, log_path: str, status: str, published_at: str = None) -> bool:
        """발행 로그 상태 업데이트"""
        valid_statuses = ["draft", "scheduled", "published", "cancelled"]

        if status not in valid_statuses:
            logger.error(f"Invalid status: {status}")
            return False

        try:
            updates = {"status": status}

            if status == "published":
                updates["published_at"] = published_at or datetime.now().isoformat()

            self.vault.update_frontmatter(log_path, updates)
            logger.info(f"Updated status to '{status}': {log_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False

    def list_logs(self, status: str = None) -> list[dict]:
        """발행 로그 목록"""
        logs = []

        notes = self.vault.list_notes(self.logs_path)

        for note_path in notes:
            try:
                meta = self.vault.read_frontmatter(note_path)

                if status and meta.get("status") != status:
                    continue

                logs.append(
                    {
                        "path": str(note_path),
                        "id": meta.get("id"),
                        "content_id": meta.get("content_id"),
                        "platform": meta.get("platform"),
                        "status": meta.get("status"),
                        "scheduled_at": meta.get("scheduled_at"),
                    }
                )
            except Exception as e:
                logger.warning(f"Error reading {note_path}: {e}")

        return logs


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(description="Publish Log - 발행 로그 생성 및 관리")

    subparsers = parser.add_subparsers(dest="command", help="명령")

    # create 명령
    create_parser = subparsers.add_parser("create", help="발행 로그 생성")
    create_parser.add_argument("--content", "-c", required=True, help="발행할 콘텐츠 경로")
    create_parser.add_argument("--platform", "-p", choices=PublishLogManager.PLATFORMS, help="발행 플랫폼")
    create_parser.add_argument("--scheduled", help="예정 발행 일시 (YYYY-MM-DD HH:MM)")
    create_parser.add_argument("--notes", help="추가 메모")

    # list 명령
    list_parser = subparsers.add_parser("list", help="발행 로그 목록")
    list_parser.add_argument(
        "--status", "-s", choices=["draft", "scheduled", "published", "cancelled"], help="상태 필터"
    )

    # update 명령
    update_parser = subparsers.add_parser("update", help="상태 업데이트")
    update_parser.add_argument("--log", "-l", required=True, help="발행 로그 경로")
    update_parser.add_argument(
        "--status", "-s", required=True, choices=["draft", "scheduled", "published", "cancelled"], help="새 상태"
    )

    args = parser.parse_args()

    manager = PublishLogManager()

    if args.command == "create":
        result = manager.create(
            content_path=args.content, platform=args.platform, scheduled_at=args.scheduled, notes=args.notes
        )

        if result["success"]:
            print(f"\n✓ 발행 로그 생성 완료: {result['log_path']}")
        else:
            print(f"\n✗ 생성 실패: {result['error']}")

    elif args.command == "list":
        logs = manager.list_logs(status=args.status)

        print(f"\n{'=' * 60}")
        print(f"Publish Logs{f' (status: {args.status})' if args.status else ''}")
        print(f"{'=' * 60}")

        for log in logs:
            status_icon = {"draft": "📝", "scheduled": "📅", "published": "✅", "cancelled": "❌"}.get(
                log["status"], "❓"
            )

            print(f"{status_icon} [{log['platform']}] {log['content_id']}")

        print(f"\nTotal: {len(logs)} logs")

    elif args.command == "update":
        success = manager.update_status(args.log, args.status)

        if success:
            print(f"\n✓ 상태 업데이트 완료: {args.status}")
        else:
            print("\n✗ 업데이트 실패")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
