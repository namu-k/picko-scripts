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
