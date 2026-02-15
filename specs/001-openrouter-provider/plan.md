# Implementation Plan: OpenRouter LLM Provider

**Branch**: `feature/openrouter-provider` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-openrouter-provider/spec.md`

## Summary

Add OpenRouter as a fourth LLM provider to picko-scripts. OpenRouter uses an OpenAI-compatible API, so the implementation reuses the existing `openai` Python package with a custom `base_url`. No new dependencies required.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: openai==2.17.0 (already installed), pyyaml, pytest
**Storage**: N/A (no new storage)
**Testing**: pytest with mocking (unittest.mock)
**Target Platform**: WSL / Windows (cross-platform)
**Project Type**: Single Python package (`picko/`)
**Performance Goals**: Same latency as existing OpenAI provider (network-bound)
**Constraints**: Must not break existing providers. No new pip dependencies.
**Scale/Scope**: 1 new class (~60 lines), 2 modified files, 2 test files, 2 doc files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Config-Driven Architecture | PASS | Uses existing LLMConfig with provider="openrouter", api_key_env default |
| II. Provider Abstraction | PASS | OpenRouterClient extends BaseLLMClient, follows OpenAIClient pattern |
| III. Obsidian-Centric Storage | N/A | No storage changes |
| IV. Test Discipline | PASS | Unit tests with mocks, integration gated behind env var |
| V. Backward Compatibility | PASS | Additive change only - new elif branch in LLMClient.__init__ |

## Project Structure

### Documentation (this feature)

```text
specs/001-openrouter-provider/
├── spec.md              # Feature specification
├── plan.md              # This file
├── tasks.md             # Task breakdown
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (changes to existing files)

```text
picko/
├── llm_client.py        # ADD: OpenRouterClient class + LLMClient branch
└── config.py            # NO CHANGES (LLMConfig already supports api_key_env, base_url)

config/
└── config.yml           # ADD: OpenRouter example comments

tests/
├── test_llm_client.py   # NEW: OpenRouterClient unit tests
└── test_config.py       # ADD: OpenRouter config loading test

CLAUDE.md                # UPDATE: Add OpenRouter to provider table
USER_GUIDE.md            # UPDATE: Add OpenRouter setup instructions
```

**Structure Decision**: Existing single-package structure. All changes fit within current layout.

## Implementation Details

### OpenRouterClient

- Inherits from `BaseLLMClient`
- Nearly identical to `OpenAIClient` but with `base_url="https://openrouter.ai/api/v1"`
- Lazy-loads `openai.OpenAI` client with custom base_url
- `generate()` and `generate_stream()` follow same pattern as OpenAIClient

### LLMClient Integration

- Add `elif config.provider == "openrouter"` branch in `LLMClient.__init__` (line ~226)
- No changes to caching, retry, or high-level methods

### get_summary_client() Update

- The `get_summary_client()` function converts `SummaryLLMConfig` to `LLMConfig`
- Currently only handles `ollama` special case for `base_url`
- Need to handle `openrouter` case: copy `api_key_env` from SummaryLLMConfig
- SummaryLLMConfig currently lacks `api_key_env` field - need to add it

### Config Changes

- `SummaryLLMConfig`: Add `api_key_env: str = ""` field for non-Ollama providers
- `config.yml`: Add OpenRouter example in comments
- No changes to `LLMConfig` or `WriterLLMConfig` (already have all needed fields)

## Complexity Tracking

No violations. This is a minimal additive change following established patterns.
