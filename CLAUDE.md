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
# Generate approved content from digest
python -m scripts.generate_content --date 2026-02-09

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
```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key (OpenAI)
set OPENAI_API_KEY=your_api_key_here
```

## Architecture Overview

### Core Modules (`picko/`)

- **config.py**: Central configuration loader with YAML support and environment variable overrides
- **vault_io.py**: Obsidian Vault interface for reading/writing markdown notes with frontmatter
- **llm_client.py**: OpenAI/Anthropic API client with caching and retry logic
- **embedding.py**: Text embedding generation and similarity calculations using OpenAI
- **scoring.py**: Content scoring algorithm (novelty, relevance, quality) with configurable weights
- **templates.py**: Jinja2-based template rendering for different content formats
- **logger.py**: Unified logging setup using loguru with daily rotation

### Scripts (`scripts/`)

- **daily_collector.py**: Main ingestion pipeline - fetches RSS, deduplicates, extracts content, scores, and creates digest
- **generate_content.py**: Creates longform articles, social media packs, and image prompts from approved digest items
- **validate_output.py**: Validates generated content for required frontmatter fields, sections, and wikilinks
- **health_check.py**: Checks system health - API keys, vault access, RSS sources, disk space

### Configuration Structure

```
config/
├── config.yml          # Main configuration
├── sources.yml         # RSS feed sources and categories
└── accounts/           # Account-specific profiles
    └── socialbuilders.yml  # Target audience, interests, channel settings
```

## Content Flow

1. **Ingestion**: RSS feeds → Content extraction → NLP processing → Scoring → Export to `Inbox/Inputs/`
2. **Curation**: Review daily digest in `Inbox/Inputs/_digests/` - check items to approve
3. **Generation**: Approved items → Longform articles (`Content/Longform/`) → Social packs (`Content/Packs/`) → Image prompts (`Assets/Images/_prompts/`)
4. **Validation**: All generated content validated for structure and completeness

## Key Design Patterns

- **Configuration-Driven**: All behavior controlled through YAML configs
- **Obsidian-Centric**: Content stored as markdown notes with YAML frontmatter
- **Template-Based**: Consistent output format using Jinja2 templates
- **Scoring System**: Multi-factor scoring to prioritize high-quality content
- **Account Profiles**: Different audiences with customized relevance scoring

## Important File Locations

- **Vault Root**: `mock_vault/` (simulated Obsidian vault)
- **Logs**: `logs/YYYY-MM-DD/` (rotated daily)
- **Cache**: `cache/embeddings/` (cached OpenAI embeddings)
- **Templates**: Embedded in `templates.py` (no physical template files)

## Testing

Use `--dry-run` flag with daily_collector to test without writing:
```bash
python -m scripts.daily_collector --date 2026-02-09 --dry-run
```

## Environment Variables

Required:
- `OPENAI_API_KEY`: OpenAI API key for LLM and embeddings

Optional:
- Override any config value by setting environment variables with `PICKO_` prefix (e.g., `PICKO_LLM_MODEL=gpt-4-turbo`)