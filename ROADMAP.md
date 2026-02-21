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

### 옵션 B: 상용 서비스 사용

#### B-1. Predis.ai (추천) ⭐

```
텍스트 한 줄 → 캐러셀/이미지/영상 자동 생성
```

| 항목 | 내용 |
|---|---|
| **핵심 기능** | 텍스트 → 캐러셀/이미지/영상 자동 생성 |
| **한국어** | ✅ 26개 언어 지원 |
| **API** | ✅ REST API + Webhook |
| **가격** | Lite $32/월, Premium $59/월 |
| **장점** | 캐러셀 생성 최강, 스케줄링 포함 |
| **단점** | 크레딧 시스템 |

**API 통합 예시**:
```python
import requests

PREDIS_API_KEY = "your_api_key"

def generate_carousel(content: dict):
    """롱폼 → 인스타 캐러셀 자동 생성"""
    response = requests.post(
        "https://api.predis.ai/v1/generate",
        headers={"Authorization": f"Bearer {PREDIS_API_KEY}"},
        json={
            "text": content["summary"],
            "content_type": "carousel",
            "brand_id": "your_brand_id",
            "input_language": "ko",
            "output_language": "ko"
        }
    )
    return response.json()
```

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
| **Predis.ai** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ✅ | ✅ | $32-249/월 |
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

### 🥇 1순위: Predis.ai 단독 (빠른 출시)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Picko (롱폼/팩)                                           │
│        │                                                    │
│        └──→ Predis.ai API                                   │
│              ├── 캐러셀 자동 생성                           │
│              ├── 이미지 자동 생성                           │
│              ├── 영상 자동 생성                             │
│              └── 스케줄링                                   │
│                                                             │
│   월 예산: $32-59                                           │
│   개발 공수: 2-3일                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점**: 최소 개발, 검증된 품질, 올인원
**단점**: 커스터마이징 제한

---

### 🥈 2순위: Picko + Predis + Fliki (완전 자동화)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Picko (롱폼/팩)                                           │
│        │                                                    │
│        ├──→ Predis.ai API → 캐러셀/이미지                   │
│        │                                                    │
│        └──→ Fliki API → 릴스/숏폼                           │
│                                                             │
│   월 예산: $53-125 (Predis $32 + Fliki $21)                 │
│   개발 공수: 3-5일                                          │
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
| **MVP 빠른 출시** | Predis.ai 단독 | $32-59 | 최소 공수, 검증됨 |
| **완전 자동화** | Predis + Fliki | $53-125 | 이미지+영상 커버 |
| **완전 커스텀** | DALL-E 3 + GPT-4o | $35-50 | 유연성 최대 |
| **최고 품질** | Midjourney + Claude | $50-80 | 감성 퀄리티 압도적 |
| **가성비** | FLUX + Gemini | $15-25 | 최저 비용 |

---

## 구현 로드맵

### Phase 1: 이미지 생성 (2-3주)

#### Week 1: Predis.ai 통합
- [ ] Predis.ai 계정 생성, API 키 발급
- [ ] `picko/predis_client.py` 구현
- [ ] `scripts/generate_images.py` 작성
- [ ] config.yml에 이미지 설정 추가

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
| **Predis 단독** | $32-59 | 포함 | 포함 | - | **$32-59** |
| **Predis + Fliki** | $32 | $21-66 | 포함 | - | **$53-125** |
| **DALL-E + GPT-4o** | $30-40 | - | $5-10 | - | **$35-50** |
| **Midjourney + Claude** | $30 | - | $5-10 | $13 (Canva) | **$48-53** |
| **FLUX + Gemini** | $10-15 | - | $1-2 | - | **$11-17** |

### 연간 예산

| 조합 | 월 | 연간 |
|---|---|---|
| Predis 단독 | $32-59 | $384-708 |
| Predis + Fliki | $53-125 | $636-1,500 |
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
  provider: "predis"  # predis | dalle | ideogram | flux

  # Predis.ai 설정
  predis:
    api_key_env: "PREDIS_API_KEY"
    brand_id: "your_brand_id"
    default_content_type: "carousel"  # carousel | single_image | video
    input_language: "ko"
    output_language: "ko"

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
    provider: "predis"  # predis | buffer | later

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
PREDIS_API_KEY=your_predis_key
FLIKI_API_KEY=your_fliki_key  # 선택
IDEOGRAM_API_KEY=your_ideogram_key  # 선택
```

---

## 참고 링크

### 공식 문서
- [Predis.ai API](https://predis.ai/docs/api)
- [Fliki API](https://fliki.ai/docs/api)
- [OpenAI DALL-E API](https://platform.openai.com/docs/guides/images)
- [Ideogram API](https://docs.ideogram.ai/)

### 비교 리뷰
- [Predis.ai Review 2026](https://socialrails.com/blog/predis-review)
- [Instagram AI Tools Comparison](https://yourgpt.ai/blog/comparison/best-ai-tools-for-instagram)
- [DALL-E vs Midjourney vs Flux](https://apatero.com/blog/dalle-vs-midjourney-vs-flux-comparison-2026)

---

*작성일: 2026-02-22*
*업데이트: v0.3.0 계획*
