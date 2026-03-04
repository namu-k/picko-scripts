"""
SourceDiscovery 단위 테스트
"""

import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from picko.source_manager import SourceManager
from scripts import source_discovery as source_discovery_module
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

    @patch("scripts.source_discovery.feedparser.parse")
    @patch("scripts.source_discovery.httpx.Client")
    def test_search_google_news_rss_success_and_cache(self, mock_client, mock_parse, temp_sources_yml, tmp_path):
        """Google News RSS 검색 + 캐시 동작"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            mock_response = MagicMock()
            mock_response.text = "<xml />"
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            entry_alpha = MagicMock()
            entry_alpha.link = "https://alpha.com/post-1"
            entry_alpha.get.return_value = entry_alpha.link

            entry_beta = MagicMock()
            entry_beta.link = "https://beta.com/post-2"
            entry_beta.get.return_value = entry_beta.link

            entry_google = MagicMock()
            entry_google.link = "https://news.google.com/abc"
            entry_google.get.return_value = entry_google.link

            feed = MagicMock()
            feed.entries = [entry_alpha, entry_beta, entry_google]
            mock_parse.return_value = feed

            with patch.object(
                discovery,
                "_probe_rss_url",
                side_effect=["https://alpha.com/feed", None],
            ):
                first = discovery._search_google_news_rss("ai")
                second = discovery._search_google_news_rss("ai")

            assert len(first) == 1
            assert first[0].url in ("https://alpha.com", "https://beta.com")
            assert first[0].discovery_method == "google_news"
            assert second == first
            assert mock_client_instance.get.call_count == 1

    @patch("scripts.source_discovery.httpx.Client")
    def test_search_google_news_rss_error_returns_empty(self, mock_client, temp_sources_yml, tmp_path):
        """Google News RSS 예외 시 빈 결과"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            mock_client.return_value.__enter__.side_effect = RuntimeError("network")
            assert discovery._search_google_news_rss("ai") == []

    def test_search_tavily_without_api_key_returns_empty(self, temp_sources_yml, tmp_path):
        """Tavily API 키 없으면 skip"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)
            discovery.tavily_api_key = ""

            assert discovery._search_tavily("ai") == []

    def test_search_tavily_daily_limit_returns_empty(self, temp_sources_yml, tmp_path):
        """Tavily 일일 한도 초과 시 skip"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)
            discovery.tavily_api_key = "test-key"
            discovery.tavily_daily_count = discovery.tavily_daily_limit

            assert discovery._search_tavily("ai") == []

    @patch("scripts.source_discovery.time.sleep")
    @patch("scripts.source_discovery.httpx.Client")
    def test_search_tavily_success(self, mock_client, _mock_sleep, temp_sources_yml, tmp_path):
        """Tavily 검색 성공 경로"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)
            discovery.tavily_api_key = "test-key"

            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "url": "https://foo.com/article",
                        "title": "Foo",
                        "content": "desc",
                    },
                    {"url": "", "title": "No URL"},
                    {
                        "url": "https://bar.com/article",
                        "title": "Bar",
                        "content": "skip",
                    },
                ]
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            with patch.object(discovery, "_probe_rss_url", side_effect=["https://foo.com/feed", None]):
                candidates = discovery._search_tavily("ai")

            assert len(candidates) == 1
            assert candidates[0].url == "https://foo.com/article"
            assert candidates[0].discovery_method == "tavily"
            assert discovery.tavily_daily_count == 1

    @patch("scripts.source_discovery.time.sleep")
    @patch("scripts.source_discovery.httpx.Client")
    def test_search_tavily_error_returns_empty(self, mock_client, _mock_sleep, temp_sources_yml, tmp_path):
        """Tavily 예외 시 빈 결과"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)
            discovery.tavily_api_key = "test-key"

            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = RuntimeError("api error")

            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            assert discovery._search_tavily("ai") == []
            assert discovery.tavily_daily_count == 0

    @patch("scripts.source_discovery.httpx.Client")
    def test_probe_rss_url_common_path_success(self, mock_client, temp_sources_yml, tmp_path):
        """HTML 링크 없을 때 common path로 RSS 탐지"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            html_response = MagicMock(status_code=200, text="<html></html>")
            head_responses = [
                MagicMock(status_code=404, headers={}),
                MagicMock(status_code=200, headers={"content-type": "application/rss+xml"}),
            ]

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = html_response
            mock_client_instance.head.side_effect = head_responses
            mock_client.return_value.__enter__.return_value = mock_client_instance

            rss_url = discovery._probe_rss_url("example.com")
            assert rss_url == "https://example.com/rss"

    @patch("scripts.source_discovery.httpx.Client")
    def test_probe_rss_url_not_found_returns_none(self, mock_client, temp_sources_yml, tmp_path):
        """RSS를 찾지 못하면 None 반환"""
        with patch("scripts.source_discovery.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.sources_file = str(temp_sources_yml)
            mock_config.accounts_dir = str(tmp_path / "accounts")
            mock_get_config.return_value = mock_config

            sm = SourceManager(temp_sources_yml)
            discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

            html_response = MagicMock(status_code=200, text="<html></html>")
            head_response = MagicMock(status_code=200, headers={"content-type": "text/html"})

            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = html_response
            mock_client_instance.head.return_value = head_response
            mock_client.return_value.__enter__.return_value = mock_client_instance

            assert discovery._probe_rss_url("example.com") is None

    @patch("scripts.source_discovery.get_config")
    def test_evaluate_candidates_scores_and_sorts(self, mock_get_config, temp_sources_yml, temp_account_yml):
        """후보 점수 부여 및 정렬"""
        mock_config = MagicMock()
        mock_config.sources_file = str(temp_sources_yml)
        mock_config.accounts_dir = str(temp_account_yml)
        mock_get_config.return_value = mock_config

        sm = SourceManager(temp_sources_yml)
        discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

        candidates = [
            SourceCandidate(
                url="https://techcrunch.com/story",
                title="스타트업 시장 분석",
                source_type="rss",
                discovery_method="test",
                keyword="스타트업",
            ),
            SourceCandidate(
                url="https://unknown.com/story",
                title="일반 뉴스",
                source_type="rss",
                discovery_method="test",
                keyword="스타트업",
            ),
        ]

        scored = discovery._evaluate_candidates(candidates)
        assert scored[0].relevance_score > scored[1].relevance_score
        assert scored[0].relevance_score == pytest.approx(1.0)
        assert scored[1].relevance_score == pytest.approx(0.5)

    @patch("scripts.source_discovery.get_config")
    def test_dedupe_candidates_uses_rss_url_for_uniqueness(self, mock_get_config, temp_sources_yml, tmp_path):
        """중복 체크 시 rss_url 우선 사용"""
        mock_config = MagicMock()
        mock_config.sources_file = str(temp_sources_yml)
        mock_config.accounts_dir = str(tmp_path / "accounts")
        mock_get_config.return_value = mock_config

        sm = SourceManager(temp_sources_yml)
        discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

        candidates = [
            SourceCandidate(
                url="https://a.com/post1",
                title="A1",
                source_type="rss",
                discovery_method="test",
                keyword="test",
                rss_url="https://a.com/feed",
            ),
            SourceCandidate(
                url="https://a.com/post2",
                title="A2",
                source_type="rss",
                discovery_method="test",
                keyword="test",
                rss_url="https://a.com/feed",
            ),
        ]

        unique = discovery._dedupe_candidates(candidates, existing_urls=set())
        assert len(unique) == 1
        assert unique[0].rss_url == "https://a.com/feed"

    @patch("scripts.source_discovery.get_config")
    def test_run_dry_run_pipeline(self, mock_get_config, temp_sources_yml, tmp_path):
        """run() dry-run 파이프라인"""
        mock_config = MagicMock()
        mock_config.sources_file = str(temp_sources_yml)
        mock_config.accounts_dir = str(tmp_path / "accounts")
        mock_get_config.return_value = mock_config

        sm = MagicMock()
        sm.get_urls.return_value = set()
        discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

        c1 = SourceCandidate(
            url="https://a.com",
            title="A",
            source_type="rss",
            discovery_method="google_news",
            keyword="ai",
        )
        c2 = SourceCandidate(
            url="https://b.com",
            title="B",
            source_type="rss",
            discovery_method="tavily",
            keyword="ai",
        )
        c1.relevance_score = 0.9
        c2.relevance_score = 0.3

        with (
            patch.object(discovery, "_search_google_news_rss", return_value=[c1]),
            patch.object(discovery, "_search_tavily", return_value=[c2]),
            patch.object(discovery, "_search_substack", return_value=[]),
            patch.object(discovery, "_dedupe_candidates", return_value=[c1, c2]),
            patch.object(discovery, "_evaluate_candidates", return_value=[c1, c2]),
            patch.object(discovery, "_save_result") as mock_save,
        ):
            result = discovery.run(dry_run=True, keywords=["ai"])

        assert result.discovered == 2
        assert result.already_known == 0
        assert result.below_threshold == 1
        assert result.added_as_pending == 1
        assert result.errors == []
        sm.add_candidate.assert_not_called()
        mock_save.assert_called_once()

    @patch("scripts.source_discovery.get_config")
    def test_run_non_dry_run_adds_pending_and_collects_errors(self, mock_get_config, temp_sources_yml, tmp_path):
        """run() 저장 경로 + 키워드별 에러 수집"""
        mock_config = MagicMock()
        mock_config.sources_file = str(temp_sources_yml)
        mock_config.accounts_dir = str(tmp_path / "accounts")
        mock_get_config.return_value = mock_config

        sm = MagicMock()
        sm.get_urls.return_value = set()
        discovery = SourceDiscovery(account_id="test_account", source_manager=sm)

        candidate = SourceCandidate(
            url="https://ok.com",
            title="ok",
            source_type="rss",
            discovery_method="google_news",
            keyword="k2",
            rss_url="https://ok.com/feed",
        )
        candidate.relevance_score = 0.8

        with (
            patch.object(
                discovery,
                "_search_google_news_rss",
                side_effect=[RuntimeError("boom"), [candidate]],
            ),
            patch.object(discovery, "_search_tavily", return_value=[]),
            patch.object(discovery, "_search_substack", return_value=[]),
            patch.object(discovery, "_dedupe_candidates", return_value=[candidate]),
            patch.object(discovery, "_evaluate_candidates", return_value=[candidate]),
            patch.object(discovery, "_generate_source_id", return_value="discovered_ok_com"),
            patch.object(discovery, "_save_result"),
        ):
            result = discovery.run(dry_run=False, keywords=["k1", "k2"])

        assert len(result.errors) == 1
        assert "k1" in result.errors[0]
        assert result.added_as_pending == 1
        sm.add_candidate.assert_called_once()

    @patch("scripts.source_discovery.get_config")
    def test_save_result_writes_files_and_cleans_old_logs(self, mock_get_config, temp_sources_yml, tmp_path):
        """결과 저장 + 오래된 로그 정리"""
        mock_config = MagicMock()
        mock_config.sources_file = str(temp_sources_yml)
        mock_config.accounts_dir = str(tmp_path / "accounts")
        mock_get_config.return_value = mock_config

        sm = SourceManager(temp_sources_yml)
        discovery = SourceDiscovery(account_id="test_account", source_manager=sm)
        discovery.discovery_dir = tmp_path / "discovery"
        (discovery.discovery_dir / "logs").mkdir(parents=True, exist_ok=True)

        old_date = (source_discovery_module.datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        old_log = discovery.discovery_dir / "logs" / f"{old_date}.log"
        old_log.write_text("old", encoding="utf-8")

        # source_discovery.py에서 datetime.timedelta를 import하지 않아 테스트에서 주입
        with patch.object(source_discovery_module, "timedelta", timedelta, create=True):
            result = DiscoveryResult(
                run_id="dr_test",
                account="test_account",
                timestamp="2026-02-27T00:00:00",
                keywords_used=["ai"],
                discovered=1,
                added_as_pending=1,
                already_known=0,
                below_threshold=0,
                errors=["e1"],
            )
            discovery._save_result(result)

        assert (discovery.discovery_dir / "latest_run.yml").exists()
        assert not old_log.exists()

    def test_main_dry_run(self, capsys):
        """CLI --dry-run 실행"""
        result = DiscoveryResult(
            run_id="dr_test",
            account="acct",
            timestamp="2026-02-27T00:00:00",
            keywords_used=["ai", "startup"],
            discovered=3,
            added_as_pending=2,
            already_known=1,
            below_threshold=0,
            errors=[],
        )

        with (
            patch("scripts.source_discovery.SourceDiscovery") as mock_discovery_cls,
            patch(
                "sys.argv",
                [
                    "source_discovery",
                    "--account",
                    "acct",
                    "--dry-run",
                    "--keywords",
                    "ai,startup",
                ],
            ),
        ):
            mock_discovery = MagicMock()
            mock_discovery.run.return_value = result
            mock_discovery_cls.return_value = mock_discovery

            source_discovery_module.main()

        output = capsys.readouterr().out
        assert "Discovery Results" in output
        assert "Account: acct" in output

    def test_main_review_and_approve_reject(self, capsys):
        """CLI --review / --approve / --reject"""
        pending_item = MagicMock()
        pending_item.id = "s1"
        pending_item.url = "https://example.com"
        pending_item.rss_url = "https://example.com/feed"
        pending_item.discovery_keyword = "ai"
        pending_item.discovered_at = "2026-02-27"

        with patch("scripts.source_discovery.SourceDiscovery") as mock_discovery_cls:
            mock_discovery = MagicMock()
            mock_discovery.review_pending.return_value = [pending_item]
            mock_discovery.approve.return_value = 2
            mock_discovery.reject.return_value = 1
            mock_discovery_cls.return_value = mock_discovery

            with patch("sys.argv", ["source_discovery", "--account", "acct", "--review"]):
                source_discovery_module.main()
            with patch(
                "sys.argv",
                ["source_discovery", "--account", "acct", "--approve", "a", "b"],
            ):
                source_discovery_module.main()
            with patch("sys.argv", ["source_discovery", "--account", "acct", "--reject", "x"]):
                source_discovery_module.main()

        output = capsys.readouterr().out
        assert "Pending Sources" in output
        assert "Approved 2 sources" in output
        assert "Rejected 1 sources" in output
