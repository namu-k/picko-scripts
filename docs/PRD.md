# Picko - Product Requirements Document (PRD)

> **버전**: 1.0.0
> **최종 수정**: 2026-03-04
> **대상 독자**: 개발자 온보딩용
> **범위**: 현재 구현된 기능 + 계획된 기능

---

## 1. 제품 개요

### 1.1 비전

Picko는 콘텐츠 파이프라인 자동화 시스템으로, RSS 피드 및 다양한 웹 소스에서 콘텐츠를 자동 수집하고, AI를 활용해 블로그 포스트, 소셜 미디어 콘텐츠, 이미지를 생성한 후 게시까지 자동화합니다.

### 1.2 핵심 가치

| 가치 | 설명 |
|------|------|
| **하이브리드 실행 모델** | 에이전틱(Agentic) + 일반 워크플로우 모두 지원 - 단순 자동화부터 AI 자율 판단까지 |
| **자동화** | 수집 → NLP → 스코어링 → 생성 → 게시까지 End-to-End 자동화 |
| **품질 검증** | LangGraph 기반 품질 검증 시스템으로 높은 품질 보장 |
| **확장성** | 플러그인 방식의 컬렉터, 액션, 어댑터 아키텍처 |
| **비용 효율** | 로컬 LLM(Ollama) + 클라우드 LLM 하이브리드 구성 |
| **Obsidian 통합** | 마크다운 + YAML 프론트매터 기반 콘텐츠 관리 |

### 1.3 하이브리드 실행 모델

Picko는 **두 가지 실행 모델**을 모두 지원합니다:

#### 🤖 에이전틱 모드 (Agentic Mode)

```
┌─────────────────────────────────────────────────────────────┐
│                    Agentic Workflow                         │
│                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────┐     │
│  │ 수집     │───▶│ 품질 검증    │───▶│ 동적 결정        │     │
│  │         │    │(QualityGraph)│    │ (dynamic_steps) │     │
│  └─────────┘    └──────────────┘    └────────┬────────┘     │
│                                               │             │
│                     ┌─────────────────────────┼─────────┐   │
│                     ▼                         ▼         ▼   │
│              ┌──────────┐            ┌──────────┐  ┌─────┐  │
│              │ 생성      │            │ 게시     │  │ ... │  │
│              └──────────┘            └──────────┘  └─────┘  │
│                                                             │
│  특징: AI가 품질 점수에 따라 다음 단계를 동적으로 결정             │
└─────────────────────────────────────────────────────────────┘
```

**특징**:
- **QualityGraph**: LangGraph 기반 상태 머신으로 품질 검증
- **동적 단계**: `dynamic_steps`로 런타임에 다음 작업 결정
- **자율 판단**: 임계값에 따라 자동 승인/거부/검토 분기
- **조건부 실행**: 표현식으로 조건부 분기

**사용 시나리오**:
- 신규 소스 발견 → 품질 검증 → 자동 등록/거부
- 콘텐츠 수집 → 품질 검증 → 자동 생성/스킵
- 소셜 팩 생성 → 품질 검증 → 자동 게시/보류

#### 📋 일반 워크플로우 모드 (Standard Workflow Mode)

```
┌─────────────────────────────────────────────────────────────┐
│                   Standard Workflow                         │
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│  │ Step 1  │───▶│ Step 2  │───▶│ Step 3 │───▶│ Step 4 │   │
│  │ 수집     │    │ NLP     │    │ 스코어링 │    │ 생성    │   │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘   │
│                                                             │
│  특징: 미리 정의된 순서대로 단계 실행                            │
└─────────────────────────────────────────────────────────────┘
```

**특징**:
- **순차 실행**: YAML에 정의된 순서대로 단계 실행
- **배치 처리**: 대량 아이템 분할 처리
- **폴백 지원**: 실패 시 대체 액션 실행
- **Dry-run**: 실제 실행 없이 테스트

**사용 시나리오**:
- 일일 RSS 수집 파이프라인
- 승인된 콘텐츠 일괄 생성
- 예약된 게시 작업

#### 🔄 모드 비교

| 구분 | 에이전틱 모드 | 일반 워크플로우 |
|------|---------------|-----------------|
| **결정 주체** | AI (QualityGraph) | 미리 정의된 규칙 |
| **단계 결정** | 런타임 동적 생성 | YAML 고정 순서 |
| **분기 처리** | 신뢰도 기반 자동 | 조건문으로 제어 |
| **적합한 작업** | 품질 판단 필요 | 반복적 자동화 |
| **예시** | `agentic_pipeline.yml` | `daily_pipeline.yml` |

### 1.3 기술 스택

```
Python 3.13+
├── LLM: Ollama (로컬), OpenAI, Anthropic, OpenRouter, Relay
├── 임베딩: sentence-transformers (로컬), OpenAI
├── 프레임워크: LangGraph (품질 검증), Jinja2 (템플릿)
├── 렌더링: Playwright (HTML → 이미지)
└── 스토리지: Obsidian Vault (마크다운 파일) -> 교체 필요
```

---

## 2. 아키텍처

### 2.1 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestration Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Workflow YAML │  │ ActionRegistry│  │ WorkflowEngine       │  │
│  │ (config/)     │  │ (actions.py)  │  │ (engine.py)          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────────┐    ┌─────────────────┐
│  Collectors   │    │  Quality System   │    │   Generators    │
│  ┌─────────┐  │    │  ┌─────────────┐  │    │  ┌───────────┐  │
│  │  RSS    │  │    │  │ QualityGraph│  │    │  │ Longform  │  │
│  │Perplexity│  │    │  │ Primary     │  │    │  │ Packs     │  │
│  └─────────┘  │    │  │ CrossCheck  │  │    │  │ Image     │  │
└───────────────┘    │  │ Feedback    │  │    │  └───────────┘  │
                     │  └─────────────┘  │    └─────────────────┘
                     └───────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────────┐    ┌─────────────────┐
│  Discovery    │    │  Core Services    │    │   Publishers    │
│  ┌─────────┐  │    │  ┌─────────────┐  │    │  ┌───────────┐  │
│  │ Reddit  │  │    │  │ LLM Client  │  │    │  │ Twitter   │  │
│  │ Mastodon│  │    │  │ Embedding   │  │    │  │ (Future)  │  │
│  │ Threads │  │    │  │ Scoring     │  │    │  └───────────┘  │
│  └─────────┘  │    │  │ Vault IO    │  │    └─────────────────┘
└───────────────┘    │  └─────────────┘  │
                     └───────────────────┘
```

### 2.2 데이터 플로우

```
RSS/Perplexity ──▶ 수집(Collector) ──▶ 중복제거 ──▶ NLP(요약/태깅)
                                                          │
                                                          ▼
Obsidian Vault ◀── 콘텐츠 생성 ◀── 품질 검증 ◀── 스코어링
       │
       └──▶ 게시(Publisher) ──▶ 성과 분석(Analytics)
```

### 2.3 디렉토리 구조

```
picko-scripts/
├── picko/                      # 핵심 모듈 (importable package)
│   ├── config.py               # 설정 로더 (dataclass, .env 자동 로드)
│   ├── vault_io.py             # Obsidian 마크다운 I/O
│   ├── llm_client.py           # 멀티 프로바이더 LLM 클라이언트
│   ├── embedding.py            # 로컬 우선 임베딩 (sentence-transformers)
│   ├── scoring.py              # 콘텐츠 스코어링 알고리즘
│   ├── account_context.py      # 계정 페르소나/스타일 로더
│   ├── prompt_loader.py        # 외부 프롬프트 로더 (Jinja2)
│   ├── prompt_composer.py      # 멀티레이어 프롬프트 조합
│   ├── templates.py            # Jinja2 템플릿 정의
│   ├── html_renderer.py        # Playwright 기반 HTML→이미지 렌더링
│   ├── multimedia_io.py        # 멀티미디어 I/O 관리
│   ├── source_manager.py       # RSS 소스 메타데이터 관리
│   ├── collectors/             # 모듈형 컬렉터 아키텍처
│   │   ├── base.py             # BaseCollector, CollectedItem
│   │   ├── rss.py              # RSS 피드 컬렉터
│   │   └── perplexity.py       # Perplexity Task 결과 컬렉터
│   ├── discovery/              # 소스 발견 서브시스템
│   │   ├── base.py             # BaseDiscoveryCollector, SourceCandidate
│   │   ├── gates.py            # HumanConfirmationGate
│   │   ├── orchestrator.py     # SourceDiscoveryOrchestrator
│   │   └── adapters/           # 플랫폼 어댑터
│   │       ├── reddit.py       # Reddit API
│   │       ├── mastodon.py     # Mastodon API
│   │       └── threads.py      # Threads API (placeholder)
│   ├── quality/                # 품질 검증 서브시스템
│   │   ├── graph.py            # QualityGraph (LangGraph)
│   │   ├── confidence.py       # 신뢰도 계산/판정
│   │   ├── feedback.py         # 피드백 루프
│   │   └── validators/         # 검증기
│   │       ├── primary.py      # 1차 검증
│   │       └── cross_check.py  # 교차 검증
│   ├── orchestrator/           # 워크플로우 오케스트레이션
│   │   ├── engine.py           # WorkflowEngine
│   │   ├── actions.py          # ActionRegistry, ActionConfig
│   │   ├── default_actions.py  # 기본 액션 구현
│   │   ├── expr.py             # 표현식 평가기
│   │   ├── batch.py            # 배치 처리
│   │   └── vault_adapter.py    # Vault 쿼리 인터페이스
│   └── notification/           # 알림/리뷰 봇
│       └── bot.py              # Telegram/Slack 봇
├── scripts/                    # 실행 CLI 스크립트
├── config/                     # 설정 파일
│   ├── config.yml              # 메인 설정
│   ├── sources.yml             # RSS 소스
│   ├── collectors.yml          # 컬렉터 설정
│   ├── prompts/                # LLM 프롬프트 템플릿
│   ├── workflows/              # 워크플로우 정의
│   ├── accounts/               # 계정 프로필
│   ├── layouts/                # 레이아웃 프리셋/테마
│   └── reference_styles/       # 레퍼런스 스타일
├── tests/                      # pytest 테스트
├── logs/                       # 일일 로테이션 로그
└── cache/                      # 임베딩 캐시
```

---

## 3. 구현된 기능

### 3.1 핵심 모듈 (`picko/`)

#### 3.1.1 LLM 클라이언트 (`llm_client.py`)

**파일**: `picko/llm_client.py`

| 기능 | 설명 |
|------|------|
| 멀티 프로바이더 | Ollama, OpenAI, Anthropic, OpenRouter, Relay 지원 |
| 태스크별 LLM | `summary_llm` (로컬), `writer_llm` (클라우드) 분리 |
| 자동 폴백 | 로컬 LLM 실패 시 클라우드 LLM으로 자동 전환 |
| 스트리밍 | `generate_stream()` 지원 |

**지원 모델**:
```yaml
# 로컬 (Ollama)
summary_llm:
  provider: "ollama"
  model: "qwen2.5:3b" | "deepseek-r1:7b" | "llama3.3:70b"

# 클라우드
writer_llm:
  provider: "openai" | "anthropic" | "openrouter" | "relay"
  model: "gpt-4o-mini" | "claude-3.5-sonnet"
```

#### 3.1.2 임베딩 (`embedding.py`)

**파일**: `picko/embedding.py`

| 기능 | 설명 |
|------|------|
| 로컬 우선 | sentence-transformers (BAAI/bge-m3) |
| Ollama 임베딩 | mxbai-embed-large:1024, qwen3-embedding:0.6b |
| OpenAI 폴백 | text-embedding-3-small |
| 캐싱 | 디스크 캐시로 비용 절감 |
| 유사도 검색 | `find_similar()`, 코사인 유사도 |

#### 3.1.3 스코어링 (`scoring.py`)

**파일**: `picko/scoring.py`

| 기능 | 설명 |
|------|------|
| 다차원 평가 | 참신도(novelty), 관련도(relevance), 품질(quality) |
| 가중치 설정 | config.yml에서 가중치 조정 가능 |
| 신선도 감쇠 | 반감기 기반 시간 가중치 |
| 자동 게이트 | `auto_approve` / `auto_reject` 임계값 |

```python
# 스코어 계산 예시
score = novelty * 0.3 + relevance * 0.4 + quality * 0.3
final_score = score * freshness_factor
```

#### 3.1.4 Vault I/O (`vault_io.py`)

**파일**: `picko/vault_io.py`

| 기능 | 설명 |
|------|------|
| 마크다운 읽기/쓰기 | YAML 프론트매터 파싱/직렬화 |
| 프론트매터 업데이트 | 기존 내용 유지하며 메타데이터만 수정 |
| 디렉토리 관리 | `ensure_dir()`, 파일 목록 조회 |

#### 3.1.5 프롬프트 시스템

**파일**: `picko/prompt_loader.py`, `picko/prompt_composer.py`

| 기능 | 설명 |
|------|------|
| Jinja2 템플릿 | `config/prompts/`에서 로드 |
| 계정별 오버라이드 | `config/accounts/<account>/prompts/` |
| 멀티레이어 조합 | base + style + identity + context |

**프롬프트 구조**:
```
config/prompts/
├── longform/
│   ├── default.md
│   ├── with_exploration.md
│   └── with_reference.md
├── packs/
│   ├── twitter.md
│   ├── linkedin.md
│   └── newsletter.md
├── image/
│   ├── default.md
│   ├── twitter.md
│   ├── linkedin.md
│   └── newsletter.md
├── exploration/
│   └── default.md
└── reference/
    └── analyze.md
```

### 3.2 컬렉터 (`picko/collectors/`)

#### 3.2.1 RSS 컬렉터

**파일**: `picko/collectors/rss.py`

```python
class RSSCollector(BaseCollector):
    """RSS 피드에서 아이템 수집"""

    async def collect(self, source: SourceMeta) -> List[CollectedItem]:
        # feedparser로 RSS 파싱
        # CollectedItem으로 변환
        # 중복 제거
```

**지원 소스 타입**: `rss`

#### 3.2.2 Perplexity 컬렉터

**파일**: `picko/collectors/perplexity.py`

```python
class PerplexityCollector(BaseCollector):
    """Perplexity Task 결과 수집"""

    async def collect(self, source: SourceMeta) -> List[CollectedItem]:
        # Inbox/Perplexity/ 디렉토리 스캔
        # .md / .html 파싱
        # 처리된 파일 아카이브
```

**지원 소스 타입**: `perplexity`

### 3.3 오케스트레이터 (`picko/orchestrator/`)

#### 3.3.1 WorkflowEngine

**파일**: `picko/orchestrator/engine.py`

```python
class WorkflowEngine:
    """YAML 정의 워크플로우 실행 엔진"""

    def run(self, workflow_path: str, dry_run: bool = False) -> bool:
        # YAML 로드
        # 단계별 실행
        # 조건 평가
        # 배치 처리
        # 동적 단계 삽입
        # 폴백 실행
```

**워크플로우 기능**:

| 기능 | 설명 | 예시 |
|------|------|------|
| 조건부 실행 | `${{ vault.count(...) > 0 }}` | 조건 만족 시에만 실행 |
| 배치 처리 | `batch.size: 10`, `batch.delay: "10s"` | 대량 아이템 분할 처리 |
| 동적 단계 | `dynamic_steps` 또는 액션 출력 | 런타임에 단계 추가 |
| 폴백 | `fallback` 설정 | 실패 시 대체 액션 실행 |
| Dry-run | `--dry-run` 플래그 | 실제 실행 없이 테스트 |

#### 3.3.2 기본 액션

**파일**: `picko/orchestrator/default_actions.py`

| 액션 | 설명 | 스크립트 |
|------|------|----------|
| `collector.run` | RSS/Perplexity 수집 | `scripts/daily_collector.py` |
| `generator.run` | 콘텐츠 생성 | `scripts/generate_content.py` |
| `renderer.run` | 이미지 렌더링 | `scripts/render_media.py` |
| `publisher.run` | 게시 | `picko/publisher.py` |
| `quality.verify` | 품질 검증 | `picko/quality/graph.py` |
| `embedding.check_duplicate` | 중복 탐지 | `picko/embedding.py` |
| `engagement.sync` | 성과 동기화 | `scripts/engagement_sync.py` |

#### 3.3.3 표현식 언어

**파일**: `picko/orchestrator/expr.py`

```yaml
# 지원 표현식
vault.count(path, filter)          # Vault 노트 개수
vault.list(path, filter)           # Vault 노트 목록
vault.field(path, field)           # 프론트매터 필드
steps.<name>.outputs.<key>         # 이전 단계 출력
> < >= <= == !=                    # 비교 연산자
contains_topic(...)                # 헬퍼 함수
score_range(...)                   # 헬퍼 함수
has_quality_flag(...)              # 헬퍼 함수
```

**예시**:
```yaml
steps:
  - name: check_items
    action: vault.count
    args:
      path: "Inbox/Inputs"
      filter: "writing_status=auto_ready"

  - name: generate
    action: generator.run
    condition: "${{ steps.check_items.outputs.count > 0 }}"
```

### 3.4 품질 시스템 (`picko/quality/`)

#### 3.4.1 QualityGraph (LangGraph)

**파일**: `picko/quality/graph.py`

```
┌─────────────────┐
│  Primary        │
│  Validation     │
└────────┬────────┘
         │
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
┌───────┐ ┌───────┐ ┌─────────┐
│Approve│ │Reject │ │Cross    │
│       │ │       │ │Check    │
└───────┘ └───────┘ └────┬────┘
                       │
                       ▼
              ┌────────────────┐
              │ Confidence     │
              │ Calculation    │
              └────────┬───────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
         ┌─────────┐      ┌─────────┐
         │ APPROVED│      │ REVIEW  │
         └─────────┘      └─────────┘
```

**상태 머신**:
1. **Primary Validation**: 1차 LLM 검증
2. **Cross-Check**: 2차 독립 검증 (다른 모델)
3. **Confidence Calculation**: 신뢰도 계산
4. **Verdict**: 승인/거부/검토 필요

#### 3.4.2 검증기

**파일**: `picko/quality/validators/primary.py`, `cross_check.py`

| 검증기 | 설명 |
|--------|------|
| PrimaryValidator | 1차 LLM 기반 검증 |
| CrossCheckValidator | 다른 프로바이더로 독립 검증 |

**교차 검증 로직**:
```python
# 다른 프로바이더 자동 선택
PROVIDER_ALTERNATIVES = {
    "openai": "anthropic",
    "anthropic": "openai",
    "relay": "openai",
}
```

#### 3.4.3 신뢰도 계산

**파일**: `picko/quality/confidence.py`

```python
def calculate_final_confidence(
    primary: float,
    cross_check: Optional[float] = None,
    external: Optional[float] = None,
    enhanced_mode: bool = False
) -> float:
    # 가중 평균
    # 교차 검증 불일치 시 50% 페널티
    # [0, 1] 범위로 정규화
```

**임계값**:
- `auto_approve_threshold: 0.85` - 자동 승인
- 일반 모드 vs 강화 모드 (신규 소스)

### 3.5 디스커버리 시스템 (`picko/discovery/`)

#### 3.5.1 소스 발견 오케스트레이터

**파일**: `picko/discovery/orchestrator.py`

```python
class SourceDiscoveryOrchestrator:
    """새 소스 발견 및 등록"""

    async def discover(
        self,
        account: str,
        keywords: List[str],
        platforms: List[str]
    ) -> List[SourceCandidate]:
        # 어댑터 병렬 실행
        # HumanConfirmationGate 적용
        # SourceManager에 등록
```

#### 3.5.2 플랫폼 어댑터

| 어댑터 | 파일 | 상태 |
|--------|------|------|
| Reddit | `adapters/reddit.py` | ✅ 구현됨 |
| Mastodon | `adapters/mastodon.py` | ✅ 구현됨 |
| Threads | `adapters/threads.py` | ⏳ Placeholder (Meta App Review 대기) |

#### 3.5.3 Human Confirmation Gate

**파일**: `picko/discovery/gates.py`

```python
class HumanConfirmationGate:
    """소스 승인/거부 자동화 규칙"""

    def evaluate(self, candidate: SourceCandidate) -> GateResult:
        # 자동 승인 조건 확인
        # 자동 거부 조건 확인
        # 검토 필요 판정
```

### 3.6 멀티미디어 시스템

#### 3.6.1 HTML 렌더러

**파일**: `picko/html_renderer.py`

```python
class ImageRenderer:
    """Playwright 기반 HTML → PNG 렌더링"""

    async def render(
        self,
        template_name: str,
        content: dict,
        layout: LayoutConfig
    ) -> bytes:
        # Jinja2 템플릿 렌더링
        # Playwright로 스크린샷
        # PNG 반환
```

#### 3.6.2 레이아웃 시스템

**파일**: `picko/layout_config.py`, `config/layouts/`

```
config/layouts/
├── _defaults.yml              # 기본값
├── presets/
│   ├── corporate.yml
│   ├── minimal_dark.yml
│   ├── minimal_light.yml
│   ├── social_gradient.yml
│   └── vibrant.yml
└── themes/
    ├── socialbuilders.yml
    ├── tech_startup.yml
    └── fitness_wellness.yml
```

**레이아웃 우선순위**:
```
defaults → preset → theme → CLI overrides
```

### 3.7 CLI 스크립트 (`scripts/`)

| 스크립트 | 용도 | 주요 옵션 |
|----------|------|-----------|
| `daily_collector.py` | RSS 수집 파이프라인 | `--date`, `--sources`, `--dry-run` |
| `generate_content.py` | 콘텐츠 생성 | `--type`, `--force`, `--auto-all` |
| `run_workflow.py` | 워크플로우 실행 | `--workflow`, `--dry-run` |
| `render_media.py` | 이미지 렌더링 | `render`, `status`, `review` |
| `health_check.py` | 시스템 상태 확인 | `--json` |
| `validate_output.py` | 콘텐츠 검증 | `--path`, `--recursive` |
| `source_curator.py` | 소스 품질 평가 | `--threshold`, `--export-csv` |
| `source_discovery.py` | 새 소스 발견 | `--keywords`, `--max-results` |
| `style_extractor.py` | 스타일 추출 | `--urls`, `--name` |
| `explore_topic.py` | 주제 탐색 | `--input-id`, `--account` |
| `archive_manager.py` | 아카이브 관리 | `--days` |
| `retry_failed.py` | 실패 재시도 | `--date`, `--stage` |

---

## 4. 워크플로우 시스템

### 4.0 하이브리드 실행 모델

Picko는 **두 가지 실행 모드**를 모두 지원하는 하이브리드 시스템입니다:

#### 🤖 에이전틱 모드 (Agentic Mode)

AI가 품질 점수와 컨텍스트를 기반으로 **자율적으로 판단**하고 다음 단계를 결정합니다.

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   수집      │────▶│  QualityGraph   │────▶│   동적 결정      │
│  (Collector)│     │  (LangGraph)    │     │ (dynamic_steps)  │
└─────────────┘     └─────────────────┘     └──────────────────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          ▼                        ▼                        ▼
                    ┌──────────┐           ┌──────────┐           ┌──────────┐
                    │  승인    │           │  거부    │           │  검토    │
                    │ (approve)│           │ (reject) │           │ (review) │
                    └──────────┘           └──────────┘           └──────────┘
                         │                      │                        │
                         ▼                      ▼                        ▼
                    ┌──────────┐           ┌──────────┐           ┌──────────┐
                    │  생성    │           │  스킵    │           │  알림    │
                    │ (publish)│           │  (skip)  │           │  (notify)│
                    └──────────┘           └──────────┘           └──────────┘
```

**특징**:
- **QualityGraph**: LangGraph 기반 상태 머신으로 품질 검증
- **동적 단계**: `dynamic_steps`로 런타임에 다음 작업 결정
- **자율 판단**: 신뢰도 임계값에 따라 자동 승인/거부/검토 분기
- **강화 검증**: 신규 소스에 대해 더 엄격한 검증 적용

**사용 시나리오**:
- 신규 소스 발견 → 품질 검증 → 자동 등록/거부
- 콘텐츠 품질 평가 → 신뢰도 기반 자동 승인
- 복잡한 의사결정이 필요한 파이프라인

#### 📋 일반 워크플로우 모드 (Standard Workflow Mode)

미리 정의된 규칙에 따라 **순차적으로 단계를 실행**합니다.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Step 1    │────▶│   Step 2    │────▶│   Step 3    │────▶│   Step 4    │
│  (collect)  │     │   (nlp)     │     │  (score)    │     │ (generate)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  [조건부 실행]      [조건부 실행]      [조건부 실행]      [조건부 실행]
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   결과 집계  │
                            └─────────────┘
```

**특징**:
- **순차 실행**: YAML에 정의된 순서대로 단계 실행
- **배치 처리**: 대량 아이템 분할 처리 (`batch.size`, `batch.delay`)
- **폴백 지원**: 실패 시 대체 액션 실행 (`fallback`)
- **Dry-run**: 실제 실행 없이 테스트 (`--dry-run`)
- **조건부 실행**: 표현식으로 조건부 분기 (`condition`)

**사용 시나리오**:
- 일일 RSS 수집 파이프라인 (매일 반복)
- 승인된 콘텐츠 일괄 생성
- 예약된 게시 작업

#### 🔄 모드 비교

| 구분 | 에이전틱 모드 | 일반 워크플로우 |
|------|---------------|-----------------|
| **결정 주체** | AI (QualityGraph) | 미리 정의된 규칙 |
| **단계 결정** | 런타임 동적 생성 | YAML 고정 순서 |
| **분기 처리** | 신뢰도 기반 자동 | 조건문으로 제어 |
| **적합한 작업** | 품질 판단 필요 | 반복적 자동화 |
| **복잡도** | 높음 | 낮음 |
| **예측 가능성** | 낮음 (AI 판단) | 높음 (고정 규칙) |
| **워크플로우 예시** | `agentic_pipeline.yml` | `daily_pipeline.yml` |

#### 💡 언제 어떤 모드를 사용할까?

| 상황 | 추천 모드 | 이유 |
|------|-----------|------|
| 매일 동일한 RSS 수집 | 일반 워크플로우 | 예측 가능, 반복적 |
| 새 소스 발견 및 등록 | 에이전틱 | 품질 판단 필요 |
| 콘텐츠 자동 승인/거부 | 에이전틱 | 신뢰도 기반 결정 |
| 승인된 콘텐츠 일괄 생성 | 일반 워크플로우 | 단순 반복 작업 |
| 복잡한 의사결정 파이프라인 | 에이전틱 | 동적 분기 필요 |
| 단순 ETL 작업 | 일반 워크플로우 | 고정된 순서 |

---

### 4.1 워크플로우 YAML 구조

```yaml
name: workflow_name
description: 워크플로우 설명

steps:
  - name: step_name
    action: action.name
    args:
      key: value
    condition: "${{ expression }}"
    batch:
      source: "${{ vault.list(...) }}"
      size: 10
      delay: "10s"
    dynamic_steps:
      - name: dynamic_step
        action: action.name
        args: {...}
    fallback:
      action: fallback.action
      args: {...}
```

### 4.2 내장 워크플로우

**파일**: `config/workflows/`

| 워크플로우 | 모드 | 설명 |
|------------|------|------|
| `daily_pipeline.yml` | 📋 일반 | 일일 수집 → 중복제거 → 생성 (고정 순서) |
| `agentic_pipeline.yml` | 🤖 에이전틱 | 발견 → 품질검증(QualityGraph) → 동적 생성/게시 |
| `approved_packs.yml` | 📋 일반 | 승인된 롱폼 → 소셜 팩 생성 (배치) |
| `twitter_publish.yml` | 📋 일반 | 트위터 팩 게시 |
| `image_generation.yml` | 📋 일반 | 이미지 프롬프트 → 렌더링 |

**에이전틱 워크플로우 상세** (`agentic_pipeline.yml`):

```yaml
steps:
  - name: collect_candidates
    action: collector.run

  - name: verify_quality
    action: quality.verify          # ← QualityGraph 실행
    dynamic_steps:                # ← 동적 단계 정의
      - name: generate_longform
        action: generator.run
        condition: "${{ steps.verify_quality.outputs.verified }}"

      - name: publish_twitter
        action: publisher.run
        condition: "${{ steps.verify_quality.outputs.verified }}"
```

**일반 워크플로우 상세** (`daily_pipeline.yml`):

```yaml
steps:
  - name: collect
    action: collector.run

  - name: dedup
    action: embedding.check_duplicate

  - name: generate
    action: generator.run
    batch:                       # ← 배치 처리
      source: "${{ vault.list('Inbox/Inputs', 'writing_status=auto_ready') }}"
      size: 10
      delay: "10s"
```
### 4.3 워크플로우 실행

```bash
# 일반 워크플로우 실행 (예측 가능한 순차 실행)
python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml

# 에이전틱 워크플로우 실행 (AI 자율 판단)
python -m scripts.run_workflow --workflow config/workflows/agentic_pipeline.yml

# Dry-run 모드 (실제 실행 없이 테스트)
python -m scripts.run_workflow --workflow config/workflows/agentic_pipeline.yml --dry-run

# 특정 계정으로 실행
python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml --account socialbuilders
```
---

## 5. 설정 시스템

### 5.1 메인 설정 (`config/config.yml`)

```yaml
# Vault 설정
vault:
  root: "mock_vault"
  inbox: "Inbox/Inputs"
  digests: "Inbox/Inputs/_digests"
  content: "Content"
  longform: "Content/Longform"
  packs: "Content/Packs"
  assets: "Assets"
  images_prompts: "Assets/Images/_prompts"
  archive: "Archive"
  logs_publish: "Logs/Publish"

# 요약용 LLM (로컬 우선)
summary_llm:
  provider: "ollama"
  model: "qwen2.5:3b"
  temperature: 0.3
  max_tokens: 1000
  base_url: "http://localhost:11434"
  fallback_provider: "relay"
  fallback_model: "gpt-4o-mini"
  fallback_api_key_env: "RELAY_API_KEY"

# 글쓰기용 LLM (클라우드)
writer_llm:
  provider: "relay"
  model: "gpt-4o-mini"
  temperature: 0.8
  max_tokens: 2000
  api_key_env: "RELAY_API_KEY"

# 임베딩 설정
embedding:
  provider: "ollama"
  model: "qwen3-embedding:0.6b"
  dimensions: 1024
  base_url: "http://localhost:11434"
  cache_enabled: true
  cache_dir: "cache/embeddings"
  fallback_provider: "local"
  fallback_model: "BAAI/bge-m3"

# 스코어링 가중치
scoring:
  weights:
    novelty: 0.3
    relevance: 0.4
    quality: 0.3
  freshness_half_life_days: 7.0
  thresholds:
    auto_approve: 0.85
    auto_reject: 0.3
    minimum_display: 0.4

# 품질 검증
quality:
  enabled: true
  primary:
    model: "gpt-4o-mini"
  cross_check:
    model: "claude-3-5-sonnet-20241022"
  final:
    auto_approve_threshold: 0.85
  feedback:
    enabled: true

# 알림
notification:
  provider: "telegram"
  review_timeout_hours: 72
```

### 5.2 계정 프로필 (`config/accounts/`)

```yaml
# config/accounts/socialbuilders.yml
account_id: "socialbuilders"
name: "Social Builders Club"
description: "AI/스타트업/성장 전문 커뮤니티"

style_name: "founder_tech_brief"

interests:
  primary: ["AI", "스타트업", "성장"]
  secondary: ["생산성", "마케팅", "팀 빌딩"]

keywords:
  high: ["AI", "GPT", "LLM", "스타트업", "창업"]
  medium: ["성장", "마케팅", "PM", "개발"]
  low: ["일반", "뉴스"]

trusted_sources:
  - "techcrunch.com"
  - "openai.com"

channels:
  twitter:
    enabled: true
    max_length: 280
    tone: "friendly"
    hashtags: true
  linkedin:
    enabled: true
    max_length: 3000
    tone: "professional"
  newsletter:
    enabled: true
    tone: "conversational"

content_settings:
  use_exploration: true
  apply_reference_style: true
  generate_packs: true
  generate_image_prompts: true

visual_settings:
  default_layout_preset: "social_gradient"
  channel_layouts:
    twitter: "minimal_dark"
    linkedin: "corporate"
```

---

## 6. 테스트

### 6.1 테스트 구조

**파일**: `tests/`

> 아래 표는 주요/대표 테스트 파일 예시이며, 실제 `tests/` 디렉토리에는 이외에도 더 많은 세부 테스트가 존재합니다.

| 테스트 파일 | 대상 모듈 | 타입 |
|-------------|-----------|------|
| `test_llm_client.py` | `llm_client.py` | Unit |
| `test_embedding.py` | `embedding.py` | Unit |
| `test_scoring.py` | `scoring.py` | Unit |
| `test_integration.py` | `vault_io.py` | Integration |
| `test_vault_adapter.py` | `vault_adapter.py` | Unit |
| `test_orchestrator_engine.py` | `engine.py` | Unit |
| `test_quality_graph.py` | `graph.py` | Unit |
| `test_e2e_dryrun.py` | 전체 파이프라인 | E2E (slow) |

### 6.2 테스트 커버리지

| 모듈 | 커버리지 | 평가 |
|------|----------|------|
| `llm_client.py` | 높음 | 로직/라우팅 잘 테스트됨 |
| `embedding.py` | 높음 | 기능/엣지케이스 포괄 |
| `scoring.py` | 높음 | 다양한 시나리오 커버 |
| `vault_io.py` | 중간 | 통합 테스트 있음, 엣지케이스 추가 필요 |

### 6.3 테스트 실행

```bash
# 전체 테스트
pytest

# 단위 테스트만
pytest -m unit

# 통합 테스트만
pytest -m integration

# 커버리지 리포트
pytest --cov=picko --cov-report=html

# 느린 테스트 제외
pytest -m "not slow"
```

### 6.4 CI/CD

**파일**: `.github/workflows/test.yml`

- PR 시 자동 테스트 실행
- 느린 테스트(E2E)는 별도 스케줄로 실행

---

## 7. 계획된 기능 (Roadmap)

### 7.1 Phase 3: 분석 & 자동화 (진행 중)

#### 7.1.1 성과 메트릭 동기화

**파일**: `scripts/engagement_sync.py`

| 항목 | 상태 | 작업 필요 |
|------|------|-----------|
| Twitter/X 메트릭 | 부분 구현 | API 연동 안정화 |
| LinkedIn 메트릭 | TODO | OAuth 플로우 구현 |
| Instagram/YouTube | 미구현 | 커넥터 추가 |

**구현 사항**:
- 플랫폼별 OAuth 인증
- API 호출 및 레이트 리밋 처리
- Publish Log와 메트릭 매핑

#### 7.1.2 스코어 캘리브레이터 자동화

**파일**: `scripts/score_calibrator.py`

| 항목 | 상태 | 작업 필요 |
|------|------|-----------|
| 분석/리포트 | ✅ 완료 | - |
| 가중치 자동 적용 | TODO | `apply_weights()` 구현 |

**구현 사항**:
- `config.yml` 안전 업데이트 (백업, 검증)
- 변경사항 diff 생성 또는 커밋/PR 자동화
- 감사 로그 기록

#### 7.1.3 중복 탐지 파이프라인 통합

**파일**: `scripts/duplicate_checker.py`

| 항목 | 상태 | 작업 필요 |
|------|------|-----------|
| CLI/알고리즘 | ✅ 완료 | - |
| 파이프라인 통합 | TODO | `daily_collector._score()`에 통합 |
| 설정 노출 | 부분 구현 | `config.yml`에 `deduplication.embedding_threshold` 추가 완료, `auto_reject_duplicates` 필드 추가 예정 |

**구현 사항**:
```yaml
# config/config.yml (현재 상태)
deduplication:
  embedding_threshold: 0.92

# config/config.yml (확장 예정)
deduplication:
  embedding_threshold: 0.92
  auto_reject_duplicates: true
```

### 7.2 Phase 3: 어댑터 완성

#### 7.2.1 Threads 어댑터

**파일**: `picko/discovery/adapters/threads.py`

| 항목 | 상태 | 비고 |
|------|------|------|
| API 호출 | Placeholder | Meta App Review 승인 필요 |
| 응답 매핑 | 미구현 | SourceCandidate 변환 |
| 테스트 | Placeholder 검증 | 실제 API 테스트 필요 |

**블로커**: Meta App Review 승인 대기

#### 7.2.2 Reddit/Mastodon 개선

| 항목 | 상태 |
|------|------|
| 기본 기능 | ✅ 구현됨 |
| 레이트 리밋 추적 | 개선 필요 |
| 에러 복구 | 개선 필요 |

### 7.3 Phase 4: 품질 시스템 강화

#### 7.3.1 자동 검증

**파일**: `specs/007-agentic-framework/tasks.md`

```yaml
# config/config.yml (현재 적용됨)
generation:
  auto_validate: true
```

**구현 사항**:
- 생성 후 자동으로 `OutputValidator.validate_path()` 실행
- 실패 시 재시도 또는 검토 필요 마킹

#### 7.3.2 Vault 프론트매터 확장

**필드 추가**:
```yaml
---
quality:
  verdict: "approved"
  confidence: 0.92
  primary_score: 0.9
  cross_check_score: 0.95

job_history:
  - action: "quality.verify"
    timestamp: "2026-03-04T12:00:00Z"
    result: "approved"
---
```

#### 7.3.3 LangGraph 체크포인트

**파일**: `specs/007-agentic-framework/tasks.md`

| 항목 | 상태 |
|------|------|
| SQLite 체크포인트 | 선택적 의존성 추가 필요 |
| 상태 복구 | 미구현 |

### 7.4 Phase 5: 확장 (Future)

| 기능 | 설명 |
|------|------|
| Instagram 어댑터 | 소스 발견 확장 |
| Facebook 어댑터 | 소스 발견 확장 |
| 코퍼레이트 스타일 | 멀티미디어 템플릿 확장 |
| 이미지 소스 매니저 | Unsplash/Pexels 통합 |

---

## 8. 개발자 온보딩

### 8.1 환경 설정

```bash
# 1. 리포지토리 클론
git clone https://github.com/namu-k/picko-scripts.git
cd picko-scripts

# 2. 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일 편집: API 키 입력

# 5. 시스템 상태 확인
python -m scripts.health_check

# 6. 테스트 실행
pytest -m unit
```

### 8.2 필수 환경 변수

```bash
# .env
RELAY_API_KEY=your_key          # 필수 (또는 OPENAI_API_KEY)
OPENROUTER_API_KEY=your_key     # 선택
ANTHROPIC_API_KEY=your_key      # 선택

# 선택 - 디스커버리 어댑터
THREADS_ACCESS_TOKEN=your_token
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
MASTODON_ACCESS_TOKEN=your_token
MASTODON_INSTANCE=mastodon.social

# 선택 - 리뷰 봇
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 8.3 핵심 진입점

| 작업 | 진입점 | 설명 |
|------|--------|------|
| 콘텐츠 수집 | `scripts/daily_collector.py` | RSS/Perplexity 수집 |
| 콘텐츠 생성 | `scripts/generate_content.py` | 롱폼/팩/이미지 생성 |
| 워크플로우 | `scripts/run_workflow.py` | YAML 기반 실행 |
| 워크플로우 정의 | `config/workflows/*.yml` | 커스텀 워크플로우 |
| 새 액션 추가 | `picko/orchestrator/default_actions.py` | 액션 등록 |

### 8.4 새 기능 추가 가이드

#### 새 컬렉터 추가

```python
# picko/collectors/new_collector.py
from picko.collectors.base import BaseCollector, CollectedItem

class NewCollector(BaseCollector):
    async def collect(self, source: SourceMeta) -> List[CollectedItem]:
        # 구현
        pass
```

#### 새 액션 추가

```python
# picko/orchestrator/default_actions.py
def register_default_actions(registry: ActionRegistry):
    registry.register("new.action", new_action_handler)

def new_action_handler(args: dict) -> ActionResult:
    # 구현
    return ActionResult(success=True, outputs={...})
```

#### 새 어댑터 추가

```python
# picko/discovery/adapters/new_adapter.py
from picko.discovery.base import BaseDiscoveryCollector, SourceCandidate

class NewDiscoveryAdapter(BaseDiscoveryCollector):
    async def discover(self, keywords: List[str]) -> List[SourceCandidate]:
        # 구현
        pass
```

### 8.5 디버깅

```bash
# 상세 로그
export LOG_LEVEL=DEBUG
python -m scripts.daily_collector --dry-run

# 특정 단계만 실행
python -m scripts.daily_collector --sources techcrunch

# LLM 호출 추적
# logs/YYYY-MM-DD/ 폴더에서 로그 확인
```

---

## 9. API 레퍼런스

### 9.1 LLM Client

```python
from picko.llm_client import LLMClient, get_summary_client, get_writer_client

# 요약용 클라이언트 (로컬 우선)
summary_client = get_summary_client()
result = summary_client.generate("Summarize: ...")

# 글쓰기용 클라이언트 (클라우드)
writer_client = get_writer_client()
article = writer_client.generate("Write a blog post about...")
```

### 9.2 Embedding

```python
from picko.embedding import get_embedding_manager

manager = get_embedding_manager()

# 텍스트 임베딩
embedding = manager.embed_text("Hello world")

# 유사한 문서 검색
similar = manager.find_similar(embedding, top_k=5, threshold=0.8)
```

### 9.3 Scoring

```python
from picko.scoring import ScoreCalculator, should_auto_approve

calculator = ScoreCalculator(config)
score = calculator.calculate(
    title="...",
    summary="...",
    tags=[...],
    account_context=account_context
)

if should_auto_approve(score):
    # 자동 승인
    pass
```

### 9.4 Vault IO

```python
from picko.vault_io import VaultIO

vault = VaultIO(config)

# 노트 읽기
note = vault.read_note("Inbox/Inputs/item.md")

# 프론트매터 업데이트
vault.update_frontmatter("Inbox/Inputs/item.md", {
    "writing_status": "auto_ready"
})

# 노트 쓰기
vault.write_note("Content/Longform/article.md", content, frontmatter)
```

### 9.5 Workflow Engine

```python
from picko.orchestrator.engine import WorkflowEngine
from picko.orchestrator.actions import ActionRegistry
from picko.orchestrator.default_actions import register_default_actions

registry = ActionRegistry()
register_default_actions(registry)

engine = WorkflowEngine(registry)
success = engine.run("config/workflows/daily_pipeline.yml", dry_run=True)
```

### 9.6 Quality Graph

```python
from picko.quality.graph import QualityGraph

graph = QualityGraph(config)
result = await graph.verify(
    item_id="abc123",
    title="Article Title",
    content="Article content...",
    enhanced_verification=False
)

print(result["verdict"])  # "approved" | "rejected" | "review"
print(result["confidence"])  # 0.0 - 1.0
```

---

## 10. 용어집

| 용어 | 정의 |
|------|------|
| **Vault** | Obsidian 마크다운 파일 저장소 |
| **Digest** | 일일 수집 결과 요약 파일 |
| **Frontmatter** | 마크다운 파일 상단의 YAML 메타데이터 |
| **CollectedItem** | 수집된 콘텐츠의 통일된 데이터 구조 |
| **SourceCandidate** | 발견된 새 소스 후보 |
| **Action** | 워크플로우에서 실행 가능한 작업 단위 |
| **Dynamic Steps** | 런타임에 동적으로 추가되는 워크플로우 단계 |
| **Quality Graph** | LangGraph 기반 품질 검증 상태 머신 |
| **Primary Validation** | 1차 LLM 기반 품질 검증 |
| **Cross-Check** | 다른 모델을 사용한 2차 독립 검증 |
| **Confidence** | 검증 결과의 신뢰도 점수 (0.0-1.0) |
| **Enhanced Verification** | 신규 소스에 대한 강화된 검증 모드 |

---

## 11. 참조 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| README | `/README.md` | 프로젝트 개요 |
| USER_GUIDE | `/USER_GUIDE.md` | 사용자 가이드 |
| CLAUDE.md | `/CLAUDE.md` | 개발자 가이드 (AI 어시스턴트용) |
| DEPLOYMENT | `/DEPLOYMENT.md` | 배포 가이드 |
| CHANGELOG | `/CHANGELOG.md` | 변경 이력 |
| SECURITY | `/SECURITY.md` | 보안 정책 |
| FOLLOWUPS | `/specs/archive/FOLLOWUPS.md` | 후속 작업 목록 (아카이브) |

---

## 12. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0.0 | 2026-03-04 | 초기 PRD 작성 |

---

*이 문서는 개발자 온보딩을 위해 작성되었습니다. 질문이나 제안은 GitHub Issues에 등록해 주세요.*
