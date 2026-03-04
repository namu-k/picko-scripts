# Picko Web UI — Design Document

**Date**: 2026-03-04
**Branch**: 011-picko-web
**Status**: Design approved, pending implementation plan

---

## 배경 및 동기

Picko는 현재 CLI 전용 도구로, 사용자는 세 가지 도구를 병행 사용해야 한다:

1. **Terminal** — 수집/생성/실행 명령
2. **Obsidian** — Digest 승인, 콘텐츠 검토
3. **Telegram 봇** — 모바일 알림 및 승인

이 분산된 워크플로를 **단일 웹 앱**으로 통합해 Obsidian + Telegram을 완전 대체한다.

---

## 결정 사항 요약

### 플랫폼
- **프론트엔드**: Next.js (React) — SSR 지원, 파일시스템 API 라우트 내장
- **백엔드**: FastAPI (Python) — 기존 Picko 모듈 직접 import
- **배포**: 클라우드 VPS (Docker Compose)
- **실시간 업데이트**: Server-Sent Events (SSE) — WebSocket보다 단순, 단방향 로그 스트림에 충분

### Obsidian/Telegram 대체 전략
Vault 파일시스템은 그대로 유지한다. FastAPI가 `vault_io.py`를 직접 호출하므로 DB 마이그레이션 없이 시작 가능. Telegram 봇(`notification/bot.py`)은 FastAPI 엔드포인트로 대체.

### 인증
Bearer token (단순 API 토큰). OAuth는 이후 단계.

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
