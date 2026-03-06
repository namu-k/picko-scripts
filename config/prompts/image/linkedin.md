# LinkedIn Image Prompt (Output-Fixed)

Generate one LinkedIn feed image prompt from the input.

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

## LinkedIn Optimization Rules
- Business context must be immediately clear (professional scenario, product, workflow, or data insight)
- Prioritize clean hierarchy and analytical readability over decoration
- Keep a clear safe area for optional headline overlay
- Use one primary concept with one supporting visual cue (chart, UI panel, framework, or object)
- Avoid visual gimmicks and cluttered multi-subject scenes
- No visible text, no watermark, no logo artifacts in generated image

## Required Output Format (Return exactly these 6 blocks)
[MAIN_PROMPT]
<Production-ready English prompt optimized for LinkedIn feed image>

[NEGATIVE_PROMPT]
<Comma-separated exclusions>

[PRIMARY_MESSAGE_VISUAL]
<What single business idea should be instantly understood>

[COMPOSITION]
<Framing, information hierarchy, safe-space placement>

[STYLE_KEYWORDS]
<5-8 keywords, comma-separated>

[COLOR_PALETTE]
<background, primary, accent, optional highlight>
