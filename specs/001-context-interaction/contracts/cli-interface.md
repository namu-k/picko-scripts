# CLI Interface Contract: Context-Driven Content Quality & Agent Interaction Protocol

**Feature**: 001-context-interaction
**Date**: 2026-02-17

## Overview

This document defines the CLI contract for the interaction system, including new flags, exit codes, and output formats.

---

## 1. generate_content.py Extensions

### 1.1 New CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--drafts N` | int | 1 | Generate N draft options (1-5) |
| `--select-draft N` | int | None | Pre-select draft N (bypasses interactive selection) |
| `--draft-timeout HOURS` | int | 24 | Override draft selection deadline |
| `--notify METHOD` | str | console | Notification method (console/log/both) |
| `--no-notify` | flag | - | Disable all notifications |
| `--suggest` | flag | enabled | Enable next command suggestions |
| `--no-suggest` | flag | - | Disable next command suggestions |
| `--non-interactive` | flag | - | Force non-interactive mode |

### 1.2 Usage Examples

```bash
# Generate 3 drafts with interactive selection
python -m scripts.generate_content --drafts 3

# Generate 3 drafts, pre-select draft 2 (non-interactive)
python -m scripts.generate_content --drafts 3 --select-draft 2

# Generate with log-only notifications
python -m scripts.generate_content --drafts 2 --notify log

# Run completely non-interactive (for CI/CD)
python -m scripts.generate_content --non-interactive --drafts 3 --select-draft 1 --notify log --no-suggest

# Custom draft timeout (8 hours instead of 24)
python -m scripts.generate_content --drafts 3 --draft-timeout 8
```

### 1.3 Exit Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 0 | Success | All content generated successfully |
| 1 | Error | LLM error, file I/O error, config error |
| 2 | Validation failure | Input validation failed |
| 3 | Draft selection pending | Drafts generated but awaiting selection |
| 4 | Deadline expired | Draft deadline passed without selection |

### 1.4 Standard Output Format

#### Successful Generation (Single Draft)
```
✅ Content Generation Complete
   Account: socialbuilders
   Type: longform
   Output: Content/Longform/2026-02-17/article-001.md
   Duration: 12.3s

💡 Next: python -m scripts.validate_output --path Content/Longform/2026-02-17/
```

#### Draft Generation (Multiple Options)
```
📝 Generated 3 Draft Options

┌─────────────────────────────────────────────────────────────┐
│ Option 1 (Score: 0.85)                                       │
│ This article explores the transformative potential of AI...  │
│ [200 more characters...]                                     │
├─────────────────────────────────────────────────────────────┤
│ Option 2 (Score: 0.82)                                       │
│ In today's rapidly evolving tech landscape, understanding... │
│ [200 more characters...]                                     │
├─────────────────────────────────────────────────────────────┤
│ Option 3 (Score: 0.78)                                       │
│ The intersection of AI and content creation represents...    │
│ [200 more characters...]                                     │
└─────────────────────────────────────────────────────────────┘

Select draft (1-3) or 'q' to quit: _
```

#### Non-Interactive Mode
```
[2026-02-17 10:00:00] INFO: Starting content generation (non-interactive mode)
[2026-02-17 10:00:05] INFO: Generated draft 1/3 for input abc123
[2026-02-17 10:00:10] INFO: Generated draft 2/3 for input abc123
[2026-02-17 10:00:15] INFO: Generated draft 3/3 for input abc123
[2026-02-17 10:00:15] INFO: Auto-selected draft 1 (score: 0.85)
[2026-02-17 10:00:15] INFO: Saved to Content/Longform/2026-02-17/article-001.md
```

---

## 2. Draft Selection Workflow

### 2.1 Interactive Selection

**Primary Method**: Terminal prompt with keyboard input

```
Select draft (1-3) or 'q' to quit: 2

✅ Selected draft 2
   Saved to: Content/Longform/2026-02-17/article-001.md
```

**Fallback Method**: CLI flag `--select-draft N`

```bash
python -m scripts.generate_content --drafts 3 --select-draft 2
```

### 2.2 Deadline-Based Selection

When drafts are generated without immediate selection:

```
⏳ Draft selection pending
   Deadline: 2026-02-18 12:00 (23 hours remaining)
   Selection ID: sel_a1b2c3

To select later:
  python -m scripts.select_draft --id sel_a1b2c3 --select 1

To list pending selections:
  python -m scripts.select_draft --list
```

### 2.3 Reminder Output (Periodic)

```
⏰ Reminder: Draft selection pending
   3 drafts awaiting selection
   Deadline: 2026-02-18 12:00 (4 hours remaining)

   python -m scripts.select_draft --id sel_a1b2c3 --list
```

---

## 3. Notification System

### 3.1 Console Notification Format

**Success**:
```
╭─────────────────────────────────────────╮
│ ✅ Content Generation Complete           │
├─────────────────────────────────────────┤
│ Items processed: 3                       │
│ Output: Content/Longform/2026-02-17/    │
│ Duration: 45.2s                          │
│ Errors: 0                                │
╰─────────────────────────────────────────╯
```

**Error**:
```
╭─────────────────────────────────────────╮
│ ❌ Content Generation Failed             │
├─────────────────────────────────────────┤
│ Error: OpenAI API rate limit exceeded    │
│ Items processed: 1/3                     │
│ Partial output: Content/Longform/...     │
╰─────────────────────────────────────────╯
```

### 3.2 Log File Format

**Location**: `logs/notifications_YYYY-MM-DD.jsonl`

```json
{"id":"a1b2c3","timestamp":"2026-02-17T10:45:00","notification_type":"completion","channel_used":"console","success":true,"task_status":"success","items_processed":3,"output_location":"Content/Longform/2026-02-17/","duration_seconds":45.2}
{"id":"d4e5f6","timestamp":"2026-02-17T11:00:00","notification_type":"error","channel_used":"console","success":true,"task_status":"failure","error":"Rate limit exceeded"}
```

### 3.3 Fallback File Format

**Location**: `logs/notification_fallback_{timestamp}.txt`

```text
NOTIFICATION FALLBACK RECORD
============================
Timestamp: 2026-02-17T10:45:00
Type: completion
Status: success

Items processed: 3
Output location: Content/Longform/2026-02-17/
Duration: 45.2s

Primary channel: console (FAILED)
Fallback channel: file (SUCCESS)
```

---

## 4. Next Command Suggestions

### 4.1 Terminal Display Format

**Primary Method**: Direct terminal output

```
💡 Suggested Next Commands:

1. Validate generated content:
   python -m scripts.validate_output --path Content/Longform/2026-02-17/

2. Review generated files:
   ls Content/Longform/2026-02-17/

3. If validation passes, create publish log:
   python -m scripts.publish_log --date 2026-02-17
```

### 4.2 Fallback File Format

**Location**: `logs/suggestions_{timestamp}.txt`

```text
# Suggested Next Commands
Generated: 2026-02-17T10:45:00
Run ID: gen_20260217_104500

1. Validate output:
   python -m scripts.validate_output --path Content/Longform/2026-02-17/

2. Review generated content:
   ls Content/Longform/2026-02-17/

3. If validation passes, create publish log:
   python -m scripts.publish_log --date 2026-02-17
```

### 4.3 Context-Aware Suggestions

| Workflow State | Suggested Command |
|----------------|-------------------|
| Content generated, no validation | `validate_output --path {output}` |
| Validation passed | `publish_log --date {date}` |
| Validation failed | `retry_failed --date {date}` |
| Drafts pending selection | `select_draft --list` |
| Items require review | Review digest at `{digest_path}` |
| Errors occurred | Check logs at `{log_path}` |

---

## 5. Environment Variables

| Variable | Values | Effect |
|----------|--------|--------|
| `CI` | `true` | Forces non-interactive mode |
| `PICKO_NON_INTERACTIVE` | `true` | Forces non-interactive mode |
| `PICKO_NOTIFY_METHOD` | `console/log/both` | Overrides notification method |
| `PICKO_NO_SUGGEST` | `true` | Disables command suggestions |

---

## 6. Configuration Schema (config.yml)

```yaml
interaction:
  draft:
    max_count: 5                    # Maximum drafts (FR-007)
    deadline_hours: 24              # Default deadline
    deadline_time: "12:00"          # Specific deadline time
    reminder_interval_hours: 2      # Reminder frequency (FR-010)
    auto_select_on_deadline: true   # Auto-select on deadline
    scoring_algorithm: "default"    # Future: context-aware

  notification:
    primary: "console"              # console | log | both
    fallback: "log"                 # log | file
    include_details: true           # Include full details
    fallback_file: "logs/notifications.jsonl"

  suggestion:
    primary: "terminal"             # terminal | file | both
    fallback_file: "logs/suggestions.txt"
    context_aware: true             # Use workflow state
```

---

## 7. Backward Compatibility

### 7.1 Default Behavior (No New Flags)

```bash
python -m scripts.generate_content
```

This behaves exactly as before:
- Generates single draft (implicit `--drafts 1`)
- No interactive prompts
- Console output unchanged
- No suggestions displayed (opt-in feature)

### 7.2 Migration Path

| Old Behavior | New Equivalent |
|--------------|----------------|
| Single draft | `--drafts 1` (default) |
| No interaction | `--non-interactive` (auto-detected in CI) |
| Console output only | `--notify console` (default) |

---

## 8. Error Messages

### 8.1 Draft-Related Errors

```
Error: Invalid draft count '6'
  Maximum drafts: 5
  Usage: --drafts N (where N is 1-5)
```

```
Error: Invalid draft selection '4'
  Available drafts: 1-3
  Usage: --select-draft N (where N is 1-3)
```

```
Error: Draft selection expired
  Selection ID: sel_a1b2c3
  Deadline: 2026-02-18 12:00
  Status: expired

  To regenerate drafts:
    python -m scripts.generate_content --force
```

### 8.2 Configuration Errors

```
Error: Invalid notification method 'email'
  Valid options: console, log, both
  Config: interaction.notification.primary
```

### 8.3 Environment Errors

```
Warning: Non-interactive mode detected (CI=true)
  Draft selection: auto (highest score)
  Notifications: log only
  Suggestions: disabled
```
