# 009 AI Video CLI — Spec

## 목표

Picko가 AI 동영상 서비스(Runway, Pika, Kling, Luma, Veo 등)에서 **즉시 사용 가능한 영상 기획서(VideoPlan)**를 자동으로 생성하는 파이프라인을 구축한다.

**핵심 요구사항:**
1. **산출물 사용성**: 생성된 VideoPlan의 각 샷이 대상 서비스에 **바로 복사-붙여넣기 가능한 수준**으로 상세해야 함
2. **품질 보증**: 생성된 VideoPlan이 **실제로 좋은 영상을 만들 수 있도록** 품질이 보장되어야 함

Picko는 영상을 직접 렌더링하지 않는다. 계정 설정 + (선택적) 기존 콘텐츠 → LLM → VideoPlan(JSON/MD) + 품질검증까지가 범위다.

---

## 범위 (In Scope)

### 기본 기능
- `picko video` CLI 서브커맨드
- `VideoPlan` 데이터 모델 (`picko/video_plan.py`)
- `picko/video/generator.py` — 계정 컨텍스트 → LLM → VideoPlan 생성 로직
- `picko/__main__.py` — 신규 서브커맨드 디스패처
- 출력: Vault 내 `Content/Video/` 경로에 JSON + 마크다운 저장

### 산출물 사용성 (NEW)
- **서비스별 구조화 파라미터**: 각 샷마다 대상 서비스별 최적화된 파라미터 생성
  - `LumaParams`, `RunwayParams`, `PikaParams`, `KlingParams`, `VeoParams`
- **오디오 사양**: 배경음악, 내레이션, 효과음 가이드
- **텍스트 오버레이**: 자막 위치, 애니메이션, 타이밍 정보
- **전환 효과**: 샷 간 전환(transition) 가이드

### 품질 보증 체계 (NEW)
- **제약 검증(Validation)**: 서비스/플랫폼 제약 준수 확인
- **품질 평가(Scoring)**: 생성된 VideoPlan 품질 점수 산출
- **품질 게이트(Gating)**: 기준 미달 시 자동 재생성
- **프롬프트 템플릿**: 서비스별 고품질 프롬프트 생성 가이드

## 범위 (Out of Scope)

- 아바타/프레젠터 서비스 연동 (HeyGen, Synthesia) — 삭제됨
- 편집/후반 서비스 연동 (Descript, Veed) — 삭제됨
- 실제 API 호출로 영상 생성 — 어댑터 스텁만, 실제 API 연동은 010+ 브랜치
- 기존 `scripts/` 스크립트 변경 — 일절 없음
- 실제 오디오 파일 생성 — 텍스트 가이드만 제공

---

## 아키텍처 결정

### 1. 기존 스크립트 무변경 원칙

`scripts/generate_content.py` 등 기존 스크립트는 **한 줄도 건드리지 않는다**.
새 CLI는 `picko/__main__.py`에서 새 서브커맨드만 처리하는 얇은 디스패처로 시작한다.

```
기존 (변경 없음)                          신규 (추가만)
────────────────────────────────          ──────────────────────────────────
python scripts/generate_content.py  →     python -m picko video
python scripts/daily_collector.py   →     python -m picko image  (향후)
                                          python -m picko copy   (향후)
```

### 2. 디스패처 구조

```
picko/__main__.py           → argparse subparsers
picko/video/__init__.py     → 패키지 마커
picko/video/generator.py    → 핵심 로직 + 품질 게이트
picko/video/validator.py    → 제약 검증 (NEW)
picko/video/quality_scorer.py → 품질 평가 (NEW)
picko/video/prompt_templates.py → 서비스별 프롬프트 템플릿 (NEW)
picko/video/constraints.py  → 서비스/플랫폼 제약 정의 (NEW)
picko/video_plan.py         → 데이터 모델 (확장)
```

`pyproject.toml`에 `picko = "picko.__main__:main"` 추가.
기존 `picko-generate`, `picko-collect` 엔트리포인트는 유지.

### 3. 품질 보증 3계층 구조 (NEW)

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: 후처리 검증                                            │
│  - VideoPlan 품질 점수 산출 (0-100)                              │
│  - 기준(70점) 미달 시 자동 재생성 (최대 2회)                       │
│  - 이슈 식별 및 개선 제안 생성                                    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: 제약 조건 강제                                         │
│  - 서비스별 파라미터 제한 (길이, 비율, 프롬프트 길이)              │
│  - 플랫폼별 요구사항 강제 (릴스 90초 이하 등)                      │
│  - Intent별 필수 구조 검증 (ad는 CTA 필수 등)                     │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: 고품질 프롬프트 생성                                    │
│  - 서비스별 프롬프트 엔지니어링 베스트 프랙티스 내장               │
│  - Few-shot 예시 포함                                            │
│  - Negative prompt 자동 생성                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4. 세 가지 독립 축

영상 기획은 세 가지 독립된 축의 조합으로 결정된다.

```
소스 (what)  ×  의도 (why)     ×  주간 맥락 (when)
───────────    ──────────────    ─────────────────
--content      --intent          --week-of
```

#### 축 1: 소스 (`--content`)

| 모드 | 트리거 | `VideoSource.type` |
|------|--------|-------------------|
| account-only | `--content` 없을 때 (기본) | `"account_only"` |
| content-based | `--content <id>` 지정 시 | `"longform"` |

**account-only**: 계정 정체성(AccountIdentity)만으로 LLM이 VideoPlan을 생성.

**content-based**: 기존 longform 콘텐츠를 활용해 영상 기획.
- `VaultIO`로 `Content/Longform/longform_{content_id}.md` 로드
- frontmatter(title, tags)와 본문(인트로, 핵심 내용, 시사점) 추출
- 콘텐츠 요약을 LLM 프롬프트에 "참고 콘텐츠" 섹션으로 주입
- `VideoPlan.source`에 `type="longform"`, `id=content_id` 기록

#### 축 2: 의도 (`--intent`)

같은 소스라도 **영상의 목적**에 따라 구조·길이·톤이 달라진다.

| intent | 용도 | 길이 | 샷 수 | 핵심 특성 |
|--------|------|------|-------|----------|
| `ad` (기본) | 전환/다운로드 유도 | 15-30초 | 3-5개 | CTA 필수, 첫 3초 훅 |
| `explainer` | 개념 설명/교육 | 45-120초 | 5-8개 | 인트로→본론→결론, 교육적 톤 |
| `brand` | 브랜드 인지도/분위기 | 15-60초 | 3-5개 | 시네마틱, 텍스트 최소화 |
| `trend` | 트렌드 반응/시의성 | 15-30초 | 3-4개 | 빠른 템포, 대화체 |

#### 축 3: 주간 맥락 (`--week-of`)

- `--week-of 2026-03-03` 지정 시 `get_weekly_slot()` 호출
- `customer_outcome`, `cta`, `operator_kpi`를 프롬프트에 주입
- 생략 시 주간 맥락 없이 생성 (독립 기획)

### 5. 계정 설정 로드

기존 `get_identity(account_id)` 함수 재사용 (`picko.account_context`).
기존 `get_weekly_slot(week_of)` 함수 재사용 (`picko.account_context`).

---

## CLI 인터페이스

```
python -m picko video [OPTIONS]
  -a, --account   계정 ID                기본: config.yml의 default_account
  -i, --intent    영상 목적               기본: ad
                  (ad | explainer | brand | trend)
  -c, --content   콘텐츠 ID              없으면 account-only 모드
  -w, --week-of   주간 슬롯 시작일        없으면 주간 맥락 없이 생성
  -s, --service   서비스 (복수 가능)      기본: luma
                  (luma | runway | pika | kling | veo)
                  ※ 복수 지정 시 각 샷에 모든 서비스의 파라미터가 생성됨
  -p, --platform  플랫폼 (복수)           기본: instagram_reel
                  (instagram_reel | youtube_short | tiktok | twitter_video)
  -l, --lang      script/caption 언어     기본: ko
                  (프롬프트는 항상 영문으로 생성됨)
  --dry-run       저장 없이 stdout 출력
  --no-validate   품질 검증 건너뛰기
  -o, --output    출력 디렉토리           기본: <vault>/Content/Video/
```

---

## 데이터 모델 (VideoPlan) — 확장

### VideoPlan 기본 구조

```python
@dataclass
class VideoPlan:
    id: str
    account: str
    intent: VideoIntent                    # ad | explainer | brand | trend
    goal: str
    source: VideoSource
    brand_style: BrandStyle
    shots: list[VideoShot]
    target_services: list[str]
    platforms: list[str]
    duration_sec: int
    created_at: str
    lang: str = "ko"                       # NEW: 자막/캡션 언어

    # NEW: 품질 정보 (생성 후 채워짐)
    quality_score: float | None = None     # 0-100
    quality_issues: list[str] = field(default_factory=list)
    quality_suggestions: list[str] = field(default_factory=list)
    quality_warning: bool = False          # 최대 재시도 초과 시 True
```

### VideoShot — 서비스별 구조화 파라미터 (NEW)

```python
@dataclass
class VideoShot:
    index: int
    duration_sec: int
    shot_type: str                         # intro | main | cta | transition

    # 공통 메타데이터
    script: str                            # 장면 설명 (내부용)
    caption: str                           # 화면에 표시할 텍스트

    # NEW: 서비스별 구조화 파라미터 (즉시 사용 가능)
    luma: LumaParams | None = None
    runway: RunwayParams | None = None
    pika: PikaParams | None = None
    kling: KlingParams | None = None
    veo: VeoParams | None = None

    # NEW: 오디오/텍스트
    audio: AudioSpec | None = None
    text_overlays: list[TextOverlay] = field(default_factory=list)

    # NEW: 전환 효과
    transition_in: str = ""                # fade | cut | dissolve | wipe
    transition_out: str = ""
```

### 서비스별 파라미터 (NEW)

```python
@dataclass
class ServiceParams:
    """모든 서비스의 공통 기반"""
    prompt: str                            # 최적화된 프롬프트 (영문)
    negative_prompt: str = ""              # 제외 요소
    aspect_ratio: str = "9:16"
    duration_sec: int = 5

@dataclass
class LumaParams(ServiceParams):
    """Luma Dream Machine 전용"""
    camera_motion: str = ""                # static | slow_pan | tilt_up | zoom_in | orbit
    motion_intensity: int = 3              # 1-5 (낮을수록 미묘)
    style_preset: str = ""                 # cinematic | natural | artistic | minimal
    start_image_url: str = ""              # 시작 이미지 URL (선택, 사용자 직접 제공)
    end_image_url: str = ""                # 끝 이미지 URL (선택, 사용자 직접 제공)
    loop: bool = False                     # 루프 영상 여부

@dataclass
class RunwayParams(ServiceParams):
    """Runway Gen-3/Gen-4 전용"""
    motion: int = 5                        # 1-10 (역동성)
    camera_move: str = ""                  # static | zoom_in | pan_left | tilt_up | orbit
    seed: int = 0                          # 재현성용 (0=랜덤)
    upscale: bool = False                  # 4K 업스케일

@dataclass
class PikaParams(ServiceParams):
    """Pika 2.x 전용"""
    pikaffect: str = ""                    # Levitate | Explode | Slice | Melt
    style_preset: str = ""                 # 3D | Anime | Realistic | Artistic
    motion_intensity: int = 3              # 1-5

@dataclass
class KlingParams(ServiceParams):
    """Kling 3.0 전용"""
    camera_motion: str = ""
    motion_intensity: int = 3
    style: str = ""                        # cinematic | documentary | commercial

@dataclass
class VeoParams(ServiceParams):
    """Google Veo 3.x 전용"""
    generate_audio: bool = True            # 오디오 자동 생성
    audio_mood: str = ""                   # calm | energetic | dramatic | ambient
    style_preset: str = ""
```

### 오디오/텍스트 사양 (NEW)

```python
@dataclass
class AudioSpec:
    """오디오 가이드"""
    mood: str = ""                         # calm | energetic | dramatic | romantic | hopeful
    genre: str = ""                        # ambient | lofi | orchestral | electronic | acoustic
    bpm: int = 0                           # 템포 (0=자동)
    voiceover_text: str = ""               # 내레이션 텍스트
    voiceover_gender: str = ""             # male | female
    voiceover_tone: str = ""               # warm | professional | casual | dramatic
    sfx: list[str] = field(default_factory=list)  # 효과음 ["chime", "whoosh", "beep"]

@dataclass
class TextOverlay:
    """텍스트 오버레이 사양"""
    text: str
    position: str = "center"               # top | center | bottom
    font_size: str = "medium"              # small | medium | large | xlarge
    font_color: str = "#FFFFFF"
    background: str = ""                   # semi-transparent | solid | none
    animation: str = ""                    # fade_in | slide_up | typewriter | pulse | bounce
    start_sec: float = 0.0
    end_sec: float = 0.0
```

---

## 제약 정의 (NEW)

### 서비스별 제약

| 서비스 | 최대 길이 | 지원 비율 | 프롬프트 제한 | 오디오 |
|--------|----------|----------|---------------|--------|
| Luma | 5초 | 16:9, 9:16, 1:1 | 500자 | ❌ |
| Runway | 10초 | 16:9, 9:16, 1:1, 4:3 | 200자 | ❌ |
| Pika | 5초 | 16:9, 9:16, 1:1 | 300자 | ❌ |
| Kling | 15초 | 16:9, 9:16 | 400자 | ❌ |
| Veo | 8초 | 16:9, 9:16 | 500자 | ✅ 자동생성 |

### 플랫폼별 제약

| 플랫폼 | 최대 길이 | 권장 길이 | 필수 비율 |
|--------|----------|----------|----------|
| instagram_reel | 90초 | 30초 | 9:16 |
| youtube_short | 60초 | 30초 | 9:16 |
| tiktok | 60초 | 30초 | 9:16 |
| twitter_video | 140초 | 45초 | 16:9 또는 1:1 |

### Intent별 필수 구조

| Intent | 필수 요소 | 권장 구조 |
|--------|----------|----------|
| ad | CTA 샷 필수 | intro(훅) → main → cta |
| explainer | intro 샷 권장 | intro → main(2-4개) → conclusion |
| brand | (없음) | intro → main(감성) → outro |
| trend | (없음) | hook → main(빠른 템포) → cta |

---

## 품질 평가 메트릭 (NEW)

### 평가 차원

| 차원 | 가중치 | 평가 기준 |
|------|--------|----------|
| prompt_quality | 25% | 구체성, 시각 묘사, 추상 표현 배제 |
| structure | 20% | Intent별 필수 구조 준수 |
| brand_alignment | 15% | 톤/비율 일관성 |
| platform_fit | 20% | 길이/비율 제약 준수 |
| actionability | 20% | 서비스 파라미터 완전성 |

### 품질 게이트

- **통과 기준**: 종합 점수 ≥ 70점
- **재생성**: 기준 미달 시 최대 2회 자동 재생성
- **피드백 루프**: 이전 시도의 이슈를 다음 프롬프트에 반영

---

## 출력 예시

### VideoPlan JSON (일부)

```json
{
  "id": "video_2026-03-05_001",
  "account": "emotional-date",
  "intent": "ad",
  "lang": "ko",
  "quality_score": 85,
  "quality_issues": [],
  "quality_suggestions": [
    "Runway용 camera_move를 추가하면 더 정교한 제어가 가능합니다."
  ],
  "shots": [
    {
      "index": 1,
      "duration_sec": 5,
      "shot_type": "intro",
      "script": "새벽 감성 배경",
      "caption": "새벽 2시, 잠이 오지 않는 밤",
      "luma": {
        "prompt": "Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving, single desk lamp warm glow, contemplative mood, 9:16 vertical format, cinematic lighting",
        "negative_prompt": "text, watermark, people, bright colors, fast motion",
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

### VideoPlan 마크다운 (사용자 검토용)

```markdown
# 영상 기획서: video_2026-03-05_001

**계정**: emotional-date | **목적**: ad | **길이**: 15초 | **품질점수**: 85

## 목표
앱 다운로드 유도

## 샷 구성

### 샷 1: intro (5초)
**장면**: 새벽 감성 배경
**자막**: 새벽 2시, 잠이 오지 않는 밤

**Luma 프롬프트** (복사해서 사용):
```
Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving, single desk lamp warm glow, contemplative mood, 9:16 vertical format, cinematic lighting
```

**Negative Prompt**:
```
text, watermark, people, bright colors, fast motion
```

**오디오**: calm / ambient / 60 BPM
**전환**: dissolve

---

### 샷 2: main (5초)
...

---

### 샷 3: cta (5초)
...

---

## 품질 정보
- **점수**: 85/100
- **제안**: Runway용 camera_move를 추가하면 더 정교한 제어가 가능합니다.
```

---

## 테스트 케이스

### 1. 감성통화데이트 앱 — ad + account-only

```bash
python -m picko video \
  --account emotional-date \
  --intent ad \
  --service luma \
  --platform instagram_reel \
  --dry-run
```

**기대 결과:**
- 15초, 3샷(새벽 배경 → 연결감 → CTA)
- 각 샷에 `luma` 파라미터 완전히 채워짐
- 품질 점수 ≥ 70
- CTA 샷 존재

### 2. 소셜빌더스 — explainer + longform

```bash
python -m picko video \
  --account socialbuilders \
  --intent explainer \
  --content lf_2026-03-01_001 \
  --service runway \
  --dry-run
```

**기대 결과:**
- 45-120초, 5-8샷
- `source.type=longform`
- 각 샷에 `runway` 파라미터 완전히 채워짐
- intro → main → conclusion 구조

### 3. 품질 게이트 테스트

```bash
python -m picko video --dry-run --no-validate  # 검증 건너뛰기
```

**기대 결과:**
- `quality_score` 없이 반환
- 검증 로직 실행 안 함

---

## 관련 파일

| 파일 | 상태 | 설명 |
|------|------|------|
| `picko/video_plan.py` | ⚠️ 확장필요 | 데이터 모델 (서비스 파라미터 추가) |
| `picko/video/__init__.py` | 🔲 미구현 | 패키지 마커 |
| `picko/video/generator.py` | 🔲 미구현 | 핵심 생성 로직 + 품질 게이트 |
| `picko/video/validator.py` | 🔲 미구현 | 제약 검증 (NEW) |
| `picko/video/quality_scorer.py` | 🔲 미구현 | 품질 평가 (NEW) |
| `picko/video/prompt_templates.py` | 🔲 미구현 | 서비스별 프롬프트 템플릿 (NEW) |
| `picko/video/constraints.py` | 🔲 미구현 | 서비스/플랫폼 제약 정의 (NEW) |
| `picko/__main__.py` | 🔲 미구현 | CLI 디스패처 |
| `pyproject.toml` | 🔲 미구현 | `picko` 엔트리포인트 추가 |
| `tests/test_video_plan.py` | 🔲 미구현 | 모델 단위 테스트 |
| `tests/test_video_generator.py` | 🔲 미구현 | 생성 로직 + 품질 테스트 |
| `tests/test_validator.py` | 🔲 미구현 | 검증 로직 테스트 (NEW) |
