# Tasks: Pipeline UX

**Input**: Design documents from `/specs/002-pipeline-ux/`
**Prerequisites**: plan.md (required), spec.md (required)

**Organization**: Phase별 — 프롬프트 → 초안 선택 → 다음 명령 제안 → 알림.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: 영역 번호 (1=프롬프트, 2=초안, 3=알림, 4=다음 명령)

---

## Phase 1: 프롬프트 개선 (영역 1)

**Purpose**: 계정·채널·스타일 변수가 롱폼/팩/이미지 프롬프트에 반영되도록 보장

- [ ] T001 [1] config/prompts/ 롱폼·팩·이미지 템플릿에 계정·채널 변수 자리 확정 및 문서화
- [ ] T002 [1] picko/prompt_composer.py에서 스타일 레이어 적용 순서·누락 변수 처리 검토 및 필요 시 수정
- [ ] T003 [1] picko/prompt_loader.py 변수 치환 로깅 또는 검증 추가
- [ ] T004 [1] 단위 테스트: 프롬프트 렌더 시 계정/채널/스타일 변수 포함 여부

**Checkpoint**: 프롬프트 품질 요구사항(SC-001) 충족

---

## Phase 2: 2~3개 초안 생성 및 선택 (영역 2)

**Purpose**: N개 초안 생성, 저장 형식, 선택된 초안만 다운스트림 사용

- [ ] T005 [2] config에 초안 개수 N(1,2,3) 설정 추가 (config.yml 또는 accounts)
- [ ] T006 [2] scripts/generate_content.py에서 롱폼(및/또는 팩) N개 초안 생성·저장 로직 구현
- [ ] T007 [2] “선택된 초안” 표시 방식 정의 및 저장(프론트매터 필드 또는 별도 파일)
- [ ] T008 [2] 이미지 생성/발행 등 다운스트림이 “선택된 초안”만 참조하도록 수정
- [ ] T009 [2] N=1일 때 기존 단일 생성 동작 유지(하위 호환) 검증
- [ ] T010 [2] 단위/통합 테스트: N개 초안 생성, 선택 초안 참조

**Checkpoint**: SC-002, SC-005 충족

---

## Phase 3: 다음 명령 제안 (영역 4)

**Purpose**: daily_collector/generate_content 종료 시 다음 권장 명령 또는 완료 메시지 출력

- [ ] T011 [4] scripts/daily_collector.py 종료 시 “다음 권장 명령: generate_content --date …” 출력
- [ ] T012 [4] scripts/generate_content.py 종료 시 다음 명령 또는 “완료.” 메시지 출력
- [ ] T013 [4] 추가 개입 불필요한 경우(예: 자동 완료) 짧은 완료 메시지 분기
- [ ] T014 [4] 테스트: 종료 시 출력 문구 검증

**Checkpoint**: SC-004, FR-006, FR-007 충족

---

## Phase 4: 알림 + 응답 완료 신호 (영역 3)

**Purpose**: 알림 발송 시점·수단, 응답 완료 신호 구현(선택)

- [ ] T015 [3] config에 알림 시점(수집 직후/생성 전·후), 수단(텔레그램 등), 완료 신호(파일/웹훅) 설정 스키마 추가
- [ ] T016 [3] picko/notify.py (또는 동등 모듈) 알림 발송 + 완료 신호 구현
- [ ] T017 [3] daily_collector.py / generate_content.py에서 알림 훅 호출(설정 없으면 스킵)
- [ ] T018 [3] 알림 미설정 시 파이프라인 정상 동작 및 테스트

**Checkpoint**: SC-003, FR-004, FR-005 충족

---

## Phase 5: Polish & Cross-Cutting

- [ ] T019 [P] CLAUDE.md 또는 USER_GUIDE.md에 초안 개수·알림·다음 명령 제안 설명 반영
- [ ] T020 전체 pytest 및 수동 시나리오로 회귀 없음 확인
- [ ] T021 spec.md 상태를 Draft → Approved로 변경(승인 후)

---

## Dependencies & Execution Order

- **Phase 1**: 선행 없음.
- **Phase 2**: Phase 1과 병렬 가능. 구현 순서는 Phase 1 → 2 권장(품질 후 선택 플로우).
- **Phase 3**: Phase 1·2와 병렬 가능. 독립적 종료 메시지 추가.
- **Phase 4**: Phase 3 이후 또는 병렬. 알림은 선택 기능이므로 마지막에 두어도 됨.
- **Phase 5**: 모든 Phase 완료 후.

## Implementation Strategy

1. **Phase 1 완료** → 프롬프트 변수 반영 검증
2. **Phase 2 완료** → N개 초안·선택 플로우 검증
3. **Phase 3 완료** → 다음 명령 제안 출력 검증
4. **Phase 4 완료** → 알림/완료 신호 검증(설정 시)
5. **Phase 5** → 문서·회귀 테스트 후 스펙 승인
