# Picko I/O-First Wireframe Spec

작성일: 2026-03-05
버전: 1.0

---

## 1) 목적

이 문서는 화면 설계를 "기능/레이아웃"보다 먼저 "입력(Input)과 출력(Output) 계약"으로 고정하기 위한 기준 문서다.

- 와이어프레임 검토 기준을 시각 요소가 아니라 I/O 완결성으로 통일한다.
- 입력 누락, 상태 불일치, 버튼 동작 모호성을 초기에 제거한다.
- 기존 문서(`mvp-wireframes.md`, `wireframes-and-flow.md`, `input-output-artifacts.md`)를 I/O 관점에서 연결한다.

---

## 2) 설계 원칙 (I/O 우선)

1. 입력이 정의되지 않은 액션 버튼은 만들지 않는다.
2. 출력이 정의되지 않은 실행 상태는 만들지 않는다.
3. 상태 전이가 정의되지 않은 배지는 만들지 않는다.
4. 모든 주요 화면은 "입력 영역 + 출력 영역 + 상태 영역" 3블록을 가져야 한다.

---

## 3) 핵심 I/O 계약

### A. Collect (`/run/collect`)

입력
- `date` (필수, YYYY-MM-DD)
- `account` (필수)
- `sources` (선택, MVP v1은 기본 전체 소스)
- `max_items` (선택, 코드 기본: 제한 없음)
- `dry_run` (선택, 기본 false)

출력
- `date`, `collected`, `processed`, `exported`, `errors[]`
- `items[]` (처리된 input id 목록)

화면 반영 규칙
- MVP v1 인라인 실행은 `date/account` 유효 시 활성화 (sources는 기본 전체)
- 고급 `/run/collect` 화면에서는 sources 선택 UI 제공 가능
- 실행 직후 `/status`로 이동
- 완료 시 결과 CTA를 `Go to Inbox`로 노출

### B. Generate (`/run/generate`)

입력
- `date` (필수)
- `type` (필수: longform/packs/images, UI 기본값: longform)
- `force`, `dry_run`, `auto_all`, `week_of` (선택, `week_of`는 YYYY-MM-DD)

출력
- `date`, `approved_items`, `longform_created`, `packs_created`, `image_prompts_created`, `video_prompts_created`, `errors[]`

화면 반영 규칙
- type 미선택 시 Generate 비활성화
- 완료 시 결과 CTA를 `Go to Review`로 노출
- dry-run이면 저장 없음 배지 표시

### C. Video Plan (`/video/new`)

입력
- `account`, `intent`, `goal`, `source_type`, `target_services`, `platforms`, `duration_sec` (필수)
- `source_id`, `brand_style.*` (조건부/선택)

출력
- `id`, `account`, `intent`, `goal`, `source`, `target_services[]`, `platforms[]`, `duration_sec`
- `shots[]` (index, duration_sec, shot_type, script, caption, background_prompt)
- 저장 시 video prompt frontmatter는 `status: pending`

화면 반영 규칙
- 필수 입력 누락 시 Generate Plan 비활성화
- 생성 완료 후 상세 화면(`/video/:id`) 진입 버튼 노출

---

## 4) 상태 전이 표준

### 콘텐츠 상태
- 런타임 `writing_status`: `pending -> auto_ready -> completed`
- 런타임 보조 상태(`status`): `rejected`, `duplicate`, `generated`
- UI가 `processing/skipped`를 표시할 경우, 내부 상태 매핑 규칙을 명시해야 함

### 비디오 플랜 상태
- 런타임 기본값: video prompt frontmatter `pending`
- 상세 워크플로우 상태(`ready/rendering/completed`)는 렌더 파이프라인 계층에서 확장 정의

### 실행 잡 상태
- `queued -> running -> completed`
- 실패 시 `failed`, 재시도 시 `retrying`

와이어프레임 표기 규칙
- 상태는 반드시 배지 + 색상 + 텍스트 3요소로 동시 표기
- running 상태는 진행률(%)와 로그 스트림이 동시에 보여야 함

---

## 5) 화면별 I/O 체크리스트

### `/inbox`
- 입력: 필터(account/date/status), 선택(checkbox), 배치 액션(generate)
- 출력: 아이템 메타(score/tags/source/elapsed), 선택 수, 생성 대상 미리보기
- 상태: writing_status 배지(auto_ready/manual/skip)

### `/status`
- 입력: stop/retry 액션
- 출력: 실시간 로그, 단계별 처리 결과, 요약 수치
- 상태: queued/running/completed/failed

### `/review`
- 입력: approve/reject, (선택)reject reason
- 출력: 생성 결과 본문/샷 목록, 원본 링크/메타
- 상태: pending/approved/rejected

### `/settings`
- 입력: config 필드 편집
- 출력: validation 결과(success/warnings/errors)
- 상태: dirty/saved/applied

---

## 6) 와이어프레임 우선순위 (I/O 기준)

1. `/inbox` (선택 정확도, 배치 액션 안전성)
2. `/status` (실행 가시성, 실패 대응)
3. Generate 모달 (`type`, `dry_run`, `force`)
4. `/review` (승인 의사결정 품질)
5. `/settings` (설정 변경 검증)

---

## 7) 기존 문서 매핑

- 상세 필드 사전: `docs/ui/input-output-artifacts.md`
- 화면 레이아웃: `docs/ui/mvp-wireframes.md`

본 문서는 위 2개 문서의 "I/O 게이트" 역할을 수행한다.

---

## 8) 리뷰 게이트 (완료 기준)

다음 항목을 모두 만족하면 I/O 중심 와이어프레임으로 승인한다.

- 각 핵심 액션 버튼에 필요한 입력이 명시되어 있다.
- 각 실행 결과에 대응하는 출력 컴포넌트가 있다.
- 각 상태 전이에 대응하는 UI 표기와 사용자 액션이 있다.
- dry-run / fail / retry 경로가 화면에서 확인 가능하다.
- 수집(collect) -> 선택(inbox) -> 생성(generate) -> 리뷰(review) 흐름이 끊기지 않는다.

---

## 9) 정합성 메모 (코드 기준)

- 본 문서의 Collect/Generate 출력 스키마는 `scripts/daily_collector.py`, `scripts/generate_content.py`의 실제 반환 키 기준으로 맞춘다.
- Video Plan 필드는 `picko/video_plan.py`의 `VideoPlan` 구조를 기준으로 맞춘다.
- 와이어프레임 라우트와 플로우는 `docs/ui/mvp-wireframes.md` 기준을 따른다.
- `type` 값이 누락된 CLI 호출은 코드에서 all 타입으로 확장될 수 있으므로, UI는 항상 명시적으로 `type`을 전송한다.
