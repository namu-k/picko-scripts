# Layout Configuration System

이미지 템플릿을 위한 YAML 기반 레이아웃 설정 시스템입니다.

## 개요

레이아웃 시스템을 통해 다음을 할 수 있습니다:
- 일관된 타이포그래피, 색상, 여백 설정
- 프리셋과 테마를 통한 스타일 재사용
- 템플릿별, 채널별 스타일 오버라이드
- CLI에서 실시간 스타일 변경

## 디렉토리 구조

```
config/layouts/
├── _defaults.yml          # 기본값 (모든 프리셋의 베이스)
├── presets/               # 프리셋 (독립적인 스타일 세트)
│   ├── minimal_dark.yml
│   ├── minimal_light.yml
│   └── social_gradient.yml
└── themes/                # 테마 (프리셋을 상속받아 오버라이드)
    └── socialbuilders.yml
```

## 설정 구조

### 기본 구조

```yaml
name: preset_name

typography:
  font_family: "'Noto Sans KR', sans-serif"
  title_size: 52          # px
  body_size: 28           # px
  caption_size: 20        # px
  title_weight: 700       # font-weight
  body_weight: 400
  line_height: 1.4

colors:
  primary: "#667eea"
  secondary: "#764ba2"
  background: "#0f0f23"
  surface: "#1a1a2e"
  text_primary: "#ffffff"
  text_secondary: "#a0aec0"
  text_muted: "#718096"
  accent: "#f093fb"
  gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
  overlay_color: "rgba(0, 0, 0, 0.6)"

spacing:
  body_padding: 80        # px
  gap: 24                 # px
  section_gap: 40         # px
  element_gap: 16         # px
  border_radius: 16       # px
  card_padding: 32        # px

# 템플릿별 오버라이드
template_overrides:
  quote:
    typography:
      title_size: 56
  data:
    colors:
      accent: "#fbbf24"
```

### 테마 (프리셋 상속)

```yaml
name: mytheme
extends: minimal_dark      # 상속받을 프리셋

# 오버라이드할 값만 지정
colors:
  primary: "#3b82f6"
  background: "#0f172a"

# 채널별 레이아웃 설정
channel_layouts:
  twitter:
    spacing:
      body_padding: 70
  linkedin:
    spacing:
      body_padding: 80
```

## 사용법

### Python API

```python
from picko.layout_config import LayoutConfigLoader, get_layout_for_template
from picko.templates import ImageRenderer

# 프리셋 로드
config = LayoutConfigLoader.load_preset("minimal_dark")

# 테마 로드
config = LayoutConfigLoader.load_theme("socialbuilders")

# 오버라이드와 함께 로드
config = get_layout_for_template(
    preset="minimal_dark",
    overrides=["colors.primary=#ff0000", "typography.title_size=64"]
)

# 렌더링에 적용
renderer = ImageRenderer()
html = renderer.render_image(
    template="quote",
    context={"quote": "테스트 문구"},
    layout_preset="minimal_dark"
)
```

### CLI

```bash
# 프리셋 사용
python -m scripts.render_media render --input input.md --layout minimal_dark

# 테마 사용
python -m scripts.render_media render --input input.md --theme socialbuilders

# 오버라이드
python -m scripts.render_media render --input input.md \
    --layout minimal_dark \
    --override colors.primary=#ff0000 \
    --override typography.title_size=64

# 결과를 파일로 저장
python -m scripts.render_media render --input input.md \
    --layout minimal_light \
    --output output.html
```

## 프리셋 목록

| 프리셋 | 설명 | 배경 | 용도 |
|--------|------|------|------|
| `minimal_dark` | 다크 미니멀 | #0f0f23 | 기본 다크 테마 |
| `minimal_light` | 라이트 미니멀 | #ffffff | 밝은 테마 |
| `social_gradient` | 소셜 그라디언트 | #0f0f23 | 눈에 띄는 소셜 미디어 |

## 테마 목록

| 테마 | 베이스 | 브랜드 컬러 |
|------|--------|-------------|
| `socialbuilders` | minimal_dark | #3b82f6 (블루) |

## CSS 변수 매핑

템플릿에서 사용할 수 있는 CSS 변수들:

```css
:root {
    /* Typography */
    --font-family
    --title-size
    --body-size
    --caption-size
    --title-weight
    --body-weight
    --line-height

    /* Colors */
    --color-primary
    --color-secondary
    --color-background
    --color-surface
    --color-text-primary
    --color-text-secondary
    --color-text-muted
    --color-accent
    --color-gradient
    --color-overlay

    /* Spacing */
    --body-padding
    --gap
    --section-gap
    --element-gap
    --border-radius
    --card-padding
}
```

## 새 프리셋 추가

1. `config/layouts/presets/`에 YAML 파일 생성
2. 필요한 값만 지정 (나머지는 defaults에서 상속)

```yaml
# config/layouts/presets/my_preset.yml
name: my_preset

colors:
  primary: "#ff6b6b"
  background: "#2d3436"
```

## 새 테마 추가

1. `config/layouts/themes/`에 YAML 파일 생성
2. `extends`로 베이스 프리셋 지정

```yaml
# config/layouts/themes/my_brand.yml
name: my_brand
extends: minimal_light

colors:
  primary: "#00cec9"
  accent: "#fd79a8"

channel_layouts:
  instagram:
    spacing:
      body_padding: 60
```
