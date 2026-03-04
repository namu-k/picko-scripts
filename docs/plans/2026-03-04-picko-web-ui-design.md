# Picko Web UI — Design Document

**Date**: 2026-03-04
**Branch**: 011-picko-web
**Status**: Design approved, pending implementation plan

---

## 배경 및 동기

Picko는 현재 CLI 전용 도구로, 사용자는 세 가지 도구를 병행 사용해야 한다:

1. **Terminal** — 수집/생성/실행 명령
2. **Obsidian** — Digest 승인, 콘텐츠 검토
3. **Telegram 봇** — 모바일에서 승인 알림 수신 및 응답

이 분산된 워크플로가 핵심 페인포인트다. 승인 하나를 하기 위해 Obsidian을 열거나 Telegram 봇에 응답해야 하고, 파이프라인 상태를 보려면 터미널로 돌아가야 한다. 이 모든 것을 **단일 웹 앱**으로 통합해 Obsidian + Telegram을 완전 대체한다.

### 동영상 지원이 범위에 포함된 배경

현재 `009-ai-video-services` 브랜치에서 `picko video` CLI가 개발 중이다. AI 동영상 서비스(Luma, Runway, Pika 등)에 바로 붙여넣기 가능한 VideoPlan을 생성하는 기능인데, 이 역시 CLI로만 접근 가능하다. 웹 UI를 만드는 김에 VideoPlan 생성 요청과 결과 검토(샷별 프롬프트 복사 등)도 함께 포함하기로 했다.

---

## UI 형태 결정

**후보**: 웹 앱 / 데스크탑 앱(Electron) / TUI / Obsidian 플러그인

**결정: 웹 앱 (브라우저)**

- 데스크탑 앱은 설치가 필요하고 플랫폼 종속성이 생김
- TUI는 현재 CLI와 가장 가깝지만 모바일 접근 불가 (Telegram 대체 불가)
- Obsidian 플러그인은 Obsidian에 여전히 종속됨
- 웹 앱은 어디서나 접근 가능하고 Telegram 봇을 완전히 대체할 수 있는 유일한 선택지

---

## 기능 범위 결정

**질문**: 어떤 기능을 UI로 다룰 것인가?

**결정: 전체 — Picko에 입력 가능한 모든 것**

구체적으로:
- Digest 승인 (writing_status 전환)
- 콘텐츠 생성 실행 트리거
- VideoPlan 생성 요청 및 결과 검토
- 소스 수집 설정 (sources.yml)
- 계정 프로필 편집 (accounts/*.yml)
- 프롬프트/스타일 편집 (config/prompts/)

단, 한 번에 다 만들지 않고 단계적으로 구현한다 (아래 로드맵 참조).

---

## Obsidian / Telegram 관계 결정

**후보**: 웹 UI가 완전 대체 / Obsidian은 두되 웹은 승인 특화 / 모바일 진입점만 웹

**결정: 완전 대체**

- Vault(마크다운 파일시스템)는 백엔드 저장소로 계속 사용하되, 사용자가 직접 Obsidian을 열 필요가 없어야 함
- Telegram 봇이 하던 알림/승인 기능은 웹 UI가 대신함
- 완전 대체를 선택한 이유: 병렬 도구가 늘수록 워크플로가 복잡해지기 때문

---

## 프론트엔드 기술 스택 결정

**후보**: Next.js (React) / SvelteKit / Vue + Vite

**결정: Next.js (React)**

- SSR/SSG 지원으로 초기 로딩 빠름
- API 라우트 내장으로 백엔드 일부를 Next.js 안에서 처리 가능
- FastAPI Python 백엔드와 REST로 연동하기 용이
- 에코시스템과 레퍼런스가 가장 풍부함

---

## 배포 환경 결정

**후보**: 로컬(Picko와 같은 PC) / 클라우드 VPS / Docker 컨테이너

**결정: 클라우드 VPS**

- 어디서나 접근 가능해야 Telegram 봇 대체가 의미 있음
- 로컬 전용이면 모바일 접근 불가 (Telegram을 대체 못함)
- Docker Compose로 `picko-api` + `picko-web` 함께 배포

**파생 결정 — Vault 마이그레이션을 하지 않는 이유**

클라우드 배포라고 해서 Vault를 DB로 마이그레이션할 필요는 없다. VPS에 Vault 디렉토리를 마운트하면 FastAPI가 기존 `vault_io.py`를 그대로 호출할 수 있다. DB 마이그레이션은 불필요한 복잡도를 추가하므로 MVP에서는 파일 그대로 유지한다.

---

## MVP 우선순위 및 로드맵 결정

**세 가지 접근 방식을 검토했다:**

### Option A: 통합 리뷰 대시보드
하루 워크플로 전체를 한 화면에서 처리. 승인 + 품질 점수 + 모니터링 통합.
- **장점**: 매일 쓰는 워크플로에 최적화
- **단점**: 초기 구현 범위가 크고, Vault 접근 레이어 설계가 선행되어야 함

### Option B: 파이프라인 오케스트레이터
단계별(collect → nlp → score → generate → publish) 시각화 중심. 각 스테이지를 노드로 표현.
- **장점**: 엔지니어링 관점에서 전체 흐름 추적에 탁월
- **단점**: 일상적인 "승인" 작업에는 과함. Vault → DB 마이그레이션이 사실상 전제됨. **선택하지 않은 이유**: 핵심 페인포인트(빠른 승인)보다 엔지니어링 뷰에 치우침

### Option C: 미니멀 승인 앱
콘텐츠 카드 하나씩 보여주고 [승인/거절/나중에]만 처리. 품질 점수 표시.
- **장점**: 2주 내 배포 가능. Telegram 봇 즉시 대체
- **단점**: 모니터링 없음. 생성 실행은 CLI 유지

**결정: C로 시작해서 A로 확장**

Telegram 봇 대체가 가장 급한 페인포인트이므로 Option C를 먼저 만든다. 그러나 최종 목표는 Option A(모니터링 + 생성 실행 + 설정 관리 통합)다. C → A로 점진적으로 확장하는 로드맵을 채택한다.

---

## 결정 사항 요약

| 항목 | 결정 | 근거 |
|------|------|------|
| UI 형태 | 웹 앱 (브라우저) | 어디서나 접근, Telegram 대체 가능 유일한 선택지 |
| 기존 도구 관계 | 완전 대체 | 도구 분산이 페인포인트 |
| 프론트엔드 | Next.js (React) | SSR, API 라우트, 에코시스템 |
| 백엔드 | FastAPI (Python) | 기존 Picko 모듈 직접 import |
| 배포 | 클라우드 VPS + Docker Compose | 모바일 접근 필요 |
| Vault 처리 | 파일 그대로 유지 | 마이그레이션은 불필요한 복잡도 |
| 실시간 업데이트 | SSE | 단방향 로그 스트림에 충분, WebSocket보다 단순 |
| 인증 | Bearer token | OAuth는 이후 단계 |
| MVP 전략 | Option C → A 점진 확장 | 승인 페인포인트 먼저, 전체 대시보드는 단계적으로 |
| 동영상 지원 | Phase 2 포함 | 009 브랜치 VideoPlan과 자연스러운 연장선 |

---

## 아키텍처

```
┌─────────────────────────────┐
│   Next.js Web App           │
│   (picko-web/)              │
│   - /inbox                  │
│   - /video/new, /video/:id  │
│   - /sources, /accounts     │
│   - /prompts                │
└────────────┬────────────────┘
             │ REST + SSE
┌────────────▼────────────────┐
│   FastAPI Backend           │
│   (picko/api/)              │
│   - Wraps Picko modules     │
│   - Streams logs via SSE    │
│   - Replaces Telegram bot   │
└────────────┬────────────────┘
             │ Python import
┌────────────▼────────────────┐
│   Picko Core Modules        │
│   vault_io, llm_client,     │
│   scoring, account_context, │
│   video/generator, ...      │
└────────────┬────────────────┘
             │ R/W
┌────────────▼────────────────┐
│   Vault (파일시스템)          │
│   Inbox/Inputs/, Content/,  │
│   config/, ...              │
└─────────────────────────────┘
```

---

## 화면 구성 — 3단계 로드맵

### Phase 1: MVP (Option C — 승인 앱)

**목표**: Telegram 봇이 하던 일을 웹으로 이전. 2주 내 배포.

| 화면 | 경로 | 핵심 기능 |
|------|------|----------|
| Inbox (Digest 승인) | `/inbox` | 수집된 콘텐츠 카드 리스트. 품질 점수·소스·태그 표시. `[auto_ready]` `[manual]` `[skip]` 버튼으로 `writing_status` 전환 |
| 파이프라인 상태 | `/status` | 단계별 진행 상황 (collect → nlp → score → generate). SSE 로그 스트림. 수동 실행 트리거 버튼 |

**Inbox 카드 UI:**
```
┌─────────────────────────────────────────────────────┐
│ [점수: 87]  TechCrunch  #AI #startup                │
│                                                     │
│ OpenAI announces new model with...                  │
│ 요약: GPT-5가 코딩 벤치마크에서...                   │
│                                                     │
│  [✅ auto_ready]  [📝 manual]  [❌ skip]            │
└─────────────────────────────────────────────────────┘
```

---

### Phase 2: 동영상 지원

**목표**: `picko video` CLI를 웹 폼으로 대체. VideoPlan 시각적 검토.

| 화면 | 경로 | 핵심 기능 |
|------|------|----------|
| VideoPlan 생성 | `/video/new` | account / intent / service(복수) / platform / week-of / content-id 입력 폼. 생성 실행 및 진행 상태 SSE 표시 |
| VideoPlan 뷰어 | `/video/:id` | 샷별 카드. 서비스 파라미터(Luma/Runway/Pika/Kling/Veo) 펼치기. **각 샷 프롬프트 복사 버튼**. 품질 점수·이슈·제안 표시 |

**VideoPlan 샷 카드 UI:**
```
┌─────────────────────────────────────────────────────┐
│ Shot 1 — intro  (5초)                               │
│ 새벽 2시, 잠이 오지 않는 밤                           │
│                                                     │
│ ▼ Luma                                              │
│   Dawn bedroom window view, blue hour...            │
│   camera: static | intensity: 2 | preset: cinematic │
│   [📋 프롬프트 복사]                                  │
│                                                     │
│ ▼ Runway  ▼ Pika  ▼ Kling  ▼ Veo                   │
└─────────────────────────────────────────────────────┘
```

---

### Phase 3: 전체 설정 관리

**목표**: YAML 설정 파일들을 웹 UI로 편집 가능하게.

| 화면 | 경로 | 편집 대상 |
|------|------|----------|
| 소스 관리 | `/sources` | `config/sources.yml` — RSS URL, 활성화/비활성화, 품질 점수 |
| 계정 프로필 | `/accounts/:id` | `config/accounts/*.yml` — AccountIdentity, 주간 슬롯, 스타일 프로필 |
| 프롬프트 에디터 | `/prompts` | `config/prompts/**/*.md` — 마크다운 에디터로 LLM 프롬프트 편집 |

---

## 선행 준비 작업 (구현 전 필수)

| 우선순위 | 작업 | 설명 |
|---------|------|------|
| 1 | FastAPI 백엔드 스켈레톤 | `picko/api/` — Picko 모듈 wrapping, 기본 엔드포인트 |
| 2 | SSE 로그 스트리밍 | 파이프라인 실행 출력을 실시간으로 프론트에 전달 |
| 3 | Bearer token 인증 미들웨어 | 모든 API 엔드포인트 보호 |
| 4 | Next.js 프로젝트 초기화 | `picko-web/` 디렉토리, Tailwind CSS |
| 5 | Docker Compose 설정 | `picko-api` + `picko-web` 서비스, Vault 디렉토리 마운트 |

---

## 주요 API 엔드포인트 (예상)

```
GET  /api/inbox              Digest 목록 (오늘 날짜 기준)
PATCH /api/inbox/:id/status  writing_status 변경 (auto_ready/manual/skip)
POST /api/run/collect        daily_collector 실행 트리거
POST /api/run/generate       generate_content 실행 트리거
GET  /api/run/stream         SSE — 실행 로그 스트림

POST /api/video              picko video 실행 (params in body)
GET  /api/video/:id          VideoPlan 조회
GET  /api/video              VideoPlan 목록

GET  /api/sources            소스 목록
PATCH /api/sources/:id       소스 활성화/비활성화
GET  /api/accounts/:id       계정 프로필
PATCH /api/accounts/:id      계정 프로필 수정
```

---

## 범위 밖 (Out of Scope)

- 실제 소셜 미디어 발행 UI (publish는 기존 CLI 유지)
- 사용자 계정 관리 / 멀티 테넌트
- 모바일 앱 (반응형 웹으로 대체)
- Obsidian 플러그인 연동
- AI 영상 서비스 직접 API 호출 (VideoPlan 생성까지만)

---

## 다음 단계

이 설계를 바탕으로 `writing-plans` 스킬로 단계별 구현 계획을 작성한다.

구현 순서: FastAPI 백엔드 → Phase 1 프론트엔드 → Docker Compose 배포 → Phase 2 → Phase 3
