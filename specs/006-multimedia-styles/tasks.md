# Tasks: 006-Multimedia-Styles

## Phase 1: Foundation (P0)

### 1.1 Layer System
- [ ] HTML 레이어 구조 정의 (background, overlay, decoration, content)
- [ ] `_layer_base.html` 공통 베이스 템플릿
- [ ] CSS 레이어 스타일 (z-index, positioning)

### 1.2 Image Source Module
- [ ] `picko/image_source.py` 모듈 생성
- [ ] `ImageSourceManager` 클래스 구현
- [ ] Unsplash API 연동 (`search_unsplash()`)
- [ ] 이미지 캐시 시스템 (`cache/images/`)
- [ ] 환경 변수 로드 (`UNSPLASH_ACCESS_KEY`)

### 1.3 Photogram Style
- [ ] `config/layouts/styles/photogram.yml` 설정
- [ ] `templates/images/styles/photogram/` 디렉토리
- [ ] `quote_photo.html` 템플릿
- [ ] `card_photo.html` 템플릿
- [ ] `hero_photo.html` 템플릿 (풀 스크린)

### 1.4 Input Schema Extension
- [ ] `multimedia_io.py`: `style`, `template`, `image_keywords` 필드 추가
- [ ] `MultimediaInput` dataclass 확장
- [ ] 파싱 로직 업데이트

### 1.5 CLI Updates
- [ ] `--style` 옵션 추가
- [ ] `--image-keywords` 옵션 추가
- [ ] `--image-source` 옵션 추가
- [ ] `styles` 서브커맨드 (사용 가능한 스타일 목록)

### 1.6 Tests
- [ ] `test_image_source.py`: Unsplash 검색, 캐시
- [ ] `test_photogram_templates.py`: 렌더링 테스트
- [ ] E2E: 전체 파이프라인 테스트

## Phase 2: Expansion (P1)

### 2.1 Illustrated Style
- [ ] `config/layouts/styles/illustrated.yml` 설정
- [ ] `templates/images/styles/illustrated/` 디렉토리
- [ ] `quote_shapes.html` (추상 도형)
- [ ] `card_abstract.html` (그라디언트 + 도형)
- [ ] `gradient_wave.html` (웨이브 패턴)

### 2.2 SVG Decoration System
- [ ] `picko/decorations.py` 모듈
- [ ] SVG 도형 라이브러리 (circle, triangle, blob, wave)
- [ ] 동적 색상 적용
- [ ] 랜덤 배치 알고리즘

### 2.3 Additional Image Sources
- [ ] Pexels API 연동
- [ ] 로컬 이미지 라이브러리 지원
- [ ] 이미지 소스 우선순위 설정

### 2.4 Tests
- [ ] `test_illustrated_templates.py`
- [ ] `test_decorations.py`

## Phase 3: Corporate (P2)

### 3.1 Corporate Style
- [ ] `config/layouts/styles/corporate.yml` 설정
- [ ] `templates/images/styles/corporate/` 디렉토리
- [ ] `infographic.html`
- [ ] `timeline.html`
- [ ] `comparison.html`

### 3.2 Data Visualization
- [ ] Chart.js 또는 SVG 차트 지원 검토
- [ ] 간단한 바차트, 파이차트 템플릿

### 3.3 Tests
- [ ] `test_corporate_templates.py`

## Documentation

- [ ] `config/layouts/README.md` 업데이트 (스타일 시스템)
- [ ] `CLAUDE.md` 업데이트 (새 CLI 옵션)
- [ ] `.env.example` 업데이트 (UNSPLASH_ACCESS_KEY)

## Dependencies

### New Python Packages
```
# requirements.txt 추가
requests  # Unsplash API 호출
```

### External APIs
- Unsplash API (무료: 50회/시간)
- Pexels API (무료: 200회/시간)
