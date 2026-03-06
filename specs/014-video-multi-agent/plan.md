# 014-video-multi-agent Implementation Plan

## Overview

스펙 문서 `specs/014-video-multi-agent/spec.md` 기반 구현 계획

---

## Phase 1: Foundation (2-3일)

### 1.1 의존성 설치
```bash
uv add langgraph
```

### 1.2 디렉토리 구조 생성
```bash
mkdir -p picko/video/agents/nodes
mkdir -p picko/video/agents/tools
mkdir -p picko/video/agents/prompts
touch picko/video/agents/__init__.py
touch picko/video/agents/nodes/__init__.py
touch picko/video/agents/tools/__init__.py
touch picko/video/agents/prompts/__init__.py
```

### 1.3 상태/스키마 정의

**파일**: `picko/video/agents/state.py`
```python
from typing import TypedDict

class VideoAgentState(TypedDict):
    # Input
    account_id: str
    intent: str
    services: list[str]
    platforms: list[str]

    # Context
    identity: dict
    account_config: dict  # visual_settings, channels
    weekly_slot: dict | None

    # Marketing extension
    campaign_context: dict | None
    performance_hints: list[str]
    experiment_vars: dict | None

    # Planning
    visual_anchor: str
    shots: list[dict]  # ShotDraft[]

    # Production
    generation_methods: list[str]
    continuity_refs: dict
    stitch_plan: dict
    asset_manifest: list[dict]

    # Copy
    hook: str
    captions: list[str]
    cta: str
    overlay_texts: list[str]

    # Prompt
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
    llm_calls: int
    token_budget: int
```

**파일**: `picko/video/agents/schemas.py`
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ShotDraft:
    shot_id: str
    purpose: str
    emotional_beat: str
    scene_description: str
    subject: str
    setting: str
    lighting: str
    camera_intent: str
    motion_type: str
    continuity_constraints: list[str] = field(default_factory=list)
    overlay_text_needed: bool = False
    generation_method: str | None = None
    risk_flags: list[str] = field(default_factory=list)

@dataclass
class StitchSegment:
    segment_id: str
    shot_ids: list[str]
    method: str  # pure_video | keyframe_motion | image_stitch
    transition_in: str
    transition_out: str
    duration_sec: float
    assets_required: list[str] = field(default_factory=list)
    processing_notes: str = ""

@dataclass
class StitchPlan:
    strategy: str  # sequential | parallel | hybrid
    segments: list[StitchSegment]
    total_duration_sec: float
    transition_style: str  # crossfade | cut | morph | wipe

@dataclass
class AssetItem:
    asset_id: str
    type: str  # image | video | audio
    shot_ids: list[str]
    generation_service: str
    prompt_ref: str
    status: str  # pending | generated | failed
    file_path: str | None = None
```

### 1.4 BaseTool 클래스
**파일**: `picko/video/agents/tools/base.py`
```python
from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def invoke(self, *args, **kwargs) -> Any:
        pass
```

### 1.5 LangGraph 기본 구조
**파일**: `picko/video/agents/graph.py`
```python
from langgraph.graph import StateGraph, END

from picko.video.agents.state import VideoAgentState

def build_video_agent_graph():
    builder = StateGraph(VideoAgentState)

    # Nodes
    builder.add_node("story_writer", story_writer_node)
    builder.add_node("stitch_planner", stitch_planner_node)
    builder.add_node("copywriter", copywriter_node)
    builder.add_node("prompt_engineer", prompt_engineer_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("orchestrator", orchestrator_node)

    # Entry
    builder.set_entry_point("story_writer")

    # Linear flow
    builder.add_edge("story_writer", "stitch_planner")

    # Fan-out (parallel)
    builder.add_edge("stitch_planner", "copywriter")
    builder.add_edge("stitch_planner", "prompt_engineer")

    # Fan-in
    builder.add_edge("copywriter", "reviewer")
    builder.add_edge("prompt_engineer", "reviewer")

    # Conditional routing
    builder.add_conditional_edges(
        "orchestrator",
        route_by_revision,
        {
            "approved": END,
            "revise_story": "story_writer",
            "revise_stitch": "stitch_planner",
            "revise_copy": "copywriter",
            "revise_prompt": "prompt_engineer",
        }
    )

    return builder

class VideoAgentGraph:
    def __init__(self):
        self.graph = build_video_agent_graph()
        self.compiled = self.graph.compile()

    def generate(self, account_id: str, **kwargs) -> VideoAgentState:
        # ... implementation
```

### 1.6 검증
- [ ] `VideoAgentState` 타입 체크
- [ ] `ShotDraft` 직렬화/역직렬화
- [ ] LangGraph 컴파일

---

## Phase 2: Core Production Flow (3-4일)

### 2.1 Story Writer Node
**파일**: `picko/video/agents/nodes/story_writer.py`

**Tools** (`tools/story.py`):
- `analyze_intent` (규칙) - Intent별 샷 구조 매핑
- `generate_anchor` (LLM) - visual_anchor 생성
- `plan_shots` (LLM) - shot sequence 생성

### 2.2 Stitch Planner Node ⭐
**파일**: `picko/video/agents/nodes/stitch_planner.py`

**Tools** (`tools/stitch.py`):
- `select_generation_method` - SERVICE_CONSTRAINTS 참조
- `build_continuity_refs`
- `plan_stitch_sequence`
- `build_asset_manifest`

**핵심 구현**:
```python
# tools/stitch.py
from picko.video.constraints import SERVICE_CONSTRAINTS

def select_generation_method(shot: ShotDraft, services: list[str]) -> str:
    """shot + 서비스 제약을 보고 생성 방식 결정"""
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

### 2.3 Prompt Engineer Node
**파일**: `picko/video/agents/nodes/prompt_engineer.py`

**Tools** (`tools/prompt.py`):
- `build_service_prompt` - generation_method 기반
- `create_keyframe_prompt`
- `apply_negative_prompt`

### 2.4 Reviewer Node (기본)
**파일**: `picko/video/agents/nodes/reviewer.py`

- 기존 `VideoPlanScorer` 재사용
- `_build_temp_plan()` 함수

### 2.5 검증
- [ ] story_writer → visual_anchor, shots 생성
- [ ] stitch_planner → generation_methods 결정
- [ ] prompt_engineer → 프롬프트 생성

---

## Phase 3: Copy & Review Loop (3-4일)

### 3.1 Copywriter Node
**파일**: `picko/video/agents/nodes/copywriter.py`

**Tools** (`tools/copy.py`):
- `create_hook` (LLM)
- `generate_caption` (LLM)
- `write_cta` (LLM)

### 3.2 Reviewer 고도화
- `check_consistency` (규칙)
- `validate_brand` (규칙)
- `review_structure` (LLM)
- `review_production_fit` (LLM)

### 3.3 Orchestrator Node
**파일**: `picko/video/agents/nodes/orchestrator.py`

**구현 사항**:
```python
# Cascade invalidation 규칙
INVALIDATION_CASCADE = {
    "story_writer":     ["stitch_planner", "copywriter", "prompt_engineer"],
    "stitch_planner":   ["prompt_engineer"],
    "copywriter":       [],
    "prompt_engineer":  [],
}

def decide_next_step(revision_target: str) -> list[str]:
    """재호출 대상 + cascade 대상 반환"""
    targets = [revision_target] + INVALIDATION_CASCADE.get(revision_target, [])
    return targets

def invalidate_downstream(state: VideoAgentState, targets: list[str]) -> VideoAgentState:
    """재실행 대상의 출력 필드를 초기화"""
    field_map = {
        "story_writer":     ["visual_anchor", "shots"],
        "stitch_planner":   ["generation_methods", "stitch_plan", "asset_manifest", "continuity_refs"],
        "copywriter":       ["hook", "captions", "cta", "overlay_texts"],
        "prompt_engineer":  ["image_prompts", "video_prompts", "negative_prompts"],
    }
    for target in targets:
        for field in field_map.get(target, []):
            state[field] = type(state[field])()
    return state
```

### 3.4 Conditional Routing
```python
def route_by_revision(state: VideoAgentState) -> str:
    if state["approved"]:
        return "approved"
    if state["iteration_count"] >= state.get("max_iterations", 3):
        return "approved"

    revision = state.get("revision_target")
    if revision == "story_writer":
        return "revise_story"
    elif revision == "stitch_planner":
        return "revise_stitch"
    # ...
    return "approved"
```

### 3.5 검증
- [ ] copywriter → hook, captions, cta 생성
- [ ] reviewer → quality_score, issues 생성
- [ ] orchestrator → cascade invalidation 동작
- [ ] revision 루프 테스트

---

## Phase 4: Integration (2-3일)

### 4.1 VideoGenerator 수정
**파일**: `picko/video/generator.py`
```python
def generate(self, validate: bool = True) -> VideoPlan:
    if self.use_multi_agent:
        return self._generate_with_agents(validate)
    return self._generate_legacy(validate)

def _generate_with_agents(self, validate: bool) -> VideoPlan:
    graph = VideoAgentGraph()
    result = graph.generate(
        account_id=self.account_id,
        intent=self.intent,
        services=self.services,
        platforms=self.platforms,
        week_of=self.week_of,
    )
    return self._state_to_plan(result)
```

### 4.2 _state_to_plan() 구현
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
    # 메타데이터 보존
    shot.notes = {
        "emotional_beat": draft.get("emotional_beat", ""),
        "generation_method": draft.get("generation_method", ""),
        "risk_flags": ",".join(draft.get("risk_flags", [])),
        "continuity": ",".join(draft.get("continuity_constraints", [])),
    }
    return shot
```

### 4.3 VideoPlan 확장
**파일**: `picko/video_plan.py`
```python
@dataclass
class VideoPlan:
    # ... existing fields ...

    # NEW
    stitch_plan: StitchPlan | None = None
    asset_manifest: list[dict] = field(default_factory=list)
    generation_methods: list[str] = field(default_factory=list)
```

### 4.4 Dry-run 지원
- `dry_run=True` 시 LLM 호출 없이 더미 데이터 반환

### 4.5 검증
- [ ] 기존 테스트 통과
- [ ] `_generate_legacy()` 동작 유지
- [ ] `_generate_with_agents()` 결과 검증

---

## Phase 5: Testing & Polish (2-3일)

### 5.1 단위 테스트
**파일**: `tests/video/agents/`

- `test_state.py` - 상태 직렬화/역직렬화
- `test_schemas.py` - ShotDraft, StitchPlan 검증
- `test_tools_story.py` - Story Writer 도구들
- `test_tools_stitch.py` - Stitch Planner 도구들
- `test_tools_copy.py` - Copywriter 도구들
- `test_tools_prompt.py` - Prompt Engineer 도구들

### 5.2 통합 테스트
- `test_graph.py` - 전체 흐름 테스트
- `test_revision_loop.py` - 재시도 루프 테스트
- `test_integration.py` - VideoGenerator 통합

### 5.3 에러 처리 테스트
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
```

### 5.4 비용 추적
```python
def enforce_budget(state: VideoAgentState) -> bool:
    """예산 초과 시 human_review로 전환"""
    return state["llm_calls"] < state.get("token_budget", 50000)
```

### 5.5 검증
- [ ] `pytest tests/video/agents/ -v` 통과
- [ ] 커버리지 80% 이상

---

## Critical Files Summary

| 파일 | Phase | 설명 |
|------|-------|------|
| `picko/video/agents/state.py` | 1 | VideoAgentState 정의 |
| `picko/video/agents/schemas.py` | 1 | ShotDraft, StitchPlan 등 |
| `picko/video/agents/graph.py` | 1-3 | LangGraph 상태머신 |
| `picko/video/agents/nodes/story_writer.py` | 2 | Story Writer 에이전트 |
| `picko/video/agents/nodes/stitch_planner.py` | 2 | ⭐ 핵심 에이전트 |
| `picko/video/agents/nodes/orchestrator.py` | 3 | 흐름 제어 |
| `picko/video/agents/tools/stitch.py` | 2 | 스티치 도구들 |
| `picko/video/generator.py` | 4 | 통합 진입점 |
| `picko/video_plan.py` | 4 | VideoPlan 확장 |

---

## Dependencies

```bash
# pyproject.toml
langgraph = "^0.2.0"
```

---

## Verification Commands

```bash
# Phase 1
pytest tests/video/agents/test_state.py -v
pytest tests/video/agents/test_schemas.py -v

# Phase 2-3
pytest tests/video/agents/test_tools_*.py -v
pytest tests/video/agents/test_nodes.py -v

# Phase 4-5
pytest tests/video/agents/test_graph.py -v
pytest tests/video/agents/test_integration.py -v

# Full suite
pytest tests/video/agents/ -v --cov=picko.video.agents
```

---

## Risk Mitigation

| 위험 | 대응 |
|-----|------|
| LangGraph API 변경 | 공식 문서 기반, 최신 버전 사용 |
| LLM 응답 불안정 | `safe_node` 래퍼 + 재시도 로직 |
| 기존 코드 호환성 | `use_multi_agent=False` 로 legacy 유지 |
| 토큰 비용 초과 | `token_budget` + `enforce_budget()` |

---

## Next Actions

1. **Phase 1 시작**: 디렉토리 구조 생성 + 의존성 설치
2. **상태/스키마 정의**: `state.py`, `schemas.py` 작성
3. **기본 그래프 구조**: `graph.py` 작성
