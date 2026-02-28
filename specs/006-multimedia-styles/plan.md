# Implementation Plan: 006-Multimedia-Styles

## Overview

다양한 시각적 스타일을 지원하는 확장 가능한 멀티미디어 템플릿 시스템 구현.

**목표**: "사람이 디자인한 것 같은" 퀄리티의 이미지 생성

---

## Architecture Summary

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

### Style Categories

| Style | Description | Templates |
|-------|-------------|-----------|
| **Minimal** | 텍스트 위주, 단순 배경 (현재) | quote, card, list, data, carousel |
| **Photogram** | 실제 사진 + 텍스트 오버레이 | quote_photo, card_photo, hero_photo |
| **Illustrated** | 추상 도형, 패턴, 그라디언트 | quote_shapes, card_abstract, gradient_wave |
| **Corporate** | 비즈니스 프레젠테이션 | infographic, timeline, comparison |

---

## Implementation Order

### Phase 1: Foundation (P0) - 우선순위

#### Step 1: Image Source Module (1.2)

**목적**: 배경 이미지 검색 및 캐시 시스템

**파일**:
- `picko/image_source.py` - 신규 모듈
- `config/image_sources.yml` - API 설정

**작업**:
1. `ImageSourceManager` 클래스 구현
2. Unsplash API 연동 (`search_unsplash()`)
3. 이미지 캐시 시스템 (`cache/images/unsplash/`)
4. 환경 변수 로드 (`UNSPLASH_ACCESS_KEY`)

**API 스펙**:
```python
class ImageSourceManager:
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

**캐시 구조**:
```
cache/
└── images/
    ├── unsplash/
    │   ├── {image_id}.jpg
    │   └── meta.json
    └── pexels/
        ├── {image_id}.jpg
        └── meta.json
```

---

#### Step 2: Layer System (1.1)

**목적**: 다층 레이어 HTML 구조

**파일**:
- `templates/images/styles/_layer_base.html` - 공통 베이스
- `templates/images/styles/_layer.css` - 레이어 CSS

**HTML 구조**:
```html
<div class="media-container">
  <!-- Background Layer -->
  <div class="layer-background">
    <img src="{{ background_image }}" class="bg-image">
  </div>
  
  <!-- Overlay Layer -->
  <div class="layer-overlay"></div>
  
  <!-- Decoration Layer -->
  <div class="layer-decoration">
    {% for shape in decoration.shapes %}
    <div class="shape shape-{{ shape.type }}"></div>
    {% endfor %}
  </div>
  
  <!-- Content Layer -->
  <div class="layer-content">
    {% block content %}{% endblock %}
  </div>
</div>
```

**CSS 스펙**:
```css
.media-container { position: relative; }
.layer-background { z-index: 1; }
.layer-overlay { z-index: 2; }
.layer-decoration { z-index: 3; }
.layer-content { z-index: 4; }
```

---

#### Step 3: Photogram Style (1.3)

**목적**: 사진 기반 템플릿 구현

**파일**:
- `config/layouts/styles/photogram.yml`
- `templates/images/styles/photogram/quote_photo.html`
- `templates/images/styles/photogram/card_photo.html`
- `templates/images/styles/photogram/hero_photo.html`

**설정 예시**:
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

---

#### Step 4: Input Schema + CLI (1.4, 1.5)

**목적**: 사용자 인터페이스 확장

**파일**:
- `picko/multimedia_io.py` - 스키마 확장
- `scripts/render_media.py` - CLI 옵션 추가

**입력 포맷 확장**:
```yaml
---
id: mm_001
account: socialbuilders
style: photogram        # NEW
template: quote_photo   # NEW
channels: [linkedin, twitter]
---

## 이미지 키워드    # NEW
business, clock, productivity

## 장식 요소        # NEW
shapes: [circle, line]
accent_color: "#3b82f6"
```

**CLI 확장**:
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

---

#### Step 5: Tests (1.6)

**파일**:
- `tests/test_image_source.py`
- `tests/test_photogram_templates.py`

**테스트 케이스**:
1. Unsplash 검색 → 이미지 반환
2. 캐시 적중 → 재다운로드 없음
3. 템플릿 렌더링 → PNG 생성
4. E2E: 입력 → 렌더링 완료

---

## Phase 2: Expansion (P1)

### 2.1 Illustrated Style
- 추상 도형, 그라디언트 템플릿
- `config/layouts/styles/illustrated.yml`

### 2.2 SVG Decoration System
- `picko/decorations.py` 모듈
- SVG 도형 라이브러리 (circle, triangle, blob, wave)

### 2.3 Additional Image Sources
- Pexels API 연동
- 로컬 이미지 라이브러리 지원

---

## Phase 3: Corporate (P2)

### 3.1 Corporate Style
- 인포그래픽, 타임라인 템플릿

### 3.2 Data Visualization
- Chart.js 또는 SVG 차트 지원 검토

---

## File Structure

```
config/
├── layouts/
│   └── styles/           # NEW
│       ├── minimal.yml
│       ├── photogram.yml
│       └── illustrated.yml
├── image_sources.yml     # NEW

picko/
├── image_source.py       # NEW
├── decorations.py        # NEW (Phase 2)
└── multimedia_io.py      # MODIFY

templates/
└── images/
    └── styles/           # NEW
        ├── _layer_base.html
        ├── _layer.css
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

cache/
└── images/               # NEW
    ├── unsplash/
    └── pexels/
```

---

## Dependencies

### New Python Packages
```
requests  # Unsplash/Pexels API 호출
```

### External APIs
- Unsplash API (무료: 50회/시간)
- Pexels API (무료: 200회/시간)

### Environment Variables
```bash
UNSPLASH_ACCESS_KEY=xxx
UNSPLASH_SECRET_KEY=xxx
PEXELS_API_KEY=xxx
```

---

## Success Criteria

1. **다양성**: 최소 3개 스타일 카테고리, 15개 이상 템플릿
2. **품질**: "사람이 디자인한 것 같은" 비주얼 퀄리티
3. **확장성**: 새 스타일 추가가 설정 파일만으로 가능
4. **성능**: 이미지 캐시로 동일 키워드 재검색 없음
5. **사용성**: CLI에서 `--style` 옵션으로 쉽게 전환

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API 호출 한도 | 캐시 + 로컬 폴백 |
| 이미지 저작권 | Unsplash/Pexels 라이선스 준수 |
| 렌더링 속도 | 이미지 최적화, WebP 지원 |
| 템플릿 복잡도 | 레이어 분리로 관리 |

---

*Created: 2026-02-28*
*Branch: 006-multimedia-styles*
