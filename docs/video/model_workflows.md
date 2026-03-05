# Model-Specific Video Generation Workflows

This document defines service-specific generation workflows used by Picko video planning.
Runtime prompt generation references `config/prompts/video/model_workflows.md`, which is the operational subset of this document.

## Scope

- Services: Luma, Runway, Pika, Kling, Veo, Sora
- Modes: text-to-video, image-to-video
- Goal: deterministic shot-level planning with service-native controls

## Cross-Model Workflow Baseline

1. Define intent and hook: lock first 3 seconds and CTA strategy.
2. Break into shot graph: intro -> main -> cta with explicit shot purpose.
3. Assign camera/motion controls: use service-specific control fields.
4. Apply negative constraints: block text artifacts, watermark, geometry drift.
5. Run QA loop: ratio, duration, motion intensity, CTA compliance.

## Service Workflows

### Luma

- Primary flow (text-to-video): subject/environment/lighting -> camera motion -> mood/style.
- Control fields: `camera_motion`, `motion_intensity`, `style_preset`.
- Image mode: `start_image_url` and optional `end_image_url` can anchor trajectory.
- Operational rule: keep motion intensity bounded for close-up shots.

### Runway

- Primary flow (text-to-video supported by model variant): concise subject action + explicit camera move.
- Control fields: `camera_move`, `motion`, optional `seed`.
- Image mode: image-to-video flow expects image input and prompt focused on motion delta.
- Operational rule: normalize motion by shot scale (close-up lower, wide higher).

### Pika

- Primary flow: short social-ready shots with singular visual objective.
- Control fields: `pikaffect`, `style_preset`, `motion_intensity`.
- Image mode: use image references only when continuity or asset lock is required.
- Operational rule: use at most one major effect per shot.

### Kling

- Primary flow: camera-first phrasing, then action and environment.
- Control fields: `camera_motion`, `motion_intensity`, `style`.
- Image mode: use start/end frame references for controlled transitions.
- Operational rule: avoid long narrative per shot; single action per shot.

### Veo

- Primary flow: physical realism and clear action progression.
- Control fields: `generate_audio`, `audio_mood`, `style_preset`.
- Image mode: optional image reference where visual consistency is needed.
- Operational rule: if audio enabled, bind audio mood to shot emotion.

### Sora

- Primary flow: explicit scene progression and cinematic camera intent.
- Control fields: `style`, `camera_motion`.
- Image mode: optional image priming for scene anchors.
- Operational rule: keep language visual-first; avoid subtitle-like instructions.

## Notes on Start Image Requirements

- Start image is mode-dependent in practice: generally optional for text-to-video, used in image-to-video mode.
- Some model variants (for example certain Runway modes) may require image input.
- Picko should treat this as `service + mode (+ model_variant)` policy, not a single service-wide boolean.

## Source Trace (Research Snapshot)

- Runway developer/help docs (prompting and API usage)
- Luma official API/docs (text/image generation)
- Google Veo docs (Vertex/guide pages)
- OpenAI Sora developer guide/cookbook pages
- Kling and Pika official API/provider docs

Because vendor capabilities evolve quickly, this document should be reviewed periodically.
