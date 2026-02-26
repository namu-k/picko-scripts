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
