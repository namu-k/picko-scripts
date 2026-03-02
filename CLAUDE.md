# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Picko is a content pipeline automation system that curates, generates, and publishes content from RSS feeds and other sources. It transforms raw content into multiple formats (longform articles, social media posts, image prompts) using LLMs and manages content through an Obsidian Vault interface.

**Key Design Decision**: The system uses different LLMs for different tasks - local LLMs (Ollama) for high-volume NLP tasks (summary, tagging, embedding) and cloud LLMs (OpenAI, Anthropic, OpenRouter, Relay) for creative writing requiring higher quality.

## Development Commands

### Daily Content Collection
```bash
# Collect content from RSS feeds
python -m scripts.daily_collector --date 2026-02-09

# Collect specific sources only
python -m scripts.daily_collector --sources techcrunch ai_news

# Run in dry-run mode (no actual writing)
python -m scripts.daily_collector --dry-run
```

### Content Generation
```bash
# Generate approved content from digest (only auto_ready items)
python -m scripts.generate_content --date 2026-02-09

# Force generate all items regardless of writing_status
python -m scripts.generate_content --auto-all

# Generate specific content types
python -m scripts.generate_content --type longform packs

# Force regenerate existing content
python -m scripts.generate_content --force
```

### Validation & Health Checks
```bash
# Validate generated content
python -m scripts.validate_output --path Content/Longform/
python -m scripts.validate_output --recursive --verbose

# Check pipeline health
python -m scripts.health_check
python -m scripts.health_check --json
```

### Source Management
```bash
# Evaluate source quality for an account
python -m scripts.source_curator --account socialbuilders --threshold 0.6

# Export source report as CSV
python -m scripts.source_curator --account socialbuilders --export-csv

# Discover new sources based on account profile
python -m scripts.source_discovery --account socialbuilders --keywords "AI, startup" --max-results 10
```

### Multimedia Rendering
```bash
# Render media from template
python -m scripts.render_media render --input Inbox/Multimedia/mm_xxx.md

# Check pipeline status
python -m scripts.render_media status

# Review pending proposals
python -m scripts.render_media review

# Review final renders
python -m scripts.render_media review --finals
```

### Simple RSS Collection
```bash
# Quick RSS collection with custom output
python -m scripts.simple_rss_collector -o ./output -c config/sources.yml

# Collect only recent 24 hours
python -m scripts.simple_rss_collector --hours 24 --max-items 50

# Dry-run mode
python -m scripts.simple_rss_collector --dry-run
```

### Workflow Orchestration (Agentic)
```bash
# Run a workflow YAML
python -m scripts.run_workflow --workflow config/workflows/daily_pipeline.yml

# Run agentic pipeline example
python -m scripts.run_workflow --workflow config/workflows/agentic_pipeline.yml

# Dry-run mode
python -m scripts.run_workflow --workflow config/workflows/agentic_pipeline.yml --dry-run
```

### Environment Setup

**Requirements**: Python 3.13+

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up API keys using .env file (recommended)
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux
# Then edit .env with your actual keys

# Alternative: Set environment variables directly
set OPENAI_API_KEY=your_api_key_here  # Windows
export OPENAI_API_KEY=your_api_key_here  # macOS/Linux
```

**Note**: The `.env` file is automatically loaded when `picko.config` is imported. The `api_key_env` values in `config.yml` (e.g., `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `RELAY_API_KEY`) reference environment variables set in `.env`.

## Architecture Overview

### Core Modules (`picko/`)

- **config.py**: Central configuration loader with task-specific LLM configs (summary_llm, writer_llm)
- **vault_io.py**: Obsidian Vault interface for reading/writing markdown notes with frontmatter
- **llm_client.py**: Multi-provider LLM client with Ollama (local), OpenAI, Anthropic, OpenRouter support
- **embedding.py**: Local-first embedding with sentence-transformers, OpenAI fallback
- **scoring.py**: Content scoring algorithm (novelty, relevance, quality) with configurable weights
- **account_context.py**: Account identity, weekly slot, and style profile loader for persona-based content
- **prompt_loader.py**: External prompt loader from `config/prompts/` with Jinja2 template support
- **prompt_composer.py**: Multi-layer prompt composition system (base + style + identity + context)
- **templates.py**: Jinja2-based template rendering for different content formats
- **logger.py**: Unified logging setup using loguru with daily rotation
- **html_renderer.py**: HTML-to-image rendering using Playwright for multimedia content
- **multimedia_io.py**: Multimedia content I/O (images, videos) with proposal and render management
- **source_manager.py**: RSS source quality management and curation
- **proposal_generator.py**: Media proposal generation from content templates
- **layout_config.py**: Layout preset and theme configuration for multimedia rendering
- **publisher.py**: Social media publishing abstraction (Twitter API integration)
- **collectors/****: Modular collector architecture
  - `BaseCollector`: Abstract base class for all collectors
  - `CollectedItem`: Unified data structure for collected content
  - `RSSCollector`: RSS feed collector extracted from daily_collector
  - `PerplexityCollector`: Perplexity Tasks result collector with file watching
- **notification/bot.py**: Human review bot (Telegram/Slack) with timeout/reminder handling
- **discovery/base.py**: `SourceCandidate` model and `BaseDiscoveryCollector` interface
- **discovery/gates.py**: Human confirmation gate (social sources always require review)
- **discovery/orchestrator.py**: Multi-adapter source discovery orchestration and source registration
- **discovery/adapters/****: Threads, Reddit, Mastodon discovery adapters
- **quality/graph.py**: LangGraph-based quality state machine (`QualityGraph`, `QualityState`)
- **quality/confidence.py**: Confidence normalization and verdict thresholds
- **quality/feedback.py**: Human feedback loop and accuracy metrics
- **quality/validators/****: Primary and cross-check validators
- **orchestrator/actions.py**: Action registry + typed action config/fallback config
- **orchestrator/engine.py**: Workflow engine with dynamic steps and fallback execution
- **orchestrator/default_actions.py**: Built-in workflow actions (collector/fetcher/nlp/embed/score/generate/publish/quality.verify)
- **orchestrator/expr.py**: Safe expression evaluator with workflow operators
- **orchestrator/vault_adapter.py**: Vault frontmatter query interface (count, list, field)
- **orchestrator/batch.py**: Batch processing support for workflow items

### LLM Architecture (Task-Specific)

The system uses different LLMs for different tasks via `picko/llm_client.py`:

| Task | Config Key | Providers | Default Models | Purpose |
|------|-----------|----------|----------------|---------|
| Summary/Tagging | `summary_llm` | ollama, openai, anthropic, openrouter, relay | deepseek-r1:7b (ollama) | Cost-effective NLP |
| Embedding | `embedding` | local, ollama, openai | BAAI/bge-m3 (local) | Similarity scoring |
| Writing | `writer_llm` | openai, anthropic, openrouter, relay | gpt-4o-mini (openai) | Quality content |

**Supported Providers:**
- **ollama**: Local LLMs (deepseek-r1:7b, qwen2.5:7b, llama3.3:70b, mxbai-embed-large:1024, qwen3-embedding:0.6b)
- **openai**: GPT-4o, GPT-4o-mini, text-embedding-3-small
- **anthropic**: Claude 3.5 Sonnet
- **openrouter**: OpenAI models via OpenRouter (uses `OPENROUTER_API_KEY`)
- **relay**: Relay provider (uses `RELAY_API_KEY`)

**Design Rationale:**
- **Local LLMs** (ollama/local) for high-volume, low-complexity tasks (summary, tagging, embedding)
- **Cloud LLMs** for creative writing requiring higher quality
- **Automatic fallback** configured via `fallback_provider`, `fallback_model`, `fallback_api_key_env`

**API Key Configuration:**
- API keys are read from environment variables specified in `api_key_env` config
- OpenRouter provider defaults to `OPENROUTER_API_KEY` if `api_key_env` is omitted
- `.env` file is automatically loaded when `picko.config` module is imported

### Multimedia Rendering Architecture

The multimedia rendering system converts content templates into images/videos:

**Components:**
- **html_renderer.py**: Renders HTML templates to PNG using Playwright
- **multimedia_io.py**: Manages media proposals, renders, and vault I/O
- **proposal_generator.py**: Generates media proposals from content templates
- **layout_config.py**: Loads layout presets and themes from `config/layouts/`

**Workflow:**
1. **Proposal Generation**: Content template → HTML template → Media proposal
2. **Review**: Human reviews proposals in Obsidian vault
3. **Rendering**: Approved proposals → Playwright → Final images/videos

**Layout System:**
- **Presets**: `corporate`, `minimal_dark`, `minimal_light`, `social_gradient`, `vibrant`
- **Themes**: Account-specific color schemes and typography
- **Defaults**: Base configuration in `_defaults.yml`

### Scripts (`scripts/`)

#### Phase 1: Core Scripts
- **daily_collector.py**: Main ingestion pipeline - fetches RSS, deduplicates, extracts content, scores, and creates digest
- **generate_content.py**: Creates longform articles, social media packs, and image prompts from approved digest items
- **validate_output.py**: Validates generated content for required frontmatter fields, sections, and wikilinks
- **health_check.py**: Checks system health - API keys, vault access, RSS sources, disk space

#### Phase 2: Utility Scripts
- **archive_manager.py**: Archives old unapproved content and cleans related cache
- **retry_failed.py**: Retries failed items from logs by specific stage (fetch/nlp/embed/score/export)
- **publish_log.py**: Creates and manages publication logs with platform tracking
- **explore_topic.py**: Topic exploration script for thought expansion before longform writing
- **style_extractor.py**: Extracts writing style from reference URLs and generates style prompts
- **source_curator.py**: Source quality evaluation and curation with threshold-based filtering
- **source_discovery.py**: Automatic source discovery based on account profiles and keywords
- **simple_rss_collector.py**: Standalone RSS collector for quick testing and ad-hoc collection

#### Phase 3: Analytics Scripts (Placeholder Implementations)
- **engagement_sync.py**: Syncs platform metrics (views, likes, etc.) to publish logs - requires API integration
- **score_calibrator.py**: Analyzes performance vs predicted scores, suggests weight adjustments
- **duplicate_checker.py**: Finds duplicate/similar content using embedding similarity

#### Phase 4: Multimedia Scripts
- **render_media.py**: Multimedia rendering pipeline - renders HTML templates to images/videos using Playwright

#### Phase 5: Orchestration & Agentic Scripts
- **run_workflow.py**: Workflow YAML execution CLI (`WorkflowEngine` + `ActionRegistry`)

### Configuration Structure

```
config/
├── config.yml          # Main configuration
├── sources.yml         # RSS feed sources and categories
├── collectors.yml      # Collector-specific configuration
├── workflows/          # Orchestration workflow definitions
│   ├── daily_pipeline.yml
│   ├── approved_packs.yml
│   ├── image_generation.yml
│   ├── twitter_publish.yml
│   └── agentic_pipeline.yml
├── prompts/            # Externalized LLM prompts
│   ├── longform/
│   │   ├── default.md
│   │   ├── with_exploration.md
│   │   └── with_reference.md
│   ├── packs/
│   │   ├── twitter.md
│   │   ├── linkedin.md
│   │   └── newsletter.md
│   ├── image/
│   │   ├── default.md
│   │   ├── twitter.md
│   │   ├── linkedin.md
│   │   └── newsletter.md
│   ├── exploration/
│   │   └── default.md
│   └── reference/
│       └── analyze.md
├── accounts/           # Account-specific profiles
│   └── socialbuilders.yml
├── layouts/            # Layout presets and themes
│   ├── _defaults.yml
│   ├── presets/
│   │   ├── corporate.yml
│   │   ├── minimal_dark.yml
│   │   ├── minimal_light.yml
│   │   ├── social_gradient.yml
│   │   └── vibrant.yml
│   └── themes/
│       ├── fitness_wellness.yml
│       ├── socialbuilders.yml
│       └── tech_startup.yml
└── reference_styles/   # Style profiles for content personalization
    └── founder_tech_brief/
        ├── profile.yml
        ├── writing_prompt.md
        ├── image_prompt.md
        └── video_prompt.md
```

**Configuration Architecture:**
- Uses `dataclass` types for type-safe configuration (`picko/config.py`)
- Lazy loading: sources and account profiles loaded on-demand
- `.env` file auto-loaded on module import for API keys
- Singleton pattern via `get_config()` for consistent access across modules
- **External Prompts**: LLM prompts stored in `config/prompts/` and loaded via `picko/prompt_loader.py`

### Code Style & Linting

```bash
# Format code (black, line length: 120)
black picko/ scripts/ tests/

# Sort imports (isort)
isort picko/ scripts/ tests/

# Lint (flake8)
flake8 picko/ scripts/ tests/

# Type checking (mypy)
mypy picko/

# Run all linting (via pre-commit)
pre-commit run --all-files
```

**Configuration**: See `pyproject.toml` for tool settings (black, isort, pytest, mypy, coverage).

## Content Flow

1. **Ingestion**: RSS feeds → Content extraction → NLP processing → Scoring → Export to `Inbox/Inputs/`
2. **Writing Method Selection**: Each input has `writing_status` field:
   - `pending`: Not yet selected (default)
   - `auto_ready`: Marked for automatic generation via API
   - `manual`: Marked for manual writing (e.g., GPT Web)
   - `completed`: Content generation finished
3. **Curation**: Review daily digest in `Inbox/Inputs/_digests/` - check items to approve
4. **Generation**: Only items with `auto_ready` status + digest checkbox are processed by `generate_content.py`
5. **Validation**: All generated content validated for structure and completeness

## Key Design Patterns

- **Configuration-Driven**: All behavior controlled through YAML configs
- **Obsidian-Centric**: Content stored as markdown notes with YAML frontmatter
- **Template-Based**: Consistent output format using Jinja2 templates
- **Scoring System**: Multi-factor scoring to prioritize high-quality content
- **Account Profiles**: Different audiences with customized relevance scoring
- **Layout System**: Preset-based layouts with theme support for multimedia rendering
- **Proposal-Review Workflow**: Media proposals require review before final rendering

## Important File Locations

- **Vault Root**: Configured in `config.yml` under `vault.root` (default: `mock_vault/`)
- **API Keys**: `.env` file at project root (auto-loaded, use `.env.example` as template)
- **Logs**: `logs/YYYY-MM-DD/` (rotated daily, retention configurable)
- **Cache**: `cache/embeddings/` (cached embeddings for cost savings)
- **Templates**: Embedded in `picko/templates.py` as Jinja2 strings (no physical template files)
- **Prompts**: External prompts in `config/prompts/` (longform, packs, image, exploration, reference)
- **Layouts**: Layout presets and themes in `config/layouts/` (presets/, themes/)
- **Reference Styles**: Style profiles in `config/reference_styles/`
- **Project Root**: Auto-detected via `PROJECT_ROOT` in `picko/config.py`

## Project Structure

```
picko-scripts/
├── picko/                   # Core modules (importable package)
│   ├── __init__.py
│   ├── config.py            # Configuration loading with dataclasses, .env support
│   ├── vault_io.py          # Obsidian markdown I/O with frontmatter
│   ├── llm_client.py        # Multi-provider LLM client
│   ├── embedding.py         # Local-first embedding manager
│   ├── scoring.py           # Content scoring algorithm
│   ├── account_context.py   # Account identity, weekly slot, style profile loader
│   ├── prompt_loader.py     # External prompt loader with Jinja2 template support
│   ├── prompt_composer.py   # Multi-layer prompt composition system
│   ├── templates.py         # Jinja2 template definitions (embedded)
│   ├── logger.py            # Loguru-based logging setup
│   ├── html_renderer.py     # HTML-to-image rendering with Playwright
│   ├── multimedia_io.py     # Multimedia content I/O management
│   ├── source_manager.py    # Source quality management
│   ├── proposal_generator.py # Media proposal generation
│   ├── layout_config.py     # Layout preset and theme configuration
│   ├── notification/        # Human review bot
│   ├── discovery/           # Source discovery subsystem
│   ├── quality/             # Quality verification subsystem
│   └── orchestrator/        # Workflow orchestration layer
├── scripts/                 # Executable CLI scripts
│   ├── daily_collector.py   # Main ingestion pipeline
│   ├── generate_content.py  # Content generation from digests
│   ├── validate_output.py   # Content validation
│   ├── health_check.py      # System health verification
│   ├── archive_manager.py   # Old content archival
│   ├── retry_failed.py      # Retry failed pipeline items
│   ├── publish_log.py       # Publication logging
│   ├── explore_topic.py     # Topic exploration for longform writing
│   ├── style_extractor.py   # Style extraction from reference URLs
│   ├── source_curator.py    # Source quality evaluation
│   ├── source_discovery.py  # Automatic source discovery
│   ├── simple_rss_collector.py  # Standalone RSS collector
│   ├── render_media.py      # Multimedia rendering pipeline
│   ├── run_workflow.py      # Workflow orchestrator CLI
│   ├── engagement_sync.py   # Platform metrics sync (Phase 3)
│   ├── score_calibrator.py  # Score weight analysis (Phase 3)
│   ├── duplicate_checker.py # Duplicate detection (Phase 3)
│   ├── setup_scheduler.ps1  # Windows Task Scheduler setup
│   └── run_daily_collector.ps1  # Scheduler runner script
├── tests/                   # Pytest tests
│   ├── conftest.py          # Shared fixtures
│   ├── test_config.py       # Config loader tests
│   ├── test_llm_client.py   # LLM client tests
│   ├── test_scoring.py      # Scoring algorithm tests
│   ├── test_templates.py    # Template rendering tests
│   ├── test_e2e_dryrun.py   # End-to-end dry-run tests
│   └── test_integration.py  # Integration tests
├── .github/workflows/       # CI/CD workflows
│   └── test.yml             # Automated testing
├── .cursor/commands/        # Cursor AI commands
├── config/                  # Configuration files
├── logs/                    # Daily rotated logs
├── cache/                   # Embedding cache
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── pyproject.toml          # Project metadata (requires Python >=3.13)
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run by marker (unit/integration/slow)
pytest -m unit
pytest -m integration
pytest -m slow

# Run with coverage
pytest --cov=picko --cov-report=html

# Run specific test function
pytest tests/test_config.py::test_load_config

# Dry-run mode (no actual writing)
python -m scripts.daily_collector --date 2026-02-09 --dry-run
```

**Pytest Markers**:
- `unit`: Fast, isolated unit tests
- `integration`: Tests that interact with external services (APIs, vault I/O)
- `slow`: Long-running tests (embedding, full pipeline)

**Test Fixtures** (see `tests/conftest.py`):
- `temp_vault_dir`: Creates temporary vault directory structure
- `mock_config`: Provides mocked Config object
- `sample_input_data`: Sample input content for testing

### Account Context Module

The `account_context.py` module provides account persona loading for personalized content:

```python
from picko.account_context import get_identity, get_weekly_slot, get_style_for_account

# Load account identity
identity = get_identity("builders_social_club")
print(identity.one_liner)  # "예비창업자~초기창업자가..."

# Load weekly slot preset
weekly_slot = get_weekly_slot("2026-02-16")
print(weekly_slot.pillar_distribution)  # {"P1": 2, "P2": 2, "P3": 2, "P4": 1}

# Load style profile
style = get_style_for_account("builders_social_club")
print(style["tone"])  # Style characteristics
```

**Data Structures:**
- `AccountIdentity`: Account persona (one_liner, target_audience, pillars, tone_voice, boundaries)
- `WeeklySlot`: Weekly content preset (pillar_distribution, customer_outcome, CTA)
- `StyleProfile`: Writing style characteristics from reference analysis

## Environment Variables

**Required (at least one):**
- `OPENAI_API_KEY`: OpenAI API key (used by openai provider, default fallback)
- `OPENROUTER_API_KEY`: OpenRouter API key (for openrouter provider)
- `RELAY_API_KEY`: Relay API key (for relay provider)
- `ANTHROPIC_API_KEY`: Anthropic API key (for anthropic provider)

**Discovery Adapter Variables (optional):**
- `THREADS_ACCESS_TOKEN`: Threads API token (requires Meta App Review for `/keyword_search`)
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`: Reddit OAuth credentials
- `MASTODON_ACCESS_TOKEN`, `MASTODON_INSTANCE`: Mastodon API credentials

**Human Review Bot Variables (optional):**
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: Telegram bot review notifications
- `REVIEW_TIMEOUT_HOURS`: Review timeout window (default 72)

**Setup via .env file (recommended):**
```bash
# Copy example .env
cp .env.example .env

# Edit with your keys
OPENAI_API_KEY=sk-your-key-here
OPENROUTER_API_KEY=sk-or-your-key-here
RELAY_API_KEY=your-relay-key-here
THREADS_ACCESS_TOKEN=your-threads-access-token
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
MASTODON_ACCESS_TOKEN=your-mastodon-access-token
MASTODON_INSTANCE=mastodon.social
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
REVIEW_TIMEOUT_HOURS=72
```

The `.env` file is automatically loaded when the `picko.config` module is imported. Each LLM config section (`summary_llm`, `writer_llm`, `embedding`) has an `api_key_env` field that specifies which environment variable to use.

## Local LLM Setup

For local LLM usage (summary/tagging/embedding):

1. **Install Ollama**: [https://ollama.ai/download](https://ollama.ai/download)
2. **Pull models**:
   ```bash
   ollama pull deepseek-r1:7b      # Summary/tagging
   ollama pull qwen2.5:7b          # Alternative for summary/tagging
   ollama pull mxbai-embed-large:1024   # Embedding (Ollama)
   ollama pull qwen3-embedding:0.6b     # Alternative embedding
   ```
3. **Configure**: Set `provider: ollama` in `config.yml` for `summary_llm` or `embedding`
4. **Install dependencies**: `pip install ollama sentence-transformers`

**Supported local models:**
- **Summary/Tagging (Ollama)**: deepseek-r1:7b, qwen2.5:7b, qwen2.5:3b
- **Embedding (Ollama)**: mxbai-embed-large:1024, qwen3-embedding:0.6b
- **Embedding (sentence-transformers)**: BAAI/bge-m3, BAAI/bge-base-en-v1.5, all-MiniLM-L6-v2
