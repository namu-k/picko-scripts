# Twitter Image Prompt (Output-Fixed)

Generate one Twitter/X card image prompt from the input.

## Input
- Title: {{ title }}
- Summary: {{ summary }}
- Tags: {{ tags | join(", ") }}

## Channel Spec
- Aspect Ratio: {{ image_specs.aspect_ratio }}
- Style Direction: {{ image_specs.style }}
- Recommended Size: {{ image_specs.recommended_size }}
- Layout Hints:
{% for hint in image_specs.layout_hints %}
  - {{ hint }}
{% endfor %}

## Twitter Optimization Rules
- First-glance clarity: subject must be recognizable within 1 second
- Leave clear negative space for optional headline overlay
- Strong focal contrast for feed-stopping visibility
- Keep composition simple: one primary subject, one secondary support element
- Avoid crowded scenes and tiny details that collapse in mobile feed
- No visible text, no watermark, no logo artifacts in generated image

## Required Output Format (Return exactly these 6 blocks)
[MAIN_PROMPT]
<Production-ready English prompt optimized for Twitter card image>

[NEGATIVE_PROMPT]
<Comma-separated exclusions>

[FOCAL_SUBJECT]
<Primary subject in 1 line>

[COMPOSITION]
<Framing, camera distance, safe-space placement>

[STYLE_KEYWORDS]
<5-8 keywords, comma-separated>

[COLOR_PALETTE]
<background, primary, accent, optional highlight>
