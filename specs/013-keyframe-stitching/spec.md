# 013 Keyframe Image Prompt & Visual Stitching — Spec

## 목표

VideoPlan 생성 시 **키프레임 이미지 프롬프트**와 **비주얼 앵커**를 함께 생성하여,
Runway Image-to-Video 스티칭 워크플로우를 지원한다.

현재 파이프라인은 텍스트→비디오 프롬프트(`background_prompt`)만 생성하며,
이미지→비디오(Image-to-Video) 스티칭에 필요한 참조 이미지 프롬프트가 없다.
또한 브랜드 톤/비주얼 스타일이 LLM 프롬프트에 주입되지 않아 샷 간 일관성이 부족하다.

**핵심 워크플로우:**
1. LLM이 `visual_anchor` (전체 영상의 시각적 기준)를 먼저 정의
2. 각 샷마다 `keyframe_image_prompt` (FLUX.2/Ideogram용 정지 이미지 프롬프트) 생성
3. 사용자가 이 프롬프트로 이미지 생성 → Runway 웹 UI의 start_image에 붙여넣어 스티칭

---

## 범위 (In Scope)

- `VideoPlan`에 `visual_anchor` 필드 추가
- `VideoShot`에 `keyframe_image_prompt` 필드 추가
- `RunwayParams`에 `reference_image_url` 필드 추가
- LLM 프롬프트에 브랜드 톤/스타일 주입 (`identity.tone_voice` 활용)
- LLM 프롬프트에 키프레임 생성 가이드라인 추가
- 품질 스코어러에 `keyframe_completeness` 차원 추가 (Runway 한정)

## 범위 (Out of Scope)

- 이미지 생성 API 연동 (FLUX.2, Ideogram 등) — 사용자가 웹에서 직접 생성
- 영상 조립 (moviepy, FFmpeg, Remotion) — 필요 없음
- Runway API 연동 — 사용자가 웹 UI에서 직접 사용
- 새 CLI 서브커맨드 — 기존 `picko video` 명령 그대로 사용

---

## 아키텍처 결정

### 1. Visual Anchor = 샷 간 일관성의 원천

`visual_anchor`는 전체 영상에서 공유되는 시각적 상수를 한 영문 문장으로 정의한다.
예: `"3AM bedroom, cool blue moonlight through sheer curtains, phone screen glow, shallow DOF, 9:16 vertical, subtle film grain"`

모든 `keyframe_image_prompt`는 이 앵커의 환경(공간, 조명, 분위기)을 그대로 포함하고,
전경(피사체/액션)만 샷별로 변경한다.

### 2. keyframe_image_prompt = 정지 이미지 전용

비디오 모션 묘사는 금지. 순수한 이미지 생성 프롬프트로,
FLUX.2/Ideogram에서 실사 수준의 고화질 참조 이미지를 생성하는 용도.

### 3. reference_image_url = 사용자 워크플로우 플레이스홀더

LLM이 채우지 않음. 사용자가 키프레임 이미지를 생성한 뒤
URL을 수동으로 붙여넣는 필드. Runway 웹 UI에서 Image-to-Video의 start_image로 사용.

### 4. 브랜드 스타일 주입 (기존 갭 수정)

현재 `BrandStyle(tone="")`로 항상 빈 값이 들어가는 문제를 수정.
`identity.tone_voice`에서 실제 톤을 가져와 LLM 프롬프트에 주입.

`identity.tone_voice` 구조 (`account_context.py`):
```python
tone_voice["tone"]      # str — "감성적, 시적, 여운 있는" (주요 톤)
tone_voice["forbidden"] # str — 금칙어/금칙 표현
tone_voice["cta_style"] # str — CTA 스타일 가이드
```

LLM 프롬프트에 세 필드 모두 주입:
```
## 브랜드 톤 & 비주얼 정체성
- 주요 톤: {identity.tone_voice["tone"]}
- 금칙 표현: {identity.tone_voice["forbidden"] or "없음"}
- CTA 스타일: {identity.tone_voice["cta_style"] or "없음"}
- 모든 영상: 9:16 수직, 브랜드 일관성 최우선
```

---

## 데이터 모델 변경

### RunwayParams (신규 필드)

```python
reference_image_url: str = ""  # 사용자가 생성된 키프레임 이미지 URL을 여기에 붙여넣음
```

### VideoShot (신규 필드)

```python
keyframe_image_prompt: str = ""  # FLUX.2/Ideogram용 정지 이미지 생성 프롬프트 (스티칭용)
```

### VideoPlan (신규 필드)

```python
visual_anchor: str = ""  # 전체 영상 공통 비주얼 기준 한 문장 (영문)
```

### BrandStyle (초기화 변경)

```python
# 변경 전
brand_style=BrandStyle(tone="")

# 변경 후
brand_style=BrandStyle(
    tone=identity.tone_voice.get("tone", ""),
    theme=self.account_id,
    aspect_ratio="9:16",
)
```

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `picko/video_plan.py` | `RunwayParams`, `VideoShot`, `VideoPlan` 필드 추가 |
| `picko/video/generator.py` | 브랜드 톤 주입, JSON 스키마 업데이트, 신규 필드 파싱 |
| `picko/video/prompt_templates.py` | `RUNWAY_CONFIG.optional_fields`에 `reference_image_url` 추가 |
| `config/prompts/video/model_workflows.md` | 키프레임 가이드 섹션 추가 |
| `picko/video/quality_scorer.py` | `keyframe_completeness` 차원 추가 (Runway 한정) |
| `tests/test_video_plan.py` | 신규 필드 직렬화/역직렬화 테스트 |
| `tests/test_prompt_templates.py` | RUNWAY_CONFIG 검증 |
| `tests/test_quality_scorer.py` | 키프레임 스코어링 테스트 |

---

## 테스트 케이스

### 1. dawn_mood_call — ad + Runway 스티칭

```bash
python -m picko video \
  --account dawn_mood_call \
  --intent ad \
  --service runway \
  --platform instagram_reel \
  --dry-run
```

기대:
- `visual_anchor`: 새벽 감성에 맞는 비주얼 앵커 문장 (영문)
- 모든 샷에 `keyframe_image_prompt` 존재
- 모든 `keyframe_image_prompt`에 `visual_anchor`의 핵심 키워드(조명, 공간)가 반영됨
- `runway.reference_image_url`은 빈 문자열 (사용자가 채울 것)
- `keyframe_completeness` 점수 >= 80
- 15초, 3-5 샷

### 2. socialbuilders — brand + Runway 스티칭

```bash
python -m picko video \
  --account socialbuilders \
  --intent brand \
  --service runway \
  --dry-run
```

기대:
- 브랜드 톤(`authoritative, informative, casual`)이 프롬프트에 반영
- `visual_anchor`에 전문적/모던한 분위기 반영
- 시네마틱, 텍스트 최소화

### 3. Luma 전용 (키프레임 없이도 동작)

```bash
python -m picko video \
  --account dawn_mood_call \
  --intent brand \
  --service luma \
  --dry-run
```

기대:
- `visual_anchor`와 `keyframe_image_prompt` 생성됨 (선택적)
- `quality_scorer`에서 `keyframe_completeness` 차원 미포함 (Runway 아님)
- 기존 동작과 호환

### 4. 기존 VideoPlan JSON 역호환

```python
def test_backward_compatibility():
    """013 이전 VideoPlan JSON도 로드 가능해야 함"""
    legacy = {
        "id": "video_2026-02-01_001",
        "account": "socialbuilders",
        "intent": "ad",
        "goal": "앱 다운로드",
        "source": {"type": "account_only", "id": "", "summary": ""},
        "brand_style": {"tone": "", "theme": "", "colors": {}, "fonts": {}, "aspect_ratio": "9:16"},
        "shots": [{"index": 1, "duration_sec": 5, "shot_type": "intro", "script": "...", "caption": "", "background_prompt": "..."}],
        "target_services": ["luma"],
        "platforms": ["instagram_reel"],
    }
    plan = VideoPlan.from_dict(legacy)

    # 새 필드는 기본값
    assert plan.visual_anchor == ""
    assert plan.shots[0].keyframe_image_prompt == ""
```

---

## 관련 파일

| 파일 | 상태 | 설명 |
|------|------|------|
| `picko/video_plan.py` | 수정 예정 | 데이터 모델 확장 |
| `picko/video/generator.py` | 수정 예정 | 프롬프트 + 파싱 |
| `picko/video/prompt_templates.py` | 수정 예정 | Runway 템플릿 |
| `picko/video/quality_scorer.py` | 수정 예정 | 품질 차원 추가 |
| `config/prompts/video/model_workflows.md` | 수정 예정 | 키프레임 가이드 |
| `specs/009-ai-video-cli/spec.md` | 참조 | 기존 비디오 CLI 스펙 |
| `specs/009-ai-video-cli/design.md` | 참조 | 기존 서비스 활용 전략 |
