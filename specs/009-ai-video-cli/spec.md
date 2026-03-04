# 009 AI Video CLI — Spec

## 목표

Picko가 AI 동영상 서비스(Runway, Pika, Kling, Luma, Veo 등)에 넘길 **영상 기획서(VideoPlan)를 자동으로 생성하는 파이프라인**을 구축한다.
Picko는 영상을 직접 렌더링하지 않는다. 계정 설정 + (선택적) 기존 콘텐츠 → LLM → VideoPlan JSON/마크다운 출력까지가 범위다.

---

## 범위 (In Scope)

- `picko video` CLI 서브커맨드
- `VideoPlan` 데이터 모델 (`picko/video_plan.py`)
- `picko/video/generator.py` — 계정 컨텍스트 → LLM → VideoPlan 생성 로직
- `picko/__main__.py` — 신규 서브커맨드 디스패처
- 출력: Vault 내 `Content/Video/` 경로에 JSON + 마크다운 저장

## 범위 (Out of Scope)

- 아바타/프레젠터 서비스 연동 (HeyGen, Synthesia) — 삭제됨
- 편집/후반 서비스 연동 (Descript, Veed) — 삭제됨
- 실제 API 호출로 영상 생성 — 어댑터 스텁만, 실제 API 연동은 010+ 브랜치
- 기존 `scripts/` 스크립트 변경 — 일절 없음

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
picko/__main__.py          → argparse subparsers
picko/video/__init__.py    → 패키지 마커
picko/video/generator.py   → 핵심 로직
picko/video_plan.py        → 데이터 모델 (완료)
```

`pyproject.toml`에 `picko = "picko.__main__:main"` 추가.
기존 `picko-generate`, `picko-collect` 엔트리포인트는 유지.

### 3. 세 가지 독립 축

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
- `_load_longform_content()` 패턴 재사용, 기존 스크립트 무변경

#### 축 2: 의도 (`--intent`)

같은 소스라도 **영상의 목적**에 따라 구조·길이·톤이 달라진다.

| intent | 용도 | 길이 | 샷 수 | 핵심 특성 |
|--------|------|------|-------|----------|
| `ad` (기본) | 전환/다운로드 유도 | 15-30초 | 3-5개 | CTA 필수, 첫 3초 훅 |
| `explainer` | 개념 설명/교육 | 45-120초 | 5-8개 | 인트로→본론→결론, 교육적 톤 |
| `brand` | 브랜드 인지도/분위기 | 15-60초 | 3-5개 | 시네마틱, 텍스트 최소화 |
| `trend` | 트렌드 반응/시의성 | 15-30초 | 3-4개 | 빠른 템포, 대화체 |

`intent`는 `VideoGenerator._build_prompt()`에서 프롬프트 디렉션을 결정한다:
- 샷 수·길이 가이드
- 톤 지시 (CTA 강조 vs 감성 vs 교육 등)
- 구조 제약 (마지막 샷 CTA 필수 vs 자유)

`VideoPlan`에 `intent` 필드로 기록되어 어떤 목적의 기획인지 추적 가능.

#### 축 3: 주간 맥락 (`--week-of`)

기존 `WeeklySlot` 시스템을 재사용한다.

- `--week-of 2026-03-03` 지정 시 `get_weekly_slot()` 호출
- `customer_outcome`, `cta`, `operator_kpi`를 프롬프트에 주입
- 같은 ad intent라도 주간 슬롯의 CTA에 맞춰 메시지가 달라짐
- 생략 시 주간 맥락 없이 생성 (독립 기획)

#### 조합 예시

```bash
# 소스 없음 + 광고 + 주간 맥락 → 이번 주 CTA에 맞는 광고 릴스
python -m picko video --intent ad --week-of 2026-03-03

# longform 기반 + 설명 영상 → 기존 글을 교육 영상으로 변환
python -m picko video --content lf_001 --intent explainer

# 소스 없음 + 브랜드 → 감성/시네마틱 브랜드 영상
python -m picko video --intent brand --service luma

# longform 기반 + 트렌드 → 기존 글의 핵심을 빠르게 소화
python -m picko video --content lf_001 --intent trend --service pika
```

### 4. 계정 설정 로드

기존 `get_identity(account_id)` 함수 재사용 (`picko.account_context`).
기존 `get_weekly_slot(week_of)` 함수 재사용 (`picko.account_context`).
별도 video 전용 설정 파일 없음. `config/accounts/<id>.yml`의 `channels`, `visual_settings`에서
필요한 정보(aspect ratio, tone 등)를 읽어온다.

---

## CLI 인터페이스

```
python -m picko video [OPTIONS]
  -a, --account   계정 ID                기본: config.yml의 default_account
  -i, --intent    영상 목적               기본: ad
                  (ad | explainer | brand | trend)
  -c, --content   콘텐츠 ID              없으면 account-only 모드
  -w, --week-of   주간 슬롯 시작일        없으면 주간 맥락 없이 생성
  -s, --service   서비스 (복수)           기본: luma
  -p, --platform  플랫폼 (복수)           기본: instagram_reel
  --dry-run       저장 없이 stdout 출력
  -o, --output    출력 디렉토리           기본: <vault>/Content/Video/
```

사용 예시:

```bash
# 가장 단순한 호출 (account-only, ad, luma, instagram_reel)
python -m picko video

# 설명 영상 (기존 longform 활용)
python -m picko video --intent explainer --content lf_2026-03-04_001

# 이번 주 CTA에 맞는 광고
python -m picko video --intent ad --week-of 2026-03-03

# 브랜드 감성 영상
python -m picko video --intent brand --service luma runway

# 저장 없이 확인만
python -m picko video --dry-run
```

---

## 데이터 모델 (VideoPlan)

`picko/video_plan.py`에 이미 구현됨. 주요 필드:

```
VideoPlan
  id              str       video_2026-03-04_001
  account         str       socialbuilders
  intent          str       ad | explainer | brand | trend
  goal            str       "앱 다운로드 유도"
  source          VideoSource
    type          str       account_only | longform
    id            str       참조 소스 ID (optional)
    summary       str       소스 내용 요약 (프롬프트 생성에 활용)
  brand_style     BrandStyle
    tone          str       "감성/몽환적"
    aspect_ratio  str       "9:16"
  target_services list[str] ["luma"]
  platforms       list[str] ["instagram_reel"]
  duration_sec    int       15
  shots           list[VideoShot]
    index         int
    duration_sec  int       5
    shot_type     str       intro | main | cta | background
    script        str       장면 설명
    caption       str       화면 자막
    background_prompt str   텍스트→비디오 프롬프트 (영문)
    notes         dict      {"luma": "서비스별 힌트"}
```

출력 파일:
- `<output>/<id>.json` — 머신 파싱용
- `<output>/<id>.md` — 사람이 읽는 기획서

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

기대: 15초, 3샷(새벽 배경 → 연결감 → CTA), `intent=ad`, Luma notes 포함.
설계 문서: `specs/009-ai-video-cli/test-case-emotional-date.md`

### 2. 소셜빌더스 — explainer + longform

```bash
python -m picko video \
  --account socialbuilders \
  --intent explainer \
  --content lf_2026-03-01_001 \
  --service runway \
  --dry-run
```

기대: 45-120초, 5-8샷, `source.type=longform`, Runway notes, 교육적 톤.

### 3. 소셜빌더스 — ad + 주간 맥락

```bash
python -m picko video \
  --account socialbuilders \
  --intent ad \
  --week-of 2026-03-03 \
  --service pika \
  --dry-run
```

기대: 15-30초, WeeklySlot의 CTA가 마지막 샷에 반영.

---

## 관련 파일

| 파일 | 상태 | 설명 |
|------|------|------|
| `picko/video_plan.py` | ✅ 완료 | 데이터 모델 |
| `picko/video/__init__.py` | 🔲 미구현 | 패키지 마커 |
| `picko/video/generator.py` | 🔲 미구현 | 핵심 생성 로직 |
| `picko/__main__.py` | 🔲 미구현 | CLI 디스패처 |
| `pyproject.toml` | 🔲 미구현 | `picko` 엔트리포인트 추가 |
| `tests/test_video_plan.py` | 🔲 미구현 | 모델 단위 테스트 |
| `tests/test_video_generator.py` | 🔲 미구현 | 생성 로직 테스트 |
| `specs/009-ai-video-cli/design.md` | ✅ 완료 | 설계 문서 (3.2,3.3 정리됨) |
