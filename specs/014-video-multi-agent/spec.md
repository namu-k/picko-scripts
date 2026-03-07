# Multi-Agent Video Planning & Production Architecture

## Meta

- **Spec ID**: 014
- **Branch**: `014-video-multi-agent`
- **Status**: Ready for Implementation
- **Created**: 2026-03-06
- **Updated**: 2026-03-07 (v4 - production loop, reviewer 분리, recipe-based 설계)

---

## 0. 문서 범위 (Core vs Marketing Layer Boundary)

이 문서는 **"비디오 planning / production recipe selection / render QA / publish gate"를 담당하는 코어 시스템**을 정의한다.

캠페인 전략, KPI 최적화, 실험 생성, 브랜드 운영 자동화는 **본 문서 범위 밖**이며, 향후 별도 마케팅 레이어에서 담당한다.
단, 추후 마케팅 레이어 통합을 위해 필요한 확장 포인트와 reserved field는 본 문서에 포함한다.

```
현재 단계의 원칙:

1. 마케팅 전략 로직은 In Scope에 넣지 않는다.
2. KPI 최적화, 실험 설계, 캠페인 전략, 브랜드 거버넌스 자동화는 Out of Scope.
3. 향후 마케팅 레이어가 연결될 수 있도록 입력 필드, reserved state, reviewer hook, metadata 슬롯은 유지한다.
4. 플랫폼 적응, 오디오 전략, 제품/UI 삽입 가능성, 사람 승인 흐름은 코어에 남긴다.
5. "마케팅 기능 구현"과 "마케팅 확장 가능성 보장"을 구분한다.
```

---

## 1. 목적

현재 VideoGenerator는 단일 LLM 호출로 VideoPlan을 생성한다. 이 방식의 한계:

- 스토리, 카피, 프롬프트, 제작 방식이 한 번에 섞여 품질 관리 어려움
- 이미지 기반 제작과 비디오 기반 제작을 구분하지 못함
- 피드백 루프가 단순 재시도 수준
- 샷 단위 일관성, 감성 톤, 제작 전략 분리 개선 불가
- 오디오 레이어 부재 (이 서비스는 목소리 기반 연결감이 핵심)
- 플랫폼별/서비스별 출력 분리 없음
- 실제 렌더 결과물에 대한 검수 체계 없음

### 핵심 설계 원칙

1. **Planning Engine + Production Loop 분리**: 기획 그래프와 실행 그래프를 명확히 나눈다
2. **Recipe-based Production**: 서비스 선택이 아니라 제작 레시피 선택이 먼저
3. **Bounded Autonomy**: VLM은 구조화된 품질 검사기로, 감성/브랜드는 사람이 판단
4. **Manual-first, API-ready**: 구독형 수동 렌더로 시작, API 전환 시 계약 유지

### 1단계 목표

> **새벽 감성 숏폼 영상을 위한 "기획 + 카피 + 프롬프트 + 오디오전략 + 제작전략 + 품질검수" 패키지를 멀티에이전트로 생성하고, 수동-보조형 렌더 루프를 통해 실제 영상까지 닫힌 production loop를 구축한다.**

### In Scope

- CreativeBrief 기반 비디오 planning
- shot/segment 단위 production mode 선택
- provider/service/platform 제약 반영
- audio_strategy 반영
- render_brief 생성
- deterministic QA
- VLM 기반 artifact QA
- human gate / publish gate
- marketing-facing extension points (reserved fields / hooks / metadata slots)
- platform_variants (delivery adaptation — 마케팅 전략이 아닌 출력 포맷 적응)

### Out of Scope

- KPI 기반 자동 최적화
- 캠페인 전략 생성 및 우선순위화
- 실험 설계 및 성과 기반 creative iteration
- 브랜드 가이드 자동 생성/수정
- 감성 키워드 발굴 시스템
- 채널 운영 정책 엔진
- 마케터용 대시보드 및 운영 분석 UI
- Product/UI Insert Planner 활성화 (ad/explainer 전용 - reserved, P1)
- Vault retrieval (과거 시리즈/anchor 재사용 - P1)

### 마케팅 레이어 확장 포인트 (Reserved — 현재 미구현)

아래는 현재 코어 엔진이 직접 사용하지 않는 reserved 슬롯이다.
향후 마케팅 기능이 추가될 때 별도 레이어에서 주입한다.
현재 단계에서는 저장/전달만 보장하고, 코어 의사결정의 필수 기준으로 사용하지 않는다.

```python
# VideoAgentState 내 확장 필드 (Reserved — 현재 코어 분기 로직에 사용하지 않음)
# 현재 단계에서는 전달/저장만 보장. 향후 마케팅 레이어에서 주입/사용.
campaign_context: dict | None      # 시리즈/캠페인 맥락
performance_hints: list[str]       # 과거 성과 기반 힌트
experiment_vars: dict | None       # A/B 테스트 변수
```

| 마케팅 기능 | 주입 포인트 | 현재 상태 |
|------------|------------|-----------|
| A/B 실험 변수 | `experiment_vars` | reserved, 비활성 |
| 성과 데이터 피드백 | `performance_hints` | reserved, 비활성 |
| 시리즈/캠페인 컨텍스트 | `campaign_context` | reserved, 비활성 |
| 채널별 포맷 적응 | `platform_variants[]` | P1 (delivery adaptation) |

---

## 2. 시스템 범위

### A. Creative Planning Graph (이번 스펙)

- 영상 콘셉트에 맞는 스토리 구조 설계
- 샷 단위 장면 설명 생성
- 훅, 캡션, CTA 등 카피 생성
- 이미지 프롬프트 및 비디오 프롬프트 생성
- 각 샷의 제작 레시피 결정 (production_mode + render_recipe)
- 오디오 전략 수립 (audio_strategy per shot)
- 샷 간 일관성, 브랜드 톤, 구조 품질 검수 (Plan Review)
- 렌더 결과물 검수 (Artifact Review - VLM + deterministic)
- 최종 게시 검수 (Publish Review - human gate)
- 필요 시 특정 에이전트 재호출

### C. Product/UI Insert Planner (Reserved Extension — 미활성)

ad/explainer 마케팅 레이어에서 활성화될 수 있는 확장 포인트. 현재 코어 범위에서는 agent node로 활성화하지 않는다.

아래 출력 슬롯만 reserved field로 유지한다:
- `ui_insert_shot_ids: list[str]` — 제품 UI 삽입이 필요한 shot
- `product_proof_required: bool` — 제품 증거 삽입 필요 여부
- `proof_overlay_copy: list[str]` — 증거 오버레이 카피
- `product_surface_mode: str` — 제품 노출 방식

현재 단계에서 `product_surface`가 존재하더라도 코어가 이를 강제 최적화하지 않는다.
필요 시 사람이 render brief를 수동 조정할 수 있도록만 한다.

---

### B. Production Execution Graph (향후 - API 전환 시)

- Asset Job Builder, Image/Motion Generator
- Stitch Renderer, Caption Burn-in
- Delivery Packager

현재는 `manual_assisted` 모드: Planning Graph가 렌더 브리프를 출력하고, 사람이 결과 파일을 업로드하면 Artifact Review를 이어감.

### 결과물

| 산출물 | 설명 |
|--------|------|
| `master_plan` | 이야기/감정선/visual anchor/샷 구조 |
| `copy_pack` | 훅, 캡션, CTA, 오버레이 (by shot_id) |
| `prompt_pack` | 이미지/비디오 프롬프트 (by shot_id) |
| `audio_plan` | 오디오 전략 (by shot_id) |
| `production_specs` | 샷별 제작 레시피 (by shot_id) |
| `stitch_plan` | 이미지 시퀀스/전환 계획 |
| `asset_manifest` | 제작 필요 자산 목록 (job DAG 방향) |
| `render_briefs` | 서비스별 렌더 브리프 (manual_assisted용) |
| `platform_variants` | 플랫폼별 파생 스펙 (P1) |
| `review_notes` | Plan/Artifact/Publish 검수 피드백 |
| `terminal_status` | auto_approved / needs_human_review / revise_required / blocked / max_iterations_reached |

---

## 3. 에이전트 구조

### 3.1 Story Writer (스토리 작가)

**역할**: Narrative arc 설계, visual anchor 생성, 샷 시퀀스 작성

**입력**:
- `creative_brief` (CreativeBrief)
- `identity`, `account_config`

**출력**:
- `visual_anchor`
- `shots_by_id: Dict[str, ShotDraft]`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `analyze_intent` | 규칙 | Intent별 샷 구조 기본값 매핑 |
| `generate_anchor` | LLM | visual anchor 생성 |
| `plan_shots` | LLM | shot sequence 및 장면 설명 생성 |

---

### 3.2 Stitch Planner (스티치 플래너)

**역할**: 각 샷의 제작 레시피 결정, production pipeline 설계

**핵심 변경 (v4)**: `generation_method` 단일 결정이 아닌 **2단 recipe selection**.

#### 1단계: shot별 production_mode 결정

- `pure_video` - 단일 비디오 모델로 생성
- `keyframe_motion` - 키프레임 이미지 + 모션 모델
- `image_stitch` - 이미지 시퀀스 + 스티치 엔진
- `hybrid_segment` - 복합 파이프라인

#### 2단계: mode별 render_recipe assignment

```python
RenderRecipe = {
    "image_service": str | None,    # "midjourney" | "flux" | None
    "motion_service": str | None,   # "runway_api" | "sora_api" | None
    "stitch_engine": str | None,    # 후처리 엔진
    "audio_strategy": str,          # shot-level audio 전략
    "continuity_ref_source": str,   # 일관성 참조 출처
}
```

**입력**:
- `shots_by_id` (Story Writer 출력)
- `services[]` + `PROVIDER_CAPABILITIES`
- `execution_mode` (manual_assisted | api)

**출력**:
- `production_by_shot_id: Dict[str, ProductionSpec]`
- `continuity_refs: ContinuityRefs`
- `stitch_plan: StitchPlan`
- `asset_manifest: list[AssetItem]`

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `select_production_mode` | 규칙 | shot별 production mode 결정 |
| `assign_render_recipe` | 규칙+LLM | mode별 recipe + fallback 할당 |
| `build_continuity_refs` | 규칙 | 캐릭터/배경/조명 일관성 참조 정리 |
| `plan_stitch_sequence` | LLM | 이미지 시퀀스/스티치 계획 작성 |
| `build_asset_manifest` | 규칙 | 제작 자산 목록 정리 |

**select_production_mode 로직 (v4)**:
```python
def select_production_mode(shot: ShotDraft, providers: list[ProviderCapability]) -> str:
    """shot 요구사항 기반으로 production mode 결정 (서비스가 아닌 mode 먼저)"""

    # 1. shot 요구사항 분석
    needs_start_end_frame = shot.motion_type in ("morph", "interpolate")
    needs_character_consistency = "character" in shot.continuity_constraints

    # 2. mode 후보 평가 (서비스 독립적)
    if needs_start_end_frame:
        mode = "keyframe_motion"
    elif needs_character_consistency and shot.motion_type == "static":
        mode = "image_stitch"
    else:
        mode = "pure_video"

    # 3. 선택된 mode를 지원하는 provider가 있는지 확인
    if not _any_provider_supports(mode, providers):
        mode = "pure_video"  # fallback

    return mode

def assign_render_recipe(
    shot_id: str,
    mode: str,
    providers: list[ProviderCapability],
    execution_mode: str,
) -> ProductionSpec:
    """mode + provider capabilities → 구체적 recipe 할당"""
    primary = _best_provider_for_mode(mode, providers, execution_mode)
    fallback = _fallback_provider_for_mode(mode, providers, execution_mode)

    return ProductionSpec(
        shot_id=shot_id,
        production_mode=mode,
        render_recipe=RenderRecipe(
            image_service=primary.image_service,
            motion_service=primary.motion_service,
            stitch_engine=primary.stitch_engine,
            audio_strategy=_infer_audio_strategy(shot_id, primary),
            continuity_ref_source=primary.continuity_method,
        ),
        fallback_recipe=fallback,
    )
```

---

### 3.3 Copywriter (카피라이터)

**역할**: 훅, 캡션, CTA 작성, 텍스트 오버레이 초안

**출력**:
- `copy_by_shot_id: Dict[str, CopyBundle]`

```python
CopyBundle = {
    "hook": str | None,         # 첫 샷에만
    "caption": str,
    "cta": str | None,          # 마지막 샷에만
    "overlay_text": str | None,
}
```

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `create_hook` | LLM | 첫 3초 훅 생성 |
| `generate_caption` | LLM | shot별 캡션 생성 |
| `write_cta` | LLM | CTA 작성 |

---

### 3.4 Prompt Engineer (프롬프트 엔지니어)

**역할**: 서비스별 비디오/이미지 프롬프트 생성

**출력**:
- `prompts_by_shot_id: Dict[str, PromptBundle]`

```python
PromptBundle = {
    "video_prompt": str,          # production_mode에 따라 "" 가능
    "image_prompt": str,          # production_mode에 따라 "" 가능
    "negative_prompt": str,
    "service_specific_params": dict,  # 서비스별 추가 파라미터
}
```

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `build_service_prompt` | LLM | 서비스별 비디오 프롬프트 생성 |
| `create_keyframe_prompt` | 규칙+LLM | keyframe 이미지 프롬프트 생성 |
| `apply_negative_prompt` | 규칙 | 서비스별 negative prompt 적용 |

---

### 3.5 Audio Director (오디오 디렉터) - NEW

**역할**: 샷별 오디오 전략 수립

이 서비스는 "목소리 기반 연결감"이 본질이므로 오디오 레이어가 필수.

**입력**:
- `shots_by_id`, `production_by_shot_id`
- `creative_brief.emotional_target`

**출력**:
- `audio_by_shot_id: Dict[str, AudioSpec]`

```python
AudioSpec = {
    "audio_strategy": str,       # native_synced_audio | post_audio_tts_sfx | ambient_only | silent_visual
    "voiceover_needed": bool,
    "voiceover_script": str | None,
    "silence_windows": list[tuple[float, float]],  # (start_sec, end_sec)
    "ambient_profile": str,      # "late_night_room" | "city_rain" | "quiet_breathing"
    "bgm_profile": str,          # "lo-fi calm" | "piano minimal" | "none"
    "sfx_cues": list[dict],      # [{"time_sec": 3.0, "effect": "notification_soft"}]
    "caption_timing_ref": str | None,
}
```

**audio_strategy 정의**:

| 전략 | 설명 | 적합 서비스 |
|------|------|------------|
| `native_synced_audio` | 영상 생성 시 오디오 동시 생성 | Sora 2, Veo 3.1 |
| `post_audio_tts_sfx` | 영상 후 TTS/SFX/BGM 결합 | Runway + 별도 오디오 API |
| `ambient_only` | 환경음/BGM만 | 모든 서비스 |
| `silent_visual` | 무음 (자막 중심) | 모든 서비스 |

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `plan_audio_strategy` | LLM | shot별 오디오 전략 결정 |
| `write_voiceover_script` | LLM | 보이스오버 스크립트 작성 |
| `assign_ambient_profile` | 규칙 | 환경음/BGM 프로파일 매핑 |

---

### 3.6 Plan Reviewer (계획 검수)

**역할**: 스토리/카피/프롬프트/오디오 계획의 사전 품질 검수

**입력**: 전체 planning state (shots, copy, prompts, audio, production specs)

**출력**:
- `plan_review: PlanReviewResult`

```python
PlanReviewResult = {
    "quality_score": float,
    "issues": list[ReviewIssue],
    "feedback_notes": list[str],
}
```

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `check_consistency` | 규칙 | anchor/shot/continuity 일관성 검사 |
| `validate_brand` | 규칙 | 금칙어/톤 위반 검사 |
| `review_structure` | LLM | 전체 구조 품질 평가 |
| `review_production_fit` | LLM | shot과 제작 방식 적합성 평가 |
| `review_audio_fit` | LLM | 오디오 전략과 감정선 적합성 |
| `review_marketing_fit` | — | **reserved hook** — 현재 단계 비활성. 향후 마케팅 레이어에서 활성화 |

### Marketing Fit Hook (Reserved)
현재 Plan Reviewer는 **구조 품질, 제작 적합성, 오디오 적합성, 브랜드 안전성**만 평가한다.
`review_marketing_fit()`는 인터페이스만 예약하고 현재 실행 그래프에 연결하지 않는다.
KPI 정렬성, 캠페인 목표 달성 가능성 평가는 향후 마케팅 레이어에서 담당한다.

---

### 3.7 Artifact Reviewer (산출물 검수) - NEW

**역할**: 실제 렌더된 영상/오디오/자막 검수

**적용 시점**: `manual_assisted` 모드에서 사용자가 렌더 결과를 업로드한 후

**입력**: 렌더된 파일 + plan 대비 기대값

**출력**:
- `artifact_review: ArtifactReviewResult`

#### 3층 QA 구조

**1층: Deterministic Checks** (규칙/도구):
- duration, aspect ratio, fps
- audio track 존재 여부, waveform/loudness
- OCR로 텍스트 존재 여부
- 파일 손상 여부

**2층: VLM Artifact Review** (Gemini/GPT-4.1):
- 좁은 질문 방식 (open-ended 평가 금지)
- "00:00~00:03에 intro hook가 있는가"
- "bedroom/moonlight/phone glow 앵커가 유지되는가"
- "금지 요소가 있는가"
- segment 단위로 잘라서 전송 (1 FPS 한계 대응)

**3층: Human Gate**:
- 감성/브랜드/리스크 확인
- 이 층은 제거 불가

**자동 재생성 허용 범위** (bounded autonomy):

| 자동 재생성 가능 | 사람 검토 필수 |
|----------------|--------------|
| aspect ratio 불일치 | 새벽 감성의 여운 충분한가 |
| duration 불일치 | 목소리 톤 적절한가 |
| 오디오 트랙 누락 | 감정선 과장 여부 |
| CTA 오버레이 누락 | 브랜드 일관성 |
| visual anchor 소실 | 미묘한 감각 실패 vs 기술 실패 |
| 금지 요소 등장 | |

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `check_media_metadata` | 규칙 | duration/ratio/fps/audio 확인 |
| `vlm_structural_qa` | VLM | 구조화된 영상 품질 질의 |
| `check_anchor_consistency` | VLM | visual anchor 유지 확인 |
| `flag_prohibited_content` | VLM | 금지 요소 탐지 |

---

### 3.8 Orchestrator (오케스트레이터)

**역할**: 상태 흐름 제어, 재호출 결정, 반복 관리

**출력**:
- `terminal_status: TerminalStatus`
- `next_step`

```python
class TerminalStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    REVISE_REQUIRED = "revise_required"
    BLOCKED = "blocked"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
```

**Tools**:
| 도구 | 방식 | 설명 |
|------|------|------|
| `decide_next_step` | 규칙 (+LLM 보조) | 다음 호출 에이전트 결정 |
| `enforce_iteration_limit` | 규칙 | 반복 횟수 제한 |
| `enforce_budget` | 규칙 | 비용 예산 확인 |

---

## 4. 상태 흐름

### 기본 흐름 (Creative Planning Graph)

```
START
  |
story_writer         -> visual_anchor, shots_by_id
  |
stitch_planner       -> production_by_shot_id, stitch_plan, asset_manifest
  |
+------------------+------------------+------------------+
|                  |                  |                  |
copywriter     prompt_engineer   audio_director        | (fan-out 병렬)
|                  |                  |                  |
+------------------+------------------+------------------+
  |
plan_reviewer        -> plan_review (quality_score, issues)
  |
orchestrator         -> terminal_status / revision dispatch
  |
[auto_approved]  -> render_brief 출력 -> manual_assisted render
[needs_human_review] -> human gate
[revise_required]    -> cascade invalidation + 재실행
```

### Manual-Assisted Render Loop

```
render_brief 출력
  |
사람이 Sora/Runway/Veo에서 렌더
  |
결과 파일 업로드
  |
artifact_reviewer    -> deterministic checks + VLM QA
  |
[pass]          -> publish_review (human gate)
[fail_auto]     -> 재생성 제안 (자동 재생성 가능 항목)
[fail_manual]   -> 사람 검토
```

### API 모드 전환 시

```
render_brief -> API render executor -> artifact_reviewer -> ...
```

Planning contract 유지, QA contract 유지, provider adapter만 교체.

### 분기 흐름 (Cascade Invalidation)

```
orchestrator 결과:
  [auto_approved]           -> END (render_brief 출력)
  [needs_human_review]      -> END (human gate)
  [revise_story]            -> story_writer + cascade(stitch, copy, prompt, audio)
  [revise_stitch]           -> stitch_planner + cascade(prompt, audio)
  [revise_copy]             -> copywriter
  [revise_prompt]           -> prompt_engineer
  [revise_audio]            -> audio_director
  [max_iterations_reached]  -> END
  [blocked]                 -> END
```

**Cascade 규칙**:
```python
INVALIDATION_CASCADE = {
    "story_writer":     ["stitch_planner", "copywriter", "prompt_engineer", "audio_director"],
    "stitch_planner":   ["prompt_engineer", "audio_director"],
    "copywriter":       [],
    "prompt_engineer":  [],
    "audio_director":   [],
}
```

---

## 5. 상태 구조

### 5.1 VideoAgentState (v4 - shot_id 기반)

```python
class VideoAgentState(TypedDict):
    # === Input: CreativeBrief ===
    account_id: str
    intent: str                        # ad | explainer | brand | trend
    services: list[str]                # ["sora", "runway", "veo"]
    platforms: list[str]               # ["instagram_reel", "tiktok", "youtube_shorts"]
    execution_mode: str                # "manual_assisted" | "api"

    # Intent-specific payload (CreativeBrief)
    creative_brief: CreativeBrief      # 풍부한 입력 스키마

    # === Context ===
    identity: dict
    account_config: dict
    weekly_slot: dict | None

    # === Reserved Marketing Fields (현재 코어 분기 로직에 사용하지 않음) ===
    # 향후 마케팅 레이어에서 주입/사용. 현재는 전달/저장만 보장.
    campaign_context: dict | None
    performance_hints: list[str]
    experiment_vars: dict | None

    # === Planning (shot_id 기반) ===
    visual_anchor: str
    shots_by_id: dict[str, dict]       # Dict[shot_id, ShotDraft]
    shot_order: list[str]              # shot_id 순서 보존

    # === Production (shot_id 기반) ===
    production_by_shot_id: dict[str, dict]  # Dict[shot_id, ProductionSpec]
    continuity_refs: dict                    # ContinuityRefs
    stitch_plan: dict                        # StitchPlan
    asset_manifest: list[dict]               # list[AssetItem]

    # === Copy (shot_id 기반) ===
    copy_by_shot_id: dict[str, dict]   # Dict[shot_id, CopyBundle]

    # === Prompt (shot_id 기반) ===
    prompts_by_shot_id: dict[str, dict]  # Dict[shot_id, PromptBundle]

    # === Audio (shot_id 기반) ===
    audio_by_shot_id: dict[str, dict]  # Dict[shot_id, AudioSpec]

    # === Plan Review ===
    plan_review: dict                  # PlanReviewResult
    revision_issues: list[dict]        # list[ReviewIssue] - 구조화된 이슈

    # === Artifact Review (렌더 후) ===
    artifact_review: dict | None       # ArtifactReviewResult

    # === Control ===
    terminal_status: str               # TerminalStatus enum value
    iteration_count: int
    max_iterations: int
    auto_approve_threshold: float
    human_review_threshold: float

    # === Cost Tracking (분리된 메트릭) ===
    llm_calls_used: Annotated[int, operator.add]
    tokens_used_estimate: Annotated[int, operator.add]
    cost_usd_estimate: Annotated[float, operator.add]
    cost_budget_usd: float             # 최대 허용 비용
```

---

## 6. 데이터 계약

### 6.1 CreativeBrief (풍부한 입력 스키마)

**설계 원칙**: CreativeBrief는 코어 엔진이 직접 사용하는 필드와, 향후 마케팅 레이어가 주입하는 optional reserved 필드를 함께 가진다.
단, reserved 필드는 현재 planning/QA 로직의 필수 분기 조건으로 사용하지 않는다.

| 구분 | 필드 | 현재 단계 사용 여부 |
|------|------|-------------------|
| **Core** | account_id, intent, platforms, services, execution_mode, target_duration_sec, audience, emotional_target, message_pillar | 필수 |
| **Core optional** | product_surface, cta_policy, brand_rules_ref | 코어에서 참조 가능 |
| **Reserved** | objective, series_id | 전달/저장만, 코어 분기 조건 아님 |

```python
@dataclass
class CreativeBrief:
    """intent별 payload를 가진 입력 스키마.
    마케터 레이어가 이 비디오 엔진 위에 깔끔하게 올라가기 위한 인터페이스."""

    account_id: str
    intent: str                        # ad | explainer | brand | trend
    objective: str = ""                # "install" | "engagement" | "awareness"
    audience: str = ""                 # "20s night owls"
    emotional_target: str = ""         # "lonely but calm"
    message_pillar: str = ""           # "someone's voice at late night"
    proof_points: list[str] = field(default_factory=list)
    product_surface: str = ""          # "app_ui_light" | "none"
    cta_policy: str = "soft"           # "soft" | "direct" | "none"
    target_duration_sec: float = 15.0
    platforms: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    execution_mode: str = "manual_assisted"
    series_id: str | None = None
    brand_rules_ref: str | None = None
```

### 6.2 ShotDraft

```python
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
```

### 6.3 ProductionSpec (shot별 제작 레시피)

```python
@dataclass
class ProductionSpec:
    shot_id: str
    production_mode: str               # pure_video | keyframe_motion | image_stitch | hybrid_segment

    render_recipe: RenderRecipe
    fallback_recipe: RenderRecipe | None = None

@dataclass
class RenderRecipe:
    image_service: str | None = None   # "midjourney" | "flux" | None
    motion_service: str | None = None  # "runway_api" | "sora_api" | "veo_api" | None
    stitch_engine: str | None = None
    audio_strategy: str = "silent_visual"
    continuity_ref_source: str = ""
```

### 6.4 Provider/Service/Platform 계약 (3층 출력)

#### Layer 1: Master Creative Plan
- 이야기와 감정선, 샷 구조, visual anchor, copy intent

#### Layer 2: Platform Variant Spec (P1 — delivery adaptation)

> `platform_variants`는 **마케팅 전략 레이어가 아니라 delivery/output adaptation 레이어**다.
> 따라서 본 코어 문서 범위에 포함한다. 다만 초기 단계에서는 reserved field (`[]`)로만 제공한다.
```python
@dataclass
class PlatformVariantSpec:
    platform: str                      # "instagram_reel" | "tiktok" | "youtube_shorts"
    duration_sec: float
    safe_zone: dict                    # {"top": 80, "bottom": 120}
    hook_strategy: str                 # "visual_first_2s" | "text_overlay"
    end_card_type: str                 # "cta_card" | "fade_out" | "loop"
    cta_placement: str                 # "overlay_bottom" | "end_screen"
    caption_max_length: int
    thumbnail_frame_shot_id: str | None = None
```

#### Layer 3: Service Render Recipe
```python
@dataclass
class ServiceRenderSpec:
    provider: str                      # "sora_app" | "sora_api" | "runway_app" | "runway_api" | "veo_api"
    execution_mode: str                # "manual_assisted" | "api"
    audio_strategy: str
    supported_ratios: list[str]        # ["9:16", "16:9", "1:1"]
    supported_durations: list[float]   # [4, 8, 12] (Sora API) | [4, 6, 8] (Veo)
    reference_asset_method: str        # "start_image" | "start_end_image" | "none"
    max_duration_per_clip: float
    native_audio: bool
```

### 6.5 ReviewIssue (구조화된 이슈)

```python
@dataclass
class ReviewIssue:
    """키워드 매칭이 아닌 구조화된 이슈 코드 기반"""
    code: str                          # "continuity.lighting_drift" | "copy.hook_weak"
    severity: str                      # "critical" | "high" | "medium" | "low"
    target_agents: list[str]           # ["stitch_planner", "prompt_engineer"]
    shot_ids: list[str] = field(default_factory=list)  # 관련 샷
    description: str = ""
```

**이슈 코드 체계**:
```
story.arc_weak
story.anchor_missing
continuity.lighting_drift
continuity.character_drift
production.recipe_mismatch
production.duration_overflow
copy.hook_weak
copy.tone_violation
copy.brand_violation
prompt.quality_low
prompt.negative_missing
audio.strategy_mismatch
audio.voiceover_missing
```

### 6.6 StitchPlan, ContinuityRefs, AssetManifest

(v3에서 변경 없음, shot_id 기반으로 참조 방식만 변경)

```python
@dataclass
class StitchPlan:
    strategy: str                      # "sequential" | "parallel" | "hybrid"
    segments: list[StitchSegment]
    total_duration_sec: float
    transition_style: str

@dataclass
class StitchSegment:
    segment_id: str
    shot_ids: list[str]
    method: str                        # production_mode
    transition_in: str
    transition_out: str
    duration_sec: float
    assets_required: list[str] = field(default_factory=list)
    processing_notes: str = ""

@dataclass
class ContinuityRefs:
    character: CharacterRef
    setting: SettingRef
    lighting: LightingRef
    color_palette: list[str] = field(default_factory=list)
```

### 6.7 AssetItem

```python
@dataclass
class AssetItem:
    asset_id: str
    type: str                          # "image" | "video" | "audio"
    shot_ids: list[str]
    generation_service: str
    prompt_ref: str                    # shot_id 기반 참조
    status: str                        # "pending" | "generated" | "failed"
    depends_on: list[str] = field(default_factory=list)  # job dependency
    estimated_cost_usd: float = 0.0
    file_path: str | None = None
```

---

## 7. Provider Capabilities Registry

```python
@dataclass
class ProviderCapability:
    provider_id: str                   # "sora_app" | "sora_api" | "runway_api" | "veo_api"
    display_name: str
    execution_modes: list[str]         # ["manual_assisted"] | ["api"] | ["manual_assisted", "api"]

    # Video generation
    supported_ratios: list[str]
    supported_durations: list[float]
    max_duration_per_clip: float
    supports_start_image: bool
    supports_end_image: bool

    # Audio
    native_audio: bool
    post_audio_api: bool               # 별도 오디오 API 지원 여부

    # Reference
    supports_reference_image: bool
    supports_first_last_frame: bool

PROVIDER_CAPABILITIES = {
    "sora_app": ProviderCapability(
        provider_id="sora_app",
        display_name="Sora (App)",
        execution_modes=["manual_assisted"],
        supported_ratios=["9:16", "16:9", "1:1"],
        supported_durations=[5, 10, 15, 20],  # 앱: 최대 20초 편집
        max_duration_per_clip=20.0,
        supports_start_image=True,
        supports_end_image=False,
        native_audio=True,
        post_audio_api=False,
        supports_reference_image=True,
        supports_first_last_frame=False,
    ),
    "sora_api": ProviderCapability(
        provider_id="sora_api",
        display_name="Sora (API)",
        execution_modes=["api"],
        supported_ratios=["1080x1920", "1920x1080", "1080x1080"],
        supported_durations=[4, 8, 12],       # API: 4/8/12초
        max_duration_per_clip=12.0,
        supports_start_image=True,
        supports_end_image=False,
        native_audio=True,
        post_audio_api=False,
        supports_reference_image=True,
        supports_first_last_frame=False,
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
        post_audio_api=False,
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
        post_audio_api=True,              # 별도 SFX/TTS/dubbing API
        supports_reference_image=True,
        supports_first_last_frame=False,
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
        supports_first_last_frame=False,
    ),
}
```

---

## 8. 파일 구조

```
picko/video/
+-- agents/
|   +-- __init__.py
|   +-- graph.py              # LangGraph 상태머신
|   +-- state.py              # VideoAgentState
|   +-- schemas.py            # ShotDraft, ProductionSpec, CreativeBrief 등
|   +-- providers.py          # ProviderCapability, PROVIDER_CAPABILITIES
|   |
|   +-- nodes/
|   |   +-- __init__.py
|   |   +-- base.py           # safe_node wrapper
|   |   +-- story_writer.py
|   |   +-- copywriter.py
|   |   +-- prompt_engineer.py
|   |   +-- stitch_planner.py
|   |   +-- audio_director.py   # NEW
|   |   +-- plan_reviewer.py    # RENAMED from reviewer.py
|   |   +-- artifact_reviewer.py # NEW
|   |   +-- publish_reviewer.py  # NEW (human gate)
|   |   +-- orchestrator.py
|   |
|   +-- tools/
|   |   +-- __init__.py
|   |   +-- base.py           # BaseTool
|   |   +-- story.py
|   |   +-- copy.py
|   |   +-- prompt.py
|   |   +-- stitch.py
|   |   +-- audio.py          # NEW
|   |   +-- review.py
|   |   +-- artifact_qa.py    # NEW (deterministic + VLM)
|   |   +-- orchestrate.py
|   |
|   +-- prompts/
|       +-- story_writer.md
|       +-- copywriter.md
|       +-- prompt_engineer.md
|       +-- stitch_planner.md
|       +-- audio_director.md  # NEW
|       +-- plan_reviewer.md   # RENAMED
|       +-- orchestrator.md
```

---

## 9. 기존 시스템 통합

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
- `picko/video/quality_scorer.py` - 품질 평가 로직 (Plan Reviewer에서 재사용)
- `picko/account_context.py` - identity, weekly_slot
- `picko/llm_client.py` - get_writer_client()

### VideoPlan 확장 전략 (옵션 A: 모델 확장)

```python
@dataclass
class VideoPlan:
    # ... 기존 필드 ...

    # NEW: Production fields
    stitch_plan: StitchPlan | None = None
    asset_manifest: list[AssetItem] = field(default_factory=list)
    production_specs: dict = field(default_factory=dict)  # shot_id -> ProductionSpec
    audio_specs: dict = field(default_factory=dict)       # shot_id -> AudioSpec
    render_briefs: list[dict] = field(default_factory=list)  # 서비스별 렌더 브리프
    platform_variants: list[dict] = field(default_factory=list)  # P1 reserved field
```

---

## 10. 구현 단계

### Phase 1. Foundation
- [ ] `agents/` 디렉토리 구조 생성
- [ ] `VideoAgentState` (shot_id 기반) 정의
- [ ] `CreativeBrief`, `ShotDraft`, `ProductionSpec` 스키마 정의
- [ ] `ProviderCapability` + `PROVIDER_CAPABILITIES` 정의
- [ ] `TerminalStatus` enum 정의
- [ ] `ReviewIssue` 구조화된 이슈 스키마 정의
- [ ] LangGraph 기본 graph 구축
- [ ] Legacy fallback 유지

### Phase 2. Core Planning Flow
- [ ] `story_writer` node + tools
- [ ] `stitch_planner` node + tools (recipe-based)
- [ ] `prompt_engineer` node + tools
- [ ] `audio_director` node + tools
- [ ] `copywriter` node + tools
- [ ] 선형 + fan-out flow 구현

### Phase 3. Review & Control Loop
- [ ] `plan_reviewer` node + tools (기존 scorer 재사용)
- [ ] `orchestrator` node + tools
- [ ] 구조화된 이슈 기반 revision routing
- [ ] Cascade invalidation
- [ ] Terminal status 기반 종료 로직

### Phase 4. Artifact Review & Manual Loop
- [ ] `artifact_reviewer` - deterministic checks
- [ ] `artifact_reviewer` - VLM QA (Gemini)
- [ ] Render brief 출력 포맷
- [ ] Manual upload -> artifact review 흐름
- [ ] Human gate 연동

### Phase 5. Integration & Testing
- [ ] `VideoGenerator` 연동
- [ ] `_state_to_plan()` 변환 (shot_id 기반)
- [ ] Tool 단위 테스트
- [ ] Graph 통합 테스트
- [ ] Revision loop 테스트
- [ ] Legacy compatibility 테스트

### Phase 6. (P1) Platform & Enhancement
- [ ] Platform Variant Builder
- [ ] Vault retrieval (과거 anchor/시리즈 재사용)
- [ ] Intent-specific rubric (ad/brand/trend/explainer 분리)
- [ ] Asset manifest job DAG

---

## 11. 검증 기준

### 성공 조건

- 최소 1개의 `visual_anchor` 생성
- 샷 구조가 유효해야 함 (shot_id 기반, 순서 보존)
- 카피/프롬프트/오디오가 샷과 shot_id로 연결
- 각 shot에 `ProductionSpec` (production_mode + render_recipe) 지정
- `audio_strategy`가 모든 shot에 지정
- Plan Reviewer가 구조화된 이슈 코드로 검수 결과 출력
- `terminal_status` enum으로 종료 상태 명확
- 비용 추적 3개 메트릭 (llm_calls, tokens, cost_usd) 분리
- 최대 반복 횟수 내 종료

---

## 12. 설정 파일

```yaml
# config/video_agents.yml
defaults:
  quality_threshold: 70
  max_iterations: 3
  human_review_threshold: 60
  auto_approve_threshold: 85
  cost_budget_usd: 1.00

execution:
  default_mode: manual_assisted       # manual_assisted | api

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
  audio_director:
    temperature: 0.5
    max_tokens: 1500
  plan_reviewer:
    temperature: 0.2
    max_tokens: 1500
  artifact_reviewer:
    vlm_provider: gemini              # gemini | gpt4
    max_segments_per_review: 5
  orchestrator:
    temperature: 0.0
    max_tokens: 500

providers:
  # 기본 활성화 서비스 (execution_mode에 따라 필터)
  manual_assisted: ["sora_app", "runway_app"]
  api: ["sora_api", "runway_api", "veo_api"]
```

---

## 13. 운영 모드 전환 설계

### 단계 1: 구독형 수동-보조 렌더 (현재)
- Story/Copy/Prompt/Audio plan 자동 생성
- **render_brief** 출력 (서비스별 렌더 지침서)
- 사람이 Sora/Runway/Veo에서 렌더
- 결과 업로드

### 단계 2: 자동 QA
- Deterministic checks (규칙)
- Gemini 기반 Artifact Reviewer (VLM)
- Plan 대비 점검
- 재생성 제안 (bounded autonomy)

### 단계 3: 사람 최종 승인
- 감성/브랜드/리스크 확인
- 게시용 변형 승인

### 단계 4: API 모드 전환
- `execution_mode = "api"` 변경
- Planning contract 유지, QA contract 유지
- **Provider adapter만 교체** (render_brief -> API call)

---

## 14. 변경 이력

### v4 (전문가 리뷰 반영 - production loop, v2 아키텍처)

| 항목 | v3 | v4 |
|------|-----|-----|
| 상태 스키마 | 배열 인덱스 기반 | **shot_id 기반** (Dict[shot_id, ...]) |
| generation_method | 단일 서비스 capability 판단 | **2단 recipe selection** (production_mode + render_recipe + fallback) |
| Reviewer | 단일 Reviewer | **Plan Reviewer + Artifact Reviewer + Human Gate** 3단 분리 |
| 오디오 | 없음 | **Audio Director** 에이전트 + `audio_strategy` 4종 |
| terminal status | `approved` + `human_review_required` boolean | **TerminalStatus enum** 5종 |
| revision routing | 키워드 매칭 (`_ISSUE_AGENT_MAP`) | **구조화된 이슈 코드** (`ReviewIssue.code`) |
| 비용 추적 | `llm_calls` vs `token_budget` (단위 불일치) | **llm_calls + tokens_used + cost_usd** 3개 분리 |
| 입력 스키마 | `account_id` + `intent` (얇음) | **CreativeBrief** (intent별 payload) |
| 실행 모드 | 없음 | **execution_mode** (manual_assisted / api) |
| Provider 계약 | `SERVICE_CONSTRAINTS` (서비스 제약) | **ProviderCapability** (provider/app/api 구분) |
| 출력 계층 | 단일 VideoPlan | **3층** (Master Plan + Platform Variant + Service Recipe) |
| VLM QA | 없음 | **3층 QA** (deterministic + VLM + human gate) |
| Provider registry | 없음 | **PROVIDER_CAPABILITIES** (Sora app/api, Veo, Runway app/api) |

### v3 (P0-P3 구현 가이드 반영)

| 항목 | v2 | v3 |
|------|-----|-----|
| SERVICE_CONSTRAINTS 참조 | 없음 | select_generation_method에서 직접 조회 |
| 에이전트 순서 (fan-out) | 순차 | copywriter + prompt_engineer 병렬 |
| Cascade invalidation | 없음 | INVALIDATION_CASCADE 규칙 |
| 에러 처리 | 없음 | safe_node 래퍼 |
| Reviewer-Scorer 통합 | 없음 | 임시 VideoPlan 구성 후 기존 Scorer 재사용 |

### v2 (리뷰 반영)

| 항목 | v1 | v2 |
|------|-----|-----|
| 마케팅 확장 포인트 | 없음 | campaign_context, performance_hints, experiment_vars |
| 에이전트 순서 | prompt -> stitch | stitch -> prompt |
| StitchPlan 계약 | dict (느슨함) | 명시적 계약 |

### v1 (초안)

- 6개 에이전트, Director를 Reviewer + Orchestrator로 분리
- Stitch Planner 추가
