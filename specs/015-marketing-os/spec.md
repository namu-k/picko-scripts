# Marketing Operating System (MOS) - Architecture Specification

> **한 줄 정의:** 브랜드-데이터-크리에이티브-학습의 4개 축이 하나의 control plane 아래에서 shared state/rule/memory를 참조하며 움직이고, 중요한 지점에만 HITL 게이트가 개입하는 Brand-Governed Marketing OS

---

## 1. 한 문단 요약

이 시스템은 **개별 마케팅 에이전트들의 나열이 아니라, 하나의 마케팅 운영체제(Marketing Operating System / Control Plane)**다. 브랜드 두뇌(전략 정의), 시장 눈(데이터 수집/평가), 크리에이티브 손(생성), 실험 뇌(학습)가 **같은 상태(state), 같은 규칙(rule), 같은 기억(memory)**을 공유하며 돌아간다. 상위 목적은 성과 극대화가 아니라 **브랜드 일관성을 유지하면서 성과를 개선하는 것**이며, 모든 생성은 브랜드 규칙 아래에서 검증 가능한 단계형 파이프라인으로 실행된다.

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CONTROL PLANE                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Orchestrator │  │ Rule Engine │  │ State Manager│  │ HITL Router │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SHARED STATE LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Brand State │  │ Data State  │  │Creative State│  │Learn State  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    SHARED MEMORY (Event Log)                     │    │
│  │  decisions | feedback | experiments | mutations | audit trail   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────┬───────────────┼───────────────┬───────────┐
        ▼           ▼               ▼               ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│  BRAND    │ │   DATA    │ │ CREATIVE  │ │LEARNING   │ │   HITL    │
│  AGENTS   │ │  AGENTS   │ │  AGENTS   │ │  AGENTS   │ │   GATES   │
└───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
        │           │               │               │           │
        └───────────┴───────────────┴───────────────┴───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   EXECUTION LAYER     │
                        │  (Publish / Deploy)   │
                        └───────────────────────┘
```

### 구성 요소

| 컴포넌트 | 역할 |
|---------|------|
| **Orchestrator** | 워크플로우 실행, 에이전트 호출 순서 제어 |
| **Rule Engine** | 브랜드 규칙, 금지 표현, 리스크 임계값 평가 |
| **State Manager** | Shared State CRUD, 버전 관리, 충돌 해결 |
| **HITL Router** | 인간 개입 필요 시 판단 → 게이트 통과/대기 |
| **Shared Memory** | 모든 결정, 피드백, 실험 결과의 이벤트 로그 |

---

## 3. Shared State / Memory 설계

### 3.1 상태 vs 규칙 vs 기억 분류

| 분류 | 특성 | 예시 |
|-----|------|------|
| **State** | 현재 값, 자주 변경, 버전 관리 | brand_strategy, approved_references |
| **Rule** | 불변에 가까움, 변경 시 인간 승인 필수 | forbidden_expressions, brand_thresholds |
| **Memory** | 누적 기록, append-only | decision_log, experiment_results |

### 3.2 상태 객체 상세

#### 브랜드 영역 (Brand Domain)

| 객체명 | 설명 | 읽기 | 쓰기 | 버전관리 | HITL |
|-------|------|------|------|---------|------|
| `brand_strategy` | 브랜드 전략 전체 | 전체 | Brand Agent | ✓ | 변경 시 |
| `positioning` | 포지셔닝 스테이트먼트 | 전체 | Brand Agent | ✓ | 변경 시 |
| `emotional_territory` | 감정 축 정의 | 전체 | Brand Agent | ✓ | 변경 시 |
| `tone_manner` | 톤앤매너 가이드 | 전체 | Brand Agent | ✓ | 변경 시 |
| `forbidden_interpretations` | 금지 해석 목록 | 전체 | Rule Engine only | ✓ | **필수** |
| `forbidden_expressions` | 금지 표현 목록 | 전체 | Rule Engine only | ✓ | **필수** |
| `brand_risk_thresholds` | 리스크 임계값 | 전체 | Rule Engine only | ✓ | **필수** |

#### 데이터 영역 (Data Domain)

| 객체명 | 설명 | 읽기 | 쓰기 | 버전관리 | HITL |
|-------|------|------|------|---------|------|
| `reference_candidates` | 수집된 레퍼런스 후보 | Data Agent | Scout Agent | - | 샘플 검토 |
| `approved_reference_library` | 승인된 레퍼런스 | 전체 | 평가 Agent | ✓ | 승인 시 |
| `content_atoms` | 추출된 패턴/원자 | Creative Agent | 추출 Agent | - | - |
| `source_credibility_scores` | 소스 신뢰도 | Data Agent | Scout Agent | - | - |
| `contamination_flags` | 오염 태그 | 전체 | Scout Agent | - | - |

#### 크리에이티브 영역 (Creative Domain)

| 객체명 | 설명 | 읽기 | 쓰기 | 버전관리 | HITL |
|-------|------|------|------|---------|------|
| `campaign_briefs` | 캠페인 브리프 | Creative Agent | 전략 Agent | ✓ | 시작 시 |
| `creative_outputs` | 생성물 | Publishing | 각 생성 Agent | ✓ | 리스크 시 |
| `content_calendar` | 게시 캘린더 | Publishing | Calendar Agent | - | - |

#### 학습 영역 (Learning Domain)

| 객체명 | 설명 | 읽기 | 쓰기 | 버전관리 | HITL |
|-------|------|------|------|---------|------|
| `experiment_results` | 실험 결과 | Learning Agent | 실험 Agent | - | - |
| `learning_updates` | 학습 업데이트 제안 | Brand Agent | Learning Agent | - | 반영 전 |
| `performance_metrics` | 성과 지표 | Learning Agent | 외부 수집 | - | - |
| `human_feedback_log` | 인간 피드백 | 전체 | HITL Gates | append-only | - |

#### 메타 영역 (Meta Domain)

| 객체명 | 설명 | 읽기 | 쓰기 | 버전관리 | HITL |
|-------|------|------|------|---------|------|
| `decision_log` | 모든 결정 기록 | Audit | Orchestrator | append-only | - |
| `risk_flags` | 리스크 플래그 | 전체 | Rule Engine | - | 발생 시 |
| `system_config` | 시스템 설정 | 전체 | Admin | ✓ | **필수** |

### 3.3 JSON 스키마 예시

```json
{
  "brand_strategy": {
    "id": "bs_001",
    "version": 3,
    "created_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-07T00:00:00Z",
    "updated_by": "agent:brand_concept|human:approver",
    "status": "active",
    "content": {
      "brand_name": "Example Brand",
      "positioning_statement": "...",
      "emotional_territory": {
        "primary_axis": "confidence vs anxiety",
        "secondary_axis": "innovation vs tradition"
      },
      "tone_manner": {
        "voice": "confident, not arrogant",
        "style": "clear, not simplistic"
      }
    },
    "change_history": [
      {"version": 1, "change": "Initial creation", "approved_by": "human:ceo"},
      {"version": 2, "change": "Added secondary emotional axis", "approved_by": "human:cmo"},
      {"version": 3, "change": "Refined tone", "approved_by": "human:cmo"}
    ]
  }
}
```

```json
{
  "forbidden_expressions": {
    "id": "fe_001",
    "version": 5,
    "rule_type": "hard_constraint",
    "entries": [
      {
        "expression": "disrupt",
        "reason": "Overused, lacks differentiation",
        "added_at": "2026-03-01",
        "added_by": "human:brand_manager"
      },
      {
        "expression": "game-changer",
        "reason": "Triggers eye-roll response",
        "added_at": "2026-03-02",
        "added_by": "learning:anti_pattern_agent"
      }
    ],
    "last_audit": "2026-03-07"
  }
}
```

```json
{
  "approved_reference_library": {
    "id": "arl_001",
    "entries": [
      {
        "reference_id": "ref_123",
        "source": "instagram",
        "category": "emotional_adjacent",
        "credibility_score": 0.85,
        "contamination_flags": [],
        "approved_at": "2026-03-05",
        "approved_by": "human:curator",
        "extracted_atoms": ["atom_1", "atom_2"],
        "brand_fit_score": 0.78
      }
    ]
  }
}
```

```json
{
  "decision_log": {
    "entry_id": "dl_20260307_001",
    "timestamp": "2026-03-07T10:30:00Z",
    "workflow": "content_generation",
    "agent": "copy_agent",
    "decision_type": "content_approval",
    "input_state_refs": ["bs_001:v3", "fe_001:v5"],
    "output_ref": "co_456",
    "rule_evaluations": [
      {"rule": "brand_fit_threshold", "result": "pass", "score": 0.82},
      {"rule": "forbidden_expression_check", "result": "pass", "violations": []}
    ],
    "hitl_gate": "bypassed",
    "human_review": null
  }
}
```

---

## 4. 에이전트 설계

### 4.1 브랜드 군 (Brand Agents)

#### 브랜드 컨셉 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 브랜드 운영체제 생성 |
| **입력** | market_research, competitor_analysis, stakeholder_input |
| **출력** | brand_strategy, positioning, emotional_territory |
| **읽기** | approved_reference_library, learning_updates |
| **쓰기** | brand_strategy, positioning, emotional_territory |
| **HITL** | **필수** (모든 변경) |
| **실패 시** | → human_brand_manager |

#### 톤앤매너 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 톤앤매너 가이드 정의/업데이트 |
| **입력** | brand_strategy, tone_examples |
| **출력** | tone_manner |
| **읽기** | brand_strategy, creative_outputs(성과 좋은 것) |
| **쓰기** | tone_manner |
| **HITL** | **필수** (변경 시) |
| **실패 시** | → brand_concept_agent |

#### 브랜드 리스크 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 오해 방지, 금지 표현 관리 |
| **입력** | brand_strategy, misread_cases, performance_data |
| **출력** | forbidden_interpretations, forbidden_expressions |
| **읽기** | brand_strategy, human_feedback_log, experiment_results |
| **쓰기** | forbidden_interpretations, forbidden_expressions |
| **HITL** | **필수** (모든 추가/변경) |
| **실패 시** | → human_brand_manager |

### 4.2 데이터 군 (Data Agents)

#### 데이터 스카우트 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 좋은 데이터 선별 수집 |
| **입력** | search_queries, category_definitions |
| **출력** | reference_candidates, source_credibility_scores |
| **읽기** | brand_strategy (평가 기준) |
| **쓰기** | reference_candidates, contamination_flags |
| **HITL** | 선택적 (새로운 카테고리 진입 시) |
| **실패 시** | → human_data_curator |

#### 데이터 신뢰도/오염 판별 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 오염 요인 태깅 |
| **입력** | reference_candidates |
| **출력** | contamination_flags, credibility_adjustment |
| **읽기** | brand_strategy |
| **쓰기** | contamination_flags, source_credibility_scores |
| **HITL** | 없음 (자동) |
| **실패 시** | → data_scout_agent |

#### 레퍼런스 평가 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 브랜드 적합성 평가 |
| **입력** | reference_candidates, brand_strategy |
| **출력** | brand_fit_score, approval_recommendation |
| **읽기** | brand_strategy, forbidden_interpretations |
| **쓰기** | approved_reference_library (승인 시) |
| **HITL** | 경계 케이스만 (score 0.6-0.8) |
| **실패 시** | → human_curator |

#### 패턴/콘텐츠 원자 추출 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 레퍼런스에서 패턴 추출 |
| **입력** | approved_reference_library |
| **출력** | content_atoms |
| **읽기** | approved_reference_library |
| **쓰기** | content_atoms |
| **HITL** | 없음 |
| **실패 시** | → 재시도 + 로깅 |

### 4.3 크리에이티브 군 (Creative Agents)

#### 전략 브리프 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 캠페인 브리프 생성 |
| **입력** | brand_strategy, approved_references, content_atoms |
| **출력** | campaign_briefs |
| **읽기** | brand_strategy, approved_reference_library, learning_updates |
| **쓰기** | campaign_briefs |
| **HITL** | **필수** (새 캠페인 시작 시) |
| **실패 시** | → human_strategist |

#### 카피 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 텍스트 카피 생성 |
| **입력** | campaign_brief, tone_manner, content_atoms |
| **출력** | creative_outputs (copy) |
| **읽기** | brand_strategy, tone_manner, forbidden_expressions |
| **쓰기** | creative_outputs |
| **HITL** | 리스크 플래그 시만 |
| **실패 시** | → 재생성 → HITL |

#### 스토리보드/이미지 프롬프트 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 비주얼 생성 가이드 |
| **입력** | campaign_brief, copy |
| **출력** | creative_outputs (storyboard, image_prompt) |
| **읽기** | brand_strategy, tone_manner |
| **쓰기** | creative_outputs |
| **HITL** | **필수** (최초안) |
| **실패 시** | → human_creative_director |

### 4.4 실험/학습 군 (Learning Agents)

#### 실험 설계 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | A/B 테스트 설계 |
| **입력** | campaign_brief, hypothesis |
| **출력** | experiment_design |
| **읽기** | brand_strategy, past experiment_results |
| **쓰기** | experiment_design |
| **HITL** | 없음 |
| **실패 시** | → default_design |

#### 성과 해석 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 성과 분석, 인사이트 추출 |
| **입력** | performance_metrics, experiment_design |
| **출력** | insights, learning_updates |
| **읽기** | brand_strategy, creative_outputs |
| **쓰기** | learning_updates |
| **HITL** | 없음 |
| **실패 시** | → human_analyst |

#### 운영 규칙 업데이트 제안 에이전트

| 항목 | 내용 |
|-----|------|
| **역할** | 규칙 변경 제안 |
| **입력** | learning_updates, performance_trends |
| **출력** | rule_change_proposals |
| **읽기** | 모든 state |
| **쓰기** | rule_change_proposals (제안만) |
| **HITL** | **필수** (모든 제안) |
| **실패 시** | → human_ops_manager |

---

## 5. HITL 설계

### 5.1 HITL 게이트 분류

| 게이트 유형 | 개입 시점 | 예시 |
|-----------|---------|------|
| **Mandatory** | 항상 | 브랜드 규칙 변경, 금지 표현 추가 |
| **Conditional** | 조건 충족 시 | brand_fit < 0.7, risk_score > 0.8 |
| **Sampling** | 랜덤 샘플 | 생성물 10% 랜덤 검토 |
| **Escalation** | 에이전트 실패 시 | 판단 불가 시 사람 승격 |

### 5.2 HITL 게이트 매트릭스

| 상황 | 자동 | 조건부 HITL | 필수 HITL |
|-----|------|------------|----------|
| 브랜드 전략 변경 | ❌ | ❌ | ✅ |
| 금지 표현 추가 | ❌ | ❌ | ✅ |
| 새 캠페인 시작 | ❌ | ❌ | ✅ |
| 일반 카피 생성 | ✅ | risk > 0.7 | ❌ |
| 레퍼런스 승인 | ✅ | fit 0.6-0.8 | ❌ |
| 성과 기반 규칙 변경 | ❌ | ❌ | ✅ |
| 일반 게시 | ✅ | ❌ | ❌ |
| 위기 상황 감지 | ❌ | ❌ | ✅ |

### 5.3 운영 모드별 HITL 범위

#### Manual-Heavy (초기 모드)

| 항목 | 설정 |
|-----|------|
| 인간 개입 범위 | 모든 주요 결정 |
| 자동화 범위 | 데이터 수집, 패턴 추출 |
| 적합 시점 | 시스템 런칭 후 0-2주 |
| 위험 요소 | 느린 속도, 인력 의존 |
| HITL 비율 | 80%+ |

#### Semi-Auto (운영 모드)

| 항목 | 설정 |
|-----|------|
| 인간 개입 범위 | 규칙 변경, 경계 케이스 |
| 자동화 범위 | 생성, 게시, 일반 평가 |
| 적합 시점 | 2-6주 |
| 위험 요소 | 규칙 낡음, drift |
| HITL 비율 | 20-40% |

#### Auto-with-Guardrails (성숙 모드)

| 항목 | 설정 |
|-----|------|
| 인간 개입 범위 | 예외, 전략 변경 |
| 자동화 범위 | 거의 전체 |
| 적합 시점 | 6주+ |
| 위험 요소 | 자동화 과신 |
| HITL 비율 | 5-15% |

---

## 6. 거버넌스 원칙

### 6.1 Brand Governance

```
┌─────────────────────────────────────────────────────────────┐
│                   BRAND GOVERNANCE HIERARCHY                 │
├─────────────────────────────────────────────────────────────┤
│  Level 1: Core Identity (immutable without C-level)         │
│  - brand_mission, brand_values, positioning                 │
├─────────────────────────────────────────────────────────────┤
│  Level 2: Operating Rules (changeable with manager approval)│
│  - tone_manner, forbidden_expressions, risk_thresholds      │
├─────────────────────────────────────────────────────────────┤
│  Level 3: Tactical Decisions (auto with guardrails)         │
│  - content_variations, channel_tactics, a/b_tests           │
└─────────────────────────────────────────────────────────────┘
```

**핵심 규칙:**

1. `brand_fit_score < threshold` → 자동 폐기 또는 HITL
2. `misread_risk > threshold` → 게시 금지
3. 성과 높음 + 브랜드 부적합 → 학습 데이터 승격 금지
4. 새로운 성과 패턴 → 브랜드 규칙 자동 덮어쓰기 금지
5. 브랜드 규칙 변경 → 버전 관리 + 인간 승인 필수

### 6.2 Data Governance

**좋은 데이터 기준:**
- 직접/인접 카테고리에서 수집
- contamination_flags = []
- credibility_score > 0.7
- 댓글/반응 데이터 충분

**오염 요인 태깅:**

| 오염 유형 | 태그 | 처리 |
|---------|------|------|
| 유명인 버프 | `celebrity_buff` | 가중치 감소 |
| 경품/이벤트 | `giveaway` | 참고용만 |
| 낚시/자극성 | `clickbait` | 제외 |
| 논란 버프 | `controversy` | 제외 |
| 데이터 부족 | `sparse_metrics` | 불확실성 증가 |

### 6.3 Creative Governance

**생성 파이프라인:**

```
1. brand_rules_check(brand_strategy, forbidden_expressions)
2. reference_search(approved_reference_library, brief)
3. brief_composition(campaign_brief, content_atoms)
4. format_generation(brief, channel)
5. risk_assessment(generated_content)
6. HITL_gate(risk_score)  # 조건부
7. approval_and_publish()
```

### 6.4 Learning Governance

**학습 → 반영 흐름:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 성과 데이터  │ ──→ │ 인사이트 추출│ ──→ │ 변경 제안   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼─────────────┐
                    ▼                          ▼             ▼
            ┌─────────────┐            ┌─────────────┐ ┌─────────────┐
            │ 단순 리포트  │            │패턴 승격 후보│ │금지규칙 후보 │
            │ (자동)      │            │ (HITL 검토) │ │ (필수 HITL) │
            └─────────────┘            └─────────────┘ └─────────────┘
```

**자동 반영 vs 인간 승인:**

| 변경 유형 | 자동 반영 | 인간 승인 |
|---------|---------|---------|
| content_atom 추가 | ✅ | ❌ |
| reference_library 확장 | ✅ (high fit) | 조건부 |
| tone_manner 미세 조정 | ❌ | ✅ |
| forbidden_expression 추가 | ❌ | **필수** |
| brand_strategy 수정 | ❌ | **필수** |
| 실험 설정 변경 | ✅ | ❌ |

---

## 7. 주요 워크플로우

### 7.1 브랜드 초기 정의 워크플로우

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BRAND DEFINITION WORKFLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1: Input Gathering                                             │
│  ├── stakeholder_interviews (human input)                           │
│  ├── market_research (data agent)                                   │
│  └── competitor_analysis (data agent)                               │
│                                                                      │
│  Step 2: Brand Concept Generation                                    │
│  ├── [brand_concept_agent]                                          │
│  │   ├── reads: market_research, competitor_analysis                │
│  │   └── writes: brand_strategy (draft)                             │
│  └── [HITL: BRAND_STRATEGY_REVIEW] ← 필수                           │
│                                                                      │
│  Step 3: Positioning & Territory                                     │
│  ├── [positioning_agent]                                            │
│  │   ├── reads: brand_strategy                                      │
│  │   └── writes: positioning, emotional_territory                   │
│  └── [HITL: POSITIONING_APPROVAL] ← 필수                            │
│                                                                      │
│  Step 4: Tone & Manner                                               │
│  ├── [tone_manner_agent]                                            │
│  │   ├── reads: brand_strategy, positioning                         │
│  │   └── writes: tone_manner                                        │
│  └── [HITL: TONE_APPROVAL] ← 필수                                   │
│                                                                      │
│  Step 5: Risk Guardrails                                             │
│  ├── [risk_agent]                                                   │
│  │   ├── reads: brand_strategy, positioning                         │
│  │   └── writes: forbidden_interpretations, forbidden_expressions   │
│  └── [HITL: RISK_RULES_APPROVAL] ← 필수                             │
│                                                                      │
│  Step 6: Activation                                                  │
│  └── state_manager.set_status(brand_strategy, "active")             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 레퍼런스 수집·평가 워크플로우

```
┌─────────────────────────────────────────────────────────────────────┐
│                   REFERENCE COLLECTION WORKFLOW                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1: Scouting                                                    │
│  ├── [data_scout_agent]                                             │
│  │   ├── reads: brand_strategy (카테고리 정의용)                     │
│  │   └── writes: reference_candidates                               │
│  └── (자동 실행, 정기적)                                             │
│                                                                      │
│  Step 2: Contamination Check                                         │
│  ├── [contamination_agent]                                          │
│  │   ├── reads: reference_candidates                                │
│  │   └── writes: contamination_flags, credibility_scores           │
│  └── (자동, HITL 없음)                                               │
│                                                                      │
│  Step 3: Brand Fit Evaluation                                        │
│  ├── [reference_eval_agent]                                         │
│  │   ├── reads: brand_strategy, forbidden_interpretations           │
│  │   ├── reads: reference_candidates + flags                        │
│  │   └── writes: brand_fit_scores                                   │
│  └── [HITL: BORDERLINE_REVIEW] ← fit 0.6-0.8만                      │
│                                                                      │
│  Step 4: Pattern Extraction                                          │
│  ├── [atom_extraction_agent]                                        │
│  │   ├── reads: approved_references                                 │
│  │   └── writes: content_atoms                                      │
│  └── (자동)                                                          │
│                                                                      │
│  Step 5: Library Update                                              │
│  └── state_manager.add_to_library(approved_references)              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 캠페인/콘텐츠 생성 워크플로우

```
┌─────────────────────────────────────────────────────────────────────┐
│                   CONTENT GENERATION WORKFLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1: Campaign Brief                                              │
│  ├── [strategy_brief_agent]                                         │
│  │   ├── reads: brand_strategy, approved_references, content_atoms  │
│  │   └── writes: campaign_brief                                     │
│  └── [HITL: CAMPAIGN_BRIEF_APPROVAL] ← 필수                         │
│                                                                      │
│  Step 2: Pre-generation Check                                        │
│  ├── rule_engine.check(forbidden_expressions, brand_thresholds)     │
│  └── pass → continue, fail → abort + alert                          │
│                                                                      │
│  Step 3: Content Creation (parallel)                                 │
│  ├── [copy_agent] → creative_outputs.copy                           │
│  ├── [storyboard_agent] → creative_outputs.storyboard               │
│  └── [image_prompt_agent] → creative_outputs.image_prompt           │
│                                                                      │
│  Step 4: Risk Assessment                                             │
│  ├── [risk_agent.evaluate]                                          │
│  │   ├── checks: brand_fit, misread_risk, forbidden_violations      │
│  │   └── outputs: risk_score, risk_flags                            │
│  └── if risk_score > threshold → [HITL: CONTENT_REVIEW]             │
│                                                                      │
│  Step 5: Format Conversion                                           │
│  ├── [channel_conversion_agent]                                     │
│  │   ├── reads: creative_outputs                                    │
│  │   └── writes: channel_ready_outputs                              │
│  └── (자동)                                                          │
│                                                                      │
│  Step 6: Publish                                                     │
│  └── execution_layer.publish(channel_ready_outputs)                 │
│                                                                      │
│  Step 7: Log                                                         │
│  └── decision_log.append(full_trace)                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.4 실험·성과 반영 워크플로우

```
┌─────────────────────────────────────────────────────────────────────┐
│                   EXPERIMENT & LEARNING WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1: Experiment Design                                           │
│  ├── [experiment_design_agent]                                      │
│  │   ├── reads: campaign_brief, past_experiments                    │
│  │   └── writes: experiment_design                                  │
│  └── (자동, 새 실험만)                                               │
│                                                                      │
│  Step 2: Data Collection (ongoing)                                   │
│  ├── external: platform_metrics (views, engagement, etc.)           │
│  └── writes: performance_metrics                                    │
│                                                                      │
│  Step 3: Performance Normalization                                   │
│  ├── [performance_normalizer]                                       │
│  │   ├── reads: performance_metrics, experiment_design              │
│  │   └── writes: normalized_results                                 │
│  └── (자동, 정기적)                                                  │
│                                                                      │
│  Step 4: Analysis                                                    │
│  ├── [performance_analyst]                                          │
│  │   ├── reads: normalized_results, creative_outputs                │
│  │   └── writes: insights, pattern_candidates                       │
│  └── (자동)                                                          │
│                                                                      │
│  Step 5: Learning Classification                                     │
│  ├── classify(insight):                                             │
│  │   ├── report_only → store & notify                               │
│  │   ├── pattern_candidate → [HITL: PATTERN_REVIEW]                 │
│  │   └── rule_change_candidate → [HITL: RULE_CHANGE_REVIEW]         │
│  └──                                                                 │
│                                                                      │
│  Step 6: Rule Update (if approved)                                   │
│  ├── [rule_update_agent]                                            │
│  │   ├── reads: approved_changes                                    │
│  │   └── writes: rule_change_proposals → state_manager              │
│  └── [HITL: FINAL_RULE_APPROVAL] ← 필수                             │
│                                                                      │
│  Step 7: Brand Evolution                                             │
│  ├── [brand_evolution_agent]                                        │
│  │   ├── reads: accumulated_insights                                │
│  │   └── writes: brand_evolution_proposals                          │
│  └── [HITL: BRAND_EVOLUTION_APPROVAL] ← 필수                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. MVP 로드맵

### 8.1 2주 MVP (Core Loop)

**필수 기능:**
- [ ] 기본 Control Plane (Orchestrator + State Manager)
- [ ] 브랜드 컨셉 에이전트 (수동 입력 지원)
- [ ] 레퍼런스 평가 에이전트 (단순 버전)
- [ ] 카피 생성 에이전트
- [ ] 기본 HITL 게이트 (브랜드 승인, 생성물 승인)
- [ ] Shared State (brand_strategy, approved_references, creative_outputs)
- [ ] Decision Log

**생략 가능:**
- 자동 데이터 스카우트
- 오염 탐지
- 실험 설계
- 성과 학습 루프
- 멀티 채널 변환

**수작업 대체:**
- 레퍼런스 수집 → 사람이 직접 추가
- 브랜드 정의 → 사람이 작성, 시스템에 입력
- 성과 분석 → 수동 리포트

**필수 HITL:**
- 브랜드 전략 승인
- 모든 생성물 승인 (100%)

**기술 리스크:**
- State 관리 복잡도
- LLM 응답 품질

### 8.2 6주 MVP (Operational)

**필수 기능:**
- [ ] 데이터 스카우트 에이전트
- [ ] 오염 판별 에이전트
- [ ] 패턴 추출 에이전트
- [ ] 전략 브리프 에이전트
- [ ] Rule Engine (금지 표현, 리스크 임계값)
- [ ] 성과 수집 + 기본 분석
- [ ] Conditional HITL (리스크 기반)

**생략 가능:**
- 자동 규칙 업데이트 제안
- 브랜드 진화 제안
- 고급 실험 설계

**수작업 대체:**
- 규칙 변경 제안 → 사람이 직접
- 브랜드 진화 → 수동 검토

**필수 HITL:**
- 브랜드 규칙 변경
- 경계 케이스 레퍼런스
- 리스크 플래그 생성물

**기술 리스크:**
- 오염 탐지 정확도
- 브랜드 적합도 평가 품질

### 8.3 3개월 버전 (Production)

**필수 기능:**
- [ ] 전체 에이전트 군
- [ ] 자동 규칙 업데이트 제안
- [ ] 브랜드 진화 제안
- [ ] 멀티 채널 변환
- [ ] 고급 실험 설계
- [ ] 성과 예측
- [ ] 감사 대시보드
- [ ] 버전 관리 UI

**생략 가능:**
- 없음 (전체 기능)

**수작업 대체:**
- 없음

**필수 HITL:**
- 브랜드 전략 변경
- 금지 규칙 변경
- 예외/위기 상황

**기술 리스크:**
- 시스템 복잡도 관리
- 대규모 state 동기화

---

## 9. 추천 기술 스택

### 9.1 Orchestration

| 옵션 | 장점 | 단점 | 추천 |
|-----|------|------|------|
| **LangGraph** | 상태 머신 내장, Python native | 학습 곡선 | ★★★★★ |
| Custom Python | 완전 제어 | 개발 공수 | ★★★★☆ |
| n8n | 시각화, 노코드 | 복잡한 로직 제한 | ★★☆☆☆ |

**추천:** LangGraph + Custom Python 하이브리드

### 9.2 Storage

| 데이터 유형 | 추천 스택 |
|-----------|---------|
| Shared State | **PostgreSQL** (JSONB) 또는 Supabase |
| Vector Search | pgvector 또는 Qdrant |
| Event Log | PostgreSQL (append-only 테이블) |
| File Storage | S3 / Supabase Storage |

### 9.3 LLM 구성

| 용도 | 모델 타입 | 추천 |
|-----|---------|------|
| 분류/평가 | Small, Fast | GPT-4o-mini, Claude Haiku |
| 생성 | High Quality | GPT-4o, Claude Sonnet |
| 전략/복잡한 판단 | Best Quality | Claude Opus, GPT-4 |

**권장:** 용도별 모델 분리

### 9.4 Rule Engine

| 옵션 | 추천도 |
|-----|-------|
| Custom Python Rules | ★★★★★ |
| Open Policy Agent (OPA) | ★★★☆☆ |

**추천:** Custom Python + JSON rule definitions

### 9.5 Monitoring

| 용도 | 도구 |
|-----|------|
| Logging | Loguru / structlog |
| Tracing | LangSmith / OpenTelemetry |
| Experiment Tracking | MLflow (optional) |

### 9.6 요약 스택

```
┌─────────────────────────────────────────────────────────┐
│                    RECOMMENDED STACK                     │
├─────────────────────────────────────────────────────────┤
│  Orchestration: LangGraph + Python                      │
│  State Storage: PostgreSQL (Supabase)                   │
│  Vector Store: pgvector                                 │
│  LLM: OpenAI (4o-mini/4o) + Claude (Haiku/Sonnet)       │
│  Rules: Custom Python + JSON                            │
│  Logging: Loguru + LangSmith                            │
│  HITL: Slack/Telegram Bot + Web Dashboard               │
│  Hosting: Vercel (frontend) + Railway/Render (backend)  │
└─────────────────────────────────────────────────────────┘
```

---

## 10. 실패 시나리오와 방어 설계

### 10.1 에이전트 판단 충돌

**시나리오:** 브랜드 에이전트는 "적합"이라고 판단, 리스크 에이전트는 "위험"이라고 판단

**방어:**
```
conflict_resolution:
  priority_order:
    - forbidden_expressions (hard veto)
    - brand_risk_thresholds
    - brand_fit_score
    - creative_preference

  tie_breaker: HITL escalation
```

### 10.2 고효과 저브랜드 콘텐츠 오염

**시나리오:** 성과는 높지만 브랜드와 맞지 않는 콘텐츠가 학습 데이터로 승격

**방어:**
```python
def promote_to_learning(content, performance):
    if content.brand_fit_score < BRAND_FIT_THRESHOLD:
        return PromotionResult(
            allowed=False,
            reason="brand_fit_below_threshold",
            action="log_only"
        )
    if content.misread_risk > MISREAD_THRESHOLD:
        return PromotionResult(
            allowed=False,
            reason="misread_risk_elevated",
            action="add_to_forbidden_candidates"
        )
    return PromotionResult(allowed=True)
```

### 10.3 데이터 수집 편향

**시나리오:** 특정 카테고리/소스에 과도하게 편향된 수집

**방어:**
- Category Coverage Report (주간)
- Source Diversity Score
- 편향 감지 시 자동 밸런싱 또는 HITL 알림

### 10.4 브랜드 Drift

**시나리오:** 시간이 지나며 생성물이 브랜드에서 멀어짐

**방어:**
- 정기 Brand Alignment Audit (주간)
- Drift Detection Score
- drift > threshold → 자동 브랜드 재정의 트리거

### 10.5 과도한 인간 개입

**시나리오:** HITL이 너무 많아 자동화 효율 저하

**방어:**
- HITL Ratio Monitoring
- Ratio > 40% → 자동으로 threshold 조정 제안
- Pattern: 자주 승인되는 패턴 → 자동 승격

### 10.6 인간 개입 부족

**시나리오:** HITL이 너무 적어 브랜드 사고 발생

**방어:**
- 최소 HITL Sampling Rate (5% 랜덤)
- 위험 키워드 감지 시 자동 HITL
- 정기 브랜드 감사

### 10.7 State 충돌/노후화

**시나리오:** 여러 에이전트가 동시에 state 수정, 또는 state가 낡음

**방어:**
- Optimistic Locking (version 기반)
- State Freshness Check (last_updated 기준)
- Conflict → last-write-wins + audit log

### 10.8 과거 실험 데이터 오류 유도

**시나리오:** 과거 실험이 현재 전략에 맞지 않는 결론을 유도

**방어:**
- Experiment Relevance Decay (시간 가중치)
- Strategy Change → 관련 실험 재평가 트리거
- Context-aware Learning (현재 브랜드 버전 기준)

---

## 11. 구현 예시

### 11.1 LangGraph State Machine (Core Loop)

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

class MarketingState(TypedDict):
    # Brand Domain
    brand_strategy: dict
    forbidden_expressions: list[str]

    # Data Domain
    reference_candidates: list[dict]
    approved_references: list[dict]

    # Creative Domain
    campaign_brief: dict
    creative_outputs: list[dict]

    # Control
    risk_score: float
    hitl_required: bool
    decision_trace: list[dict]

def brand_rules_check(state: MarketingState) -> MarketingState:
    """Step 1: 브랜드 규칙 확인"""
    # Rule Engine 호출
    violations = rule_engine.check_forbidden(
        state.get("creative_outputs", []),
        state["forbidden_expressions"]
    )
    state["risk_score"] = len(violations) * 0.2
    state["hitl_required"] = state["risk_score"] > 0.7
    return state

def reference_search(state: MarketingState) -> MarketingState:
    """Step 2: 레퍼런스 검색"""
    brief = state["campaign_brief"]
    refs = vector_search(
        query=brief["theme"],
        collection=state["approved_references"],
        top_k=5
    )
    state["selected_references"] = refs
    return state

def generate_content(state: MarketingState) -> MarketingState:
    """Step 3: 콘텐츠 생성"""
    outputs = copy_agent.generate(
        brief=state["campaign_brief"],
        references=state["selected_references"],
        tone=state["brand_strategy"]["tone_manner"]
    )
    state["creative_outputs"] = outputs
    return state

def risk_assessment(state: MarketingState) -> MarketingState:
    """Step 4: 리스크 평가"""
    risk = risk_agent.assess(
        content=state["creative_outputs"],
        brand=state["brand_strategy"]
    )
    state["risk_score"] = risk.score
    state["hitl_required"] = risk.score > 0.7
    return state

def hitl_gate(state: MarketingState) -> str:
    """라우팅: HITL 필요 여부"""
    if state["hitl_required"]:
        return "human_review"
    return "publish"

def human_review(state: MarketingState) -> MarketingState:
    """HITL: 인간 검토"""
    approval = hitl_router.request_review(
        content=state["creative_outputs"],
        context=state["decision_trace"]
    )
    state["human_approved"] = approval.approved
    state["human_feedback"] = approval.feedback
    return state

def publish(state: MarketingState) -> MarketingState:
    """게시"""
    execution_layer.publish(state["creative_outputs"])
    decision_log.append(state)
    return state

# Graph 구성
graph = StateGraph(MarketingState)

graph.add_node("brand_check", brand_rules_check)
graph.add_node("ref_search", reference_search)
graph.add_node("generate", generate_content)
graph.add_node("assess", risk_assessment)
graph.add_node("human_review", human_review)
graph.add_node("publish", publish)

graph.add_edge("brand_check", "ref_search")
graph.add_edge("ref_search", "generate")
graph.add_edge("generate", "assess")
graph.add_conditional_edges("assess", hitl_gate, {
    "human_review": "human_review",
    "publish": "publish"
})
graph.add_edge("human_review", "publish")
graph.add_edge("publish", END)

graph.set_entry_point("brand_check")

marketing_workflow = graph.compile()
```

### 11.2 Rule Engine 예시

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class Rule:
    name: str
    condition: Callable[[dict], bool]
    action: str  # "block", "warn", "log"
    priority: int

class RuleEngine:
    def __init__(self):
        self.rules: list[Rule] = []

    def register(self, rule: Rule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, context: dict) -> dict:
        results = []
        for rule in self.rules:
            if rule.condition(context):
                results.append({
                    "rule": rule.name,
                    "action": rule.action,
                    "priority": rule.priority
                })
                if rule.action == "block":
                    break
        return {
            "blocked": any(r["action"] == "block" for r in results),
            "warnings": [r for r in results if r["action"] == "warn"],
            "results": results
        }

# 규칙 정의 예시
engine = RuleEngine()

engine.register(Rule(
    name="forbidden_expression_check",
    condition=lambda ctx: any(
        expr in ctx.get("content", "")
        for expr in ctx.get("forbidden_expressions", [])
    ),
    action="block",
    priority=100
))

engine.register(Rule(
    name="brand_fit_threshold",
    condition=lambda ctx: ctx.get("brand_fit_score", 1.0) < 0.6,
    action="block",
    priority=90
))

engine.register(Rule(
    name="misread_risk_high",
    condition=lambda ctx: ctx.get("misread_risk", 0) > 0.8,
    action="block",
    priority=85
))

engine.register(Rule(
    name="low_performance_high_risk",
    condition=lambda ctx: (
        ctx.get("performance_score", 0) > 0.8 and
        ctx.get("brand_fit_score", 1) < 0.5
    ),
    action="warn",
    priority=70
))
```

### 11.3 HITL Router 예시

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class HITLType(Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    SAMPLING = "sampling"
    ESCALATION = "escalation"

@dataclass
class HITLRequest:
    id: str
    type: HITLType
    content: dict
    context: dict
    created_at: datetime
    timeout_hours: int
    callback_url: str

class HITLRouter:
    def __init__(self, notification_client, dashboard_url):
        self.notification = notification_client
        self.dashboard_url = dashboard_url
        self.pending_reviews = {}

    def request_review(self, content: dict, context: dict,
                       hitl_type: HITLType = HITLType.CONDITIONAL) -> dict:
        request = HITLRequest(
            id=generate_id(),
            type=hitl_type,
            content=content,
            context=context,
            created_at=datetime.now(),
            timeout_hours=24,
            callback_url=f"{self.dashboard_url}/review"
        )

        # 알림 발송
        self.notification.send(
            channel="slack",
            message=self._format_message(request)
        )

        # 대기 큐에 추가
        self.pending_reviews[request.id] = request

        # 동기 대기 (또는 비동기 처리)
        return self._wait_for_response(request)

    def should_trigger_hitl(self, state: dict) -> tuple[bool, HITLType]:
        """HITL 필요 여부 판단"""
        # Mandatory cases
        if state.get("workflow") == "brand_strategy_change":
            return True, HITLType.MANDATORY
        if state.get("workflow") == "forbidden_rule_change":
            return True, HITLType.MANDATORY

        # Conditional cases
        if state.get("risk_score", 0) > 0.8:
            return True, HITLType.CONDITIONAL
        if 0.6 <= state.get("brand_fit_score", 1) <= 0.8:
            return True, HITLType.CONDITIONAL

        # Sampling
        if random.random() < 0.05:  # 5% 샘플링
            return True, HITLType.SAMPLING

        return False, None
```

---

## 12. 결론

이 시스템은 **개별 에이전트의 나열이 아니라, 중앙 Control Plane 아래에서 모든 것이 연결된 마케팅 운영체제**다.

**핵심 설계 원칙:**

1. **Brand First:** 성과보다 브랜드 일관성이 상위 원칙
2. **Shared Everything:** 모든 에이전트가 같은 state/rule/memory 공유
3. **Judgment > Generation:** 생성은 판단의 실행일 뿐
4. **Selective HITL:** 모든 것에 사람이 개입하지 않고, 게이트로 제어
5. **Auditability:** 모든 결정이 추적 가능

**다음 단계:**
- 2주 MVP 구현 시작
- 브랜드 컨셉 에이전트 + 기본 HITL 게이트부터
- 점진적으로 에이전트 추가

---

*Spec Version: 1.0*
*Last Updated: 2026-03-07*
