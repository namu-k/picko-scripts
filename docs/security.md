# Security Policy

This document outlines the security policies and procedures for the Picko project.

## Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [Secret Management](#secret-management)
- [Security Best Practices](#security-best-practices)
- [Dependency Management](#dependency-management)
- [Incident Response](#incident-response)

---

## Supported Versions

Currently, only the latest version of Picko receives security updates.

| Version | Security Support |
|---------|------------------|
| v0.2.x+ | ✅ Supported |
| v0.1.x | ❌ Unsupported |

---

## Reporting a Vulnerability

The Picko team takes security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**Do NOT open a public issue.** Instead, send your report privately:

1. **Email**: Send an email to the repository owner with the subject `[SECURITY] Vulnerability Report`
2. **Include as much information as possible**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

### What to Expect

- **Confirmation**: You should receive a response within 48 hours
- **Assessment**: We will investigate the issue and determine severity
- **Resolution**: We will work on a fix and provide an estimated timeline
- **Disclosure**: We will coordinate public disclosure with you

### Vulnerability Disclosure Process

1. **Report Submission**: Security vulnerability is reported privately
2. **Initial Response**: Team acknowledges receipt within 48 hours
3. **Investigation**: Team validates and assesses the vulnerability
4. **Fix Development**: Team develops and tests the fix
5. **Release**: Fix is released in a security update
6. **Public Disclosure**: Advisory is published after the fix is available

---

## Secret Management

### API Keys and Credentials

Picko requires API keys to function. These must **never** be committed to the repository.

#### Local Development

```bash
# Set environment variable temporarily
set OPENAI_API_KEY=sk-your-key-here  # Windows
export OPENAI_API_KEY=sk-your-key-here  # macOS/Linux

# Or persist in shell profile (~/.bashrc, ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
```

#### GitHub Actions

Store credentials as **Repository Secrets**:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the secret with an appropriate name (e.g., `OPENAI_API_KEY`)

### Required Secrets

| Secret Name | Purpose | Required |
|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API access for LLM features | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API access (optional) | No |
| `OLLAMA_BASE_URL` | Self-hosted Ollama instance (optional) | No |

### Secret Detection

The CI/CD pipeline includes checks for accidentally committed secrets:

```yaml
# From .github/workflows/test.yml
- name: Verify OPENAI_API_KEY is not in code
  run: |
    if grep -r "sk-" --include="*.py" --include="*.yml" --exclude-dir=".git" .; then
      echo "::error::Found potential API key in code!"
      exit 1
    fi
```

### Best Practices

1. **Never commit** API keys, tokens, or passwords
2. **Use environment variables** for all sensitive configuration
3. **Rotate keys regularly** (at least every 90 days)
4. **Use different keys** for development and production
5. **Revoke compromised keys** immediately
6. **Monitor usage** on OpenAI/LLM provider dashboards

---

## Security Best Practices

### For Users

1. **Keep Dependencies Updated**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Run Security Audits**
   ```bash
   safety check
   pip-audit
   ```

3. **Review Logs Regularly**
   - Check `logs/` directory for unusual activity
   - Monitor API usage on provider dashboards

4. **Use Virtual Environments**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```

### For Developers

1. **Pre-commit Hooks**
   - Enabled by default: `pre-commit install`
   - Runs checks before each commit

2. **Code Review Checklist**
   - No secrets committed
   - Dependencies are pinned
   - Input validation is present
   - Error handling doesn't expose sensitive data

3. **Testing**
   ```bash
   # Run full test suite
   pytest tests/ -v

   # Run security checks
   safety check
   pip-audit
   ```

---

## Dependency Management

### Pinned Versions

All dependencies are pinned to specific versions in `requirements.txt`:

```
pyyaml==6.0.3
openai==2.17.0
# ...
```

### Updating Dependencies

When updating dependencies:

1. **Check for vulnerabilities**:
   ```bash
   safety check
   pip-audit
   ```

2. **Update one package at a time**:
   ```bash
   pip install --upgrade package_name
   pip freeze > requirements.txt
   ```

3. **Test thoroughly** after updates

4. **Run full test suite**:
   ```bash
   pytest tests/ -v
   ```

### Security Scanning

The project uses two security scanning tools:

| Tool | Purpose | Command |
|------|---------|---------|
| **safety** | Checks against known vulnerabilities | `safety check` |
| **pip-audit** | Audits dependencies for issues | `pip-audit` |

Both run automatically in CI/CD on every push.

---

## Incident Response

### What Constitutes a Security Incident?

- Confirmed exploitation of a vulnerability
- Unauthorized access to user data
- Compromise of API keys or secrets
- Malicious code injection

### Incident Response Steps

1. **Identification**: Incident is discovered or reported
2. **Containment**: Immediate actions to limit impact
3. **Eradication**: Remove the threat
4. **Recovery**: Restore normal operations
5. **Post-Incident Review**: Document lessons learned

### Contact for Incidents

For active security incidents, contact the repository owner directly via email with the subject `[SECURITY] Incident`.

---

## Security Features in Picko

### Built-in Protections

1. **Input Validation**: All user inputs are validated before processing
2. **Secret Exclusion**: API keys are never logged
3. **Path Traversal Protection**: Vault paths are validated
4. **Rate Limiting**: Respects LLM provider rate limits

### Configuration

Security-related settings in `config/config.yml`:

```yaml
# API keys should be set via environment variables, not in config
llm:
  provider: "openai"
  api_key_env: "OPENAI_API_KEY"  # References environment variable
```

---

## Related Documentation

- [deployment.md](./deployment.md) - Deployment and secret setup guide
- [changelog.md](./changelog.md) - Security updates in release notes
- [GitHub Security Advisories](https://github.com/namu-k/picko-scripts/security/advisories)

---

## Security License

This project is provided as-is without warranties. See [LICENSE](LICENSE) for details.

**License**: Apache License 2.0

---

**Last Updated**: 2026-02-15

**Security Policy Version**: 1.0
