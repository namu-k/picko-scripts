# Implementation Plan: Context-Driven Content Quality & Agent Interaction Protocol

**Branch**: `001-context-interaction` | **Date**: 2026-02-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-context-interaction/spec.md`

## Summary

This feature enhances the Picko content pipeline in two areas:

1. **Quality (프롬프트 개선)**: Inject account, channel, style, and weekly context variables into all prompt types (longform, packs, image) as structured template variables, ensuring brand consistency.

2. **Interaction (에이전트-운영자 소통)**: Implement a robust agent-operator communication protocol with primary and fallback methods at every interaction point: draft selection, notifications, and next command suggestions.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: Jinja2 (existing), PyYAML (existing), argparse (existing)
**Storage**: File-based (Obsidian vault markdown + YAML frontmatter)
**Testing**: pytest with mocked LLM calls
**Target Platform**: Linux/Windows/macOS CLI
**Project Type**: Single project (existing picko package structure)
**Performance Goals**: Draft generation latency <30s per draft; notification delivery <5s
**Constraints**: Must work in non-interactive environments (CI/CD, scheduled tasks)
**Scale/Scope**: Single operator per run; up to 5 drafts per content item

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Config-Driven Architecture | ✅ PASS | New interaction settings will be configurable via `config/config.yml` under new `interaction` section |
| II. Provider Abstraction | ✅ PASS | No new LLM providers; uses existing `LLMClient` for draft generation |
| III. Obsidian-Centric Storage | ✅ PASS | Draft storage uses `vault_io.py`; notification records stored as markdown files |
| IV. Test Discipline | ✅ PASS | New modules require unit tests with mocked API calls; integration tests gated by env vars |
| V. Backward Compatibility | ✅ PASS | New CLI flags are optional; existing `generate_content.py` behavior unchanged when flags not used |

**Quality Standards Compliance**:
- Type hints: Required for all new functions
- Docstrings: Required for public classes/methods (Korean or English)
- Formatting: Black (120 char), isort
- Logging: Use `picko.logger.get_logger()`
- Error messages: Clear and actionable

## Scope Justification

**사용자 요청에 따른 범위 구성**: 이 기능은 사용자가 명시적으로 4개 영역을 하나의 feature로 요청함:
1. 프롬프트·계정·채널·스타일 변수
2. 초안 선택 소통
3. 알림·완료 신호
4. 다음 명령 제안

**단일 브랜치 유지 이유**:
- 4개 영역 모두 `generate_content.py`를 수정하지만, **순차적 Phase 구현**으로 충돌 최소화
- 영역 간 의존성: (1)의 변수 주입이 (2)의 초안 생성에 영향
- 알림(3)은 외부 의존성 없이 console + log만 사용하므로 분리 필요 없음
- 사용자 요청: "4개 영역"을 명시적으로 지정

**대안 기각**: 3개 PR로 분리하면 관리 오버헤드 증가, 요청 범위와 불일치.

---

## Design Decisions

이 섹션은 구현 전에 반드시 확정되어야 할 핵심 설계 결정을 명시합니다.

### D1. 초안 저장 형식 (Draft Storage Format)

**결정**: N개 초안 = N개 별도 파일 (N-파일 방식)

```
Content/Longform/2026-02-17/
├── article-001.md              # 선택된 초안 (N=1일 때와 동일한 이름)
└── .drafts/
    └── article-001/
        ├── draft-1.md          # 초안 1
        ├── draft-2.md          # 초안 2
        └── draft-3.md          # 초안 3
```

**이유**:
- Vault에서 각 초안을 독립적으로 조회/비교 가능
- 파일 삭제로 미선택 초안 정리 용이
- 이미지/발행 스크립트는 `.drafts/` 폴더를 무시하면 됨

**대안 기각**: 1파일 N블록 방식은 YAML frontmatter에 배열을 저장해야 하고, vault 검색/비교가 어려움.

### D2. 선택된 초안 표시 (Selected Draft Expression)

**결정**: 최종 파일명 규칙 유지 + `.drafts/` 폴더 존재로 선택 완료 여부 판단

```yaml
# 선택된 초안 파일 (기존과 동일한 위치/이름)
---
title: "Article Title"
draft_selected: true
draft_id: "draft-2"
draft_selected_at: "2026-02-17T15:00:00"
---
```

**이유**:
- 기존 downstream 스크립트가 파일 경로를 변경할 필요 없음
- `draft_selected` 프론트매터 필드로 선택 상태 추적
- `.drafts/` 폴더 삭제로 미선택 초안 정리

**대안 기각**: `*_selected.md` 파일명 접미사는 모든 downstream 스크립트의 파일 탐지 로직 변경 필요.

### D3. Config 스키마 (Configuration Schema)

**확정된 config.yml 구조**:

```yaml
interaction:
  draft:
    max_count: 5                    # FR-007: 최대 초안 수 (1-5)
    deadline_hours: 24              # FR-010: 마감까지 시간
    deadline_time: "12:00"          # 구체적 마감 시각 (다음 날 점심)
    reminder_interval_hours: 2      # FR-010: 리마인더 간격
    auto_select_on_deadline: true   # 마감 시 자동 선택
    scoring_algorithm: "default"    # 스코어링 알고리즘 (현재: 기존 scoring.py)

  notification:
    primary: "console"              # console | log | both
    fallback: "log"                 # log (fallback만)
    include_details: true           # 에러, 출력 경로 포함
    retry_count: 3                  # 알림 실패 시 재시도 횟수
    retry_delay_seconds: 5          # 재시도 간격

  suggestion:
    enabled: true                   # 제안 기능 활성화
    primary: "terminal"             # terminal | file | both
    fallback_file: "logs/suggestions.txt"
    context_aware: true             # 워크플로우 상태 기반 제안
```

**위치**: `config/config.yml` 최상위 레벨에 `interaction:` 섹션 추가

### D4. N=1일 때 하위 호환성 (Backward Compatibility for N=1)

**결정**: `--drafts 1` 또는 플래그 미지정 시 기존과 완전히 동일한 동작

| 항목 | N=1 (기본) | N>1 |
|------|------------|-----|
| 출력 파일명 | `article-001.md` | `article-001.md` (선택된 것만) |
| `.drafts/` 폴더 | 생성 안 함 | 생성 (미선택 초안 보관) |
| 프론트매터 | 기존과 동일 | `draft_*` 필드 추가 |
| downstream 영향 | 없음 | `.drafts/` 무시 필요 |

**validate_output.py 수정**: `.drafts/` 폴더 내 파일은 검증에서 제외

### D5. 비용 영향 (Cost Impact)

**명시적 비용 증가**:

| 초안 수 | API 호출 | 예상 비용 (GPT-4o-mini 기준) |
|---------|----------|------------------------------|
| 1 (기본) | 1× | 기존과 동일 |
| 2 | 2× | 약 2배 |
| 3 | 3× | 약 3배 |
| 5 (최대) | 5× | 약 5배 |

**운영자 가이드**:
- 중요 콘텐츠에만 N>1 사용 권장
- 일반 콘텐츠는 N=1 (기본값) 유지
- CI/CD 환경에서는 `--drafts 1` 명시 권장

---

## Architecture Overview

### Two-Category Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY (프롬프트 개선)                        │
│  Context Variable Injection: Account, Channel, Style, Weekly    │
├─────────────────────────────────────────────────────────────────┤
│                  INTERACTION (에이전트-운영자 소통)                 │
│  Primary Method          │  Fallback Method                      │
│  ────────────────────────┼────────────────────────────────────── │
│  Interactive CLI prompt  │  CLI flag / File-based selection      │
│  Console notification    │  Log file entry                       │
│  Terminal display        │  Text file in logs/                   │
└─────────────────────────────────────────────────────────────────┘
```

### Four Functional Areas

| Area | Module | Primary Method | Fallback Method |
|------|--------|----------------|-----------------|
| (1) Prompts/Account/Channel/Style | `picko/context_variables.py` | Config-driven injection | Default fallback values |
| (2) Draft Selection | `picko/interaction/draft_selector.py` | Interactive CLI prompt | `--select-draft N` CLI flag |
| (3) Notifications | `picko/interaction/notifier.py` | Console output + log | Persistent file record |
| (4) Next Commands | `picko/interaction/command_suggester.py` | Terminal display | `.next_commands.txt` file |

## Project Structure

### Documentation (this feature)

```text
specs/001-context-interaction/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Usage guide
├── contracts/           # Phase 1: CLI contracts
│   └── cli-interface.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2: Implementation tasks (via /speckit.tasks)
```

### Source Code (existing structure + new modules)

```text
picko/
├── context_variables.py      # NEW: Context variable set builder
├── prompt_composer.py        # MODIFY: Add structured variable injection
├── prompt_loader.py          # MODIFY: Ensure consistent variable availability
├── account_context.py        # MODIFY: Extend identity fields to variables
└── interaction/              # NEW: Interaction module directory
    ├── __init__.py
    ├── base.py               # InteractionPoint, InteractionResult base classes
    ├── draft_selector.py     # Draft selection workflow
    ├── notifier.py           # Notification system
    ├── command_suggester.py  # Next command suggestions
    └── config.py             # InteractionConfig dataclass

scripts/
├── generate_content.py       # MODIFY: Add --drafts flag, integrate interaction
└── interaction_cli.py        # NEW: Standalone interaction utility (optional)

config/
├── config.yml                # MODIFY: Add interaction section
└── prompts/                  # MODIFY: Update templates with new variable names
    ├── longform/
    ├── packs/
    └── image/

tests/
├── test_context_variables.py # NEW: Unit tests for context variable injection
├── test_interaction/
│   ├── test_draft_selector.py
│   ├── test_notifier.py
│   └── test_command_suggester.py
└── test_integration_context.py
```

**Structure Decision**: Extend existing `picko/` package with new `interaction/` submodule. This follows Constitution Principle I (Config-Driven) by keeping all behavior in the core package, and Principle III (Obsidian-Centric) by using existing vault patterns.

## Interaction Point Design

### Communication Methods Matrix

| Interaction Point | Primary Method | Fallback Method | Config Key |
|-------------------|----------------|-----------------|------------|
| Draft Selection (interactive) | `input()` prompt | `--select-draft N` CLI flag | `interaction.draft.primary` |
| Draft Selection (deadline) | Reminder at interval | Auto-select on deadline | `integration.draft.reminder_interval` |
| Draft Presentation | Console table | Markdown file in vault | `interaction.draft.display` |
| Completion Notification | Console summary | Log file entry | `interaction.notification.primary` |
| Error Alert | Console error block | Log file + status file | `interaction.notification.error` |
| Next Command Display | Terminal output | `.next_commands.txt` | `interaction.suggestion.primary` |

### Default Configuration Schema

```yaml
# config/config.yml addition
interaction:
  draft:
    max_count: 5                    # Maximum drafts (FR-007)
    deadline_hours: 24              # Default: next-day lunchtime (~24h)
    deadline_time: "12:00"          # Specific time for deadline
    reminder_interval_hours: 2      # Reminder frequency (FR-010)
    auto_select_on_deadline: true   # Auto-select if no response
    scoring_algorithm: "default"    # Future: context-aware scoring

  notification:
    primary: "console"              # console | log | both
    fallback: "log"                 # log | file
    include_details: true           # Include errors, output paths

  suggestion:
    primary: "terminal"             # terminal | file | both
    fallback_file: "logs/suggestions.txt"
    context_aware: true             # Base on workflow state
```

## Complexity Tracking

No constitution violations. All changes follow existing patterns:
- Config-driven: New `interaction` section in config.yml
- Provider abstraction: Uses existing LLMClient
- Obsidian-centric: Drafts stored via vault_io.py
- Testable: All new modules have unit test counterparts

---

## Pre-Implementation Requirements

### Audit Task: 영역 1 착수 전 필수 조사

영역 1 (프롬프트 변수 주입) 구현 전, 현재 `prompt_composer.py`와 `prompt_loader.py`에서 **실제로 누락된 변수 목록**을 조사해야 합니다.

**Audit 체크리스트**:
- [ ] `PromptComposer.apply_identity()`에서 설정하는 변수 목록 확인
- [ ] `PromptComposer.apply_style()`에서 style characteristics를 변수로 노출하는지 확인
- [ ] `PromptComposer.apply_context()`에서 pillar_distribution 변수화 여부 확인
- [ ] `PromptLoader.get_pack_prompt()`에 전달되는 변수 목록 확인
- [ ] 기존 프롬프트 템플릿(`config/prompts/*.md`)에서 사용하는 변수 목록 수집
- [ ] 새 변수 명명 규칙(`account.*`, `style.*`, `channel.*`, `weekly.*`)과 기존 변수 충돌 여부 확인

**산출물**: `research.md`에 "누락 변수 목록" 섹션 추가

### Test Fixture Design

초안 선택 플로우 테스트를 위한 픽스처 설계:

```python
# tests/conftest.py

@pytest.fixture
def pending_draft_selection(tmp_path):
    """대기 중인 초안 선택 상태를 시뮬레이션하는 파일 생성."""
    draft_dir = tmp_path / "Content" / "Longform" / "2026-02-17" / ".drafts" / "article-001"
    draft_dir.mkdir(parents=True)

    # 3개 초안 생성
    for i in range(1, 4):
        draft_file = draft_dir / f"draft-{i}.md"
        draft_file.write_text(f"---\ntitle: Draft {i}\nscore: {0.9 - i*0.05}\n---\nContent {i}")

    # 선택 대기 상태의 메타데이터
    meta_file = draft_dir / "selection.yaml"
    meta_file.write_text(yaml.dump({
        "status": "pending",
        "deadline": "2026-02-18T12:00:00",
        "created_at": "2026-02-17T10:00:00",
    }))

    return draft_dir

@pytest.fixture
def selected_draft(tmp_path):
    """선택 완료된 초안 상태를 시뮬레이션."""
    output_file = tmp_path / "Content" / "Longform" / "2026-02-17" / "article-001.md"
    output_file.parent.mkdir(parents=True)
    output_file.write_text("""---
title: Selected Article
draft_selected: true
draft_id: draft-2
draft_selected_at: 2026-02-17T15:00:00
---
Selected content here...
""")
    return output_file
```

**알림 테스트 전략**:
- Console 알림: `capsys` fixture로 stdout 캡처
- Log 알림: `tmp_path`에 로그 파일 생성 후 내용 검증
- Mock: 외부 API 없음 (console + log만 사용)

---

## Phase Summary

| Phase | Output | Status |
|-------|--------|--------|
| Phase 0 | research.md | ✅ Complete |
| Phase 1 | data-model.md, contracts/cli-interface.md, quickstart.md | ✅ Complete |
| Phase 2 | tasks.md | Not started (via /speckit.tasks) |

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| LLM 비용 증가 (N배 API 호출) | 운영 비용 | 기본값 N=1 유지, 중요 콘텐츠만 N>1 권장 | 문서화 완료 |
| 초안 선택 없이 방치 | 파이프라인 정체 | `auto_select_on_deadline` 설정으로 마감 시 자동 선택 | 설계 완료 |
| 알림 실패 | 알림 누락 | 3회 재시도 + fallback file 기록 | 설계 완료 |
| generate_content.py 충돌 | 구현 지연 | Phase별 순차 구현, 각 Phase 완료 후 commit | 프로세스 |
| 하위 호환성 깨짐 | downstream 오류 | N=1일 때 기존과 동일한 파일명/구조 보장 | 설계 완료 |

---

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Implementation Plan | `specs/001-context-interaction/plan.md` | This document |
| Research | `specs/001-context-interaction/research.md` | Technical research and decisions |
| Data Model | `specs/001-context-interaction/data-model.md` | Entity definitions for 4 modules |
| CLI Contract | `specs/001-context-interaction/contracts/cli-interface.md` | CLI flags and output formats |
| Quickstart | `specs/001-context-interaction/quickstart.md` | Usage guide |

---

## Next Steps

Run `/speckit.tasks` to generate implementation tasks based on this plan.
