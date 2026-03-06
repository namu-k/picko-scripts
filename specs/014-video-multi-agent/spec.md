# Multi-Agent Video Planning & Production Architecture

## Meta

- **Spec ID**: 014
- **Branch**: `014-video-multi-agent`
- **Status**: Ready for Implementation
- **Created**: 2026-03-06
- **Updated**: 2026-03-06 (v3 - 구현 가이드 추가)

---

## 1. 목적

현재 VideoGenerator는 단일 LLM 호출로 VideoPlan을 생성한다. 이 방식의 한계:

- 스토리, 카피, 프롬프트, 제작 방식이 한 번에 섞여 품질 관리 어려움
- 이미지 기반 제작과 비디오 기반 제작을 구분하지 못함
- 피드백 루프가 단순 재시도 수준
- 샷 단위 일관성, 감성 톤, 제작 전략 분리 개선 불가

### 1단계 목표

> **새벽 감성 숏폼 영상을 위한 "기획 + 카피 + 프롬프트 + 제작전략 + 품질검수" 패키지를 멀티에이전트로 생성하는 비디오 제작 시스템을 구축한다.**

### 범위 밖 (Out of Scope)

- 감성 키워드 발굴
- 브랜드 가이드 초안화
- 시리즈 기획
- 채널별 포맷 적응
- 실험 설계
- 성과 분석
- 외부 피드백 통합
- 레퍼런스 탐색 시스템

### 마케팅 레이어 확장 포인트

향후 마케팅 기능이 추가될 때를 대비해 명시적 확장 슬롯을 정의한다:

```python
# VideoAgentState 내 확장 필드
campaign_context: dict | None      # 시리즈/캠페인 맥락 (Story Writer 참조)
performance_hints: list[str]       # 과거 성과 기반 힌트 (Reviewer 참조)
experiment_vars: dict | None       # A/B 테스트 변수 (Orchestrator 참조)
```

| 마케팅 기능 | 주입 포인트 | 참조 에이전트 |
|------------|------------|---------------|
| A/B 실험 변수 | `experiment_vars` | Orchestrator |
| 성과 데이터 피드백 | `performance_hints` | Reviewer |
| 시리즈/캠페인 컨텍스트 | `campaign_context` | Story Writer |
| 채널별 포맷 적응 | `platforms[]` + 전용 노드 | (향후 추가) |

---

## 2. 시스템 범위

### 포함 범위

- 영상 콘셉트에 맞는 스토리 구조 설계
- 샷 단위 장면 설명 생성
- 훅, 캡션, CTA 등 카피 생성
- 이미지 프롬프트 및 비디오 프롬프트 생성
- 각 샷의 제작 방식 결정 (pure video / keyframe + motion / image sequence + stitch)
- 샷 간 일관성, 브랜드 톤, 구조 품질 검수
- 필요 시 특정 에이전트 재호출

### 결과물

| 산출물 | 설명 |
|--------|------|
| `visual_anchor` | 전체 샷 공통 비주얼 기준 |
| `shot_list` | 샷 시퀀스 |
| `copy_pack` | 훅, 캡션, CTA, 오버레이 |
| `image_prompt_pack` | 키프레임용 이미지 프롬프트 |
| `video_prompt_pack` | 비디오 생성용 프롬프트 |
| `production_plan` | 샷별 제작 방식 |
| `stitch_plan` | 이미지 시퀀스/전환 계획 |
| `asset_manifest` | 제작 필요 자산 목록 |
| `review_notes` | 품질 검수 피드백 |
| `final_status` | approved / rejected |

---

## 3. 에이전트 구조

### 3.1 Story Writer (스토리 작가)

**역할**: Narrative arc 설계, visual anchor 생성, 샷 시퀀스 작성

**출력**:
- `visual_anchor`
- `shots[]` 초안

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `analyze_intent` | 규칙 | Intent별 샷 구조 기본값 매핑 |
| `generate_anchor` | LLM | visual anchor 생성 |
| `plan_shots` | LLM | shot sequence 및 장면 설명 생성 |

---

### 3.2 Copywriter (카피라이터)

**역할**: 훅, 캡션, CTA 작성, 텍스트 오버레이 초안

**출력**:
- `hook`
- `captions[]`
- `cta`
- `overlay_texts[]`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `create_hook` | LLM | 첫 3초 훅 생성 |
| `generate_caption` | LLM | shot별 캡션 생성 |
| `write_cta` | LLM | CTA 작성 |

---

### 3.3 Prompt Engineer (프롬프트 엔지니어)

**역할**: 서비스별 비디오/이미지 프롬프트 생성

**출력**:
- `video_prompts[]`
- `image_prompts[]`
- `negative_prompts[]`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `build_service_prompt` | LLM | 서비스별 비디오 프롬프트 생성 |
| `create_keyframe_prompt` | 규칙+LLM | keyframe 이미지 프롬프트 생성 |
| `apply_negative_prompt` | 규칙 | 서비스별 negative prompt 적용 |

---

### 3.3 Stitch Planner (스티치 플래너) ⭐ NEW

**역할**: 각 샷의 제작 방식 결정, 이미지 기반 영상 제작 전략 수립

**주요 책임**:
- shot별 생성 방식 선택 (pure video / image + motion / image sequence + stitch)
- continuity reference 정의
- 전환 방식 및 자산 구성 계획
- 최종 제작용 asset manifest 작성

**입력**:
- `shots[]` (Story Writer 출력)
- `services[]` (요청된 서비스 목록)
- `SERVICE_CONSTRAINTS` (서비스별 제약 사항)

**출력**:
- `generation_methods[]`
- `continuity_refs`
- `stitch_plan`
- `asset_manifest`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `select_generation_method` | 규칙+LLM | shot별 생성 방식 선택 (`SERVICE_CONSTRAINTS` 참조) |
| `build_continuity_refs` | 규칙 | 캐릭터/배경/조명 일관성 참조 정리 |
| `plan_stitch_sequence` | LLM | 이미지 시퀀스/스티치 계획 작성 |
| `build_asset_manifest` | 규칙 | 제작 자산 목록 정리 |

**select_generation_method 로직**:
```python
def select_generation_method(shot: ShotDraft, services: list[str]) -> str:
    """shot + 서비스 제약을 보고 생성 방식 결정"""
    from picko.video.constraints import SERVICE_CONSTRAINTS

    for service in services:
        c = SERVICE_CONSTRAINTS[service]

        # image_stitch는 start_image 지원 필수
        if not c.supports_start_image:
            return "pure_video"

        # keyframe_motion은 start+end 이미지 모두 필요
        if shot.motion_type in ("morph", "interpolate"):
            if c.supports_start_image and c.supports_end_image:
                return "keyframe_motion"
            return "pure_video"

    # 복잡한 경우 LLM 보조 판단
    return _llm_decide_method(shot, services)
```

---

### 3.5 Reviewer (리뷰어)

**역할**: 구조, 감성 톤, 일관성, 제작 전략 품질 검수

**출력**:
- `quality_score`
- `quality_issues[]`
- `feedback_notes[]`
- `revision_target`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `check_consistency` | 규칙 | anchor/shot/continuity 일관성 검사 |
| `validate_brand` | 규칙 | 금칙어/톤 위반 검사 |
| `review_structure` | LLM | 전체 품질 평가 |
| `review_production_fit` | LLM | shot과 제작 방식 적합성 평가 |

---

### 3.6 Orchestrator (오케스트레이터)

**역할**: 상태 흐름 제어, 재호출 결정, 반복 관리

**출력**:
- `approved`
- `next_step`
- `human_review_required`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `decide_next_step` | 규칙 (+LLM 보조) | 다음 호출 에이전트 결정 |
| `enforce_iteration_limit` | 규칙 | 반복 횟수 제한 |
| `mark_human_review` | 규칙 | human review 필요 여부 판단 |

---

## 4. 상태 흐름

### 기본 흐름 (2-pass + Fan-out)

```
START
  ↓
story_writer         → visual_anchor, shots[]
  ↓
stitch_planner       → generation_methods[], stitch_plan, asset_manifest
  ↓
┌─────────────────────┼─────────────────────┐
│                     │                     │
copywriter        prompt_engineer          │ (fan-out 병렬)
│                     │                     │
└─────────────────────┴─────────────────────┘
  ↓
reviewer             → quality_score, issues, revision_target
  ↓
orchestrator         → approved / cascade invalidation + 재실행
```

**핵심 변경점**:
- Stitch Planner가 Story Writer 직후 실행 (generation_method 먼저 확정)
- Copywriter와 Prompt Engineer는 **병렬 실행** (서로 의존 없음)
- Prompt Engineer는 generation_method를 입력으로 받아 선택적 프롬프트 생성

### 분기 흐름 (Cascade Invalidation)

```
orchestrator 결과:
  [approved]                → END
  [revise_story]            → story_writer + (stitch_planner, copywriter, prompt_engineer)  # cascade
  [revise_stitch]           → stitch_planner + (prompt_engineer)  # cascade
  [revise_copy]             → copywriter  # 독립적
  [revise_prompt]           → prompt_engineer  # 독립적
  [max_iterations]          → END
  [budget_exceeded]         → END (human_review_required=true)
```

**Cascade 규칙**:
```python
INVALIDATION_CASCADE = {
    "story_writer":     ["stitch_planner", "copywriter", "prompt_engineer"],
    "stitch_planner":   ["prompt_engineer"],  # method 변경 → 프롬프트 재생성
    "copywriter":       [],                    # 카피는 독립적
    "prompt_engineer":  [],                    # 프롬프트는 독립적
}
```

---

## 5. 상태 구조

```python
class VideoAgentState(TypedDict):
    # Input
    account_id: str
    intent: str
    services: list[str]
    platforms: list[str]

    # Context
    identity: dict
    account_config: dict            # ⭐ NEW: visual_settings, channels 포함
    weekly_slot: dict | None

    # ⭐ 마케팅 레이어 확장 포인트
    campaign_context: dict | None      # 시리즈/캠페인 맥락
    performance_hints: list[str]       # 과거 성과 기반 힌트
    experiment_vars: dict | None       # A/B 테스트 변수

    # Planning
    visual_anchor: str
    shots: list[dict]               # ShotDraft 리스트

    # Production (Stitch Planner 출력) - ⭐ prompt_engineer보다 먼저 실행
    generation_methods: list[str]
    continuity_refs: ContinuityRefs
    stitch_plan: StitchPlan
    asset_manifest: AssetManifest

    # Copy (copywriter와 prompt_engineer 병렬 실행)
    hook: str
    captions: list[str]
    cta: str
    overlay_texts: list[str]

    # Prompt (generation_method 기반 생성)
    image_prompts: list[str]
    video_prompts: list[str]
    negative_prompts: list[str]

    # Review
    quality_score: float
    quality_issues: list[str]
    feedback_notes: list[str]
    revision_target: str | None

    # Control
    iteration_count: int
    approved: bool
    human_review_required: bool

    # ⭐ NEW: 비용 추적
    llm_calls: int                  # 총 LLM 호출 횟수
    token_budget: int               # 최대 허용 토큰 (기본: 50000)
```

---

## 6. 데이터 계약

### 6.1 ShotDraft

```python
ShotDraft = {
    "shot_id": str,
    "purpose": str,              # 샷의 목적
    "emotional_beat": str,       # 감정 포인트
    "scene_description": str,    # 장면 설명
    "subject": str,              # 피사체
    "setting": str,              # 배경/세팅
    "lighting": str,             # 조명
    "camera_intent": str,        # 카메라 의도
    "motion_type": str,          # 모션 타입
    "continuity_constraints": list[str],  # 연속성 제약
    "narrative_transition": str | None,   # ⭐ 샷 간 서사 전환 의도
    # "contrast_shift" | "emotional_continuity" | "time_passage" | "reveal"
    "overlay_text_needed": bool,
    "generation_method": str | None,  # pure_video | keyframe_motion | image_stitch
    "risk_flags": list[str],
}
```

### 6.2 StitchPlan

```python
StitchPlan = {
    "strategy": str,                    # "sequential" | "parallel" | "hybrid"
    "segments": list[StitchSegment],    # 각 세그먼트 정의
    "total_duration_sec": float,
    "transition_style": str,            # "crossfade" | "cut" | "morph" | "wipe"
}

StitchSegment = {
    "segment_id": str,
    "shot_ids": list[str],              # 이 세그먼트에 포함된 샷들
    "method": str,                      # "pure_video" | "keyframe_motion" | "image_stitch"
    "transition_in": str,               # "crossfade" | "cut" | "morph" | "fade"
    "transition_out": str,
    "duration_sec": float,
    "assets_required": list[str],       # ["image_001.png", "video_002.mp4", ...]
    "processing_notes": str,            # 생성 시 주의사항
}
```

### 6.3 ContinuityRefs

```python
ContinuityRefs = {
    "character": {
        "description": str,             # "young woman, black hair, casual wear"
        "key_features": list[str],      # ["glasses", "minimal makeup"]
    },
    "setting": {
        "primary": str,                 # "bedroom, 3AM, moonlight"
        "secondary": str | None,        # "living room, warm lamp"
    },
    "lighting": {
        "type": str,                    # "moonlight", "warm lamp", "natural"
        "color_temp": str,              # "cool blue", "warm orange"
        "intensity": str,               # "dim", "soft", "bright"
    },
    "color_palette": list[str],         # ["#1a1a2e", "#16213e", "#0f3460"]
}
```

### 6.4 AssetManifest

```python
AssetManifest = list[AssetItem]

AssetItem = {
    "asset_id": str,                    # "img_001", "vid_001"
    "type": str,                        # "image" | "video" | "audio"
    "shot_ids": list[str],              # 사용되는 샷들
    "generation_service": str,          # "runway" | "luma" | "midjourney"
    "prompt_ref": str,                  # image_prompts 또는 video_prompts의 인덱스
    "status": str,                      # "pending" | "generated" | "failed"
    "file_path": str | None,            # 생성 후 파일 경로
}
```

---

## 7. 파일 구조

```
picko/video/
├── agents/
│   ├── __init__.py
│   ├── graph.py              # LangGraph 상태머신
│   ├── state.py              # VideoAgentState
│   ├── schemas.py            # ShotDraft 등
│   │
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── story_writer.py
│   │   ├── copywriter.py
│   │   ├── prompt_engineer.py
│   │   ├── stitch_planner.py
│   │   ├── reviewer.py
│   │   └── orchestrator.py
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py           # BaseTool
│   │   ├── story.py
│   │   ├── copy.py
│   │   ├── prompt.py
│   │   ├── stitch.py         # NEW
│   │   ├── review.py
│   │   └── orchestrate.py
│   │
│   └── prompts/
│       ├── story_writer.md
│       ├── copywriter.md
│       ├── prompt_engineer.md
│       ├── stitch_planner.md
│       ├── reviewer.md
│       └── orchestrator.md
```

---

## 8. 기존 시스템 통합

```python
class VideoGenerator:
    def __init__(self, ..., use_multi_agent: bool = True):
        self.use_multi_agent = use_multi_agent

    def generate(self) -> VideoPlan:
        if self.use_multi_agent:
            return self._generate_with_agents()
        return self._generate_legacy()
```

### 재사용 컴포넌트

- `picko/video/prompt_templates.py` - SERVICE_CONFIGS
- `picko/video/quality_scorer.py` - 품질 평가 로직
- `picko/account_context.py` - identity, weekly_slot
- `picko/llm_client.py` - get_writer_client()

### 8.1 VideoPlan 확장 전략

현재 `VideoPlan`/`VideoShot`에는 stitch 관련 필드가 없다. `VideoAgentState → VideoPlan` 변환 시 다음 중 하나를 선택해야 한다:

**옵션 A: VideoPlan 모델 확장 (권장)**

```python
# picko/video_plan.py 수정
@dataclass
class VideoPlan:
    # ... 기존 필드 ...

    # NEW: Production fields
    stitch_plan: StitchPlan | None = None
    asset_manifest: list[AssetItem] = field(default_factory=list)
    generation_methods: list[str] = field(default_factory=list)

@dataclass
class VideoShot:
    # ... 기존 필드 ...

    # NEW: Production metadata
    generation_method: str = ""  # pure_video | keyframe_motion | image_stitch
    continuity_notes: str = ""
```

**옵션 B: 별도 산출물로 분리**

```python
# 새 파일: picko/video/production_plan.py
@dataclass
class ProductionPlan:
    video_plan_id: str
    stitch_plan: StitchPlan
    asset_manifest: AssetManifest
    generation_methods: list[str]

# VideoGenerator.generate() returns tuple
def generate(self) -> tuple[VideoPlan, ProductionPlan]:
    ...
```

**결정**: 옵션 A 선택. 이유:
1. 기존 코드가 `VideoPlan`만 반환하도록 작성됨
2. JSON 직렬화/역직렬화가 이미 구현되어 있음
3. `to_markdown()` 출력에 자연스럽게 포함 가능

---

## 9. 구현 단계

### Phase 1. Foundation
- [ ] `agents/` 디렉토리 구조 생성
- [ ] `VideoAgentState` TypedDict 정의
- [ ] `ShotDraft` 스키마 정의
- [ ] LangGraph 기본 graph 구축
- [ ] Legacy fallback 유지

### Phase 2. Core Production Flow
- [ ] `story_writer` node + tools
- [ ] `prompt_engineer` node + tools
- [ ] `stitch_planner` node + tools ⭐
- [ ] 선형 flow 구현
- [ ] 최소 `reviewer` 추가

### Phase 3. Copy & Review Loop
- [ ] `copywriter` node + tools
- [ ] `reviewer` 고도화 (4개 tools)
- [ ] `orchestrator` node + tools
- [ ] Selective retry 구현

### Phase 4. Integration
- [ ] `VideoGenerator` 연동
- [ ] `_state_to_plan()` 변환 로직
- [ ] 기존 scorer와 결합
- [ ] Dry-run 지원

### Phase 5. Testing & Polish
- [ ] Tool 단위 테스트
- [ ] Graph 통합 테스트
- [ ] Retry path 테스트
- [ ] Legacy compatibility 테스트

---

## 10. 검증 기준

### 성공 조건

- 최소 1개의 `visual_anchor` 생성
- 샷 구조가 유효해야 함
- 카피와 프롬프트가 샷과 연결되어야 함
- 각 shot에 생성 방식이 지정되어야 함
- stitch plan 또는 pure video plan이 있어야 함
- reviewer가 승인 또는 수정 사유를 명확히 출력
- 최대 반복 횟수 내 종료

### 테스트

```bash
pytest tests/video/agents/ -v
```

```python
from picko.video.agents.graph import VideoAgentGraph

graph = VideoAgentGraph()
result = graph.generate(
    account_id="dawn_mood_call",
    intent="ad",
    services=["runway"],
    platforms=["instagram_reel"],
)

print(f"Approved: {result['approved']}")
print(f"Shots: {len(result['shots'])}")
print(f"Asset Manifest: {result['asset_manifest']}")
```

---

## 11. 설정 파일

```yaml
# config/video_agents.yml
defaults:
  quality_threshold: 70
  max_iterations: 3
  # ⭐ 개선: 승인 시 항상 리뷰가 아닌, 낮은 점수일 때만 리뷰
  human_review_on_low_score: true
  human_review_threshold: 60        # 60점 이하면 human review
  auto_approve_threshold: 85        # 85점 이상이면 자동 승인

agents:
  story_writer:
    temperature: 0.7
    max_tokens: 2000
  copywriter:
    temperature: 0.8
    max_tokens: 1500
  prompt_engineer:
    temperature: 0.3
    max_tokens: 3000
  stitch_planner:
    temperature: 0.2
    max_tokens: 2000
  reviewer:
    temperature: 0.2
    max_tokens: 1500
  orchestrator:
    temperature: 0.0
    max_tokens: 500
```

### 11.1 프롬프트 파일 스펙

각 에이전트의 프롬프트 파일(`prompts/*.md`)은 다음 구조를 따른다:

```markdown
# {에이전트명} 프롬프트

## Role
{에이전트의 역할 설명}

## Context Variables
- {{variable_name}}: {설명}

## Input Format
{입력 JSON 스키마}

## Output Format
{출력 JSON 스키마}

## Guidelines
1. {지침 1}
2. {지침 2}

## Examples
### Example 1
Input: {...}
Output: {...}
```

**Temperature와의 관계**:
- `temperature: 0.0-0.3`: 정확성 중시, 일관된 출력 (Reviewer, Orchestrator, Prompt Engineer)
- `temperature: 0.4-0.7`: 균형, 약간의 창의성 (Story Writer)
- `temperature: 0.7-1.0`: 창의성 중시, 다양한 표현 (Copywriter)

---

## 12. Critical Files

| 파일 | 용도 |
|------|------|
| `picko/video/agents/graph.py` | LangGraph 상태머신 (핵심) |
| `picko/video/agents/state.py` | VideoAgentState 정의 |
| `picko/video/agents/schemas.py` | ShotDraft 스키마 |
| `picko/video/agents/nodes/stitch_planner.py` | ⭐ 새로운 핵심 에이전트 |
| `picko/video/agents/tools/stitch.py` | 스티치 관련 도구들 |
| `picko/video/generator.py` | 통합 진입점 |

---

## 14. 구현 상세

### 14.1 에러 처리 전략

각 노드에 `safe_node` 래퍼 적용:

```python
# nodes/base.py
def safe_node(func):
    """노드 실행 래퍼 — LLM 실패 시 상태에 에러 기록"""
    def wrapper(state: VideoAgentState) -> dict:
        try:
            return func(state)
        except Exception as e:
            node_name = func.__name__.replace("_node", "")
            logger.error(f"{node_name} failed: {e}")
            return {
                "quality_issues": state.get("quality_issues", []) + [f"{node_name} 실행 실패: {e}"],
                "revision_target": node_name,
            }
    return wrapper

@safe_node
def story_writer_node(state: VideoAgentState) -> dict:
    # ... 기존 로직
```

Orchestrator 입력 검증:

```python
def _validate_state_completeness(state: VideoAgentState) -> list[str]:
    """필수 필드가 비어있으면 해당 에이전트를 재실행 대상으로"""
    missing = []
    if not state.get("visual_anchor"):
        missing.append("story_writer")
    if not state.get("shots"):
        missing.append("story_writer")
    if not state.get("generation_methods"):
        missing.append("stitch_planner")
    if not state.get("video_prompts") and not state.get("image_prompts"):
        missing.append("prompt_engineer")
    return missing
```

### 14.2 Reviewer와 기존 Scorer 통합

Reviewer 노드에서 임시 VideoPlan 구성 후 기존 scorer 호출:

```python
# nodes/reviewer.py
from picko.video.quality_scorer import VideoPlanScorer

def _build_temp_plan(state: VideoAgentState) -> VideoPlan:
    """state에서 임시 VideoPlan 구성 (scorer 호출용)"""
    shots = []
    for i, shot_draft in enumerate(state["shots"]):
        shot = VideoShot(
            index=i + 1,
            duration_sec=shot_draft.get("duration_sec", 5),
            shot_type=shot_draft.get("purpose", "main"),
            script=shot_draft.get("scene_description", ""),
            caption=state["captions"][i] if i < len(state["captions"]) else "",
            background_prompt=state["video_prompts"][i] if i < len(state["video_prompts"]) else "",
        )
        _attach_service_params(shot, state, i)
        shots.append(shot)

    return VideoPlan(
        id="temp_review",
        account=state["account_id"],
        intent=state["intent"],
        goal="",
        source=VideoSource(type="account_only"),
        brand_style=BrandStyle(tone=""),
        shots=shots,
        target_services=state["services"],
        platforms=state["platforms"],
    )

def review_node(state: VideoAgentState) -> dict:
    temp_plan = _build_temp_plan(state)

    # 기존 scorer 재사용
    scorer = VideoPlanScorer()
    score = scorer.score(temp_plan, state["services"])

    # 멀티에이전트 전용 추가 검수
    production_issues = _review_production_fit(state)

    return {
        "quality_score": score.overall,
        "quality_issues": score.issues + production_issues,
        "feedback_notes": score.suggestions,
    }
```

### 14.3 ShotDraft → VideoShot 매핑

VideoShot에 필드 추가 대신 `notes` dict 활용:

```python
def _shot_draft_to_video_shot(draft: dict, index: int, state: VideoAgentState) -> VideoShot:
    shot = VideoShot(
        index=index,
        duration_sec=draft.get("duration_sec", 5),
        shot_type=draft.get("purpose", "main"),
        script=draft.get("scene_description", ""),
        caption=state["captions"][index - 1] if index <= len(state["captions"]) else "",
        background_prompt=state["video_prompts"][index - 1] if index <= len(state["video_prompts"]) else "",
        transition_in=_get_transition(state["stitch_plan"], index, "in"),
        transition_out=_get_transition(state["stitch_plan"], index, "out"),
    )

    # 에이전트 메타데이터를 notes에 보존
    shot.notes = {
        "emotional_beat": draft.get("emotional_beat", ""),
        "generation_method": draft.get("generation_method", ""),
        "risk_flags": ",".join(draft.get("risk_flags", [])),
        "continuity": ",".join(draft.get("continuity_constraints", [])),
    }

    return shot
```

### 14.4 프롬프트 파일 로딩

기존 `prompt_loader.py` 확장:

```python
# agents/prompts/loader.py
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

def load_agent_prompt(agent_name: str) -> str:
    """에이전트 시스템 프롬프트 로드"""
    path = PROMPTS_DIR / f"{agent_name}.md"
    return path.read_text(encoding="utf-8")
```

각 노드에서 사용:

```python
from picko.video.agents.prompts.loader import load_agent_prompt

def story_writer_node(state):
    system_prompt = load_agent_prompt("story_writer")
    client = get_writer_client()
    result = client.generate(
        user_prompt,
        system_prompt=system_prompt,
        temperature=0.7
    )
```

### 14.5 Account Config 전달

그래프 초기화 시 전체 account YAML 로드:

```python
# graph.py
from picko.config import get_config

def _init_state(account_id: str, **kwargs) -> VideoAgentState:
    config = get_config()
    account_config = config.get_account(account_id)  # dawn_mood_call.yml 전체
    identity = get_identity(account_id)

    return VideoAgentState(
        account_id=account_id,
        identity=identity.__dict__ if identity else {},
        account_config=account_config or {},  # visual_settings, channels 포함
        # ...
    )
```

Story Writer 프롬프트에서 활용:

```markdown
<!-- prompts/story_writer.md -->
## 비주얼 설정
- 레이아웃 프리셋: {{account_config.visual_settings.default_layout_preset}}
- 채널 톤: {{account_config.channels.instagram.tone}}

이 설정에 맞는 visual anchor를 생성하세요.
```

### 14.6 비용/토큰 관리

Orchestrator가 매 반복마다 예산 확인:

```python
# config/video_agents.yml
defaults:
  token_budget: 50000  # 약 $0.50 (claude sonnet 기준)

def enforce_budget(state: VideoAgentState) -> bool:
    """예산 초과 시 human_review로 전환"""
    return state["llm_calls"] < state.get("token_budget", 50000)
```

### 14.7 LangGraph 의존성

```bash
uv add langgraph
```

Phase 1 체크리스트에 추가:

```yaml
Phase 1. Foundation:
  - [ ] uv add langgraph
  - [ ] `agents/` 디렉토리 구조 생성
  # ...
```

---

## 15. 변경 이력

### v3 (P0-P3 구현 가이드 반영)

| 항목 | v2 | v3 (구현 가이드) |
|------|-----|-----------------|
| SERVICE_CONSTRAINTS 참조 | 없음 | `select_generation_method`에서 직접 조회 |
| 에이전트 순서 (fan-out) | 순차 | **copywriter + prompt_engineer 병렬** (LangGraph fan-out) |
| Cascade invalidation | 없음 | `INVALIDATION_CASCADE` 규칙 추가 |
| 에러 처리 | 없음 | `safe_node` 래퍼 + 입력 검증 |
| Reviewer-Scorer 통합 | 없음 | 임시 VideoPlan 구성 후 기존 Scorer 재사용 |
| ShotDraft → VideoShot 매핑 | 없음 | `notes` dict에 메타데이터 보존 |
| 비용 추적 | 없음 | `llm_calls`, `token_budget` 필드 추가 |
| 프롬프트 로더 | 없음 | `prompts/loader.py` (기존 prompt_loader 확장) |
| account_config | 없음 | `visual_settings`, `channels` 포함 |
| LangGraph 의존성 | 미포함 | `uv add langgraph` 명시 |

### v2 (리뷰 반영)

| 항목 | v1 | v2 (리뷰 반영) |
|------|-----|----------------|
| 마케팅 확장 포인트 | 없음 | `campaign_context`, `performance_hints`, `experiment_vars` 추가 |
| 에이전트 순서 | prompt → stitch | **stitch → prompt** (제작 방식 먼저 결정) |
| StitchPlan 계약 | `dict` (느슨함) | `StitchPlan`, `StitchSegment` 명시적 계약 |
| AssetManifest 계약 | `list[dict]` | `AssetItem` 명시적 계약 |
| ContinuityRefs | 없음 | 캐릭터/배경/조명/색상 명시적 정의 |
| human_review 로직 | 승인 시 항상 | **낮은 점수일 때만** (threshold 기반) |
| 프롬프트 파일 스펙 | 없음 | 각 에이전트별 `.md` 파일 구조 정의 |
| VideoPlan 확장 전략 | 불명확 | 옵션 A (모델 확장) 선택 및 명시화 |

### v1 (초안)

| 항목 | 이전 | v1 |
|------|------|-----|
| 에이전트 수 | 4개 | 6개 |
| Director | 1개 | Reviewer + Orchestrator로 분리 |
| Stitch Planner | 없음 | ⭐ 추가 (핵심) |
| 상태 필드 | 기본 | production 관련 필드 추가 |
| 구현 단계 | 4단계 | 5단계 (세분화) |
| 범위 | 모호 | 1단계: 비디오 제작만 명확히 한정 |
