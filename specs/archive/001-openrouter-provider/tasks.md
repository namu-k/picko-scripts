# Tasks: OpenRouter LLM Provider

**Input**: Design documents from `/specs/001-openrouter-provider/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: Unit tests included (provider integration requires test coverage per constitution).

**Organization**: Tasks grouped by user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Foundation changes that all user stories depend on

- [x] T001 Add `api_key_env` field to `SummaryLLMConfig` in `picko/config.py`
- [x] T002 Add `OpenRouterClient` class to `picko/llm_client.py` (BaseLLMClient subclass, OpenAI-compatible with base_url)
- [x] T003 Add `provider == "openrouter"` branch in `LLMClient.__init__` in `picko/llm_client.py`
- [x] T004 Update `get_summary_client()` to handle openrouter provider in `picko/llm_client.py`

**Checkpoint**: OpenRouterClient exists and LLMClient can instantiate it

---

## Phase 2: User Story 1 - Configure OpenRouter as Writer LLM (Priority: P1)

**Goal**: writer_llm with provider="openrouter" works for content generation

**Independent Test**: Set writer_llm.provider to "openrouter" in config, verify LLMClient initializes and generate() calls OpenRouter API

- [x] T005 [US1] Add OpenRouter example config block (commented) to `config/config.yml`
- [x] T006 [US1] Write unit test for OpenRouterClient.generate() with mocked OpenAI client in `tests/test_llm_client.py`
- [x] T007 [US1] Write unit test for LLMClient init with provider="openrouter" in `tests/test_llm_client.py`
- [x] T008 [US1] Write config loading test for openrouter provider in `tests/test_config.py`

**Checkpoint**: Writer LLM with openrouter provider initializes and passes mocked tests

---

## Phase 3: User Story 2 - Use OpenRouter for Summary/Tagging (Priority: P2)

**Goal**: summary_llm with provider="openrouter" works for daily_collector

**Independent Test**: Set summary_llm.provider to "openrouter" in config, verify get_summary_client() returns working client

- [x] T009 [US2] Write unit test for get_summary_client() with openrouter provider in `tests/test_llm_client.py`

**Checkpoint**: Summary LLM with openrouter provider works through get_summary_client()

---

## Phase 4: User Story 3 - Stream Generation Support (Priority: P2)

**Goal**: OpenRouterClient.generate_stream() returns streaming chunks

**Independent Test**: Call generate_stream() on OpenRouterClient with mocked streaming response

- [x] T010 [US3] Write unit test for OpenRouterClient.generate_stream() with mocked streaming in `tests/test_llm_client.py`

**Checkpoint**: Streaming generation passes mocked test

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and validation

- [x] T011 [P] Update CLAUDE.md with OpenRouter provider in LLM Architecture table
- [x] T012 [P] Update docs/user-guide.md with OpenRouter setup instructions
- [x] T013 Run full pytest suite to verify no regressions
- [x] T014 Update spec.md status from "Draft" to "Approved"

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (US1)**: Depends on Phase 1 completion
- **Phase 3 (US2)**: Depends on Phase 1 completion (can parallel with Phase 2)
- **Phase 4 (US3)**: Depends on Phase 1 completion (can parallel with Phase 2, 3)
- **Phase 5 (Polish)**: Depends on all previous phases

### Parallel Opportunities

- T006, T007, T008 can run in parallel (different test classes/files)
- T011, T012 can run in parallel (different documentation files)
- Phases 2, 3, 4 can run in parallel after Phase 1

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Writer LLM with OpenRouter (T005-T008)
3. **STOP and VALIDATE**: Run pytest, verify OpenRouterClient works
4. Continue with remaining phases

### Incremental Delivery

1. Setup → OpenRouterClient ready
2. US1 → Writer LLM working → Test
3. US2 → Summary LLM working → Test
4. US3 → Streaming working → Test
5. Polish → Docs updated, all tests pass
