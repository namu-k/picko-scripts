# 005 오케스트레이션 레이어 — 설계 스펙

## 1. 배경

현재 Picko 파이프라인은 독립 스크립트의 순차 실행에 의존한다:

```
daily_collector.py → (수동 큐레이션) → generate_content.py → render_media.py
```

각 단계 간 연결이 암묵적이고, 조건 분기/배치 처리/승인 대기 같은 흐름 제어가 없다.
이 스펙은 기존 스크립트를 래핑하는 오케스트레이션 레이어를 정의한다.

---

## 2. 목표

| 목표 | 설명 |
|------|------|
| Vault 상태 기반 조건 | frontmatter 필드를 워크플로우 조건으로 사용 |
| 배치 처리 | 대량 아이템을 크기/딜레이 제어하며 처리 |
| 승인 흐름 | 사용자 승인을 워크플로우에 선언적으로 포함 |
| 중복 검사 액션 | 임베딩 기반 중복 검사를 step으로 사용 |
| 점진적 마이그레이션 | 기존 스크립트 변경 최소화 |

### 비목표

- 범용 워크플로우 엔진 (Airflow, Temporal 수준)
- 실시간 이벤트 스트리밍
- 분산 실행

---

## 3. 아키텍처

### 3.1 전체 구조

```
config/
└── workflows/
    └── daily_pipeline.yml        # 워크플로우 정의

picko/
├── orchestrator/
│   ├── __init__.py
│   ├── engine.py                 # 워크플로우 실행 엔진
│   ├── vault_adapter.py          # Vault 상태 쿼리 어댑터
│   ├── actions.py                # 액션 레지스트리 (기존 스크립트 래핑)
│   └── batch.py                  # 배치 처리 유틸리티
│
├── vault_io.py                   # 기존 (변경 없음)
├── embedding.py                  # 기존 (변경 없음)
└── ...

scripts/
├── run_workflow.py               # 워크플로우 실행 CLI
├── daily_collector.py            # 기존 (액션으로도 호출 가능)
├── generate_content.py           # 기존 (액션으로도 호출 가능)
└── ...
```

### 3.2 데이터 흐름

```
워크플로우 YAML 로드
       ↓
  Step 순회 시작
       ↓
  ┌─────────────────────┐
  │ condition 평가       │──(false)──→ skip, 다음 step
  │ (vault_adapter 사용) │
  └─────────┬───────────┘
            │(true)
            ↓
  ┌─────────────────────┐
  │ action 실행          │
  │ (기존 스크립트 래핑)  │
  │ batch 설정 적용      │
  └─────────┬───────────┘
            │
            ↓
  outputs 저장 → 다음 step에서 참조 가능
       ↓
  다음 step으로
```

---

## 4. 워크플로우 DSL

### 4.1 기본 구조

```yaml
# config/workflows/daily_pipeline.yml

name: daily_pipeline
description: 일일 콘텐츠 수집 → 생성 파이프라인
trigger: manual  # manual | cron

steps:
  - name: collect
    action: collector.run
    args:
      account: socialbuilders

  - name: generate_auto_ready
    action: generator.run
    args:
      account: socialbuilders
      type: longform
    condition: ${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}
```

### 4.2 Vault 상태 조건

`${{ vault.xxx }}` 표현식으로 Vault frontmatter를 쿼리한다.

#### 지원 함수

| 함수 | 설명 | 예시 |
|------|------|------|
| `vault.count(path, filter)` | 조건에 맞는 노트 수 | `vault.count('Inbox/Inputs', 'writing_status=auto_ready')` |
| `vault.list(path, filter)` | 조건에 맞는 노트 경로 목록 | `vault.list('Content/Longform', 'derivative_status=approved')` |
| `vault.field(path, field)` | 특정 노트의 필드 값 | `vault.field(steps.prev.output_path, 'writing_status')` |

#### 필터 문법

```
field=value              # 등호 비교
field!=value             # 불등호
field>value              # 숫자 비교 (>, <, >=, <=)
filter1,filter2          # AND 조건
```

**설계 결정:** 복잡한 쿼리 언어 대신 단순한 `field=value` 필터를 사용한다.
복잡한 조건이 필요하면 Python 액션에서 처리한다.

### 4.3 배치 처리

```yaml
steps:
  - name: generate_batch
    action: generator.run
    args:
      account: socialbuilders
    batch:
      source: ${{ vault.list('Inbox/Inputs', 'writing_status=auto_ready') }}
      size: 5          # 한 번에 처리할 아이템 수
      delay: 10s       # 배치 간 대기 (rate limit 용도, 선택)
```

- `source`: 배치 대상 아이템 목록 (vault.list 결과)
- `size`: 배치 크기
- `delay`: 배치 간 대기 시간 (LLM provider rate limit 대응용, 선택적)
- 각 배치의 결과는 `steps.<name>.outputs`에 누적

**참고:** `delay`는 `llm_client.py`의 provider별 rate limit과 별개이다.
`delay`는 워크플로우 레벨의 조절이고, provider rate limit은 호출 레벨의 조절이다.

### 4.4 승인 대기 (2-pass 패턴)

단일 프로세스가 대기하는 대신, **2-pass 실행**으로 승인 흐름을 구현한다.

```yaml
# Pass 1: 수집 + longform 생성
name: pipeline_pass1
steps:
  - name: collect
    action: collector.run
    args: { account: socialbuilders }

  - name: generate_longform
    action: generator.run
    args: { account: socialbuilders, type: longform }
    condition: ${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}

# --- 사용자가 Vault에서 derivative_status: approved 설정 ---

# Pass 2: 승인된 항목으로 packs 생성
name: pipeline_pass2
steps:
  - name: generate_packs
    action: generator.run
    args: { account: socialbuilders, type: packs }
    condition: ${{ vault.count('Content/Longform', 'derivative_status=approved') > 0 }}
    batch:
      source: ${{ vault.list('Content/Longform', 'derivative_status=approved') }}
      size: 5
```

**설계 결정:** `vault.wait_status` + `timeout: 24h` 방식 대신 2-pass 패턴을 채택한다.

이유:
- 현재 실행 모델이 cron/수동 기반이므로 long-running 프로세스가 불필요
- 실행 간 상태 저장 로직이 불필요 (Vault 자체가 상태)
- 디버깅이 단순 (각 pass를 독립적으로 실행/테스트 가능)

### 4.5 임베딩 액션

```yaml
steps:
  - name: check_duplicate
    action: embedding.check_duplicate
    args:
      source: ${{ steps.collect.outputs.items }}
      threshold: 0.9
    outputs:
      duplicates: result.duplicates
      unique: result.unique

  - name: process_unique
    action: generator.run
    args:
      items: ${{ steps.check_duplicate.outputs.unique }}
```

- `threshold`는 코사인 유사도 기준이며, 기존 `scoring.py`의 novelty 점수와 정합성을 맞춤
- 기존 `embedding.py`의 `get_embedding()` + `cosine_similarity()`를 래핑

---

## 5. 핵심 컴포넌트 설계

### 5.1 VaultAdapter

Vault frontmatter를 쿼리하는 어댑터. 기존 `vault_io.py`의 `VaultIO` 위에 집계 기능을 추가한다.

```python
# picko/orchestrator/vault_adapter.py

class VaultAdapter:
    """Vault frontmatter 쿼리 어댑터"""

    def __init__(self, vault_io: VaultIO):
        self.vault_io = vault_io

    def count(self, path: str, filter_expr: str) -> int:
        """조건에 맞는 노트 수 반환"""
        return len(self.list(path, filter_expr))

    def list(self, path: str, filter_expr: str) -> list[Path]:
        """조건에 맞는 노트 경로 목록 반환"""
        # 1. path 하위의 모든 .md 파일 스캔
        # 2. 각 파일의 frontmatter 파싱
        # 3. filter_expr 조건 평가
        # 4. 매칭된 파일 경로 반환
        ...

    def field(self, note_path: str, field_name: str) -> Any:
        """특정 노트의 frontmatter 필드 값 반환"""
        ...
```

**성능 고려:** 파일이 많아질 경우를 대비하여:
- 1차 구현: 전체 스캔 (단순, 수백 파일 수준에서 충분)
- 향후: 인메모리 캐시 또는 manifest 파일로 최적화

### 5.2 ActionRegistry

기존 스크립트를 액션으로 래핑하는 레지스트리.

```python
# picko/orchestrator/actions.py

class ActionRegistry:
    """액션 이름 → 실행 함수 매핑"""

    def __init__(self):
        self._actions: dict[str, Callable] = {}

    def register(self, name: str, fn: Callable):
        self._actions[name] = fn

    def execute(self, name: str, args: dict) -> ActionResult:
        fn = self._actions[name]
        return fn(**args)


# 기본 액션 등록
def register_default_actions(registry: ActionRegistry):
    registry.register("collector.run", _run_collector)
    registry.register("generator.run", _run_generator)
    registry.register("embedding.check_duplicate", _check_duplicate)


def _run_collector(**kwargs) -> ActionResult:
    """scripts/daily_collector.py의 DailyCollector를 래핑"""
    ...

def _run_generator(**kwargs) -> ActionResult:
    """scripts/generate_content.py의 ContentGenerator를 래핑"""
    ...

def _check_duplicate(**kwargs) -> ActionResult:
    """picko/embedding.py 기반 중복 검사"""
    ...
```

### 5.3 WorkflowEngine

```python
# picko/orchestrator/engine.py

class WorkflowEngine:
    """워크플로우 YAML을 로드하고 실행"""

    def __init__(self, vault_adapter: VaultAdapter, action_registry: ActionRegistry):
        self.vault = vault_adapter
        self.actions = action_registry
        self.step_outputs: dict[str, Any] = {}

    def run(self, workflow_path: Path) -> WorkflowResult:
        workflow = self._load(workflow_path)
        results = []

        for step in workflow["steps"]:
            # 1. condition 평가
            if not self._evaluate_condition(step.get("condition")):
                results.append(StepResult(step["name"], skipped=True))
                continue

            # 2. batch 처리
            if "batch" in step:
                result = self._run_batched(step)
            else:
                result = self._run_step(step)

            # 3. outputs 저장
            self.step_outputs[step["name"]] = result.outputs
            results.append(result)

        return WorkflowResult(results)
```

### 5.4 BatchProcessor

```python
# picko/orchestrator/batch.py

class BatchProcessor:
    """배치 단위로 아이템을 처리"""

    def run(
        self,
        items: list,
        action_fn: Callable,
        size: int = 10,
        delay_seconds: float = 0,
    ) -> list[ActionResult]:
        results = []
        for i in range(0, len(items), size):
            batch = items[i : i + size]
            result = action_fn(batch)
            results.append(result)

            if delay_seconds > 0 and i + size < len(items):
                time.sleep(delay_seconds)

        return results
```

---

## 6. 표현식 평가

`${{ }}` 내부의 표현식을 평가하는 간단한 인터프리터.

### 6.1 지원 범위

```
${{ vault.count(...) }}          # VaultAdapter 메서드 호출
${{ vault.list(...) }}
${{ vault.field(...) }}
${{ steps.<name>.outputs.<key> }} # 이전 step 결과 참조
${{ args.<key> }}                 # 워크플로우 실행 인자
```

### 6.2 비지원 (의도적 제외)

- 임의 Python 코드 실행
- 복잡한 논리 연산 (`AND`, `OR` 체이닝)
- 중첩 표현식

복잡한 로직이 필요하면 Python 액션으로 작성한다.

### 6.3 구현 방식

`eval()` 대신 정규식 기반 파서 + 허용된 함수만 호출하는 안전한 평가기를 사용한다.

```python
# 표현식 예시와 파싱 결과
"${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}"
→ call: vault.count('Inbox/Inputs', 'writing_status=auto_ready')
→ compare: result > 0
→ return: bool
```

---

## 7. 구현 단계

전체 DSL을 설계하되, 구현은 단계적으로 진행한다.

### Phase 1: 핵심 (1차 구현 범위)

| 컴포넌트 | 설명 |
|----------|------|
| `VaultAdapter` | `count()`, `list()`, `field()` + 필터 파싱 |
| `ActionRegistry` | `collector.run`, `generator.run` 래핑 |
| `WorkflowEngine` | YAML 로드, step 순회, condition 평가 |
| `run_workflow.py` | CLI: `python -m scripts.run_workflow --workflow daily_pipeline` |

### Phase 2: 확장

| 컴포넌트 | 설명 |
|----------|------|
| `BatchProcessor` | 배치 크기/딜레이 처리 |
| `embedding.check_duplicate` 액션 | 중복 검사 액션 |
| step outputs 참조 | `${{ steps.<name>.outputs }}` |

### Phase 3: 고도화

| 컴포넌트 | 설명 |
|----------|------|
| VaultAdapter 캐싱 | 대량 파일 성능 최적화 |
| 에러 핸들링 | step 실패 시 continue/abort 정책 |
| 로깅/리포트 | 워크플로우 실행 결과 리포트 |

---

## 8. 워크플로우 예시: 전체 일일 파이프라인

```yaml
# config/workflows/daily_pipeline.yml

name: daily_pipeline
description: 일일 콘텐츠 수집 → 중복 제거 → 생성

steps:
  # 1. 수집
  - name: collect
    action: collector.run
    args:
      account: socialbuilders

  # 2. 중복 제거
  - name: dedup
    action: embedding.check_duplicate
    args:
      source: ${{ steps.collect.outputs.items }}
      threshold: 0.9

  # 3. auto_ready 상태인 항목 longform 생성
  - name: generate_longform
    action: generator.run
    args:
      account: socialbuilders
      type: longform
    condition: ${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}
    batch:
      source: ${{ vault.list('Inbox/Inputs', 'writing_status=auto_ready') }}
      size: 5
```

```yaml
# config/workflows/approved_packs.yml

name: approved_packs
description: 승인된 longform → packs 생성

steps:
  - name: generate_packs
    action: generator.run
    args:
      account: socialbuilders
      type: packs
    condition: ${{ vault.count('Content/Longform', 'derivative_status=approved') > 0 }}
    batch:
      source: ${{ vault.list('Content/Longform', 'derivative_status=approved') }}
      size: 5
```

---

## 9. 기존 코드와의 관계

| 기존 모듈 | 변경 사항 |
|-----------|----------|
| `vault_io.py` | 변경 없음. VaultAdapter가 래핑하여 사용 |
| `embedding.py` | 변경 없음. 액션에서 임포트하여 사용 |
| `scoring.py` | 변경 없음. threshold 값과 정합성만 확인 |
| `daily_collector.py` | 변경 없음. 기존 CLI 그대로 유지 + 액션으로도 호출 가능 |
| `generate_content.py` | 변경 없음. 액션으로도 호출 가능 |
| `llm_client.py` | 변경 없음. batch delay와 provider rate limit은 별개 계층 |

**원칙:** 기존 스크립트는 독립 실행을 계속 지원한다. 오케스트레이터는 추가 계층이다.

---

## 10. 리스크 및 완화

| 리스크 | 완화 |
|--------|------|
| VaultAdapter 전체 스캔 성능 | Phase 1에서 수백 파일 수준이면 충분. Phase 3에서 캐싱 추가 |
| 표현식 파서 복잡도 증가 | 의도적으로 단순하게 유지. 복잡한 로직은 Python 액션으로 |
| 기존 스크립트 인터페이스 변경 | 액션은 래퍼이므로 기존 인터페이스 보존 |
| YAML DSL의 한계 | 범용 엔진이 아닌 Picko 전용으로 범위 제한 |

---

*작성일: 2026-02-25*
*브랜치: spec/005-orchestration-layer*
*상태: 설계 확정 대기*
