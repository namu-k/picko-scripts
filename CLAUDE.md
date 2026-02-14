# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Picko is a content pipeline automation system that curates, generates, and publishes content from RSS feeds and other sources. It transforms raw content into multiple formats (longform articles, social media posts, image prompts) using LLMs and manages content through an Obsidian Vault interface.

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

### Environment Setup

**Requirements**: Python 3.13+

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up API key (OpenAI)
set OPENAI_API_KEY=your_api_key_here  # Windows
export OPENAI_API_KEY=your_api_key_here  # macOS/Linux
```

## Architecture Overview

### Core Modules (`picko/`)

- **config.py**: Central configuration loader with task-specific LLM configs (summary_llm, writer_llm)
- **vault_io.py**: Obsidian Vault interface for reading/writing markdown notes with frontmatter
- **llm_client.py**: Multi-provider LLM client with Ollama (local), OpenAI, Anthropic support
- **embedding.py**: Local-first embedding with sentence-transformers, OpenAI fallback
- **scoring.py**: Content scoring algorithm (novelty, relevance, quality) with configurable weights
- **templates.py**: Jinja2-based template rendering for different content formats
- **logger.py**: Unified logging setup using loguru with daily rotation

### LLM Architecture (Task-Specific)

The system uses different LLMs for different tasks:

| Task | LLM Client | Provider | Model | Purpose |
|------|-----------|----------|-------|---------|
| Summary/Tagging | `get_summary_client()` | Ollama (local) | deepseek-r1:7b | Cost-effective NLP |
| Embedding | `get_embedding_manager()` | sentence-transformers | BAAI/bge-m3 | Local similarity |
| Writing | `get_writer_client()` | OpenAI (cloud) | gpt-4o-mini | Quality content |

**Design Rationale:**
- **Local LLMs** for high-volume, low-complexity tasks (summary, tagging, embedding)
- **Cloud LLMs** for creative writing requiring higher quality
- **Automatic fallback** to cloud if local models fail

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

### Configuration Structure

```
config/
├── config.yml          # Main configuration
├── sources.yml         # RSS feed sources and categories
└── accounts/           # Account-specific profiles
    └── socialbuilders.yml  # Target audience, interests, channel settings
```

**Configuration Architecture:**
- Uses `dataclass` types for type-safe configuration (`picko/config.py`)
- Lazy loading: sources and account profiles loaded on-demand
- Environment variable override: prefix any config key with `PICKO_` (e.g., `PICKO_VAULT_ROOT`)
- Singleton pattern via `get_config()` for consistent access across modules

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

## Important File Locations

- **Vault Root**: Configured in `config.yml` under `vault.root` (default: `mock_vault/`)
- **Logs**: `logs/YYYY-MM-DD/` (rotated daily, retention configurable)
- **Cache**: `cache/embeddings/` (cached OpenAI embeddings for cost savings)
- **Templates**: Embedded in `picko/templates.py` as Jinja2 strings (no physical template files)
- **Project Root**: Auto-detected via `PROJECT_ROOT` in `picko/config.py`

## Project Structure

```
picko-scripts/
├── picko/                   # Core modules (importable package)
│   ├── __init__.py
│   ├── config.py            # Configuration loading with dataclasses
│   ├── vault_io.py          # Obsidian markdown I/O with frontmatter
│   ├── llm_client.py        # Multi-provider LLM client
│   ├── embedding.py         # Local-first embedding manager
│   ├── scoring.py           # Content scoring algorithm
│   ├── templates.py         # Jinja2 template definitions (embedded)
│   └── logger.py            # Loguru-based logging setup
├── scripts/                 # Executable CLI scripts
│   ├── daily_collector.py   # Main ingestion pipeline
│   ├── generate_content.py  # Content generation from digests
│   ├── validate_output.py   # Content validation
│   ├── health_check.py      # System health verification
│   ├── archive_manager.py   # Old content archival
│   ├── retry_failed.py      # Retry failed pipeline items
│   └── publish_log.py       # Publication logging
├── config/                  # Configuration files
├── logs/                    # Daily rotated logs
├── cache/                   # Embedding cache
├── requirements.txt         # Python dependencies
└── pyproject.toml          # Project metadata (requires Python >=3.13)
```

## Testing

Use `--dry-run` flag with daily_collector to test without writing:
```bash
python -m scripts.daily_collector --date 2026-02-09 --dry-run
```

Use health_check to verify system status:
```bash
python -m scripts.health_check          # Human-readable output
python -m scripts.health_check --json   # Machine-readable output
```

## Environment Variables

Required:
- `OPENAI_API_KEY`: OpenAI API key for writer LLM (and fallback for summary/embedding)

Optional:
- Override any config value by setting environment variables with `PICKO_` prefix

## Local LLM Setup

For local LLM usage (summary/tagging/embedding):

1. **Install Ollama**: [https://ollama.ai/download](https://ollama.ai/download)
2. **Pull models**: `ollama pull deepseek-r1:7b`
3. **Configure**: Set `summary_llm.provider: ollama` in config.yml
4. **Install dependencies**: `pip install ollama sentence-transformers`

**Supported local models:**
- deepseek-r1:7b (summary/tagging)
- qwen2.5:7b (alternative)
- BAAI/bge-m3 (embedding)
- sentence-transformers/all-MiniLM-L6-v2 (lightweight embedding)