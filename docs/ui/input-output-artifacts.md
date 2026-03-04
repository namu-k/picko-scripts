# Picko UI 입력/산출물 문서

작성일: 2026-03-04
버전: 1.0

## 목차
1. [입력 파라미터](#입력-파라미터)
2. [출력 결과](#출력-결과)
3. [중간 산출물](#중간-산출물)
4. [데이터 흐름도](#데이터-흐름도)
5. [상태 전이](#상태-전이)
6. [UI 적용 가이드](#ui-적용-가이드)

---

## 입력 파라미터

### 1. 실행 관련 입력

#### `/run/collect` (수집)
| 파라미터 | 타입 | 필수 | 설명 | UI 컨트롤 | 기본값 |
|---------|------|------|------|-----------|--------|
| `date` | string | ✅ | 수집 날짜 (YYYY-MM-DD) | date picker | today |
| `account` | string | ✅ | 계정 ID | select | socialbuilders |
| `sources` | list | ✅ | RSS 소스 ID 목록 | multi-select | - |
| `max_items` | int | ❌ | 최대 수집 아이템 수 | number input | 100 |
| `dry_run` | bool | ❌ | 드라이런 모드 | checkbox | false |

#### `/run/generate` (생성)
| 파라미터 | 타입 | 필수 | 설명 | UI 컨트롤 | 기본값 |
|---------|------|------|------|-----------|--------|
| `date` | string | ✅ | 생성 대상 날짜 | date picker | today |
| `type` | list | ✅ | 생성 타입 (longform/packs/images) | multi-select | longform |
| `force` | bool | ❌ | 상태 무시 강제 생성 | checkbox | false |
| `dry_run` | bool | ❌ | 드라이런 모드 | checkbox | false |
| `auto_all` | bool | ❌ | 모든 항목 자동 생성 | checkbox | false |
| `week_of` | string | ❌ | 특정 주 (YYYY-W##) | week picker | - |

#### `/video/new` (동영상 생성)
| 파라미터 | 타입 | 필수 | 설명 | UI 컨트롤 | 기본값 |
|---------|------|------|------|-----------|--------|
| `account` | string | ✅ | 계정 ID | select | socialbuilders |
| `intent` | enum | ✅ | 동영상 의도 (ad/explainer/brand/trend) | radio | explainer |
| `goal` | string | ✅ | 목표 | textarea | - |
| `source_type` | enum | ✅ | 소스 타입 | radio | account_only |
| `source_id` | string | ❌ | 소스 ID (조건부) | autocomplete | - |
| `target_services` | list | ✅ | 대상 서비스 | multi-select | - |
| `platforms` | list | ✅ | 플랫폼 | multi-select | - |
| `duration_sec` | int | ✅ | 총 길이(초) | number input | 60 |
| `brand_style.tone` | string | ❌ | 톤 | select | professional |
| `brand_style.theme` | string | ❌ | 테마 | select | technology |
| `brand_style.aspect_ratio` | string | ❌ | 화면 비율 | select | 9:16 |

### 2. 설정 관련 입력

#### `/settings` (전체 설정)
| 그룹 | 항목 | 타입 | 설명 | UI 컨트롤 |
|------|------|------|------|-----------|
| **Vault** | `root` | string | Vault 루트 경로 | text input |
|  | `inbox` | string | 입력물 경로 | text input |
|  | `digests` | string | 다이제스트 경로 | text input |
|  | `explorations` | string | 탐색물 경로 | text input |
|  | `content` | string | 콘텐츠 경로 | text input |
| **LLM** | `global.provider` | enum | LLM 제공사 | select |
|  | `global.model` | string | 모델 ID | text input |
|  | `global.temperature` | number | 온도 (0-2) | range slider |
|  | `global.max_tokens` | int | 최대 토큰 수 | number input |
| **SummaryLLM** | `provider` | enum | 요약 LLM 제공사 | select |
|  | `model` | string | 모델 ID | text input |
|  | `temperature` | number | 온도 | range slider |
|  | `fallback_provider` | enum | 폴백 제공사 | select |
| **WriterLLM** | `provider` | enum | 작성 LLM 제공사 | select |
|  | `model` | string | 모델 ID | text input |
| **Embedding** | `provider` | enum | 임베딩 제공사 | select |
|  | `model` | string | 모델 ID | text input |
|  | `dimensions` | int | 차원 수 | number input |
|  | `device` | enum | 디바이스 (cpu/cuda) | select |
|  | `cache_enabled` | bool | 캐시 활성화 | switch |
| **Scoring** | `weights.novelty` | number | 신선도 가중치 (0-1) | range slider |
|  | `weights.relevance` | number | 관련성 가중치 (0-1) | range slider |
|  | `weights.quality` | number | 품질 가중치 (0-1) | range slider |
| **Quality** | `enabled` | bool | 품질 검사 활성화 | switch |
|  | `auto_approve_threshold` | number | 자동 승인 임계값 | number input |
| **Notification** | `provider` | enum | 알림 제공사 | select |
|  | `review_timeout_hours` | int | 검토 시간(시) | number input |

### 3. 계정 관련 입력

#### `/accounts/:id` (계정 편집)
| 섹션 | 항목 | 타입 | 설명 | UI 컨트롤 |
|------|------|------|------|-----------|
| **AccountIdentity** | `one_liner` | string | 한 줄 소개 | text input |
|  | `target_audience` | string | 타겟 대상 | text input |
|  | `value_proposition` | string | 가치 제안 | textarea |
|  | `tone_voice` | string | 톤 앤 보이스 | select |
|  | `boundaries` | string | 경계 조건 | textarea |
| **WeeklySlot** | `week_of` | string | 주차 (YYYY-W##) | date picker |
|  | `customer_outcome` | string | 고객 성과 | textarea |
|  | `operator_kpi` | string | 운영자 KPI | text input |
|  | `cta` | string | 행동 유도 문구 | text input |
| **StyleProfile** | `source_urls` | list | 참조 URL 목록 | url list |
|  | `characteristics` | string | 특징 | textarea |

### 4. 소스 관련 입력

#### `/sources` (소스 관리)
| 액션 | 입력 | 타입 | 설명 | UI 컨트롤 |
|------|------|------|------|-----------|
| **소스 추가** | `url` | string | RSS URL | text input |
|  | `category` | string | 카테고리 | select |
| **소스 발견** | `account` | string | 대상 계정 | select |
|  | `keywords` | list | 키워드 목록 | tag input |
| **소스 평가** | `threshold` | number | 품질 임계값 | range slider |
|  | `action` | enum | 액션 (approve/reject) | button |

---

## 출력 결과

### 1. 실행 결과

#### 수집 실행 (`/run/collect` 출력)
```json
{
  "job_id": "collect_20260304_001",
  "status": "completed",
  "summary": {
    "total_attempted": 100,
    "collected": 23,
    "duplicates": 2,
    "errors": 0
  },
  "items": [
    {
      "id": "T-001",
      "title": "AI 트렌드 2026",
      "source": "TechCrunch",
      "collected_at": "2026-03-04T12:23:15Z",
      "score": 92,
      "tags": ["AI", "Trend", "Strategy"]
    }
  ]
}
```

#### 생성 실행 (`/run/generate` 출력)
```json
{
  "job_id": "generate_20260304_001",
  "status": "completed",
  "summary": {
    "requested": 18,
    "generated": 15,
    "failed": 3,
    "skipped": 2
  },
  "results": [
    {
      "input_id": "T-001",
      "type": "longform",
      "status": "completed",
      "output_path": "Content/Longform/L-2026-03-04_1.md",
      "generated_at": "2026-03-04T14:30:45Z"
    }
  ]
}
```

#### 동영상 생성 (`/video/new` 출력)
```json
{
  "plan_id": "VP-001",
  "status": "ready",
  "video_plan": {
    "title": "AI 트렌드 분석",
    "duration": 60,
    "total_shots": 5,
    "estimated_render_time": "2-3 hours"
  },
  "shots": [
    {
      "shot_id": "S-001",
      "duration": 12,
      "script": "AI가 바꾸는 미래의 일상은?",
      "visual_description": "음악, 문 앞에 서있는 사람"
    }
  ]
}
```

### 2. 콘텐츠 출력 포맷

#### Longform Article
```markdown
---
title: "AI 트렌드 2026: 기회와 도전"
account: "socialbuilders"
tags: ["AI", "Trend", "Strategy"]
score: 92
---

# AI 트렌드 2026: 기회와 도전

## 1. 개요
...

## 2. 주요 트렌드
...

## 3. 기회 분석
...

## 4. 도전 과제
...

## 5. 결론
...
```

#### Social Pack
```markdown
---
title: "GPT-5 발표"
account: "socialbuilders"
tags: ["AI", "Product"]
type: "twitter"
---

## 트윗 1 (Hook)
GPT-5가 발표되었습니다! 💥 3가지 혁신적인 기능은...

## 트윗 2 (Detail)
1. 멀티모달 통합으로 텍스트→이미지→코드 완벽히 연결
2. 컨텍스트 창 200K 토큰으로 장문 문서 처리
3. 실시간 번역과 감정 분석 추가

## 트윗 3 (CTA)
자세한 내용은 블로그에서 확인하세요! 👇
https://example.com/gpt5
```

### 3. 설정 출력

#### 설정 적용 결과
```json
{
  "config_version": "2.0",
  "applied_at": "2026-03-04T15:00:00Z",
  "changes": {
    "llm.global.model": "gpt-4o-mini",
    "scoring.weights.novelty": 0.3
  },
  "validation": {
    "status": "success",
    "warnings": [],
    "errors": []
  }
}
```

---

## 중간 산출물

### 1. 다이제스트 (Digest)
**위치**: `Inbox/_digests/YYYY-MM-DD.md`

```markdown
---
date: 2026-03-04
total_items: 23
auto_ready: 5
manual: 3
skip: 15
---

## 다이제스트 2026-03-04

### AI 카테고리 (8 items)
#### [auto_ready] AI 트렌드 2026 (T-001)
- 소스: TechCrunch
- 품질 점수: 92
- 핵심 키워드: 트렌드, 전략, 기회
- 추천: longform 생성 권장

#### [manual] GPT-5 발표 (T-002)
- 소스: AI News
- 품질 점수: 88
- 핵심 키워드: 신제품, 기능, OpenAI
- 추천: 심층 분석 필요
```

### 2. 콘텐츠 스케치 (Exploration)
**위치**: `Inbox/Explorations/YYYY-MM-DD/`

```
L-2026-03-04_1_exploration.md
---
topic: "AI 트렌드 2026"
questions: [
  "AI가 어떤 산업에 가장 큰 영향을 미칠 것인가?",
  "기업들이 AI 도입 시 마주할 주요 장벽은?",
  "2026년 AI 트렌드 예측"
]
outline: [
  1. 서론: AI 변화의 속도
  2. 주요 영향 산업 5개
  3. 도전 과제와 해결책
  4. 미래 전망
]
references: [...]
```

### 3. 미디어 프로포절 (Media Proposal)
**위치**: `Inbox/Multimedia/YYYY-MM-DD/`

```
mm_20260304_001_proposal.yml
---
id: "mm-20260304-001"
content_id: "L-2026-03-04_1"
type: "video"
plan: {
  intent: "explainer",
  duration: 60,
  platforms: ["tiktok", "youtube_shorts"],
  style: {
    tone: "professional",
    theme: "technology",
    ratio: "9:16"
  },
  shots: [
    {
      id: 1,
      duration: 12,
      script: "AI 트렌드 2026 소개",
      visual: "animated intro"
    }
  ]
}
review_status: "pending"
---
```

### 4. 품질 검사 보고 (Quality Report)
**위치**: `Inbox/Quality/YYYY-MM-DD/`

```
quality_20260304_001.json
{
  "content_id": "L-2026-03-04_1",
  "primary_score": 0.85,
  "cross_check_score": 0.82,
  "verdict": "approved",
  "feedback": {
    "strengths": ["깊이 있는 분석", "실용적 인사이트"],
    "weaknesses": ["일부 구조 개선 필요", "더 최신 데이터 추가"]
  }
}
```

### 5. 렌더링 큐 (Render Queue)
**위치**: `cache/render_queue/`

```
render_queue_20260304.json
{
  "pending": [
    {
      "media_id": "mm_20260304_001",
      "priority": "high",
      "estimated_time": "2h"
    }
  ],
  "processing": [],
  "completed": []
}
```

---

## 데이터 흐름도

### 1. 콘텐츠 처리 흐름
```
[ RSS Feeds ]
     ↓ (Collect)
[ Collected Items ]
     ↓ (NLP)
[ Processed Items ] → [ Duplicate Check ]
     ↓ (Score)
[ Scored Items ] → [ Quality Check ]
     ↓ (Export)
[ Inbox Items ] → [ Digest Creation ]
     ↓ (Selection)
[ Auto-Ready Items ] → [ Generate ]
[ Generated Content ] → [ Validation ]
[ Final Content ]
```

### 2. 동영상 생성 흐름
```
[ Source Content ]
     ↓ (VideoPlan Creation)
[ Video Plan ]
     ↓ (Shot Generation)
[ Shot List ] → [ Prompt Review ]
     ↓ (Approval)
[ Render Queue ]
     ↓ (Rendering)
[ Final Video ]
```

### 3. 설정 관리 흐름
```
[ Config File ]
     ↓ (Validation)
[ Config Object ]
     ↓ (Apply)
[ Runtime Config ] → [ API Config ]
[ UI Config ] → [ Form Values ]
```

---

## 상태 전이

### 1. 콘텐츠 상태
```
pending
    ↓ [auto_ready]
auto_ready
    ↓ [generate]
processing
    ↓ [complete]
completed
    ↓ [skip]
skipped
```

### 2. 동영상 플랜 상태
```
draft
    ↓ [generate]
ready
    ↓ [approve]
approved
    ↓ [render]
rendering
    ↓ [complete]
completed
    ↓ [reject]
rejected
```

### 3. 실행 잡 상태
```
queued
    ↓ [start]
running
    ↓ [complete]
completed
    ↓ [fail]
failed
    ↓ [retry]
retrying
```

### 4. 소스 상태
```
active
    ↓ [deactivate]
inactive
    ↓ [reactivate]
active

pending
    ↓ [approve]
approved
    ↓ [reject]
rejected
    ↓ [discover]
discovery
```

---

## UI 적용 가이드

### 1. 입력 파라미터 → UI 컨트롤 매핑

| 파라미터 종류 | 권장 UI 컨트롤 | 고려사항 |
|--------------|----------------|----------|
| **날짜/시간** | date picker/week picker | 미래 날짜 제한 가능 |
| **단일 선택** | radio button / dropdown | 항목 수에 따라 선택 |
| **다중 선택** | multi-select / checkbox group | 최대 선택 수 제한 |
| **숫자** | number input / range slider | 최소/최대값 제한 |
| **텍스트** | text input / textarea | 길이 제한, 포맷 검증 |
| **부울** | toggle switch / checkbox | 기본값 제공 |
| **URL** | url input with preview | 유효성 검증 |
| **파일** | file upload / drag & drop | 파일 크기 제한 |

### 2. 출력 결과 → UI 표시

| 결과 종류 | 권장 UI 컨트롤 | 상태 표시 |
|----------|----------------|-----------|
| **텍스트** | markdown viewer / code editor | syntax highlighting |
| **JSON** | json tree viewer / collapsible | key-value 표시 |
| **리스트** | data table / card grid | 정렬/필터링 |
| **진행률** | progress bar / step indicator | 퍼센트 표시 |
| **상태** | badge / status indicator | 색상 코드화 |
| **알림** | toast modal / notification bar | 자동 닫기 옵션 |

### 3. 중간 산출물 처리

| 산출물 | UI 표시 방식 | 액션 옵션 |
|--------|--------------|----------|
| **다이제스트** | expandable card | [Auto-Select] [Export] |
| **스케치** | modal editor | [Save] [Delete] |
| **프로포절** | detail view | [Approve] [Reject] [Edit] |
| **품질 보고** | report card | [View Details] [Recheck] |
| **렌더링 큐** | real-time list | [Pause] [Cancel] [Priority] |

### 4. 실시간 업데이트 패턴

| 업데이트 종류 | UI 반영 방식 | 간격 |
|--------------|--------------|------|
| **진행률** | progress bar increment | 1-5초 |
| **로그** | append to log panel | 실시간 |
| **상태 변경** | badge update | 즉시 |
| **카운터** | number animation | 1초 |
| **알림** | toast notification | 즉시 |

---

## 파일 구조 참조

```
picko-scripts/
├── config/
│   ├── config.yml          # 메인 설정
│   ├── sources.yml         # RSS 소스 목록
│   ├── accounts/           # 계정 프로필
│   └── prompts/            # 프롬프트 템플릿
├── vault/
│   ├── Inbox/Inputs/      # 수집된 콘텐츠
│   ├── Inbox/_digests/    # 다이제스트
│   ├── Inbox/Explorations/ # 탐색물
│   ├── Content/           # 생성된 콘텐츠
│   ├── Multimedia/        # 미디어 관련
│   └── Quality/           # 품질 검사
└── cache/
    ├── embeddings/        # 임베딩 캐시
    └── render_queue/      # 렌더링 큐
```

이 문서를 UI 디자인 시 참고하면, 입력값과 출력값의 관계를 명확히 이해하고 더 정확한 UI를 설계할 수 있습니다!
