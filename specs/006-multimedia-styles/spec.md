# 006: Multimedia Template Styles System

## Overview

다양한 시각적 스타일을 지원하는 확장 가능한 멀티미디어 템플릿 시스템. 현재 미니멀 텍스트 위주 디자인에서 포토그램, 일러스트레이션, 코퍼레이트 등 다양한 스타일로 확장.

## Motivation

**현재 한계점:**
- 배경: 단색/그라디언트만 지원
- 레이어: 단일 레이어 구조
- 장식 요소: 없음
- 시각적 깊이: 그림자, 블러 효과 최소화
- 스타일 다양성: 7개 고정 템플릿

**목표:**
- "사람이 디자인한 것 같은" 퀄리티의 이미지 생성
- 다양한 스타일 카테고리 지원
- 배경 이미지, 패턴, 장식 요소 추가
- 확장 가능한 템플릿 아키텍처

## Style Categories

### 1. Minimal (현재)
- 텍스트 위주, 단순한 배경
- 템플릿: quote, card, list, data, carousel, social_quote, modern_card

### 2. Photogram (신규)
- 실제 사진 + 텍스트 오버레이
- 배경 이미지 소스: Unsplash, Pexels, 로컬
- 템플릿: quote_photo, card_photo, hero_photo

### 3. Illustrated (신규)
- 추상 도형, 패턴, 그라디언트
- SVG 기반 장식 요소
- 템플릿: quote_shapes, card_abstract, gradient_wave

### 4. Corporate (신규)
- 비즈니스 프레젠테이션 스타일
- 인포그래픽, 타임라인
- 템플릿: infographic, timeline, comparison

## Architecture

### Layer System

```
┌─────────────────────────────────┐
│   Content Layer (텍스트, 브랜드)   │  ← 최상위
├─────────────────────────────────┤
│   Decoration Layer (도형, 아이콘)  │
├─────────────────────────────────┤
│   Overlay Layer (어둡게, 블러)     │
├─────────────────────────────────┤
│   Background Layer (이미지, 색상)  │  ← 최하위
└─────────────────────────────────┘
```

### Configuration Schema

```yaml
# config/layouts/styles/photogram.yml
style: photogram
name: "Photogram Quote"

layers:
  background:
    type: image
    source: unsplash
    keywords: ["business", "startup", "technology"]
    blur: 0

  overlay:
    type: gradient
    gradient: "linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.7) 100%)"

  decoration:
    shapes: []
    icons: []

  content:
    alignment: center
    typography:
      title_size: 64
      title_color: "#ffffff"
      title_shadow: "0 4px 20px rgba(0,0,0,0.5)"
```

### Template Structure

```html
<!-- templates/images/styles/photogram/quote_photo.html -->
<div class="layer-background">
  <img src="{{ background_image }}" class="bg-image">
</div>
<div class="layer-overlay" style="background: {{ overlay_gradient }}"></div>
<div class="layer-decoration">
  {% for shape in decoration.shapes %}
  <div class="shape shape-{{ shape.type }}"></div>
  {% endfor %}
</div>
<div class="layer-content">
  <div class="quote">{{ quote }}</div>
  {% if author %}<div class="author">— {{ author }}</div>{% endif %}
</div>
```

## Image Source System

### Supported Sources

| Source | Type | API Required | Usage |
|--------|------|--------------|-------|
| Unsplash | 원격 | Yes (API Key) | 키워드 기반 검색 |
| Pexels | 원격 | Yes (API Key) | 키워드 기반 검색 |
| Local | 로컬 | No | 지정된 폴더에서 랜덤 선택 |
| Inline | Base64 | No | 템플릿에 직접 포함 |

### Image Selection Flow

```
1. 입력 템플릿에서 키워드 추출
   ↓
2. 키워드 → 이미지 소스 검색
   ↓
3. 이미지 다운로드/캐시
   ↓
4. 템플릿 렌더링에 이미지 경로 전달
```

### Cache Strategy

- 이미지 캐시: `cache/images/{source}/{image_id}.jpg`
- 메타데이터: `cache/images/{source}/meta.json`
- TTL: 7일 (재사용 최적화)

## Input Schema Extension

```yaml
# mm_xxx.md (확장된 입력 포맷)
---
id: mm_001
account: socialbuilders
style: photogram        # NEW: 스타일 카테고리
template: quote_photo   # NEW: 구체적 템플릿
channels: [linkedin, twitter]
---

## 주제/컨셉
창업자를 위한 시간 관리

## 포함할 텍스트
시간은 창업자의 가장 귀한 자산이다

## 이미지 키워드    # NEW: 배경 이미지 검색 키워드
business, clock, productivity

## 장식 요소        # NEW: 선택적 장식
shapes: [circle, line]
accent_color: "#3b82f6"
```

## CLI Extensions

```bash
# 스타일 지정
python -m scripts.render_media render --input mm.md --style photogram

# 이미지 키워드 오버라이드
python -m scripts.render_media render --input mm.md --image-keywords "startup,desk"

# 이미지 소스 지정
python -m scripts.render_media render --input mm.md --image-source unsplash

# 사용 가능한 스타일 목록
python -m scripts.render_media styles
```

## API Changes

### `ImageRenderer.render_image()` 확장

```python
def render_image(
    self,
    template: str,
    context: dict,
    layout_config: LayoutConfig | None = None,
    layout_preset: str | None = None,
    layout_theme: str | None = None,
    layout_overrides: list[str] | None = None,
    style: str = "minimal",           # NEW
    background_image: str | None = None,  # NEW
    image_keywords: list[str] | None = None,  # NEW
) -> str:
```

### 새 모듈: `picko/image_source.py`

```python
class ImageSourceManager:
    """Manage background image sources."""

    def search(
        self,
        keywords: list[str],
        source: str = "unsplash",
        orientation: str = "landscape",
    ) -> str:
        """Search and return cached image path."""

    def get_random_local(self, category: str) -> str:
        """Get random image from local library."""
```

## Implementation Phases

### Phase 1: Foundation (P0)
- [ ] 레이어 시스템 HTML 구조
- [ ] `image_source.py` 모듈 (Unsplash API)
- [ ] `photogram` 스타일 카테고리
- [ ] 입력 포맷 확장 (이미지 키워드)

### Phase 2: Expansion (P1)
- [ ] `illustrated` 스타일 카테고리
- [ ] SVG 장식 요소 시스템
- [ ] Pexels API 지원
- [ ] 로컬 이미지 라이브러리

### Phase 3: Corporate (P2)
- [ ] `corporate` 스타일 카테고리
- [ ] 인포그래픽 템플릿
- [ ] 타임라인, 비교 템플릿
- [ ] 차트/그래프 지원

## Configuration Files

### New Files

```
config/
├── layouts/
│   └── styles/           # NEW
│       ├── minimal.yml
│       ├── photogram.yml
│       └── illustrated.yml
├── image_sources.yml     # NEW: API 키, 기본 설정

templates/
└── images/
    └── styles/           # NEW
        ├── photogram/
        │   ├── quote_photo.html
        │   ├── card_photo.html
        │   └── hero_photo.html
        ├── illustrated/
        │   ├── quote_shapes.html
        │   └── card_abstract.html
        └── corporate/
            ├── infographic.html
            └── timeline.html
```

### Environment Variables

```bash
# .env
UNSPLASH_ACCESS_KEY=xxx
UNSPLASH_SECRET_KEY=xxx
PEXELS_API_KEY=xxx
```

## Success Criteria

1. **다양성**: 최소 3개 스타일 카테고리, 15개 이상 템플릿
2. **품질**: "사람이 디자인한 것 같은" 비주얼 퀄리티
3. **확장성**: 새 스타일 추가가 설정 파일만으로 가능
4. **성능**: 이미지 캐시로 동일 키워드 재검색 없음
5. **사용성**: CLI에서 `--style` 옵션으로 쉽게 전환

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API 호출 한도 | 캐시 + 로컬 폴백 |
| 이미지 저작권 | Unsplash/Pexels 라이선스 준수 |
| 렌더링 속도 | 이미지 최적화, WebP 지원 |
| 템플릿 복잡도 | 레이어 분리로 관리 |
