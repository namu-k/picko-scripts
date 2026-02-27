# Deployment Guide

This guide covers setting up Picko for local development and CI/CD deployment.

## Table of Contents

- [Local Setup](#local-setup)
- [GitHub Actions Setup](#github-actions-setup)
- [Auto Collection Workflow](#auto-collection-workflow)
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
| `RELAY_API_KEY` | Relay provider API key | Optional |
| `TAVILY_API_KEY` | Tavily API key (for web search) | Optional |
| `UNSPLASH_ACCESS_KEY` | Unsplash API key (for images) | Optional |
| `UNSPLASH_SECRET_KEY` | Unsplash API secret | Optional |
| `PEXELS_API_KEY` | Pexels API key (for images) | Optional |
---

### 3. Tavily API Key

**Tavily** provides web search capabilities for content discovery and source discovery.

**Required for**: Source discovery and web-based content collection

1. Go to [https://tavily.com](https://tavily.com)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key

### 4. Relay API Key (Optional)

**Relay** is an LLM provider that can be used as a fallback or alternative to OpenAI/Anthropic.

**Required for**: Using Relay provider for LLM requests

1. Go to [https://relay.app](https://relay.app)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key

### 5. Unsplash API Key (Optional)

**Unsplash** provides high-quality stock photos for multimedia templates.

**Required for**: Photogram style background images

1. Go to [https://unsplash.com/developers](https://unsplash.com/developers)
2. Sign in or create an account
3. Create a new application
4. Copy the **Access Key** and **Secret Key**

**Rate Limits**: 50 requests/hour (free tier)

### 6. Pexels API Key (Optional)

**Pexels** provides free stock photos and videos.

**Required for**: Alternative image source for Photogram style

1. Go to [https://www.pexels.com/api/](https://www.pexels.com/api/)
2. Sign in or create an account
3. Create a new application
4. Copy the **API Key**

**Rate Limits**: 200 requests/hour (free tier)

---

---

## Auto Collection Workflow

> **파일**: `.github/workflows/auto_collect.yml`

### 스케줄

| Job | 트리거 | 실행 시각 (KST) |
|-----|--------|----------------|
| `daily-collect` | `cron: '0 23 * * *'` | 매일 08:00 |
| `weekly-discover` | `cron: '0 21 * * 0'` | 매주 일요일 06:00 |

### 필요한 GitHub Secrets

아래 3개를 모두 Repository Settings → Secrets and variables → Actions에 추가해야 합니다.

| Secret | 용도 | 필수 여부 |
|--------|------|----------|
| `OPENAI_API_KEY` | daily-collect LLM 요약·생성 | **필수** |
| `TAVILY_API_KEY` | weekly-discover 웹 검색 | **필수** |
| `RELAY_API_KEY` | Relay LLM 폴백 | 선택 |

### workflow_dispatch 수동 실행 방법

스케줄을 기다리지 않고 즉시 실행하려면:

1. GitHub 리포지토리 → **Actions** 탭 이동
2. 좌측 워크플로우 목록에서 **Daily Collection & Weekly Discovery** 클릭
3. 우측 **Run workflow** 드롭다운 클릭
4. 브랜치 확인 후 **Run workflow** 클릭
5. 상단 목록에 실행 중인 항목이 나타나면 클릭하여 로그 확인

> **참고**: `workflow_dispatch`로 수동 실행하면 `daily-collect` job만 실행됩니다.
> (`weekly-discover`는 일요일 cron에만 실행)

### 로컬 사전 검증

```bash
# 워크플로우 YAML 문법 검사
python -c "import yaml; yaml.safe_load(open('.github/workflows/auto_collect.yml', encoding='utf-8')); print('OK')"

# daily-collect 동작 확인 (dry-run)
python -m scripts.daily_collector --account socialbuilders --dry-run

# source discovery 동작 확인
python -m scripts.source_discovery --account socialbuilders --dry-run
```

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
|| `TAVILY_API_KEY` | Tavily API key for web search | - |

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
|| Verify all API keys are set
python -c "import os; print('OpenAI:', os.getenv('OPENAI_API_KEY') or 'NOT FOUND')"
python -c "import os; print('Tavily:', os.getenv('TAVILY_API_KEY') or 'NOT FOUND')"
python -c "import os; print('Relay:', os.getenv('RELAY_API_KEY') or 'NOT FOUND')"

|# Test health check
python -m scripts.health_check
||

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
