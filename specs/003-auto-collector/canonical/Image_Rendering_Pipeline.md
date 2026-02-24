# 이미지 렌더링 파이프라인

## 1. 개요

CLI 기반 멀티미디어 생성 시스템의 이미지 렌더링 파이프라인 설계.

**핵심 원칙:**
- 템플릿 기반 자동 생성 + 누락 시 대화형 전환
- API로 배경 생성 + HTML로 레이아웃 오버레이
- 2단계 사람 검토 루프

---

## 2. 워크플로우

```
┌─────────────────────────────────────────────────────────────┐
│                     입력 단계                                │
│  Inbox/Multimedia/{id}.md (또는 Content/Longform/{id}.md)   │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   1단계: LLM 분석 & 제안                     │
│  - 참조 문서 로드 (account_id 자동 + 유형+ID 추가)           │
│  - 콘텐츠 유형/레이아웃/텍스트/배경프롬프트 결정              │
│  - 검토용 제안서 생성                                        │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
                   [사람 승인/수정]
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   2단계: 렌더링                              │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ 배경: API 생성   │    │ 레이아웃: HTML   │                │
│  │ (DALL-E/SDXL)   │    │ 템플릿 + 텍스트  │                │
│  └────────┬────────┘    └────────┬────────┘                │
│           └──────────┬──────────┘                          │
│                      ↓                                      │
│              Playwright 렌더링                              │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
                   [사람 승인/거절/재생성]
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                     저장                                     │
│  Assets/Images/{account}/{YYYY-MM-DD}/img_{channel}_{id}.png│
│  + meta_{id}.md (메타데이터)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 입력 템플릿 구조

### 3.1 위치
- 독립 생성: `Inbox/Multimedia/mm_{timestamp}_{id}.md`
- 롱폼 파생: `Content/Longform/{id}.md` 참조

### 3.2 템플릿 형식

```yaml
---
id: mm_20260224_001
account: socialbuilders
source_type: standalone  # standalone | from_longform
longform_ref: ""  # 롱폼 있으면 경로
channels: [linkedin, twitter]  # 대상 채널
content_types: [image]  # image | video | carousel
created: 2026-02-24
status: draft  # draft → proposed → approved → rendered → final
---

## 주제/컨셉
(필수) 핵심 메시지나 주제

## 참조 문서
(선택) 추가 참조 문서
refs:
  - type: reference_style, id: founder_tech_brief
  - type: exploration, id: xxx

## 포함할 텍스트
(선택) 이미지에 들어갈 문구/인용문

## 비고
(선택) 추가 요구사항
```

---

## 4. 참조 문서 시스템

### 4.1 자동 로드 (account_id 기반)

account_id 지정 시 자동 로드:

| 문서 유형 | 위치 | 용도 |
|-----------|------|------|
| 계정 설정 | `config/accounts/{id}.yml` | 채널, 톤, 해시태그 |
| 계정 정체성 | `mock_vault/.../{account}/계정 정체성.md` | 페르소나, 타겟 |
| 주간 슬롯 | `mock_vault/.../{account}/주간 슬롯.md` | 발행 플랜 |

### 4.2 추가 지정 (유형+ID)

```yaml
refs:
  - type: longform, id: input_7ce483b7a9e4
  - type: reference_style, id: founder_tech_brief
  - type: image_style, id: minimal_infographic
```

### 4.3 참조 문서 유형 레지스트리

| type | 위치 패턴 | 설명 |
|------|-----------|------|
| `longform` | `Content/Longform/{id}.md` | 롱폼 글 |
| `reference_style` | `Assets/References/{id}.md` | 글쓰기 스타일 |
| `exploration` | `Inbox/Explorations/{id}.md` | 주제 탐색 결과 |
| `image_style` | `0. 프레임워크/이미지 스타일 프리셋 라이브러리.md#{preset}` | 비주얼 스타일 |

---

## 5. 렌더링 파이프라인

### 5.1 배경 이미지 생성 (API)

**기본:** Stability AI (SDXL) - 대량/저렴
**폴백:** OpenAI DALL-E - 정밀 구성

```python
# config.yml
image_generation:
  provider_default: "stability"
  provider_fallback: "openai"
  output_dir: "Assets/Images"
```

### 5.2 HTML 레이아웃 오버레이

**방식:** 기본 템플릿 + LLM 수정

```python
# 1. 템플릿 선택
template = select_template(content_type)  # quote, card, list, data, carousel

# 2. LLM이 변수 채움 + 필요시 CSS 수정
rendered_html = llm.fill_template(template, context)

# 3. Playwright로 렌더링
image = playwright_render(rendered_html, background_image)
```

### 5.3 HTML 템플릿 목록

| 템플릿 | 파일 | 용도 | 구성 |
|--------|------|------|------|
| 인용문형 | `quote.html` | 인용문/문구 | 배경 + 중앙 텍스트 |
| 카드형 | `card.html` | 썸네일 카드 | 썸네일 + 제목 + 요약 |
| 리스트형 | `list.html` | 체크리스트/단계 | 번호/불릿 + 항목들 |
| 데이터형 | `data.html` | 숫자 강조 | 숫자 + 라벨 |
| 캐러셀형 | `carousel.html` | 다중 슬라이드 | 여러 장 연결 |

---

## 6. 2단계 검토 루프

### 6.1 1단계: 제안 검토 (CLI 대화형)

LLM이 생성한 제안서를 CLI에서 대화형으로 검토:

```
$ python -m scripts.render_media --review

📋 검토 대기: mm_20260224_001

┌─────────────────────────────────────────────────────────────┐
│ 제안 내용                                                    │
├─────────────────────────────────────────────────────────────┤
│ 유형: quote                                                 │
│ 템플릿: quote.html                                          │
│ 배경 프롬프트: "minimal gradient background, soft blue..."  │
│ 오버레이 텍스트: "실패는 성공의 어머니다"                     │
│ 스타일: minimal_infographic                                 │
│ 채널: linkedin, twitter                                     │
└─────────────────────────────────────────────────────────────┘

[A] 승인  [E] 수정  [R] 거절  [S] 건너뛰기
선택: _
```

**수정 선택 시:**
```
수정할 항목을 선택:
1. content_type (현재: quote)
2. template (현재: quote.html)
3. background_prompt (현재: minimal gradient...)
4. overlay_text (현재: 실패는 성공의 어머니다)
5. channels (현재: linkedin, twitter)
6. 전체 커스텀 입력

선택: 4
새 텍스트 입력: 성공은 준비된 자에게 온다
```

### 6.2 2단계: 결과물 검토 (CLI 대화형)

렌더링 완료 후 결과물 확인:

```
$ python -m scripts.render_media --review finals

🖼️  결과물 검토: mm_20260224_001

[이미지 미리보기 - 터미널에서 ASCII 또는 외부 뷰어 호출]

생성 정보:
- 배경 API: stability
- 템플릿: quote.html
- 출력: Assets/Images/socialbuilders/2026-02-24/img_linkedin_mm_001.png

[A] 승인 (저장)  [R] 재생성  [D] 거절 (삭제)  [O] 외부에서 열기
선택: _
```

**재생성 선택 시:**
```
재생성 옵션:
1. 배경만 재생성 (동일 프롬프트)
2. 배경 프롬프트 수정 후 재생성
3. 템플릿/레이아웃 수정 후 재생성
4. 전체 재생성

선택: _
```

### 6.3 상태 전이 다이어그램

```
┌─────────┐   실행    ┌──────────┐   승인    ┌──────────┐
│  draft  │ ───────→ │ proposed │ ───────→ │ approved │
└─────────┘          └──────────┘          └──────────┘
                          │                      │
                     거절/수정                   │ 렌더링
                          ↓                      ↓
                     [종료 또는 재시도]     ┌──────────┐
                                           │ rendered │
                                           └────┬─────┘
                                                │
                                    ┌───────────┼───────────┐
                                    ↓           ↓           ↓
                               [승인]      [재생성]     [거절]
                                    ↓           ↓           ↓
                              ┌──────────┐  rendered   [삭제]
                              │  final   │     ↑
                              └──────────┘     │
                                           다시 검토
```

### 6.4 derivative_status 확장 (롱폼 연동)

롱폼에서 이미지 생성 트리거를 위해 `derivative_status` 필드 확장:

```yaml
# Content/Longform/long_input_xxx.md
---
id: input_xxx
derivative_status:
  status: approved  # pending | approved | rejected
  packs_channels: [linkedin, twitter]
  images_requested: true      # 새 필드: 이미지 생성 요청
  images_channels: [linkedin] # 새 필드: 이미지 생성할 채널
  images_approved: false      # 기존 필드: 결과물 승인
---
```

**롱폼 → 이미지 워크플로우:**
```
1. generate_content.py 실행 (롱폼 생성)
2. 사람이 롱폼 검토 후 derivative_status.images_requested: true 설정
3. render_media.py 실행 → 롱폼 참조하여 이미지 제안 생성
4. CLI 대화형 검토 → 승인 → 렌더링
5. 최종 승인 → images_approved: true
```

---

## 7. 저장 구조

```
Assets/Images/
└── {account}/
    └── {YYYY-MM-DD}/
        ├── img_{channel}_{id}.png      # 최종 이미지
        ├── img_{channel}_{id}_bg.png   # 배경 (선택 보관)
        └── meta_{id}.md                # 메타데이터
```

### 7.1 메타데이터 형식

```yaml
---
id: mm_20260224_001
account: socialbuilders
channel: linkedin
created: 2026-02-24
status: final

# 생성 정보
rendering:
  template: quote.html
  background_api: stability
  background_prompt: "minimal gradient..."
  style_preset: minimal_infographic

# 참조
source:
  type: standalone
  refs:
    - type: reference_style, id: founder_tech_brief

# 검토 이력
review_history:
  - stage: proposal, status: approved, at: 2026-02-24T10:00:00
  - stage: final, status: approved, at: 2026-02-24T10:30:00
---

# 이미지 설명
(사람이 추가한 메모)
```

---

## 8. CLI 인터페이스

### 8.1 기본 실행

```bash
# 독립 입력 템플릿 실행
python -m scripts.render_media --input Inbox/Multimedia/mm_xxx.md

# 롱폼에서 이미지 생성 (derivative_status.images_requested: true인 항목)
python -m scripts.render_media --from-longform

# 누락 정보 있을 경우 대화형 전환
> ⚠️ 누락된 필드: 주제/컨셉
> 주제를 입력하세요: 창업자를 위한 시간 관리
>
> 채널을 선택하세요 (복수 선택: 쉼표로 구분)
> [1] linkedin  [2] twitter  [3] instagram  [4] youtube
> 선택: 1,2
```

### 8.2 검토 모드

```bash
# 대기 중인 제안 검토 (1단계)
python -m scripts.render_media --review

# 결과물만 검토 (2단계)
python -m scripts.render_media --review --finals

# 특정 항목 검토
python -m scripts.render_media --review --id mm_20260224_001
```

### 8.3 상태 확인

```bash
python -m scripts.render_media --status

# Output:
# 📊 이미지 렌더링 상태
# ─────────────────────────────────────────
# ID                    STATUS          CHANNELS
# ─────────────────────────────────────────
# mm_20260224_001       proposed        linkedin, twitter
# mm_20260224_002       rendered        instagram
# mm_20260223_003       final           linkedin
# ─────────────────────────────────────────
# 대기 중: 2개 (제안 1, 결과 1)
```

### 8.4 재생성

```bash
# 특정 항목 재생성
python -m scripts.render_media --regenerate --id mm_20260224_001

# 배경만 재생성
python -m scripts.render_media --regenerate --id mm_20260224_001 --background-only
```

### 8.5 일괄 처리

```bash
# 모든 대기 항목 자동 처리 (검토 없이)
python -m scripts.render_media --batch --auto-approve

# 특정 계정만
python -m scripts.render_media --batch --account socialbuilders
```

---

## 9. 동영상 확장 (향후)

이미지 파이프라인 완성 후 확장 예정:

1. 슬라이드쇼형: 정적 이미지 N장 + TTS + 자막
2. AI 비디오 생성형: Runway/Pika/Sora
3. 발화형: HeyGen/D-ID

---

## 10. 구현 우선순위

| 순서 | 작업 | 설명 |
|------|------|------|
| 1 | 입력 템플릿 파서 | `Inbox/Multimedia/` 읽기 |
| 2 | 참조 문서 로더 | account_id 자동 로드 + refs 파싱 |
| 3 | LLM 제안 생성기 | 유형/레이아웃/프롬프트 결정 |
| 4 | HTML 템플릿 시스템 | 기본 템플릿 5종 |
| 5 | Playwright 렌더러 | HTML → PNG |
| 6 | 검토 인터페이스 | CLI 대화형 검토 |
| 7 | 저장 및 메타데이터 | 최종 결과물 저장 |

---

## 11. 관련 문서

- [멀티미디어 생성 파이프라인](../../mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0.%20프레임워크/멀티미디어%20생성%20파이프라인.md) - 개요
- [이미지 생성 API 선택·설정](../../mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0.%20프레임워크/이미지%20생성%20API%20선택·설정.md) - API 가이드
- [이미지 스타일 프리셋 라이브러리](../../mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0.%20프레임워크/이미지%20스타일%20프리셋%20라이브러리.md) - 스타일 프리셋

---

*작성일: 2026-02-24*
*브랜치: 003-auto-collector*
