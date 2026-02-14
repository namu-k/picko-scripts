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

### [ ] 4. Enable and test pre-commit hooks
- **Priority**: P2
- **Owner**: Unassigned
- **Description**: Install and configure pre-commit hooks
- **Commands**:
  - `pip install pre-commit`
  - `pre-commit install`
  - `pre-commit run --all-files`
- **Acceptance**: All hooks pass on current codebase

### [ ] 5. Pin all dependencies
- **Priority**: P2
- **Owner**: Unassigned
- **Description**: Pin dependency versions in requirements.txt
- **Tool**: `pip-compile` or manual pinning
- **Acceptance**: All versions pinned with `==` or `~=`

### [ ] 6. Run security audit and fix vulnerabilities
- **Priority**: P1
- **Owner**: Unassigned
- **Commands**:
  - `safety check`
  - `pip-audit`
- **Acceptance**: Zero known vulnerabilities

## Medium Priority

### [ ] 7. Add CI badge to README.md
- **Priority**: P3
- **Owner**: Unassigned
- **Description**: Add GitHub Actions workflow badge to README
- **Badge**: `[![Test](https://github.com/your-username/picko-scripts/actions/workflows/test.yml/badge.svg)](https://github.com/your-username/picko-scripts/actions/workflows/test.yml)`

### [ ] 8. Create v0.2.0 GitHub Release
- **Priority**: P3
- **Owner**: Unassigned
- **Description**: Tag commit 753183c (or newer) as v0.2.0 and create GitHub release
- **Changelog**: Use CHANGELOG.md v0.2.0 section

### [ ] 9. Document OPENAI_API_KEY setup
- **Priority**: P3
- **Owner**: Unassigned
- **Description**: Add detailed instructions for setting up GitHub Actions Secrets
- **Location**: README.md or separate DEPLOYMENT.md

### [x] 10. Test Windows Task Scheduler script
- **Priority**: P2
- **Owner**: Completed
- **Description**: Verify `setup_scheduler.ps1` works correctly
- **Command**: `.\scripts\setup_scheduler.ps1 -VaultPath "C:\picko-scripts\mock_vault" -Hour 8 -Minute 0 -WhatIf`
- **Result**: PASS - Would create task 'Picko Daily Collector' successfully

## Low Priority

### [ ] 11. Set up daily health check monitoring
- **Priority**: P4
- **Owner**: Unassigned
- **Description**: Configure `.github/workflows/health_check.yml` and verify notifications

### [ ] 12. Create SECURITY.md policy
- **Priority**: P4
- **Owner**: Unassigned
- **Description**: Document security policy, vulnerability reporting, and secret management

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
