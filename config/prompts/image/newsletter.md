# Newsletter Image Prompt (Output-Fixed)

Generate one newsletter hero image prompt from the input.

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

## Newsletter Hero Optimization Rules
- Hero intent first: image should communicate the issue's core topic at a glance
- Reserve generous headline-safe space for email title/subtitle overlay
- Use an editorial composition with strong focal point and calm background
- Prefer narrative clarity over decorative complexity
- Maintain brand-consistent tone and restrained palette
- No visible text, no watermark, no logo artifacts in generated image

## Required Output Format (Return exactly these 6 blocks)
[MAIN_PROMPT]
<Production-ready English prompt optimized for newsletter hero image>

[NEGATIVE_PROMPT]
<Comma-separated exclusions>

[HERO_FOCUS]
<Primary focal subject and supporting context>

[COMPOSITION]
<Header-safe area, focal placement, depth layering>

[STYLE_KEYWORDS]
<5-8 keywords, comma-separated>

[COLOR_PALETTE]
<background, primary, accent, optional highlight>
