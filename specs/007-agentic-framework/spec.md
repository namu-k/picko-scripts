# 007: Agentic Framework

## Overview

Picko를 에이전틱 워크플로우로 변환하는 두 개의 독립적인 하위 시스템 설계 및 구현.

**상세 설계 문서:**
- [agentic-framework-spec.md](../../docs/plans/2026-02-28-agentic-framework-spec.md) — 비즈니스 요구사항 & 아키텍처
- [hybrid-agentic-pipeline-design.md](../../docs/plans/2026-02-28-hybrid-agentic-pipeline-design.md) — 기술 구현 상세

---

## Current Status (2026-03-01)

- **Phase 4 (Integration)**: 4.1~4.5 구현 완료
- **Foundation/Quality/Discovery**: 핵심 모듈 및 테스트 대부분 구현 완료
- **남은 핵심 작업**
  - `config.yml` deduplication/auto_validate 구성화
  - Quality 결과의 Vault frontmatter(`quality`, `job_history`) 반영
  - `needs_review` Bot 알림 + `pending` 상태 보존 연동
  - `.env.example` Bot 토큰 항목 추가
  - `langgraph-checkpoint-sqlite` 의존성 정책 확정

상세 진행 상태는 `tasks.md`를 기준으로 유지합니다.

---

## Phase 0: Enable Existing Quality Gates ⭐ NEW

**기존에 구현되었으나 비활성화된 품질 관문을 즉시 활성화.**

이 Phase는 새 코드 없이 기존 코드의 주석을 해제하거나 호출만 추가하면 완료됩니다.

### 활성화 항목

| 항목 | 현황 | 조치 | 우선순위 |
|------|------|------|----------|
| **Auto-Approve Threshold** | `scoring.py`에 구현, 미호출 | `daily_collector._score()`에서 호출 추가 | 🔴 Critical |
| **Auto-Reject Threshold** | `scoring.py`에 구현, 미호출 | `daily_collector._score()`에서 호출 추가 | 🔴 Critical |
| **DuplicateChecker** | 독립 CLI, 파이프라인 미통합 | `_score()`에 embedding 중복 탐지 추가 | 🟠 High |
| **Validation Auto-Run** | 독립 CLI, 수동 실행 | `generate_content` 후 자동 검증 | 🟡 Medium |
| **Freshness Weight** | 코드에서 0.15 하드코딩 | `config.yml`에 명시 추가 | 🟡 Medium |
| **Relevance Normalization** | 동적 base로 점수 왜곡 | 고정 base 사용 | 🟢 Low |

### 예상 효과

- Auto-Approve/Reject 활성화로 **인간 검토 부하 30-50% 감소** 예상
- DuplicateChecker 통합으로 **중복 콘텐츠 90% 이상 사전 차단**
- Validation 자동화로 **불완전한 콘텐츠 즉시 검출**

상세 태스크: [tasks.md](./tasks.md#phase-0-enable-existing-quality-gates-p0-)

---

기존 파이프라인에 다단계 LLM 검증 추가.

- LangGraph 상태 머신으로 1차 → 2차 교차 → 신뢰도 계산 흐름 제어
- 신뢰도 임계값에 따라 자동 승인 / Telegram Bot 알림 / 자동 거절
- 피드백 루프: 사람 검토 결과를 Vault에 기록, 정확도 추적

## Subsystem B: Autonomous Source Discovery

소셜 미디어 API를 통해 새 콘텐츠 소스 자동 발견.

- Threads, Reddit, Mastodon API 어댑터
- 모든 소셜 플랫폼 소스는 항상 Telegram Bot 사람 검토
- 승인된 새 소스는 초기 5회 수집 동안 Subsystem A 강화 검증 적용

## 공통 인프라

- **Human Review Bot:** Telegram / Slack. 아이템별 대기 (파이프라인 비블로킹)
- **Vault Logging:** 상태 추적, job_history, 피드백 기록
- **Rollback:** 모든 새 기능은 config.yml 플래그로 즉시 비활성화 가능
