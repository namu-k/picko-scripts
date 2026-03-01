# Changelog

All notable changes to Picko will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-02-26

### Added
- **Auto Collector V2 (004)**:
  - `picko/source_manager.py`: Source metadata CRUD with V2 extension fields support
  - `picko/collectors/`: Modular collector architecture
    - `BaseCollector`: Abstract base class for all collectors
    - `CollectedItem`: Unified data structure for collected content
    - `RSSCollector`: RSS feed collector extracted from daily_collector
    - `PerplexityCollector`: Perplexity Tasks result collector with file watching
  - `scripts/source_discovery.py`: Automatic source discovery with Google News, Tavily, Substack integration
  - `scripts/source_curator.py`: Source quality evaluation and curation CLI
  - `config/collectors.yml`: Collector configuration with quality rules
  - `.github/workflows/auto_collect.yml`: Daily collection + weekly discovery automation
- **Orchestration Layer (005)**:
  - `picko/orchestrator/`: Workflow automation layer
    - `VaultAdapter`: Vault frontmatter query interface (count, list, field)
    - `WorkflowEngine`: YAML workflow loader and executor
    - `ActionRegistry`: Action name → function mapping
    - `ExprEvaluator`: Safe expression evaluation for workflow conditions
  - `scripts/run_workflow.py`: CLI for running YAML-defined workflows
  - `config/workflows/`: Workflow definitions
    - `daily_pipeline.yml`: Daily collection → generation pipeline
    - `approved_packs.yml`: Approved longform → packs generation
    - `image_generation.yml`: Image rendering workflow
    - `twitter_publish.yml`: Twitter publishing workflow
- **Publisher Module**:
  - `picko/publisher.py`: Social media publishing abstraction
  - Twitter API integration with OAuth 1.0a support
  - Workflow scheduler for automated publishing
- **Tests**:
  - `test_collectors.py`: RSSCollector and PerplexityCollector tests
  - `test_source_manager.py`: SourceManager CRUD tests
  - `test_source_discovery.py`: Source discovery engine tests
  - `test_source_curator.py`: Source curation tests
  - `test_orchestrator_*.py`: Orchestration layer tests (5 test files)

### Changed
- `daily_collector.py`: Integrated RSSCollector and PerplexityCollector
- Documentation updated for new modules and workflows

### Security
- Tavily API key support via environment variable

## [Unreleased]

### Added
- **Tests** (Phase 2 utility scripts):
  - `test_archive_manager.py`: Archive operations and cleanup tests
  - `test_duplicate_checker.py`: Embedding-based duplicate detection tests
  - `test_health_check.py`: System health verification tests
  - `test_publish_log.py`: Publication logging tests
  - `test_retry_failed.py`: Failed item retry mechanism tests
  - `test_simple_rss_collector.py`: Standalone RSS collection tests
  - `test_style_extractor.py`: Style extraction from URLs tests
- **Specs**:
  - `specs/006-multimedia-styles/`: Multimedia styles system specification and tasks
- **Docs**:
  - `AGENT_GUIDE.md`: CLI coding agent guide for pipeline replication
### Changed
- Extended test coverage for collectors, daily_collector, embedding, engagement_sync, generate_content, publisher, render_media, scheduler, source_discovery, validate_output
- Hardened `.gitignore` to exclude local artifacts (`NUL`, `C*picko-scripts.sisyphus*`, `.ruff_cache/`)

### Fixed
- Aligned `specs/006-multimedia-styles/tasks.md` with plan.md (path references, cache metadata, mock annotations)

## [0.5.0] - 2026-03-01

### Added
- **Agentic Framework (007)**:
  - `picko/orchestrator/engine.py`: Dynamic step execution support
    - Workflow-level `dynamic_steps` declarations in YAML
    - Action-emitted `dynamic_steps` via step outputs
    - Runtime insertion with condition evaluation
  - `picko/orchestrator/default_actions.py`: `quality.verify` action
    - Single-item mode for workflow invocation
    - Batch mode with verified/pending/rejected grouping
    - Integration with `QualityGraph.verify()`
  - `picko/discovery/orchestrator.py`: Source discovery orchestration
    - Multi-adapter sequential execution
    - Human confirmation gate integration
    - Trusted domain evaluation
  - `picko/discovery/adapters/`: Platform adapters
    - `threads.py`: Threads API adapter (placeholder, App Review required)
    - `reddit.py`: Reddit API adapter (OAuth)
    - `mastodon.py`: Mastodon API adapter
  - `picko/discovery/gates.py`: Human confirmation gate logic
- **Tests**:
  - `test_adapter_threads.py`: Threads adapter placeholder and rate limit tests
  - `test_adapter_reddit.py`: Reddit adapter tests
  - `test_adapter_mastodon.py`: Mastodon adapter tests
  - `test_discovery_orchestrator.py`: Discovery orchestration tests
  - `test_discovery_gates.py`: Human confirmation gate tests
  - `test_orchestrator_engine.py`: Dynamic steps tests (2 new)
  - `test_orchestrator_default_actions.py`: Quality verify tests
- **Specs**:
  - `specs/007-agentic-framework/`: Complete specification and task breakdown
  - `docs/plans/2026-02-28-agentic-framework-spec.md`: Business requirements
  - `docs/plans/2026-02-28-hybrid-agentic-pipeline-design.md`: Technical design

### Changed
- `.env.example`: Added discovery adapter environment variables (THREADS_ACCESS_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, MASTODON_ACCESS_TOKEN, MASTODON_INSTANCE)

### Fixed
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

[0.4.0]: https://github.com/namu-k/picko-scripts/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/namu-k/picko-scripts/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/namu-k/picko-scripts/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/namu-k/picko-scripts/releases/tag/v0.1.0
