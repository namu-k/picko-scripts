<!-- Sync Impact Report
  Version change: 0.0.0 → 1.0.0
  Modified principles: None (initial creation)
  Added sections: Core Principles (5), Development Workflow, Quality Standards, Governance
  Removed sections: None
  Templates requiring updates: ✅ plan-template.md (reviewed), ✅ spec-template.md (reviewed), ✅ tasks-template.md (reviewed)
  Follow-up TODOs: None
-->

# Picko-Scripts Constitution

## Core Principles

### I. Config-Driven Architecture

All behavior MUST be driven by YAML configuration (`config/config.yml`, `config/sources.yml`, `config/accounts/*.yml`). New features MUST integrate with the existing `Config` dataclass hierarchy in `picko/config.py`. Environment variable overrides via `api_key_env` fields are the standard pattern for secrets. Hardcoded values are prohibited for anything that could reasonably vary between deployments.

### II. Provider Abstraction

LLM providers MUST implement `BaseLLMClient` (abstract base class in `picko/llm_client.py`) with `generate()` and `generate_stream()` methods. The `LLMClient` wrapper provides caching, retry, and fallback logic that all providers inherit. New providers MUST NOT break existing OpenAI, Anthropic, or Ollama provider functionality. Provider selection is determined by the `provider` field in `LLMConfig`, `SummaryLLMConfig`, or `WriterLLMConfig`.

### III. Obsidian-Centric Storage

All content I/O MUST go through `picko/vault_io.py` using Markdown + YAML frontmatter format. Directory structure follows the Obsidian vault convention defined in `VaultConfig`. Templates are rendered via `picko/templates.py` using Jinja2. No alternative storage backends are permitted without explicit constitution amendment.

### IV. Test Discipline

Unit tests MUST cover new provider classes with mocked API calls. Integration tests with real API keys SHOULD be gated behind environment variable checks (e.g., `OPENROUTER_API_KEY`). Config loading tests MUST verify new provider options parse correctly from YAML. Existing test suite (`pytest`) MUST continue to pass with no regressions. Tests reside in `tests/` and follow `test_*.py` naming.

### V. Backward Compatibility

Changes MUST NOT alter behavior of existing providers (OpenAI, Anthropic, Ollama). Config files without new fields MUST continue to work with defaults. The task-specific client pattern (`get_llm_client()`, `get_summary_client()`, `get_writer_client()`) MUST be preserved. Dependencies MUST NOT be added if existing packages suffice (e.g., `openai` package already supports custom `base_url`).

## Quality Standards

- Type hints MUST be used for all function signatures and class attributes
- Docstrings MUST be provided for public classes and methods (Korean or English, following existing patterns)
- Code MUST follow existing formatting (Black, 120 char line length, isort)
- Logging MUST use `picko.logger.get_logger()` with appropriate levels
- Error messages MUST be clear and actionable, especially for missing API keys

## Development Workflow

- Feature branches follow `feature/<name>` convention
- Changes are validated with `pytest` before merge
- Documentation updates (CLAUDE.md, USER_GUIDE.md) MUST accompany feature changes that affect user-facing behavior
- Config examples in `config/config.yml` MUST be updated for new providers

## Governance

This constitution governs all development on picko-scripts. Amendments require documentation of the change rationale and impact on existing principles. All code changes MUST be verified against these principles during review. Use CLAUDE.md as runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2026-02-16 | **Last Amended**: 2026-02-16
