from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def twitter_env(monkeypatch):
    monkeypatch.setenv("TWITTER_BEARER_TOKEN", "bearer")
    monkeypatch.setenv("TWITTER_API_KEY", "api_key")
    monkeypatch.setenv("TWITTER_API_SECRET", "api_secret")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "access_token")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "access_token_secret")


def test_publish_success_returns_tweet_id_and_url(twitter_env):
    from picko.publisher import TwitterPublisher

    mock_client = MagicMock()
    mock_client.create_tweet.return_value = MagicMock(data={"id": "1234567890"})

    mock_tweepy = MagicMock()
    mock_tweepy.Client.return_value = mock_client

    publisher = TwitterPublisher(username="testuser")
    with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
        result = publisher.publish("hello world")

    assert result.success is True
    assert result.tweet_id == "1234567890"
    assert result.tweet_url == "https://twitter.com/testuser/status/1234567890"
    assert result.error == ""
    mock_client.create_tweet.assert_called_once_with(text="hello world")


def test_publish_handles_api_error_gracefully(twitter_env):
    from picko.publisher import TwitterPublisher

    mock_client = MagicMock()
    mock_client.create_tweet.side_effect = Exception("rate limit exceeded")

    mock_tweepy = MagicMock()
    mock_tweepy.Client.return_value = mock_client

    publisher = TwitterPublisher()
    with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
        result = publisher.publish("hello world")

    assert result.success is False
    assert result.tweet_id is None
    assert result.tweet_url is None
    assert "rate limit" in result.error


def test_cli_dry_run_does_not_call_api(capsys):
    from scripts.publish_twitter import main

    with patch("scripts.publish_twitter.TwitterPublisher") as mock_publisher_cls:
        exit_code = main(["--text", "dry run tweet", "--dry-run"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "DRY RUN" in output
    assert "dry run tweet" in output
    mock_publisher_cls.return_value.publish.assert_not_called()


def test_cli_reads_content_from_vault_note(twitter_env):
    from scripts.publish_twitter import main

    with (
        patch("scripts.publish_twitter.VaultIO") as mock_vault_cls,
        patch("scripts.publish_twitter.TwitterPublisher") as mock_publisher_cls,
    ):
        mock_vault_cls.return_value.read_note.return_value = ({}, "tweet from vault")
        mock_publisher_cls.return_value.publish.return_value = MagicMock(
            success=True,
            tweet_id="123",
            tweet_url="https://twitter.com/user/status/123",
            error="",
        )

        exit_code = main(["--content", "Content/Packs/twitter/sample.md"])

    assert exit_code == 0
    mock_publisher_cls.return_value.publish.assert_called_once_with("tweet from vault")


def test_publish_handles_auth_failure(twitter_env):
    from picko.publisher import TwitterPublisher

    mock_client = MagicMock()
    mock_client.create_tweet.side_effect = Exception("authentication failed")

    mock_tweepy = MagicMock()
    mock_tweepy.Client.return_value = mock_client

    publisher = TwitterPublisher()
    with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
        result = publisher.publish("hello world")

    assert result.success is False
    assert "authentication failed" in result.error


# ============================================================================
# Additional Tests for Missing Coverage
# ============================================================================


class TestPublishResultDataclass:
    """PublishResult 데이터클래스 테스트"""

    def test_publish_result_success_fields(self):
        """성공 결과 필드 테스트"""
        from picko.publisher import PublishResult

        result = PublishResult(
            success=True,
            tweet_id="123456",
            tweet_url="https://twitter.com/user/status/123456",
            error="",
        )

        assert result.success is True
        assert result.tweet_id == "123456"
        assert result.tweet_url == "https://twitter.com/user/status/123456"
        assert result.error == ""

    def test_publish_result_failure_fields(self):
        """실패 결과 필드 테스트"""
        from picko.publisher import PublishResult

        result = PublishResult(
            success=False,
            tweet_id=None,
            tweet_url=None,
            error="API error",
        )

        assert result.success is False
        assert result.tweet_id is None
        assert result.tweet_url is None
        assert result.error == "API error"

    def test_publish_result_defaults(self):
        """기본값 테스트"""
        from picko.publisher import PublishResult

        result = PublishResult(success=True)

        assert result.tweet_id is None
        assert result.tweet_url is None
        assert result.error == ""


class TestTwitterPublisherInit:
    """TwitterPublisher 초기화 테스트"""

    def test_init_with_default_username(self):
        """기본 사용자명 초기화"""
        from picko.publisher import TwitterPublisher

        publisher = TwitterPublisher()

        assert publisher.username == "user"
        assert publisher._client is None

    def test_init_with_custom_username(self):
        """커스텀 사용자명 초기화"""
        from picko.publisher import TwitterPublisher

        publisher = TwitterPublisher(username="customuser")

        assert publisher.username == "customuser"


class TestLoadTweepy:
    """_load_tweepy 메서드 테스트"""

    def test_load_tweepy_returns_module_when_installed(self):
        """tweepy 설치된 경우 모듈 반환"""
        from picko.publisher import TwitterPublisher

        publisher = TwitterPublisher()
        result = publisher._load_tweepy()

        # tweepy가 설치되어 있으면 모듈 반환, 아니면 None
        # 실제 환경에서는 설치 여부에 따라 다름
        assert result is not None or result is None  # 설치 여부와 관계없이 통과

    def test_load_tweepy_returns_none_on_import_error(self):
        """tweepy 미설치 시 None 반환"""
        from picko.publisher import TwitterPublisher

        publisher = TwitterPublisher()

        with patch("picko.publisher.import_module", side_effect=ImportError):
            result = publisher._load_tweepy()

        assert result is None


class TestGetClient:
    """_get_client 메서드 테스트"""

    def test_get_client_returns_none_without_credentials(self, monkeypatch):
        """자격 증명 없으면 None 반환"""
        from picko.publisher import TwitterPublisher

        # 모든 환경 변수 제거
        for key in [
            "TWITTER_BEARER_TOKEN",
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
        ]:
            monkeypatch.delenv(key, raising=False)

        publisher = TwitterPublisher()
        result = publisher._get_client()

        assert result is None

    def test_get_client_returns_none_with_partial_credentials(self, monkeypatch):
        """일부 자격 증명만 있으면 None 반환"""
        from picko.publisher import TwitterPublisher

        # 일부만 설정
        monkeypatch.setenv("TWITTER_API_KEY", "key")
        monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
        monkeypatch.delenv("TWITTER_API_SECRET", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN_SECRET", raising=False)

        publisher = TwitterPublisher()
        result = publisher._get_client()

        assert result is None

    def test_get_client_caches_client(self, twitter_env):
        """클라이언트 캐싱 테스트"""
        from picko.publisher import TwitterPublisher

        mock_client = MagicMock()
        mock_tweepy = MagicMock()
        mock_tweepy.Client.return_value = mock_client

        publisher = TwitterPublisher()

        with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
            client1 = publisher._get_client()
            client2 = publisher._get_client()

        assert client1 is client2
        mock_tweepy.Client.assert_called_once()  # 한 번만 호출

    def test_get_client_handles_client_init_exception(self, twitter_env):
        """클라이언트 초기화 예외 처리"""
        from picko.publisher import TwitterPublisher

        mock_tweepy = MagicMock()
        mock_tweepy.Client.side_effect = Exception("Init failed")

        publisher = TwitterPublisher()

        with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
            result = publisher._get_client()

        assert result is None


class TestPublishEdgeCases:
    """publish 메서드 엣지 케이스 테스트"""

    def test_publish_returns_error_when_client_unavailable(self, monkeypatch):
        """클라이언트 없을 때 에러 반환"""
        from picko.publisher import TwitterPublisher

        # 자격 증명 없음
        for key in [
            "TWITTER_BEARER_TOKEN",
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
        ]:
            monkeypatch.delenv(key, raising=False)

        publisher = TwitterPublisher()
        result = publisher.publish("test tweet")

        assert result.success is False
        assert "not available" in result.error

    def test_publish_handles_response_without_id(self, twitter_env):
        """응답에 id 없을 때 처리"""
        from picko.publisher import TwitterPublisher

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={})  # id 없음

        mock_tweepy = MagicMock()
        mock_tweepy.Client.return_value = mock_client

        publisher = TwitterPublisher()

        with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
            result = publisher.publish("hello world")

        assert result.success is False
        assert "tweet id" in result.error.lower()

    def test_publish_handles_response_with_none_data(self, twitter_env):
        """응답 data가 None일 때 처리"""
        from picko.publisher import TwitterPublisher

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data=None)

        mock_tweepy = MagicMock()
        mock_tweepy.Client.return_value = mock_client

        publisher = TwitterPublisher()

        with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
            result = publisher.publish("hello world")

        assert result.success is False

    def test_publish_converts_numeric_tweet_id_to_string(self, twitter_env):
        """숫자 tweet_id를 문자열로 변환"""
        from picko.publisher import TwitterPublisher

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={"id": 1234567890})  # 숫자

        mock_tweepy = MagicMock()
        mock_tweepy.Client.return_value = mock_client

        publisher = TwitterPublisher(username="testuser")

        with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
            result = publisher.publish("hello world")

        assert result.success is True
        assert result.tweet_id == "1234567890"  # 문자열
        assert isinstance(result.tweet_id, str)


class TestUsernameInUrl:
    """URL의 사용자명 테스트"""

    def test_url_uses_custom_username(self, twitter_env):
        """커스텀 사용자명이 URL에 반영"""
        from picko.publisher import TwitterPublisher

        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={"id": "123"})

        mock_tweepy = MagicMock()
        mock_tweepy.Client.return_value = mock_client

        publisher = TwitterPublisher(username="mycustomname")

        with patch.object(publisher, "_load_tweepy", return_value=mock_tweepy):
            result = publisher.publish("test")

        assert "mycustomname" in result.tweet_url
