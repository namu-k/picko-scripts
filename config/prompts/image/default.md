# Image Prompt Generator (Output-Fixed)

입력 콘텐츠를 바탕으로 SNS 카드용 단일 이미지 프롬프트를 생성하라.

## Input
- Title: {{ title }}
- Summary: {{ summary }}
- Tags: {{ tags | join(", ") }}

## Global Constraints
- Output language for prompt: English only
- Aspect ratio intent: 16:9 social card composition
- Keep center-safe area clean for optional text overlay
- No visible text inside image, no watermark, no logo artifacts
- Avoid vague adjectives without concrete visual elements

## Prompt Construction Rules
- Must include all 6 blocks in one coherent sentence flow:
  1) Subject
  2) Environment
  3) Composition/Camera
  4) Lighting/Color mood
  5) Style keywords
  6) Quality and constraints
- Prefer concrete nouns and actions over abstract slogans
- Color palette should be limited to 3-4 dominant colors
- Keep tone professional and platform-ready

## Required Output Format (Return exactly these 5 blocks)
[MAIN_PROMPT]
<One production-ready English prompt sentence or two short sentences>

[NEGATIVE_PROMPT]
<Comma-separated exclusions>

[STYLE_KEYWORDS]
<5-8 style keywords, comma-separated>

[MOOD]
<2-4 mood keywords, comma-separated>

[COLOR_PALETTE]
<background, primary, accent, optional highlight>
