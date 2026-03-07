# 014-video-multi-agent Implementation Plan (v2)

## Overview

스펙 문서 `specs/014-video-multi-agent/spec.md` v4 기반 구현 계획.

**v2 핵심 변경사항**:
- shot_id 기반 상태 스키마 (배열 인덱스 제거)
- recipe-based production (2단 레시피 선택)
- Reviewer 3단 분리 (Plan / Artifact / Human Gate)
- Audio Director 추가
- TerminalStatus enum (boolean 조합 제거)
- 구조화된 이슈 코드 (키워드 매칭 제거)
- CreativeBrief 입력 스키마
- Provider/Service/Platform 3층 출력
- manual_assisted -> API 전환 설계

---

## Design Decisions (구현 전 확정된 설계 결정)

### D1. Fan-out / Fan-in 동작 방식

LangGraph StateGraph에서 stitch_planner 이후 copywriter, prompt_engineer, audio_director가 **3-way fan-out**으로 병렬 실행. plan_reviewer는 세 predecessor가 모두 완료된 후 1회만 실행.

병렬 노드가 동일 필드에 쓰는 경우 reducer 필요:
- `llm_calls_used`: `Annotated[int, operator.add]`
- `tokens_used_estimate`: `Annotated[int, operator.add]`
- `cost_usd_estimate`: `Annotated[float, operator.add]`
- 나머지 필드는 각 노드가 전담하므로 충돌 없음

### D2. State 필드 소유권

| 필드 | 설정 주체 | 시점 |
|------|----------|------|
| `plan_review`, `revision_issues` | Plan Reviewer | 매 review 후 |
| `terminal_status`, `iteration_count` | Orchestrator | 매 routing 전 |
| `llm_calls_used`, `tokens_used_estimate`, `cost_usd_estimate` | 각 노드 (반환 dict) | LLM 호출 직후 |
| `artifact_review` | Artifact Reviewer | 렌더 결과 업로드 후 |

Plan Reviewer는 **평가만**. 승인/거절 결정은 Orchestrator 전담.

### D3. Cascade Invalidation = 필드 초기화 (clear)

"invalidate" = 해당 에이전트 출력 필드를 `{}` / `""` / `None`으로 초기화.
이전 결과 보존 없음. 재실행하면 처음부터 생성.

`revise_story` 시 실행 순서:
```
story_writer -> stitch_planner -> copywriter || prompt_engineer || audio_director
```

### D4. Orchestrator 결정 로직

```
Orchestrator 결정 (TerminalStatus 기반):
  if cost_usd >= budget:        -> BLOCKED (비용 초과)
  if score >= auto_threshold:   -> AUTO_APPROVED
  if score <= human_threshold:  -> NEEDS_HUMAN_REVIEW
  if iterations >= max:         -> MAX_ITERATIONS_REACHED
  if 60 < score < 85:          -> REVISE_REQUIRED (issues 기반 dispatch)
  hard fail (brand violation):  -> REVISE_REQUIRED (story_writer 필수)
```

### D5. shot_id 기반 데이터 정합성

**모든 shot-level 데이터는 shot_id를 키로 사용한다.**

| Dict | 보장 주체 |
|------|----------|
| `shots_by_id` | story_writer |
| `production_by_shot_id` | stitch_planner |
| `copy_by_shot_id` | copywriter |
| `prompts_by_shot_id` | prompt_engineer |
| `audio_by_shot_id` | audio_director |

`shot_order: list[str]`로 순서를 보존한다.

불변식: 모든 shot-level dict의 key set == set(shot_order)

### D6. Duration 출처

- 총 영상 길이: `creative_brief.target_duration_sec` (기본: 플랫폼별)
  - instagram_reel: 15s, tiktok: 30s, youtube_shorts: 60s
- story_writer가 shot별 `duration_sec` 초안 설정
- stitch_planner가 `total_duration_sec`에 맞게 조정

### D7. Revision Routing (구조화된 이슈 코드)

키워드 매칭 대신 `ReviewIssue.code` 프리픽스로 target agent를 결정:

```python
_CODE_AGENT_MAP = {
    "story.":       "story_writer",
    "continuity.":  "stitch_planner",
    "production.":  "stitch_planner",
    "copy.":        "copywriter",
    "prompt.":      "prompt_engineer",
    "audio.":       "audio_director",
}

def resolve_revision_targets(issues: list[ReviewIssue]) -> list[str]:
    """이슈 코드에서 target agents 추출 (우선순위: severity 순)"""
    sorted_issues = sorted(issues, key=lambda i: _SEVERITY_ORDER[i.severity])
    targets = []
    for issue in sorted_issues:
        for prefix, agent in _CODE_AGENT_MAP.items():
            if issue.code.startswith(prefix) and agent not in targets:
                targets.append(agent)
    return targets
```

다중 이슈 동시 처리: 가장 upstream인 agent부터 cascade 실행.

### D8. Error Handling

`safe_node` -> `revision_issues`에 에러 기록 -> plan_reviewer가 score=0 -> orchestrator가 REVISE_REQUIRED.
iteration으로 카운트되므로 max_iterations에 도달하면 종료.

### D9. manual_assisted 렌더 루프

Planning graph가 완료되면 `render_brief`를 출력한다.
사용자가 외부 도구(Sora 앱, Runway 앱 등)에서 렌더 후 결과 파일을 업로드.
Artifact Reviewer가 3층 QA를 수행. QA 통과 후 **Publish Reviewer (human gate)** 가 최종 게시 승인.

```
planning_graph.invoke() -> render_briefs
user renders externally
user uploads result
artifact_reviewer.invoke(result, plan) -> pass / fail_auto / fail_manual
  [pass]        -> publish_reviewer_node (human gate: 감성/브랜드/리스크 확인)
  [fail_auto]   -> 자동 재생성 제안 (bounded autonomy 항목만)
  [fail_manual] -> 사람 검토 요청
publish_reviewer_node -> PUBLISH_APPROVED / PUBLISH_BLOCKED
```

`publish_reviewer_node`는 **제거 불가 human gate**: 감성 여운, 브랜드 일관성, 리스크를 사람이 최종 확인.
상태에 `publish_status: str` 필드를 추가 (`"pending" | "approved" | "blocked"`).

API 전환 시: render_brief -> API executor -> artifact_reviewer -> publish_reviewer (계약 동일)

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

# node 파일
touch picko/video/agents/nodes/base.py
touch picko/video/agents/nodes/story_writer.py
touch picko/video/agents/nodes/copywriter.py
touch picko/video/agents/nodes/prompt_engineer.py
touch picko/video/agents/nodes/stitch_planner.py
touch picko/video/agents/nodes/audio_director.py
touch picko/video/agents/nodes/plan_reviewer.py
touch picko/video/agents/nodes/artifact_reviewer.py
touch picko/video/agents/nodes/orchestrator.py

# tool 파일
touch picko/video/agents/tools/base.py
touch picko/video/agents/tools/story.py
touch picko/video/agents/tools/copy.py
touch picko/video/agents/tools/prompt.py
touch picko/video/agents/tools/stitch.py
touch picko/video/agents/tools/audio.py
touch picko/video/agents/tools/review.py
touch picko/video/agents/tools/artifact_qa.py
touch picko/video/agents/tools/orchestrate.py

# prompt 파일
touch picko/video/agents/prompts/story_writer.md
touch picko/video/agents/prompts/copywriter.md
touch picko/video/agents/prompts/prompt_engineer.md
touch picko/video/agents/prompts/stitch_planner.md
touch picko/video/agents/prompts/audio_director.md
touch picko/video/agents/prompts/plan_reviewer.md
touch picko/video/agents/prompts/orchestrator.md

# provider registry
touch picko/video/agents/providers.py
```

### 1.3 상태/스키마 정의

**파일**: `picko/video/agents/state.py`
```python
import operator
from enum import Enum
from typing import Annotated, TypedDict


class TerminalStatus(str, Enum):
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    REVISE_REQUIRED = "revise_required"
    BLOCKED = "blocked"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


class VideoAgentState(TypedDict):
    # === Input ===
    account_id: str
    intent: str
    services: list[str]
    platforms: list[str]
    execution_mode: str                      # "manual_assisted" | "api"
    creative_brief: dict                     # CreativeBrief as dict

    # === Context ===
    identity: dict
    account_config: dict
    weekly_slot: dict | None

    # Marketing extension
    campaign_context: dict | None
    performance_hints: list[str]
    experiment_vars: dict | None

    # === Planning (shot_id 기반) ===
    visual_anchor: str
    shots_by_id: dict[str, dict]             # {shot_id: ShotDraft}
    shot_order: list[str]                    # shot_id 순서

    # === Production (shot_id 기반) ===
    production_by_shot_id: dict[str, dict]   # {shot_id: ProductionSpec}
    continuity_refs: dict                    # ContinuityRefs
    stitch_plan: dict                        # StitchPlan
    asset_manifest: list[dict]               # list[AssetItem]

    # === Copy (shot_id 기반) ===
    copy_by_shot_id: dict[str, dict]         # {shot_id: CopyBundle}

    # === Prompt (shot_id 기반) ===
    prompts_by_shot_id: dict[str, dict]      # {shot_id: PromptBundle}

    # === Audio (shot_id 기반) ===
    audio_by_shot_id: dict[str, dict]        # {shot_id: AudioSpec}

    # === Plan Review ===
    plan_review: dict                        # PlanReviewResult
    revision_issues: list[dict]              # list[ReviewIssue]

    # === Artifact Review ===
    artifact_review: dict | None             # ArtifactReviewResult

    # === Publish Review (human gate) ===
    publish_status: str                      # "pending" | "approved" | "blocked"

    # === Control ===
    terminal_status: str                     # TerminalStatus value
    iteration_count: int
    max_iterations: int
    auto_approve_threshold: float
    human_review_threshold: float

    # === Cost Tracking (분리된 메트릭) ===
    llm_calls_used: Annotated[int, operator.add]
    tokens_used_estimate: Annotated[int, operator.add]
    cost_usd_estimate: Annotated[float, operator.add]
    cost_budget_usd: float
```

**파일**: `picko/video/agents/schemas.py`
```python
from dataclasses import dataclass, field


@dataclass
class CreativeBrief:
    account_id: str
    intent: str                        # ad | explainer | brand | trend
    objective: str = ""
    audience: str = ""
    emotional_target: str = ""
    message_pillar: str = ""
    proof_points: list[str] = field(default_factory=list)
    product_surface: str = ""
    cta_policy: str = "soft"
    target_duration_sec: float = 15.0
    platforms: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    execution_mode: str = "manual_assisted"
    series_id: str | None = None
    brand_rules_ref: str | None = None


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
    duration_sec: float = 5.0
    continuity_constraints: list[str] = field(default_factory=list)
    narrative_transition: str | None = None
    overlay_text_needed: bool = False
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class RenderRecipe:
    image_service: str | None = None
    motion_service: str | None = None
    stitch_engine: str | None = None
    audio_strategy: str = "silent_visual"
    continuity_ref_source: str = ""


@dataclass
class ProductionSpec:
    shot_id: str
    production_mode: str               # pure_video | keyframe_motion | image_stitch | hybrid_segment
    render_recipe: RenderRecipe = field(default_factory=RenderRecipe)
    fallback_recipe: RenderRecipe | None = None


@dataclass
class CopyBundle:
    hook: str | None = None
    caption: str = ""
    cta: str | None = None
    overlay_text: str | None = None


@dataclass
class PromptBundle:
    video_prompt: str = ""
    image_prompt: str = ""
    negative_prompt: str = ""
    service_specific_params: dict = field(default_factory=dict)


@dataclass
class AudioSpec:
    audio_strategy: str = "silent_visual"
    voiceover_needed: bool = False
    voiceover_script: str | None = None
    silence_windows: list[tuple[float, float]] = field(default_factory=list)
    ambient_profile: str = ""
    bgm_profile: str = ""
    sfx_cues: list[dict] = field(default_factory=list)
    caption_timing_ref: str | None = None


@dataclass
class ReviewIssue:
    code: str                          # "continuity.lighting_drift"
    severity: str                      # "critical" | "high" | "medium" | "low"
    target_agents: list[str] = field(default_factory=list)
    shot_ids: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class StitchSegment:
    segment_id: str
    shot_ids: list[str]
    method: str
    transition_in: str
    transition_out: str
    duration_sec: float
    assets_required: list[str] = field(default_factory=list)
    processing_notes: str = ""


@dataclass
class StitchPlan:
    strategy: str
    segments: list[StitchSegment]
    total_duration_sec: float
    transition_style: str


@dataclass
class AssetItem:
    asset_id: str
    type: str                          # image | video | audio
    shot_ids: list[str]
    generation_service: str
    prompt_ref: str
    status: str = "pending"
    depends_on: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    file_path: str | None = None
```

**파일**: `picko/video/agents/providers.py`
```python
from dataclasses import dataclass, field


@dataclass
class ProviderCapability:
    provider_id: str
    display_name: str
    execution_modes: list[str]
    supported_ratios: list[str]
    supported_durations: list[float]
    max_duration_per_clip: float
    supports_start_image: bool
    supports_end_image: bool
    native_audio: bool
    post_audio_api: bool = False
    supports_reference_image: bool = False
    supports_first_last_frame: bool = False


PROVIDER_CAPABILITIES: dict[str, ProviderCapability] = {
    "sora_app": ProviderCapability(
        provider_id="sora_app",
        display_name="Sora (App)",
        execution_modes=["manual_assisted"],
        supported_ratios=["9:16", "16:9", "1:1"],
        supported_durations=[5, 10, 15, 20],
        max_duration_per_clip=20.0,
        supports_start_image=True,
        supports_end_image=False,
        native_audio=True,
        supports_reference_image=True,
    ),
    "sora_api": ProviderCapability(
        provider_id="sora_api",
        display_name="Sora (API)",
        execution_modes=["api"],
        supported_ratios=["9:16", "16:9", "1:1"],   # canonical; API 내부 해상도는 _normalize_ratio로 변환
        supported_durations=[4, 8, 12],
        max_duration_per_clip=12.0,
        supports_start_image=True,
        supports_end_image=False,
        native_audio=True,
        supports_reference_image=True,
    ),
    "veo_api": ProviderCapability(
        provider_id="veo_api",
        display_name="Veo 3.1 (API)",
        execution_modes=["api"],
        supported_ratios=["9:16", "16:9"],
        supported_durations=[4, 6, 8],
        max_duration_per_clip=8.0,
        supports_start_image=True,
        supports_end_image=False,
        native_audio=True,
        supports_reference_image=True,
        supports_first_last_frame=True,
    ),
    "runway_api": ProviderCapability(
        provider_id="runway_api",
        display_name="Runway Gen-4.5 (API)",
        execution_modes=["api"],
        supported_ratios=["9:16", "16:9", "1:1"],
        supported_durations=[5, 10],
        max_duration_per_clip=10.0,
        supports_start_image=True,
        supports_end_image=True,
        native_audio=False,
        post_audio_api=True,
        supports_reference_image=True,
    ),
    "runway_app": ProviderCapability(
        provider_id="runway_app",
        display_name="Runway (App)",
        execution_modes=["manual_assisted"],
        supported_ratios=["9:16", "16:9", "1:1"],
        supported_durations=[5, 10],
        max_duration_per_clip=10.0,
        supports_start_image=True,
        supports_end_image=True,
        native_audio=False,
        post_audio_api=True,
        supports_reference_image=True,
    ),
}


def get_providers_for_mode(execution_mode: str) -> dict[str, ProviderCapability]:
    """execution_mode에 맞는 provider만 필터"""
    return {
        pid: cap
        for pid, cap in PROVIDER_CAPABILITIES.items()
        if execution_mode in cap.execution_modes
    }


def get_providers_for_mode_and_services(
    execution_mode: str,
    requested_services: list[str],
) -> dict[str, ProviderCapability]:
    """execution_mode + 사용자 requested_services 교집합 필터.
    교집합이 비어 있으면 mode-only 필터로 fallback."""
    mode_providers = get_providers_for_mode(execution_mode)
    if not requested_services:
        return mode_providers
    intersected = {
        pid: cap
        for pid, cap in mode_providers.items()
        if pid in requested_services
    }
    return intersected if intersected else mode_providers  # fallback
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
    builder.add_node("audio_director", audio_director_node)
    builder.add_node("plan_reviewer", plan_reviewer_node)
    builder.add_node("orchestrator", orchestrator_node)

    # Entry
    builder.set_entry_point("story_writer")

    # Linear: story -> stitch
    builder.add_edge("story_writer", "stitch_planner")

    # Fan-out (3-way parallel)
    builder.add_edge("stitch_planner", "copywriter")
    builder.add_edge("stitch_planner", "prompt_engineer")
    builder.add_edge("stitch_planner", "audio_director")

    # Fan-in (3 -> plan_reviewer)
    builder.add_edge("copywriter", "plan_reviewer")
    builder.add_edge("prompt_engineer", "plan_reviewer")
    builder.add_edge("audio_director", "plan_reviewer")

    # plan_reviewer -> orchestrator
    builder.add_edge("plan_reviewer", "orchestrator")

    # Conditional routing
    builder.add_conditional_edges(
        "orchestrator",
        route_by_revision,
        {
            "auto_approved": END,
            "needs_human_review": END,
            "max_iterations_reached": END,
            "blocked": END,
            "revise_story": "story_writer",
            "revise_stitch": "stitch_planner",
            "revise_copy": "copywriter",
            "revise_prompt": "prompt_engineer",
            "revise_audio": "audio_director",
        },
    )

    return builder


def route_by_revision(state: VideoAgentState) -> str:
    status = state.get("terminal_status", "pending")

    if status == "auto_approved":
        return "auto_approved"
    if status == "needs_human_review":
        return "needs_human_review"
    if status == "max_iterations_reached":
        return "max_iterations_reached"
    if status == "blocked":
        return "blocked"

    # REVISE_REQUIRED: revision_issues에서 가장 upstream agent 찾기
    issues = state.get("revision_issues", [])
    targets = _resolve_revision_targets(issues)
    if not targets:
        return "revise_story"  # 방어

    primary = targets[0]
    route_map = {
        "story_writer": "revise_story",
        "stitch_planner": "revise_stitch",
        "copywriter": "revise_copy",
        "prompt_engineer": "revise_prompt",
        "audio_director": "revise_audio",
    }
    return route_map.get(primary, "revise_story")


# Issue code -> agent mapping
_CODE_AGENT_MAP = {
    "story.": "story_writer",
    "continuity.": "stitch_planner",
    "production.": "stitch_planner",
    "copy.": "copywriter",
    "prompt.": "prompt_engineer",
    "audio.": "audio_director",
}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Agent upstream order (가장 upstream이 먼저)
_AGENT_UPSTREAM_ORDER = {
    "story_writer": 0,
    "stitch_planner": 1,
    "copywriter": 2,
    "prompt_engineer": 2,
    "audio_director": 2,
}


def _resolve_revision_targets(issues: list[dict]) -> list[str]:
    """이슈 코드에서 target agents 추출, upstream 순서로 정렬"""
    sorted_issues = sorted(
        issues,
        key=lambda i: _SEVERITY_ORDER.get(i.get("severity", "low"), 3),
    )
    targets = []
    for issue in sorted_issues:
        code = issue.get("code", "")
        for prefix, agent in _CODE_AGENT_MAP.items():
            if code.startswith(prefix) and agent not in targets:
                targets.append(agent)
        # issue에 직접 target_agents가 있으면 사용
        for agent in issue.get("target_agents", []):
            if agent not in targets:
                targets.append(agent)
    # upstream 순서로 정렬
    targets.sort(key=lambda a: _AGENT_UPSTREAM_ORDER.get(a, 99))
    return targets
```

### 1.6 그래프 초기화

```python
# graph.py (continued)
import yaml
from pathlib import Path
from picko.config import get_config
from picko.account_context import get_identity, get_weekly_slot

_PLATFORM_DURATION: dict[str, float] = {
    "instagram_reel": 15.0,
    "tiktok": 30.0,
    "youtube_shorts": 60.0,
}

_AGENT_CONFIG_PATH = Path(__file__).parents[3] / "config" / "video_agents.yml"


class VideoAgentGraph:
    def __init__(self):
        self.graph = build_video_agent_graph()
        self.compiled = self.graph.compile()
        self._agent_config = self._load_agent_config()

    def _load_agent_config(self) -> dict:
        if _AGENT_CONFIG_PATH.exists():
            return yaml.safe_load(_AGENT_CONFIG_PATH.read_text()) or {}
        return {}

    def generate(self, creative_brief: dict, **kwargs) -> VideoAgentState:
        config = get_config()
        account_id = creative_brief["account_id"]
        identity = get_identity(account_id)
        account_config = config.get_account(account_id) or {}
        defaults = self._agent_config.get("defaults", {})
        platforms = creative_brief.get("platforms", ["instagram_reel"])
        execution_mode = creative_brief.get("execution_mode", "manual_assisted")

        initial_state: VideoAgentState = {
            # Input
            "account_id": account_id,
            "intent": creative_brief.get("intent", "brand"),
            "services": creative_brief.get("services", ["sora_app"]),
            "platforms": platforms,
            "execution_mode": execution_mode,
            "creative_brief": creative_brief,
            # Context
            "identity": identity.__dict__ if identity else {},
            "account_config": account_config,
            "weekly_slot": None,
            # Marketing extension
            "campaign_context": kwargs.get("campaign_context"),
            "performance_hints": kwargs.get("performance_hints", []),
            "experiment_vars": kwargs.get("experiment_vars"),
            # Planning
            "visual_anchor": "",
            "shots_by_id": {},
            "shot_order": [],
            # Production
            "production_by_shot_id": {},
            "continuity_refs": {},
            "stitch_plan": {},
            "asset_manifest": [],
            # Copy
            "copy_by_shot_id": {},
            # Prompt
            "prompts_by_shot_id": {},
            # Audio
            "audio_by_shot_id": {},
            # Plan Review
            "plan_review": {},
            "revision_issues": [],
            # Artifact Review
            "artifact_review": None,
            # Publish Review
            "publish_status": "pending",
            # Control
            "terminal_status": "pending",
            "iteration_count": 0,
            "max_iterations": defaults.get("max_iterations", 3),
            "auto_approve_threshold": defaults.get("auto_approve_threshold", 85),
            "human_review_threshold": defaults.get("human_review_threshold", 60),
            # Cost
            "llm_calls_used": 0,
            "tokens_used_estimate": 0,
            "cost_usd_estimate": 0.0,
            "cost_budget_usd": defaults.get("cost_budget_usd", 1.0),
        }

        return self.compiled.invoke(initial_state)
```

### 1.7 검증
- [ ] `VideoAgentState` 타입 체크
- [ ] `CreativeBrief`, `ShotDraft`, `ProductionSpec` 직렬화/역직렬화
- [ ] `TerminalStatus` enum 동작
- [ ] `ReviewIssue` 구조 검증
- [ ] `ProviderCapability` + `get_providers_for_mode()` 동작
- [ ] LangGraph 컴파일 (3-way fan-out)

---

## Phase 2: Core Planning Flow (3-4일)

### 2.1 Story Writer Node
**파일**: `picko/video/agents/nodes/story_writer.py`

**입력**: `creative_brief`, `identity`, `account_config`
**출력**: `visual_anchor`, `shots_by_id`, `shot_order`

```python
@safe_node
def story_writer_node(state: VideoAgentState) -> dict:
    brief = state["creative_brief"]
    identity = state["identity"]

    # LLM: generate visual anchor + shots
    visual_anchor = generate_anchor(brief, identity)
    shots = plan_shots(brief, visual_anchor, identity)

    # shot_id 기반 구조로 변환
    shots_by_id = {s["shot_id"]: s for s in shots}
    shot_order = [s["shot_id"] for s in shots]

    return {
        "visual_anchor": visual_anchor,
        "shots_by_id": shots_by_id,
        "shot_order": shot_order,
        "llm_calls_used": 2,
        "tokens_used_estimate": 1500,      # anchor + plan_shots 합산 추정
        "cost_usd_estimate": 0.006,        # Sonnet 4.6 기준: 1500 tokens ~$0.006
    }
```

### 2.2 Stitch Planner Node (recipe-based)
**파일**: `picko/video/agents/nodes/stitch_planner.py`

**핵심 변경**: 서비스 capability 판단이 아닌 **2단 recipe selection**.

```python
@safe_node
def stitch_planner_node(state: VideoAgentState) -> dict:
    shots_by_id = state["shots_by_id"]
    shot_order = state["shot_order"]
    execution_mode = state["execution_mode"]
    requested_services = state.get("services", [])

    # execution_mode + 사용자 requested_services 교집합 필터
    providers = get_providers_for_mode_and_services(execution_mode, requested_services)

    # shot별 production spec 결정 (2단 recipe)
    production_by_shot_id = {}
    for shot_id in shot_order:
        shot = ShotDraft(**shots_by_id[shot_id])

        # 1단계: production_mode 결정 (서비스 독립)
        mode = select_production_mode(shot, list(providers.values()))

        # 2단계: recipe 할당 (provider 매칭)
        spec = assign_render_recipe(shot_id, mode, list(providers.values()), execution_mode)
        production_by_shot_id[shot_id] = asdict(spec)

    # duration 조정
    target_dur = state["creative_brief"].get("target_duration_sec", 15.0)
    adjusted_shots = _distribute_duration(shots_by_id, shot_order, target_dur)

    # continuity refs + stitch plan + asset manifest
    continuity_refs = build_continuity_refs(adjusted_shots, shot_order)
    stitch_plan = plan_stitch_sequence(adjusted_shots, shot_order, production_by_shot_id)
    asset_manifest = build_asset_manifest(adjusted_shots, shot_order, production_by_shot_id)

    return {
        "shots_by_id": adjusted_shots,
        "production_by_shot_id": production_by_shot_id,
        "continuity_refs": continuity_refs,
        "stitch_plan": stitch_plan,
        "asset_manifest": asset_manifest,
        "llm_calls_used": 1,
        "tokens_used_estimate": 800,
        "cost_usd_estimate": 0.003,
    }
```

### 2.3 Prompt Engineer Node
**파일**: `picko/video/agents/nodes/prompt_engineer.py`

production_mode에 따라 적절한 프롬프트 생성:
- `pure_video`: video_prompt 중심
- `keyframe_motion`: image_prompt + video_prompt
- `image_stitch`: image_prompt 중심

```python
@safe_node
def prompt_engineer_node(state: VideoAgentState) -> dict:
    prompts_by_shot_id = {}
    for shot_id in state["shot_order"]:
        shot = state["shots_by_id"][shot_id]
        prod = state["production_by_shot_id"][shot_id]
        mode = prod["production_mode"]
        recipe = prod["render_recipe"]

        bundle = build_prompt_bundle(shot, mode, recipe)
        prompts_by_shot_id[shot_id] = asdict(bundle)

    n_shots = len(state["shot_order"])
    return {
        "prompts_by_shot_id": prompts_by_shot_id,
        "llm_calls_used": n_shots,
        "tokens_used_estimate": n_shots * 400,
        "cost_usd_estimate": n_shots * 0.0016,
    }
```

### 2.4 Audio Director Node
**파일**: `picko/video/agents/nodes/audio_director.py`

```python
@safe_node
def audio_director_node(state: VideoAgentState) -> dict:
    brief = state["creative_brief"]
    audio_by_shot_id = {}

    for shot_id in state["shot_order"]:
        shot = state["shots_by_id"][shot_id]
        prod = state["production_by_shot_id"][shot_id]

        audio_spec = plan_audio_for_shot(
            shot=shot,
            production_spec=prod,
            emotional_target=brief.get("emotional_target", ""),
        )
        audio_by_shot_id[shot_id] = asdict(audio_spec)

    return {
        "audio_by_shot_id": audio_by_shot_id,
        "llm_calls_used": 1,
        "tokens_used_estimate": 600,
        "cost_usd_estimate": 0.0024,
    }
```

### 2.5 Copywriter Node
**파일**: `picko/video/agents/nodes/copywriter.py`

```python
@safe_node
def copywriter_node(state: VideoAgentState) -> dict:
    brief = state["creative_brief"]
    copy_by_shot_id = {}

    for i, shot_id in enumerate(state["shot_order"]):
        shot = state["shots_by_id"][shot_id]
        is_first = (i == 0)
        is_last = (i == len(state["shot_order"]) - 1)

        bundle = generate_copy_for_shot(
            shot=shot,
            brief=brief,
            is_first=is_first,
            is_last=is_last,
        )
        copy_by_shot_id[shot_id] = asdict(bundle)

    return {
        "copy_by_shot_id": copy_by_shot_id,
        "llm_calls_used": 1,
        "tokens_used_estimate": 500,
        "cost_usd_estimate": 0.002,
    }
```

### 2.6 검증
- [ ] story_writer -> shots_by_id, shot_order, visual_anchor
- [ ] stitch_planner -> production_by_shot_id (recipe-based)
- [ ] prompt_engineer -> prompts_by_shot_id
- [ ] audio_director -> audio_by_shot_id
- [ ] copywriter -> copy_by_shot_id
- [ ] 불변식: 모든 dict key set == set(shot_order)

---

## Phase 3: Review & Control Loop (3-4일)

### 3.1 Plan Reviewer Node
**파일**: `picko/video/agents/nodes/plan_reviewer.py`

기존 `VideoPlanScorer` 재사용 + 멀티에이전트 전용 검수 항목 추가.

```python
@safe_node
def plan_reviewer_node(state: VideoAgentState) -> dict:
    # 기존 scorer 재사용 (임시 VideoPlan 구성)
    temp_plan = _build_temp_plan(state)
    scorer = VideoPlanScorer()
    score = scorer.score(temp_plan, state["services"])

    # 멀티에이전트 전용 추가 검수
    production_issues = _review_production_fit(state)
    audio_issues = _review_audio_fit(state)

    # 구조화된 이슈 코드 생성
    review_issues = []
    for issue_text in score.issues:
        review_issues.append(_classify_issue(issue_text))
    review_issues.extend(production_issues)
    review_issues.extend(audio_issues)

    return {
        "plan_review": {
            "quality_score": score.overall,
            "issues": [asdict(i) for i in review_issues],
            "feedback_notes": score.suggestions,
        },
        "revision_issues": [asdict(i) for i in review_issues],
        "llm_calls_used": 2,
        "tokens_used_estimate": 1200,
        "cost_usd_estimate": 0.0048,
    }


def _classify_issue(issue_text: str) -> ReviewIssue:
    """텍스트 이슈를 구조화된 ReviewIssue로 변환"""
    # 이슈 텍스트에서 코드/severity 추론
    code = _infer_issue_code(issue_text)
    severity = _infer_severity(issue_text)
    targets = _infer_target_agents(code)
    return ReviewIssue(
        code=code,
        severity=severity,
        target_agents=targets,
        description=issue_text,
    )
```

### 3.2 Orchestrator Node
**파일**: `picko/video/agents/nodes/orchestrator.py`

TerminalStatus enum 기반 결정.

```python
INVALIDATION_CASCADE = {
    "story_writer":     ["stitch_planner", "copywriter", "prompt_engineer", "audio_director"],
    "stitch_planner":   ["prompt_engineer", "audio_director"],
    "copywriter":       [],
    "prompt_engineer":  [],
    "audio_director":   [],
}

_FIELD_DEFAULTS: dict[str, dict] = {
    "story_writer":     {"visual_anchor": "", "shots_by_id": {}, "shot_order": []},
    "stitch_planner":   {"production_by_shot_id": {}, "stitch_plan": {}, "asset_manifest": [], "continuity_refs": {}},
    "copywriter":       {"copy_by_shot_id": {}},
    "prompt_engineer":  {"prompts_by_shot_id": {}},
    "audio_director":   {"audio_by_shot_id": {}},
}


def orchestrator_node(state: VideoAgentState) -> dict:
    updates: dict = {
        "iteration_count": state["iteration_count"] + 1,
    }

    score = state.get("plan_review", {}).get("quality_score", 0.0)
    cost = state.get("cost_usd_estimate", 0.0)
    budget = state.get("cost_budget_usd", 1.0)
    auto_threshold = state.get("auto_approve_threshold", 85)
    human_threshold = state.get("human_review_threshold", 60)
    max_iter = state.get("max_iterations", 3)

    # 비용 초과
    if cost >= budget:
        updates["terminal_status"] = "blocked"
        return updates

    # 자동 승인
    if score >= auto_threshold:
        updates["terminal_status"] = "auto_approved"
        return updates

    # max iterations
    if state["iteration_count"] + 1 >= max_iter:
        updates["terminal_status"] = "max_iterations_reached"
        return updates

    # human review
    if score <= human_threshold:
        updates["terminal_status"] = "needs_human_review"
        return updates

    # Hard fail: brand violation -> story_writer 필수 (D4 규칙)
    issues = state.get("revision_issues", [])
    has_brand_violation = any(
        i.get("code", "").startswith("copy.brand_violation") for i in issues
    )
    if has_brand_violation:
        updates["terminal_status"] = "revise_required"
        cascade_updates = _build_invalidation_updates("story_writer")
        updates.update(cascade_updates)
        return updates

    # Revision required (일반)
    updates["terminal_status"] = "revise_required"
    targets = _resolve_revision_targets(issues)
    if targets:
        primary = targets[0]
        cascade_updates = _build_invalidation_updates(primary)
        updates.update(cascade_updates)

    return updates


def _build_invalidation_updates(revision_target: str) -> dict:
    targets = [revision_target] + INVALIDATION_CASCADE.get(revision_target, [])
    updates: dict = {}
    for target in targets:
        updates.update(_FIELD_DEFAULTS.get(target, {}))
    return updates
```

### 3.3 검증
- [ ] plan_reviewer -> 구조화된 ReviewIssue 출력
- [ ] orchestrator -> TerminalStatus enum 기반 결정
- [ ] cascade invalidation (shot_id 기반 dict 초기화)
- [ ] revision loop 동작 (이슈 코드 -> agent routing)
- [ ] 비용 초과 -> BLOCKED
- [ ] max_iterations -> MAX_ITERATIONS_REACHED

---

## Phase 4: Artifact Review & Manual Loop (3-4일)

### 4.1 Render Brief 출력

Planning graph 완료 시 (AUTO_APPROVED) 렌더 브리프 생성:

```python
def build_render_briefs(state: VideoAgentState) -> list[dict]:
    """서비스별 렌더 지침서 생성 (manual_assisted용)"""
    briefs = []
    for shot_id in state["shot_order"]:
        prod = state["production_by_shot_id"][shot_id]
        prompt = state["prompts_by_shot_id"][shot_id]
        audio = state["audio_by_shot_id"][shot_id]
        copy = state["copy_by_shot_id"][shot_id]
        shot = state["shots_by_id"][shot_id]

        briefs.append({
            "shot_id": shot_id,
            "provider": prod["render_recipe"].get("motion_service") or prod["render_recipe"].get("image_service"),
            "production_mode": prod["production_mode"],
            "video_prompt": prompt.get("video_prompt", ""),
            "image_prompt": prompt.get("image_prompt", ""),
            "negative_prompt": prompt.get("negative_prompt", ""),
            "audio_strategy": audio.get("audio_strategy", "silent_visual"),
            "duration_sec": shot.get("duration_sec", 5.0),
            "scene_description": shot.get("scene_description", ""),
            "caption": copy.get("caption", ""),
            "service_specific_params": prompt.get("service_specific_params", {}),
        })
    return briefs
```

### 4.2 Artifact Reviewer - Deterministic Checks
**파일**: `picko/video/agents/tools/artifact_qa.py`

```python
def deterministic_checks(file_path: str, expected: dict) -> list[dict]:
    """규칙 기반 미디어 파일 검사 (VLM에 의존하지 않는 객관적 검사)"""
    issues = []

    # 파일 손상 여부 (가장 먼저)
    if not _is_file_intact(file_path):
        issues.append({"check": "file_integrity", "auto_regen_ok": True, "description": "file corrupted or unreadable"})
        return issues  # 이후 검사 불가

    # duration check
    actual_dur = _get_media_duration(file_path)
    if abs(actual_dur - expected["duration_sec"]) > 1.0:
        issues.append({"check": "duration", "expected": expected["duration_sec"], "actual": actual_dur, "auto_regen_ok": True})

    # aspect ratio check (canonical ratio 문자열로 정규화 후 비교)
    actual_ratio = _normalize_ratio(_get_aspect_ratio(file_path))
    expected_ratio = _normalize_ratio(expected.get("aspect_ratio", ""))
    if actual_ratio != expected_ratio:
        issues.append({"check": "aspect_ratio", "expected": expected_ratio, "actual": actual_ratio, "auto_regen_ok": True})

    # fps check
    actual_fps = _get_fps(file_path)
    expected_fps = expected.get("fps")
    if expected_fps and abs(actual_fps - expected_fps) > 1.0:
        issues.append({"check": "fps", "expected": expected_fps, "actual": actual_fps, "auto_regen_ok": True})

    # audio track presence
    has_audio = _has_audio_track(file_path)
    if expected.get("audio_strategy") != "silent_visual" and not has_audio:
        issues.append({"check": "audio_missing", "expected": "audio track present", "auto_regen_ok": True})

    # waveform/loudness check (오디오 있는 경우만)
    if has_audio:
        loudness_lufs = _get_loudness_lufs(file_path)
        if loudness_lufs is not None and loudness_lufs < -40.0:
            issues.append({"check": "loudness_too_low", "actual_lufs": loudness_lufs, "auto_regen_ok": True})

    # OCR: 텍스트 오버레이 필요한 shot인데 텍스트 없는 경우
    if expected.get("overlay_text_needed"):
        detected_text = _ocr_detect_text(file_path)
        if not detected_text:
            issues.append({"check": "overlay_text_missing", "auto_regen_ok": True})

    return issues


def _normalize_ratio(ratio: str) -> str:
    """'1080x1920' -> '9:16', '1920x1080' -> '16:9' 등 canonical ratio로 정규화"""
    _RESOLUTION_TO_RATIO = {
        "1080x1920": "9:16",
        "1920x1080": "16:9",
        "1080x1080": "1:1",
    }
    return _RESOLUTION_TO_RATIO.get(ratio, ratio)
```

### 4.3 Artifact Reviewer - VLM QA
**파일**: `picko/video/agents/nodes/artifact_reviewer.py`

VLM은 **좁은 질문**만 수행. Open-ended 평가 금지.

```python
VLM_QA_QUESTIONS = [
    "Does the video contain an intro hook in the first 3 seconds? (yes/no)",
    "Is the visual anchor ({anchor}) maintained throughout? (yes/no/partial)",
    "Are there any prohibited elements (violence, explicit content)? (yes/no)",
    "Does the character appearance remain consistent? (yes/no/partial)",
    "Is the lighting consistent with the plan ({lighting})? (yes/no)",
]

def artifact_reviewer_node(state: dict, uploaded_file: str) -> dict:
    """렌더 결과물 3층 QA"""
    expected = _build_expected_from_plan(state)

    # Layer 1: Deterministic
    det_issues = deterministic_checks(uploaded_file, expected)

    # Layer 2: VLM (only if deterministic passes)
    vlm_issues = []
    if not det_issues:
        vlm_issues = vlm_structural_qa(uploaded_file, state)

    # Layer 3: Human gate flag
    needs_human = any(i.get("needs_human") for i in vlm_issues)

    auto_regen_items = [i for i in (det_issues + vlm_issues) if i.get("auto_regen_ok")]
    human_review_items = [i for i in (det_issues + vlm_issues) if not i.get("auto_regen_ok")]

    return {
        "artifact_review": {
            "passed": not det_issues and not vlm_issues,
            "deterministic_issues": det_issues,
            "vlm_issues": vlm_issues,
            "auto_regen_suggestions": auto_regen_items,
            "human_review_items": human_review_items,
            "needs_human_gate": needs_human or bool(human_review_items),
        },
    }
```

### 4.4 Publish Reviewer Node (Human Gate)
**파일**: `picko/video/agents/nodes/publish_reviewer.py`

artifact_reviewer 통과 후 반드시 거치는 human gate. 제거 불가.

```python
def publish_reviewer_node(state: dict, human_decision: str) -> dict:
    """사람이 감성/브랜드/리스크를 최종 확인 후 게시 승인/거절.
    human_decision: "approved" | "blocked"
    """
    return {
        "publish_status": human_decision,
    }
```

CLI/UI 연동 시: `human_decision`을 사용자 입력에서 받는다.
게시 자동화 파이프라인에서도 이 노드는 interactive pause point로 유지.

### 4.5 검증
- [ ] render_brief 출력 포맷 검증 (render_briefs in VideoPlan)
- [ ] deterministic_checks 동작
- [ ] VLM QA 좁은 질문 패턴 검증
- [ ] auto_regen vs human_review 분류
- [ ] publish_reviewer_node -> publish_status 업데이트
- [ ] publish_status "pending" -> "approved" / "blocked" 전환

---

## Phase 5: Integration & Testing (2-3일)

### 5.1 VideoGenerator 수정
**파일**: `picko/video/generator.py`

```python
def _generate_with_agents(self, validate: bool) -> VideoPlan:
    # CreativeBrief의 핵심 필드를 모두 채운다.
    # VideoGenerator가 보유한 속성을 최대한 매핑하고, 없는 필드는 기본값.
    brief = CreativeBrief(
        account_id=self.account_id,
        intent=self.intent,
        objective=getattr(self, "objective", ""),
        audience=getattr(self, "audience", ""),
        emotional_target=getattr(self, "emotional_target", ""),
        message_pillar=getattr(self, "message_pillar", ""),
        proof_points=getattr(self, "proof_points", []),
        product_surface=getattr(self, "product_surface", ""),
        cta_policy=getattr(self, "cta_policy", "soft"),
        target_duration_sec=self.target_duration_sec,
        platforms=self.platforms,
        services=self.services,
        execution_mode=getattr(self, "execution_mode", "manual_assisted"),
        series_id=getattr(self, "series_id", None),
        brand_rules_ref=getattr(self, "brand_rules_ref", None),
    )

    graph = VideoAgentGraph()
    result = graph.generate(creative_brief=asdict(brief))
    return self._state_to_plan(result)
```

### 5.2 _state_to_plan() (shot_id 기반)

```python
def _state_to_plan(self, state: VideoAgentState) -> VideoPlan:
    shots = []
    for i, shot_id in enumerate(state["shot_order"]):
        shot_data = state["shots_by_id"][shot_id]
        copy_data = state["copy_by_shot_id"].get(shot_id, {})
        prompt_data = state["prompts_by_shot_id"].get(shot_id, {})
        prod_data = state["production_by_shot_id"].get(shot_id, {})

        shot = VideoShot(
            index=i + 1,
            duration_sec=shot_data.get("duration_sec", 5),
            shot_type=shot_data.get("purpose", "main"),
            script=shot_data.get("scene_description", ""),
            caption=copy_data.get("caption", ""),
            background_prompt=prompt_data.get("video_prompt", ""),
        )
        shot.notes = {
            "shot_id": shot_id,
            "emotional_beat": shot_data.get("emotional_beat", ""),
            "production_mode": prod_data.get("production_mode", ""),
            "audio_strategy": state["audio_by_shot_id"].get(shot_id, {}).get("audio_strategy", ""),
        }
        shots.append(shot)

    # render_briefs: manual_assisted 단계의 핵심 실무 산출물
    render_briefs = build_render_briefs(state)

    plan = VideoPlan(
        id="agent_" + state["account_id"],
        account=state["account_id"],
        intent=state["intent"],
        shots=shots,
        target_services=state["services"],
        platforms=state["platforms"],
        stitch_plan=state.get("stitch_plan"),
        asset_manifest=state.get("asset_manifest", []),
        production_specs=state.get("production_by_shot_id", {}),
        audio_specs=state.get("audio_by_shot_id", {}),
        render_briefs=render_briefs,
        platform_variants=[],   # reserved: Platform Variant Builder (P1)
    )
    return plan
```

### 5.3 검증
- [ ] 기존 테스트 통과 (legacy path)
- [ ] `_generate_with_agents()` 결과 검증
- [ ] `_state_to_plan()` shot_id 매핑 정확성
- [ ] render_brief 출력 동작

---

## Phase 6: Testing & Polish (2-3일)

### 6.1 단위 테스트
**파일**: `tests/video/agents/`

- `test_state.py` - 상태 직렬화/역직렬화, TerminalStatus
- `test_schemas.py` - CreativeBrief, ShotDraft, ProductionSpec, ReviewIssue
- `test_providers.py` - ProviderCapability, get_providers_for_mode
- `test_tools_story.py` - Story Writer 도구들
- `test_tools_stitch.py` - Stitch Planner (recipe selection)
- `test_tools_copy.py` - Copywriter 도구들
- `test_tools_prompt.py` - Prompt Engineer 도구들
- `test_tools_audio.py` - Audio Director 도구들
- `test_tools_review.py` - Plan Reviewer (이슈 분류)
- `test_artifact_qa.py` - Deterministic checks

### 6.2 통합 테스트
- `test_graph.py` - 전체 흐름 (3-way fan-out)
- `test_revision_loop.py` - 이슈 코드 기반 revision
- `test_integration.py` - VideoGenerator 통합
- `test_render_brief.py` - 렌더 브리프 출력

### 6.3 검증
- [ ] `pytest tests/video/agents/ -v` 통과
- [ ] 커버리지 80% 이상

---

## Critical Files Summary

| 파일 | Phase | 설명 |
|------|-------|------|
| `picko/video/agents/state.py` | 1 | VideoAgentState + TerminalStatus |
| `picko/video/agents/schemas.py` | 1 | CreativeBrief, ProductionSpec, ReviewIssue 등 |
| `picko/video/agents/providers.py` | 1 | ProviderCapability registry |
| `picko/video/agents/graph.py` | 1-3 | LangGraph (3-way fan-out, 이슈 코드 routing) |
| `picko/video/agents/nodes/stitch_planner.py` | 2 | recipe-based production |
| `picko/video/agents/nodes/audio_director.py` | 2 | 오디오 전략 |
| `picko/video/agents/nodes/plan_reviewer.py` | 3 | 구조화된 이슈 코드 |
| `picko/video/agents/nodes/orchestrator.py` | 3 | TerminalStatus 기반 결정 |
| `picko/video/agents/nodes/artifact_reviewer.py` | 4 | 3층 QA |
| `picko/video/agents/nodes/publish_reviewer.py` | 4 | Human gate (게시 최종 승인) |
| `picko/video/agents/tools/artifact_qa.py` | 4 | Deterministic + VLM |
| `picko/video/generator.py` | 5 | 통합 진입점 |

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
pytest tests/video/agents/test_providers.py -v

# Phase 2
pytest tests/video/agents/test_tools_*.py -v

# Phase 3
pytest tests/video/agents/test_graph.py -v

# Phase 4
pytest tests/video/agents/test_artifact_qa.py -v
pytest tests/video/agents/test_render_brief.py -v

# Full suite
pytest tests/video/agents/ -v --cov=picko.video.agents
```

---

## Risk Mitigation

| 위험 | 대응 |
|-----|------|
| LangGraph 3-way fan-out 동작 | 공식 문서 기반 검증, fan-in barrier 테스트 |
| VLM 영상 평가 정확도 | bounded autonomy: 자동 재생성은 객관적 항목만 |
| Provider API 제약 변경 | PROVIDER_CAPABILITIES registry 분리, 업데이트 용이 |
| manual -> API 전환 | planning/QA contract 분리, provider adapter만 교체 |
| 비용 추적 정확도 | 3개 메트릭 분리, cost_budget_usd로 hard limit |
| 기존 코드 호환성 | `use_multi_agent=False`로 legacy 유지 |
