# Monitoring and Alerting Plan

## Overview
This document defines the monitoring strategy for the Picko content pipeline.

## CI/CD Monitoring

### GitHub Actions Monitoring
- **Location**: `.github/workflows/test.yml`
- **Frequency**: On every push and PR
- **Alerts**: GitHub Actions notifications (built-in)

### Daily Health Check Workflow (Recommended Addition)

Create `.github/workflows/health_check.yml`:

```yaml
name: Daily Health Check

on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8:00 AM UTC
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run health check
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python -m scripts.health_check

      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.name,
              title: '🚨 Daily Health Check Failed',
              body: 'The scheduled health check workflow failed. Please investigate.'
            })
```

## Local Monitoring

### Log Files
- **Location**: `logs/YYYY-MM-DD/*.log`
- **Key files to monitor**:
  - `daily_collector.log` - RSS ingestion issues
  - `generate_content.log` - Content generation failures
  - `errors.log` - All errors aggregated

### Health Check Script

Run manually or via cron:

```bash
# Check all systems
python -m scripts.health_check

# Get JSON output for automation
python -m scripts.health_check --json > health_status.json
```

### Validation Script

Validate generated content:

```bash
python -m scripts.validate_output --path Content/ --recursive --verbose
```

## Alerting Channels

### Email Notifications (Setup Required)

Modify health check to send email on critical failures:

```python
# Add to picko/logger.py or scripts/health_check.py
import smtplib
from email.message import EmailMessage

def send_alert(subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'picko@example.com'
    msg['To'] = 'admin@example.com'
    msg.set_content(body)

    smtp = smtplib.SMTP('smtp.example.com', 587)
    smtp.send_message(msg)
    smtp.quit()
```

### Slack Integration (Optional)

Create Slack incoming webhook and add to health_check.py:

```python
def notify_slack(message):
    import requests
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={'text': message})
```

## Metrics to Track

### Pipeline Health Metrics
| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| RSS sources accessible | 100% | <90% |
| Daily collector success rate | >95% | <90% |
| Content generation success rate | >95% | <85% |
| API key configured | ✅ | ❌ |
| Vault access | ✅ | ❌ |
| Disk space available | >1GB | <500MB |

### Quality Metrics
| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Test coverage | >80% | <70% |
| Flake8 warnings | 0 | >10 |
| Mypy errors | 0 (strict) | >5 |

## Incident Response

### Severity Levels

**P1 - Critical** (Immediate action required)
- Vault inaccessible
- API keys compromised
- All content generation failing
- Security vulnerability detected

**P2 - High** (Action within 4 hours)
- Multiple RSS sources down
- New content not being collected
- Test suite failing

**P3 - Medium** (Action within 24 hours)
- Single RSS source down
- Coverage dropped below threshold
- Lint errors introduced

**P4 - Low** (Action within 1 week)
- Documentation updates needed
- Minor code quality improvements

### Escalation Path

1. **Automated Alert** → GitHub Issue/Slack message
2. **Triage** → Assign to maintainer (P1/P2), backlog for P3/P4
3. **Resolution** → Fix deployed, tested, and merged
4. **Post-Mortem** → For P1/P2, document incident in docs/incidents/

## Recommended Tools

- **Logging**: loguru (already configured)
- **Metrics**: Optional - Prometheus/Grafana setup
- **Uptime Monitoring**: UptimeRobot or similar for RSS sources
- **Error Tracking**: Optional - Sentry integration

---

*Document version: 0.2.0*
*Last updated: 2026-02-15*
