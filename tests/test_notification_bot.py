"""
Unit tests for HumanReviewBot
Phase 1.1 implementation tests
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from picko.notification.bot import HumanReviewBot, ReviewRequest, ReviewType


class TestHumanReviewBot:
    """HumanReviewBot tests"""

    def test_init_default_provider(self):
        """기본 provider는 telegram"""
        bot = HumanReviewBot()
        assert bot.provider == "telegram"

    def test_init_custom_provider(self):
        """커스텀 provider 설정"""
        bot = HumanReviewBot(provider="slack")
        assert bot.provider == "slack"

    def test_init_timeout_from_env(self):
        """타임아웃 설정"""
        bot = HumanReviewBot(timeout_hours=48)
        assert bot.timeout_hours == 48

    def test_is_configured_no_token(self):
        """토큰 없으면 미설정"""
        bot = HumanReviewBot()
        # 토큰이 없으면 False
        assert bot.is_configured() is False

    def test_is_configured_with_token(self):
        """토큰 있으면 설정됨"""
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat"},
        ):
            bot = HumanReviewBot()
            assert bot.is_configured() is True

    @pytest.mark.asyncio
    async def test_notify_quality_review_not_configured(self):
        """미설정 시 알림 실패"""
        bot = HumanReviewBot()
        success = await bot.notify_quality_review(
            item_id="test_001",
            title="Test Article",
            confidence=0.75,
            reason="Low confidence score",
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_notify_quality_review_success(self):
        """알림 성공 시 pending에 추가"""
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat"},
        ):
            bot = HumanReviewBot()
            with patch.object(bot, "_send_telegram", AsyncMock(return_value=True)):
                success = await bot.notify_quality_review(
                    item_id="test_001",
                    title="Test Article",
                    confidence=0.75,
                    reason="Low confidence score",
                )

                assert success is True
                assert "test_001" in bot._pending_reviews

    @pytest.mark.asyncio
    async def test_notify_source_discovered(self):
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "test_chat"},
        ):
            bot = HumanReviewBot()
            with patch.object(bot, "_send_telegram", AsyncMock(return_value=True)):
                success = await bot.notify_source_discovered(
                    source_id="source_001",
                    handle="@ai_news",
                    platform="threads",
                    score=0.87,
                    metadata={"followers": 12500},
                )

                assert success is True
                assert "source_001" in bot._pending_reviews

    def test_handle_callback_approve(self):
        """승인 콜백 처리"""
        bot = HumanReviewBot()
        bot._pending_reviews["test_001"] = ReviewRequest(
            item_id="test_001",
            review_type=ReviewType.QUALITY,
            title="Test",
            confidence=0.75,
            reason="Test",
            created_at=datetime.now(),
        )

        mock_vault = MagicMock()
        result = bot.handle_callback("approve:test_001", mock_vault)

        assert "승인" in result
        mock_vault.update_frontmatter.assert_called_once()

    def test_handle_callback_reject(self):
        """거절 콜백 처리"""
        bot = HumanReviewBot()
        bot._pending_reviews["test_001"] = ReviewRequest(
            item_id="test_001",
            review_type=ReviewType.QUALITY,
            title="Test",
            confidence=0.75,
            reason="Test",
            created_at=datetime.now(),
        )

        mock_vault = MagicMock()
        result = bot.handle_callback("reject:test_001", mock_vault)

        assert "거절" in result
        assert "test_001" not in bot._pending_reviews

    def test_handle_callback_invalid_format(self):
        """잘못된 콜백 형식"""
        bot = HumanReviewBot()
        mock_vault = MagicMock()

        result = bot.handle_callback("invalid", mock_vault)

        assert "잘못된" in result or "알 수 없는" in result

    def test_check_timeouts(self):
        """만료된 리뷰 자동 거절"""
        bot = HumanReviewBot(timeout_hours=1)

        # 2시간 전에 생성된 리뷰
        old_time = datetime.now() - timedelta(hours=2)
        bot._pending_reviews["old_item"] = ReviewRequest(
            item_id="old_item",
            review_type=ReviewType.QUALITY,
            title="Old",
            confidence=0.75,
            reason="Test",
            created_at=old_time,
        )

        mock_vault = MagicMock()
        expired = bot.check_timeouts(mock_vault)

        assert "old_item" in expired
        assert "old_item" not in bot._pending_reviews

    def test_get_pending_reminders(self):
        """재알림 필요한 리뷰 찾기"""
        bot = HumanReviewBot(reminder_hours=1)

        # 2시간 전 리뷰 (재알림 필요)
        old_time = datetime.now() - timedelta(hours=2)
        bot._pending_reviews["old_item"] = ReviewRequest(
            item_id="old_item",
            review_type=ReviewType.QUALITY,
            title="Old",
            confidence=0.75,
            reason="Test",
            created_at=old_time,
        )

        # 방금 생성된 리뷰 (재알림 불필요)
        bot._pending_reviews["new_item"] = ReviewRequest(
            item_id="new_item",
            review_type=ReviewType.QUALITY,
            title="New",
            confidence=0.75,
            reason="Test",
            created_at=datetime.now(),
        )

        reminders = bot.get_pending_reminders()

        assert len(reminders) == 1
        assert reminders[0][0] == "old_item"

    def test_format_quality_message(self):
        """품질 리뷰 메시지 포맷"""
        bot = HumanReviewBot()
        request = ReviewRequest(
            item_id="test_001",
            review_type=ReviewType.QUALITY,
            title="Test Article",
            confidence=0.72,
            reason="Low confidence",
            created_at=datetime.now(),
        )

        message = bot._format_quality_message(request)

        assert "품질 검토" in message
        assert "Test Article" in message
        assert "0.72" in message

    def test_format_source_message(self):
        """소스 발견 메시지 포맷"""
        bot = HumanReviewBot()
        request = ReviewRequest(
            item_id="source_001",
            review_type=ReviewType.SOURCE,
            title="@ai_news (threads)",
            confidence=0.87,
            reason="Discovered",
            created_at=datetime.now(),
            metadata={"followers": 12500, "keyword": "AI"},
        )

        message = bot._format_source_message(request)

        assert "소스 발견" in message
        assert "@ai_news" in message
        assert "12500" in message


class TestReviewRequest:
    """ReviewRequest tests"""

    def test_create_review_request(self):
        """리뷰 요청 생성"""
        request = ReviewRequest(
            item_id="test_001",
            review_type=ReviewType.QUALITY,
            title="Test",
            confidence=0.75,
            reason="Test reason",
            created_at=datetime.now(),
        )

        assert request.item_id == "test_001"
        assert request.review_type == ReviewType.QUALITY
        assert request.metadata is None

    def test_create_with_metadata(self):
        """메타데이터 포함 생성"""
        request = ReviewRequest(
            item_id="test_001",
            review_type=ReviewType.SOURCE,
            title="Test",
            confidence=0.75,
            reason="Test",
            created_at=datetime.now(),
            metadata={"followers": 1000},
        )

        assert request.metadata == {"followers": 1000}
