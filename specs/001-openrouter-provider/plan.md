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
│                        # UPDATE: get_summary_client() to pass api_key_env
└── config.py            # MODIFIED: add api_key_env: str = "" to SummaryLLMConfig

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

- Add `elif config.provider == "openrouter"` branch in `LLMClient.__init__`
- No changes to caching, retry, or high-level methods

### get_summary_client() Update

- The `get_summary_client()` function converts `SummaryLLMConfig` to `LLMConfig`
- Currently only handles `ollama` special case for `base_url`
- Updated to pass `api_key_env` for all non-Ollama providers (including openrouter)
- `SummaryLLMConfig` required a new `api_key_env: str = ""` field to support this

### Config Changes

- `picko/config.py`: `SummaryLLMConfig` gains `api_key_env: str = ""` (empty = use provider default)
- `picko/llm_client.py`: `get_summary_client()` passes `api_key_env` to `LLMConfig`
- `config/config.yml`: OpenRouter usage example added as comments
- `LLMConfig` and `WriterLLMConfig` unchanged (already have all needed fields)

## Traceability Matrix

| FR | Requirement | Implementing File(s) | Task(s) | Validating Test(s) |
|----|-------------|---------------------|---------|-------------------|
| FR-001 | OpenAI 호환 API, base_url 사용 | `picko/llm_client.py` (OpenRouterClient) | T002 | `TestOpenRouterClient::test_client_lazy_init` |
| FR-002 | provider/model 형식 모델 ID 지원 | `picko/llm_client.py` (OpenRouterClient.generate) | T002 | `TestOpenRouterClient::test_generate` |
| FR-003 | api_key_env 환경변수에서 API 키 로드 | `picko/config.py` (LLMConfig.api_key), `picko/llm_client.py` | T001, T002 | `TestOpenRouterConfig::test_llm_config_openrouter`, `TestOpenRouterClient::test_client_lazy_init` |
| FR-004 | generate() + generate_stream() 구현 | `picko/llm_client.py` (OpenRouterClient) | T002 | `TestOpenRouterClient::test_generate`, `test_generate_no_system_prompt`, `test_generate_stream` |
| FR-005 | LLMClient 캐싱·재시도 로직 활용 | `picko/llm_client.py` (LLMClient.__init__) | T003 | `TestLLMClientOpenRouter::test_llm_client_generate_openrouter` |
| FR-006 | config.yml에서 provider="openrouter" 설정 | `picko/config.py`, `config/config.yml` | T001, T004, T005 | `TestOpenRouterConfig::test_summary_llm_config_api_key_env`, `TestLoadConfig::test_load_config_openrouter_writer` |
| FR-007 | 기존 프로바이더 동작 불변 | `picko/llm_client.py` (LLMClient.__init__ elif 추가) | T003 | 기존 전체 테스트 스위트 (57개 통과, regression 없음) |

## Complexity Tracking

No violations. This is a minimal additive change following established patterns.
