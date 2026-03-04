# 개발 환경 설정

이 문서는 Picko 프로젝트의 로컬 개발 환경을 설정하는 방법을 안내합니다.

## 사전 요구 사항

### 필수 소프트웨어
- **Python 3.13+**: [Python 공식 다운로드 페이지](https://www.python.org/downloads/)
- **Git**: [Git 공식 다운로드 페이지](https://git-scm.com/download/win)
- **Node.js 18+**: [Node.js 공식 다운로드 페이지](https://nodejs.org/)
- **Visual Studio Code**: [VS Code 공식 다운로드 페이지](https://code.visualstudio.com/)

### 필수 환경 변수
프로젝트 루트에 `.env` 파일을 생성하고 다음 환경 변수를 설정합니다:

```bash
# OpenAI API (가장 일반적으로 사용)
OPENAI_API_KEY=your_openai_api_key_here

# 또는 다른 LLM 제공자 선택
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
RELAY_API_KEY=your_relay_api_key_here

# 소셜 미디어 게시를 위한 토큰 (선택)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
```

## 개발 환경 구축

### 1. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone https://github.com/namu-k/picko-scripts.git
cd picko-scripts

# 가상 환경 생성
python -m venv .venv

# Windows 환경 활성화
.venv\Scripts\activate

# macOS/Linux 환경 활성화
source .venv/bin/activate
```

### 2. 의존성 설치

```bash
# 기본 의존성 설치
pip install -r requirements.txt

# 개발 의존성 설치
pip install -r requirements-dev.txt

# 또는 직접 설치
pip install black isort flake8 mypy pytest pre-commit
```

### 3. Git 설정

```bash
# Git 기본 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 본인 브랜치 설정 (main 브랜치는 보호됨)
git checkout -b feature-your-feature-name
```

## VS Code 설정

### 1. 확장 프로그램 설치
다음 확장 프로그램을 설치하세요:

- **Python** - Python 지원
- **Pylance** - Python 언어 서버
- **Jupyter** - Jupyter 노트북 지원
- **GitLens** - Git 상세 기능
- **Docker** - Docker 지원
- **Black Formatter** - 자동 코드 포맷팅

### 2. VS Code 설정 파일 생성
`.vscode/settings.json` 파일을 생성하세요:

```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.eslint": true
    },
    "files.associations": {
        "*.yaml": "yaml",
        "*.yml": "yaml"
    }
}
```

### 3. 디버깅 설정
`.vscode/launch.json` 파일을 생성하세요:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true
        },
        {
            "name": "Python: Daily Collector",
            "type": "python",
            "request": "launch",
            "module": "scripts.daily_collector",
            "args": ["--date", "2026-03-04"],
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Generate Content",
            "type": "python",
            "request": "launch",
            "module": "scripts.generate_content",
            "console": "integratedTerminal"
        }
    ]
}
```

## 테스트 데이터 생성

### 1. 가상 Obsidian Vault 설정
테스트를 위해 가상 Vault를 설정합니다:

```bash
# 테스트 Vault 생성
mkdir -p test_vault/Content/Longform
mkdir -p test_vault/Content/Packs
mkdir -p test_vault/Assets/Images/_prompts
mkdir -p test_vault/Inbox/Inputs
mkdir -p test_vault/Inbox/Inputs/_digests

# config.yml 수정
vault:
  root: "test_vault"
```

### 2. 샘플 RSS 소스 생성
`config/sources.yml` 파일에 테스트용 RSS 소스를 추가:

```yaml
test_sources:
  - name: "TechCrunch"
    url: "https://techcrunch.com/feed/"
    category: "tech"
    enabled: true
    max_items: 5
    quality_threshold: 0.5
```

### 3. 샘플 콘텐츠 생성
테스트를 위한 샘플 콘텐츠를 생성:

```python
# scripts/generate_sample_data.py 예제
def create_sample_content():
    """테스트용 샘플 콘텐츠 생성"""
    sample_items = [
        {
            "title": "새로운 AI 기술 발표",
            "content": "새로운 AI 기술이 발표되었습니다...",
            "category": "tech",
            "source": "TechCrunch",
            "published": "2026-03-04T10:00:00Z"
        },
        # 추가 샘플 데이터...
    ]
    return sample_items
```

### 4. 테스트 스크립트 실행

```bash
# 건강 검사
python -m scripts.health_check

# 테스트 모드로 실행 (실제 작업 수행 없음)
python -m scripts.daily_collector --date 2026-03-04 --dry-run
python -m scripts.generate_content --date 2026-03-04 --dry-run
```

## 프로젝트 구조

```
picko-scripts/
├── picko/                 # 핵심 패키지
│   ├── __init__.py
│   ├── config.py          # 설정 관리
│   ├── vault_io.py        # Obsidian Vault I/O
│   ├── llm_client.py      # LLM 클라이언트
│   └── ...
├── scripts/               # 실행 스크립트
├── tests/                 # 테스트 코드
├── config/                # 설정 파일
├── docs/                  # 문서
├── logs/                  # 로그 파일
├── cache/                 # 캐시 파일
└── .env                   # 환경 변수
```

## 문제 해결

### 1. pip 설치 오류
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 가상 환경 재설치
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 모듈 임포트 오류
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 또는 Python 경로 추가
python -c "import sys; sys.path.insert(0, '.')"
```

### 3. API 키 문제
```bash
# 환경 변수 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env
```

### 4. 가상 환경 문제
```bash
# 가상 환경 활성화 확인
which python  # /path/to/venv/bin/python

# 가상 환경 내에서 실행되는지 확인
python -c "import sys; print(sys.executable)"
```

## 추가 팁

1. **IDE 설정**: VS Code 외에 PyCharm이나 JetBrains Rider를 사용할 수 있습니다.
2. **컨테이너 개발**: Docker를 사용한 컨테이너 개발 환경을 구성할 수 있습니다.
3. **원격 개발**: GitHub Codespaces나 VS Code Remote를 사용한 원격 개발이 가능합니다.
4. **백업 정기적 프로젝트 백업**을 권장합니다.

## 참고 자료

- [Python 공식 문서](https://docs.python.org/3/)
- [Black 포매터 문서](https://black.readthedocs.io/)
- [Flake8 문서](https://flake8.pycqa.org/)
- [MyPy 문서](https://mypy.readthedocs.io/)
- [pytest 문서](https://docs.pytest.org/)
