# Tasks: 007-Agentic-Framework

## Status Legend
- ○ Not started
- ◍ In progress
- ● Completed
- ◆ Partially implemented (needs activation)

---

## Phase 0: Enable Existing Quality Gates (P0) ⭐ NEW

**가정: 기존 구현된 기능 중 미사용/비활성화된 것들을 먼저 활성화**

이 Phase는 새로운 코드 없이 기존 코드의 "주석을 해제"하는 것만으로 수행 가능합니다.

### 0.1 Auto-Approve/Reject Thresholds 🔹 CRITICAL

**현황:** `scoring.py` lines 356-362에 `should_auto_approve()` / `should_auto_reject()` 구현되어 있으나 `daily_collector.py`에서 호출하지 않음.

**정확한 삽입 위치:** `daily_collector.py` line 381 (`item["score_obj"] = score`) 직후

- ○ `scripts/daily_collector.py::_score()` 수정 (line 381 직후)
  - 현재: `should_display()`만 호출 (lines 425, 467)
  - 변경: `should_auto_approve()` / `should_auto_reject()` 추가 호출
  - auto_reject 시: `item["status"] = "rejected"` 설정
  - auto_approve 시: `item["writing_status"] = "auto_ready"` 자동 설정

```python
# daily_collector.py line 381 직후에 추가
# (item["score_obj"] = score 다음, existing_embeddings.append 전)

# Auto-approve / auto-reject quality gates
if self.scorer.should_auto_approve(score):
    item["writing_status"] = "auto_ready"
    item["auto_decision"] = "approved"
    logger.info(f"Auto-approved: {item.get('id', 'unknown')} (score={score.total:.2f})")
elif self.scorer.should_auto_reject(score):
    item["status"] = "rejected"
    item["auto_decision"] = "rejected"
    logger.info(f"Auto-rejected: {item.get('id', 'unknown')} (score={score.total:.2f})")
    continue  # skip to next item (don't add to existing_embeddings)
else:
    item.setdefault("writing_status", "pending")
```

- ○ `_export()` 에서 `status == "rejected"` 아이템 건너뛰도록 추가 확인
- ○ 수동 테스트: 고점/저점 아이템으로 auto 동작 확인
- ○ 로그 기록: auto-approve/reject 사유 (`score.total` 값)
### 0.2 DuplicateChecker Pipeline Integration 🔹 HIGH

**현황:** `scripts/duplicate_checker.py` 가 별도 CLI로서 파이프라인에서 자동 호출되지 않음.

**⚠️ API 확인 필요:** `DuplicateChecker.check_content()` 는 파일 경로를 받으며, embedding은 내부에서 생성합니다.

- ○ `scripts/daily_collector.py::_score()` 또는 `_dedupe()` 에 통합
  - 1차 URL 해시 중복 제거 후
  - 2차 Embedding 유사도 검사 추가
  - Threshold: 0.92 이상 시 중복 플래그 또는 건너뜀

```python
# daily_collector._score() 내부에 추가
# 주의: check_content()는 content_path(str)를 받음
from scripts.duplicate_checker import DuplicateChecker

# 이미 export된 노트 경로 목록
existing_note_paths = [str(p) for p in self.vault.list_notes(inbox_path)]
checker = DuplicateChecker(threshold=0.92)

# 새 아이템의 텍스트로 임시 임베딩 생성 후 비교
new_text = f"{item.get('title', '')} {item.get('summary', '')}"
new_embedding = self.embedder.embed(new_text)

# 기존 임베딩들과 유사도 비교
max_sim = 0.0
duplicate_of = None
for existing_emb in existing_embeddings:
    sim = self.embedder.cosine_similarity(new_embedding, existing_emb)
    if sim > max_sim:
        max_sim = sim
        # 해당 임베딩의 content_id 찾기 (별도 매핑 필요)

if max_sim >= 0.92:
    item["duplicate_of"] = duplicate_of
    item["duplicate_similarity"] = max_sim
    item["status"] = "duplicate"
    logger.warning(f"Duplicate detected: {item['id']} (sim={max_sim:.2f})")
    continue
```

- ○ Config 추가: `config.yml` 에 `deduplication.embedding_threshold: 0.92`
- ○ 로그: 중복 감지 시 `duplicate_of` ID 기록
- ○ **추가 작업:** `existing_embeddings` 와 `content_id` 매핑 테이블 필요
### 0.3 Freshness Weight Config 🔹 MEDIUM

**현황:** `scoring.py` 에서 `freshness` 가중치를 코드에서 하드코딩 (0.15)하나 `config.yml` 에 동일 값이 없음.

- ○ `config/config.yml` 에 `scoring.weights.freshness` 추가

```yaml
scoring:
  weights:
    novelty: 0.3
    relevance: 0.4
    quality: 0.3
    freshness: 0.15  # ADD THIS
```

- ○ 결과: 전체 가중치 합계 1.15로 정규화
- ○ 상대적으로 가중치 재조정 가능

### 0.4 Validation Auto-Run 🔹 MEDIUM

**현황:** `validate_output.py` 가 별도 CLI로 수동 실행되며 CI에서만 호출됨.

**⚠️ API 확인 필요:** `OutputValidator.validate_path()` 는 `ValidationReport` 를 반환하며, 개별 결과는 `report.results[0]` 로 접근해야 함.

- ○ `scripts/generate_content.py` 수정
  - `__init__` 에 `self.validator = OutputValidator()` 추가
  - Longform/Packs/Images 생성 후 각각 검증 실행
  - 검증 실패 시 로그 기록 및 results['errors'] 에 추가

```python
# 1. ContentGenerator.__init__ 에 추가
from scripts.validate_output import OutputValidator
self.validator = OutputValidator()

# 2. _generate_longform() 내부, vault.write_note() 직후에 추가
if not self.dry_run:
    output_path = f"{self.config.vault.longform}/{longform_data['id']}.md"
    # ... write_note 호출 ...
    logger.info(f"Created longform: {output_path}")

    # Validation
    try:
        report = self.validator.validate_path(output_path, recursive=False)
        if report.results:
            result = report.results[0]
            if not result.valid:
                logger.error(f"Longform validation FAILED: {result.errors}")
                results['errors'].append({
                    "path": output_path,
                    "type": "longform",
                    "errors": result.errors,
                })
            else:
                logger.info(f"Longform validation passed: {output_path}")
    except Exception as e:
        logger.warning(f"Validation error: {e}")

# 3. Packs와 Images에도 동일 패턴 적용
# _generate_packs(), _generate_packs_for_channels(), _generate_image_prompt()
```

- ○ Config 추가: `generation.auto_validate: true` (켜고 끔 목적)
- ○ 로그: 검증 실패 사유별 기록
### 0.5 Relevance Normalization Fix 🔹 LOW

**현황:** `scoring._calculate_relevance()` 의 `base = max(2.0, 3.5 - 0.5*matches)` 가 AccountIdentity 필드 수에 따라 점수를 완곡시킨다.

- ○ `picko/scoring.py::_calculate_relevance()` 수정
  - 현재: 동적 base 계산
  - 변경: 고정 base 사용 (또는 config에서 설정 가능)

```python
# 수정 전
base = max(2.0, 3.5 - (matches * 0.5))

# 수정 후
FIXED_BASE = 3.0  # 일관된 기준
# 또는 config에서 로드
```

- ○ 단위 테스트: matches 수가 달라도 동일한 점수 범위 보장

### 0.6 Tests
- ○ `tests/test_scoring_auto_gates.py` — auto-approve/reject 활성화 테스트
- ○ `tests/test_collector_dedup.py` — embedding 중복 탐지 통합 테스트
- ○ `tests/test_generation_validation.py` — 자동 검증 테스트
---

## Pre-Implementation Design Decisions ⚠️

**Phase 1 착수 전 반드시 결정해야 할 설계 이슈들**

### D1. HumanReviewBot Async/Sync Strategy 🔹 CRITICAL

**이슈:** Telegram Bot API는 기본적으로 polling 방식이나 webhook 방식을 지원. 스케줄러(`daily_collector`)와 병행 실행 시 어떤 방식을 사용할지 결정 필요.

**옵션:**
1. **Polling (권장):** 별도 스레드에서 `bot.polling()` 실행. 스케줄러와 독립적.
   - 장점: 설정 간단, 방화벽 제약 없음
   - 단점: 메시지 지연 가능 (최대 polling 간격)
2. **Webhook:** FastAPI/Flask 서버를 80/443 포트에 실행.
   - 장점: 실시간 응답
   - 단점: 포트 충돌 가능, HTTPS 인증서 필요
3. **Hybrid:** 스케줄러 실행 시에만 polling 시작, 종료 시 중단.
   - 장점: 리소스 효율
   - 단점: 스케줄러 외 시간대 알림 불가

**결정 필요:** [ ] Polling / [ ] Webhook / [ ] Hybrid

### D2. SourceMeta 필드: `api_provider` vs `platform` 🔹 CLARIFICATION

**현황:** `SourceMeta`에 `platform` 필드가 이미 존재 (newsletter 전용, line 43).
새로 추가할 `api_provider`와 용도가 다름:

| 필드 | 용도 | 예시 값 |
|------|------|--------|
| `platform` | 뉴스레터 플랫폼 식별 | `substack`, `buttondown`, `beehiiv` |
| `api_provider` | 소셜 API 제공자 식별 | `threads`, `reddit`, `mastodon` |

**결정:** 두 필드 모두 유지 (용도 다름). 혼동 방지를 위해 주석 추가.

### D3. `quality.verify` Action: source_id Tracking 🔹 HIGH

**이슈:** `quality.verify` 액션이 새 소스 여부를 감지할 때, 아이템의 출처(source_id)를 어떻게 추적할지 정의 필요.

**현재 아이템 frontmatter:**
```yaml
source: techcrunch  # source_id (sources.yml의 id)
```

**제안 로직:**
1. `item.get("source")` → `source_id`
2. `SourceManager.get_by_id(source_id)` → `SourceMeta`
3. `SourceMeta.auto_discovered == True` && `collected_count < 5` → 새 소스
4. 새 소스면 `enhanced_verification = True` 설정

**구현 위치:** `picko/orchestrator/default_actions.py::quality_verify()`

### D4. `collections_remaining` Concurrent Write Handling 🔹 MEDIUM

**이슈:** 여러 프로세스가 동시에 `collections_remaining`을 감소시킬 때 race condition 발생 가능.

**해결 방안 옵션:**
1. **File Locking:** `portalocker` 또는 `fcntl` 사용
2. **Atomic Update:** YAML 대신 SQLite DB 사용 (이미 LangGraph checkpoint에서 사용)
3. **Single Process:** 감소 로직을 한 프로세스에서만 수행 (orchestrator)

**권장:** Option 3 (Single Process) - orchestrator가 유일한 작성자. 읽기 전용은 다른 프로세스에서 가능.

### D5. Bot Webhook Server Coexistence 🔹 LOW

**이슈:** Webhook 방식 선택 시 스케줄러(예: APScheduler, Windows Task Scheduler)와 포트 충돌 가능.

**해결 방안:**
- Polling 방식 선택 (D1에서 Polling 선택 시 문제 없음)
- 또는 Webhook 서버를 별도 프로세스로 실행 (포트 8080 등)

---
## Phase 1: Foundation (P0)

**공통 인프라 — 다른 모든 Phase의 선행 조건**

### 1.1 Notification Bot ⬅️ **START HERE**
- ⬜ `picko/notification/__init__.py`
- ⬜ `picko/notification/bot.py` — `HumanReviewBot` 클래스
  - `notify_quality_review(item_id, title, confidence, reason)` → Telegram/Slack 메시지 전송
  - `notify_source_discovered(source_id, handle, platform, score)` → 소스 발견 알림
  - `handle_callback(callback_data)` → 승인/거절 버튼 응답 처리
  - Vault frontmatter 업데이트 (status: approved / rejected)
- ⬜ 72시간 만료 자동 거절 (`REVIEW_TIMEOUT_HOURS`)
- ⬜ 재알림 기능 (24h 미응답 시)
- ⬜ 환경 변수: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (또는 Slack 대응)

### 1.2 Human Confirmation Gate
- ⬜ `picko/discovery/gates.py` — `HumanConfirmationGate` 클래스
  - `requires_review(platform, domain, relevance_score) -> bool`
  - 소셜 플랫폼(threads/reddit/mastodon/instagram/facebook/linkedin): 항상 True
  - 신뢰 도메인 RSS + score >= 0.9: False
- ⬜ `tests/test_gates.py`

### 1.3 BaseDiscoveryCollector
- ⬜ `picko/discovery/__init__.py`
- ⬜ `picko/discovery/base.py` — `BaseDiscoveryCollector` 추상 클래스
  - `search(keyword: str) -> list[SourceCandidate]`
  - `SourceCandidate` 데이터클래스 (handle, platform, url, relevance_score, metadata)

### 1.4 SourceMeta 스키마 확장
- ⬜ `picko/source_manager.py` — `SourceMeta`에 필드 추가:
  - `human_review_required: bool = False`
  - `api_provider: str | None = None`
  - `account_handle: str | None = None`
  - `last_api_sync: str | None = None`
  - `enhanced_verification: dict | None = None`  # {enabled, collections_remaining, elevated_threshold}
- ⬜ `to_dict()` / `from_dict()` 업데이트
- ⬜ 기존 V2 필드와 중복 없음 확인

### 1.5 Tests
- ⬜ `tests/test_discovery_gates.py`
- ⬜ `tests/test_notification_bot.py` (mock Telegram API)
- ⬜ `tests/test_source_meta_extended.py`

---

## Phase 2: Quality Layer (P0)

**선행 조건: Phase 1 완료**

### 2.1 LangGraph 의존성
- ⬜ `pyproject.toml`에 추가: `langgraph>=0.3.0,<0.4.0`, `langchain-core>=0.3.0,<0.4.0`
- ⬜ `langgraph-checkpoint-sqlite` 패키지 별도 설치 필요 (0.3.x에서 분리됨)
- ⬜ `SqliteSaver` 임포트 경로 0.3.x 기준으로 확인

### 2.2 QualityState & Graph
  - ⬜ `picko/quality/__init__.py`
  - ⬜ `picko/quality/graph.py` — `QualityState` TypedDict + LangGraph 상태 머신
  - 노드: `primary_validation`, `cross_check`, `external_check`, `confidence_calc`, `human_review`
  - 라우팅: confidence >= 0.9 → approved, 0.7-0.9 → cross_check, < 0.7 → rejected
  - SQLite 체크포인트 (`cache/quality_checkpoints.db`)
  - 강화 검증 모드: `enhanced_verification=True`이면 cross_check 의무화 + 임계값 0.92

  ### 2.3 Primary Validator
  - ⬜ `picko/quality/validators/__init__.py`
  - ⬜ `picko/quality/validators/primary.py`
  - `validate(item: dict) -> dict`
  - 평가 기준: 사실 정확성, 출처 신뢰성, 편향 여부, 가치 제공 (0-10)
  - JSON 파싱 실패 시 fallback: `needs_review`, confidence=0.5

### 2.4 Cross-Check Validator
  - ⬜ `picko/quality/validators/cross_check.py`
  - 1차와 다른 LLM 모델 사용 (GPT ↔ Claude)
  - `agreement` 여부 계산

  ### 2.5 Confidence Calculator (정규화 포함)
  - ⬜ `picko/quality/confidence.py`
  - `calculate_final_confidence(primary, cross_check=None, external=None) -> float`
  - **정규화 로직:** 사용 단계 수에 따라 가중치 자동 재계산
    - primary only: 1.0
    - primary + cross_check: 62.5% / 37.5%
    - primary + cross_check + external: 50% / 30% / 20%
  - cross_check 불일치 시 50% 패널티

### 2.6 Feedback Loop
  - ⬜ `picko/quality/feedback.py` — `FeedbackLoop` 클래스
  - `record_feedback(item_id, ai_verdict, human_verdict, ...) → JSONL 기록
  - `get_accuracy_metrics(days=30) -> dict`

### 2.7 Vault Integration
- ⬜ 품질 검증 완료 후 Vault frontmatter 업데이트 (`quality`, `job_history`)
- ⬜ `needs_review` 아이템: Bot 알림 전송 후 `pending` 상태로 보존

### 2.8 Tests
- ⬜ `tests/test_quality_graph.py` — 상태 전환, 라우팅
- ⬜ `tests/test_quality_validators.py` — JSON 파싱, verdict 로직
- ⬜ `tests/test_quality_confidence.py` — 가중치 정규화 케이스
- ⬜ `tests/test_quality_feedback.py` — 피드백 기록, 메트릭
  - ⬜ `tests/test_quality_enhanced_verification.py` — 강화 검증 모드

  ---

  ## Phase 3: Platform Adapters (P0)

**선행 조건: Phase 1, 2 완료 + Threads API 동작 검증**

  > ⚠️ **Phase 3 시작 전 필수:** Meta Graph API에서 `/keyword_search` 실제 동작 확인.
  > 검증 실패 시 Reddit → Mastodon 순서로 먼저 진행.

  ### 3.1 Threads Adapter
- ⬜ `picko/discovery/adapters/__init__.py`
- ⬜ `picko/discovery/adapters/threads.py` — `ThreadsDiscoveryAdapter`
  - `search(keyword) -> list[SourceCandidate]`
  - Meta API `/keyword_search` 연동 (500 쿼리/7일 레이트 리밋 준수)
  - API 버전 고정
- ⬜ 환경 변수: `THREADS_ACCESS_TOKEN`

  ### 3.2 Reddit Adapter
  - ⬜ `picko/discovery/adapters/reddit.py` — `RedditDiscoveryAdapter`
  - `/subreddits/search` 연동 (60 요청/분)
  - OAuth 인증
    - ⬜ 환경 변수: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`

  ### 3.3 Mastodon Adapter
- ⬜ `picko/discovery/adapters/mastodon.py` — `MastodonDiscoveryAdapter`
  - `/api/v2/search` 연동 (30 요청/분)
  - ⬜ 환경 변수: `MASTODON_ACCESS_TOKEN`

  ### 3.4 Discovery Orchestrator
- ⬜ `picko/discovery/orchestrator.py` — `SourceDiscoveryOrchestrator`
  - 여러 어댑터를 순서대로 실행
  - `HumanConfirmationGate` 통과 후 `SourceMeta` 생성
  - `pending` 소스: Vault + sources.yml에 기록, Bot 알림 전송
  - `active` 소스: `enhanced_verification` 플래그 설정 후 sources.yml에 추가

### 3.5 Tests
- ⬜ `tests/test_adapter_threads.py` (HTTP mock)
- ⬜ `tests/test_adapter_reddit.py` (HTTP mock)
- ⬜ `tests/test_adapter_mastodon.py` (HTTP mock)
- ⬜ `tests/test_discovery_orchestrator.py`
---

## Phase 4: Integration (P1)

**선행 조건: Phase 1, 2, 3 완료**
- ⬜ `picko/orchestrator/engine.py` — `dynamic_steps` 지원
- ⬜ `picko/orchestrator/actions.py` — `ActionConfig`에 `fallback` 필드 추가
- ⬜ `picko/orchestrator/expr.py` — 새 연산자: `contains_topic`, `score_range`, `has_quality_flag`

### 4.2 Quality Action 등록
- ⬜ `picko/orchestrator/default_actions.py`에 `quality.verify` 액션 등록
  - 새 소스 여부 감지 → `enhanced_verification` 모드 자동 적용
  - 검증 완료 후 `collections_remaining` 감소

### 4.3 Config 확장
- ⬜ `config/config.yml`에 `quality` 섹션 추가
  - `quality.enabled: true/false` (롤백 플래그)
  - `quality.primary.model`, `quality.cross_check.model`
  - `quality.final.auto_approve_threshold: 0.85`
  - `quality.feedback.enabled: true`
- ⬜ `config/config.yml`에 `notification` 섹션 추가
  - `notification.provider: telegram` (또는 slack)
  - `notification.review_timeout_hours: 72`

### 4.4 Example Workflow
- ⬜ `config/workflows/agentic_pipeline.yml` — 품질 검증 포함 전체 파이프라인 예시

### 4.5 E2E Tests
- ⬜ `tests/test_e2e_agentic.py`
  - 전체 파이프라인 + 품질 검증
  - fallback on fetcher failure
  - low confidence → pending 상태 확인
  - high confidence → auto approve
  - 강화 검증 모드 E2E
  - LangGraph 체크포인트 재개

---

## Phase 5: Meta Platforms (P2, 선택)

**선행 조건: App Review 승인**

### 5.1 Instagram Adapter
- ⬜ `picko/discovery/adapters/instagram.py`
- ⬜ `/ig_hashtag_search` 연동

### 5.2 Facebook Adapter
- ⬜ `picko/discovery/adapters/facebook.py`
- ⬜ `/pages/search` 연동

---

## Documentation

- ⬜ `CLAUDE.md` 업데이트 (새 모듈, 환경 변수)
- ⬜ `.env.example` 업데이트 (Bot 토큰, Threads/Reddit/Mastodon API 키)
- ⬜ `specs/007-agentic-framework/spec.md` ✅ 완료

---

## Dependencies

### New Python Packages
```toml
"langgraph>=0.3.0,<0.4.0",
"langchain-core>=0.3.0,<0.4.0",
"python-telegram-bot>=21.0",   # Telegram 선택 시
# "slack-sdk>=3.0",            # Slack 선택 시
```

### External APIs
- Meta Threads API (500 쿼리/7일) — **Phase 3 전 동작 확인 필수**
- Reddit OAuth API (60 요청/분)
- Mastodon Instance API (30 요청/분)
- Telegram Bot API / Slack API

### Environment Variables
```bash
THREADS_ACCESS_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
MASTODON_ACCESS_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
REVIEW_TIMEOUT_HOURS=72
```

---

## Recommended Implementation Order

```
1. Notification Bot (1.1)           ← Human Review 인프라
   ↓
2. Human Confirmation Gate (1.2)    ← Gate 로직
   ↓
3. SourceMeta 확장 (1.4)            ← 데이터 스키마
   ↓
4. Quality Layer (Phase 2)          ← 핵심 검증 엔진
   ↓
5. Platform Adapters (Phase 3)      ← 소스 발견 (Threads 동작 확인 후)
   ↓
6. Integration (Phase 4)            ← 전체 연결
```

---

*Created: 2026-03-01*
*Branch: 007-agentic*
