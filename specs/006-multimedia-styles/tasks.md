# Tasks: 006-Multimedia-Styles

## Status Legend
- ⬜ Not started
- 🔄 In progress
- ✅ Completed

---

## Phase 1: Foundation (P0)

### 1.1 Layer System
- ⬜ HTML 레이어 구조 정의 (background, overlay, decoration, content)
- ⬜ `templates/images/styles/_layer_base.html` 공통 베이스 템플릿
- ⬜ `templates/images/styles/_layer.css` 레이어 CSS

### 1.2 Image Source Module ⬅️ **START HERE**
- ⬜ `picko/image_source.py` 모듈 생성
- ⬜ `ImageSourceManager` 클래스 구현
- ⬜ Unsplash API 연동 (`search_unsplash()`)
- ⬜ 이미지 캐시 시스템 (`cache/images/unsplash/`, `meta.json`)
- ⬜ 캐시 TTL 설정 (7일)
- ⬜ 환경 변수 로드 (`UNSPLASH_ACCESS_KEY`)
- ⬜ `config/image_sources.yml` 설정 파일

### 1.3 Photogram Style
- ⬜ `config/layouts/styles/photogram.yml` 설정
- ⬜ `templates/images/styles/photogram/` 디렉토리
- ⬜ `quote_photo.html` 템플릿
- ⬜ `card_photo.html` 템플릿
- ⬜ `hero_photo.html` 템플릿 (풀 스크린)
- ⬜ `html_renderer.py` 스타일 파라미터 확장

### 1.4 Input Schema Extension
- ⬜ `multimedia_io.py`: `style`, `template`, `image_keywords` 필드 추가
- ⬜ `MultimediaInput` dataclass 확장
- ⬜ 파싱 로직 업데이트

### 1.5 CLI Updates
- ⬜ `--style` 옵션 추가
- ⬜ `--image-keywords` 옵션 추가
- ⬜ `--image-source` 옵션 추가
- ⬜ `styles` 서브커맨드 (사용 가능한 스타일 목록)

### 1.6 Tests
- ⬜ `test_image_source.py`: Unsplash 검색, 캐시 적중
- ⬜ `test_photogram_templates.py`: 템플릿 렌더링 → PNG 생성
- ⬜ E2E: 입력 → 렌더링 완료

---

## Phase 2: Expansion (P1)

### 2.1 Illustrated Style
- ⬜ `config/layouts/styles/illustrated.yml` 설정
- ⬜ `templates/images/styles/illustrated/` 디렉토리
- ⬜ `quote_shapes.html` (추상 도형)
- ⬜ `card_abstract.html` (그라디언트 + 도형)
- ⬜ `gradient_wave.html` (웨이브 패턴)

### 2.2 SVG Decoration System
- ⬜ `picko/decorations.py` 모듈
- ⬜ SVG 도형 라이브러리 (circle, triangle, blob, wave)
- ⬜ 동적 색상 적용
- ⬜ 랜덤 배치 알고리즘

### 2.3 Additional Image Sources
- ⬜ Pexels API 연동
- ⬜ 로컬 이미지 라이브러리 지원
- ⬜ 이미지 소스 우선순위 설정

### 2.4 Tests
- ⬜ `test_illustrated_templates.py`
- ⬜ `test_decorations.py`

---

## Phase 3: Corporate (P2)

### 3.1 Corporate Style
- ⬜ `config/layouts/styles/corporate.yml` 설정
- ⬜ `templates/images/styles/corporate/` 디렉토리
- ⬜ `infographic.html`
- ⬜ `timeline.html`
- ⬜ `comparison.html`

### 3.2 Data Visualization
- ⬜ Chart.js 또는 SVG 차트 지원 검토
- ⬜ 간단한 바차트, 파이차트 템플릿

### 3.3 Tests
- ⬜ `test_corporate_templates.py`

---

## Documentation

- ⬜ `config/layouts/README.md` 업데이트 (스타일 시스템)
- ⬜ `CLAUDE.md` 업데이트 (새 CLI 옵션)
- ✅ `.env.example` 업데이트 (UNSPLASH_ACCESS_KEY)
- ✅ `FOLLOWUPS.md` 업데이트 (006 작업 추가)
- ✅ `DEPLOYMENT.md` 업데이트 (Unsplash/Pexels API)
- ✅ `specs/006/plan.md` 구현 계획 작성

---

## Dependencies

### New Python Packages
```
# requirements.txt 추가
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

## Recommended Implementation Order

```
1. Image Source Module (1.2)    ← 기반 구축
   ↓
2. Layer System (1.1)           ← HTML/CSS 구조
   ↓
3. Photogram Style (1.3)        ← 템플릿 구현
   ↓
4. Input Schema + CLI (1.4-1.5) ← 사용자 인터페이스
   ↓
5. Tests (1.6)                  ← 검증
```

---

*Updated: 2026-02-28*
*Branch: 006-multimedia-styles*
