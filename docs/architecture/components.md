# 컴포넌트 상세 설명

> **최종 수정**: 2026-03-04
> **대상 독자**: 개발자, 시스템 아키텍트
> **문서 성격**: 이 문서는 시스템의 **설계 개요**이며, 코드 메서드 시그니처와 정확히 일치하지 않을 수 있습니다. 정확한 API는 소스 코드를 참조하세요.

---

## 1. 컴포넌트 개요

이 문서는 Picko 시스템의 주요 컴포넌트들을 상세히 설명합니다. 각 컴포넌트의 역할, 인터페이스, 의존성 구조를 다룹니다.

---

## 2. 컴포넌트 상세

### 2.1 오케스트레이션 컴포넌트

#### 2.1.1 WorkflowEngine
**위치**: `picko/orchestrator/engine.py`

**역할**:
- YAML 정의 워크플로우 실행 엔진
- 단계별 실행 조율
- 조건부 평가 및 분기 처리

**주요 메소드**:
```python
class WorkflowEngine:
    def __init__(self, registry: ActionRegistry):
        # 액션 레지스트리 초기화

    def run(self, workflow_path: str, dry_run: bool = False) -> bool:
        # 워크플로우 실행

    def add_step(self, step: Step) -> None:
        # 단계 추가

    def evaluate_condition(self, condition: str, context: dict) -> bool:
        # 조건식 평가
```

**인터페이스**:
```python
# 워크플로우 정의 예시
workflow:
  name: "daily_pipeline"
  steps:
    - name: "collect"
      action: "collector.run"
      condition: "${{ vault.count('Inbox/Inputs') > 0 }}"

    - name: "generate"
      action: "generator.run"
      batch:
        source: "${{ vault.list('Inbox/Inputs', 'writing_status=auto_ready') }}"
        size: 10
        delay: "10s"
      fallback:
        action: "generator.retry"
        args: { max_retries: 3 }
```

**의존성**:
- `ActionRegistry`: 실행 가능한 액션 조회
- `VaultAdapter`: 조건 평가를 위한 Vault 접근
- `ExpressionEvaluator`: 조건식 평가

---

#### 2.1.2 ActionRegistry
**위치**: `picko/orchestrator/actions.py`

**역할**:
- 실행 가능한 액션의 등록 및 관리
- 액션 실행 시 권한 및 유효성 검사

**주요 메소드**:
```python
class ActionRegistry:
    def register(self, name: str, handler: callable, metadata: dict = None):
        # 액션 핸들러 등록

    def get_handler(self, name: str) -> callable:
        # 핸들러 조회

    def execute(self, action: str, args: dict) -> ActionResult:
        # 액션 실행
```

**액션 메타데이터**:
```python
# 액션 등록 예시
registry.register(
    name="collector.run",
    handler=collect_handler,
    metadata={
        "description": "콘텐츠 수집 실행",
        "args": ["source", "date"],
        "async": True,
        "timeout": 300
    }
)
```

**의존성**:
- 각 액션별 구현체 (예: `daily_collector.py`)

---

#### 2.1.3 ExpressionEvaluator
**위치**: `picko/orchestrator/expr.py`

**역할**:
- 워크플로우 내 표현식 평가
- 안전한 표현식 실행 환경 제공

**지원 표현식**:
```python
# Vault 접근
vault.count(path, filter)
vault.list(path, filter)
vault.field(path, field)

# 단계 출력 접근
steps.step_name.outputs.key

# 비교 연산자
>, >=, <, <=, ==, !=

# 헬퍼 함수
contains_topic(text, topics)
score_range(score, min, max)
has_quality_flag(item, flag)
```

**의존성**:
- `VaultAdapter`: Vault 데이터 접근
- `VaultSteps`: 이전 단계 결과

---

### 2.2 수집 컴포넌트

#### 2.2.1 BaseCollector
**위치**: `picko/collectors/__init__.py`

**역할**:
- 모든 컬렉터의 추상 기반 클래스
- 표준화된 수집 인터페이스 제공

**추상 메소드**:
```python
class BaseCollector(ABC):
    @abstractmethod
    def collect(self, account_id: str) -> list[CollectedItem]:
        """계정 컨텍스트로 콘텐츠 수집"""
        pass

    @abstractmethod
    def name(self) -> str:
        """컬렉터 식별자"""
        pass
```

**데이터 모델**:
```python
@dataclass
class CollectedItem:
    url: str
    title: str
    body: str
    source_id: str
    source_type: str
    published_at: str | None = None
    category: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)
```

**공통 기능**:
- 중복 제거
- 표준화된 출력 형식

---

#### 2.2.2 RSSCollector
**위치**: `picko/collectors/rss.py`

**역할**:
- RSS 피드에서 콘텐츠 수집
- 다양한 RSS 형식 지원

**주요 메소드**:
```python
class RSSCollector(BaseCollector):
    def collect(self, account_id: str) -> list[CollectedItem]:
        # feedparser로 RSS 파싱
        # CollectedItem으로 변환

    async def parse_feed(self, url: str) -> List[dict]:
        # RSS 피드 파싱
```

**지원 형식**:
- RSS 2.0
- Atom 1.0
- JSON Feed

**의존성**:
- `feedparser`: RSS 파싱
- `SourceMeta`: 소스 메타데이터

---

#### 2.2.3 PerplexityCollector
**위치**: `picko/collectors/perplexity.py`

**역할**:
- Perplexity Task 결과 수집
- 파일 시스템 기반 수집

**주요 메소드**:
```python
class PerplexityCollector(BaseCollector):
    def collect(self, account_id: str) -> list[CollectedItem]:
        # 디렉토리 스캔
        # 파일 파싱

    async def scan_directory(self, path: str) -> List[str]:
        # 파일 목록 조회
```

**지원 파일 형식**:
- `.md` (Markdown)
- `.html` (HTML)

**처리 방식**:
- 파일 변환 및 아카이브
- 중복 검사

---

### 2.3 품질 검증 컴포넌트

#### 2.3.1 QualityGraph
**위치**: `picko/quality/graph.py`

**역할**:
- LangGraph 기반 품질 검증 상태 머신
- 다단계 품질 평가

**상태 정의**:
```python
class QualityGraph:
    def __init__(self):
        # 상태 머신 초기화
        self.add_state("primary_validation")
        self.add_state("cross_check")
        self.add_state("confidence_calculation")
        self.add_state("verdict")

        # 전이 규칙 설정
        self.set_entry_point("primary_validation")
        self.add_edge("primary_validation", "cross_check")
        self.add_edge("cross_check", "confidence_calculation")
        self.add_edge("confidence_calculation", "verdict")
```

**주요 메소드**:
```python
class QualityGraph:
    async def verify(
        self,
        item_id: str,
        title: str,
        content: str,
        enhanced_verification: bool = False
    ) -> VerificationResult:
        # 품질 검증 실행
        pass

    def add_conditional_edges(self, state: str, condition: callable):
        # 조건부 전이 추가
```

**검증 결과**:
```python
@dataclass
class VerificationResult:
    verdict: "approved" | "rejected" | "review"
    confidence: float
    primary_score: float
    cross_check_score: Optional[float]
    feedback: str
```

**의존성**:
- `PrimaryValidator`: 1차 검증
- `CrossCheckValidator`: 2차 검증
- `ConfidenceCalculator`: 신뢰도 계산

---

#### 2.3.2 PrimaryValidator
**위치**: `picko/quality/validators/primary.py`

**역할**:
- 1차 LLM 기반 품질 검증
- 기본 품질 기준 평가

**검증 항목**:
- 콘텐츠 품질
- 관련성
- 독성/허위 정보
- 가독성

**의존성**:
- `LLMClient`: LLM 호출
- `PromptLoader`: 프롬프트 로드

---

#### 2.3.3 CrossCheckValidator
**위치**: `picko/quality/validators/cross_check.py`

**역할**:
- 다른 프로바이더로 독립 검증
- 검증 결과 비교

**특징**:
- 프로바이더 자동 선택
- 결과 불일치 감지
- 강화 검증 모드

**의존성**:
- `LLMClient`: 여러 프로바이더 지원
- `ProviderAlternatives`: 프로바이더 매핑

---

### 2.4 생성 컴포넌트

#### 2.4.1 ContentGenerator
**위치**: `scripts/generate_content.py`

**역할**:
- 다양한 형식의 콘텐츠 생성
- 플러그인 방식 확장

**지원 형식**:
- 롱폼 아티클
- 소셜 미디어 팩 (Twitter, LinkedIn)
- 이미지 프롬프트

**주요 메소드**:
```python
class ContentGenerator:
    async def generate_longform(self, item_id: str) -> None:
        # 롱폼 아티클 생성

    async def generate_packs(self, item_id: str) -> None:
        # 소셜 팩 생성

    async def generate_image_prompts(self, item_id: str) -> None:
        # 이미지 프롬프트 생성
```

**의존성**:
- `LLMClient`: 글쓰기용 LLM
- `PromptComposer`: 프롬프트 조합
- `TemplateRenderer`: 템플릿 렌더링
- `VaultIO`: 결과 저장

---

#### 2.4.2 TemplateRenderer
**위치**: `picko/templates.py`

**역할**:
- Jinja2 템플릿 기반 콘텐츠 렌더링
- 동적 템플릿 로드

**주요 메소드**:
```python
class TemplateRenderer:
    def render(self, template_name: str, context: dict) -> str:
        # 템플릿 렌더링

    def load_template(self, name: str) -> Template:
        # 템플릿 로드
```

**템플릿 종류**:
- `longform`: 롱폼 아티클
- `packs`: 소셜 미디어 팩
- `image`: 이미지 프롬프트
- `exploration`: 주제 탐색

**의존성**:
- `Jinja2`: 템플릿 엔진
- `PromptLoader`: 외부 프롬프트 로드

---

### 2.5 핵심 서비스 컴포넌트

#### 2.5.1 LLMClient
**위치**: `picko/llm_client.py`

**역할**:
- 다중 LLM 프로바이더 통합 클라이언트
- 일관된 인터페이스 제공

**지원 프로바이더**:
- Ollama (로컬)
- OpenAI
- Anthropic
- OpenRouter
- Relay

**주요 메소드**:
```python
class LLMClient:
    async def generate(self, prompt: str, **kwargs) -> str:
        # LLM 호출

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator:
        # 스트리밍 LLM 호출

    async def generate_with_fallback(self, prompt: str, **kwargs) -> str:
        # 폴백 포함 LLM 호출
```

**특징**:
- 자동 폴백 메커니즘
- 타임아웃 처리
- 재시로 로직

**의존성**:
- 각 프로바이더별 SDK
- `Config`: 설정 로드

---

#### 2.5.2 EmbeddingManager
**위치**: `picko/embedding.py`

**역할**:
- 텍스트 임베딩 생성 및 관리
- 유사도 검색

**지원 임베딩**:
- 로컬: sentence-transformers, Ollama
- 클라우드: OpenAI

**주요 메소드**:
```python
class EmbeddingManager:
    async def embed_text(self, text: str) -> np.ndarray:
        # 텍스트 임베딩

    async def find_similar(
        self,
        embedding: np.ndarray,
        top_k: int = 5,
        threshold: float = 0.8
    ) -> List[SimilarItem]:
        # 유사한 문서 검색

    def save_embedding(self, id: str, embedding: np.ndarray) -> None:
        # 임베딩 저장

    def load_embedding(self, id: str) -> Optional[np.ndarray]:
        # 임베딩 로드
```

**의존성**:
- `sentence-transformers`: 로컬 임베딩
- `numpy`: 벡터 연산
- `Config`: 임베딩 설정

---

#### 2.5.3 VaultIO
**위치**: `picko/vault_io.py`

**역할**:
- Obsidian Vault 마크다운 I/O
- 프론트매터 관리

**주요 메소드**:
```python
class VaultIO:
    def read_note(self, path: str) -> VaultNote:
        # 노트 읽기

    def write_note(self, path: str, content: str, frontmatter: dict = None) -> None:
        # 노트 쓰기

    def update_frontmatter(self, path: str, updates: dict) -> None:
        # 프론트매터 업데이트

    def list_notes(self, path: str, pattern: str = None) -> List[str]:
        # 노트 목록 조회
```

**VaultNote 구조**:
```python
@dataclass
class VaultNote:
    frontmatter: dict
    content: str
    path: str
```

**의존성**:
- `pathlib`: 파일 시스템 접근
- `yaml`: YAML 파싱
- `Config`: Vault 경로 설정

---

### 2.6 디스커버리 컴포넌트

#### 2.6.1 DiscoveryOrchestrator
**위치**: `picko/discovery/orchestrator.py`

**역할**:
- 새 소스 발견 및 등록 조율
- 여러 어댑터 병렬 실행

**주요 메소드**:
```python
class DiscoveryOrchestrator:
    async def discover(
        self,
        account: str,
        keywords: List[str],
        platforms: List[str]
    ) -> List[SourceCandidate]:
        # 소스 발견 실행

    async def register_candidate(self, candidate: SourceCandidate) -> bool:
        # 소스 후보 등록
```

**의존성**:
- `DiscoveryAdapters`: 플랫폼별 어댑터
- `HumanConfirmationGate`: 수동 승인
- `SourceManager`: 소스 관리

---

#### 2.6.2 DiscoveryAdapters
**위치**: `picko/discovery/adapters/`

**지원 어댑터**:
- RedditAdapter
- MastodonAdapter
- ThreadsAdapter (placeholder)

**공통 인터페이스**:
```python
class BaseDiscoveryCollector(ABC):
    @abstractmethod
    async def discover(self, keywords: List[str]) -> List[SourceCandidate]:
        pass
```

**의존성**:
- 각 플랫폼별 API SDK
- `RateLimiter`: API 레이트 리밋
- `SourceCandidate`: 표준화된 데이터 구조

---

## 3. 컴포넌트 간 의존성

### 3.1 의존성 다이어그램

```
WorkflowEngine
    ↓ (의존)
ActionRegistry
    ↓ (사용)
DefaultActions
    ↓ (호출)
Collector/Generator/Quality Systems
    ↓ (사용)
Core Services (LLM, Embedding, VaultIO)
```

### 3.2 의존성 상세

#### 3.2.1 오케스트레이션 계층
- `WorkflowEngine` → `ActionRegistry` → `DefaultActions`
- 모든 액션은 핵심 서비스에 의존

#### 3.2.2 서비스 계층
- `Collector` → `EmbeddingManager` (중복 제거)
- `Generator` → `LLMClient` (콘텐츠 생성)
- `Quality` → `LLMClient` (검증)

#### 3.2.3 저장소 계층
- 모든 컴포넌트 → `VaultIO` (데이터 저장)
- `EmbeddingManager` → 로컬 캐시 (임베딩 저장)

### 3.3 주의사항

1. **순환 의존성 방지**
   - 컴포넌트 간 직접적인 순환 참조 금지
   - 이벤트 기반 통신으로 간접적 통신

2. **의존성 주입**
   - 생성자 주입을 통한 명시적 의존성 선언
   - 의존성 주입 컨테이너 활용 권장

3. **인터페이스 분리**
   - 컴포넌트별 최소한의 인터페이스 노출
   - 내부 구현은 캡슐화

---

## 4. 인터페이스 명세

### 4.1 Collector 인터페이스

```python
class ICollector(ABC):
    """컬렉터 기본 인터페이스"""

    @abstractmethod
    def collect(self, account_id: str) -> list[CollectedItem]:
        """계정 단위 콘텐츠 수집"""
        pass

    @abstractmethod
    def name(self) -> str:
        """컬렉터 식별자"""
        pass
```

### 4.2 Validator 인터페이스

```python
class IValidator(ABC):
    """검증자 기본 인터페이스"""

    @abstractmethod
    async def validate(
        self,
        item: CollectedItem,
        context: dict = None
    ) -> ValidationResult:
        """아이템 검증"""
        pass
```

### 4.3 Generator 인터페이스

```python
class IGenerator(ABC):
    """생성자 기본 인터페이스"""

    @abstractmethod
    async def generate(self, item_id: str, type: str) -> None:
        """콘텐츠 생성"""
        pass
```

### 4.4 Publisher 인터페이스

```python
class IPublisher(ABC):
    """게시자 기본 인터페이스"""

    @abstractmethod
    async def publish(self, item_id: str, platform: str) -> PublishResult:
        """콘텐츠 게시"""
        pass
```

---

## 5. 확장 가이드

### 5.1 새로운 컬렉터 추가

1. `BaseCollector` 상속
2. `collect(account_id)` 및 `name()` 구현
3. `SourceMeta` 타입에 따라 소스 등록
4. `ActionRegistry`에 액션 등록

### 5.2 새로운 검증기 추가

1. `IValidator` 구현
2. 특정 검증 로직 작성
3. `QualityGraph`에 통합

### 5.3 새로운 생성기 추가

1. `IGenerator` 구현
2. 템플릿 작성
3. `ActionRegistry`에 등록

### 5.4 새로운 플랫폼 어댑터 추가

1. `BaseDiscoveryCollector` 상속
2. 플랫폼 API 연동
3. `SourceCandidate` 변환 로직 구현
4. `DiscoveryOrchestrator`에 등록

---

*이 문서는 Picko 시스템의 모든 컴포넌트를 상세히 설명하며, 개발자가 컴포넌트를 이해하고 확장할 수 있도록 돕습니다.*
