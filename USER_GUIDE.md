# Picko 사용자 가이드

Picko는 RSS 피드와 웹 소스에서 콘텐츠를 자동으로 수집하고, AI를 활용해 다양한 형태의 콘텐츠(블로그 포스트, 소셜 미디어 게시물 등)를 생성하는 콘텐츠 파이프라인 시스템입니다.

이 가이드에서는 Picko를 처음 사용하는 분들을 위해 시스템의 개념, 설치 방법, 설정, 그리고 일일 작업 흐름을 상세히 설명합니다.

## 목차

1. [시스템 개요](#시스템-개요)
2. [사전 준비 사항](#사전-준비-사항)
3. [설치 및 초기 설정](#설치-및-초기-설정)
4. [콘텐츠 파이프라인 이해하기](#콘텐츠-파이프라인-이해하기)
5. [첫 실행: 단계별 가이드](#첫-실행-단계별-가이드)
6. [일일 작업 흐름](#일일-작업-흐름)
7. [구성 요소 상세 설명](#구성-요소-상세-설명)
8. [문제 해결](#문제-해결)
9. [팁과 모범 사례](#팁과-모범-사례)

---

## 시스템 개요

### Picko는 무엇인가요?

Picko는 다음과 같은 작업을 자동화합니다:

1. **콘텐츠 수집**: RSS 피드, 뉴스 사이트 등에서 관심 주제의 콘텐츠를 자동 수집
2. **콘텐츠 분석**: AI로 요약, 핵심 포인트 추출, 태깅, 점수 매기기
3. **콘텐츠 생성**: 승인된 콘텐츠를 바탕으로 블로그 포스트, 소셜 미디어 게시물 생성
4. **품질 관리**: 생성된 콘텐츠의 품질을 검증하고 관리

### 사용 사례 예시

- **뉴스 큐레이션**: 테크 뉴스를 매일 아침 요약받기
- **소셜 미디어 운영**: 트위터, 링크드인, 뉴스레터용 콘텐츠 자동 생성
- **연구원 보조**: 관련 논문/기사를 수집하고 요약
- **콘텐츠 마케팅**: 블로그 포스트 아이디어를 자동으로 발굴

---

## 사전 준비 사항

### 1. 필수 요구사항

**하드웨어**
- RAM: 최소 4GB (권장 8GB 이상)
- 디스크: 최소 1GB 여유 공간

**소프트웨어**
- Python 3.13 이상
- Git (선택사항)

**계정**
- OpenAI API 계정 및 API 키 (GPT-4o 모델 사용)
  - [OpenAI API 키 발급 방법](https://platform.openai.com/api-keys)

### 2. 비용 안내

OpenAI API 사용에 따른 비용이 발생합니다:

- **GPT-4o**: 텍스트 생성 시 약 $0.005/1K토큰
- **text-embedding-3-small**: 임베딩 시 약 $0.00002/1K토큰

예상 비용 (하루 10개 콘텐츠 처리 기준):
- 수집 및 분석: $0.05
- 콘텐츠 생성: $0.10
- **일일 총비용**: 약 $0.15 (월 $4-5)

### 3. 콘텐츠 소스 준비

수집할 콘텐츠 소스를 준비하세요:

**RSS 피드 권장**
- 기술 뉴스: TechCrunch, Hacker News, The Verge
- AI 뉴스: AI News, MIT Technology Review
- 산업별: 해당 분야의 전문 매체 RSS

**웹사이트 URL**
- 정기적으로 크롤링할 블로그나 뉴스 사이트 URL

---

## 설치 및 초기 설정

### 1. 리포지토리 클론

```bash
git clone https://github.com/your-username/picko-scripts.git
cd picko-scripts
```

### 2. Python 가상환경 설정

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

설치되는 주요 라이브러리:
- `openai`: OpenAI API 클라이언트
- `anthropic`: Anthropic Claude API 클라이언트
- `httpx`: HTTP 요청
- `feedparser`: RSS 피드 파싱
- `beautifulsoup4`: HTML 파싱
- `loguru`: 로깅
- `jinja2`: 템플릿 렌더링

### 4. OpenAI API 키 설정

```bash
# Windows
set OPENAI_API_KEY=sk-your-api-key-here

# macOS/Linux
export OPENAI_API_KEY=sk-your-api-key-here
```

### 5. 구성 파일 설정

#### 5.1 메인 설정 (`config/config.yml`)

```yaml
# Vault 경로 (Obsidian이 있는 경로)
vault:
  root: "C:/Users/YourName/Obsidian/PickoVault"
  inbox: "Inbox/Inputs"
  digests: "Inbox/Inputs/_digests"
  content: "Content"
  longform: "Content/Longform"
  packs: "Content/Packs"
  assets: "Assets"
  images_prompts: "Assets/Images/_prompts"
  archive: "Archive"
  logs_publish: "Logs/Publish"

# LLM 설정
llm:
  provider: "openai"
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 4000
  api_key_env: "OPENAI_API_KEY"

# 임베딩 설정
embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  dimensions: 1536
  cache_enabled: true
  cache_dir: "cache/embeddings"

# 점수 계산 설정
scoring:
  weights:
    novelty: 0.3    # 참신도 가중치
    relevance: 0.4  # 관련도 가중치
    quality: 0.3    # 품질 가중치
  thresholds:
    auto_approve: 0.85     # 이 점수 이상 자동 승인
    auto_reject: 0.3       # 이 점수 이하 자동 거부
    minimum_display: 0.4   # 이 점수 이상만 표시
```

#### 5.2 콘텐츠 소스 설정 (`config/sources.yml`)

```yaml
sources:
  # RSS 피드 예시
  - id: "techcrunch"
    type: "rss"
    url: "https://techcrunch.com/feed/"
    category: "tech_news"
    enabled: true

  - id: "hacker_news"
    type: "rss"
    url: "https://hnrss.org/frontpage"
    category: "tech_community"
    enabled: true

  - id: "ai_news"
    type: "rss"
    url: "https://www.artificialintelligence-news.com/feed/"
    category: "ai"
    enabled: true

# 카테고리별 설정
categories:
  tech_news:
    relevance_boost: 1.0
    max_items_per_day: 20

  ai:
    relevance_boost: 1.2
    max_items_per_day: 25
```

#### 5.3 계정 프로필 설정 (`config/accounts/socialbuilders.yml`)

```yaml
account:
  id: "socialbuilders"
  name: "소셜빌더스"
  description: "AI/테크 트렌드 큐레이션 채널"

# 관심 주제 (관련도 점수 계산에 사용)
interests:
  primary:
    - "AI/머신러닝"
    - "스타트업"
    - "생산성 도구"
  secondary:
    - "디자인"
    - "마케팅 자동화"

# 키워드 가중치
keywords:
  high_relevance:
    - "ChatGPT"
    - "Claude"
    - "Notion"
    - "자동화"
  medium_relevance:
    - "생산성"
    - "스타트업"
  low_relevance:
    - "테크"
    - "앱"

# 채널별 설정
channels:
  twitter:
    max_length: 280
    tone: "casual"
    hashtags: true
  linkedin:
    max_length: 1500
    tone: "professional"
    hashtags: false
  newsletter:
    max_length: 5000
    tone: "informative"
```

---

## 콘텐츠 파이프라인 이해하기

Picko의 작동 방식을 이해하면 효율적으로 사용할 수 있습니다.

### 파이프라인 구조

```
┌─────────────────┐
│  1. 수집 (Ingest)  │  RSS/웹에서 콘텐츠 수집
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. 중복 제거     │  URL 정규화 및 중복 확인
└────────┬────────┘
         ▼
┌─────────────────┐
│  3. 추출 (Fetch)  │  본문, 제목, 발행일 추출
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. 분석 (NLP)    │  AI로 요약, 태깅, 핵심 포인트
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. 임베딩        │  텍스트를 벡터로 변환
└────────┬────────┘
         ▼
┌─────────────────┐
│  6. 점수 계산     │  참신도, 관련도, 품질 점수
└────────┬────────┘
         ▼
┌─────────────────┐
│  7. 승인         │  Digest에서 체크박스로 승인
└────────┬────────┘
         ▼
┌─────────────────┐
│  8. 생성         │  블로그, 소셜 미디어 콘텐츠 생성
└────────┬────────┘
         ▼
┌─────────────────┐
│  9. 발행         │  생성된 콘텐츠 발행
└─────────────────┘
```

### 폴더 구조

```
PickoVault/                 # Obsidian Vault
├── Inbox/                  # 수집된 콘텐츠
│   └── Inputs/            # 원본 콘텐츠 저장
│       ├── input_xxx.md   # 개별 콘텐츠
│       └── _digests/      # 일일 요약
│           └── 2026-02-09.md
├── Content/               # 생성된 콘텐츠
│   ├── Longform/         # 블로그 포스트
│   └── Packs/            # 소셜 미디어
│       ├── twitter/
│       ├── linkedin/
│       └── newsletter/
├── Assets/               # 이미지, 프롬프트
│   └── Images/
│       └── _prompts/
└── Logs/                 # 발행 로그
    └── Publish/
```

---

## 첫 실행: 단계별 가이드

### 1단계: 시스템 건강 확인

먼저 시스템이 제대로 설정되었는지 확인하세요.

```bash
python -m scripts.health_check
```

**예상 출력:**

```
============================================================
Health Check Report - 2026-02-09 22:00:00
============================================================

✅ Vault Access: Read/Write OK
   └─ C:/Users/YourName/Obsidian/PickoVault

✅ OpenAI API Key: Configured
   └─ sk-proj...xxxx

✅ RSS Sources: All 3 sources accessible

✅ Directories: All 6 directories exist

✅ Disk Space: 50.2 GB available

============================================================
Summary: 5 passed, 0 failed
============================================================
```

오류가 있다면 설정을 다시 확인하세요.

### 2단계: 첫 콘텐츠 수집 (dry-run)

실제로 저장하지 않고 시뮬레이션을 해보세요.

```bash
python -m scripts.daily_collector --dry-run
```

**예상 출력:**

```
22:00:15 | INFO     | daily_collector | Starting collection for date: 2026-02-09
22:00:15 | INFO     | daily_collector | Collected 45 items from sources
22:00:16 | INFO     | daily_collector | After dedupe: 42 unique items
22:00:45 | INFO     | daily_collector | Fetched content for 38 items
22:01:30 | INFO     | daily_collector | [DRY RUN] Skipping export and digest creation

==================================================
Collection Results for 2026-02-09
==================================================
Collected: 45
Processed: 38
Exported:  0
```

### 3단계: 실제 콘텐츠 수집

dry-run이 정상이면 실제로 저장해보세요.

```bash
python -m scripts.daily_collector
```

### 4단계: Digest 확인 및 승인

Obsidian에서 다음 파일을 엽니다:

```
Inbox/Inputs/_digests/2026-02-09.md
```

다음과 같이 승인할 항목을 체크하세요:

```markdown
## [ ] OpenAI의 새로운 모델 발표

- **ID**: input_7ce483b7a9e4
- **Score**: 0.85 (N:0.90 R:0.80 Q:0.85)
- **Source**: [TechCrunch](https://techcrunch.com/...)
- > GPT-5가 곧 출시된다고...

## [x] Claude 4의 새로운 기능   ← 체크!

- **ID**: input_abc123def456
- **Score**: 0.92
- **Source**: [AI News](...)
- > Anthropic이 새로운 기능을...
```

### 5단계: 콘텐츠 생성

승인한 항목으로 콘텐츠를 생성하세요.

```bash
python -m scripts.generate_content --date 2026-02-09
```

**예상 출력:**

```
22:15:00 | INFO     | generate_content | Starting content generation for 2026-02-09
22:15:00 | INFO     | generate_content | Found 1 approved items
22:15:01 | INFO     | generate_content | Generating longform for: input_abc123def456
22:15:30 | INFO     | generate_content | Generating packs for: input_abc123def456
22:15:45 | INFO     | generate_content | Created pack: Content/Packs/twitter/pack_input_abc123def456_twitter.md
22:15:50 | INFO     | generate_content | Created pack: Content/Packs/linkedin/pack_input_abc123def456_linkedin.md

==================================================
Content Generation Results for 2026-02-09
==================================================
Approved Items:      1
Longform Created:    1
Packs Created:       2
Image Prompts:       1
```

### 6단계: 생성된 콘텐츠 확인

Obsidian에서 다음 위치를 확인하세요:

- **Longform**: `Content/Longform/longform_input_abc123def456.md`
- **Twitter**: `Content/Packs/twitter/pack_input_abc123def456_twitter.md`
- **LinkedIn**: `Content/Packs/linkedin/pack_input_abc123def456_linkedin.md`
- **Image Prompt**: `Assets/Images/_prompts/img_input_abc123def456.md`

---

## 일일 작업 흐름

### 매일 아침 루틴

**1. 콘텐츠 수집 (자동화 가능)**

```bash
# 오늘 날짜로 수집
python -m scripts.daily_collector

# 특정 소스만 수집
python -m scripts.daily_collector --sources techcrunch ai_news
```

**2. Digest 확인 및 승인**

Obsidian에서 `Inbox/Inputs/_digests/오늘날짜.md` 열고 승인할 항목 체크

**3. 콘텐츠 생성**

```bash
python -m scripts.generate_content
```

**4. 품질 검증**

```bash
python -m scripts.validate_output --path Content/ --recursive --verbose
```

### 주간 루틴

**1. 오래된 콘텐츠 아카이브**

```bash
# 30일 이상 된 미승인 콘텐츠 아카이브
python -m scripts.archive_manager --days 30
```

**2. 실패 항목 재시도**

```bash
# 어제 실패한 항목 재시도
python -m scripts.retry_failed --date yesterday
```

### 발행 시

**발행 로그 생성**

```bash
python -m scripts.publish_log create --content Content/Longform/longform_xxx.md --platform linkedin
```

---

## 구성 요소 상세 설명

### 콘텐츠 점수 계산

Picko는 세 가지 기준으로 콘텐츠를 평가합니다:

| 점수 항목 | 설명 | 가중치 |
|---------|------|--------|
| **Novelty** (참신도) | 기존 콘텐츠와 얼마나 다른지 | 30% |
| **Relevance** (관련도) | 관심 주제와 얼마나 관련있는지 | 40% |
| **Quality** (품질) | 제목 길이, 본문 길이, 소스 신뢰도 | 30% |

**점수 임계값:**

- `auto_approve: 0.85` - 이 점수 이상 자동 승인
- `minimum_display: 0.4` - 이 점수 이상만 Digest에 표시
- `auto_reject: 0.3` - 이 점수 이하 자동 제외

### 채널별 콘텐츠

**Twitter**
- 최대 280자
- 캐주얼한 톤
- 해시태그 포함

**LinkedIn**
- 최대 1,500자
- 전문적인 톤
- 해시태그 미포함

**Newsletter**
- 최대 5,000자
- 정보 중심 톤
- 구조화된 섹션

### 계정 프로필 활용

계정 프로필(`config/accounts/socialbuilders.yml`)을 수정하여 콘텐츠의 성격을 조정하세요:

```yaml
interests:
  primary:
    - "관심 주제 1"    # 관련도 점수 1.0
    - "관심 주제 2"

keywords:
  high_relevance:      # 관련도 점수 +1.0
    - "중요 키워드"
  medium_relevance:    # 관련도 점수 +0.5
    - "보통 키워드"
  low_relevance:       # 관련도 점수 +0.2
    - "일반 키워드"
```

---

## 문제 해결

### 일반적인 문제

**문제 1: API 키 오류**

```
Error: OPENAI_API_KEY not found
```

**해결:**
```bash
# API 키가 설정되었는지 확인
echo $OPENAI_API_KEY  # macOS/Linux
echo %OPENAI_API_KEY% # Windows

# 다시 설정
export OPENAI_API_KEY=sk-your-key  # macOS/Linux
set OPENAI_API_KEY=sk-your-key     # Windows
```

**문제 2: Vault 경로 오류**

```
FileNotFoundError: Vault root not found
```

**해결:**
`config/config.yml`의 `vault.root` 경로를 실제 경로로 수정하세요.

**문제 3: RSS 피드 접근 오류**

```
Failed to fetch source techcrunch: Connection timeout
```

**해결:**
1. 인터넷 연결 확인
2. `config/sources.yml`의 URL이 정확한지 확인
3. `health_check.py`로 소스 접근성 테스트

**문제 4: 생성된 콘텐츠 품질이 낮음**

**해결:**
1. `scoring.thresholds.auto_approve` 값을 높여서 더 높은 품질만 승인
2. 계정 프로필의 `interests`와 `keywords`를 구체화
3. `llm.temperature` 값을 낮춰서 더 일관된 출력

### 로그 확인

문제가 발생하면 로그를 확인하세요:

```bash
# 오늘의 로그
logs/2026-02-09/daily_collector.log
logs/2026-02-09/errors.log
```

---

## 팁과 모범 사례

### 효율적인 사용

1. **자동화**: cron/macOS Scheduler/Windows Task Scheduler로 매일 자동 실행
   ```bash
   # 매일 아침 8시에 실행
   0 8 * * * cd /path/to/picko-scripts && python -m scripts.daily_collector
   ```

2. **소스 최적화**: 너무 많은 소스는 정보 과부하를 일으킴
   - RSS 피드 5-10개 권장
   - 카테고리별로 나누어 관리

3. **점수 임계값 조정**: 처음에는 보수적으로 설정 후 경험에 따라 조정

### 콘텐츠 품질 향상

1. **관심 주제 구체화**: 일반적인 "AI"보다 "LLM", "Computer Vision" 등 구체적일수록 좋음

2. **신뢰할 수 있는 소스**: `config/accounts/socialbuilders.yml`의 `trusted_sources`에 신뢰할 수 있는 소스 등록

3. **검증 습관화**: `validate_output.py`를 정기적으로 실행하여 품질 확인

### 비용 절감

1. **임베딩 캐시 활성화**: `embedding.cache_enabled: true`로 설정
2. **소스 수 제한**: 불필요한 소스 비활성화
3. **API 사용량 모니터링**: OpenAI 대시보드에서 사용량 확인

---

## 추가 도움말

- **클래스 및 함수 레퍼런스**: 각 모듈의 docstring 참조
- **예시 설정**: `config/` 디렉토리의 예시 파일들
- **로그**: `logs/` 디렉토리의 상세 실행 로그

---

버전: 0.1.0
최종 업데이트: 2026-02-09
