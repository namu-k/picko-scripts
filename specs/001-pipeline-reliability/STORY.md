# 001-pipeline-reliability: 작업 스토리

> 이 문서는 `specs/001-pipeline-reliability/` 폴더에서 진행된 작업의 **목적**, **접근방법**, **해결과정**을 한 흐름으로 정리한 스토리입니다.

---

## 1. 목적 (Why)

### 1.1 배경

Picko 콘텐츠 파이프라인은 **RSS 수집 → NLP·스코어링 → 다이제스트 → 콘텐츠 생성(롱폼/팩/이미지)** 흐름으로 동작한다.  
이미 **daily_collector**, **generate_content**, **validate_output**, **explore_topic**, **prompt_loader** 등 핵심 기능은 구현되어 있었고, BCP 이슈(프롬프트 외부화, 주제 탐색, 레퍼런스 문체, 채널별 이미지 등)도 상당 부분 완료된 상태였다.

그럼에도 **프로덕션에 그대로 내보내기에는 위험**이 있었다.

- **scripts/** 구간 테스트 커버리지 **0%** → 무음 실패·회귀 위험
- **engagement_sync**는 플레이스홀더만 있고, 실제 engagement 데이터 수집 없음 → **피드백 루프 단절**
- **Account Profiles** 미비 → 개인화·스코어 보정 기반 부족

즉, “기능은 있는데 **안정성·검증·가치 증명**이 부족한” 상태를 **프로덕션에 가까운 수준**으로 끌어올리는 것이 목적이었다.

### 1.2 목표 정리

| 목표 | 설명 |
|------|------|
| **안정성** | scripts/ 핵심 경로에 테스트를 두어 무음 실패를 줄이고 회귀를 잡을 수 있게 한다. |
| **피드백 루프** | 최소 1개 플랫폼(Twitter)에서 engagement 메트릭을 실제로 수집해 score calibration·ROI 검증이 가능하게 한다. |
| **운영 기반** | Account Profile(계정 프로필)을 갖추고, 문서·벤치마크로 “무엇을 어떻게 검증하는지”를 남긴다. |

---

## 2. 접근방법 (How)

### 2.1 전문가 패널: Team PIPELINE

“어디까지 해야 프로덕션에 가깝다고 볼 수 있는가?”에 대한 **견해 차이**를 명시적으로 다루기 위해 **가상 전문가 패널(Team PIPELINE)** 을 도입했다.

| 전문가 | 역할 | 관점 |
|--------|------|------|
| **Maya Chen (CPO)** | 성장 옹호자 | “출시가 완벽보다 낫다” — 핵심 파이프라인이 돌면 충분, Account는 수동으로도 가능 |
| **Viktor Petrov (QA)** | 품질 수호자 | “테스트 없는 코드는 깨진 코드” — scripts/ 0% 커버리지는 용납 불가 |
| **Dr. Sarah Kim (Architect)** | 실무 조율자 | “진짜 위험은 끊어진 피드백 루프” — engagement 없이는 ROI 증명·보정 불가 |

이를 통해 **즉시 배포**, **Twitter+LinkedIn 동시 구현**, **수동 CSV 의존** 같은 극단적 대안은 거절하고, **최소 공통 합의** 위주로 액션 플랜을 잡았다.

### 2.2 논의·문서 기반의 작업 순서

- **개선_논의_콘텐츠_파이프라인.md**: 현황·이슈(주제 탐색, 프롬프트 관리, 파생 승인, 레퍼런스, 채널 선택 등)와 제안 작업 순서를 정리.
- **TEAM_BETTER_CONTENT_PIPELINE.md**: 팀 역할(리드, 백엔드, 프롬프트, UX)·Phase별 태스크·GitHub 이슈(#3~#8) 매핑.
- **advisory_report.md / advisory_report_v2.md**: Team PIPELINE 결론을 바탕으로 **KPI(Time-to-Production, System Reliability, Feedback Loop Integrity)** 와 **Phase별 액션 플랜**을 문서화.

즉, “일단 코드부터”가 아니라 **목적 → 논의 → 우선순위 → 액션 플랜 → 실행** 순서로 접근했다.

### 2.3 벤치마크·시나리오로 검증 정의

변경 전후를 비교하고 품질을 추적하기 위해 **고정 시나리오**를 두었다.

- **benchmarks.md**: E2E(S1~S8), 기능 패키지(F1~F9) 시나리오 목록과 공통 평가지표(success_rate, duration, content_quality 등) 정의.
- **tests/benchmarks/scenarios/**: 시나리오별 YAML로 “무엇을 어떤 명령으로 검증하는지”를 재현 가능하게 정의.

이렇게 **목적(안정성·피드백 루프·운영 기반)** 과 **검증 방법(시나리오·KPI)** 을 먼저 정한 뒤, 구현과 버그 수정을 진행했다.

---

## 3. 해결과정 (What & When)

### 3.1 Phase 1: 안정성 확보 (테스트 추가)

**문제**: scripts/ 테스트 커버리지 0%, 무음 실패·회귀 위험.

**접근**:
- Advisory Report에서 **P0**로 daily_collector, generate_content, validate_output 테스트 추가를 확정.
- 각 스크립트별로 **단위 테스트 파일**을 새로 추가하고, Mock 기반으로 파이프라인 단계별 동작을 검증.

**결과** (patch_review.md, PR-10-review 기준):
- `tests/test_daily_collector.py` (23개 테스트): 초기화, URL 정규화, 중복 제거, RSS fetch, NLP, 임베딩, 스코어, 날짜 파싱, ingest, run 등.
- `tests/test_generate_content.py` (23개 테스트): 초기화, 다이제스트 파싱, 라인 파싱, 입력 로드, 섹션 추출, 처리 여부, run, 탐색 로드, writing_status 등.
- `tests/test_validate_output.py` (25개 테스트): 검증 결과/리포트, 타입 감지, 필수/권장 필드, 섹션, 위키링크, 품질, 경로 검증 등.

scripts/ 구간 커버리지가 **0% → 약 55~65%** 수준으로 올라가, System Reliability KPI가 3/10에서 6~8/10 근처로 개선될 수 있는 기반이 마련되었다.

### 3.2 Phase 2: 피드백 루프 복구 (Twitter API)

**문제**: engagement_sync가 플레이스홀더만 있어, engagement 데이터 수집·score calibration이 불가능.

**접근**:
- “한 플랫폼이라도 실제 데이터를 쓸 수 있게 한다”는 합의에 따라 **Twitter API 1개만** 우선 구현.
- engagement_sync.py에 `_get_twitter_client()`, `_fetch_twitter_metrics()`, `_extract_tweet_id()` 등을 추가하고, tweepy는 **optional import**로 두어 의존성·LSP 이슈를 완화.

**결과**:
- Twitter API v2 연동으로 views, likes, retweets, replies 등 메트릭 수집 경로 확보.
- tweepy 미설치 시 경고 후 빈 메트릭 반환 등 에러 처리 정리.
- Feedback Loop Integrity KPI를 0/10에서 4~6/10 수준으로 끌어올릴 수 있는 “최소 구현”이 완료되었다.

### 3.3 Phase 3: 계정 프로필·설정 기반

**문제**: Account Profile 없음/불일치로 레퍼런스·스코어·개인화 기반이 약함.

**접근**:
- `config/accounts/socialbuilders.yml` 생성 (account_id, style_name, interests, channels, keywords 등).
- **config.py**에서 계정 로드 시 **vault 루트 → 프로젝트 루트** 순 fallback으로, 실제 운영/테스트 환경 모두에서 같은 파일을 참조하도록 수정.
- 문서·시나리오에서 사용하던 계정 ID `builders_social_club`를 **socialbuilders**(파일명 stem과 일치)로 통일해 BUG-003/BUG-004 유형 이슈를 제거.

**결과**:
- get_identity('socialbuilders'), get_style_for_account('socialbuilders'), get_account('socialbuilders')가 정상 동작하는지 검증 가능해졌고, generate_content 기본 계정을 default → socialbuilders로 바꾸는 등(BUG-005 대응) 경고를 줄였다.

### 3.4 버그 수정·호환성 정리

**발단**: 벤치마크 시나리오(S1~S8, F1~F9)를 실제로 돌리면서 **bug_report.md**에 5개 버그(BUG-001~005)와 LSP/타입 이슈가 정리됨.

**접근**:
- **bug_fix_instructions.md**에서 우선순위(High → Medium → Low → 부가)와 의존성을 정하고, 버그별로 “수정 작업”과 “검증 방법”을 구체적으로 기술.
- High: BUG-003(계정 ID 통일), BUG-004(계정 YAML 경로·파싱 fallback).
- Medium: BUG-001(validate_output에 `--path` 옵션 추가), BUG-002(daily_collector `--max-items` 및 S1 시나리오 타임아웃 완화).
- Low: BUG-005(기본 계정을 socialbuilders로).
- 부가: tweepy optional 처리, score_calibrator 테스트 쪽 타입(float) 통일.

**결과**:
- CLI 호환성(validate_output `--path`), 계정 로드 안정성, S1 타임아웃 회피, 기본 계정 경고 제거 등이 단위 테스트·벤치마크 시나리오로 재검증 가능한 형태로 정리되었다.

### 3.5 리뷰·문서화

- **patch_review.md**: 패치 범위(계획 문서, 설정, 기능, 테스트), 테스트 결과, Twitter 연동·Account Profile 검증, KPI 달성 현황, 다음 단계를 요약.
- **PR-10-review.md**: feature/pipeline-reliability → main 머지 전 리뷰. 잘된 점(테스트·picko 코어·스크립트·타입), 수정 권장(mock_vault 생성물 제거, pytest 실행 확인, Twitter env 문서화), 머지 전 체크리스트를 정리.

전체적으로 “한 번에 다 고치기”보다 **안정성(테스트) → 피드백 루프(1개 플랫폼) → 계정/설정 → 버그/호환성 → 리뷰** 순서로 단계를 나누어 해결했다.

---

## 4. 설계 방향: Vault–Pipeline 연결 브리지

001에서 쌓은 **계정 프로필·config·프롬프트 주입**은 단순 설정 확장이 아니라, **“기획(Vault)과 실행(Pipeline) 사이의 단절을 잇는 브리지”** 로 가기 위한 기반이다. 이 방향을 명시적으로 두는 이유는, “단순 기계적 자동화”가 아니라 **기획 의도가 실시간으로 반영되는 지능형 워크플로우**로 전환하기 위함이다.

### 4.1 현재 상황: 연결 끊김 (As-Is)

| 구분 | 내용 |
|------|------|
| **기획과 실행의 분리** | Vault(기획 문서)와 Pipeline(실행 스크립트) 사이에 연동이 없음. 기획자가 정한 타겟, 필러(주제), 톤앤매너가 스크립트에 자동으로 전달되지 않음. |
| **문제** | daily_collector, generate_content 등이 “누구를 위한 글인지”, “이번 주 목표가 무엇인지”, “어떤 스타일로 쓸지”를 모른 채 동작함. |
| **결과** | 생성물이 **계획과 무관하게 생성**되어, 브랜드 정체성과 어긋나거나 품질이 떨어질 수 있음. |

### 4.2 제안: 연결 브리지 구축 (To-Be)

**“기획 문서(Markdown·YAML)를 시스템의 설정값(Configuration)으로 직접 사용한다.”**

| 연결 고리 | 활용 방식 |
|-----------|-----------|
| **① 계정 정체성 (identity / accounts \*.yml)** | 타겟·톤앤매너를 **수치(가중치)** 로 활용. **relevance 스코어링**의 기준점, 스타일 추출 시 **“누구에게 보여줄 것인가”** 컨텍스트 주입. |
| **② 주간 슬롯 (weekly_slot)** | 이번 주 목표(KPI)·행동 유도(CTA)를 스크립트에 직접 주입. **필러별 분류**(검증/빌드/성장/스케일 등)에 맞춰 수집·생성, **프롬프트에 “이번 주 목표”** 를 넣어 목적에 맞는 글 생성. |
| **③ 스타일 프로필 연동** | style_extractor로 추출한 레퍼런스 스타일을 계정의 톤앤보이스와 매칭해, **일관된 브랜드 목소리**를 내도록 함. |

이미 **account_context**(get_identity, get_weekly_slot, get_style_for_account), **prompt_composer**(weekly_context 주입), **scoring**(interests·keywords 반영) 등이 이 브리지의 일부를 구현하고 있다. 001은 그 **토대를 안정화**한 것이고, 이후 단계에서 “기획 문서만 수정하면 파이프라인 전반에 반영되는” 수준까지 연결도를 높이는 것이 목표가 된다.

### 4.3 기대 효과

| 효과 | 설명 |
|------|------|
| **일관성** | 기획자가 identity·계정 프로필만 수정해도 생성되는 콘텐츠의 톤·타겟이 일괄 반영됨. |
| **효율성** | 매번 프롬프트를 손으로 고치지 않고, 주간 계획(weekly_slot)만 업데이트하면 시스템이 목표에 맞게 동작함. |
| **전략적 자동화** | “글을 찍어내는 봇”이 아니라 **“전략에 따라 움직이는 에이전트”** 에 가까운 구조로 전환. |

---

## 5. 산출물·참조 요약

| 문서 | 역할 |
|------|------|
| **개선_논의_콘텐츠_파이프라인.md** | 개선 이슈·제안·작업 순서 논의 |
| **TEAM_BETTER_CONTENT_PIPELINE.md** | 팀 역할·Phase·이슈 매핑 |
| **advisory_report.md** / **advisory_report_v2.md** | Team PIPELINE 결론, KPI, 액션 플랜 |
| **jobs_to_do.md** | 완료/미완료 기능·이슈·테스트 커버리지·권장 조치·KPI 목표 |
| **benchmarks.md** | 시나리오 목록·평가지표·평가 템플릿 |
| **bug_report.md** | 벤치마크 실행 중 발견된 버그(BUG-001~005) 상세 |
| **bug_fix_instructions.md** | 버그별 수정 지시·검증 방법·체크리스트 |
| **patch_review.md** | 패치 검토·테스트·기능·KPI 현황 |
| **PR-10-review.md** | feature/pipeline-reliability PR 리뷰·머지 전 체크 |
| **STORY.md** (본 문서) | 목적·접근·해결 과정·설계 방향의 스토리 정리 |

---

## 6. 요약 한 줄

**“기능은 갖춰졌지만 테스트·피드백·계정 기반이 부족했던 파이프라인을, 전문가 관점 논의와 KPI·시나리오를 바탕으로 단계별로 안정화·피드백 루프·버그 수정까지 이어가며 프로덕션에 가깝게 만들고, 궁극적으로는 Vault(기획)와 Pipeline(실행)을 잇는 '연결 브리지'—기획 의도가 실시간으로 반영되는 지능형 워크플로우—로 나아가기 위한 기반을 마련한 작업”** 이라고 요약할 수 있다.
