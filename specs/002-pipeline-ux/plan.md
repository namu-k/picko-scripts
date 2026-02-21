# Implementation Plan: Pipeline UX

**Branch**: `002-pipeline-ux` | **Date**: 2026-02-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-pipeline-ux/spec.md`

## Summary

파이프라인 사용성 개선: (1) 롱폼/팩/이미지 프롬프트에 계정·채널·스타일 변수 반영, (2) 2~3개 초안 생성 후 선택된 초안만 다운스트림 사용, (3) 알림(텔레그램 등) 및 응답 완료 신호, (4) 종료 시 다음 명령 제안 출력.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: 기존(picko, pyyaml, jinja2). 알림 시 텔레그램 봇 사용 시 선택적 의존성(requests 또는 python-telegram-bot).
**Storage**: Obsidian Vault (기존). 초안 N개 저장 시 파일/프론트매터 확장.
**Testing**: pytest (단위·통합), 수동 시나리오 검증.
**Target Platform**: WSL / Windows (cross-platform)
**Constraints**: 기존 daily_collector/generate_content 동작 하위 호환 유지.

## Constitution Check

*GATE: Must pass before implementation.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Config-Driven Architecture | PASS | 프롬프트·초안 개수·알림 설정은 config/sources/accounts 기반 |
| II. Provider Abstraction | N/A | LLM 변경 없음 |
| III. Obsidian-Centric Storage | PASS | 초안·선택 상태는 vault 경로/프론트매터로 표현 |
| IV. Test Discipline | PASS | 새 동작에 대한 테스트 추가, 기존 스위트 유지 |
| V. Backward Compatibility | PASS | N=1, 알림 미설정 시 기존과 동일 동작 |

## Project Structure

### Documentation (this feature)

```text
specs/002-pipeline-ux/
├── spec.md              # 기능 명세 (4개 영역)
├── plan.md              # 본 문서
├── tasks.md             # Phase별 태스크
└── checklists/
    └── requirements.md  # 품질 체크리스트
```

### Source Code (수정·추가 대상)

```text
config/
├── config.yml           # 초안 개수, 알림 시점/수단, 완료 신호 옵션
├── prompts/            # 롱폼/팩/이미지 프롬프트 (변수 치환 강화)
└── accounts/            # 기존 계정·스타일 프로필 활용

picko/
├── prompt_loader.py     # 변수 주입 검증/로깅
├── prompt_composer.py   # 계정·채널·스타일 레이어 적용 확인
├── account_context.py   # 기존 유지, 필요 시 확장
└── (신규) notify.py     # 알림 발송 + 완료 신호 (선택적)

scripts/
├── daily_collector.py   # 종료 시 다음 명령 제안, 알림 훅
└── generate_content.py # N개 초안 생성, 선택된 초안 참조, 종료 시 다음 명령 제안

tests/
└── test_*.py            # 프롬프트 변수, 초안 개수, 알림 스킵, 다음 명령 출력 검증
```

## Implementation Details

### 영역 1: 프롬프트 개선

- **수정 대상**: `config/prompts/` 템플릿, `picko/prompt_loader.py`, `picko/prompt_composer.py`
- **내용**: 계정 정체성(one_liner, target_audience, tone_voice), 채널별 형식, 스타일 프로필이 Jinja2 변수로 주입되도록 보장. 이미 `account_context`, `prompt_composer`가 있으므로 누락 변수 처리·기본값 정리.

### 영역 2: 2~3개 초안 선택

- **수정 대상**: `scripts/generate_content.py`, vault 출력 경로/프론트매터
- **내용**: 설정 `draft_count: 2|3` (또는 유사 키)로 N개 생성. 동일 입력에 대해 N개 파일 또는 한 파일 내 N개 블록 저장. “선택된 초안”은 프론트매터 `selected_draft: 1` 또는 별도 파일(예: `*_selected.md`)로 표현. 이미지 생성/발행 스크립트는 선택된 초안만 읽도록 수정.

### 영역 3: 알림 + 응답 완료

- **수정 대상**: `scripts/daily_collector.py`, `scripts/generate_content.py`
- **신규(선택)**: `picko/notify.py` — 발송 시점(수집 직후/생성 전·후), 수단(텔레그램 등), 완료 신호(파일 터치/웹훅) 구현.
- **의존성**: 텔레그램 봇 사용 시 `requests` 또는 `python-telegram-bot` 추가 가능. config에 알림 비활성화 시 스킵.

### 영역 4: 다음 명령 제안

- **수정 대상**: `scripts/daily_collector.py`, `scripts/generate_content.py`
- **내용**: 종료 시 실행한 날짜/옵션을 반영해 “다음 권장 명령: python -m scripts.generate_content --date YYYY-MM-DD” 등 한 줄 출력. 추가 개입 불필요 시 “완료.” 등 짧은 메시지.

## Traceability Matrix

| FR | Requirement | Implementing File(s) | Validating Test(s) |
|----|-------------|---------------------|--------------------|
| FR-001 | 프롬프트 변수 반영 | prompt_loader, prompt_composer, config/prompts | 프롬프트 렌더 테스트 |
| FR-002 | N개 초안 생성·저장 | generate_content.py, config | 초안 N개 생성 테스트 |
| FR-003 | 선택된 초안만 다운스트림 | generate_content, 이미지/발행 스크립트 | 선택 초안 참조 테스트 |
| FR-004 | 알림 시점·수단 | notify.py, daily_collector, generate_content | 알림 스킵/발송 테스트 |
| FR-005 | 응답 완료 신호 | notify.py, config | 완료 신호 테스트 |
| FR-006 | 다음 명령 제안 | daily_collector, generate_content | 종료 출력 검증 |
| FR-007 | 완료 메시지 | daily_collector, generate_content | 출력 문구 검증 |

## Dependencies & Execution Order

- **Phase 1 (프롬프트)**: 독립. 먼저 완료 시 품질 기준 확보.
- **Phase 2 (초안 선택)**: Phase 1과 병렬 가능. generate_content 변경이 핵심.
- **Phase 3 (다음 명령 제안)**: daily_collector/generate_content 종료 로직만 추가. Phase 1·2와 병렬 가능.
- **Phase 4 (알림)**: Phase 3 이후 또는 병렬. notify 모듈 추가 시 의존성 도입.
