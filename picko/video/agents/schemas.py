from dataclasses import dataclass, field


@dataclass
class CreativeBrief:
    account_id: str
    intent: str
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
    performance_hints: list[str] = field(default_factory=list)
    experiment_vars: dict[str, object] = field(default_factory=dict)


@dataclass
class ShotDraft:
    shot_id: str
    purpose: str
    scene_description: str
    subject: str
    setting: str
    lighting: str
    camera_intent: str
    motion_type: str = "static"
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
    production_mode: str
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
    service_specific_params: dict[str, object] = field(default_factory=dict)


@dataclass
class AudioSpec:
    audio_strategy: str
    voiceover_needed: bool = False
    voiceover_script: str | None = None
    silence_windows: list[tuple[float, float]] = field(default_factory=list)
    ambient_profile: str = ""
    bgm_profile: str = ""
    sfx_cues: list[dict[str, object]] = field(default_factory=list)
    caption_timing_ref: str | None = None


@dataclass
class ReviewIssue:
    code: str
    severity: str
    target_agents: list[str] = field(default_factory=list)
    shot_ids: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class PlanReviewResult:
    quality_score: float
    issues: list[ReviewIssue]
    feedback_notes: list[str] = field(default_factory=list)


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
    transition_style: str = ""


@dataclass
class ContinuityRefs:
    character: dict[str, object] = field(default_factory=dict)
    setting: dict[str, object] = field(default_factory=dict)
    lighting: dict[str, object] = field(default_factory=dict)
    color_palette: list[str] = field(default_factory=list)


@dataclass
class AssetItem:
    asset_id: str
    type: str
    shot_ids: list[str]
    generation_service: str
    prompt_ref: str
    status: str
    depends_on: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    file_path: str | None = None
