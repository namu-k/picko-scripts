# Picko MVP UI 와이어프레임 문서

작성일: 2026-03-04
버전: 1.0

## 목차
1. [개요](#개요)
2. [핵심 디자인 원칙](#핵심-디자인-원칙)
3. [화면별 와이어프레임](#화면별-와이어프레임)
4. [UI 컴포넌트 라이브러리](#ui-컴포넌트-라이브러리)
5. [인터랙션 패턴](#인터랙션-패턴)
6. [기술 구현 가이드](#기술-구현-가이드)

---

## 개요

### 디자인 목표
최소 MVP를 위한 핵심 화면을 설계합니다.
- **리뷰 중심**: 사용자가 최소한의 클릭으로 많은 작업 처리
- **실시간 피드백**: 모든 작업의 진행 상태를 명확히 보여줌
- **직관성**: 복잡한 기능을 단순화하고 명확한 시각적 계층 구조 제공

### 핵심 플로우
```
설정 → 자동 수집 → 인박스 선택 → 생성 → 리뷰 → 결과물 확인
```

- **설정**: 한 번만 하면 되는 초기 구성
- **자동 수집**: 버튼 하나로 수집 실행
- **인박스 선택**: 수집된 아이템 중 생성할 것 고르기
- **생성**: 선택된 아이템으로 콘텐츠 생성
- **리뷰**: 생성된 결과물 승인/거절
- **결과물**: 승인된 콘텐츠 확인

---

## 핵심 디자인 원칙

### 1. Single Task, Single Screen
- 각 화면은 단일 목적에 집중
- 불필요한 탐색 최소화
- 작업 완료 시 자연스러운 흐름

### 2. Progressive Disclosure
- 기본값을 제공하여 초기 선택 부담 감소
- 고급 옵션은 필요 시에만 노출
- 단계적 정보 제공

### 3. Visual Feedback Loop
- 모든 액션에 즉각적인 시각적 응답
- 진행 상태를 시각적으로 표현
- 완료/실패 상태를 명확히 구분

### 4. Power User Friendly
- 키보드 단축키 지원
- 배치 작업 가능
- 반복 작업 최소화

---

## 화면별 와이어프레임

### 1. 대시보드 (/)

#### 레이아웃 구조
```
┌─────────────────────────────────────────────────────────────┐
│  Picko  [ Dashboard ] [ Inbox ] [ Review ] [ Video ]        │  <!-- 공통 nav bar -->
│                                            [ Manage ▼ ]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │  <!-- 상태 카드 -->
│  │ 📊 Summary  │  │ ⚡ Active    │  │ 🎯 Action Needed   │ │
│  │             │  │              │  │                    │ │
│  │ Collected:12│  │ Processing:3 │  │ →Inbox to select:15│ │
│  │ Generated: 8│  │ Queued: 5    │  │ →To approve: 3     │ │
│  │             │  │ Errors: 0    │  │ →Video review: 2   │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │  <!-- 최근 활동 -->
│  │ Recent Activity                                     │   │
│  │ ─────────────────────────────────────────────────── │   │
│  │ • TechCrunch article processed (2m ago)             │   │
│  │ • Twitter pack generated (5m ago)                   │   │
│  │ • Reddit source curated (15m ago)                   │   │
│  │ • Daily digest exported (1h ago)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│              [ ▶ Start New Collection ]                     │  <!-- 단일 액션 -->
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 주요 컴포넌트
- **상태 카드**: 3개 그룹으로 정보 구분 (Summary, Active, Action Needed)
- **Action Needed 카드**: 각 줄이 클릭 가능한 링크 — Inbox / Review(Generated탭) / Review(Video탭)로 바로 이동
- **활동 피드**: 최근 작업을 시간순으로 표시
- **Start New Collection**: 대시보드 전용 단일 액션 버튼

#### 상태 표현
- 숫자 카드: 배경색으로 상태 표시 (초록: 좋음, 주황: 주의, 빨강: 문제)
- 활동 피드: 시간 표시 (2m ago, 5m ago 등)
- Action Needed 숫자: 0이면 초록, 1 이상이면 주황으로 강조

#### "Start New Collection" 버튼 동작 (MVP v1)

버튼 클릭 시 페이지 이동 없이 **인라인 모달**로 파라미터 입력 후 즉시 실행.
대부분 기본값이 있어 빠른 실행이 가능하며, `/run/collect` 전용 페이지가 필요 없음.

```
┌─────────────────────────────────────────────────────────────┐
│  PICKO • Content Pipeline Automation                        │
├─────────────────────────────────────────────────────────────┤
│  ...                                                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  🚀 Run Collection                           [✕]   │    │
│  │  ─────────────────────────────────────────────────  │    │
│  │  Date:      [ 2026-03-04 ]          (기본: 오늘)   │    │
│  │  Account:   [ socialbuilders      ▼ ]              │    │
│  │  Max items: [ 100                 ]                │    │
│  │  [ ] Dry Run  (저장 없이 미리보기)                  │    │
│  │                                                     │    │
│  │            [ Cancel ]  [ ▶ Run Now ]               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- `Run Now` 클릭 시 모달 닫히고 `/status` 화면으로 이동 (실시간 로그)
- Dry Run 체크 시 버튼 텍스트가 `▶ Preview` 로 변경되어 의도 명확화
- Sources 선택은 생략 (기본: 전체) — 고급 옵션은 `/settings`에서 관리

#### 향후 개선 방향 (v2 — 예약 실행)

> 구현 전제: 백엔드에 스케줄러(APScheduler 또는 cron) 연동 필요

```
│  [ ▶ Run Now ]    [ 🕐 Schedule... ]                        │
│                                                             │
│  다음 예약: 매일 09:00  [편집]                               │
│  마지막 실행: 오늘 09:01 ✅  (23 collected)                 │
```

- "Run Now" 모달은 v1과 동일하게 유지
- "Schedule..." 버튼은 별도 모달로 cron 표현식 또는 시간 선택 UI 제공
- 예약 상태를 대시보드 상태 카드 아래에 항상 표시 (다음 실행 시각 + 마지막 결과)

---

### 2. 실행 상태 (/status) - **작업 진행 & 결과**

> Run Collection 또는 Generate Selected 실행 후 자동으로 이동. 두 작업 모두 동일한 화면 재사용.

#### 실행 중 상태

```
┌─────────────────────────────────────────────────────────────┐
│  ← Dashboard    RUNNING: Collection          2026-03-04     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [████████████████░░░░░░░░░░]  18 / 50          [ ■ Stop ] │
│                                                             │
│  12:34:01  ✅ techcrunch.com — 5 items fetched              │
│  12:34:03  ✅ reddit.com/r/startups — 8 items fetched       │
│  12:34:05  ⏳ hackernews.com — fetching...                  │
│  12:34:06  ❌ someoldblog.com — timeout (skipped)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 완료 상태

```
┌─────────────────────────────────────────────────────────────┐
│  ← Dashboard    DONE: Collection             2026-03-04     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [████████████████████████████]  50 / 50       ✅ Complete  │
│                                                             │
│  12:34:01  ✅ techcrunch.com — 5 items fetched              │
│  12:34:03  ✅ reddit.com/r/startups — 8 items fetched       │
│  12:34:07  ✅ hackernews.com — 10 items fetched             │
│  12:34:06  ❌ someoldblog.com — timeout (skipped)           │
│  ...                                                        │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│  ✅ 23 collected  •  ❌ 1 error  •  ⏱ 12s                   │
│                                                             │
│                              [ → Go to Inbox ]             │
└─────────────────────────────────────────────────────────────┘
```

- **Collection 완료** → "Go to Inbox"
- **Generate 완료** → "Go to Review"
- **Dry Run 완료** → "Go to Dashboard" (저장 없음 안내 포함)
- Stop 클릭 시 확인 없이 즉시 중단, 이미 처리된 항목은 저장됨

---

### 3. 인박스 (/inbox) - **수집 후 선택**

> 목적: 오늘 수집된 아이템 중 어떤 것을 콘텐츠로 생성할지 고른다.
> 읽기 깊이: 요약 + 태그 수준으로 충분 (선택 결정, 품질 승인 아님)

#### 레이아웃 구조
```
┌─────────────────────────────────────────────────────────────┐
│  ← Dashboard    INBOX  •  2026-03-04          [Sort] [✕]   │
├─────────────────────────────────────────────────────────────┤
│  Account: [ socialbuilders ▼ ]   Date: [ 2026-03-04 ▼ ]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [ auto_ready: 5 ]  [ manual: 3 ]  [ skip: 10 ]  [ all ]  │
│                                                             │
│  ☑  T-001  "OpenAI GPT-5 발표"      92%  TechCrunch   2h  │
│  ☑  T-002  "AI Startup $50M"        88%  VentureBeat  3h  │
│  ☑  T-003  "Apple's AI Strategy"    85%  The Verge    4h  │
│  ▼ (클릭 시 인라인 확장)                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Tags: AI, Product, OpenAI                            │  │
│  │  Summary: OpenAI가 GPT-5를 공식 발표. 멀티모달 강화,  │  │
│  │  컨텍스트 200K 토큰, 실시간 번역 기능 포함.           │  │
│  │  Source: https://techcrunch.com/...                   │  │
│  └───────────────────────────────────────────────────────┘  │
│  ☐  T-004  "Meta AI Update"          72%  Wired        5h  │
│  ☐  T-005  "EU AI Regulation"        68%  Reuters      6h  │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│  5 selected  [ ☑ All ]  [ ☐ None ]                         │
│                              [ ▶ Generate Selected ]        │
└─────────────────────────────────────────────────────────────┘
```

#### "Generate Selected" 클릭 시 모달
```
┌─────────────────────────────────────────────────────┐
│  Generate 5 items                             [✕]   │
│  ─────────────────────────────────────────────────  │
│  Type:  ☑ Longform  ☑ Packs  ☑ Images               │
│  Style: [ socialbuilders_style            ▼ ]       │
│         (계정 기본값. 변경 시 이번 생성에만 적용)    │
│                                                     │
│  [ ] Dry Run  (저장 없이 미리보기)                   │
│                                                     │
│            [ Cancel ]  [ ▶ Generate ]              │
└─────────────────────────────────────────────────────┘
```
- `Generate` 클릭 → 모달 닫힘 → `/status` 화면으로 이동

#### 주요 컴포넌트
- **상태 탭**: auto_ready / manual / skip / all 필터
- **아이템 행**: 체크박스, 제목, 점수, 소스, 경과 시간
- **인라인 확장**: 클릭 시 요약·태그·원문 링크 표시 (토글)
- **하단 액션 바**: 선택 수 표시 + Generate 모달 트리거

#### 상호작용
- `auto_ready` 탭 기본 선택 (이미 자동 체크된 상태로 진입)
- 아이템 클릭 → 인라인 확장 토글 (체크박스는 별도)
- 새로고침 후에도 체크 상태 유지 (localStorage)

---

### 4. 리뷰 (/review) - **생성 후 승인**

> 목적: generate 후 생성된 콘텐츠/영상 기획의 품질을 최종 승인한다.
> 읽기 깊이: 전문 읽기 필요 → 모달에서 읽고 승인

#### 레이아웃 구조
```
┌─────────────────────────────────────────────────────────────┐
│  ← Dashboard    REVIEW  •  2026-03-04                  [✕]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [ 📝 Generated (8) ]  [ 🎬 Video Plans (3) ]              │
│                                                             │
│  ── Generated 탭 ────────────────────────────────────────── │
│                                                             │
│  L-001  "AI 트렌드 2026: 기회와 도전"        Longform       │
│  ↳ TechCrunch T-001  •  Generated 10m ago                  │
│  [ 📖 Read & Decide ]          [ ✓ Approve ]  [ ✗ Reject ] │
│  ─────────────────────────────────────────────────────────  │
│  P-001  "GPT-5 발표 트윗팩"                  Pack           │
│  ↳ AI News T-002  •  Generated 8m ago                      │
│  [ 📖 Read & Decide ]          [ ✓ Approve ]  [ ✗ Reject ] │
│  ─────────────────────────────────────────────────────────  │
│  P-002  "Apple AI 인사이트 팩"               Pack           │
│  ↳ The Verge T-003  •  Generated 6m ago                    │
│  [ 📖 Read & Decide ]          [ ✓ Approve ]  [ ✗ Reject ] │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Video Plans 탭
```
│  ── Video Plans 탭 ──────────────────────────────────────── │
│                                                             │
│  VP-001  "AI 트렌드 분석"   Explainer · 60s · TikTok       │
│  [ 📋 View Shots ]           [ ✓ Approve ]  [ ✗ Reject ]   │
│  ─────────────────────────────────────────────────────────  │
│  VP-002  "GPT-5 소개"       Brand · 45s · YouTube Shorts   │
│  [ 📋 View Shots ]           [ ✓ Approve ]  [ ✗ Reject ]   │
```

#### "Read & Decide" 클릭 시 모달
```
┌──────────────────────────────────────────────────────────────┐
│  L-001  "AI 트렌드 2026: 기회와 도전"                  [✕]  │
│  ↳ Longform  •  TechCrunch T-001  •  Generated 10m ago      │
│  ────────────────────────────────────────────────────────    │
│                                                              │
│  [전체 마크다운 본문 스크롤 영역]                             │
│                                                              │
│  # AI 트렌드 2026: 기회와 도전                              │
│  ## 1. 개요                                                  │
│  ...                                                         │
│  ## 2. 주요 트렌드                                           │
│  ...                                                         │
│                                                              │
│  ────────────────────────────────────────────────────────    │
│  [ ✗ Reject ]                      [ ✓ Approve ]            │
└──────────────────────────────────────────────────────────────┘
```
- Approve/Reject → 모달 닫힘 → 리스트에서 해당 항목 상태 업데이트

#### 주요 컴포넌트
- **최상위 탭**: Generated / Video Plans (단계가 다른 두 승인 타입)
- **아이템 행**: 제목, 타입 배지, 원본 소스, 생성 경과 시간
- **빠른 승인**: 읽지 않고도 Approve/Reject 버튼 인라인 제공 (재확인 없이 즉시 반영)
- **Read & Decide 모달**: 전문 읽기 후 승인/거절 (모달 내 버튼)

#### 상호작용
- 인라인 Approve/Reject: 확인 다이얼로그 없이 즉시 반영 (실수 방지는 Undo toast로)
- Approve → 배지 카운트 감소, 항목 흐리게 처리 후 목록에서 제거
- Reject → 피드백 입력 옵션 제공 (선택, 1줄 이내)

---

### 5. 계정 관리 (/accounts, /accounts/:id)

> Manage 드롭다운에서 진입. 계정 데이터는 DB에 저장 (vault 의존 없음). 완전한 CRUD 지원.

#### `/accounts` — 계정 목록

```
┌─────────────────────────────────────────────────────────────────┐
│  Accounts                                         [ + New Account ] │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  socialbuilders                                    →      │  │
│  │  SaaS founders에게 도구와 인사이트를 제공합니다             │  │
│  │  Pillars: Productivity · Growth · Community · Insight     │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  devtools_kr                                       →      │  │
│  │  한국 개발자를 위한 도구 큐레이션                           │  │
│  │  Pillars: Tools · Tutorial · Career · Community           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### `/accounts/:id` — 계정 상세 & 편집 (Identity 탭)

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Accounts   socialbuilders                    [ 🗑 Delete ]   │
│  [ Identity ]  [ Schedule ]                                     │
├─────────────────────────────────────────────────────────────────┤
│  (Identity 탭)                                                   │
│                                                                 │
│  Account ID    socialbuilders              (변경 불가)           │
│  Default Style [ socialbuilders_style              ▼ ]          │
│  One-liner    [ SaaS founders에게 도구와 인사이트를 제공합니다 ]  │
│                                                                 │
│  Value        [ 검증된 SaaS 도구와 실전 인사이트를             ]  │
│  Proposition  [ 매일 아침 큐레이션해서 전달합니다              ]  │
│                                                                 │
│  Target       [ SaaS founders         ] [ + Add ]              │
│  Audience     ✕ SaaS founders  ✕ indie hackers  ✕ B2B builders │
│                                                                 │
│  Pillars      P1 [ Productivity tools      ]                    │
│               P2 [ Growth strategy         ]                    │
│               P3 [ Community & networking  ]                    │
│               P4 [ Industry insight        ]                    │
│                                                                 │
│  Tone & Voice                                                   │
│    Style      [ Friendly professional  ▼ ]                     │
│    Language   [ Korean                 ▼ ]                     │
│    Emoji      [ ● ON ]                                          │
│                                                                 │
│  Boundaries   [ 정치적 콘텐츠 제외        ] [ + Add ]           │
│               ✕ 정치적 콘텐츠 제외  ✕ 경쟁사 직접 언급 금지      │
│                                                                 │
│  Bio          [ 매일 SaaS 인사이트를 큐레이션합니다            ]  │
│  Bio (sub)    [ For builders who ship.                        ]  │
│  Link Purpose [ 뉴스레터 구독 유도                             ]  │
│                                                                 │
│                              [ Cancel ]  [ 💾 Save Identity ]  │
└─────────────────────────────────────────────────────────────────┘
```

#### Schedule 탭

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Accounts   socialbuilders                    [ 🗑 Delete ]   │
│  [ Identity ]  [ Schedule ]                                     │
├─────────────────────────────────────────────────────────────────┤
│  Week of  [ 2026-03-02  ▼ ]  (주간 슬롯은 주마다 별도 저장)      │
│                                                [ + New Week ]   │
├─────────────────────────────────────────────────────────────────┤
│  Customer Outcome  [ 이번 주 팔로워가 도구 1개를 도입하게 한다 ]  │
│  Operator KPI      [ Saves 200+ / Reach 5000+               ]  │
│  CTA               [ 뉴스레터 링크 클릭                       ]  │
│                                                                 │
│  Pillar Distribution                                            │
│  P1 [ 2 ] P2 [ 2 ] P3 [ 2 ] P4 [ 1 ]   (합계: 7)              │
│                                                                 │
│  Daily Schedule                                                 │
│  ┌──────┬────────┬──────────────────────────────────────────┐  │
│  │  Day │ Pillar │ Topic                                    │  │
│  ├──────┼────────┼──────────────────────────────────────────┤  │
│  │  Mon │ [ P1▼] │ [ Notion 대체 도구 5선                 ] │  │
│  │  Tue │ [ P2▼] │ [ 콜드 이메일 오픈율 높이는 법         ] │  │
│  │  Wed │ [ P3▼] │ [ 빌드인퍼블릭 커뮤니티 소개           ] │  │
│  │  Thu │ [ P1▼] │ [ Zapier vs Make 비교                 ] │  │
│  │  Fri │ [ P4▼] │ [ 이번 주 SaaS 업계 뉴스              ] │  │
│  │  Sat │ [ P2▼] │ [ 성장 사례: $0→$10k MRR              ] │  │
│  │  Sun │ [ P3▼] │ [ 커뮤니티 Q&A 하이라이트             ] │  │
│  └──────┴────────┴──────────────────────────────────────────┘  │
│                                                                 │
│                              [ Cancel ]  [ 💾 Save Schedule ]  │
└─────────────────────────────────────────────────────────────────┘
```

#### `/accounts/new` — 새 계정 생성

```
┌─────────────────────────────────────────────────────────────────┐
│  New Account                                                    │
├─────────────────────────────────────────────────────────────────┤
│  Account ID   [ socialbuilders        ]  (영문, 하이픈 허용)     │
│  One-liner    [                       ]                         │
│                                                                 │
│  (나머지 필드는 생성 후 Identity 탭에서 편집)                     │
│                                                                 │
│                              [ Cancel ]  [ Create Account ]    │
└─────────────────────────────────────────────────────────────────┘
```

#### 주요 컴포넌트
- **태그 입력**: Target Audience, Boundaries — 텍스트 입력 후 Enter로 태그 추가, ✕로 제거
- **Pillar 배분 합계**: Daily Schedule의 Pillar 선택 수와 Distribution 숫자가 일치하지 않으면 저장 시 경고
- **Delete 확인**: 계정 삭제 시 "이 계정의 모든 소스/슬롯 데이터가 삭제됩니다" 확인 모달

---

### 6. 스타일 관리 (/styles)

> Manage 드롭다운에서 진입. StyleProfile은 공유 가능한 독립 리소스. 레퍼런스 URL 분석으로 생성되며 직접 편집 불가. 여러 계정이 동일한 스타일 공유 가능.

#### `/styles` — 스타일 목록

```
┌─────────────────────────────────────────────────────────────────┐
│  Styles                                        [ + New Style ]  │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  socialbuilders_style                                     │  │
│  │  Analyzed 2026-02-15 · 120 samples                       │  │
│  │  Used by: socialbuilders                          [ → ]  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  tech_influencer                                          │  │
│  │  Analyzed 2026-01-20 · 80 samples                        │  │
│  │  Used by: devtools_kr, socialbuilders             [ → ]  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### `/styles/:name` — 스타일 상세

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Styles   socialbuilders_style               [ 🗑 Delete ]   │
├─────────────────────────────────────────────────────────────────┤
│  Analyzed at   2026-02-15 · 120 samples                         │
│  Used by       socialbuilders                                   │
├─────────────────────────────────────────────────────────────────┤
│  Reference URLs                                                 │
│  • https://twitter.com/levelsio               [ ✕ ]            │
│  • https://twitter.com/marc_louvion           [ ✕ ]            │
│  • https://twitter.com/thepatwalls            [ ✕ ]            │
│  [ + Add URL ]                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Characteristics  (읽기 전용 — Re-analyze로만 갱신)              │
│  평균 길이       280자 이내                                       │
│  해시태그        1–2개                                           │
│  이모지          문장 끝에 1개                                    │
│  문체            짧고 단정한 문장                                 │
│  CTA 위치        마지막 줄                                        │
├─────────────────────────────────────────────────────────────────┤
│  Max Samples   [ 120 ]                                          │
│  [ ] Dry Run                                                    │
│                                    [ 🔄 Re-analyze ]           │
└─────────────────────────────────────────────────────────────────┘
```

#### `/styles/new` — 새 스타일 생성

```
┌─────────────────────────────────────────────────────────────────┐
│  New Style                                                      │
├─────────────────────────────────────────────────────────────────┤
│  Name         [ socialbuilders_style  ]  (영문, 언더스코어 허용) │
│                                                                 │
│  Reference URLs                                                 │
│  [ https://twitter.com/...            ]  [ + Add ]             │
│                                                                 │
│  Max Samples  [ 10 ]                                            │
│  [ ] Dry Run                                                    │
│                                                                 │
│            [ Cancel ]  [ ▶ Analyze & Create ]                  │
└─────────────────────────────────────────────────────────────────┘
```

- Analyze & Create → 분석 실행 후 Characteristics 저장 → 목록으로 이동
- Dry Run → 저장 없이 Characteristics만 미리보기

---

### 7. 소스 관리 (/sources)

> Manage 드롭다운에서 진입. 기존 소스 관리(Active/Pending) + 신규 소스 발견(Discover).

#### 탭 구성

| 탭 | 기능 | 대응 스크립트 |
|----|------|--------------|
| Active | 현재 활성 소스 목록, 토글, 품질 점수 | `source_curator --status` / `--report` |
| Pending | 발견된 후보 소스 승인/거절 | `source_curator --approve/--reject` / `source_discovery --review` |
| Discover | 새 소스 탐색 실행 | `source_discovery --account --keywords` |

#### Active 탭

```
┌─────────────────────────────────────────────────────────────────┐
│  Sources                                                        │
│  [ Active (12) ]  [ Pending (3) ]  [ Discover ]                 │
├─────────────────────────────────────────────────────────────────┤
│  [ 🔍 Filter... ]                  [ 📊 Quality Report ] [ 🧹 Cleanup ] │
├─────────────────────────────────────────────────────────────────┤
│  Source                      Type    Score  Last Collected       │
├─────────────────────────────────────────────────────────────────┤
│  ● techcrunch.com/feed       RSS     92     2h ago    [ ● ON ]  │
│  ● reddit.com/r/startups     Reddit  87     2h ago    [ ● ON ]  │
│  ● hacker-news.firebaseio    HN      85     3h ago    [ ● ON ]  │
│  ○ someoldblog.com/rss       RSS     41     5d ago    [ ○ OFF]  │
│  ● producthunt.com/feed      RSS     78     2h ago    [ ● ON ]  │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

- **Score**: source_curator 품질 점수 (0–100). 낮을수록 흐리게 표시
- **Toggle**: ON/OFF로 수집 대상 포함 여부 결정
- **Quality Report**: `--report` 결과를 모달로 표시
- **Cleanup**: 저품질 소스(`--cleanup`) 실행 전 확인 모달 → Dry Run 옵션 포함

#### Pending 탭

```
┌─────────────────────────────────────────────────────────────────┐
│  Sources                                                        │
│  [ Active (12) ]  [ Pending (3) ]  [ Discover ]                 │
├─────────────────────────────────────────────────────────────────┤
│  3 sources waiting for review                                   │
│                                          [ ✓ Approve All ] [ ✕ Reject All ] │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  reddit.com/r/buildinpublic          RSS   Score: 76      │  │
│  │  Discovered for: socialbuilders · 2026-03-03              │  │
│  │  Keywords matched: "build in public", "indie hacker"      │  │
│  │                              [ ✕ Reject ]  [ ✓ Approve ]  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  substack.com/some-newsletter        Newsletter  Score: 68│  │
│  │  Discovered for: socialbuilders · 2026-03-03              │  │
│  │  Keywords matched: "saas", "startup"                      │  │
│  │                              [ ✕ Reject ]  [ ✓ Approve ]  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

- 각 카드에서 개별 Approve / Reject
- 상단 Approve All / Reject All로 일괄 처리
- Approve → Active 탭으로 이동, Reject → 목록에서 제거

#### Discover 탭

```
┌─────────────────────────────────────────────────────────────────┐
│  Sources                                                        │
│  [ Active (12) ]  [ Pending (3) ]  [ Discover ]                 │
├─────────────────────────────────────────────────────────────────┤
│  새로운 RSS/Reddit 소스를 자동으로 탐색합니다.                    │
│                                                                 │
│  Account    [ socialbuilders          ▼ ]                       │
│  Keywords   [ saas, indie hacker, build in public ]             │
│             (쉼표로 구분. 비워두면 계정 기본 키워드 사용)          │
│  [ ] Dry Run  (실제 저장 없이 미리보기)                           │
│                                                                 │
│                              [ ▶ Run Discovery ]               │
├─────────────────────────────────────────────────────────────────┤
│  최근 실행                                                       │
│  2026-03-03 14:22  socialbuilders  → 5 found, 3 pending         │
│  2026-02-28 09:10  socialbuilders  → 2 found, 0 pending         │
└─────────────────────────────────────────────────────────────────┘
```

- Run Discovery 후: "5 sources found → Pending 탭에서 검토하세요" 알림
- Dry Run 시: 결과를 모달로 미리보기만 (저장 안 함)

#### 주요 컴포넌트
- **탭 배지**: Pending 탭 숫자는 항상 최신 상태 유지
- **Score 색상**: 80+ 초록, 60–79 노랑, 60 미만 빨강/흐리게

---

### 8. 설정 화면 (/settings)

> Manage 드롭다운에서 진입. 수평 탭으로 config.yml 구조를 그대로 반영.

#### 탭 구성

| 탭 | 담당 설정 |
|----|----------|
| Vault | 경로 설정 (root + 10개 하위 경로) |
| LLM | Summary / Writer / Embedding 모델 설정 |
| Scoring | 점수 가중치, 임계값, 신선도 |
| Processing | 배치, 품질 체크, 중복 제거 |
| Advanced | 로깅, 알림, 생성 설정 |

#### 공통 레이아웃 구조
```
┌─────────────────────────────────────────────────────────────────┐
│  Manage > Settings                                          │
│  [ Vault ] [ LLM ] [ Scoring ] [ Processing ] [ Advanced ] │
├─────────────────────────────────────────────────────────────────┤
│  (탭 내용)                                                  │
│                                                             │
│                    [ Cancel ]  [ 💾 Save Changes ]          │
└─────────────────────────────────────────────────────────────────┘
```

#### Vault 탭
```
│  (Vault 탭)                                                 │
│                                                             │
│  Root          [ /Users/name/obsidian/picko    ]            │
│                                                             │
│  inbox         [ {root}/inbox                 ]            │
│  longform      [ {root}/longform              ]            │
│  packs         [ {root}/packs                 ]            │
│  images        [ {root}/images                ]            │
│  video_plans   [ {root}/video_plans           ]            │
│  sources       [ {root}/sources               ]            │
│  accounts      [ {root}/accounts              ]            │
│  styles        [ {root}/styles                ]            │
│  weekly_slots  [ {root}/weekly_slots          ]            │
│  explorations  [ {root}/explorations          ]            │
```

#### LLM 탭
```
│  (LLM 탭)                                                   │
│                                                             │
│  Summary LLM                                                │
│    Provider  [ openai          ▼ ]                         │
│    Model     [ gpt-4o-mini     ]                           │
│    Fallback  [ gpt-3.5-turbo   ]                           │
│                                                             │
│  Writer LLM                                                 │
│    Provider  [ openai          ▼ ]                         │
│    Model     [ gpt-4o          ]                           │
│                                                             │
│  Embedding                                                  │
│    Provider  [ openai          ▼ ]                         │
│    Model     [ text-embedding-3-small ]                    │
│    Device    [ cpu             ▼ ]                         │
│    Cache     [ ● ON ]                                       │
```

#### Scoring 탭
```
│  (Scoring 탭)                                               │
│                                                             │
│  Weights (합계 1.0)                                         │
│    recency     ████████░░  0.8                             │
│    relevance   ██████░░░░  0.6                             │
│    quality     ████████░░  0.8                             │
│    uniqueness  █████░░░░░  0.5                             │
│                                                             │
│  Thresholds                                                 │
│    auto_ready  [ 0.75 ]                                     │
│    skip        [ 0.30 ]                                     │
│                                                             │
│  Freshness                                                  │
│    max_age_hours  [ 48  ]                                   │
│    decay_rate     [ 0.1 ]                                   │
```

#### Processing 탭
```
│  (Processing 탭)                                            │
│                                                             │
│  Batch                                                      │
│    Max retries     [ 3  ]                                   │
│    Retry delay     [ 5  ] seconds                           │
│    Request timeout [ 30 ] seconds                           │
│                                                             │
│  Quality Check                                              │
│    [ ☑ ] Enabled                                            │
│    Primary model       [ gpt-4o-mini    ]                   │
│    Auto approve above  [ 0.85 ]                             │
│    [ ☑ ] Feedback enabled                                   │
│                                                             │
│  Deduplication                                              │
│    Embedding threshold  [ 0.92 ]                            │
```

#### Advanced 탭
```
│  (Advanced 탭)                                              │
│                                                             │
│  Logging                                                    │
│    Level   [ INFO  ▼ ]                                      │
│    [ ☑ ] File logging                                       │
│    [ ☐ ] Console logging                                    │
│                                                             │
│  Notification                                               │
│    [ ☐ ] Slack enabled                                      │
│    Webhook  [                              ]                │
│                                                             │
│  Generation                                                 │
│    Max retries       [ 2  ]                                 │
│    [ ☑ ] Auto approve high quality                          │
│    Auto approve threshold  [ 0.90 ]                         │
```

#### 주요 컴포넌트
- 탭 전환 시 미저장 변경사항 있으면 "저장하지 않은 변경사항이 있습니다" 경고
- Save Changes는 현재 탭만 저장 (탭별 독립 저장)

---

## UI 컴포넌트 라이브러리

### 0. 네비게이션 바 (공통)

모든 화면 상단에 고정 표시되는 공통 네비게이션.

```
┌─────────────────────────────────────────────────────────────┐
│  Picko  [ Dashboard ] [ Inbox ] [ Review ] [ Video ]        │
│                                            [ Manage ▼ ]     │
│                                           ┌──────────────┐  │
│                                           │  Sources     │  │
│                                           │  Accounts    │  │
│                                           │  Styles      │  │
│                                           │  Settings    │  │
│                                           └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

| 항목 | 경로 | 성격 |
|------|------|------|
| Dashboard | `/` | 현황 파악 + 워크플로우 진입 |
| Status | `/status` | 실행 중 진행 로그 + 완료 결과 (Collection/Generate 공용) |
| Inbox | `/inbox` | 수집 후 생성 대상 선택 |
| Review | `/review` | 생성물/영상기획 승인 |
| Video | `/video` | VideoPlan 생성 및 목록 |
| Manage > Sources | `/sources` | 소스 활성화/발견/승인 |
| Manage > Accounts | `/accounts` | 계정 목록 및 상세 편집 |
| Manage > Styles | `/styles` | 스타일 프로필 생성/관리 |
| Manage > Settings | `/settings` | 전역 설정 (Vault, LLM 등) |

### 1. 버튼 (Buttons)

```
[ ▶ Primary Action ]   — 주요 액션, 강조색
[ Secondary Action ]   — 보조 액션, 테두리만
[ ✗ Destructive    ]   — 삭제/거절, 빨간색
[ Cancel           ]   — 취소, 회색
```

| 타입 | 용도 |
|------|------|
| Primary | Generate, Approve, Run, Save |
| Secondary | 일반 액션 |
| Destructive | Delete, Reject, Cleanup |

### 2. 체크박스 (Checkboxes)

```
☑ 선택됨
☐ 미선택
━ 일부 선택 (indeterminate)
```

### 3. 상태 표시기 (Status Indicators)

```
● 활성 / 완료 (초록)
○ 비활성 / 대기 (회색)
⚡ 처리 중 (주황)
✅ 성공
❌ 실패/오류
⏳ 진행 중
```

### 4. 탭 배지

```
[ 📝 Generated (8) ]   — 처리 대기 항목 수
[ Pending (3) ]        — 숫자 0이면 배지 숨김
```

---

## 인터랙션 패턴

### 모달
- 배경 클릭 또는 [✕] 클릭으로 닫기
- ESC 키로 닫기
- 모달 내 폼 제출은 Enter 키 지원

### Undo Toast
- Approve/Reject 즉시 반영 후 "Undo" 토스트 3초 표시
- Undo 클릭 시 이전 상태로 복원

### 인라인 확장
- 아이템 행 클릭 → 아래로 확장 (토글)
- 체크박스 클릭은 확장 트리거 안 함 (독립 동작)

---

## 기술 구현 가이드

### 라우팅
```
/                  → Dashboard
/status            → 실행 상태 (Collection/Generate 공용)
/inbox             → 인박스
/review            → 리뷰
/video             → 동영상 목록
/video/:id         → VideoPlan 상세
/accounts          → 계정 목록
/accounts/new      → 새 계정 생성
/accounts/:id      → 계정 상세/편집
/styles            → 스타일 목록
/styles/new        → 새 스타일 생성
/styles/:name      → 스타일 상세
/sources           → 소스 관리
/settings          → 설정
```

### 전체 워크플로우 흐름
```
Dashboard
  → [Start New Collection] → 모달 → /status(collection)
  → [Go to Inbox] → /inbox
  → [Generate Selected] → 모달 → /status(generate)
  → [Go to Review] → /review
  → [Approve/Reject] → Done

Action Needed 카드
  → "Inbox to select: N"    → /inbox
  → "To approve: N"         → /review (Generated 탭)
  → "Video review: N"       → /review (Video Plans 탭)
```

---

## 키보드 단축키

| 키 | 기능 |
|----|------|
| `Ctrl/Cmd + Enter` | 실행 |
| `Ctrl/Cmd + S` | 저장 |
| `Ctrl/Cmd + R` | 새로고침 |
| `Esc` | 모달 닫기 |
| `Tab` | 다음 입력 필드 |
| `Shift + Tab` | 이전 입력 필드 |
| `Ctrl/Cmd + /` | 빠른 검색 |

---

## 접근성 고려사항

### 1. 화면 읽기기 지원
- 모든 컴포넌트에 적절한 ARIA 레이블
- 키보드 네비게이션 완벽 지원
- 포커스 시각적 표시

### 2. 색상 대비
- 텍스트 대비 비율 4.5:1 이상
- 색상만 의존하지 않는 인디케이터

### 3. 반응형 디자인
- 모바일 우선 접근
- 터치 가능 영역 최소 48x48px
- 가로 스크롤 최소화
