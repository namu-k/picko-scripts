# Collectors.md ↔ Collector_automation.md Doc Sync (Claude-Centric)

## TL;DR
> **Summary**: `Collectors.md`를 로컬-first + Claude Code 중심 워크플로우로 재작성해 `Collector_automation.md`와 충돌을 제거한다.
> **Deliverables**: `Collectors.md` 업데이트(Claude-centric), 경로/모드(로컬 vs Vault) 명시, Make/Zapier 역할을 이메일->파일로 제한, 검증 가능한 acceptance criteria 추가.
> **Effort**: Quick
> **Parallel**: NO
> **Critical Path**: T1 (conflict map) -> T2 (rewrite) -> T3 (link + acceptance) -> T4 (doc QA)

## Context
### Target Files
- Update: `C:\picko-scripts\Collectors.md`
- Must align with:
  - `C:\picko-scripts\mock_vault\config\Folders_to_operate_social-media_copied_from_Vault\0. 프레임워크\Collector_automation.md`
  - `C:\picko-scripts\mock_vault\config\Folders_to_operate_social-media_copied_from_Vault\0. 프레임워크\Perplexity_email_setup.md`

### Current Conflict
- `Collectors.md`는 클라우드 SaaS 중심(Feedly/Make/Claude API/Placid/Bannerbear/Notion)으로 “The Trio”를 기본 흐름으로 제시.
- `Collector_automation.md`는 로컬-first(파일로 떨어뜨리기 + Claude Code가 폴더 처리) 구조가 기본.

### Canonical Code References (repo truth)
- Lightweight RSS-to-md collector: `C:\picko-scripts\scripts\simple_rss_collector.py`
- Full pipeline collector: `C:\picko-scripts\scripts\daily_collector.py`
- Downstream generation: `C:\picko-scripts\scripts\generate_content.py`

## Work Objectives
### Core Objective
- Collectors.md에서 “기본 운영 경로”를 로컬-first + Claude Code 중심으로 통일하고, 충돌하는 SaaS 중심 흐름은 옵션/부가로 격리한다.

### Definition of Done
- `Collectors.md`에서 아래가 모두 만족:
  - Claude Code(CLI)가 기본 처리자로 명시됨
  - Make/Zapier는 Perplexity 이메일을 파일로 저장하는 용도로만 명시됨
  - Notion/Placid/Bannerbear는 “옵션(비핵심)”으로만 남거나 제거됨
  - “정본 폴더 구조”가 명시됨(로컬 모드: `C:\MyAIWorker\...` + Vault 모드: `Inbox/Inputs/...`)
  - 최소 3개 acceptance criteria가 문서에 포함(파일 생성/경로 기반, 사람 확인 불필요)
  - 참조 링크가 실제 존재 파일로 연결됨(Collector_automation, Perplexity_email_setup, simple_rss_collector)

## Execution Strategy
- 단일 변경으로 `Collectors.md`를 전면 교체(부분 patch보다 충돌 위험이 낮음).
- 서식은 markdown 표준으로 정리(특수 bullet `•` 대신 `-` 권장).

## TODOs

- [x] 1. Collectors.md conflict map 작성

  **What to do**:
  - `Collectors.md`에서 아래 요소를 “핵심 흐름/옵션”으로 재분류한다:
    - RSS 수집, Perplexity, Make/Zapier, Claude(웹/CLI/API), 디자인 렌더링, 저장(Notion)
  - “충돌 포인트”를 문서 상단에 짧게 정리한다(왜 로컬-first로 바꾸는지).

  **Acceptance Criteria**:
  - [ ] 충돌 요소 3개 이상이 명시적으로 정리됨(예: Make의 역할, Notion 저장, SaaS 렌더링).

  **QA Scenarios**:
  ```
  Scenario: Conflict points are explicit
    Tool: Read
    Steps: Open Collectors.md and list workflows described
    Expected: A short list of conflicting workflows exists
  ```

- [x] 2. Collectors.md를 Claude-centric 로컬-first 워크플로우로 전면 재작성

  **What to do**:
  - `.sisyphus/drafts/collectors-claude-centric.md`의 “Proposed Collectors.md Replacement”를 기반으로 `Collectors.md` 전체를 교체한다.
  - 내용 구조는 최소 다음을 포함:
    - 목적/원칙(파일로 떨어뜨리기)
    - 정본 폴더 구조(로컬 vs Vault)
    - RSS 수집(스크립트/명령)
    - Perplexity 이메일->파일(링크)
    - Claude Code 처리(입출력 파일 고정)
    - 자동화/동기화 주의사항
    - 옵션(디자인/DB 저장)

  **Must NOT do**:
  - Make 트리거(RSS)->Claude API->Notion을 기본 경로로 남기지 않는다.

  **References**:
  - Draft: `.sisyphus/drafts/collectors-claude-centric.md`
  - Alignment source: `mock_vault/.../Collector_automation.md`

  **Acceptance Criteria**:
  - [ ] Collectors.md에서 “Claude Code(CLI)”가 기본 처리자로 1회 이상 등장
  - [ ] Make/Zapier가 이메일->파일 용도로만 설명됨

  **QA Scenarios**:
  ```
  Scenario: Core flow is local-first
    Tool: Read
    Steps: Scan headings/sections
    Expected: Collection -> local files -> Claude Code processing is the primary narrative
  ```

- [x] 3. 코드/문서 링크 및 실행 명령 검증(문서 QA)

  **What to do**:
  - Collectors.md에 아래 참조를 포함(텍스트/경로 정확히):
    - `scripts/simple_rss_collector.py`
    - `mock_vault/.../Collector_automation.md`
    - `mock_vault/.../Perplexity_email_setup.md`
  - RSS 수집 명령은 `--output`을 포함해 Vault 밖으로 빠지는 실수를 방지한다.

  **Acceptance Criteria**:
  - [ ] 문서에 포함된 파일 경로 3개 모두 실제로 존재
  - [ ] RSS 예시 커맨드가 `--output`을 포함

  **QA Scenarios**:
  ```
  Scenario: References resolve
    Tool: Grep/Read
    Steps: Search for the three file paths in Collectors.md
    Expected: Each path appears exactly once in the "References" section
  ```

- [x] 4. Acceptance Criteria 섹션 추가 및 실행가능성 점검

  **What to do**:
  - Collectors.md 하단에 acceptance criteria 3개를 추가한다:
    1) RSS `.md` 파일 생성
    2) Perplexity 이메일->파일 드롭(패턴)
    3) Claude 처리 결과 파일 생성
  - 사람의 눈으로 확인 요구 없이 “파일 생성/경로/패턴”으로 정의한다.

  **Acceptance Criteria**:
  - [ ] “자동 검증 기준” 섹션이 존재
  - [ ] 각 항목이 경로와 파일명 패턴을 포함

  **QA Scenarios**:
  ```
  Scenario: Acceptance criteria are machine-checkable
    Tool: Read
    Steps: Review criteria formatting
    Expected: Each item includes an executable-style instruction and an expected file/path outcome
  ```

## Final Verification Wave
- [x] F1. Scope fidelity: only docs updated (no code changes)
- [x] F2. Conflict check: no remaining "The Trio" core flow

## Commit Strategy
- Commit 1: `docs: align Collectors with local-first Claude Code workflow`
- Files: `Collectors.md`
