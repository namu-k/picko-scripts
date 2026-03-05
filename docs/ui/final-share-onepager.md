# Picko UI/Backend Final Share - One Pager

작성일: 2026-03-05

## 1) 목표

코어 파이프라인이 있는 상태에서, UI 마무리와 백엔드 연결을 위한 최종 기준을 1페이지로 고정한다.

## 2) 현재 결론 (핵심)

- 현재 우선순위는 IA 단독 문서보다 I/O 중심 와이어프레임이다.
- UI 문서 간 정합성과 코드 정합성은 최종 점검 후 반영 완료했다.
- UI 라우트(`/run/*`, `/status`)는 현재 CLI 기반 런타임(`scripts/*.py`)과 Vault I/O를 어댑터로 연결해야 한다.

## 3) 단일 기준 문서 (먼저 읽기)

- MVP 화면 상세: `docs/ui/mvp-wireframes.md`

## 4) FE/BE 공통 계약 (합의 완료)

### Collect (`/run/collect`)
- 필수 입력: `date`, `account`
- 선택 입력: `sources`(미지정 시 전체), `max_items`, `dry_run`
- 출력 키: `date`, `collected`, `processed`, `exported`, `errors[]`, `items[]`

### Generate (`/run/generate`)
- 입력: `date`, `type`, `force`, `dry_run`, `auto_all`, `week_of`
- `week_of` 포맷: `YYYY-MM-DD`
- 출력 키: `approved_items`, `longform_created`, `packs_created`, `image_prompts_created`, `video_prompts_created`, `errors[]`
- UI 규칙: `type`은 항상 명시 전송 (누락 시 CLI 기본이 all로 확장 가능)

### Video Plan (`/video/new`)
- 출력 계약: `id`, `account`, `intent`, `goal`, `source`, `target_services[]`, `platforms[]`, `duration_sec`, `shots[]`
- 저장 기본 상태: video prompt frontmatter `status: pending`

## 5) 상태 표기 원칙

- 런타임 `writing_status`: `pending -> auto_ready -> completed`
- 런타임 보조 `status`: `rejected`, `duplicate`, `generated`
- UI에 `processing/skipped`를 표시하면 내부 상태 매핑 규칙을 함께 정의해야 한다.

## 6) account 정보 입력/전달 경로

- Collect: CLI/어댑터에서 `--account` 입력 (`scripts/daily_collector.py`)
- Collect 런타임: `DailyCollector(account_id=...)` -> `self.account_id` 저장 -> `config.get_account(self.account_id)` 로 계정 프로필 로드
- Export 시점: 수집 아이템에 `item["account_id"] = self.account_id` 주입 후 Input 노트 생성
- Generate: Digest/입력 노트에서 `account_id`를 읽고, 없으면 `socialbuilders` 폴백
- Prompt/채널 생성: `get_effective_prompt(account_id=...)`, `config.get_account(account_id)` 경로로 계정별 톤/채널 설정 반영

## 7) FE 마무리 체크리스트

- `/` 대시보드 인라인 Collect 모달: `max_items` 기본값 100 표기
- `/status`에서 collect/generate 공통 진행 로그 재사용
- `/inbox`에서 `writing_status` 필터와 배치 generate 액션 연결
- generate 실행 시 `type` 강제 선택 및 payload 명시 전송

## 8) BE 마무리 체크리스트

- UI 요청을 CLI 실행으로 매핑하는 어댑터 계층 확정
- collect/generate 결과 JSON 키를 문서 계약과 동일하게 반환
- dry-run 경로에서 저장/생성 미수행 보장
- `week_of` 입력을 `YYYY-MM-DD`로 일관 처리

## 9) 최종 DoD (Definition of Done)

- 문서 3종(`io-first`, `input-output-artifacts`, `mvp-wireframes`) 간 파라미터/상태/기본값 충돌 없음
