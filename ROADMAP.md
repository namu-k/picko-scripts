# Picko 제품화 로드맵

> 콘텐츠 파이프라인 자동화 시스템 → 이미지/영상 생성까지 확장

---

## 📋 목차

1. [현재 상태](#현재-상태)
2. [확장 목표](#확장-목표)
3. [이미지 생성 옵션](#이미지-생성-옵션)
4. [숏폼 동영상 생성](#숏폼-동영상-생성)
5. [AI 자동화 서비스 비교](#ai-자동화-서비스-비교)
6. [추천 조합](#추천-조합)
7. [구현 로드맵](#구현-로드맵)
8. [비용 요약](#비용-요약)

---

## 현재 상태

### 완료된 기능

```
RSS 수집 → NLP/스코어링 → 큐레이션 → 롱폼/팩 생성 → Obsidian Vault
```

| 기능 | 상태 | 모듈 |
|---|---|---|
| RSS 수집 | ✅ | `scripts/daily_collector.py` |
| NLP 처리 | ✅ | `picko/llm_client.py` (Ollama/OpenAI) |
| 스코어링 | ✅ | `picko/scoring.py` |
| 롱폼 생성 | ✅ | `scripts/generate_content.py` |
| 소셜 팩 | ✅ | `scripts/generate_content.py` |
| 이미지 프롬프트 | ✅ | `config/prompts/image/` |
| **이미지 생성** | ❌ | TBD |
| **영상 생성** | ❌ | TBD |

### 현재 기술 스택

```yaml
LLM:
  summary: Ollama (qwen2.5:3b) - 로컬
  writer: Relay (gpt-4o-mini) - 클라우드
  embedding: Ollama (qwen3-embedding:0.6b) - 로컬

Storage:
  vault: Obsidian Markdown + YAML frontmatter
  cache: cache/embeddings/
```

---

## 확장 목표

### Phase 1: 이미지 생성 (2-3주)

```
롱폼/팩 → 이미지 프롬프트 → 고품질 이미지 → 인스타/블로그용
```

**요구사항**:
- 감성적/몽환적 퀄리티
- 구도/배치 고려 (레이아웃)
- 텍스트 포함 이미지 가능
- 브랜드 일관성

### Phase 2: 숏폼 동영상 (4-6주)

```
롱폼/팩 → 대본 → TTS → 영상 소스 → 편집 → 릴스/쇼츠
```

**요구사항**:
- 60초 이내 숏폼
- AI 내레이션/아바타
- 플랫폼별 리사이징

### Phase 3: 통합 파이프라인 (2주)

```
RSS → NLP → 승인 → 롱폼 → [이미지 + 영상] → 게시
```

---

## 이미지 생성 옵션

### 옵션 A: 직접 구축 (API 조합)

#### A-1. DALL-E 3 + GPT-4o Vision (추천)

```
┌─────────────────────────────────────────────────────────┐
│   Claude 3.5 → 프롬프트 생성                            │
│        ↓                                                │
│   DALL-E 3 API → 이미지 + 텍스트 배치                   │
│        ↓                                                │
│   GPT-4o Vision → 레이아웃 QA                           │
│        ↓                                                │
│   PIL/Pillow → 인스타 사이즈 변환                       │
└─────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|---|---|
| **이미지 모델** | DALL-E 3 (OpenAI) |
| **QA 모델** | GPT-4o Vision |
| **가격** | $0.04/장 (HD), $0.08/장 (4K) |
| **월 예산** | $35-50 (일 3포스트) |
| **장점** | API 통합 용이, 텍스트 배치 가능, 기존 키 재사용 |
| **단점** | Midjourney 대비 감성 퀄리티 아쉬움 |

**설정 예시**:
```yaml
# config/config.yml
image:
  provider: "dalle"

  dalle:
    model: "dall-e-3"
    size: "1024x1024"
    quality: "hd"
    style: "natural"  # vivid | natural (감성은 natural)

  vision_qa:
    enabled: true
    model: "gpt-4o"
    min_score: 0.7

  style_guide:
    mood: "soft, dreamy, calm, warm"
    colors: ["#F5F5F5", "#E8E8E8", "#D4C5B9"]
    avoid: ["harsh contrasts", "neon", "busy backgrounds"]
```

---

#### A-2. Midjourney + Claude Vision (최고 퀄리티)

```
┌─────────────────────────────────────────────────────────┐
│   Claude 3.5 → 프롬프트 생성                            │
│        ↓                                                │
│   Midjourney v7 → 감성 이미지                           │
│        ↓                                                │
│   Claude 3.5 Vision → 레이아웃 QA                       │
│        ↓                                                │
│   Canva Pro → 텍스트/로고 배치                          │
└─────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|---|---|
| **이미지 모델** | Midjourney v7 |
| **가격** | $30/월 (Standard), $60/월 (Pro) |
| **장점** | 압도적 감성 퀄리티, 브랜드 스타일 학습 |
| **단점** | API 제한적 (Discord 의존), 자동화 복잡 |

**자동화 방법**:
- Apify Actor: $19/월
- 또는 Midjourney Web Editor + 수동

---

#### A-3. Ideogram + Gemini Vision (텍스트 특화)

```
┌─────────────────────────────────────────────────────────┐
│   Claude 3.5 → 카피 + 프롬프트                          │
│        ↓                                                │
│   Ideogram 2.0 API → 텍스트 포함 이미지                 │
│        ↓                                                │
│   Gemini 2.0 Flash → 타이포그래피 QA (초저가)           │
└─────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|---|---|
| **이미지 모델** | Ideogram 2.0 |
| **가격** | $8-10/월 |
| **텍스트 정확도** | 90-95% (Midjourney 30% 대비) |
| **장점** | 타이포그래피 최강, 저렴 |
| **추천 용도** | 명언, 캡션 포스트 |

---

#### A-4. FLUX + Qwen-VL (로컬/가성비)

```
┌─────────────────────────────────────────────────────────┐
│   Qwen2.5:7b → 프롬프트                                 │
│        ↓                                                │
│   FLUX.1 (Replicate) → 이미지                           │
│        ↓                                                │
│   Qwen-VL → 기본 검수                                   │
└─────────────────────────────────────────────────────────┘
```

| 항목 | 내용 |
|---|---|
| **이미지 모델** | FLUX.1 |
| **가격** | $0.002-0.003/장 |
| **월 예산** | $10-20 |
| **장점** | 최저 비용, 오픈소스 |
| **단점** | 감성 퀄리티 조율 어려움 |

---

### 옵션 B: 자체 브랜드 자동화 시스템 (GPT + Midjourney + HTML)

#### B-1. 커스텀 자동화 시스템 (추천) ⭐

> GPT + Midjourney + HTML 자동 렌더링으로 브랜드 인스타그램 썸네일 제작

**핵심 개념**:
> GPT는 "디자이너"가 아니라 "아트 디렉터 + 레이아웃 선택기" 역할

```
[1] GPT (전략 & 레이아웃 설계)
        ↓ JSON
[2] Midjourney (배경 이미지 생성)
        ↓ 이미지 파일
[3] HTML 템플릿 시스템
        ↓
[4] Playwright 렌더링
        ↓
[5] PNG 출력 (1080 x 1350)
```

| 항목 | 내용 |
|---|---|
| **출력 사이즈** | 1080 x 1350 (4:5) 인스타 피드 |
| **이미지 모델** | Midjourney v7 |
| **전략 모델** | GPT-4o / Claude 3.5 |
| **렌더링** | Node.js + Playwright |
| **월 예산** | $35-60 (Midjourney $30-60 + API 토큰 $5) |
| **장점** | 템플릿 티 없음, 완전한 브랜드 일관성, 무제한 커스터마이징 |
| **단점** | 초기 구축 공수 (1-2주) |

**브랜드 규칙 정의 (고정값)**:
```json
{
  "brand": {
    "primary_color": "#111111",
    "accent_color": "#FF4D4D",
    "font_display": "Pretendard",
    "font_body": "Pretendard",
    "corner_radius": "28px",
    "style": "minimal luxury"
  }
}
```

**레이아웃 시스템** (6~10개 레이아웃 권장):
- **L1**: Top Headline + Center Subject
- **L2**: Split Layout (좌측 텍스트 / 우측 이미지)
- **L3**: Text Card Overlay (중앙 카드형 텍스트 + 배경 흐림)
- **L4**: Big Typography Focus (텍스트 70%, 이미지 보조)
- **L5**: Accent Block (컬러 블록 + 텍스트)
- **L6**: Minimal Frame (여백 강조)

**GPT 역할** (매 포스트마다 생성):
```json
{
  "layout": "L3_text_card",
  "headline": "AI 시대, 기획이 전부다",
  "subline": "도구보다 사고력이 중요하다",
  "tone": "bold",
  "image_prompt": "dramatic cinematic lighting, modern office, high contrast",
  "overlay_strength": 0.45
}
```

**품질 유지 포인트**:
- GPT가 CSS까지 만들게 하면 망함 → 레이아웃은 사람이 설계
- 레이아웃 1~2개만 쓰면 티남 → 최소 7개 이상
- 이미지엔 텍스트 넣지 않기 → 후편집 통제력
- 디자인 시스템이 먼저 → GPT는 전략만

**자동화 수준**:
- 100% 자동 → 빠르지만 감성 약함
- **80% 자동 + 20% 수동** → 가장 현실적 (추천)

---

## 숏폼 동영상 생성

### 옵션 A: 직접 구축

```
┌─────────────────────────────────────────────────────────┐
│   1. 롱폼 → 숏폼 대본 변환 (LLM)                        │
│   2. 대본 → 스토리보드 (LLM + Vision)                   │
│   3. 스토리보드 → 영상 소스 (Runway/Pika)               │
│   4. TTS 음성 합성 (ElevenLabs)                         │
│   5. 편집 & 렌더링 (FFmpeg)                             │
└─────────────────────────────────────────────────────────┘
```

| 도구 | 용도 | 가격 |
|---|---|---|
| **Runway Gen-3** | 텍스트→영상 | $12/월 |
| **Pika Labs** | 텍스트→영상 | $8/월 |
| **ElevenLabs** | TTS | $5/월 |
| **Fliki** | 텍스트→영상 자동화 | $21/월 |
| **HeyGen** | AI 아바타 | $29/월 |

---

### 옵션 B: 상용 서비스

#### Fliki (추천)

```
텍스트/블로그 → AI 내레이션 영상 자동 생성
```

| 항목 | 내용 |
|---|---|
| **핵심 기능** | 텍스트 → 영상 (AI 보이스 2000개, 80개 언어) |
| **한국어** | ✅ 한국어 음성 지원 |
| **가격** | Standard $21/월, Premium $66/월 |
| **API** | ✅ Enterprise 플랜 |
| **장점** | AI 보이스 퀄리티 최고, 릴스/쇼츠 생성 |

---

## AI 자동화 서비스 비교

### 종합 비교표

| 서비스 | 캐러셀 | 영상 | 이미지 | 카피 | 스케줄링 | 한국어 | API | 가격 |
|---|---|---|---|---|---|---|---|---|
| **커스텀 시스템** | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ✅ | ✅ | $35-60/월 |
| **Fliki** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ❌ | ✅ | ✅ | $21-88/월 |
| **Creasquare** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ✅ | ⚠️ | $25-199/월 |
| **Ocoya** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ✅ | ⚠️ | $15-159/월 |
| **InVideo AI** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ❌ | ❓ | ❓ | $8+/월 |
| **Lately.ai** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ❓ | ⚠️ | $119-199/월 |
| **Canva** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | ✅ | ⚠️ | $13-30/월 |

### 이미지 생성 모델 비교

| 모델 | 감성 퀄리티 | 텍스트 정확도 | API | 가격 | 추천 |
|---|---|---|---|---|---|
| **Midjourney v7** | ⭐⭐⭐⭐⭐ | 30% | ⚠️ 제한적 | $30/월 | 브랜드 감성 |
| **DALL-E 3** | ⭐⭐⭐⭐ | 70% | ✅ 완벽 | $0.04/장 | **범용 1순위** |
| **Ideogram 2.0** | ⭐⭐⭐⭐ | 90-95% | ✅ 베타 | $8-10/월 | 텍스트 특화 |
| **FLUX.1** | ⭐⭐⭐⭐ | 60% | ✅ Replicate | $0.002/장 | 가성비 |

### 비전 모델 비교

| 모델 | 디자인 평가 | 가격 (1M tokens) |
|---|---|---|
| **GPT-4o Vision** | ⭐⭐⭐⭐⭐ | $2.50/$10 |
| **Claude 3.5 Vision** | ⭐⭐⭐⭐⭐ | $3/$15 |
| **Gemini 2.0 Flash** | ⭐⭐⭐⭐ | $0.10/$0.40 (최저) |

---

## 추천 조합

### 🥇 1순위: 커스텀 자동화 시스템 (브랜드 감성 최우선)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Picko (롱폼/팩)                                           │
│        │                                                    │
│        └──→ GPT-4o/Claude → 레이아웃 & 전략 설계            │
│              │                                              │
│              └──→ Midjourney → 배경 이미지                  │
│                    │                                        │
│                    └──→ HTML 템플릿 + Playwright → PNG      │
│                                                             │
│   월 예산: $35-60                                           │
│   개발 공수: 1-2주                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점**: 템플릿 티 없음, 완전한 브랜드 일관성, 무제한 커스터마이징
**단점**: 초기 구축 공수

---

### 🥈 2순위: 커스텀 + Fliki (이미지+영상 커버)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Picko (롱폼/팩)                                           │
│        │                                                    │
│        ├──→ GPT + Midjourney + HTML → 캐러셀/이미지         │
│        │                                                    │
│        └──→ Fliki API → 릴스/숏폼                           │
│                                                             │
│   월 예산: $56-126 (Midjourney $30-60 + Fliki $21-66)       │
│   개발 공수: 2-3주                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점**: 완전 자동화, 이미지+영상 커버
**단점**: 비용 증가

---

### 🥉 3순위: DALL-E 3 + GPT-4o Vision (직접 구축)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Claude 3.5 → 프롬프트 생성                                │
│        │                                                    │
│        └──→ DALL-E 3 API → 이미지                           │
│              │                                              │
│              └──→ GPT-4o Vision → QA                        │
│                    │                                        │
│                    └──→ PIL → 리사이징                      │
│                                                             │
│   월 예산: $35-50                                           │
│   개발 공수: 2-3주                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점**: 완전한 커스터마이징, 기존 API 키 재사용
**단점**: 개발 공수 큼, 품질 조율 필요

---

### 🏆 최종 추천

| 상황 | 추천 조합 | 월 비용 | 이유 |
|---|---|---|---|
| **브랜드 감성 최우선** | 커스텀 자동화 | $35-60 | 템플릿 티 없음, 완전 커스텀 |
| **완전 자동화** | 커스텀 + Fliki | $56-126 | 이미지+영상 커버 |
| **완전 커스텀** | DALL-E 3 + GPT-4o | $35-50 | 유연성 최대 |
| **최고 품질** | Midjourney + Claude | $50-80 | 감성 퀄리티 압도적 |
| **가성비** | FLUX + Gemini | $15-25 | 최저 비용 |

---

## 구현 로드맵

### Phase 1: 이미지 생성 (2-3주)

#### Week 1: 디자인 시스템 구축
- [ ] 브랜드 규칙 정의 (컬러, 폰트, 코너 라디우스 등)
- [ ] 6~10개 레이아웃 HTML 템플릿 제작
- [ ] `picko/layout_client.py` 구현 (레이아웃 선택 로직)

#### Week 2: 파이프라인 통합
- [ ] `generate_content.py`에 이미지 생성 연동
- [ ] Obsidian Vault에 이미지 저장 구조 설계
- [ ] 브랜드 템플릿 설정

#### Week 3: 테스트 & 최적화
- [ ] 이미지 품질 검수 로직
- [ ] 실패 시 재시도 메커니즘
- [ ] 비용 모니터링

---

### Phase 2: 숏폼 동영상 (4-6주)

#### Week 4-5: Fliki 통합
- [ ] Fliki 계정 생성, API 키 발급
- [ ] `picko/fliki_client.py` 구현
- [ ] 숏폼 대본 생성 프롬프트 작성

#### Week 6-7: 영상 파이프라인
- [ ] `scripts/generate_shorts.py` 작성
- [ ] 플랫폼별 리사이징 (Reels/Shorts/TikTok)
- [ ] 썸네일 자동 생성

#### Week 8-9: 통합 & 테스트
- [ ] 전체 파이프라인 통합 테스트
- [ ] 업로드 스케줄링 연동

---

### Phase 3: 통합 & 배포 (2주)

#### Week 10: 최종 통합
- [ ] `config/config.yml` 확장
- [ ] 전체 파이프라인 E2E 테스트
- [ ] 문서화 업데이트

#### Week 11: 배포
- [ ] GitHub Actions 워크플로우 확장
- [ ] 모니터링 & 알림 설정
- [ ] 사용자 가이드 작성

---

## 비용 요약

### 월 예산 비교

| 조합 | 이미지 | 영상 | QA | 기타 | 합계 |
|---|---|---|---|---|---|
| **커스텀 자동화** | $30-50 | - | $5-10 | - | **$35-60** |
| **커스텀 + Fliki** | $30-50 | $21-66 | $5-10 | - | **$56-126** |
| **DALL-E + GPT-4o** | $30-40 | - | $5-10 | - | **$35-50** |
| **Midjourney + Claude** | $30 | - | $5-10 | $13 (Canva) | **$48-53** |
| **FLUX + Gemini** | $10-15 | - | $1-2 | - | **$11-17** |

### 연간 예산

| 조합 | 월 | 연간 |
|---|---|---|
| 커스텀 자동화 | $35-60 | $420-720 |
| 커스텀 + Fliki | $56-126 | $672-1,512 |
| DALL-E + GPT-4o | $35-50 | $420-600 |

---

## 설정 예시

### config/config.yml 확장

```yaml
# ============================================
# 이미지 생성 설정
# ============================================
image:
  enabled: true
  provider: "custom"  # custom | dalle | ideogram | flux

  # 커스텀 자동화 설정
  custom:
    midjourney:
      provider: "apify"  # apify | manual
      actor_id: "apify/midjourney-scraper"
    playwright:
      viewport_width: 1080
      viewport_height: 1350
      device_scale_factor: 2
    templates_dir: "config/layouts/"
    layouts:
      - "L1_top_headline"
      - "L2_split"
      - "L3_text_card"
      - "L4_big_typography"
      - "L5_accent_block"
      - "L6_minimal_frame"

  # DALL-E 설정 (직접 구축 시)
  dalle:
    model: "dall-e-3"
    size: "1024x1024"
    quality: "hd"
    style: "natural"

  # Ideogram 설정
  ideogram:
    api_key_env: "IDEOGRAM_API_KEY"
    model: "ideogram-2.0"
    style_preset: "Soft"

  # 품질 검수
  vision_qa:
    enabled: true
    provider: "openai"  # openai | anthropic | google
    model: "gpt-4o"
    min_score: 0.7

  # 브랜드 스타일 가이드
  style_guide:
    mood: "soft, dreamy, calm, warm, minimalist"
    colors:
      primary: "#1a1a2e"
      secondary: "#16213e"
      accent: "#0f3460"
      background: "#F5F5F5"
    typography:
      headline: "Pretendard Bold"
      body: "Pretendard Regular"
    avoid:
      - "harsh contrasts"
      - "neon colors"
      - "busy backgrounds"
      - "clipart style"

# ============================================
# 영상 생성 설정
# ============================================
video:
  enabled: true
  provider: "fliki"  # fliki | runway | heygen

  fliki:
    api_key_env: "FLIKI_API_KEY"
    default_voice: "korean_female_natural"
    aspect_ratio: "9:16"  # Reels/Shorts
    max_duration: 60

  # 숏폼 설정
  shorts:
    platforms:
      - "instagram_reels"
      - "youtube_shorts"
      - "tiktok"
    default_duration: 60

# ============================================
# 소셜 미디어 게시 설정
# ============================================
social:
  scheduling:
    enabled: true
    provider: "custom"  # custom | buffer | later

  platforms:
    instagram:
      enabled: true
      auto_post: true
      post_times: ["09:00", "12:00", "18:00"]
    twitter:
      enabled: true
      auto_post: true
    linkedin:
      enabled: true
      auto_post: false  # 수동 승인
```

### .env 확장

```bash
# 기존 키
OPENAI_API_KEY=sk-...
RELAY_API_KEY=...

# 이미지/영상 생성
MIDJOURNEY_API_KEY=your_midjourney_key  # Apify용
FLIKI_API_KEY=your_fliki_key  # 선택 (영상)
IDEOGRAM_API_KEY=your_ideogram_key  # 선택
```

---

## 참고 링크

### 공식 문서
- [Midjourney Docs](https://docs.midjourney.com/)
- [Apify Midjourney Actor](https://apify.com/apify/midjourney-scraper)
- [Playwright Docs](https://playwright.dev/python/)
- [Fliki API](https://fliki.ai/docs/api)
- [OpenAI DALL-E API](https://platform.openai.com/docs/guides/images)
- [Ideogram API](https://docs.ideogram.ai/)

### 비교 리뷰
- [Instagram AI Tools Comparison](https://yourgpt.ai/blog/comparison/best-ai-tools-for-instagram)
- [DALL-E vs Midjourney vs Flux](https://apatero.com/blog/dalle-vs-midjourney-vs-flux-comparison-2026)

---

*작성일: 2026-02-22*
*업데이트: v0.3.0 계획*
