"""
SourceDiscovery 단위 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from picko.source_manager import SourceManager
from scripts.source_discovery import DiscoveryResult, SourceCandidate, SourceDiscovery


@pytest.fixture
def temp_sources_yml(tmp_path):
    """임시 sources.yml"""
    sources_data = {
        "sources": [
            {
                "id": "existing",
                "type": "rss",
                "url": "https://existing.com/feed",
                "category": "test",
                "enabled": True,
            }
        ],
        "categories": {},
    }
    sources_file = tmp_path / "sources.yml"
    with open(sources_file, "w", encoding="utf-8") as f:
        yaml.dump(sources_data, f)
    return sources_file


@pytest.fixture
def temp_account_yml(tmp_path):
    """임시 계정 프로필"""
    accounts_dir = tmp_path / "accounts"
    accounts_dir.mkdir()

    account_data = {
        "account_id": "test_account",
        "interests": {
            "primary": ["스타트업", "투자"],
            "secondary": ["마케팅"],
        },
        "keywords": {
            "high_relevance": ["창업자", "VC"],
            "medium_relevance": ["성장"],
        },
        "trusted_sources": ["TechCrunch", "Y Combinator"],
    }

    account_file = accounts_dir / "test_account.yml"
    with open(account_file, "w", encoding="utf-8") as f:
        yaml.dump(account_data, f)

    return accounts_dir


class TestSourceCandidate:
    """SourceCandidate dataclass 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        candidate = SourceCandidate(
            url="https://example.com",
            title="Test",
            source_type="rss",
            discovery_method="google_news",
            keyword="test",
        )

        assert candidate.rss_url is None
        assert candidate.description == ""
        assert candidate.relevance_score == 0.0
        assert candidate.platform is None


class TestDiscoveryResult:
    """DiscoveryResult dataclass 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = DiscoveryResult(
            run_id="test_001",
            account="test",
            timestamp="2026-02-25T10:00:00",
        )

        assert result.keywords_used == []
        assert result.discovered == 0
        assert result.added_as_pending == 0
        assert result.errors == []


class TestSourceDiscovery:
    """SourceDiscovery 클래스 테스트"""

    @patch("scripts.source_discovery.get_config")
    def test_extract_keywords(self, mock_get_config, temp_sources_yml, temp_account_yml, tmp_path):
        """키워드 추출"""
        # Mock config
        mock_config = MagicMock()
        mock_config.sources_file = str(temp_sources_yml)
        mock_config.accounts_dir = str(temp_account_yml)
        mock_get_config.return_value = mock_config

        sm = SourceManager(temp_sources_yml)
        discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

        keywords = discovery._extract_keywords()

        # primary + high_relevance 키워드
        assert "스타트업" in keywords
        assert "투자" in keywords
        assert "창업자" in keywords
        assert "VC" in keywords

    @patch("scripts.source_discovery.httpx.Client")
    def test_probe_rss_url_success(self, mock_client, temp_sources_yml, tmp_path):
        """RSS URL 탐지 성공"""
        # Mock config
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            # Mock HTTP response with RSS link
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '<link type="application/rss+xml" href="/feed" />'

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.head.return_value = MagicMock(status_code=200)
            mock_client.return_value.__enter__.return_value = mock_client_instance

            rss_url = discovery._probe_rss_url("example.com")

            assert rss_url == "https://example.com/feed"

    def test_dedupe_candidates(self, temp_sources_yml, tmp_path):
        """후보 중복 제거"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            sm.load()
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            candidates = [
                SourceCandidate(
                    url="https://existing.com/feed",
                    title="Existing",
                    source_type="rss",
                    discovery_method="test",
                    keyword="test",
                ),
                SourceCandidate(
                    url="https://new.com",
                    title="New",
                    source_type="rss",
                    discovery_method="test",
                    keyword="test",
                ),
                SourceCandidate(
                    url="https://new.com",  # 중복
                    title="New Duplicate",
                    source_type="rss",
                    discovery_method="test",
                    keyword="test",
                ),
            ]

            existing_urls = sm.get_urls()
            unique = discovery._dedupe_candidates(candidates, existing_urls)

            # existing.com/feed은 기존 URL이므로 제외
            # new.com 중복은 하나만 유지
            assert len(unique) == 1
            assert unique[0].url == "https://new.com"

    def test_generate_source_id(self, temp_sources_yml, tmp_path):
        """소스 ID 생성"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            candidate = SourceCandidate(
                url="https://sub.example.com/feed",
                title="Test",
                source_type="rss",
                discovery_method="test",
                keyword="test",
            )

            source_id = discovery._generate_source_id(candidate)

            assert source_id.startswith("discovered_")
            assert "sub_example_com" in source_id

    @patch("scripts.source_discovery.httpx.Client")
    def test_search_substack(self, mock_client, temp_sources_yml, tmp_path):
        """Substack 검색"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            # Mock Substack search response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = """
            <html>
            <a href="https://newsletter1.substack.com">Newsletter 1</a>
            <a href="https://newsletter2.substack.com">Newsletter 2</a>
            </html>
            """

            # Mock RSS feed check
            mock_head_response = MagicMock()
            mock_head_response.status_code = 200
            mock_head_response.headers = {"content-type": "application/rss+xml"}

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.head.return_value = mock_head_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            candidates = discovery._search_substack("test")

            assert len(candidates) == 2
            assert candidates[0].source_type == "newsletter"
            assert candidates[0].platform == "substack"
