# Deployment Guide

This guide covers setting up Picko for local development and CI/CD deployment.

## Table of Contents

- [Local Setup](#local-setup)
- [GitHub Actions Setup](#github-actions-setup)
- [Environment Variables Reference](#environment-variables-reference)
- [Troubleshooting](#troubleshooting)

---

## Local Setup

### 1. OpenAI API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### 2. Set Environment Variable

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-actual-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-your-actual-key-here"
```

**macOS/Linux:**
```bash
export OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Persistent Configuration (Optional)

**Windows - Set User Environment Variable:**
```powershell
setx OPENAI_API_KEY "sk-your-actual-key-here"
```

**macOS/Linux - Add to ~/.bashrc or ~/.zshrc:**
```bash
echo 'export OPENAI_API_KEY="sk-your-actual-key-here"' >> ~/.bashrc
source ~/.bashrc
```

---

## GitHub Actions Setup

### Setting Up GitHub Secrets

GitHub Actions requires the API key to be stored as a repository secret. This keeps your credentials secure and never exposes them in logs.

#### Step 1: Navigate to Repository Settings

1. Go to your repository on GitHub
2. Click **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**

#### Step 2: Add New Secret

1. Click **New repository secret**
2. Fill in the form:
   - **Name**: `OPENAI_API_KEY`
   - **Secret**: `sk-your-actual-key-here` (paste your actual key)
3. Click **Add secret**

#### Step 3: Verify Secret is Set

The secret should now appear in the list with:
- Name: `OPENAI_API_KEY`
- Updated: [timestamp]
- Visibility: Visible to workflows with read access

### How the Workflow Uses the Secret

The `.github/workflows/test.yml` workflow references the secret:

```yaml
- name: Run pytest
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY || 'dummy_key_for_testing' }}
  run: |
    pytest tests/ --cov=picko --cov-report=xml
```

**Key points:**
- The secret is injected as an environment variable during workflow execution
- A fallback dummy key is used if the secret isn't set (for testing)
- Secrets are never printed to logs by GitHub Actions

### Additional Secrets (Optional)

For other LLM providers, you may want to add these secrets as well:

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude) | Optional |
| `OLLAMA_BASE_URL` | Ollama instance URL | Optional (if using self-hosted) |

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | `sk-proj-...` |
| `PICKO_VAULT_ROOT` | Override vault path (optional) | `/path/to/vault` |

### Optional LLM Provider Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | - |
| `OLLAMA_HOST` | Ollama host URL | `http://localhost:11434` |

### Configuration Override Pattern

Any config value can be overridden with environment variables using the `PICKO_` prefix:

```bash
# Override vault.root
export PICKO_VAULT_ROOT="/custom/vault/path"

# Override LLM model
export PICKO_LLM_MODEL="gpt-4o"

# Override scoring threshold
export PICKO_SCORING_THRESHOLDS_AUTO_APPROVE="0.9"
```

---

## Troubleshooting

### Error: "OPENAI_API_KEY not found"

**Symptoms:**
```
Error: OPENAI_API_KEY environment variable not found
```

**Solutions:**
1. Verify the environment variable is set: `echo $OPENAI_API_KEY`
2. For local: Set the variable in your current shell
3. For GitHub: Check the secret is correctly named `OPENAI_API_KEY` (case-sensitive)

### Error: "Invalid API key"

**Symptoms:**
```
Error: Incorrect API key provided
```

**Solutions:**
1. Verify the key starts with `sk-`
2. Check the key hasn't been revoked or expired
3. Ensure you're using the correct key for the environment (test vs production)

### GitHub Actions Fails with Authentication Error

**Symptoms:**
- Tests fail in CI but pass locally
- Error mentions authentication or API key

**Solutions:**
1. Go to Repository Settings → Secrets and variables → Actions
2. Verify `OPENAI_API_KEY` secret exists
3. If missing, re-add the secret with the correct value
4. Re-run the workflow

### Workflow Times Out During Tests

**Symptoms:**
- Tests hang indefinitely
- Workflow exceeds time limit

**Solutions:**
1. Check if OpenAI API is accessible from GitHub Actions runners
2. Consider using a mock API key for unit tests
3. Add timeout to test steps in workflow

### Security Best Practices

1. **Never commit API keys** to the repository
2. **Use different keys** for development and production
3. **Rotate keys regularly** (OpenAI allows key rotation)
4. **Monitor usage** on OpenAI dashboard for unusual activity
5. **Set spending limits** on your OpenAI account

### Checking Your Setup

**Local:**
```bash
# Verify API key is set
python -c "import os; print('API Key found' if os.getenv('OPENAI_API_KEY') else 'API Key NOT found')"

# Test health check
python -m scripts.health_check
```

**GitHub Actions:**
1. Go to Actions tab in your repository
2. Click on a recent workflow run
3. Check the "Run pytest" step logs
4. Look for "✓ No API keys found in source code" (security check passed)
5. Verify tests pass with API key injected

---

## Further Reading

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [USER_GUIDE.md](USER_GUIDE.md) - Usage instructions
- [CLAUDE.md](CLAUDE.md) - Developer guide
