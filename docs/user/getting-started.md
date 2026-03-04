# 사용자 매뉴얼: 빠른 시작 가이드 (User Manual: Getting Started)

이 문서는 Picko 스크립트 시스템을 처음 사용하는 분들을 위한 빠른 시작 가이드입니다.

## 목차
- [시스템 개요](#시스템-개요)
- [시작하기 전 준비](#시작하기-전-준비)
- [첫 실행](#첫-실행)
- [기본 기능 사용법](#기본-기능-사용법)
- [FAQ](#faq)
- [문제 해결](#문제-해결)

## 시스템 개요

### Picko는 무엇인가요?

Picko는 RSS 피드와 다양한 콘텐츠 소스에서 정보를 수집하고, 자동으로 다양한 형태의 콘텐츠를 생성하는 콘텐츠 파이프라인 시스템입니다.

**주요 기능:**
- 📡 RSS 피드 자동 수집
- 🤖 AI 기반 콘텐츠 자동 생성 (긴 글, 소셜 미디어, 이미지 프롬프트)
- 📊 콘텐츠 품질 평가 및 필터링
- 🎯 타겟팅된 콘텐츠 배포
- 📝 Obsidian 통합 노트 관리

### 아키텍처 개요

```
RSS 피드
    ↓ (수집)
┌─────────────┐
│ RSS 수집기  │
├─────────────┤
│    NLP      │ → 요약, 태깅, 임베딩
├─────────────┤
│   평가 시스템 │ → 품질 점수 계산
├─────────────┤
│  콘텐츠 생성 │ → AI 콘텐츠 생성
├─────────────┤
│   Obsidian  │ → 노트 관리
└─────────────┘
```

## 시작하기 전 준비

### 1. 시스템 요구사항

- **운영체제**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **Python**: 3.13 이상
- **메모리**: 최소 4GB (권장 8GB)
- **스토리지**: 최소 5GB 여유 공간
- **네트워크**: 인터넷 연결

### 2. Python 설치

```bash
# Windows
winget install --id Python.Python.3.13

# macOS
brew install python@3.13

# Ubuntu
sudo apt update
sudo apt install python3.13 python3.13-venv
```

### 3. 프로젝트 설치

```bash
# 프로젝트 클론
git clone https://github.com/namu-k/picko-scripts.git
cd picko-scripts

# 가상 환경 생성
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

### 4. 환경 설정

1. **API 키 설정**

```bash
# .env 파일 생성
cp .env.example .env
```

```env
# .env 파일 내용
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# 선택적: 소셜 미디어 API 키
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret

# 선택적: 알릴 설정
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

2. **콘텐츠 저장소 설정**

```bash
# 테스트용 모의 데이터베이스 설정 (선택사항)
python -c "from picko.vault_io import VaultIO; VaultIO('mock_vault').init()"
```

## 첫 실행

### 1. 초기 시스템 확인

```bash
# 시스템 상태 확인
python -m scripts.health_check

# 예상 출력:
# ✅ Configuration loaded successfully
# ✅ Python environment is ready
# ✅ Required dependencies are installed
# ✅ Network connectivity is OK
# ✅ All systems are operational
```

### 2. RSS 소스 설정

1. **RSS 소스 파일 수정**

```yaml
# config/sources.yml
sources:
  - id: techcrunch
    name: "TechCrunch"
    url: "https://techcrunch.com/feed"
    category: "technology"
    enabled: true

  - id: ai_news
    name: "AI News"
    url: "https://www.artificialintelligence-news.com/feed/"
    category: "ai"
    enabled: true

  - id: startup_weekly
    name: "Startup Weekly"
    url: "https://startupweekly.feed"
    category: "startup"
    enabled: true
```

2. **소스 테스트**

```bash
# RSS 소스 연결 테스트
python -m scripts.simple_rss_collector --dry-run --hours 24
```

### 3. 첫 번째 RSS 수집 실행

```bash
# 오늘자 RSS 수집 (건조 모드)
python -m scripts.daily_collector --date 2026-03-04 --dry-run

# 실제 실행 (최초 실행 시 권장)
python -m scripts.daily_collector --date 2026-03-04
```

```bash
# 실행 결과 예시
[INFO] Starting daily collection for 2026-03-04
[INFO] Processing 3 RSS feeds...
[INFO] TechCrunch: 12 articles collected
[INFO] AI News: 8 articles collected
[INFO] Startup Weekly: 5 articles collected
[INFO] Total collected: 25 articles
[INFO] NLP processing completed
[INFO] Scoring completed (5 high-quality articles selected)
[INFO] Articles exported to Inbox/Inputs/
```

### 4. 콘텐츠 확인

수집된 콘텐츠는 다음 위치에 저장됩니다:

```
mock_vault/
└── Inbox/
    ├── Inputs/
    │   ├── collected_2026-03-04.md  # 수집 결과
    │   ├── _digests/
    │   │   ├── daily_2026-03-04.md   # 일일 다이제스트
    │   │   └── ...                    # 다른 날짜의 다이제스트
    │   └── ...                        # 다른 날짜의 파일
    └── Content/
        ├── Longform/
        │   ├── article_2026-03-04_01.md
        │   └── ...
        ├── Packs/
        │   ├── twitter/
        │   ├── linkedin/
        │   └── newsletter/
        └── ...
```

### 5. 생성된 콘텐츠 확인

수집된 콘텐츠는 다음과 같은 구조를 가집니다:

```markdown
---
title: "새로운 AI 기술 발표: OpenAI가 GPT-5를 공개했습니다"
source: techcrunch
tags:
  - AI
  - 기술
  - 인공지능
summary: "OpenAI가 GPT-5를 공개했으며, 향상된 추론 능력을 자랑합니다..."
score: 92
writing_status: "auto_ready"
pub_date: 2026-03-04T12:00:00Z
---

# 새로운 AI 기술 발표: OpenAI가 GPT-5를 공개했습니다

[기사 원본 링크](https://techcrunch.com/2026/03/04/openai-gpt5/)

## 요약

OpenAI가 오늘 GPT-5를 공개했습니다...

## 주요 내용

- 향상된 추론 능력
- 더 나은 맥락 이해
- 멀티모달 기능 강화

## 생각

이 기술 발표는 AI 발전에 중요한 이정표입니다...
```

## 기본 기능 사용법

### 1. 일일 콘텐츠 생성

```bash
# 다이제스트에서 승인된 아이템 자동 생성
python -m scripts.generate_content --date 2026-03-04

# 모든 아이템 강제 생성
python -m scripts.generate_content --auto-all

# 특정 타입만 생성
python -m scripts.generate_content --type longform packs

# 특정 타입 강제 생성
python -m scripts.generate_content --type longform --force
```

### 2. 콘텐츠 확인

생성된 콘텐츠는 다음 타입으로 저장됩니다:

- **Longform**: 긴 형태의 기사 (1000+ 단어)
- **Packs**: 소셜 미디어 게시물 팩 (Twitter, LinkedIn, Newsletter)
- **Image**: 이미지 생성 프롬프트

```markdown
# Longform 예시 (mock_vault/Content/Longform/)
---
title: "AI 기술의 미래: GPT-5가 가져올 변화"
tags:
  - AI
  - 기술
  - 미래
publish_date: 2026-03-04
generated_by: auto
---

# AI 기술의 미래: GPT-5가 가져올 변화

## 서론

OpenAI가 GPT-5를 발표하면서 AI 기술의 새로운 지평이 열렸습니다...

## 본문

... (생성된 기사 내용) ...

## 결론

GPT-5의 발표는 AI 기술 발전에 중요한 이정표이며...
```

### 3. 콘텐츠 검증

```bash
# 특정 경로의 콘텐츠 검증
python -m scripts.validate_output --path mock_vault/Content/Longform/

# 재귀 검증
python -m scripts.validate_output --recursive --verbose

# 검증 결과 예시
[INFO] Validating 3 files in mock_vault/Content/Longform/
[INFO] ✅ article_2026-03-04_01.md - PASSED
[INFO] ✅ article_2026-03-04_02.md - PASSED
[INFO] ✅ article_2026-03-04_03.md - PASSED
[INFO] Validation completed: 3/3 files passed
```

### 4. 소스 관리

```bash
# 소스 품질 평가
python -m scripts.source_curator --account socialbuilders --threshold 0.7

# 소스 품질 CSV 내보내기
python -m scripts.source_curator --account socialbuilders --export-csv

# 새로운 소스 발견
python -m scripts.source_discovery --account socialbuilders --keywords "AI, startup" --max-results 10
```

### 5. 멀티미디어 렌더링

```bash
# 이미지 생성 요청 (제안 단계)
python -m scripts.render_media render --input mock_vault/Inbox/Inputs/collected_2026-03-04.md

# 제안 보기
python -m scripts.render_media review

# 최종 이미지 생성 (승인된 제안)
python -m scripts.render_media review --finals
```

### 6. 콘텐츠 게시

```bash
# 게시 로그 생성
python -m scripts.publish_log --platform twitter --article article_2026-03-04_01.md

# 게시 상태 확인
python -m scripts.publish_log --status
```

## 워크플로우 예시

### 하루의 전체 워크플로우

```bash
# 1. 아침에 RSS 피드 수집
python -m scripts.daily_collector --date $(date +%Y-%m-%d)

# 2. 다이제스트에서 관심 있는 콘텐츠 선택
# (mock_vault/Inbox/Inputs/_digests/daily_YYYY-MM-DD.md에서 수동 선택)

# 3. 콘텐츠 생성
python -m scripts.generate_content --date $(date +%Y-%m-%d)

# 4. 생성된 콘텐츠 검증
python -m scripts.validate_output --recursive

# 5. 멀티미디어 콘텐츠 생성 (선택적)
python -m scripts.render_media review

# 6. 게시 준비
python -m scripts.publish_log --status
```

### 주간 업데이트

```bash
# 지난 주의 모든 콘텐츠 생성
for date in 2026-02-28 2026-02-29 2026-03-01 2026-03-02 2026-03-03 2026-03-04; do
    python -m scripts.generate_content --date $date
done

# 모든 생성 콘텐츠 검증
python -m scripts.validate_output --recursive

# 소스 품질 평가
python -m scripts.source_curator --account socialbuilders

# 오래된 콘텐츠 아카이빙
python -m scripts.archive_manager --days 30
```

## FAQ

### 일반 질문

**Q: Picko는 어떻게 작동하나요?**
A: Picko는 RSS 피드에서 콘텐츠를 수집하고, AI를 이용해 요약과 태깅을 한 후 품질 평가를 거쳐 상위 콘텐츠를 선택합니다. 선택된 콘텐츠는 다양한 형식으로 자동 생성됩니다.

**Q: 누가 사용할 수 있나요?**
A: 블로거, 콘텐츠 제작자, 소셜 미디어 매니저, 마케팅 전문가 등 다양한 분들이 사용할 수 있습니다.

**Q: 사용 가능한 AI 모델은 무엇인가요?**
A: GPT-4o-mini, GPT-4o, Claude 3.5 Sonnet, DeepSeek-R1 등 다양한 모델을 지원합니다. 기본 설정은 비용 효율적인 GPT-4o-mini를 사용합니다.

**Q: 얼마나 많은 비용이 드나요?**
A: 사용량에 따라 다릅니다. 일반적으로 월간 50-200달러 정도로, 수집하는 피드의 양과 생성하는 콘텐츠의 양에 비례합니다.

### 설정 관련 질문

**Q: API 키는 어떻게 구하나요?**
A: OpenAI, Anthropic, OpenRouter 등에서 API 키를 구매할 수 있습니다. 첫 사용자는 보통 무료 크레딧이 제공됩니다.

**Q: 콘텐츠 저장소는 어디에 만들어지나요?**
A: 기본적으로 `mock_vault/` 디렉토리에 생성됩니다. 설정 파일에서 경로를 변경할 수 있습니다.

**Q: 여러 계정을 관리할 수 있나요?**
A: 네, `config/accounts/` 디렉토리에 여러 계정 프로필을 설정할 수 있습니다.

### 사용 관련 질문

**Q: 수집된 콘텐츠를 어떻게 선택하나요?**
A: `mock_vault/Inbox/Inputs/_digests/` 파일에서 매일 다이제스트를 확인하고, 관심 있는 콘텐츠 앞의 체크박스를 선택합니다.

**Q: 콘텐츠 생성을 어떻게 제어하나요?**
A: `writing_status` 필드를 통해 생성 여부를 제어할 수 있습니다. 자동 생성 대상은 `writing_status: "auto_ready"` 상태여야 합니다.

**Q: 생성된 콘텐츠는 수정할 수 있나요?**
A: 네, 모든 생성된 콘텐츠는 일반 텍스트 파일이므로 편집기로 수정할 수 있습니다.

### 문제 해결

**Q: RSS 피드가 수집되지 않습니다.**
A: 피드 URL이 유효한지 확인하고, 네트워크 연결을 확인하세요. `--dry-run` 옵션으로 테스트해볼 수 있습니다.

**Q: 콘텐츠 생성이 실패합니다.**
A: API 키가 유효한지 확인하고, 사용량 제한이 있는지 확인하세요. 오류 로그를 확인해 구체적인 원인을 파악할 수 있습니다.

**Q: 생성된 콘텐츠의 품질이 낮습니다.**
A: 소스 RSS 피드의 품질, AI 모델 선택, 프롬프트 설정 등이 영향을 줄 수 있습니다. 고급 모델로 변경하거나 프롬프트를 최적화해볼 수 있습니다.

## 문제 해결

### 일반적인 오류 및 해결 방법

#### 1. 모듈 오류

**오류**: `ModuleNotFoundError: No module named 'picko'`

**해결**: 가상 환경을 활성화했는지 확인하세요.

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

#### 2. API 오류

**오류**: `Invalid API key`

**해결**: `.env` 파일에 API 키가 올바르게 설정되었는지 확인하세요.

```bash
# .env 파일 확인
cat .env

# API 키 유효성 테스트
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

#### 3. 네트워크 오류

**오류**: `ConnectionError` 또는 `Timeout`

**해결**: 네트워크 연결을 확인하고, 프록시 설정을 확인하세요.

```bash
# 네트워크 연결 테스트
ping api.openai.com

# Python 테스트
python -c "import requests; print(requests.get('https://api.openai.com').status_code)"
```

#### 4. 권한 오류

**오류**: `PermissionError: [Errno 13] Permission denied`

**해결**: 디렉토리 쓰기 권한을 확인하세요.

```bash
# Windows (관리자 권한으로 실행)
# 또는
# macOS/Linux
chmod 755 /path/to/directory
```

### 로그 분석

**로깅 설정 확인**:

```bash
# 로그 디렉토리 확인
ls logs/

# 특정 날짜의 로그 확인
cat logs/2026-03-04/daily_collector.log

# 오류 로그만 확인
cat logs/error.log
```

**디버깅 모드 활성화**:

```bash
# DEBUG 모드로 실행
export LOG_LEVEL=DEBUG
python -m scripts.daily_collector --date 2026-03-04

# 로그 레벨 변경 (Windows)
set LOG_LEVEL=DEBUG

# 로그 레벨 변경 (macOS/Linux)
export LOG_LEVEL=DEBUG
```

### 고급 문제 해결

#### 1. 데이터베이스 문제

```bash
# 데이터베이스 재설정
python -m scripts.init_db

# 데이터베이스 백업
cp -r mock_vault mock_vault.backup

# 캐시 정리
rm -rf cache/*
```

#### 2. 성능 문제

```bash
# 메모리 사용량 확인
python -c "import psutil; print(psutil.virtual_memory())"

# 프로세스 확인
tasklist | findstr python  # Windows
ps aux | grep python        # macOS/Linux

# 병렬 처리 확인
python -c "import multiprocessing; print(multiprocessing.cpu_count())"
```

### 지원 채널

1. **문서**: [GitHub Wiki](https://github.com/namu-k/picko-scripts/wiki)
2. **이슈**: [GitHub Issues](https://github.com/namu-k/picko-scripts/issues)
3. **커뮤니티**: [Discord 서버](https://discord.gg/picko)
4. **이메일**: support@picko.com

### 추가 학습 자료

- [아키텍처 개요](../architecture/README.md)
- [개발 가이드](../development/guidelines.md)
- [테스트 전략](../testing/strategy.md)
- [배포 가이드](../operations/deployment.md)
- [모니터링 가이드](../operations/monitoring.md)

## 다음 단계

이제 기본 사용법을 익혔으니, 다음 단계로 나아가세요:

1. **고급 설정**: [개발 가이드](../development/guidelines.md)를 확인하세요.
2. **자동화**: 워크플로우를 자동화해 보세요.
3. **커스터마이징**: 자신만의 설정을 추가해 보세요.
4. **커뮤니티 참여**: 다른 사용자들과 소통해 보세요.

Happy content creation! 🎉
