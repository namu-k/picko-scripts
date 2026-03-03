"""
Pytest configuration and shared fixtures
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session", autouse=True)
def ensure_mock_vault_exists():
    """실제 config를 쓰는 테스트를 위해 mock_vault 디렉터리를 프로젝트 루트에 생성."""
    mock_vault = PROJECT_ROOT / "mock_vault"
    (mock_vault / "Inbox" / "Inputs").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Inbox" / "Inputs" / "_digests").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Content" / "Longform").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Content" / "Packs" / "twitter").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Content" / "Packs" / "linkedin").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Content" / "Packs" / "newsletter").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Assets" / "Images" / "_prompts").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Logs" / "Publish").mkdir(parents=True, exist_ok=True)
    (mock_vault / "Archive").mkdir(parents=True, exist_ok=True)


@pytest.fixture
def temp_vault_dir(tmp_path):
    """임시 Vault 디렉토리"""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Inbox" / "Inputs").mkdir(parents=True)
    (vault / "Inbox" / "Inputs" / "_digests").mkdir(parents=True)
    (vault / "Content" / "Longform").mkdir(parents=True)
    (vault / "Content" / "Packs" / "twitter").mkdir(parents=True)
    (vault / "Content" / "Packs" / "linkedin").mkdir(parents=True)
    (vault / "Content" / "Packs" / "newsletter").mkdir(parents=True)
    (vault / "Assets" / "Images" / "_prompts").mkdir(parents=True)
    (vault / "Logs" / "Publish").mkdir(parents=True)
    (vault / "Archive").mkdir(parents=True)
    return vault


@pytest.fixture
def mock_config(temp_vault_dir):
    """Mock config 객체"""
    config = MagicMock()
    config.vault.root = str(temp_vault_dir)
    config.vault.inbox = "Inbox/Inputs"
    config.vault.digests = "Inbox/Inputs/_digests"
    config.vault.content = "Content"
    config.vault.longform = "Content/Longform"
    config.vault.packs = "Content/Packs"
    config.vault.images_prompts = "Assets/Images/_prompts"
    config.vault.archive = "Archive"
    config.vault.logs_publish = "Logs/Publish"

    config.llm.provider = "openai"
    config.llm.model = "gpt-4o-mini"
    config.llm.temperature = 0.7
    config.llm.api_key_env = "OPENAI_API_KEY"

    config.summary_llm.provider = "ollama"
    config.summary_llm.model = "deepseek-r1:7b"

    config.writer_llm.provider = "openai"
    config.writer_llm.model = "gpt-4o-mini"

    config.embedding.provider = "local"
    config.embedding.model = "BAAI/bge-m3"
    config.embedding.dimensions = 1024
    config.embedding.cache_enabled = True
    config.embedding.cache_dir = str(temp_vault_dir / "cache")

    config.scoring.weights = {"novelty": 0.3, "relevance": 0.4, "quality": 0.3}
    config.scoring.thresholds = {
        "auto_approve": 0.85,
        "auto_reject": 0.3,
        "minimum_display": 0.4,
    }
    config.generation.auto_validate = True
    config.deduplication.embedding_threshold = 0.92
    config.notification.provider = "telegram"
    config.notification.review_timeout_hours = 72

    return config


@pytest.fixture
def sample_input_data():
    """샘플 Input 데이터"""
    return {
        "id": "input_test123",
        "title": "AI와 머신러닝의 최신 트렌드",
        "source": "TechCrunch",
        "source_url": "https://techcrunch.com/ai-trends",
        "publish_date": "2026-02-15",
        "collected_at": "2026-02-15T10:00:00",
        "summary": "AI 기술이 빠르게 발전하고 있습니다.",
        "key_points": [
            "LLM 모델의 성능 향상",
            "멀티모달 AI의 등장",
            "에너지 효율성 개선",
        ],
        "excerpt": "최근 AI 연구는...",
        "tags": ["AI", "머신러닝", "LLM"],
        "score": {"novelty": 0.85, "relevance": 0.90, "quality": 0.80, "total": 0.855},
    }
