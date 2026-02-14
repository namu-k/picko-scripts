# Changelog

All notable changes to Picko will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/your-username/picko-scripts/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-username/picko-scripts/releases/tag/v0.1.0
