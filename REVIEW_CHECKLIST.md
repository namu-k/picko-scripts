# Code Review Checklist

Before merging any PR to `main`, ensure all items below are checked.

## Pre-Merge Requirements

### Testing
- [ ] All tests pass: `pytest tests/ -v`
- [ ] New code has test coverage (aim for >85%)
- [ ] Manual testing completed for new features
- [ ] E2E dry-run test passes: `python -m scripts.generate_content --dry-run`

### Code Quality
- [ ] No flake8 errors: `flake8 picko/ scripts/`
- [ ] No mypy errors (or exceptions documented): `mypy picko/`
- [ ] Code formatted with black: `black picko/ scripts/`
- [ ] Imports sorted with isort: `isort picko/ scripts/`

### Security
- [ ] No secrets in diff (no API keys, tokens, passwords)
- [ ] `.env` files in `.gitignore`
- [ ] Security scan passes: `safety check` and `pip-audit`

### Documentation
- [ ] CHANGELOG.md updated with version entry
- [ ] Version bumped in `pyproject.toml`
- [ ] New features documented in README.md or USER_GUIDE.md
- [ ] API changes documented in CLAUDE.md

### Breaking Changes
- [ ] Breaking changes listed in CHANGELOG.md
- [ ] Migration guide provided if needed

## Post-Merge Actions

- [ ] Create GitHub release tag
- [ ] Update milestone/project board
- [ ] Notify team of deployment
- [ ] Monitor CI for 24 hours after merge

## Specific Review Guidelines

### For Core Modules (`picko/`)
- Config changes: Update CLAUDE.md "Configuration Architecture"
- LLM changes: Document new models/providers
- Template changes: Verify rendering output

### For Scripts (`scripts/`)
- New CLI flags: Update help text and docs
- New environment variables: Document in CLAUDE.md
- Performance changes: Document any new requirements

### For CI/CD
- Workflow changes: Test in fork first
- New dependencies: Update requirements.txt with pinned versions

---

## Quick Reference Commands

```bash
# Run all checks
pytest tests/ -v && flake8 picko/ scripts/ && mypy picko/

# Format code
black picko/ scripts/
isort picko/ scripts/

# Security scan
safety check
pip-audit

# Dry-run test
python -m scripts.generate_content --dry-run
```
