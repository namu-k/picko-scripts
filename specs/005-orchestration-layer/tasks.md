# 005 Orchestration Layer - 구현 태스크

## 의존성 맵

```
┌────────────┬──────────────────┐
│    Task    │       의존       │
├────────────┼──────────────────┤
│ 2a, 2b     │ 없음 (병렬 가능) │
├────────────┼──────────────────┤
│ 2c         │ 2a               │
├────────────┼──────────────────┤
│ 2d         │ 2b               │
├────────────┼──────────────────┤
│ 2e         │ 2c, 2d           │
└────────────┴──────────────────┘
```

---

## Phase 1: 핵심 (✅ 완료)

| 컴포넌트 | 상태 | 파일 |
|----------|------|------|
| `VaultAdapter` | ✅ | `picko/orchestrator/vault_adapter.py` |
| `ActionRegistry` | ✅ | `picko/orchestrator/actions.py` |
| `WorkflowEngine` | ✅ | `picko/orchestrator/engine.py` |
| `ExprEvaluator` | ✅ | `picko/orchestrator/expr.py` |
| `run_workflow.py` | ✅ | `scripts/run_workflow.py` |
| 기본 액션 | ✅ | `picko/orchestrator/default_actions.py` |

---

## Phase 2: 확장 (현재)

### Task 2a: BatchProcessor 구현
**파일:** `picko/orchestrator/batch.py`
**의존성:** 없음

**단계:**
1. `BatchProcessor` 클래스 구현:
   - `__init__(size, delay_seconds)`
   - `run(items, action_fn)` - 배치 단위 처리
2. 배치 분할 로직 (size 기준)
3. 배치 간 대기 (delay_seconds)
4. 결과 누적 반환

**검증:**
```bash
python -c "
from picko.orchestrator.batch import BatchProcessor
bp = BatchProcessor(size=3, delay_seconds=0.1)
items = list(range(10))
results = bp.run(items, lambda x: {'sum': sum(x)})
print(f'Batches: {len(results)}')
"
```

---

### Task 2b: embedding.check_duplicate 액션
**파일:** `picko/orchestrator/default_actions.py`
**의존성:** 없음

**단계:**
1. `_check_duplicate()` 함수 구현:
   - `picko/embedding.py`의 `get_embedding()` + `cosine_similarity()` 활용
   - 임계값 기반 중복 판정
2. `register_default_actions()`에 등록
3. 결과에 `duplicates`, `unique` 포함

**검증:**
```bash
python -c "
from picko.orchestrator.actions import ActionRegistry
from picko.orchestrator.default_actions import register_default_actions
registry = ActionRegistry()
register_default_actions(registry)
print('embedding.check_duplicate' in registry._actions)
"
```

---

### Task 2c: WorkflowEngine 배치 처리
**파일:** `picko/orchestrator/engine.py`
**의존성:** Task 2a

**단계:**
1. `_execute_step()` 수정:
   - `batch` 섹션 감지
   - `BatchProcessor` 사용하여 처리
   - 결과 누적
2. `batch` 설정 파싱:
   - `source`: 배치 대상 목록
   - `size`: 배치 크기
   - `delay`: 배치 간 대기 시간

**검증:**
```bash
python -m scripts.run_workflow --workflow test_batch --dry-run
```

---

### Task 2d: 워크플로우에 batch 적용
**파일:** `config/workflows/daily_pipeline.yml`
**의존성:** Task 2b

**단계:**
1. `generate_longform` step에 batch 추가:
   ```yaml
   batch:
     source: ${{ vault.list('Inbox/Inputs', 'writing_status=auto_ready') }}
     size: 5
     delay: 10s
   ```
2. `dedup` step에 `embedding.check_duplicate` 액션 사용

**검증:**
```bash
python -m scripts.run_workflow --workflow daily_pipeline --dry-run
```

---

### Task 2e: 단위 테스트 작성
**파일:** `tests/test_orchestrator_batch.py`
**의존성:** Task 2c, 2d

**단계:**
1. `BatchProcessor` 테스트:
   - 배치 분할 테스트
   - delay 동작 테스트
   - 결과 누적 테스트
2. `embedding.check_duplicate` 액션 테스트:
   - 중복 감지 테스트
   - 임계값 테스트
3. WorkflowEngine batch 테스트:
   - YAML 파싱 테스트
   - 배치 실행 테스트

**검증:**
```bash
pytest tests/test_orchestrator_batch.py -v
```

---

## Phase 3: 고도화 (이후)

| 컴포넌트 | 설명 |
|----------|------|
| VaultAdapter 캐싱 | 대량 파일 성능 최적화 |
| 에러 핸들링 | step 실패 시 continue/abort 정책 |
| 로깅/리포트 | 워크플로우 실행 결과 리포트 |

---

## 체크리스트

### Phase 1 완료 후
- [x] VaultAdapter count/list/field 동작 확인
- [x] WorkflowEngine YAML 로드 확인
- [x] ExprEvaluator 표현식 평가 확인
- [x] run_workflow.py CLI 동작 확인

### Phase 2 완료 후
- [x] BatchProcessor 단위 테스트 통과
- [x] embedding.check_duplicate 액션 등록 확인
- [ ] daily_pipeline.yml 배치 처리 동작
- [x] 전체 테스트 통과
---

*작성일: 2026-02-26*
*브랜치: 005-orchestration-layer-phase2*
