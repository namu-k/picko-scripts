# Research: Context-Driven Content Quality & Agent Interaction Protocol

**Date**: 2026-02-17
**Feature**: 001-context-interaction

## Research Summary

This document captures research findings for implementing the two-category feature: Quality (prompt improvement) and Interaction (agent-operator communication).

---

## 1. Context Variable Injection (Quality)

### 1.1 Existing Variable System

**Decision**: Extend existing `PromptComposer` and `PromptLoader` to inject structured variables.

**Rationale**:
- `picko/prompt_composer.py` already has `apply_style()`, `apply_identity()`, `apply_context()` methods
- These methods currently set limited variables (`target_audience`, `tone_voice`, `cta`, `customer_outcome`)
- Extension points are well-defined; no architectural changes needed

**Alternatives Considered**:
| Alternative | Rejected Because |
|-------------|------------------|
| Create new VariableInjector class | Adds complexity; PromptComposer already handles variable composition |
| Modify templates only | Doesn't ensure consistency across rendering paths |
| Use globals | Violates Constitution Principle I (Config-Driven) |

### 1.2 Variable Naming Convention

**Decision**: Use namespaced variable names (`account.*`, `style.*`, `channel.*`, `weekly.*`, `content.*`).

**Rationale**:
- Jinja2 supports dot notation natively
- Prevents naming collisions between context sources
- Self-documenting: `{{ account.target_audience }}` is clearer than `{{ target_audience }}`
- Consistent with existing `weekly_cta` pattern (can migrate to `weekly.cta`)

**Variable Schema**:
```yaml
account:
  one_liner: str
  target_audience: list[str]
  value_proposition: str
  pillars: list[str]
  tone_voice: dict
  bio: str
  link_purpose: str

style:
  tone: str
  sentence_style: str
  structure_patterns: list[str]
  vocabulary: list[str]
  hooks: list[str]
  closings: list[str]

channel:
  name: str
  max_length: int
  format: str
  platform_conventions: list[str]
  use_hashtags: bool

weekly:
  cta: str
  customer_outcome: str
  operator_kpi: str
  pillar_distribution: dict[str, int]

content:
  title: str
  summary: str
  key_points: list[str]
  excerpt: str
  exploration: dict | None
```

### 1.3 Rendering Path Consistency

**Decision**: Both `PromptComposer` and `PromptLoader` will use shared variable builder function.

**Implementation**:
```python
# picko/context_variables.py
def build_context_variables(
    account_id: str,
    channel: str | None = None,
    weekly_slot: WeeklySlot | None = None,
    content_data: dict | None = None
) -> dict:
    """Build complete context variable set for prompt rendering."""
    variables = {}
    variables["account"] = _load_account_variables(account_id)
    variables["style"] = _load_style_variables(account_id)
    if channel:
        variables["channel"] = _load_channel_variables(account_id, channel)
    if weekly_slot:
        variables["weekly"] = _serialize_weekly_slot(weekly_slot)
    if content_data:
        variables["content"] = content_data
    return variables
```

---

## 2. Agent-Operator Interaction Protocol

### 2.1 Interaction Point Architecture

**Decision**: Create `picko/interaction/` module with base classes and specialized handlers.

**Rationale**:
- Separation of concerns: interaction logic independent of content generation
- Testability: each interaction type can be unit tested in isolation
- Extensibility: new interaction types can be added without modifying existing code
- Follows existing pattern: `picko/` contains all core logic

**Module Structure**:
```
picko/interaction/
├── base.py           # InteractionPoint, InteractionResult, InteractionConfig
├── draft_selector.py # DraftSelectionInteraction
├── notifier.py       # NotificationInteraction
├── command_suggester.py # CommandSuggestionInteraction
└── config.py         # InteractionSettings dataclass
```

### 2.2 Primary/Fallback Communication Pattern

**Decision**: Each interaction point implements a two-tier communication strategy.

**Pattern**:
```python
class InteractionPoint(ABC):
    @abstractmethod
    def execute_primary(self, context: dict) -> InteractionResult:
        """Primary communication method."""
        pass

    @abstractmethod
    def execute_fallback(self, context: dict) -> InteractionResult:
        """Fallback when primary fails or times out."""
        pass

    def execute(self, context: dict) -> InteractionResult:
        """Try primary, fall back on failure."""
        try:
            result = self.execute_primary(context)
            if result.success:
                return result
        except Exception as e:
            logger.warning(f"Primary method failed: {e}")

        return self.execute_fallback(context)
```

### 2.3 Non-Interactive Mode Detection

**Decision**: Detect via `sys.stdin.isatty()` and environment variable `CI=true`.

**Rationale**:
- `sys.stdin.isatty()` returns `False` in piped/redirected contexts
- `CI=true` is standard convention (GitHub Actions, GitLab CI, Jenkins)
- Existing codebase uses this pattern (confirmed in scripts/)

**Implementation**:
```python
def is_interactive() -> bool:
    """Check if running in interactive mode."""
    import sys
    import os

    # Explicit non-interactive flag
    if os.environ.get("CI", "").lower() == "true":
        return False
    if os.environ.get("PICKO_NON_INTERACTIVE", "").lower() == "true":
        return False

    # Check if stdin is a TTY
    return sys.stdin.isatty()
```

### 2.4 Deadline-Based Selection

**Decision**: Store pending selections as files with deadline metadata; check on each run.

**Rationale**:
- No persistent background process required
- File-based storage compatible with Obsidian vault
- Works across process invocations (generate → later selection)
- Reminder system can be implemented as separate check script

**Storage Format**:
```markdown
---
type: draft_selection
status: pending
created_at: 2026-02-17T10:00:00
deadline: 2026-02-18T12:00:00
last_reminder: 2026-02-17T14:00:00
reminder_interval_hours: 2
account_id: socialbuilders
content_type: longform
input_id: abc123
---

# Draft Options

## Option 1 (Score: 0.85)
[Preview text...]

## Option 2 (Score: 0.82)
[Preview text...]

## Option 3 (Score: 0.78)
[Preview text...]
```

---

## 3. CLI Integration

### 3.1 Existing CLI Patterns (from exploration)

**Findings**:
- `scripts/generate_content.py` uses `argparse` with subcommand-style organization
- Common flags: `--date`, `--dry-run`, `--force`, `--type`, `--account`
- Help text follows consistent format with examples
- Exit codes: 0 = success, 1 = error, 2 = validation failure

### 3.2 New CLI Flags

**Decision**: Add flags to existing `generate_content.py` rather than create new script.

**New Flags**:
```bash
# Draft generation
--drafts N              # Generate N drafts (1-5, default: 1)
--select-draft N        # Pre-select draft N (non-interactive)
--draft-timeout HOURS   # Override default deadline

# Notifications
--notify METHOD         # Override notification method (console/log/both)
--no-notify             # Disable notifications

# Suggestions
--suggest               # Enable next command suggestions (default: on)
--no-suggest            # Disable suggestions

# Interaction mode
--non-interactive       # Force non-interactive mode
```

---

## 4. Notification System

### 4.1 Notification Channels

**Decision**: Support console output and log file as primary/fallback channels.

**Channel Priority**:
1. **Console**: Rich formatting, immediate feedback
2. **Log File**: Persistent record, searchable, works in non-interactive

**Notification Content** (per FR-014):
- Task status (success/failure)
- Items processed count
- Output location
- Errors encountered (if any)
- Timestamp

### 4.2 Notification Format

**Console Output**:
```
╭─────────────────────────────────────────╮
│ ✅ Content Generation Complete           │
├─────────────────────────────────────────┤
│ Items processed: 3                       │
│ Output: Content/Longform/2026-02-17/    │
│ Duration: 45.2s                          │
╰─────────────────────────────────────────╯

💡 Next: python -m scripts.validate_output --path Content/Longform/
```

**Log File Format**:
```json
{
  "timestamp": "2026-02-17T10:45:00",
  "event": "generation_complete",
  "status": "success",
  "items_processed": 3,
  "output_path": "Content/Longform/2026-02-17/",
  "duration_seconds": 45.2,
  "errors": []
}
```

---

## 5. Next Command Suggestion

### 5.1 Context-Aware Suggestions

**Decision**: Suggest commands based on workflow state analysis.

**Suggestion Rules**:
| Condition | Suggested Command |
|-----------|-------------------|
| Content generated successfully | `python -m scripts.validate_output --path {output}` |
| Validation passed | `python -m scripts.publish_log --content {path}` |
| Validation failed | `python -m scripts.retry_failed --date {date}` |
| Drafts pending selection | `python -m scripts.select_draft --list` |
| Items require review | Review digest at `Inbox/Inputs/_digests/{date}.md` |

### 5.2 Fallback File Format

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

---

## 6. Testing Strategy

### 6.1 Unit Tests

| Module | Test Focus |
|--------|------------|
| `context_variables.py` | Variable building, missing fields fallback |
| `draft_selector.py` | Selection logic, timeout, auto-select |
| `notifier.py` | Channel selection, fallback behavior |
| `command_suggester.py` | Context analysis, suggestion accuracy |

### 6.2 Integration Tests

| Scenario | Test |
|----------|------|
| End-to-end draft generation | Run with `--drafts 3`, verify 3 options created |
| Non-interactive mode | Run with `--non-interactive`, verify no prompts |
| Notification fallback | Simulate console failure, verify log written |
| Context injection | Generate content, verify variables in prompt |

### 6.3 Test Fixtures

```python
# tests/conftest.py additions
@pytest.fixture
def interaction_config():
    return InteractionConfig(
        draft_max_count=5,
        draft_deadline_hours=24,
        reminder_interval_hours=2,
        notification_primary="console",
        notification_fallback="log"
    )

@pytest.fixture
def sample_draft_options():
    return [
        DraftOption(content_text="Draft 1...", quality_score=0.85),
        DraftOption(content_text="Draft 2...", quality_score=0.82),
        DraftOption(content_text="Draft 3...", quality_score=0.78),
    ]
```

---

## 7. Dependencies

### 7.1 No New External Dependencies

All functionality can be implemented using existing dependencies:
- `argparse`: CLI argument parsing (existing)
- `jinja2`: Template rendering (existing)
- `pyyaml`: Configuration loading (existing)
- `loguru`: Logging (existing via `picko.logger`)

### 7.2 Internal Dependencies

| New Module | Depends On |
|------------|------------|
| `context_variables.py` | `account_context.py`, `config.py` |
| `interaction/base.py` | `logger.py`, `config.py` |
| `interaction/draft_selector.py` | `vault_io.py`, `interaction/base.py` |
| `interaction/notifier.py` | `logger.py`, `interaction/base.py` |
| `interaction/command_suggester.py` | `interaction/base.py` |

---

## 8. Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Draft scoring algorithm | Deferred to implementation phase; start with existing `scoring.py` weights |
| Deadline time format | Use `deadline_time: "12:00"` in config for next-day lunchtime |
| Reminder mechanism | File-based with timestamp check; separate check script for cron |
| Variable migration | New templates use `account.*` style; existing templates migrate incrementally |

---

## References

- Feature Spec: `specs/001-context-interaction/spec.md`
- Constitution: `.specify/memory/constitution.md`
- Existing Prompt System: `picko/prompt_composer.py`, `picko/prompt_loader.py`
- Account Context: `picko/account_context.py`
- Vault I/O: `picko/vault_io.py`
