# Auto Collector V2 - 구현 계획

## 1. 개요

### 1.1 목표
- 계정별 맞춤 콘텐츠 소스 **자동 발견** 및 **지속적 큐레이션**
- RSS, Perplexity, 뉴스레터 등 **다중 입력 채널** 통합
- **반복 실행**을 통한 소스 품질 관리

### 1.2 핵심 가치
```
계정 프로필 (관심사/키워드)
        ↓
   [자동 발견 엔진]
        ↓
   새로운 소스 후보
        ↓
   [품질 평가 & 승인]
        ↓
   활성 소스 풀
        ↓
   [일일 수집]
        ↓
   Inbox/Inputs/
```

---

## 2. 아키텍처

### 2.1 컴포넌트 구조

```
scripts/
├── source_discovery.py      # NEW: 소스 자동 발견
├── perplexity_collector.py  # NEW: Perplexity 이메일 수집
├── newsletter_collector.py  # NEW: 뉴스레터 수집 (선택)
├── source_curator.py        # NEW: 소스 품질 평가 & 관리
├── daily_collector.py       # 기존: 일일 수집 (확장)
└── simple_rss_collector.py  # 기존: 단순 RSS (유지)

picko/
├── source_manager.py        # NEW: 소스 메타데이터 관리
└── discovery_engine.py      # NEW: 발견 알고리즘

config/
├── sources.yml              # 기존: 소스 목록 (확장)
└── discovery_rules.yml      # NEW: 발견 규칙
```

### 2.2 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCE DISCOVERY CYCLE                       │
│                    (주 1회 또는 온디맨드)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ 계정 프로필   │───→│ 발견 엔진    │───→│ 소스 후보    │       │
│  │ (관심사/키워드)│    │ (검색/API)   │    │ (RSS/뉴스레터)│       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                  │               │
│                                                  ↓               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ 활성 소스    │←───│ 품질 평가    │←───│ LLM 분석     │       │
│  │ 풀 갱신      │    │ & 승인       │    │ (관련성/품질) │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     DAILY COLLECTION CYCLE                       │
│                       (매일 자동 실행)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ RSS 피드     │    │ Perplexity   │    │ 뉴스레터     │       │
│  │ 수집         │    │ 이메일       │    │ (선택)       │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             ↓                                   │
│                    ┌──────────────┐                             │
│                    │ 콘텐츠 통합  │                             │
│                    │ & 중복 제거  │                             │
│                    └──────┬───────┘                             │
│                           ↓                                     │
│                    ┌──────────────┐                             │
│                    │ 점수 매기기  │                             │
│                    │ (계정별)     │                             │
│                    └──────┬───────┘                             │
│                           ↓                                     │
│                    ┌──────────────┐                             │
│                    │ Inbox/Inputs │                             │
│                    │ 저장         │                             │
│                    └──────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase별 구현

### Phase 1: 소스 자동 발견 (핵심)

**목표:** 계정 관심사 기반으로 새로운 소스 자동 찾기

#### 3.1.1 발견 방법

| 방법 | API/도구 | 설명 |
|------|----------|------|
| RSS 디렉토리 검색 | RSSHub, feedly API | 키워드로 RSS 피드 검색 |
| 뉴스 검색 | Google News RSS | 키워드 관련 뉴스 → 소스 추출 |
| **뉴스레터 검색** | Substack API, buttondown | 키워드 관련 뉴스레터 발견 |
| 팟캐스트 검색 | iTunes API | 키워드 관련 팟캐스트 |
| 웹 검색 | Tavily/Bing API | "keyword RSS feed" 검색 |

#### 3.1.2 구현 작업

```python
# scripts/source_discovery.py

class SourceDiscoveryEngine:
    """
    계정 프로필 기반 소스 자동 발견
    """

    def discover_sources(self, account_id: str) -> list[SourceCandidate]:
        """
        1. 계정 프로필에서 관심사/키워드 추출
        2. 각 키워드로 소스 검색
        3. LLM으로 관련성 평가
        4. 중복 제거 후 후보 반환
        """
        pass

    def search_rss_feeds(self, keyword: str) -> list[RSSFeed]:
        """RSS 디렉토리에서 키워드 관련 피드 검색"""
        pass

    def search_newsletters(self, keyword: str) -> list[Newsletter]:
        """뉴스레터 플랫폼에서 검색"""
        pass

    def search_substack(self, keyword: str) -> list[SubstackNewsletter]:
        """
        Substack에서 키워드 관련 뉴스레터 검색
        - Substack 검색 API 또는 웹 스크래핑 사용
        - 구독자 수, 발행 빈도, 카테고리 정보 수집
        """
        pass

    def evaluate_relevance(self, source: Source, account: Account) -> float:
        """LLM으로 소스-계정 관련성 평가 (0-1)"""
        pass
```

#### 3.1.3 CLI 인터페이스

```bash
# 소스 발견 실행
python -m scripts.source_discovery --account socialbuilders

# 발견된 후보 검토
python -m scripts.source_discovery --review

# 특정 키워드로만 검색
python -m scripts.source_discovery --keywords "스타트업,VC,투자"

# 건조 실행 (실제 저장 안 함)
python -m scripts.source_discovery --dry-run
```

---

### Phase 2: Perplexity 이메일 수집

**목표:** Perplexity Tasks 결과를 자동으로 Inbox로 가져오기

#### 3.2.1 구현 방법

**옵션 A: Gmail API 직접 사용** (추천)
- 장점: 외부 서비스 불필요, 무료
- 단점: OAuth 설정 필요

**옵션 B: IMAP 사용**
- 장점: 모든 이메일 프로바이더 호환
- 단점: 보안 설정 복잡

#### 3.2.2 구현 작업

```python
# scripts/perplexity_collector.py

class PerplexityEmailCollector:
    """
    Perplexity Tasks 이메일 수집
    """

    def __init__(self, credentials_path: Path):
        self.gmail = GmailService(credentials_path)

    def fetch_perplexity_emails(self, since: datetime) -> list[PerplexityEmail]:
        """
        Perplexity에서 온 이메일 가져오기
        """
        pass

    def parse_email_content(self, email: Email) -> ParsedContent:
        """
        이메일 본문에서 핵심 내용 추출
        - 주제, 요약, 주요 포인트, 링크
        """
        pass

    def save_to_inbox(self, content: ParsedContent) -> Path:
        """
        Inbox/Inputs/에 마크다운으로 저장
        """
        pass
```

#### 3.2.3 설정

```yaml
# config/collectors.yml

perplexity:
  enabled: true
  gmail_credentials: "./secrets/gmail_credentials.json"
  gmail_token: "./secrets/gmail_token.json"
  query: "from:perplexity.ai"
  poll_interval_hours: 6
  output_dir: "Inbox/Inputs/Perplexity"
```

---

### Phase 3: 소스 품질 관리

**목표:** 수집된 소스의 품질을 지속적으로 모니터링

#### 3.3.1 품질 메트릭

| 메트릭 | 설명 | 계산 방법 |
|--------|------|-----------|
| `relevance_score` | 계정 관련성 | LLM 평가 (0-1) |
| `quality_score` | 콘텐츠 품질 | 기사 수, 인용도, 도메인 권위 |
| `freshness_score` | 최신성 | 마지막 발행일 |
| `consistency_score` | 일관성 | 발행 주기 안정성 |
| `signal_noise_ratio` | 신호/잡음 비율 | 수집 대 스킵 비율 |

#### 3.3.2 자동 관리 규칙

```yaml
# config/discovery_rules.yml

quality_rules:
  # 품질 임계값
  min_relevance_score: 0.6
  min_quality_score: 0.5
  max_inactive_days: 30

  # 자동 비활성화
  auto_disable:
    - condition: "signal_noise_ratio < 0.2"
      action: "disable"
      message: "낮은 신호/잡음 비율"

    - condition: "freshness_score < 0.3"
      action: "review"
      message: "오래된 소스"

  # 자동 승격
  auto_promote:
    - condition: "quality_score > 0.9 AND collected_count > 50"
      action: "trusted"
      message: "고품질 소스 승격"
```

#### 3.3.3 CLI 인터페이스

```bash
# 소스 품질 리포트
python -m scripts.source_curator --report

# 저품질 소스 정리
python -m scripts.source_curator --cleanup

# 소스 상태 확인
python -m scripts.source_curator --status

# 소스 수동 승인/거부
python -m scripts.source_curator --approve SOURCE_ID
python -m scripts.source_curator --reject SOURCE_ID
```

---

### Phase 4: 통합 수집 파이프라인

**목표:** 모든 채널을 통합한 일일 수집

#### 3.4.1 확장된 daily_collector.py

```python
# scripts/daily_collector.py (확장)

class UnifiedDailyCollector:
    """
    통합 일일 수집기
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.collectors = [
            RSSCollector(),
            PerplexityCollector(),
            # NewsletterCollector(),  # Phase 5
        ]

    def run(self) -> CollectionResult:
        """
        1. 각 컬렉터 실행
        2. 결과 통합
        3. 중복 제거 (임베딩 기반)
        4. 점수 매기기
        5. Inbox 저장
        """
        all_items = []

        for collector in self.collectors:
            items = collector.collect(self.account_id)
            all_items.extend(items)

        # 중복 제거
        unique_items = self.deduplicate(all_items)

        # 점수 매기기
        scored_items = self.score(unique_items)

        # 저장
        self.save_to_inbox(scored_items)

        return CollectionResult(...)
```

---

## 4. 파일 구조

### 4.1 소스 메타데이터

```yaml
# config/sources.yml (확장)

sources:
  # 기존 RSS
  - id: "techcrunch"
    type: "rss"
    url: "https://techcrunch.com/feed/"
    category: "tech_news"
    enabled: true

    # 새로운 필드
    auto_discovered: false
    added_at: "2025-01-01"
    quality_score: 0.85
    relevance_scores:
      socialbuilders: 0.9
      tech_founder: 0.8
    last_collected: "2026-02-25"
    collected_count: 150
    signal_noise_ratio: 0.7

  # 자동 발견된 RSS
  - id: "yc_blog"
    type: "rss"
    url: "https://www.ycombinator.com/blog/rss"
    category: "startup"
    enabled: true

    auto_discovered: true
    discovered_at: "2026-02-20"
    discovered_by: "source_discovery"
    discovery_keyword: "스타트업"
    quality_score: 0.92
    relevance_scores:
      socialbuilders: 0.95

  # 자동 발견된 Substack 뉴스레터
  - id: "lenny_newsletter"
    type: "newsletter"
    platform: "substack"
    url: "https://lennysnewsletter.com"
    rss_url: "https://lennysnewsletter.com/feed"
    category: "product"
    enabled: true

    auto_discovered: true
    discovered_at: "2026-02-22"
    discovered_by: "source_discovery"
    discovery_keyword: "PMF"
    subscribers: 500000
    quality_score: 0.95
    relevance_scores:
      socialbuilders: 0.92
```

### 4.2 발견 히스토리

```yaml
# data/discovery_history.yml

discovery_runs:
  - run_id: "dr_20260225_001"
    account: "socialbuilders"
    timestamp: "2026-02-25T10:00:00"
    keywords_used: ["스타트업", "VC", "투자", "PMF"]

    discovered:
      total: 25
      approved: 8
      rejected: 12
      pending: 5

    new_sources:
      - id: "indie_hackers"
        type: "rss"
        url: "https://indiehackers.com/feed"
        relevance_score: 0.88
```

---

## 5. 실행 스케줄

### 5.1 주기적 작업

| 작업 | 주기 | 명령 |
|------|------|------|
| 일일 수집 | 매일 8:00 | `python -m scripts.daily_collector` |
| 소스 발견 | 주 1회 | `python -m scripts.source_discovery` |
| 품질 평가 | 주 1회 | `python -m scripts.source_curator --evaluate` |
| Perplexity 수집 | 6시간마다 | `python -m scripts.perplexity_collector` |

### 5.2 GitHub Actions

```yaml
# .github/workflows/source_discovery.yml

name: Weekly Source Discovery

on:
  schedule:
    - cron: '0 6 * * 1'  # 매주 월요일 6:00 UTC

jobs:
  discover:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run source discovery
        run: python -m scripts.source_discovery --all-accounts
```

---

## 6. 구현 우선순위

| 순서 | 작업 | 예상 시간 | 의존성 |
|------|------|-----------|--------|
| 1 | `source_discovery.py` 핵심 로직 | 4h | 없음 |
| 1a | Substack/뉴스레터 발견 추가 | 2h | 1 |
| 2 | `perplexity_collector.py` Gmail API | 3h | OAuth 설정 |
| 3 | `source_curator.py` 품질 평가 | 3h | 없음 |
| 4 | `daily_collector.py` 통합 | 2h | 1, 2 |
| 5 | CLI 인터페이스 | 2h | 없음 |
| 6 | 테스트 작성 | 3h | 1-5 |
| 7 | 문서화 | 1h | 1-6 |

**총 예상:** 20시간

---

## 7. 리스크 및 대안

### 7.1 리스크

| 리스크 | 확률 | 영향 | 대안 |
|--------|------|------|------|
| Gmail API 할당량 초과 | 중 | 중 | IMAP 폴백 |
| RSS 피드 구조 변경 | 높 | 낮 | 적응형 파서 |
| LLM API 비용 증가 | 중 | 중 | 로컬 LLM 사용 |
| 소스 발견 정확도 낮음 | 중 | 중 | 수동 승인 강화 |

### 7.2 MVP 범위

1차 릴리스에서 제외:
- ~~뉴스레터 직접 수집~~ → **포함** (Substack RSS 사용)
- 팟캐스트 트랜스크립션
- 웹 스크래핑

---

## 8. 성공 기준

- [ ] 계정별 새로운 소스 5개 이상 자동 발견
- [ ] Perplexity 이메일 95% 이상 자동 수집
- [ ] 수집된 콘텐츠 중복률 10% 미만
- [ ] 소스 품질 자동 평가 정확도 80% 이상
- [ ] 전체 파이프라인 실행 시간 5분 미만

---

*작성일: 2026-02-25*
*브랜치: 004-auto-collector-v2*
