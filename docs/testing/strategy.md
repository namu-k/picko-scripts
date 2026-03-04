# 테스트 전략 (Testing Strategy)

이 문서는 Picko 스크립트 시스템의 테스트 전략을 정의합니다.
> **문서 성격**: 테스트 전략 및 패턴 가이드이며, 예시 코드는 실제 테스트와 디테일이 다를 수 있습니다.

## 목차
- [테스트 전략 개요](#테스트-전략-개요)
- [단위 테스트 전략](#단위-테스트-전략)
- [통합 테스트 시나리오](#통합-테스트-시나리오)
- [E2E 테스트 케이스](#e2e-테스트-케이스)
- [테스트 데이터 관리](#테스트-데이터-관리)
- [CI/CD 테스트 통합](#cicd-테스트-통합)
- [테스트 실행 절차](#테스트-실행-절차)

## 테스트 전략 개요

### 테스트 원칙

1. **안정성 우선**: 모든 테스트는 재현 가능하고 안정적이어야 합니다.
2. **독립성**: 테스트 간 의존성을 최소화합니다.
3. **비용 효율성**: 외부 API 호출 비용을 최적화합니다.
4. **피드백 속도**: 로컬에서 빠르게 실행 가능해야 합니다.
5. **자동화**: 모든 테스트는 자동화되어야 합니다.

### 테스트 레벨

| 레벨 | 목적 | 범위 | 실행 시점 |
|------|------|------|----------|
| 단위 테스트 | 컴포넌트 개별 검증 | 함수/메소드 | 개발 시점 |
| 통합 테스트 | 컴포넌트 상호작용 검증 | 모듈 간 통합 | 빌드 시점 |
| E2E 테스트 | 전체 시스템 워크플로우 검증 | 시스템 전체 | 배포 전 |
| 성능 테스트 | 부하/스트레스 테스트 | 시스템 전체 | 배포 전 |

### 테스트 환경

- **로컬 테스트**: 개발 환경에서 빠른 피드백
- **CI 테스트**: PR 병합 전 검증
- **스테이징 테스트**: 실제 환경 테스트
- **모의 테스트**: 외부 의존성 모의

## 단위 테스트 전략

### 테스트 범위

핵심 모듈에 대한 단위 테스트를 작성합니다:

1. **picko/config.py**: 설정 로드 및 검증
2. **picko/llm_client.py**: LLM API 호출
3. **picko/vault_io.py**: Obsidian Vault I/O
4. **picko/scoring.py**: 콘텐츠 점수 계산
5. **picko/embedding.py**: 임베딩 생성
6. **picko/source_manager.py**: RSS 소스 관리

### 테스트 프레임워크 구성

```python
# tests/conftest.py
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

@pytest.fixture
def temp_vault_dir():
    """임시 테스트 Vault 디렉토리"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_config():
    """모의 테스트용 설정"""
    return {
        'vault': {
            'root': '/tmp/test_vault'
        },
        'summary_llm': {
            'provider': 'openai',
            'model': 'gpt-4o-mini'
        },
        'embedding': {
            'cache_dir': '/tmp/test_cache'
        }
    }

@pytest.fixture
def sample_rss_data():
    """샘플 RSS 데이터"""
    return {
        'title': 'Sample RSS Feed',
        'description': 'Sample description',
        'link': 'https://example.com/article1',
        'pub_date': '2026-03-01T00:00:00Z',
        'content': 'Sample content...',
        'author': 'Test Author'
    }
```

### 핵심 모듈 테스트 예시

```python
# tests/test_config.py
import pytest
from picko.config import Config, load_config
from pathlib import Path

def test_config_creation():
    """Config 클래스 생성 테스트"""
    config = Config()
    assert config.vault.root is not None
    assert config.summary_llm is not None
    assert config.embedding.cache_dir is not None

def test_load_config_from_file(mock_config):
    """YAML 파일에서 설정 로드 테스트"""
    with patch('picko.config._load_file', return_value=mock_config):
        config = load_config()
        assert config.vault.root == '/tmp/test_vault'
        assert config.summary_llm.provider == 'openai'

def test_config_validation():
    """설정 검증 테스트"""
    config = Config()
    with pytest.raises(ValueError):
        config.vault.root = None  # 필수 필드 누락
```

```python
# tests/test_llm_client.py
import pytest
from unittest.mock import Mock, patch
from picko.llm_client import LLMClient

@pytest.fixture
def llm_client():
    """LLM 클라이언트 테스트용 fixture"""
    return LLMClient(
        provider='openai',
        model='gpt-4o-mini',
        api_key='test-key'
    )

@pytest.mark.asyncio
async def test_llm_completion(llm_client):
    """LLM 응답 생성 테스트"""
    mock_response = Mock()
    mock_response.choices = [Mock(text='Generated text')]

    with patch('openai.ChatCompletion.acreate', return_value=mock_response):
        result = await llm_client.completion('Prompt')
        assert result == 'Generated text'

@pytest.mark.asyncio
async def test_llm_error_handling(llm_client):
    """LLM 오류 처리 테스트"""
    with patch('openai.ChatCompletion.acreate', side_effect=Exception('API Error')):
        with pytest.raises(Exception) as exc_info:
            await llm_client.completion('Prompt')
        assert 'API Error' in str(exc_info.value)
```

```python
# tests/test_scoring.py
import pytest
from picko.scoring import ContentScorer

def test_score_content(sample_rss_data):
    """콘텐츠 점수 계산 테스트"""
    scorer = ContentScorer()
    score = scorer.score(
        {
            'title': sample_rss_data['title'],
            'text': sample_rss_data['content'],
            'source': sample_rss_data['link'],
        }
    )
    assert 0 <= score.total <= 1
    assert 0 <= score.novelty <= 1
    assert 0 <= score.relevance <= 1
    assert 0 <= score.quality <= 1
```

### 모의 객체 사용 패턴

```python
# tests/test_vault_io.py
import pytest
from unittest.mock import Mock, patch
from picko.vault_io import VaultIO

@pytest.fixture
def vault_io():
    return VaultIO('/tmp/vault')

def test_read_file(vault_io, temp_vault_dir):
    """Vault 파일 읽기 테스트"""
    # 테스트 파일 생성
    test_file = temp_vault_dir / 'test.md'
    test_file.write_text('---\ntitle: Test\n---\nContent')

    with patch('picko.vault_io.VaultIO.root', temp_vault_dir):
        content = vault_io.read_file('test.md')
        assert content['title'] == 'Test'
        assert content['content'] == 'Content'

def test_write_file(vault_io, temp_vault_dir):
    """Vault 파일 쓰기 테스트"""
    with patch('picko.vault_io.VaultIO.root', temp_vault_dir):
        vault_io.write_file('test.md', {
            'title': 'Test',
            'content': 'Content'
        })

        # 파일 확인
        test_file = temp_vault_dir / 'test.md'
        assert test_file.exists()
        assert '---\ntitle: Test\n---\nContent' in test_file.read_text()
```

## 통합 테스트 시나리오

### RSS 수집 파이프라인 테스트

```python
# tests/integration/test_rss_pipeline.py
import pytest
import tempfile
import json
from pathlib import Path
from scripts.daily_collector import DailyCollector
from picko.source_manager import SourceManager

@pytest.fixture
def test_sources():
    return [{
        'id': 'techcrunch',
        'name': 'TechCrunch',
        'url': 'https://techcrunch.com/feed',
        'category': 'tech',
        'enabled': True
    }]

@pytest.fixture
def temp_output_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.mark.integration
def test_rss_collection_workflow(test_sources, temp_output_dir):
    """RSS 수집 워크플로우 통합 테스트"""
    # 소스 관리자 초기화
    source_manager = SourceManager()
    source_manager.load_sources(test_sources)

    # 수집기 초기화
    collector = DailyCollector(
        sources=test_sources,
        output_dir=temp_output_dir,
        dry_run=True  # 실제 API 호출 방지
    )

    # 워크플로우 실행
    with patch('scripts.daily_collector.RSSCollector') as mock_collector:
        mock_collector_instance = Mock()
        mock_collector.return_value = mock_collector_instance

        # RSS 수집 모의
        mock_collector_instance.collect.return_value = [{
            'id': 'test-1',
            'title': 'Test Article',
            'content': 'Test content...',
            'url': 'https://example.com/test',
            'pub_date': '2026-03-01T00:00:00Z'
        }]

        # 워크플로우 실행
        result = collector.run()

        # 결과 검증
        assert result['status'] == 'success'
        assert len(result['items']) == 1
        assert result['items'][0]['title'] == 'Test Article'
```

### 콘텐츠 생성 파이프라인 테스트

```python
# tests/integration/test_content_generation.py
import pytest
from unittest.mock import Mock, patch
from scripts.generate_content import ContentGenerator

@pytest.fixture
def sample_input():
    return {
        'id': 'test-1',
        'title': 'Test Article',
        'content': 'Sample RSS content',
        'tags': ['tech', 'ai'],
        'summary': 'This is a test article',
        'score': 85,
        'auto_ready': True
    }

@pytest.mark.integration
def test_content_generation_workflow(sample_input):
    """콘텐츠 생성 워크플로우 테스트"""
    generator = ContentGenerator()

    with patch('picko.llm_client.LLMClient') as mock_llm:
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance

        # LLM 응답 모의
        mock_llm_instance.completion.side_effect = [
            'Generated longform article content...',  # longform
            'Generated tweet thread...',  # twitter
            'Generated newsletter content...',  # newsletter
            'Generated image prompt...'  # image
        ]

        # 생성 실행
        result = generator.generate_content(sample_input, ['longform', 'twitter'])

        # 결과 검증
        assert result['longform']['status'] == 'success'
        assert result['twitter']['status'] == 'success'
        assert 'Generated longform article content' in result['longform']['content']
        assert 'Generated tweet thread' in result['twitter']['content']
```

### 다중 환경 테스트

```python
# tests/integration/test_environment.py
import pytest
import os
from pathlib import Path

@pytest.mark.parametrize("env_name", ["local", "staging", "production"])
def test_configuration_in_different_environments(env_name):
    """다른 환경에서의 설정 테스트"""
    env_vars = {
        'local': {
            'VAULT_ROOT': '/tmp/vault',
            'LOG_LEVEL': 'DEBUG'
        },
        'staging': {
            'VAULT_ROOT': '/data/staging_vault',
            'LOG_LEVEL': 'INFO'
        },
        'production': {
            'VAULT_ROOT': '/data/production_vault',
            'LOG_LEVEL': 'WARNING'
        }
    }

    # 환경 변수 설정
    for key, value in env_vars[env_name].items():
        os.environ[key] = value

    # 설정 로드
    from picko.config import load_config
    config = load_config()

    # 검증
    assert config.vault.root == env_vars[env_name]['VAULT_ROOT']
    assert config.log_level == env_vars[env_name]['LOG_LEVEL']
```

## E2E 테스트 케이스

### 테스트 환경 설정

```python
# tests/e2e/test_env_setup.py
import pytest
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.common.by import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def test_setup():
    """E2E 테스트 환경 설정"""
    # 테스트용 컨테이너 시작
    try:
        subprocess.run(['docker-compose', '-f', 'docker-compose.test.yml', 'up', '-d'], check=True)
        time.sleep(10)  # 컨테이너 시작 대기

        # Selenium 웹드라이버 설정
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)

        yield {
            'driver': driver,
            'base_url': 'http://localhost:8080'
        }

        # 클린업
        driver.quit()
        subprocess.run(['docker-compose', '-f', 'docker-compose.test.yml', 'down'], check=True)

    except subprocess.CalledProcessError as e:
        raise Exception(f"Test environment setup failed: {e}")
```

### 완전한 워크플로우 테스트

```python
# tests/e2e/test_full_workflow.py
import pytest
import json
from pathlib import Path

@pytest.mark.e2e
def test_daily_collection_to_content_generation(test_setup):
    """RSS 수집부터 콘텐츠 생성까지의 전체 워크플로우 테스트"""
    driver = test_setup['driver']
    base_url = test_setup['base_url']

    # 1. RSS 수집 테스트
    driver.get(f"{base_url}/collect")

    # 수집 버튼 클릭
    collect_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "collect-button"))
    )
    collect_button.click()

    # 수집 완료 대기
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, "collection-complete"))
    )

    # 결과 확인
    status = driver.find_element(By.ID, "status").text
    assert "SUCCESS" in status

    # 2. 콘텐츠 생성 테스트
    driver.get(f"{base_url}/generate")

    # 생성 버튼 클릭
    generate_button = driver.find_element(By.ID, "generate-button")
    generate_button.click()

    # 생성 완료 대기
    WebDriverWait(driver, 300).until(
        EC.presence_of_element_located((By.ID, "generation-complete"))
    )

    # 결과 확인
    result_element = driver.find_element(By.ID, "result")
    assert "COMPLETED" in result_element.text

    # 3. 결과 검증
    content_count = len(driver.find_elements(By.CLASS_NAME, "content-item"))
    assert content_count > 0

    # 콘텐츠 다운로드 테스트
    download_button = driver.find_element(By.ID, "download-all")
    download_button.click()

    # 다운로드 완료 확인
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "download-complete"))
    )
```

### API 통합 테스트

```python
# tests/e2e/test_api_integration.py
import pytest
import requests
import json

@pytest.fixture
def api_client():
    return requests.Session()
    # 실제 API 클라이언트 테스트 시 인증 설정

@pytest.mark.e2e
def test_api_endpoints(api_client):
    """API 엔드포인트 통합 테스트"""
    base_url = "http://localhost:8080/api/v1"

    # 1. Health check
    response = api_client.get(f"{base_url}/health")
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

    # 2. RSS 수집
    payload = {
        'sources': ['techcrunch', 'ai_news'],
        'date': '2026-03-04'
    }
    response = api_client.post(
        f"{base_url}/collect",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 202  # Accepted
    job_id = response.json()['job_id']

    # 3. 작업 상태 확인
    response = api_client.get(f"{base_url}/jobs/{job_id}")
    assert response.status_code == 200
    job_data = response.json()
    assert job_data['status'] in ['pending', 'running', 'completed']

    # 4. 콘텐츠 생성
    response = api_client.post(
        f"{base_url}/generate",
        json={'auto_ready': True, 'types': ['longform', 'twitter']},
        headers={'Content-Type': 'application/json'}
    )
    assert response.status_code == 202
    generation_job_id = response.json()['job_id']

    # 5. 결과 확인
    max_retries = 10
    for _ in range(max_retries):
        response = api_client.get(f"{base_url}/jobs/{generation_job_id}")
        if response.json()['status'] == 'completed':
            break
        time.sleep(5)

    response = api_client.get(f"{base_url}/content/latest")
    assert response.status_code == 200
    content = response.json()
    assert len(content) > 0
```

### 스트레스 테스트

```python
# tests/e2e/test_stress.py
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.stress
def test_concurrent_rss_collection():
    """동시 RSS 수집 테스트"""
    results = []
    errors = []

    def collect_feed(source_id):
        try:
            result = daily_collector.collect(source_id)
            results.append(result)
        except Exception as e:
            errors.append(str(e))

    # 10개 스레드로 동시 수집
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(collect_feed, f'source-{i}') for i in range(10)]

        # 모든 작업 완료 대기
        for future in futures:
            future.result(timeout=60)

    # 결과 검증
    assert len(errors) == 0
    assert len(results) == 10
    for result in results:
        assert result['status'] == 'success'

@pytest.mark.stress
def test_memory_usage():
    """메모리 사용량 테스트"""
    import psutil
    process = psutil.Process()

    # 초기 메모리 확인
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # 대량 데이터 처리
    for i in range(100):
        large_content = 'A' * (10 * 1024)  # 10KB
        processed_content = process_content(large_content)

    # 최종 메모리 확인
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # 메모리 증가율 검증 (증가가 100MB 미만이어야 함)
    assert memory_increase < 100
```

## 테스트 데이터 관리

### 테스트 데이터 구조

```
tests/
├── data/
│   ├── rss_samples/
│   │   ├── techcrunch.xml
│   │   ├── ai_news.xml
│   │   └── sample_rss.json
│   ├── vault_content/
│   │   ├── sample_input.md
│   │   ├── expected_output.md
│   │   └── frontmatter_examples/
│   └── test_fixtures/
│       ├── valid_config.yml
│       ├── invalid_config.yml
│       └── sample_accounts.yml
└── temp/
    └── # 테스트 실행 시 생성되는 임시 파일
```

### 테스트 데이터 예시

```xml
<!-- tests/data/rss_samples/techcrunch.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>TechCrunch</title>
        <description>Latest tech news</description>
        <link>https://techcrunch.com</link>

        <item>
            <title>OpenAI releases GPT-5 with improved reasoning</title>
            <description>OpenAI announced today that GPT-5 features significantly improved reasoning capabilities...</description>
            <link>https://techcrunch.com/2026/03/04/openai-gpt5-reasoning/</link>
            <pubDate>Mon, 04 Mar 2026 12:00:00 GMT</pubDate>
            <category>AI</category>
            <guid>https://techcrunch.com/2026/03/04/openai-gpt5-reasoning/</guid>
        </item>

        <item>
            <title>Microsoft invests $10B in Anthropic</title>
            <description>Microsoft announced a $10 billion investment in Anthropic to advance AI safety research...</description>
            <link>https://techcrunch.com/2026/03/04/microsoft-anthropic-investment/</link>
            <pubDate>Mon, 04 Mar 2026 11:30:00 GMT</pubDate>
            <category>Business</category>
            <guid>https://techcrunch.com/2026/03/04/microsoft-anthropic-investment/</guid>
        </item>
    </channel>
</rss>
```

```yaml
# tests/data/test_fixtures/valid_config.yml
vault:
  root: /tmp/test_vault

llm:
  summary_llm:
    provider: openai
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
  embedding:
    provider: local
    model: BAAI/bge-m3

cache:
  embedding_dir: /tmp/test_cache
  max_size: 1000000

log_level: DEBUG
log_dir: /tmp/test_logs
```

```markdown
<!-- tests/data/vault_content/sample_input.md -->
---
title: Sample RSS Article
source: techcrunch
tags:
  - AI
  - Technology
  - Machine Learning
summary: This is a sample article about AI technology
score: 85
auto_ready: true
pub_date: 2026-03-04T12:00:00Z
---

# Sample Article Title

This is a sample article content generated from RSS feeds. It contains various sections and paragraphs to simulate real content.

## Introduction

This article introduces the topic of AI technology and its impact on society.

## Main Content

The main content section discusses various aspects of AI technology including machine learning, natural language processing, and computer vision.

## Conclusion

The article concludes with future outlook and recommendations for further reading.
```

### 테스트 데이터 관리 도구

```python
# tests/utils/test_data_manager.py
import json
import yaml
from pathlib import Path
from typing import Dict, Any

class TestDataManager:
    """테스트 데이터 관리자"""

    def __init__(self, base_path: Path):
        self.base_path = base_path

    def load_rss_sample(self, filename: str) -> Dict[str, Any]:
        """RSS 샘플 데이터 로드"""
        return self._load_json(self.base_path / 'rss_samples' / filename)

    def load_config_fixture(self, filename: str) -> Dict[str, Any]:
        """설정 테스트 데이터 로드"""
        return self._load_yaml(self.base_path / 'test_fixtures' / filename)

    def load_vault_content(self, filename: str) -> str:
        """Vault 콘텐츠 로드"""
        return (self.base_path / 'vault_content' / filename).read_text()

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """JSON 파일 로드"""
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """YAML 파일 로드"""
        with path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f)

# 사용 예시
test_data = TestDataManager(Path(__file__).parent / 'data')
rss_data = test_data.load_rss_sample('techcrunch.json')
config = test_data.load_config_fixture('valid_config.yml')
content = test_data.load_vault_content('sample_input.md')
```

### 테스트 데이터 정리

```python
# tests/utils/test_cleanup.py
import os
import shutil
from pathlib import Path

def cleanup_test_environment():
    """테스트 환경 정리"""
    temp_dirs = [
        '/tmp/test_vault',
        '/tmp/test_cache',
        '/tmp/test_logs',
        './test_output'
    ]

    for temp_dir in temp_dirs:
        path = Path(temp_dir)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

def cleanup_database():
    """테스트 데이터베이스 정리"""
    # 임시 DB 파일 삭제
    db_files = [
        './test.db',
        './test.db-journal'
    ]

    for db_file in db_files:
        path = Path(db_file)
        if path.exists():
            path.unlink()

def reset_mocks():
    """모의 객체 초기화"""
    # 테스트 시 생성된 모의 상태 초기화
    from unittest import mock

    # 모든 패치 객체 중지
    mock.patch.stopall()

    # 모의된 객체 초기화
    mock.resetall()
```

## CI/CD 테스트 통합

### GitHub Actions 테스트 워크플로우

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.13]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-mock black isort flake8 mypy

    - name: Run linting
      run: |
        black --check picko/ scripts/
        isort --check-only picko/ scripts/
        flake8 picko/ scripts/
        mypy picko/

    - name: Run unit tests
      run: |
        pytest tests/unit/ --cov=picko --cov-report=xml --cov-report=html --cov-report=term-missing

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest

    needs: unit-tests

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.13

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-mock

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --tb=short
      env:
        API_KEY: ${{ secrets.API_KEY }}

  e2e-tests:
    runs-on: ubuntu-latest

    needs: integration-tests

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: picko_test
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.13

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest selenium webdriver-manager

    - name: Start test services
      run: |
        docker-compose -f docker-compose.test.yml up -d

    - name: Run E2E tests
      run: |
        pytest tests/e2e/ -v --tb=short
      timeout-minutes: 10

    - name: Cleanup
      if: always()
      run: |
        docker-compose -f docker-compose.test.yml down
```

### 테스트 결과 보고

```python
# scripts/test_reporter.py
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

class TestReporter:
    """테스트 결과 보고서 생성기"""

    def __init__(self, test_results_dir: Path):
        self.test_results_dir = test_results_dir
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'details': {}
        }

    def parse_junit_xml(self, xml_file: Path) -> dict:
        """JUnit XML 파싱"""
        tree = ET.parse(xml_file)
        root = tree.getroot()

        result = {
            'total': int(root.get('tests', 0)),
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'testcases': []
        }

        for testcase in root.findall('testcase'):
            status = 'passed'
            message = None

            failure = testcase.find('failure')
            if failure is not None:
                status = 'failed'
                message = failure.get('message')

            error = testcase.find('error')
            if error is not None:
                status = 'error'
                message = error.get('message')

            skipped = testcase.find('skipped')
            if skipped is not None:
                status = 'skipped'

            result[status] += 1
            result['testcases'].append({
                'name': testcase.get('name'),
                'class': testcase.get('classname'),
                'time': float(testcase.get('time', 0)),
                'status': status,
                'message': message
            })

        return result

    def generate_report(self):
        """보고서 생성"""
        # 모든 테스트 결과 파싱
        for xml_file in self.test_results_dir.glob('*.xml'):
            test_type = xml_file.stem
            self.report_data['details'][test_type] = self.parse_junit_xml(xml_file)

        # 요약 계산
        for test_type, details in self.report_data['details'].items():
            total = details['total']
            passed = details['passed']
            self.report_data['summary'][test_type] = {
                'total': total,
                'passed': passed,
                'pass_rate': (passed / total * 100) if total > 0 else 0,
                'failed': details['failed'],
                'errors': details['errors'],
                'skipped': details['skipped']
            }

        # 전체 요약
        total_tests = sum(s['total'] for s in self.report_data['summary'].values())
        total_passed = sum(s['passed'] for s in self.report_data['summary'].values())
        self.report_data['summary']['overall'] = {
            'total': total_tests,
            'passed': total_passed,
            'pass_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'failed': sum(s['failed'] for s in self.report_data['summary'].values()),
            'errors': sum(s['errors'] for s in self.report_data['summary'].values()),
            'skipped': sum(s['skipped'] for s in self.report_data['summary'].values())
        }

        return self.report_data

    def save_report(self, output_file: Path):
        """보고서 저장"""
        report = self.generate_report()

        with output_file.open('w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # HTML 보고서 생성
        self._generate_html_report(output_file.with_suffix('.html'), report)

    def _generate_html_report(self, output_file: Path, report: dict):
        """HTML 보고서 생성"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .summary table {{ width: 100%; border-collapse: collapse; }}
                .summary th, .summary td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                .summary th {{ background: #333; color: white; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .error {{ color: orange; }}
                .testcase {{ margin: 10px 0; padding: 10px; background: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Test Report</h1>
            <p>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="summary">
                <h2>Overall Summary</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Tests</td><td>{report['summary']['overall']['total']}</td></tr>
                    <tr><td class="passed">Passed</td><td>{report['summary']['overall']['passed']}</td></tr>
                    <tr><td class="failed">Failed</td><td>{report['summary']['overall']['failed']}</td></tr>
                    <tr><td class="error">Errors</td><td>{report['summary']['overall']['errors']}</td></tr>
                    <tr><td>Pass Rate</td><td>{report['summary']['overall']['pass_rate']:.1f}%</td></tr>
                </table>
            </div>

            <h2>Detailed Results</h2>
        """

        for test_type, details in report['details'].items():
            html_content += f"""
            <h3>{test_type}</h3>
            <p>Pass Rate: {report['summary'][test_type]['pass_rate']:.1f}%</p>
            <ul>
            """

            for testcase in details['testcases']:
                status_class = testcase['status']
                if testcase['message']:
                    html_content += f"""
                    <li class="testcase">
                    <span class="{status_class}">{testcase['name']} - {testcase['status']}</span>
                    <br><small>{testcase['message']}</small>
                    </li>
                    """
                else:
                    html_content += f"""
                    <li class="testcase">
                    <span class="{status_class}">{testcase['name']} - {testcase['status']}</span>
                    </li>
                    """

            html_content += """
            </ul>
            """

        html_content += """
        </body>
        </html>
        """

        with output_file.open('w', encoding='utf-8') as f:
            f.write(html_content)
```

## 테스트 실행 절차

### 로컬 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 단위 테스트만 실행
pytest tests/unit/

# 통합 테스트 실행
pytest tests/integration/

# E2E 테스트 실행
pytest tests/e2e/

# 특정 테스트 실행
pytest tests/test_config.py::test_config_creation

# 커버리지 보고서 생성
pytest --cov=picko --cov-report=html --cov-report=term-missing

# 병렬 실행
pytest -n 4

# 빠른 실패 모드 (첫 실패 시 중단)
pytest --x

# 상세 출력
pytest -v -s

# 특정 마커로 테스트 실행
pytest -m unit
pytest -m integration
pytest -m e2e
pytest -m stress
pytest -m slow
```

### 테스트 환경 설정

```bash
# 테스트용 가상 환경 생성
python -m venv .venv.test
.venv.test\Scripts\activate

# 테스트용 의존성 설치
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock pytest-html

# 테스트 설정 파일 생성
cp .env.example .env.test
echo "TEST_MODE=true" >> .env.test
echo "LOG_LEVEL=DEBUG" >> .env.test

# 데이터베이스 초기화
python scripts/init_test_db.py

# 테스트 데이터 준비
python scripts/prepare_test_data.py
```

### 테스트 결과 검증

```python
# scripts/validate_test_results.py
import json
import sys
from pathlib import Path

def validate_test_results(test_report_path: Path, min_pass_rate: float = 90.0):
    """테스트 결과 검증"""
    if not test_report_path.exists():
        print(f"Test report not found: {test_report_path}")
        return False

    try:
        with test_report_path.open('r', encoding='utf-8') as f:
            report = json.load(f)

        overall = report['summary']['overall']
        pass_rate = overall['pass_rate']

        print(f"Test Results:")
        print(f"  Total: {overall['total']}")
        print(f"  Passed: {overall['passed']}")
        print(f"  Failed: {overall['failed']}")
        print(f"  Errors: {overall['errors']}")
        print(f"  Pass Rate: {pass_rate:.1f}%")

        if pass_rate < min_pass_rate:
            print(f"\n❌ FAIL: Pass rate ({pass_rate:.1f}%) is below minimum ({min_pass_rate}%)")
            sys.exit(1)

        print(f"\n✅ PASS: All tests passed with {pass_rate:.1f}% pass rate")
        return True

    except Exception as e:
        print(f"Error validating test results: {e}")
        sys.exit(1)

if __name__ == "__main__":
    report_path = Path("test_results/report.json")
    validate_test_results(report_path)
```

### 자동화 테스트 스크립트

```bash
#!/bin/bash
# run_all_tests.sh

set -e

echo "🚀 Starting test run..."

# 테스트 환경 설정
echo "📝 Setting up test environment..."
python -m venv .venv.test
.venv.test\Scripts\activate
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock pytest-html

# 설정 파일 생성
cp .env.example .env.test
echo "TEST_MODE=true" >> .env.test
echo "LOG_LEVEL=DEBUG" >> .env.test

# 초기화
python scripts/init_test_db.py

# 데이터 준비
echo "📦 Preparing test data..."
python scripts/prepare_test_data.py

# 테스트 실행
echo "🧪 Running tests..."

# 단위 테스트
echo "Running unit tests..."
pytest tests/unit/ --cov=picko --cov-report=xml --cov-report=html --cov-report=term-missing -v

# 통합 테스트
echo "Running integration tests..."
pytest tests/integration/ -v --cov=picko.integration

# E2E 테스트 (선택적)
if [ "$RUN_E2E" = "true" ]; then
    echo "Running E2E tests..."
    docker-compose -f docker-compose.test.yml up -d
    pytest tests/e2e/ -v --tb=short --cov=picko.e2e
    docker-compose -f docker-compose.test.yml down
fi

# 보고서 생성
echo "📊 Generating test report..."
python scripts/test_reporter.py

# 결과 검증
echo "✅ Validating test results..."
python scripts/validate_test_results.py test_results/report.json

echo "🎉 All tests completed successfully!"
```

### 테스트 커버리지 요구사항

| 구분 | 최소 커버리지 | 주요 영역 |
|------|--------------|----------|
| 단위 테스트 | 90% | 핵심 비즈니스 로직 |
| 통합 테스트 | 80% | 컴포넌트 간 상호작용 |
| 전체 커버리지 | 85% | 프로젝트 전체 |
| 코드 라인 커버리지 | 80% | 실행된 코드 라인 비율 |
| 브랜치 커버리지 | 75% | 코드 분기 커버리지 |

### 커버리지 보고서 분석

```python
# scripts/coverage_analyzer.py
import json
from pathlib import Path

def analyze_coverage(coverage_file: Path):
    """커버리지 보고서 분석"""
    if not coverage_file.exists():
        print(f"Coverage report not found: {coverage_file}")
        return

    with coverage_file.open('r') as f:
        coverage = json.load(f)

    print("📊 Coverage Analysis")
    print("=" * 50)

    # 모듈별 커버리지
    for module, data in coverage['files'].items():
        lines_covered = len(data['lines_covered'])
        lines_total = len(data['lines_total'])
        branch_coverage = data.get('branch_coverage', 0)

        coverage_rate = (lines_covered / lines_total * 100) if lines_total > 0 else 0

        print(f"\n📁 Module: {module}")
        print(f"   Lines: {lines_covered}/{lines_total} ({coverage_rate:.1f}%)")
        print(f"   Branch: {branch_coverage:.1f}%")

        # 커버리지가 낮은 파일
        if coverage_rate < 80:
            print(f"   ⚠️  Low coverage warning!")

    # 전체 통계
    total_lines = sum(len(d['lines_total']) for d in coverage['files'].values())
    covered_lines = sum(len(d['lines_covered']) for d in coverage['files'].values())

    overall_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0

    print(f"\n📈 Overall Coverage: {overall_coverage:.1f}%")

    if overall_coverage < 85:
        print("❌ Overall coverage is below required 85%")
        return False

    print("✅ Coverage meets requirements")
    return True
```

이 문서는 Picko 스크립트 시스템의 모든 측면에 대한 포괄적인 테스트 전략을 제공합니다. 각 테스트 유형에 대한 구체적인 예시와 실용적인 구현 방법을 포함하고 있습니다.
