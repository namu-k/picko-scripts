# 013 Keyframe Image Prompt & Visual Stitching — Design

## 개요

숏폼 영상의 품질을 결정짓는 핵심은 **샷 간 시각적 일관성**이다.
텍스트→비디오 생성은 매 샷마다 조명, 배경, 분위기가 달라지는 문제가 있다.

이 문제를 해결하는 방법이 **이미지 기반 스티칭 워크플로우**다:

```
Visual Anchor (전체 기준)
    ↓
Keyframe Image Prompt (샷별, 정지 이미지)
    ↓
이미지 생성 도구 (FLUX.2 / Ideogram)에서 참조 이미지 생성
    ↓
Runway Web UI → Image-to-Video (start_image로 사용)
    ↓
일관된 비주얼의 영상 클립 완성
```

---

## 1. Visual Anchor 개념

### 정의

Visual Anchor는 전체 영상에서 **모든 샷이 공유하는 시각적 상수**를 한 영문 문장으로 정의한 것이다.

### 예시

| 계정 | intent | visual_anchor |
|------|--------|---------------|
| dawn_mood_call | ad | `"3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow, shallow depth of field, 9:16 vertical, subtle film grain"` |
| dawn_mood_call | brand | `"Empty city street at dawn, warm amber streetlights, light fog, reflections on wet pavement, 9:16 vertical, cinematic color grading"` |
| socialbuilders | ad | `"Modern co-working space, clean white desk, laptop screen glow, natural window light, professional atmosphere, 9:16 vertical, crisp focus"` |

### 앵커에 반드시 포함할 요소

1. **공간/장소** — bedroom, office, street, studio
2. **조명/색온도** — blue moonlight, warm amber, natural daylight
3. **분위기/질감** — film grain, shallow DOF, cinematic grading
4. **화면 비율** — `9:16 vertical` (필수)
5. **브랜드 연관 요소** — phone glow (통화 앱), laptop (비즈니스)

### 앵커에 포함하면 안 되는 것

- 특정 인물/동작 묘사 (그건 개별 샷의 영역)
- 비디오 모션 언급 (pan, zoom 등 — 이건 RunwayParams)
- 한국어 (이미지 생성 모델은 영문 프롬프트 최적화)

---

## 2. Keyframe Image Prompt 작성 규칙

### 구조

```
[visual_anchor 환경 복사] + [샷별 피사체/액션] + [기술 스펙]
```

### 예시: dawn_mood_call 광고 (3샷)

**visual_anchor:** `"3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow, shallow depth of field, 9:16 vertical, subtle film grain"`

| 샷 | keyframe_image_prompt |
|----|----------------------|
| 1 (intro) | `"3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow, shallow depth of field, side profile of person lying in bed illuminated by phone light, 9:16 vertical, photorealistic, subtle film grain, no text, no watermark"` |
| 2 (main) | `"3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow, shallow depth of field, hand reaching for phone on wooden nightstand with warm lamp, 9:16 vertical, photorealistic, subtle film grain, no text, no watermark"` |
| 3 (cta) | `"3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow, shallow depth of field, phone screen showing call connection interface with soft purple glow, 9:16 vertical, photorealistic, subtle film grain, no text, no watermark"` |

### 핵심 규칙

1. **앵커 키워드 복사**: `visual_anchor`의 조명/공간/분위기 키워드를 모든 샷에 동일하게 복사
2. **전경만 변경**: 피사체(인물/사물/액션)만 샷별로 다르게 기술
3. **필수 태그**: `photorealistic, 9:16 vertical, no text, no watermark`
4. **모션 금지**: "moving", "walking", "panning" 등 동영상 표현 사용 금지 — 정지 이미지 프롬프트
5. **영문 전용**: 이미지 생성 모델(FLUX.2, Ideogram)은 영문 프롬프트에 최적화

---

## 3. 사용자 워크플로우

### Step-by-Step

```
1. picko video 실행
   → visual_anchor + 샷별 keyframe_image_prompt가 포함된 VideoPlan 생성

2. 각 샷의 keyframe_image_prompt를 이미지 생성 도구에 입력
   (FLUX.2 웹 UI, Ideogram 등)
   → 참조 이미지 다운로드

3. Runway 웹 UI에서 Image-to-Video 모드 선택
   → start_image에 생성된 이미지 업로드
   → VideoPlan의 runway.prompt를 텍스트 프롬프트로 입력
   → motion, camera_move 값 참고하여 설정

4. 생성된 영상 클립 다운로드
   → 필요시 클립 이어붙이기 (선택)
```

### VideoPlan 마크다운 출력 예시

```markdown
# Video Plan: dawn_mood_call_ad_001

## Visual Anchor
3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow,
shallow depth of field, 9:16 vertical, subtle film grain

## Shot 1 — intro (5초)
**장면:** 새벽 2시, 침대에 누워 휴대폰 빛을 받는 옆얼굴
**자막:** 잠들기 아쉬운 이 밤

**Keyframe Image Prompt:**
> 3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow,
> shallow depth of field, side profile of person lying in bed illuminated by
> phone light, 9:16 vertical, photorealistic, subtle film grain, no text,
> no watermark

**Runway 설정:**
- prompt: Side profile face illuminated by phone screen...
- motion: 3
- camera_move: static
- reference_image_url: _(이미지 생성 후 URL 붙여넣기)_
```

---

## 4. 브랜드 스타일 주입

### 현재 상태 (문제)

```python
# generator.py — BrandStyle 항상 빈 값
brand_style=BrandStyle(tone="")
```

`AccountIdentity.tone_voice`에 `tone.primary` 값이 있지만 LLM 프롬프트에 주입되지 않음.

### 수정 후

LLM 프롬프트에 다음 블록 추가:

```
## 브랜드 톤 & 비주얼 정체성
- 주요 톤: 감성적, 시적, 여운 있는, 몽환적인
- 금칙 표현: 없음
- CTA 스타일: 없음
- 모든 영상: 9:16 수직, 브랜드 일관성 최우선
```

이 톤 정보가 LLM의 `visual_anchor` 생성에 직접 영향을 주어,
"감성적, 몽환적인" 계정이면 앵커도 그에 맞는 분위기로 생성됨.

---

## 5. 크로스샷 일관성 메커니즘

### 일관성 보장 체인

```
계정 톤 (style.yml)
    ↓ LLM 프롬프트에 주입
visual_anchor (영상 전체 기준)
    ↓ 모든 keyframe_image_prompt에 복사
keyframe_image_prompt (샷별)
    ↓ 이미지 생성 도구에서 참조 이미지 생성
참조 이미지 → Runway start_image
    ↓ Image-to-Video로 영상 생성
일관된 영상 클립
```

### 품질 게이트

`quality_scorer.py`의 `keyframe_completeness` 차원에서 자동 검증.
이 차원은 Runway가 `target_services`에 포함된 경우에만 활성화.

```python
def _score_keyframe_completeness(self, plan: "VideoPlan", services: list[str]) -> float:
    if "runway" not in services:
        return 100.0

    score = 100.0

    # visual_anchor 존재 및 충분성
    if not plan.visual_anchor:
        score -= 30
    elif len(plan.visual_anchor) < 40:
        score -= 10

    # 각 샷의 keyframe_image_prompt 검증
    for shot in plan.shots:
        if not shot.keyframe_image_prompt:
            score -= 15
        else:
            # 화면비 명시 여부
            kf = shot.keyframe_image_prompt.lower()
            if "9:16" not in kf and "vertical" not in kf:
                score -= 5
            # 프롬프트 길이 충분성 (40자 = "환경 + 피사체" 최소 묘사에 필요한 경험적 기준)
            if len(shot.keyframe_image_prompt) < 40:
                score -= 5
            # visual_anchor 핵심 키워드 교차 검증
            if plan.visual_anchor:
                anchor_words = set(plan.visual_anchor.lower().split()[:5])
                keyframe_words = set(kf.split())
                if not anchor_words & keyframe_words:
                    score -= 5  # 앵커 키워드 미반영

    return max(0, score)
```

---

## 6. 기존 시스템과의 관계

### 009-ai-video-cli (기존)

009 브랜치에서 구축한 영상 기획 파이프라인의 **확장**이다.
기존 구조를 변경하지 않고 필드와 프롬프트 가이드만 추가한다.

| 009에서 만든 것 | 013에서 추가하는 것 |
|----------------|-------------------|
| `VideoPlan`, `VideoShot` 데이터 모델 | `visual_anchor`, `keyframe_image_prompt` 필드 |
| `VideoGenerator` LLM 파이프라인 | 브랜드 톤 주입 + 키프레임 가이드 |
| `RunwayParams` (prompt, motion, camera_move) | `reference_image_url` 필드 |
| `BrandStyle` 스켈레톤 | 실제 데이터로 초기화 |
| `quality_scorer` 6개 차원 | `keyframe_completeness` 차원 |

### 하위 호환성

- `visual_anchor`, `keyframe_image_prompt`, `reference_image_url`은 모두 기본값 `""`
- 기존 코드에서 생성한 VideoPlan JSON을 `from_dict()`로 읽어도 문제없음
- Runway 미사용 플랜의 품질 점수에 영향 없음
