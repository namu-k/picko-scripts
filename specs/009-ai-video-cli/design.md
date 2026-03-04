# AI 동영상 제작 서비스 활용 전략 (브랜치 009)

이 문서는 Picko 프로젝트가 **직접 동영상을 렌더링하지 않고**, 상용 AI 동영상 제작 서비스를 최대한 잘 활용하기 위한 전략과 통합 포인트를 정리한다.

- **Picko의 역할**: 원본 콘텐츠 수집·요약·구조화 → **서비스 즉시 적용 가능한 VideoPlan 생성** → 외부 서비스에 넘길 표준 포맷 정의
- **외부 서비스의 역할**: 비디오 렌더링, 타임라인 편집, 아바타·음성 합성, 이펙트/모션 적용

**핵심 원칙:**
1. **산출물 사용성**: 생성된 VideoPlan의 각 샷이 대상 서비스에 **바로 복사-붙여넣기 가능**
2. **품질 보증**: 생성된 VideoPlan이 **실제로 좋은 영상을 만들 수 있도록** 검증된 프로세스 적용

---

## 1. 주요 서비스 상세 스펙

### 1.1 Luma Dream Machine

| 항목 | 값 |
|------|-----|
| 최대 길이 | 5초 |
| 지원 비율 | 16:9, 9:16, 1:1 |
| 프롬프트 제한 | 500자 |
| 오디오 | ❌ 미지원 |
| API | ✅ 지원 |

**프롬프트 작성 가이드:**

```
✅ 좋은 예시:
"Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving,
single desk lamp warm glow, contemplative mood, 9:16 vertical format, cinematic lighting,
slow ambient atmosphere, no people visible"

❌ 나쁜 예시:
"beautiful morning scene" (너무 추상적)
"dawn city" (구체성 부족)
```

**LumaParams 구조:**
```python
@dataclass
class LumaParams:
    prompt: str                    # 50-150자 권장, 영문
    negative_prompt: str           # "text, watermark, blurry, distorted"
    aspect_ratio: str = "9:16"     # 16:9 | 9:16 | 1:1
    duration_sec: int = 5          # 고정 5초
    camera_motion: str = ""        # static | slow_pan | tilt_up | zoom_in | orbit
    motion_intensity: int = 3      # 1-5 (낮을수록 미묘)
    style_preset: str = ""         # cinematic | natural | artistic | minimal
    start_image_url: str = ""      # 시작 이미지 (선택)
    end_image_url: str = ""        # 끝 이미지 (선택)
    loop: bool = False             # 루프 영상 여부
```

**Picko 활용 전략:**
- 감성/몽환적 분위기의 B-roll
- 5초 루프 배경 영상
- 빠른 생성으로 반복 실험 가능

---

### 1.2 Runway Gen-3/Gen-4

| 항목 | 값 |
|------|-----|
| 최대 길이 | 10초 |
| 지원 비율 | 16:9, 9:16, 1:1, 4:3 |
| 프롬프트 제한 | 200자 |
| 오디오 | ❌ 미지원 |
| API | ✅ 지원 |

**프롬프트 작성 가이드:**

```
✅ 좋은 예시:
"Cinematic product shot, minimalist studio lighting, slow camera push in,
soft shadows, professional commercial style, 9:16"

❌ 나쁜 예시:
"nice product video with good lighting" (모호함)
```

**RunwayParams 구조:**
```python
@dataclass
class RunwayParams:
    prompt: str                    # 100-200자 권장, 영문
    negative_prompt: str           # "text, watermark, cartoon"
    aspect_ratio: str = "9:16"
    duration_sec: int = 5          # 1-10초
    motion: int = 5                # 1-10 (역동성, 높을수록 역동적)
    camera_move: str = ""          # static | zoom_in | pan_left | tilt_up | orbit
    seed: int = 0                  # 재현성용 (0=랜덤)
    upscale: bool = False          # 4K 업스케일
```

**Picko 활용 전략:**
- 브랜드 인트로/아웃로
- 고품질 광고 컷
- 카메라 워크가 중요한 샷

---

### 1.3 Pika 2.x

| 항목 | 값 |
|------|-----|
| 최대 길이 | 5초 |
| 지원 비율 | 16:9, 9:16, 1:1 |
| 프롬프트 제한 | 300자 |
| 오디오 | ❌ 미지원 |
| API | ✅ 지원 |

**PikaParams 구조:**
```python
@dataclass
class PikaParams:
    prompt: str                    # 50-200자 권장
    negative_prompt: str           # "text, watermark"
    aspect_ratio: str = "9:16"
    duration_sec: int = 5          # 3-5초
    pikaffect: str = ""            # Levitate | Explode | Slice | Melt | Inflate
    style_preset: str = ""         # 3D | Anime | Realistic | Artistic
    motion_intensity: int = 3      # 1-5
```

**Picko 활용 전략:**
- 빠른 반복 실험이 필요한 샷
- 트렌드 반응형 숏폼
- Pikaffects 같은 특수 효과가 필요한 경우

---

### 1.4 Kling 3.0

| 항목 | 값 |
|------|-----|
| 최대 길이 | 15초 (연장 시 최대 3분) |
| 지원 비율 | 16:9, 9:16 |
| 프롬프트 제한 | 400자 |
| 오디오 | ❌ 미지원 |
| API | ⚠️ 제한적 |

**KlingParams 구조:**
```python
@dataclass
class KlingParams:
    prompt: str                    # 100-300자 권장
    negative_prompt: str           # "text, watermark"
    aspect_ratio: str = "9:16"
    duration_sec: int = 10         # 5-15초
    camera_motion: str = ""        # static | pan | tilt | zoom
    motion_intensity: int = 3      # 1-5
    style: str = ""                # cinematic | documentary | commercial
```

**Picko 활용 전략:**
- 1-2분 설명/튜토리얼 영상
- 긴 러닝타임이 필요한 explainer
- 비용 효율적인 장편 제작

---

### 1.5 Google Veo 3.x

| 항목 | 값 |
|------|-----|
| 최대 길이 | 8초 |
| 지원 비율 | 16:9, 9:16 |
| 프롬프트 제한 | 500자 |
| 오디오 | ✅ 자동 생성 |
| API | ✅ 지원 |

**VeoParams 구조:**
```python
@dataclass
class VeoParams:
    prompt: str                    # 100-300자 권장
    negative_prompt: str           # "text, watermark"
    aspect_ratio: str = "9:16"
    duration_sec: int = 8          # 1-8초
    generate_audio: bool = True    # 오디오 자동 생성
    audio_mood: str = ""           # calm | energetic | dramatic | ambient
    style_preset: str = ""         # cinematic | natural | artistic
```

**Picko 활용 전략:**
- 오디오가 필요한 브랜드 영상
- 품질이 최우선인 핵심 샷
- 프리미엄 광고 컷

---

## 2. 품질 보증 체계

### 2.1 3계층 품질 보증 구조

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: 후처리 검증 (Quality Scoring)                          │
│  - VideoPlan 품질 점수 산출 (0-100)                              │
│  - 기준(70점) 미달 시 자동 재생성 (최대 2회)                       │
│  - 이슈 식별 및 개선 제안 생성                                    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: 제약 조건 강제 (Constraints & Validation)              │
│  - 서비스별 파라미터 제한 (길이, 비율, 프롬프트 길이)              │
│  - 플랫폼별 요구사항 강제 (릴스 90초 이하 등)                      │
│  - Intent별 필수 구조 검증 (ad는 CTA 필수 등)                     │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: 고품질 프롬프트 생성 (Prompt Templates)                 │
│  - 서비스별 프롬프트 엔지니어링 베스트 프랙티스 내장               │
│  - Few-shot 예시 포함                                            │
│  - Negative prompt 자동 생성                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer 1: 프롬프트 템플릿

**템플릿 구조:**
```python
SERVICE_PROMPT_TEMPLATES = {
    "luma": """
## 역할
너는 Luma Dream Machine용 비디오 프롬프트 전문가다.

## Luma 프롬프트 베스트 프랙티스
1. 구체적 시각 묘사: "새벽 도시" → "새벽 5시 서울, 블루 아워, 고층 빌딩 실루엣"
2. 카메라 움직임 명시: static, slow pan left, gentle zoom in
3. 조명/분위기: soft lighting, golden hour, neon lights
4. 스타일 키워드: cinematic, dreamlike, photorealistic
5. 비율 내장: 항상 "9:16 vertical" 포함

## 피해야 할 것
- 추상적 표현 ("아름다운", "멋진")
- 텍스트/로고 요청
- 복잡한 내러티브

## Few-shot 예시
Input: "새벽 감성"
Output: "Dawn bedroom window, blue hour cityscape, soft curtains moving,
single desk lamp warm glow, contemplative mood, 9:16 vertical, cinematic"
""",
    # runway, pika, kling, veo 템플릿...
}
```

### 2.3 Layer 2: 제약 검증

**검증 항목:**

| 검증 유형 | 대상 | 에러/경고 |
|-----------|------|----------|
| 길이 초과 | 총 duration > 플랫폼 최대 | ERROR |
| 권장 길이 초과 | 총 duration > 플랫폼 권장 | WARNING |
| 비율 불일치 | 서비스 미지원 비율 | ERROR |
| 프롬프트 길이 | 서비스별 제한 초과 | ERROR |
| 필수 구조 | intent별 필수 샷 누락 | ERROR/WARNING |
| 브랜드 일관성 | 샷 간 비율/톤 불일치 | WARNING |

**검증기 구조:**
```python
class VideoPlanValidator:
    def validate(self, plan: VideoPlan) -> list[ValidationError]:
        errors = []
        errors += self._validate_duration(plan)
        errors += self._validate_platform_compatibility(plan)
        errors += self._validate_service_constraints(plan)
        errors += self._validate_structure(plan)
        errors += self._validate_brand_consistency(plan)
        return errors
```

### 2.4 Layer 3: 품질 점수

**평가 차원:**

| 차원 | 가중치 | 평가 기준 |
|------|--------|----------|
| prompt_quality | 25% | 구체성, 시각 묘사, 추상 표현 배제, negative prompt 존재 |
| structure | 20% | Intent별 필수 구조 준수, 샷 수 적절성 |
| brand_alignment | 15% | 톤/비율 일관성, 브랜드 가이드 준수 |
| platform_fit | 20% | 길이/비율 제약 준수, 권장사항 반영 |
| actionability | 20% | 서비스 파라미터 완전성, 즉시 사용 가능성 |

**품질 게이트:**
```python
QUALITY_THRESHOLD = 70  # 이 점수 이상이어야 통과
MAX_RETRIES = 2         # 최대 재시도 횟수

def generate_with_quality_gate(self) -> VideoPlan:
    for attempt in range(MAX_RETRIES + 1):
        plan = self._generate_plan()
        score = self.scorer.score(plan)

        if score.overall >= QUALITY_THRESHOLD:
            plan.quality_score = score.overall
            return plan

        # 피드백을 다음 시도에 반영
        self._feedback = score.issues + score.suggestions

    # 최대 재시도 초과 - 마지막 결과 반환하되 경고
    plan._quality_warning = True
    return plan
```

---

## 3. VideoPlan 스키마 (확장)

### 3.1 전체 구조

```json
{
  "id": "video_2026-03-05_001",
  "account": "emotional-date",
  "intent": "ad",
  "lang": "ko",
  "goal": "앱 다운로드 유도",
  "source": {
    "type": "account_only",
    "id": "",
    "summary": ""
  },
  "brand_style": {
    "tone": "감성/몽환적",
    "aspect_ratio": "9:16"
  },
  "target_services": ["luma"],
  "platforms": ["instagram_reel"],
  "duration_sec": 15,
  "quality_score": 85,
  "quality_issues": [],
  "quality_suggestions": ["Runway용 camera_move 추가 권장"],
  "shots": [
    {
      "index": 1,
      "duration_sec": 5,
      "shot_type": "intro",
      "script": "새벽 감성 배경",
      "caption": "새벽 2시, 잠이 오지 않는 밤",
      "luma": {
        "prompt": "Dawn bedroom window view, blue hour cityscape outside...",
        "negative_prompt": "text, watermark, people, bright colors",
        "aspect_ratio": "9:16",
        "camera_motion": "static",
        "motion_intensity": 2,
        "style_preset": "cinematic"
      },
      "audio": {
        "mood": "calm",
        "genre": "ambient",
        "bpm": 60
      },
      "text_overlays": [{
        "text": "새벽 2시, 잠이 오지 않는 밤",
        "position": "bottom",
        "animation": "fade_in",
        "start_sec": 1.0,
        "end_sec": 4.5
      }],
      "transition_out": "dissolve"
    }
  ]
}
```

### 3.2 서비스 파라미터 매핑

| VideoPlan 필드 | Luma | Runway | Pika | Kling | Veo |
|----------------|------|--------|------|-------|-----|
| prompt | ✅ | ✅ | ✅ | ✅ | ✅ |
| negative_prompt | ✅ | ✅ | ✅ | ✅ | ✅ |
| aspect_ratio | ✅ | ✅ | ✅ | ✅ | ✅ |
| duration_sec | 5(고정) | 1-10 | 3-5 | 5-15 | 1-8 |
| camera_motion | ✅ | camera_move | - | ✅ | - |
| motion_intensity | 1-5 | motion(1-10) | 1-5 | 1-5 | - |
| style_preset | ✅ | - | ✅ | style | ✅ |
| seed | - | ✅ | - | - | - |
| audio | - | - | - | - | ✅ |

---

## 4. 구현 우선순위

### Phase 1: 기반 구축
1. `constraints.py` — 서비스/플랫폼 제약 정의
2. `video_plan.py` 확장 — 서비스별 파라미터 dataclass 추가
3. `validator.py` — 제약 검증 로직

### Phase 2: 품질 시스템
4. `prompt_templates.py` — 서비스별 프롬프트 템플릿
5. `quality_scorer.py` — 품질 평가 로직
6. `generator.py` — 품질 게이트 통합

### Phase 3: CLI
7. `__main__.py` — CLI 디스패처
8. 테스트 작성 및 검증

---

## 5. 실제 사용 가이드

VideoPlan을 생성한 후, 실제 AI 동영상 서비스에서 어떻게 사용하는지 안내한다.

### 5.1 Luma Dream Machine

1. https://lumalabs.ai/dream-machine 접속
2. **Prompt** 필드에 `luma.prompt` 복사-붙여넣기
3. **Negative Prompt** 필드에 `luma.negative_prompt` 복사 (고급 설정)
4. **Aspect Ratio** 선택 (9:16 / 16:9 / 1:1)
5. **Camera Motion** 선택 (static / pan / tilt / zoom / orbit)
6. 시작 이미지가 필요한 경우 `luma.start_image_url`의 이미지를 업로드

### 5.2 Runway Gen-3/Gen-4

1. https://runwayml.com 접속 → Gen-3 Alpha 선택
2. **Text to Video** 모드 선택
3. **Prompt** 필드에 `runway.prompt` 복사-붙여넣기
4. **Motion** 슬라이더 조정 (1-10, `runway.motion` 값 참조)
5. **Camera** 드롭다운에서 `runway.camera_move` 값 선택
6. 재현성이 필요한 경우 **Seed** 필드에 `runway.seed` 입력

### 5.3 Pika 2.x

1. https://pika.art 접속
2. **Text-to-Video** 모드 선택
3. **Prompt** 필드에 `pika.prompt` 복사-붙여넣기
4. **Pikaffects**에서 특수 효과 선택 (`pika.pikaffect` 값)
5. **Style**에서 스타일 프리셋 선택 (`pika.style_preset` 값)

### 5.4 Kling 3.0

1. https://klingai.com 접속
2. **Text to Video** 선택
3. **Prompt** 필드에 `kling.prompt` 복사-붙여넣기
4. **Duration** 설정 (5-15초, `kling.duration_sec` 값)
5. **Camera Motion** 및 **Style** 설정

### 5.5 Google Veo 3.x

1. Google Vertex AI 또는 Gemini Advanced 접속
2. **Veo** 모델 선택
3. **Prompt** 필드에 `veo.prompt` 복사-붙여넣기
4. **Generate Audio** 옵션 활성화 (`veo.generate_audio`가 True인 경우)
5. **Audio Mood** 선택 (`veo.audio_mood` 값)

### 5.6 워크플로우 요약

```
VideoPlan 생성 (picko video)
    ↓
마크다운에서 각 샷의 프롬프트 확인
    ↓
해당 서비스 웹사이트 접속
    ↓
프롬프트 복사-붙여넣기
    ↓
영상 생성
    ↓
다운로드 후 편집 소프트웨어에서 조합
```

---

## 6. 향후 확장

### 5.1 010+ 브랜치에서 구현 예정
- 실제 API 연동 (Luma, Runway, Pika 등)
- 생성된 영상 피드백 수집
- A/B 테스트용 변형 생성

### 5.2 장기 고려사항
- 사용자 피드백 기반 프롬프트 템플릿 개선
- 서비스별 비용/품질 최적화
- 멀티모달 입력 (이미지, 오디오 참조)
