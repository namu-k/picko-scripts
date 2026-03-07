# 014 Video Multi-Agent — Core Tasks

기준 문서:
- 스펙: `specs/014-video-multi-agent/spec.md` (v4, 2026-03-07)
- 구현 계획: `specs/014-video-multi-agent/plan.md` (v2)

작업 범위(현재 문서):
- 포함: planning/recipe selection/render QA/publish gate 코어
- 제외: KPI/캠페인/실험/마케팅 대시보드/marketing fit 활성화/Product UI Insert Planner 활성화

---

## 충돌 기록 (Spec vs Plan)

### C-01 Provider 선택 규칙 충돌
- 충돌 지점:
  - `spec.md`: provider 선택은 `execution_mode`와 `requested_services`의 **교집합 기준**으로 결정
  - `plan.md` 예시 코드: 교집합이 비면 mode-only provider로 fallback
- 현재 처리 방침:
  - 임의로 숨기지 않고 본 문서에 명시 기록
  - 구현 task에서는 **교집합 우선 원칙을 강제**하고, 교집합이 비는 경우는 자동 fallback 대신 명시적 review 이슈/blocked 경로로 다룸
- 영향 범위:
  - `picko/video/agents/providers.py`
  - `picko/video/agents/nodes/stitch_planner.py`
  - `picko/video/agents/nodes/orchestrator.py`
  - 관련 테스트

---

## Task 1. 상태 스키마 및 타입 안정성

목적
- shot_id/segment_id 기반 상태 모델을 고정하고, 코어/마케팅 경계를 타입 수준에서 분리한다.

수정/생성할 파일
- 생성: `picko/video/agents/state.py`
- 생성: `picko/video/agents/schemas.py`
- 생성: `picko/video/agents/providers.py`
- 생성: `picko/video/agents/__init__.py`
- 생성: `tests/video/agents/test_state.py`
- 생성: `tests/video/agents/test_schemas.py`
- 생성: `tests/video/agents/test_providers.py`

구현 내용
- `VideoAgentState`를 shot_id 중심 Dict 구조로 정의 (`shots_by_id`, `production_by_shot_id`, `copy_by_shot_id`, `prompts_by_shot_id`, `audio_by_shot_id`).
- `shot_order`와 `StitchSegment.segment_id`를 통해 순서/세그먼트 정합성을 보존.
- `TerminalStatus` 도입 (`auto_approved`, `needs_human_review`, `revise_required`, `blocked`, `max_iterations_reached`; 필요 시 내부 `pending`).
- `CreativeBrief`, `ShotDraft`, `RenderRecipe`, `ProductionSpec`, `ReviewIssue` 등 core schema 정의.
- reserved 필드(`campaign_context`, `performance_hints`, `experiment_vars`) 및 reserved 슬롯(`platform_variants`, product/UI insert 관련 슬롯)을 유지하되 분기 핵심 조건으로 사용하지 않음.
- `ProviderCapability`/`PROVIDER_CAPABILITIES` 및 `execution_mode + requested_services` 교집합 필터 함수 제공.

입력/출력 또는 상태 변화
- 입력: `creative_brief` dict + account context
- 출력: 타입 안정적인 `VideoAgentState` 초기 상태
- 상태 변화: planning/review/publish에서 참조 가능한 공통 계약 수립

테스트 항목
- TypedDict/dataclass 기본 생성 및 직렬화/역직렬화.
- `shot_order`와 shot-level dict key set 일치 불변식 검증.
- provider 교집합 필터 결과 검증(교집합 유/무 케이스 분리).
- reserved 필드가 누락 없이 전달되는지 검증.

완료 기준
- 상태/스키마/프로바이더 테스트 통과.
- 배열 인덱스 기반 의존이 코어 경로에서 제거.

---

## Task 2. Graph/Node/Orchestration 코어 구축

목적
- planning graph를 story -> stitch -> (copy/prompt/audio fan-out) -> plan review -> orchestrator 구조로 구성하고 revision loop를 제어한다.

수정/생성할 파일
- 생성: `picko/video/agents/graph.py`
- 생성: `picko/video/agents/nodes/base.py`
- 생성: `picko/video/agents/nodes/story_writer.py`
- 생성: `picko/video/agents/nodes/stitch_planner.py`
- 생성: `picko/video/agents/nodes/copywriter.py`
- 생성: `picko/video/agents/nodes/prompt_engineer.py`
- 생성: `picko/video/agents/nodes/audio_director.py`
- 생성: `picko/video/agents/nodes/plan_reviewer.py`
- 생성: `picko/video/agents/nodes/orchestrator.py`
- 생성: `picko/video/agents/nodes/__init__.py`
- 생성: `tests/video/agents/test_graph.py`
- 생성: `tests/video/agents/test_revision_loop.py`

구현 내용
- LangGraph `StateGraph`에 3-way fan-out/fan-in 구성.
- 병렬 노드 합산 필드에 reducer 적용 (`llm_calls_used`, `tokens_used_estimate`, `cost_usd_estimate`).
- `INVALIDATION_CASCADE` 기반 필드 초기화 전략 구현.
- `ReviewIssue.code` 기반 routing으로 revision target agent 결정.
- `safe_node` 래퍼로 노드 실패를 구조화 이슈로 전환.

입력/출력 또는 상태 변화
- 입력: 초기 `VideoAgentState`
- 출력: planning 완료 상태(리뷰 결과 + terminal status)
- 상태 변화: `iteration_count`, `revision_issues`, `terminal_status` 갱신

테스트 항목
- fan-out/fan-in 경로에서 상태 merge 검증.
- revision issue 코드별 라우팅 결과 검증.
- max iteration/budget 초과/auto approve/human review 분기 검증.

완료 기준
- graph compile 성공.
- 핵심 분기 테스트 통과 및 무한 루프 없음.

---

## Task 3. Provider/Service Selection 및 Recipe 기반 Production

목적
- shot_id 단위로 production_mode와 render_recipe를 분리 결정하고 provider 제약을 반영한다.

수정/생성할 파일
- 생성: `picko/video/agents/tools/stitch.py`
- 수정: `picko/video/agents/nodes/stitch_planner.py`
- 수정: `picko/video/agents/providers.py`
- 생성: `tests/video/agents/test_tools_stitch.py`

구현 내용
- 1단계: `select_production_mode(shot)` (서비스 독립).
- 2단계: `assign_render_recipe(shot_id, mode, providers, execution_mode)`.
- provider 결정은 `execution_mode`와 `requested_services` 교집합 기준.
- `audio_strategy`/`continuity_ref_source`를 recipe에 포함.
- 교집합 공백 시 silent fallback이 아닌 명시적 이슈(`production.recipe_mismatch`) 또는 blocked/review 경로 처리.

입력/출력 또는 상태 변화
- 입력: `shots_by_id`, `shot_order`, `services`, `execution_mode`
- 출력: `production_by_shot_id`, `continuity_refs`, `stitch_plan`, `asset_manifest`

테스트 항목
- shot 유형별 mode 선택 테스트.
- provider 교집합 필터 + recipe 할당 테스트.
- 교집합 없음/지원 duration 불일치 등 실패 경로 테스트.

완료 기준
- 모든 shot에 `ProductionSpec`이 생성되고 shot_id로 조회 가능.
- 선택 로직이 배열 인덱스에 의존하지 않음.

---

## Task 4. Render Brief 생성

목적
- manual_assisted 렌더를 위한 shot_id 기반 `render_briefs`를 생성한다.

수정/생성할 파일
- 생성: `picko/video/agents/runtime.py` (또는 `picko/video/agents/tools/render_brief.py`)
- 수정: `picko/video/agents/graph.py` (완료 시점 출력 경로)
- 생성: `tests/video/agents/test_render_brief.py`

구현 내용
- `shots_by_id`/`production_by_shot_id`/`prompts_by_shot_id`/`audio_by_shot_id`/`copy_by_shot_id`를 합쳐 render brief 생성.
- shot_id를 primary key로 유지.
- 출력 슬롯 `render_briefs` 유지, `platform_variants`는 reserved로 `[]` 유지.

입력/출력 또는 상태 변화
- 입력: planning 완료 state
- 출력: 서비스별 render brief 목록
- 상태 변화: `render_briefs` 생성, publish 전 단계 산출물 확보

테스트 항목
- 필수 키(`shot_id`, `production_mode`, prompt/audio/caption) 존재 검증.
- shot_order 순서 보존 검증.

완료 기준
- AUTO_APPROVED 경로에서 render briefs를 안정적으로 반환.

---

## Task 5. Review/QA/Publish Gate 분리 구현

목적
- Reviewer 역할을 Plan Reviewer / Artifact Reviewer / Publish Reviewer로 분리하고, QA 순서를 deterministic -> VLM -> human gate로 강제한다.

수정/생성할 파일
- 생성: `picko/video/agents/tools/review.py`
- 생성: `picko/video/agents/tools/artifact_qa.py`
- 생성: `picko/video/agents/nodes/artifact_reviewer.py`
- 생성: `picko/video/agents/nodes/publish_reviewer.py`
- 수정: `picko/video/agents/nodes/plan_reviewer.py`
- 생성: `tests/video/agents/test_tools_review.py`
- 생성: `tests/video/agents/test_artifact_qa.py`
- 생성: `tests/video/agents/test_publish_reviewer.py`

구현 내용
- Plan Reviewer: 구조/production/audio/brand 검수 + 구조화 이슈 코드 출력.
- `review_marketing_fit`는 reserved hook으로 no-op 유지(활성화 금지).
- Artifact Reviewer: deterministic checks 우선, 통과 시 VLM structural QA 수행, 이후 human gate 필요 여부 산출.
- deterministic QA 세부 항목: duration, aspect ratio, fps, file integrity, audio track presence, OCR/text presence, waveform/loudness 기본 검증.
- Publish Reviewer: 사람 결정(`approved`/`blocked`) 반영하여 `publish_status` 업데이트.

입력/출력 또는 상태 변화
- 입력: planning state + uploaded artifact(artifact review), human decision(publish review)
- 출력: `plan_review`, `artifact_review`, `publish_status`
- 상태 변화: QA 결과에 따라 auto_regen_suggestions/human_review_items 분기

테스트 항목
- deterministic 실패 시 VLM 스킵 검증.
- duration mismatch 시 deterministic fail 검증.
- corrupted file 시 deterministic fail 검증.
- fps mismatch 시 deterministic fail 검증.
- OCR/text missing 조건 검증.
- audio waveform/loudness 이상치 검증.
- VLM 이슈 분류(`auto_regen_ok` vs human review) 검증.
- publish_status 전이(`pending` -> `approved`/`blocked`) 검증.
- invalid human decision 입력 방어(구조화 에러 또는 blocked 처리) 검증.
- 이미 `approved`/`blocked` 상태에서 중복 전이 방지 검증.
- human gate 이전 publish decision 적용 시도 방어 검증.

완료 기준
- 3단 reviewer 역할이 코드/테스트에서 분리되어 확인 가능.
- Artifact QA 순서가 강제되고 우회 경로 없음.

---

## Task 5.5. Post-Render Runtime EntryPoints

목적
- external render 결과를 코어 QA/publish gate에 연결하는 실행 인터페이스를 구현한다.

수정/생성할 파일
- 생성/수정: `picko/video/agents/runtime.py`
- 수정: `picko/video/generator.py`
- 생성: `tests/video/agents/test_runtime.py`

구현 내용
- `review_rendered_artifact(plan: VideoPlan, uploaded_file: str) -> ArtifactReviewResult` 구현.
- `apply_publish_decision(plan: VideoPlan, human_decision: str) -> PublishReviewResult` 구현.
- manual_assisted flow에서 planning 결과와 artifact review / publish review 연결.
- uploaded artifact와 shot/segment/render brief 매핑 검증.

입력/출력 또는 상태 변화
- 입력: planning 완료 `VideoPlan`, `uploaded_file`, `human_decision`.
- 출력: `artifact_review`, `publish_status`.
- 상태 변화: planning 이후 post-render QA/publish gate를 별도 엔트리포인트로 호출 가능.

테스트 항목
- planning 결과로부터 artifact review 진입 가능 여부.
- `uploaded_file` 누락/불일치 시 구조화 이슈 반환.
- publish decision 적용 후 `publish_status` 반영.
- runtime entrypoint가 planning entrypoint와 독립 호출 가능함을 검증.

완료 기준
- planning 이후 post-render QA 및 publish gate가 별도 runtime entrypoint로 호출 가능.

---

## Task 6. VideoGenerator 통합 및 `_state_to_plan()`

목적
- 기존 generator와 멀티에이전트 코어를 연결하고 shot_id 기반 state를 `VideoPlan`으로 변환한다.

수정/생성할 파일
- 수정: `picko/video/generator.py`
- 수정: `picko/video_plan.py` (필요 시 production/render/publish 슬롯 확장)
- 수정: `picko/video/__init__.py`
- 생성: `tests/video/agents/test_integration.py`

구현 내용
- `_generate_with_agents()` 진입점 추가 및 legacy path 유지.
- `_state_to_plan()`에서 `shot_order`를 기준으로 `VideoShot` 매핑.
- `render_briefs`, `production_specs`, `audio_specs`, `publish_status`, `platform_variants` 슬롯 반영.
- reserved 필드 보존(핵심 분기 사용 금지) 확인.

입력/출력 또는 상태 변화
- 입력: generator 입력(account/services/platforms/intent + brief 확장 필드)
- 출력: 확장된 `VideoPlan`
- 상태 변화: legacy 단일 LLM 생성 경로와 multi-agent 경로 공존

테스트 항목
- multi-agent on/off 경로 테스트.
- `_state_to_plan()` shot_id 정확 매핑 테스트.
- render_briefs/publish_status/platform_variants 출력 슬롯 검증.

완료 기준
- 기존 테스트 회귀 없이 통합 테스트 통과.

---

## Task 7. 테스트 보강 및 검증 파이프라인

목적
- 코어가 planning -> QA -> publish gate까지 독립 동작함을 테스트로 증명한다.

수정/생성할 파일
- 생성/수정: `tests/video/agents/test_graph.py`
- 생성/수정: `tests/video/agents/test_revision_loop.py`
- 생성/수정: `tests/video/agents/test_render_brief.py`
- 생성/수정: `tests/video/agents/test_artifact_qa.py`
- 생성/수정: `tests/video/agents/test_integration.py`

구현 내용
- happy path: auto_approved -> render_briefs -> artifact pass -> publish approved.
- revise path: structured issue -> target routing -> cascade invalidation.
- blocked path: budget/execution/provider mismatch.
- deterministic QA fail 및 human gate 경로 검증.

입력/출력 또는 상태 변화
- 입력: representative creative briefs + mock provider capabilities + mock artifacts
- 출력: 상태 전이 로그 및 최종 terminal/publish 상태

테스트 항목
- 상태 불변식/분기/리뷰 순서/슬롯 보존 검증.
- core 범위 외 기능이 활성화되지 않았는지 확인.

완료 기준
- `tests/video/agents/` 스위트 통과.
- 실패 시 어떤 계약이 깨졌는지 추적 가능한 테스트 메시지 확보.

---

## Task 8. Reserved Field/Extension Point 정리

목적
- 향후 마케팅 레이어 연결을 위해 reserved contract를 유지하되, 현재 코어 분기에서 비활성 상태를 명확히 고정한다.

수정/생성할 파일
- 수정: `picko/video/agents/state.py`
- 수정: `picko/video/agents/nodes/plan_reviewer.py`
- 수정: `picko/video/generator.py`
- 생성: `tests/video/agents/test_reserved_fields.py`

구현 내용
- reserved 입력/상태/출력 필드 전달 경로 유지.
- `review_marketing_fit` no-op 유지 및 실행 그래프 비연결.
- `platform_variants` 슬롯 유지(초기 `[]`).
- Product/UI Insert Planner 관련 슬롯(`ui_insert_shot_ids`, `product_proof_required`, `proof_overlay_copy`, `product_surface_mode`)는 schema에 reserved로 보존하고 비활성 유지.

입력/출력 또는 상태 변화
- 입력: reserved 필드 포함 brief/state
- 출력: 필드 보존된 state/plan
- 상태 변화: core decision 로직은 reserved 필드의 값에 의해 직접 분기되지 않음

테스트 항목
- reserved 필드 전달/직렬화 검증.
- reserved hook 비활성(호출/분기 미반영) 검증.
- reserved marketing field 값 변경이 core planning/review/orchestration 분기에 영향이 없는지 검증.
- `objective`/`series_id` 유무가 provider selection, revision routing, terminal_status에 직접 영향 주지 않는지 검증.

완료 기준
- 코어와 마케팅 레이어 경계가 테스트/코드에서 명시적으로 유지.

---

## 실행 순서 (고정)

1. 상태 스키마와 타입 안정성 (Task 1)
2. graph / node / orchestration (Task 2)
3. provider/service selection (Task 3)
4. render brief 생성 (Task 4)
5. review / QA / publish gate (Task 5)
5.5 post-render runtime entrypoints (Task 5.5)
6. generator 통합 (Task 6)
7. 테스트 보강 (Task 7)
8. reserved field 정리 (Task 8)

## 최종 수용 기준

- 코어만으로 planning -> QA -> publish gate까지 독립 수행 가능.
- shot_id/segment_id 기반 상태 전이가 전체 경로에서 유지.
- 마케팅 레이어 기능은 미구현 상태를 유지하되 연결 포인트는 보존.
