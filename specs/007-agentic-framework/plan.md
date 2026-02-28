# Implementation Plan: 007-Agentic-Framework

> **Status:** Ready
> **Created:** 2026-03-01
> **Branch:** 007-agentic

---

## Reference Documents

| Document | Path | Purpose |
|----------|------|---------|
| **Spec** | `docs/plans/2026-02-28-agentic-framework-spec.md` | 비즈니스 요구사항, 전체 아키텍처 |
| **Design** | `docs/plans/2026-02-28-hybrid-agentic-pipeline-design.md` | 기술 구현 상세, 코드 예시 |
| **Tasks** | `specs/007-agentic-framework/tasks.md` | 작업 체크리스트 |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **D1. Bot Async/Sync** | Polling | 설정 간단, 방화벽 제약 없음 |
| **D2. SourceMeta 필드** | `api_provider` + `platform` 둘 다 유지 | 용도 다름 (소셜 API vs 뉴스레터 플랫폼) |
| **D3. source_id Tracking** | `item.get("source")` → `SourceManager.get_by_id()` | 제안 로직 사용 |
| **D4. Concurrent Write** | Single Process | Orchestrator가 유일한 작성자 |
| **D5. Webhook Coexistence** | N/A (Polling 선택) | 문제 없음 |

---

## Implementation Order

```
Phase 0: Enable Existing Quality Gates (P0) ← START HERE
    │
    │  기존 코드 활성화만으로 수행 가능
    │  - 0.1 Auto-Approve/Reject Thresholds
    │  - 0.2 DuplicateChecker Pipeline Integration
    │  - 0.3 Freshness Weight Config
    │  - 0.4 Validation Auto-Run
    │  - 0.5 Relevance Normalization Fix
    │  - 0.6 Tests
    │
    ▼
Phase 1: Foundation (P0)
    │
    │  인프라 구축
    │  - 1.1 Notification Bot (Polling)
    │  - 1.2 Human Confirmation Gate
    │  - 1.3 BaseDiscoveryCollector
    │  - 1.4 SourceMeta 스키마 확장
    │  - 1.5 Tests
    │
    ▼
Phase 2: Quality Layer (P0)
    │
    │  LangGraph 검증 엔진 (선행 조건)
    │  - 2.1 LangGraph 의존성
    │  - 2.2 QualityState & Graph
    │  - 2.3~2.5 Validators
    │  - 2.6 Feedback Loop
    │  - 2.7 Vault Integration
    │  - 2.8 Tests
    │
    ▼
Phase 3: Platform Adapters (P0)
    │
    │  소셜 미디어 어댑터 (Phase 2 선행)
    │  - 3.1 Threads Adapter
    │  - 3.2 Reddit Adapter
    │  - 3.3 Mastodon Adapter
    │  - 3.4 Discovery Orchestrator
    │  - 3.5 Tests
    │
    ▼
Phase 4: Integration (P1)
    │
    ▼
Phase 5: Meta Platforms (P2, 선택)
```

---

## Quick Start

```bash
# Phase 0 작업 시작
# tasks.md의 Phase 0 섹션 참조
```

---

*See `tasks.md` for detailed checklist.*
