# 개발 가이드

이 문서는 Picko 프로젝트의 코딩 컨벤션 및 개발 프로세스를 안내합니다.

## 코딩 컨벤션

### Python 컨벤션

#### 1. 코드 스타일
- **포맷터**: Black을 사용한 자동 포맷팅
- **라인 길이**: 최대 120자
- **인덴트**: 4 spaces (탭 금지)

```bash
# 코드 포맷팅
black picko/ scripts/ tests/

# 정렬
isort picko/ scripts/ tests/
```

#### 2. 네이밍 컨벤션
- **클래스**: PascalCase
  ```python
  class ContentProcessor:
      pass

  class RSSCollector:
      pass
  ```

- **함수/메서드**: snake_case
  ```python
  def process_content():
      pass

  def fetch_rss_feeds():
      pass
  ```

- **변수**: snake_case
  ```python
  content_items = []
  processed_count = 0
  ```

- **상수**: UPPER_SNAKE_CASE
  ```python
  MAX_RETRIES = 3
  DEFAULT_TIMEOUT = 30
  ```

- **프라이빗 변수**: `_` 접두사
  ```python
  def _parse_feed_data():
      pass
  ```

#### 3. 타입 힌팅
모든 함수는 타입 힌트를 사용해야 합니다.

```python
from typing import List, Dict, Optional, Union

def process_content(
    items: List[Dict[str, str]],
    max_items: int = 10,
    dry_run: bool = False
) -> Dict[str, Union[int, List[str]]]:
    """
    콘텐츠를 처리합니다.

    Args:
        items: 처리할 아이템 리스트
        max_items: 최대 처리 개수
        dry_run: 테스트 모드 여부

    Returns:
        처리 결과 (개수와 실패 리스트)
    """
    pass
```

#### 4. 모듈 임포트
- 표준 라이브러리 먼저, 그 다음 서드파티, 마지막으로 로컬 모듈
- 한 줄에 하나의 임포트
- 절대 경로 사용 권장

```python
# 좋은 예
import os
import sys
from datetime import datetime
from typing import List

import requests
from loguru import logger
import yaml

from picko.config import get_config
from picko.vault_io import VaultIO
```

#### 5. 함수 정의
- 함수는 작게 유지 (50라인 이하)
- 하나의 함수는 하나의 책임만 가짐
- docstring 필수 (Google 스타일)

```python
def generate_longform_content(
    item_data: Dict[str, Any],
    style_profile: Dict[str, str],
    output_dir: str
) -> str:
    """
    롱폼 콘텐츠를 생성합니다.

    Args:
        item_data: 입력 데이터
        style_profile: 스타일 프로필
        output_dir: 출력 디렉터리

    Returns:
        생성된 콘텐츠 파일 경로
    """
    # 구현...
    return file_path
```

### YAML 컨벤션

#### 1. 들여쓰기
- 2 spaces 사용 (탭 금지)
- 계층 구조 명확히 유지

```yaml
# 좋은 예
daily_pipeline:
  steps:
    - name: "collect"
      action: "collector"
      config:
        sources:
          - techcrunch
          - ai_news
    - name: "process"
      action: "nlp"
```

#### 2. 키 명명
- kebab-case 사용
- 축약어 피하기
- 의미 있는 이름 사용

```yaml
# 좋은 예
feed_sources:
  techcrunch_rss:
    url: "https://techcrunch.com/feed/"
    category: "tech"
    quality_threshold: 0.5
```

#### 3. 주석
- `#` 뒤에 공백 하나
- 문서화가 필요한 곳에 주석 추가

```yaml
# 일일 배치 처리 설정
daily_pipeline:
  # 실행 시간 (UTC 기준)
  schedule: "09:00"

  # 처리할 소스 리스트
  sources:
    - techcrunch
    - ai_news
```

## 커밋 메시지 규칙

### 커밋 메시지 형식
```
<타입>(<범위>): <제목>

본문 (선택)

바닥글 (선택)
```

### 커밋 타입
- **feat**: 새로운 기능 추가
- **fix**: 버그 수정
- **docs**: 문서 수정
- **style**: 코드 형식 변경 (포맷팅 등)
- **refactor**: 리팩토링
- **test**: 테스트 관련
- **chore**: 빌드/데ploy/패키지 관리
- **perf**: 성능 개선

### 예시
```
feat(llm): OpenAI 클라이언트에 fallback 기능 추가

OpenAI API 실패 시 Relay로 자동 전환되도록 구현했습니다.
fallback 설정을 config.yml에서 지정할 수 있습니다.

Related: #123
Closes: #456
```

### 범위 규칙
- 모듈 이름을 범위로 사용
- `picko/`, `scripts/`, `config/` 등

```
feat(picko/vault_io): Vault에서 YAML frontmatter 지원

- YAML 형식의 frontmatter 읽기 기능
- 기존 JSON 형식과 호환성 유지

fix(scripts/daily_collector): 중복 아이템 처리 오류 수정
```

## 코드 리뷰 프로세스

### 1. Pull Request 생성
1. `main` 브랜치에서 기능 브랜치 생성
2. 커밋 메시지 규칙에 맞게 커밋
3. Pull Request 생성
4. **반드시** PR 템플릿 작성

### 2. PR 템플릿
```markdown
## 변경 사항
- [ ] 기능 추가
- [ ] 버그 수정
- [ ] 문서 업데이트

## 테스트
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] E2E 테스트 수행 (필요한 경우)

## 변경 사항
- [ ] 버전 업데이트 (필요한 경우)
- [ ] 문서 업데이트
- [ ] 브랜치 정리

## 체크리스트
- [ ] 라인 당 120자 이내
- [ ] Black 포맷팅 적용
- [ ] mypy 타입 검사 통과
- [ ] flake8 린팅 통과
- [ ] 테스트 커버리지 80% 이상
```

### 3. 리뷰 체크리스트
- [ ] 기능 요구 사항 충족 여부
- [ ] 코드 품질 및 성능
- [ ] 테스트 커버리지
- [ ] 보안 이슈
- [ ] 문서 업데이트

### 4. 리뷰 주기
- 최소 1명의 팀원 리뷰 필수
- 소규모 변경: 1일 이내
- 대규모 변경: 3일 이내 리뷰 완료

## 테스트 작성 가이드

### 1. 테스트 구조
```python
# tests/test_example.py

import pytest
from picko.example import ExampleClass

@pytest.fixture
def example_instance():
    """테스트용 Fixture"""
    return ExampleClass()

def test_example_function(example_instance):
    """단위 테스트 예시"""
    result = example_instance.example_function("test")
    assert result == "test_result"

class TestExampleClass:
    """클래스 단위 테스트"""

    def test_init(self):
        """초기화 테스트"""
        instance = ExampleClass()
        assert instance.value is None

    @pytest.mark.parametrize("input,expected", [
        ("hello", "world"),
        ("test", "result"),
    ])
    def test_method(self, input, expected):
        """파라미터라이즈 테스트"""
        instance = ExampleClass()
        result = instance.method(input)
        assert result == expected
```

### 2. 테스트 범위
- **단위 테스트**: 각 모듈/함수별 독립적 테스트
- **통합 테스트**: 모듈 간 상호작용 테스트
- **E2E 테스트**: 전체 시스템 테스트

### 3. 테스트 실행
```bash
# 모든 테스트 실행
pytest

# 특정 파일 테스트
pytest tests/test_config.py

# 특정 테스트만 실행
pytest tests/test_config.py::test_load_config

# 커버리지 보고서 생성
pytest --cov=picko --cov-report=html
```

### 4. 테스트 데이터 관리
테스트 데이터는 `tests/data/`에 저장합니다.

```
tests/
├── conftest.py          # 공용 Fixture
├── data/                # 테스트 데이터
│   ├── sample_rss.xml
│   └── sample_config.yml
├── test_config.py
└── test_vault_io.py
```

### 5. 모의(Mock) 객체
```python
from unittest.mock import Mock, patch
import pytest

@pytest.fixture
def mock_llm_client():
    """LLM 클라이언트 모의"""
    mock_client = Mock()
    mock_client.generate.return_value = "test response"
    return mock_client

@patch('picko.llm_client.LLMClient')
def test_with_mock(mock_class, mock_llm_client):
    """모의 객체를 사용한 테스트"""
    # 테스트 코드
    pass
```

## 기타 규칙

### 1. 오류 처리
```python
try:
    # 예외가 발생할 수 있는 코드
    result = risky_operation()
except ValueError as e:
    logger.error(f"Value error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise CustomError("Operation failed") from e
```

### 2. 로깅
```python
from loguru import logger

# 로깅 레벨 사용
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")

# 구조화된 로깅
logger.info("Processing item",
          item_id=item.id,
          category=item.category)
```

### 3. 환경별 설정
개발/테스트/프로덕션 환경을 구분합니다.

```python
# config/config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    debug: bool = False
    test_mode: bool = False
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls):
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            test_mode=os.getenv("TEST_MODE", "false").lower() == "true",
            api_key=os.getenv("API_KEY")
        )
```

## 자동화된 검사

### 1. Pre-commit 설정
`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
```

### 2. CI/CD 파이프라인
`.github/workflows/ci.yml`:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pip install -r requirements-dev.txt
      - run: black --check picko/ scripts/ tests/
      - run: isort --check-only picko/ scripts/ tests/
      - run: flake8 picko/ scripts/ tests/
      - run: mypy picko/
      - run: pytest --cov=.
```

## 참고 자료

- [PEP 8 - Python 스타일 가이드](https://peps.python.org/pep-0008/)
- [Black 포매터 문서](https://black.readthedocs.io/)
- [pytest 문서](https://docs.pytest.org/)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
