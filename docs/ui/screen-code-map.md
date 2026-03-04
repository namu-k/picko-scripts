# Screen-Code Mapping (MVP v1 First Pass)

작성일: 2026-03-04
목적: 화면별로 프론트엔드 라우트, API, 백엔드 실행 지점을 한 번에 추적할 수 있도록 연결 정보를 고정한다.

## 사용 규칙 (Template)

- 화면/버튼/플로우가 바뀌면 아래 표를 같이 업데이트한다.
- 최소 1개 이상의 증거 링크(문서/코드 경로+라인)를 각 칸에 남긴다.
- `Scope`는 `MVP v1`, `v1.x`, `v2` 중 하나로 명시한다.

### Mapping Table Template

| Screen | Route | FE Trigger / State | API Endpoint(s) | Backend Action | Module / Function | Evidence | Scope | Notes / Gaps |
|---|---|---|---|---|---|---|---|---|
| 예: Dashboard | `/` | Start button click | `POST /api/v1/workflows/{workflow_name}/run` | `collector.run` | `scripts/daily_collector.py:run` | `docs/ui/...`, `docs/api/...`, `picko/...` | MVP v1 | 없으면 `TBD` |

## Current Mapping (First Pass)

| Screen | Route | FE Trigger / State | API Endpoint(s) | Backend Action | Module / Function | Evidence | Scope | Notes / Gaps |
|---|---|---|---|---|---|---|---|---|
| Dashboard | `/` | `Start New Collection` -> `Run Now` | `POST /api/v1/collect/rss`, `POST /api/v1/collect/perplexity`, (orchestrated) `POST /api/v1/workflows/{workflow_name}/run` | `collector.run` | `scripts/daily_collector.py:109`, `picko/orchestrator/default_actions.py:54` | `docs/ui/mvp-wireframes.md:65`, `docs/ui/mvp-wireframes.md:107`, `docs/ui/mvp-wireframes.md:132`, `docs/api/README.md:46`, `docs/api/README.md:79`, `docs/api/README.md:357` | MVP v1 | `/run/collect`는 별도 페이지 없이 인라인 모달로 명시됨 |
| Status | `/status` | Collect/Generate 실행 후 자동 진입, 진행률/로그 표시 | `GET /api/v1/workflows/executions/{execution_id}` | Workflow execution status | `picko/orchestrator/engine.py:54`, `scripts/run_workflow.py:51` | `docs/ui/mvp-wireframes.md:153`, `docs/ui/mvp-wireframes.md:155`, `docs/api/README.md:395`, `scripts/run_workflow.py:50` | MVP v1 | 실시간 스트림 방식(SSE/WebSocket)은 구현 선택(TBD) |
| Inbox | `/inbox` | 아이템 선택 후 `Generate Selected` | `POST /api/v1/generate/longform`, `POST /api/v1/generate/packs`, (이미지 최종 렌더 시) `POST /api/v1/media/render/batch` | `generator.run` | `scripts/generate_content.py:87`, `scripts/generate_content.py:483`, `scripts/generate_content.py:591`, `scripts/generate_content.py:662`, `picko/orchestrator/default_actions.py:74` | `docs/ui/mvp-wireframes.md:203`, `docs/ui/mvp-wireframes.md:234`, `docs/api/README.md:106`, `docs/api/README.md:136`, `docs/api/README.md:338` | MVP v1 | `generate_content`는 이미지 프롬프트 생성 중심, 최종 PNG 렌더는 별도 흐름 |
| Review | `/review` | Generated/Video Plans 승인/거절, 모달 읽기 후 결정 | `POST /api/v1/quality/verify`, `GET /api/v1/quality/graph/{item_id}` | `quality.verify` | `picko/orchestrator/default_actions.py:26`, `picko/quality/graph.py` | `docs/ui/mvp-wireframes.md:266`, `docs/ui/mvp-wireframes.md:323`, `docs/api/README.md:177`, `docs/api/README.md:213` | MVP v1 | 콘텐츠 승인 UI의 실제 저장/상태 전이 API는 상세 계약 보강 필요 |
| Video | `/video` | VideoPlan 생성, 목록 조회, 재생성/복사 | `POST /api/v1/media/render/image`, `POST /api/v1/media/render/batch` | `renderer.run` (render path) | `scripts/render_media.py:82`, `picko/orchestrator/default_actions.py:122`, `picko/video_plan.py` | `docs/ui/mvp-wireframes.md:338`, `docs/api/README.md:304`, `docs/api/README.md:338`, `scripts/render_media.py:66` | MVP v1 | VideoPlan CRUD 전용 API는 문서화 미흡, 현재는 CLI/모듈 조합 중심 |
| Video Detail | `/video/:id` | 샷 상세 확인, Export JSON, Regenerate | (TBD: dedicated endpoint), reuse media/workflow endpoints | (TBD) | `picko/video_plan.py`, `scripts/render_media.py` | `docs/ui/mvp-wireframes.md:423` | MVP v1 | 상세 화면 전용 REST 경로는 API 문서에 직접 정의되어 있지 않음 |
| Sources | `/sources` | Active/Pending/Discover 탭, 승인/거절/발견 실행 | `POST /api/v1/discover/sources`, `POST /api/v1/discover/register` | source discovery / curation actions | `scripts/source_discovery.py:118`, `scripts/source_curator.py:80`, `picko/source_manager.py` | `docs/ui/mvp-wireframes.md:744`, `docs/ui/mvp-wireframes.md:1022`, `docs/api/README.md:244`, `docs/api/README.md:278` | MVP v1 (ops) | UI에서 `source_curator` 동작(approve/reject/report) endpoint 명시 보강 필요 |
| Settings | `/settings` | Vault/LLM/Scoring/Processing 설정 수정, 저장 | `GET /api/v1/system/status` (health), config update endpoints TBD | settings read/write + health checks | `picko/config.py`, `scripts/health_check.py:43` | `docs/ui/mvp-wireframes.md:841`, `docs/ui/mvp-wireframes.md:1025`, `docs/api/README.md:492`, `scripts/health_check.py:36` | MVP v1 | 설정 저장 API (`PUT/PATCH /settings`)는 API 문서에 미정 |
| Accounts (Management) | `/accounts`, `/accounts/:id` | 계정 목록/편집/CRUD | TBD | TBD | `config/accounts/*.yml`, account modules | `docs/ui/mvp-wireframes.md:526`, `docs/ui/mvp-wireframes.md:529`, `docs/ui/mvp-wireframes.md:531` | v2 | MVP v1 제외 명시됨 |

## Quick Onboarding (개발자용)

1. 화면 라우트는 `docs/ui/mvp-wireframes.md`에서 찾는다.
2. 해당 액션 API는 `docs/api/README.md`에서 찾는다.
3. 액션 이름은 `picko/orchestrator/default_actions.py`에서 찾는다.
4. 실제 실행 로직은 `scripts/*.py` + `picko/*` 모듈로 따라간다.

## Open Gaps (다음 보강 대상)

- Review 승인/거절 상태 전이를 위한 명시적 REST endpoint 계약.
- VideoPlan(`/video`, `/video/:id`)의 생성/조회/수정/삭제 전용 API 계약.
- Settings 저장(`PUT/PATCH`) 계약 문서화.
- Sources의 curate/approve/reject를 API 명세와 1:1 정합화.
