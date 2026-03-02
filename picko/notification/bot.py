"""
Human Review Bot for Telegram/Slack notifications

Provides async human review workflow for quality verification and source discovery.
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from picko.logger import get_logger

logger = get_logger("notification")

# Default cache directory for pending reviews persistence
DEFAULT_CACHE_DIR = Path("cache")


class ReviewType(Enum):
    """리뷰 타입"""

    QUALITY = "quality"
    SOURCE = "source"


@dataclass
class ReviewRequest:
    """리뷰 요청 데이터"""

    item_id: str
    review_type: ReviewType
    title: str
    confidence: float
    reason: str
    created_at: datetime
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "item_id": self.item_id,
            "review_type": self.review_type.value,
            "title": self.title,
            "confidence": self.confidence,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewRequest":
        """Create from dictionary (JSON deserialization)"""
        return cls(
            item_id=data["item_id"],
            review_type=ReviewType(data["review_type"]),
            title=data["title"],
            confidence=data["confidence"],
            reason=data["reason"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata"),
        )


class HumanReviewBot:
    """
    Telegram/Slack을 통한 비동기 Human Review 처리

    Polling 방식으로 동작하며, 파이프라인과 독립적으로 실행됩니다.
    Pending reviews are persisted to JSON file to survive restarts.
    """

    DEFAULT_TIMEOUT_HOURS = 72
    DEFAULT_REMINDER_HOURS = 24
    PENDING_REVIEWS_FILE = "pending_reviews.json"

    def __init__(
        self,
        provider: str | None = None,
        timeout_hours: int | None = None,
        reminder_hours: int | None = None,
        cache_dir: Path | str | None = None,
    ):
        """
        Initialize HumanReviewBot

        Args:
            provider: "telegram" or "slack" (default: from env NOTIFICATION_PROVIDER)
            timeout_hours: 리뷰 만료 시간 (default: 72)
            reminder_hours: 재알림 간격 (default: 24)
            cache_dir: 캐시 디렉토리 (default: cache/)
        """
        self.provider = provider or os.getenv("NOTIFICATION_PROVIDER", "telegram")
        self.timeout_hours = timeout_hours or int(os.getenv("REVIEW_TIMEOUT_HOURS", str(self.DEFAULT_TIMEOUT_HOURS)))
        self.reminder_hours = reminder_hours or int(
            os.getenv("REVIEW_REMINDER_HOURS", str(self.DEFAULT_REMINDER_HOURS))
        )

        # Cache directory for persistence
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Telegram credentials
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        # Slack credentials (optional)
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_channel = os.getenv("SLACK_CHANNEL_ID")

        # Pending reviews tracking (loaded from file)
        self._pending_reviews: dict[str, ReviewRequest] = {}
        self._load_pending_reviews()

        self._validate_config()

        logger.info(
            f"HumanReviewBot initialized: provider={self.provider}, "
            f"timeout={self.timeout_hours}h, reminder={self.reminder_hours}h, "
            f"pending_reviews={len(self._pending_reviews)}"
        )

    def _get_reviews_file_path(self) -> Path:
        """Get the path to the pending reviews JSON file"""
        return self.cache_dir / self.PENDING_REVIEWS_FILE

    def _load_pending_reviews(self) -> None:
        """Load pending reviews from JSON file"""
        file_path = self._get_reviews_file_path()
        if not file_path.exists():
            logger.debug("No existing pending reviews file")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._pending_reviews = {
                item_id: ReviewRequest.from_dict(req_data) for item_id, req_data in data.items()
            }
            logger.info(f"Loaded {len(self._pending_reviews)} pending reviews from {file_path}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load pending reviews: {e}. Starting fresh.")
            self._pending_reviews = {}

    def _save_pending_reviews(self) -> None:
        """Save pending reviews to JSON file"""
        file_path = self._get_reviews_file_path()

        try:
            data = {item_id: req.to_dict() for item_id, req in self._pending_reviews.items()}
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self._pending_reviews)} pending reviews to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save pending reviews: {e}")

    def _validate_config(self) -> None:
        """설정 검증"""
        if self.provider == "telegram":
            if not self.telegram_token:
                logger.warning("TELEGRAM_BOT_TOKEN not set")
            if not self.telegram_chat_id:
                logger.warning("TELEGRAM_CHAT_ID not set")
        elif self.provider == "slack":
            if not self.slack_token:
                logger.warning("SLACK_BOT_TOKEN not set")
            if not self.slack_channel:
                logger.warning("SLACK_CHANNEL_ID not set")

    def is_configured(self) -> bool:
        """필수 설정이 완료되었는지 확인"""
        if self.provider == "telegram":
            return bool(self.telegram_token and self.telegram_chat_id)
        elif self.provider == "slack":
            return bool(self.slack_token and self.slack_channel)
        return False

    async def notify_quality_review(
        self,
        item_id: str,
        title: str,
        confidence: float,
        reason: str,
    ) -> bool:
        """
        품질 검증 결과 사람 검토 요청

        Args:
            item_id: 아이템 ID
            title: 콘텐츠 제목
            confidence: 신뢰도 점수 (0.0-1.0)
            reason: 검토 요청 사유

        Returns:
            전송 성공 여부
        """
        request = ReviewRequest(
            item_id=item_id,
            review_type=ReviewType.QUALITY,
            title=title,
            confidence=confidence,
            reason=reason,
            created_at=datetime.now(),
        )

        text = self._format_quality_message(request)
        keyboard = self._build_keyboard(request, "approve", "reject")

        success = await self._send(text, keyboard)

        if success:
            self._pending_reviews[item_id] = request
            self._save_pending_reviews()
            logger.info(f"Quality review notification sent: {item_id}")

        return success

    async def notify_source_discovered(
        self,
        source_id: str,
        handle: str,
        platform: str,
        score: float,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        새 소스 발견 사람 검토 요청

        Args:
            source_id: 소스 ID
            handle: 계정 핸들 (예: @ai_news)
            platform: 플랫폼 (threads, reddit, mastodon)
            score: 관련도 점수
            metadata: 추가 정보 (팔로워 수 등)

        Returns:
            전송 성공 여부
        """
        request = ReviewRequest(
            item_id=source_id,
            review_type=ReviewType.SOURCE,
            title=f"{handle} ({platform})",
            confidence=score,
            reason=f"Discovered source with relevance score: {score:.2f}",
            created_at=datetime.now(),
            metadata={"handle": handle, "platform": platform, **(metadata or {})},
        )

        text = self._format_source_message(request)
        keyboard = self._build_keyboard(request, "source_approve", "source_reject")

        success = await self._send(text, keyboard)

        if success:
            self._pending_reviews[source_id] = request
            self._save_pending_reviews()
            logger.info(f"Source discovery notification sent: {source_id}")

        return success

    def handle_callback(self, callback_data: str, vault_adapter: Any) -> str:
        """
        버튼 클릭 콜백 처리

        Args:
            callback_data: 콜백 데이터 (예: "approve:item_xxx")
            vault_adapter: Vault 업데이트용 어댑터

        Returns:
            처리 결과 메시지
        """
        try:
            action, item_id = callback_data.split(":", 1)

            if action in ("approve", "source_approve"):
                status_key = "status" if action == "approve" else "source_status"
                vault_adapter.update_frontmatter(item_id, {status_key: "approved"})
                self._pending_reviews.pop(item_id, None)
                self._save_pending_reviews()
                logger.info(f"Approved: {item_id}")
                return f"✅ 승인됨: {item_id}"
            elif action in ("reject", "source_reject"):
                status_key = "status" if action == "reject" else "source_status"
                vault_adapter.update_frontmatter(item_id, {status_key: "rejected"})
                self._pending_reviews.pop(item_id, None)
                self._save_pending_reviews()
                logger.info(f"Rejected: {item_id}")
                return f"❌ 거절됨: {item_id}"
            else:
                logger.warning(f"Unknown callback action: {action}")
                return f"⚠️ 알 수 없는 액션: {action}"

        except ValueError as e:
            logger.error(f"Invalid callback data: {callback_data}, error: {e}")
            return f"⚠️ 잘못된 요청: {callback_data}"

    def check_timeouts(self, vault_adapter: Any) -> list[str]:
        """
        만료된 리뷰 자동 거절

        Args:
            vault_adapter: Vault 업데이트용 어댑터

        Returns:
            만료된 item_id 목록
        """
        now = datetime.now()
        timeout_threshold = timedelta(hours=self.timeout_hours)
        expired = []

        for item_id, request in list(self._pending_reviews.items()):
            if now - request.created_at > timeout_threshold:
                # 자동 거절
                status_key = "status" if request.review_type == ReviewType.QUALITY else "source_status"
                vault_adapter.update_frontmatter(item_id, {status_key: "rejected"})
                del self._pending_reviews[item_id]
                expired.append(item_id)
                logger.warning(f"Review timeout, auto-rejected: {item_id}")

        if expired:
            self._save_pending_reviews()

        return expired

    def get_pending_reminders(self) -> list[tuple[str, ReviewRequest]]:
        """
        재알림이 필요한 리뷰 목록

        Returns:
            (item_id, request) 튜플 목록
        """
        now = datetime.now()
        reminder_threshold = timedelta(hours=self.reminder_hours)
        reminders = []

        for item_id, request in self._pending_reviews.items():
            if now - request.created_at >= reminder_threshold:
                reminders.append((item_id, request))

        return reminders

    def _format_quality_message(self, request: ReviewRequest) -> str:
        """품질 리뷰 메시지 포맷"""
        return (
            f"🔍 [품질 검토 요청] {request.item_id}\n\n"
            f"제목: {request.title}\n"
            f"신뢰도: {request.confidence:.2f} (낮은 신뢰도로 검토 요청)\n"
            f"이유: {request.reason}\n\n"
            f"⏰ 만료: {request.created_at + timedelta(hours=self.timeout_hours):%Y-%m-%d %H:%M}"
        )

    def _format_source_message(self, request: ReviewRequest) -> str:
        """소스 발견 메시지 포맷"""
        metadata = request.metadata or {}
        followers = metadata.get("followers", "N/A")

        return (
            f"🌐 [새 소스 발견] {request.title}\n\n"
            f"관련도: {request.confidence:.2f}\n"
            f"팔로워: {followers}\n"
            f"발견 키워드: {metadata.get('keyword', 'N/A')}\n\n"
            f"⏰ 만료: {request.created_at + timedelta(hours=self.timeout_hours):%Y-%m-%d %H:%M}"
        )

    def _build_keyboard(self, request: ReviewRequest, approve_action: str, reject_action: str) -> list[dict[str, str]]:
        """인라인 키보드 버튼 구성"""
        return [
            {
                "text": "✅ 승인",
                "callback_data": f"{approve_action}:{request.item_id}",
            },
            {
                "text": "❌ 거절",
                "callback_data": f"{reject_action}:{request.item_id}",
            },
        ]

    async def _send(self, text: str, keyboard: list[dict[str, str]]) -> bool:
        """
        실제 메시지 전송

        Args:
            text: 메시지 텍스트
            keyboard: 인라인 키보드 버튼

        Returns:
            전송 성공 여부
        """
        if not self.is_configured():
            logger.warning(f"Bot not configured, skipping notification: {text[:50]}...")
            return False

        try:
            if self.provider == "telegram":
                return await self._send_telegram(text, keyboard)
            elif self.provider == "slack":
                return await self._send_slack(text, keyboard)
            else:
                logger.error(f"Unknown provider: {self.provider}")
                return False

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def _send_telegram(self, text: str, keyboard: list[dict[str, str]]) -> bool:
        """Telegram 메시지 전송"""
        try:
            # Lazy import to avoid dependency if not using Telegram
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import Application

            app = Application.builder().token(self.telegram_token).build()

            # Build keyboard
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"]) for btn in keyboard]]
            )

            await app.bot.send_message(
                chat_id=self.telegram_chat_id,
                text=text,
                reply_markup=reply_markup,
            )

            return True

        except ImportError:
            logger.warning("python-telegram-bot not installed")
            return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def _send_slack(self, text: str, keyboard: list[dict[str, str]]) -> bool:
        """Slack 메시지 전송"""
        try:
            # Lazy import to avoid dependency if not using Slack
            from slack_sdk.web.async_client import AsyncWebClient

            client = AsyncWebClient(token=self.slack_token)

            # Build blocks for buttons
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": text}},
                {
                    "type": "actions",
                    "block_id": "review_actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": btn["text"]},
                            "value": btn["callback_data"],
                            "action_id": btn["callback_data"].split(":")[0],
                        }
                        for btn in keyboard
                    ],
                },
            ]

            await client.chat_postMessage(
                channel=self.slack_channel,
                blocks=blocks,
                text=text,
            )

            return True

        except ImportError:
            logger.warning("slack-sdk not installed")
            return False
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False
