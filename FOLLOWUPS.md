# Follow-up Tasks from Hardening Plan

This document tracks follow-up items from the hardening plan execution. Each item below should be created as a GitHub Issue.

## Critical (Must Complete)

### [x] 1. Fix failing tests
- **Priority**: P1
- **Owner**: Completed (commit 575e7b7)
- **Description**: Run full test suite and fix any failures
- **Command**: `pytest tests/ -v`
- **Acceptance**: All tests pass (46/46)

### [x] 2. Fix flake8 lint warnings
- **Priority**: P1
- **Owner**: Completed (commit 03a333f)
- **Description**: Run flake8 and fix all warnings
- **Command**: `flake8 picko/ scripts/`
- **Acceptance**: Zero flake8 warnings (E9, F63, F7, F82)
- **Result**: All files compile successfully, no critical issues found

### [x] 3. Add type hints to core modules
- **Priority**: P2
- **Owner**: Completed (commits 1b83f67, fcd7c89, 9e042d7, d606b7f, 2931637)
- **Description**: Add type hints to `picko/*.py` for mypy compliance
- **Files**: config.py, vault_io.py, llm_client.py, embedding.py, scoring.py, logger.py, templates.py
- **Acceptance**: `mypy picko/` passes without errors
- **Result**: SUCCESS - 0 mypy errors (reduced from 101 initial errors)

## High Priority

### [x] 4. Enable and test pre-commit hooks
- **Priority**: P2
- **Owner**: Completed
- **Description**: Install and configure pre-commit hooks
- **Commands**:
  - `pip install pre-commit`
  - `pre-commit install`
  - `pre-commit run --all-files`
- **Acceptance**: All hooks pass on current codebase
- **Result**: SUCCESS - All hooks (black, isort, flake8, mypy) pass

### [x] 5. Pin all dependencies
- **Priority**: P2
- **Owner**: Completed
- **Description**: Pin dependency versions in requirements.txt
- **Tool**: Manual pinning with `uv pip list`
- **Acceptance**: All versions pinned with `==`
- **Result**: SUCCESS - All dependencies pinned in requirements.txt and pyproject.toml

### [x] 6. Run security audit and fix vulnerabilities
- **Priority**: P1
- **Owner**: Completed
- **Commands**:
  - `safety check`
  - `pip-audit`
- **Acceptance**: Zero known vulnerabilities
- **Result**: PASS - 0 vulnerabilities found (116 packages scanned)

## Medium Priority

### [x] 7. Add CI badge to README.md
- **Priority**: P3
- **Owner**: Complete
- **Description**: Add GitHub Actions workflow badge to README
- **Result**: Badge already present in README.md (line 3)
- **Note**: Update `namu-k` placeholder with actual GitHub username when pushing to remote

### [x] 8. Create v0.2.0 GitHub Release
- **Priority**: P3
- **Owner**: Complete
- **Description**: Tag commit 34d10e1 as v0.2.0 and create GitHub release
- **Changelog**: Used CHANGELOG.md v0.2.0 section
- **Result**: Tag created successfully on commit 34d10e1
- **Note**: Push tag with `git push origin v0.2.0` and create release on GitHub

### [x] 9. Document OPENAI_API_KEY setup
- **Priority**: P3
- **Owner**: Complete
- **Description**: Add detailed instructions for setting up GitHub Actions Secrets
- **Location**: Created DEPLOYMENT.md
- **Result**: Comprehensive deployment guide covering local setup, GitHub Actions Secrets, troubleshooting, and security best practices

### [x] 10. Test Windows Task Scheduler script
- **Priority**: P2
- **Owner**: Completed
- **Description**: Verify `setup_scheduler.ps1` works correctly
- **Command**: `.\scripts\setup_scheduler.ps1 -VaultPath "C:\picko-scripts\mock_vault" -Hour 8 -Minute 0 -WhatIf`
- **Result**: PASS - Would create task 'Picko Daily Collector' successfully

## Low Priority

### [x] 11. Set up daily health check monitoring
- **Priority**: P4
- **Owner**: Complete
- **Description**: Configure `.github/workflows/health_check.yml` and verify notifications
- **Result**: Enhanced workflow with labels setup, success reporting, and auto-close of resolved issues
- **Schedule**: Daily at 8:00 AM UTC (4:00 PM KST)

### [x] 12. Create SECURITY.md policy
- **Priority**: P4
- **Owner**: Complete
- **Description**: Document security policy, vulnerability reporting, and secret management
- **Result**: Comprehensive security policy covering vulnerability reporting, secret management, best practices, and incident response

---

## Quick Commands for Reference

```bash
# Install all development tools
pip install pytest pytest-cov flake8 mypy black isort pre-commit safety pip-audit

# Run all checks
pytest tests/ -v
flake8 picko/ scripts/
mypy picko/
safety check
pip-audit

# Setup pre-commit
pre-commit install
pre-commit run --all-files

# Test Windows scheduler
powershell .\scripts\setup_scheduler.ps1 -VaultPath "C:\picko-scripts\mock_vault" -WhatIf
```

---

*Created: 2026-02-15*
*Reference: Commit 753183c and hardening plan*


---

## 006: Multimedia Styles System

### Phase 1: Foundation (P0)

#### 1.1 Layer System
- [ ] HTML layer structure (background, overlay, decoration, content)
- [ ] `_layer_base.html` common base template
- [ ] CSS layer styles (z-index, positioning)

#### 1.2 Image Source Module
- [ ] Create `picko/image_source.py` module
- [ ] Implement `ImageSourceManager` class
- [ ] Unsplash API integration (`search_unsplash()`)
- [ ] Image cache system (`cache/images/`)
- [ ] Environment variable loading (`UNSPLASH_ACCESS_KEY`)

#### 1.3 Photogram Style
- [ ] `config/layouts/styles/photogram.yml` configuration
- [ ] `templates/images/styles/photogram/` directory
- [ ] `quote_photo.html` template
- [ ] `card_photo.html` template
- [ ] `hero_photo.html` template (full screen)

#### 1.4 Input Schema Extension
- [ ] `multimedia_io.py`: add `style`, `template`, `image_keywords` fields
- [ ] Extend `MultimediaInput` dataclass
- [ ] Update parsing logic

#### 1.5 CLI Updates
- [ ] Add `--style` option
- [ ] Add `--image-keywords` option
- [ ] Add `--image-source` option
- [ ] Add `styles` subcommand (list available styles)

#### 1.6 Tests
- [ ] `test_image_source.py`: Unsplash search, cache
- [ ] `test_photogram_templates.py`: rendering tests
- [ ] E2E: full pipeline test

### Phase 2: Expansion (P1)

#### 2.1 Illustrated Style
- [ ] `config/layouts/styles/illustrated.yml` configuration
- [ ] `templates/images/styles/illustrated/` directory
- [ ] `quote_shapes.html` (abstract shapes)
- [ ] `card_abstract.html` (gradient + shapes)
- [ ] `gradient_wave.html` (wave pattern)

#### 2.2 SVG Decoration System
- [ ] `picko/decorations.py` module
- [ ] SVG shape library (circle, triangle, blob, wave)
- [ ] Dynamic color application
- [ ] Random placement algorithm

#### 2.3 Additional Image Sources
- [ ] Pexels API integration
- [ ] Local image library support
- [ ] Image source priority configuration

#### 2.4 Tests
- [ ] `test_illustrated_templates.py`
- [ ] `test_decorations.py`

### Phase 3: Corporate (P2)

#### 3.1 Corporate Style
- [ ] `config/layouts/styles/corporate.yml` configuration
- [ ] `templates/images/styles/corporate/` directory
- [ ] `infographic.html`
- [ ] `timeline.html`
- [ ] `comparison.html`

#### 3.2 Data Visualization
- [ ] Evaluate Chart.js or SVG chart support
- [ ] Simple bar chart, pie chart templates

#### 3.3 Tests
- [ ] `test_corporate_templates.py`

### Documentation
- [ ] Update `config/layouts/README.md` (style system)
- [ ] Update `CLAUDE.md` (new CLI options)
- [ ] Update `.env.example` (UNSPLASH_ACCESS_KEY)

---

*006 Section Added: 2026-02-28*
*Branch: 006-multimedia-styles*
