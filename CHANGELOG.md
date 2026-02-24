# Changelog

All notable changes to Picko will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Image Rendering Pipeline**:
  - `multimedia_io.py`: Multimedia input template parser with YAML frontmatter support
  - `proposal_generator.py`: Content type detection (quote, card, list, data, carousel) and proposal generation
  - `html_renderer.py`: Playwright-based HTML-to-PNG rendering with background overlay support
  - `render_media.py`: CLI for image rendering with status, review, and render commands
  - HTML templates: `quote.html`, `card.html`, `list.html` for social media images
  - Reference document loader with path traversal protection
  - Platform-specific dimension support (configurable)
  - 2-stage interactive review workflow (proposal → render → final)
- **Security**:
  - Path traversal validation in `load_reference()`
  - Template whitelist validation in `ImageRenderer`
  - Comprehensive error handling in CLI (FileNotFoundError, PermissionError, UnicodeDecodeError)
- **Tests**:
  - `test_multimedia_io.py`: Input parser and reference loader tests (6 tests)
  - `test_proposal_generator.py`: Content type detection tests (6 tests)
  - `test_html_renderer.py`: Playwright rendering tests (3 tests)
  - `test_image_templates.py`: HTML template tests (4 tests)
  - `test_render_media_cli.py`: CLI command tests (4 tests)
  - `test_render_media_integration.py`: End-to-end pipeline tests (4 tests)
- **Account Context System**:
  - `account_context.py`: Account identity, weekly slot, and style profile loader
  - `AccountIdentity`: Dataclass for account persona (one_liner, target_audience, pillars, tone_voice, boundaries)
  - `WeeklySlot`: Dataclass for weekly content preset (pillar_distribution, customer_outcome, CTA)
  - `StyleProfile`: Dataclass for writing style characteristics from reference analysis
  - `AccountContextLoader`: Loader class with caching for account context files
  - `get_identity()`, `get_weekly_slot()`, `get_style_for_account()`: Convenience functions
- **Prompt Composer**:
  - `prompt_composer.py`: Multi-layer prompt composition system
  - `PromptComposer`: Class for composing prompts from multiple sources
  - Layers: base_prompt + style + identity + context
  - `get_effective_prompt()`: Convenience function for composed prompts
  - Integration with `generate_content.py` for automatic prompt composition
- **Scoring Integration**:
  - `ContentScorer` now accepts `account_identity` parameter for persona-based relevance scoring
  - Target audience and pillar matching in relevance calculation
  - `score_content()` function supports `account_identity` parameter
- **Tests**:
  - `test_account_context.py`: Comprehensive tests for account context module
  - `test_prompt_composer.py`: Tests for prompt composition system
  - Parser tests for identity and weekly slot markdown files
  - Loader tests with caching verification
  - Real file integration tests (marked as slow)

### Changed
- `scoring.py`: Enhanced relevance calculation with `AccountIdentity` integration
- `generate_content.py`: Weekly slot context injection for content generation

## [0.3.0] - 2026-02-16

### Added
- **Content Pipeline UX Improvements (BCP-001~006)**:
  - `explore_topic.py`: Topic exploration script for thought expansion before longform writing
  - `prompt_loader.py`: External prompt loader with Jinja2 template support
  - Channel selection UI and parsing in generate_content.py
  - Derivative approval stage for packs/images generation
  - Reference-based style system for writing
  - Channel-specific image layout recommendations
- **External Prompts**:
  - `config/prompts/longform/`: Longform article prompts (default, with_exploration, with_reference)
  - `config/prompts/packs/`: Social media pack prompts (twitter, linkedin, newsletter)
  - `config/prompts/image/`: Image prompt templates with channel-specific layouts
  - `config/prompts/exploration/`: Topic exploration prompts
  - `config/prompts/reference/`: Reference analysis prompts
- **Enhanced Testing**:
  - `test_explore_topic.py`: Comprehensive tests for topic exploration
  - `test_prompt_loader.py`: Unit tests for prompt loader module
  - `test_llm_client.py`: Extended tests including `get_writer_client()` FR-003 compliance

### Changed
- `generate_content.py` now uses external prompts from `config/prompts/`
- `llm_client.py` added `get_writer_client()` for task-specific LLM client retrieval
- Account profile configuration enhanced with channel-specific settings
- Documentation updated to reflect new pipeline features

### Fixed
- `explore_topic.py`: Use proper path for explorations directory
- Removed cache and test output files from version control

## [0.2.0] - 2026-02-15

### Added
- **Phase 3 Scripts** (scaffolds):
  - `engagement_sync.py`: Platform metrics sync to publish logs
  - `score_calibrator.py`: Performance vs predicted score analysis
  - `duplicate_checker.py`: Embedding-based duplicate content detection
- **Testing Framework**:
  - Pytest test suite with unit and integration tests
  - Tests for config loading, scoring algorithm, and template rendering
  - Test fixtures and shared conftest.py
- **CI/CD**:
  - GitHub Actions workflow for automated testing
  - Flake8 linting configuration
  - Coverage reporting with pytest-cov
- **Automation**:
  - Windows Task Scheduler setup script (`setup_scheduler.ps1`)
  - Scheduled task runner script (`run_daily_collector.ps1`)
- **Development Tools**:
  - Pre-commit hooks configuration (black, isort, flake8, mypy)
  - Mypy type checking configuration
  - Pytest configuration

### Changed
- Updated documentation with Phase 3 information and CI badge
- Enhanced CLAUDE.md with project structure and workflow details
- Task tracking updated in task.md

### Dependencies
- Added pytest, pytest-cov, flake8, black, isort, mypy, pre-commit to requirements.txt
- Added safety and pip-audit for vulnerability scanning

## [0.1.0] - 2026-02-09

### Added
- **Phase 1 Scripts**:
  - `daily_collector.py`: RSS feed ingestion and content extraction
  - `generate_content.py`: Content generation from digest approval
  - `validate_output.py`: Generated content validation
  - `health_check.py`: System health verification
- **Phase 2 Scripts**:
  - `archive_manager.py`: Old content archival
  - `retry_failed.py`: Retry failed pipeline items
  - `publish_log.py`: Publication logging
- **Core Modules**:
  - `config.py`: Configuration loader with task-specific LLM configs
  - `vault_io.py`: Obsidian Vault markdown I/O
  - `llm_client.py`: Multi-provider LLM client (Ollama, OpenAI, Anthropic)
  - `embedding.py`: Local-first embedding with sentence-transformers
  - `scoring.py`: Content scoring algorithm (novelty, relevance, quality)
  - `templates.py`: Jinja2 template rendering
  - `logger.py`: Loguru-based logging

### Features
- Task-specific LLM architecture (local for NLP, cloud for writing)
- Pre-writing approval workflow (writing_status field)
- Multi-format content generation (longform, social packs, image prompts)
- Obsidian Vault integration with YAML frontmatter

### Documentation
- README.md with quick start guide
- USER_GUIDE.md with detailed usage instructions
- CLAUDE.md for developer guidance
- implementation_plan.md with technical design

[0.3.0]: https://github.com/namu-k/picko-scripts/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/namu-k/picko-scripts/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/namu-k/picko-scripts/releases/tag/v0.1.0
