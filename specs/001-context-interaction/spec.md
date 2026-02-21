# Feature Specification: Context-Driven Content Quality & Agent Interaction Protocol

**Feature Branch**: `001-context-interaction`
**Created**: 2026-02-17
**Status**: Draft
**Input**: User description: "품질 요구사항 — 롱폼/팩/이미지 프롬프트에 계정·채널·스타일 변수 반영. (2) 인터랙션 요구사항 — 에이전트-운영자 소통이 필요한 모든 지점마다 적절한 소통 방법과 폴백 소통 방법 마련."

## Clarifications

### Session 2026-02-17

- Q: What should be the default timeout for operator draft selection? → A: Deadline-based system: next-day lunchtime (configurable), with 2-hour reminder intervals when no response (configurable).
- Q: What is the maximum number of drafts the system should support? → A: 5 drafts maximum.
- Q: How should draft quality be scored for auto-selection? → A: Deferred — scoring.py exists but context-aware scoring (by field, target) is needed; exact algorithm not yet decided.

---

## Scope Definition

### In Scope
- Variable injection system for account, channel, and style context into all content types (longform, packs, image prompts)
- Agent-operator interaction protocol with primary and fallback communication methods
- Draft generation with operator selection workflow
- Notification and completion signaling system
- Next command suggestion mechanism at workflow completion

### Out of Scope
- Publishing API integrations
- Dashboard UI development
- Automated regression testing framework

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Context-Aware Content Generation (Priority: P1)

**As an** operator running the content generation pipeline,
**I want** all generated content (longform, packs, image prompts) to automatically reflect my account identity, channel specifications, and writing style,
**So that** content is consistently on-brand without manual editing.

**Why this priority**: This is the core quality improvement. Without proper context injection, generated content lacks brand consistency and requires significant manual post-processing. This directly impacts operator productivity and content quality.

**Independent Test**: Can be fully tested by running `generate_content` with a specific account profile and verifying that all output files contain elements matching the account's identity (tone, audience), channel specs (length, format), and style characteristics.

**Acceptance Scenarios**:

1. **Given** an account profile with defined target_audience, tone_voice, and pillars, **When** generating longform content for that account, **Then** the generated content must reference these context variables in the prompt and the output must reflect them.

2. **Given** a style profile with defined characteristics (tone, sentence_style, structure_patterns), **When** generating any content type, **Then** the style profile must be injected into the prompt as structured variables (not just as a text section).

3. **Given** multiple channels (Twitter, LinkedIn, Newsletter) with different specifications, **When** generating pack content for each channel, **Then** each pack must receive channel-specific variables (max_length, format, platform_conventions).

4. **Given** a weekly slot with cta, customer_outcome, and pillar_distribution, **When** generating content for that week, **Then** all content types must receive these weekly context variables.

---

### User Story 2 - Draft Selection Workflow (Priority: P1)

**As an** operator reviewing generated content,
**I want** the agent to generate multiple draft options and let me select the best one,
**So that** I can choose the most appropriate output without re-running the entire pipeline.

**Why this priority**: This addresses a critical pain point in the current workflow where a single output may not meet quality expectations. Multiple drafts with selection capability significantly improves output quality and operator satisfaction.

**Independent Test**: Can be fully tested by running content generation with `--drafts N` flag and verifying that N options are presented and operator can select one which is then saved.

**Acceptance Scenarios**:

1. **Given** the operator requests content generation with `--drafts 3`, **When** the generation completes, **Then** 3 distinct draft options must be presented to the operator.

2. **Given** multiple drafts are generated, **When** the operator selects draft #2, **Then** only draft #2 is saved to the output location and the others are discarded.

3. **Given** draft selection is enabled but the operator does not respond within the deadline window, **Then** the system must send periodic reminders (default: every 2 hours) until the deadline passes or selection is made.

4. **Given** the operator is unavailable, **When** running in unattended mode, **Then** the system must skip draft selection and save the highest-scored draft automatically.

---

### User Story 3 - Notification & Completion Signaling (Priority: P2)

**As an** operator running long-running content generation tasks,
**I want** to receive notifications when tasks complete or require attention,
**So that** I don't have to actively monitor the process.

**Why this priority**: Enables asynchronous workflow management. Operators can start tasks and be notified when attention is needed, improving productivity.

**Independent Test**: Can be fully tested by running content generation and verifying that completion notifications are sent through the configured channel.

**Acceptance Scenarios**:

1. **Given** content generation starts, **When** the task completes successfully, **Then** a completion signal must be sent via the primary notification method.

2. **Given** content generation encounters an error requiring operator attention, **When** the error occurs, **Then** an alert must be sent via the primary notification method with error details.

3. **Given** the primary notification method fails, **When** sending notification, **Then** the fallback notification method must be attempted.

4. **Given** all notification methods fail, **When** the task completes, **Then** the completion status must be logged persistently for later review.

---

### User Story 4 - Next Command Suggestion (Priority: P2)

**As an** operator completing a workflow step,
**I want** the agent to suggest relevant next commands,
**So that** I can continue the workflow efficiently without consulting documentation.

**Why this priority**: Reduces cognitive load and improves workflow continuity. Operators receive contextual guidance for next steps.

**Independent Test**: Can be fully tested by completing a content generation run and verifying that relevant next command suggestions are presented.

**Acceptance Scenarios**:

1. **Given** content generation completes with auto_ready items, **When** the run finishes, **Then** the agent must suggest the validate command as a next step.

2. **Given** content generation completes with items requiring review, **When** the run finishes, **Then** the agent must suggest reviewing the digest file.

3. **Given** validation fails, **When** reporting the failure, **Then** the agent must suggest the retry command with appropriate parameters.

4. **Given** next command suggestion fails to display, **When** the task completes, **Then** a fallback text file with suggestions must be created in the logs directory.

---

### Edge Cases

- What happens when account profile is missing required fields (target_audience, pillars)?
  - System must use default values from a fallback profile and log a warning.

- What happens when style profile file is corrupted or missing expected keys?
  - System must skip style injection and continue with base prompt, logging the issue.

- What happens when operator doesn't respond to draft selection within the deadline?
  - System must send reminders at configured intervals (default: 2 hours). If deadline passes without response in non-interactive mode, auto-select based on scoring (algorithm TBD per context) or save all drafts with clear labeling.

- What happens when both primary and fallback notification methods fail?
  - System must write a persistent notification record to a designated file that can be checked later.

- What happens when running in a non-interactive environment (CI/CD, scheduled task)?
  - System must detect non-interactive mode and use automated decision-making for all interaction points.

- What happens when channel configuration is missing for a requested pack type?
  - System must skip that channel and log a warning, continuing with available channels.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Context Variable Injection

- **FR-001**: System MUST inject account identity variables (one_liner, target_audience, value_proposition, pillars, tone_voice, bio) into all prompt types as structured template variables.

- **FR-002**: System MUST inject style profile variables (tone, sentence_style, structure_patterns, vocabulary, hooks, closings) into all prompt types as a structured object, not just as embedded text.

- **FR-003**: System MUST inject channel-specific variables (channel name, max_length, format requirements, platform conventions, use_hashtags flag) into pack and image prompts.

- **FR-004**: System MUST inject weekly slot variables (cta, customer_outcome, operator_kpi, pillar_distribution) into all content types when a weekly slot is active.

- **FR-005**: System MUST use a consistent variable naming convention across all prompt templates (e.g., `account.*`, `style.*`, `channel.*`, `weekly.*`, `content.*`).

- **FR-006**: System MUST support both PromptComposer (layered) and PromptLoader (direct) rendering paths with identical variable availability.

#### Draft Selection Workflow

- **FR-007**: System MUST support a `--drafts N` CLI flag to generate N draft options (maximum 5) instead of a single output.

- **FR-008**: System MUST present generated drafts to the operator with sufficient context for selection (preview text, scores, key differences).

- **FR-009**: System MUST support operator selection via interactive prompt (primary) and CLI flag specification (fallback).

- **FR-010**: System MUST implement a deadline-based selection window (default: next-day lunchtime, configurable) with periodic reminders (default: every 2 hours, configurable) when no response is received.

- **FR-011**: System MUST save only the selected draft to the final output location, discarding unselected drafts.

#### Notification System

- **FR-012**: System MUST send completion notifications through a configurable primary channel (default: console output with completion summary).

- **FR-013**: System MUST support at least one fallback notification channel (default: log file entry).

- **FR-014**: System MUST include in notifications: task status (success/failure), items processed count, output location, any errors encountered.

- **FR-015**: System MUST log notification attempts and outcomes for troubleshooting.

#### Next Command Suggestion

- **FR-016**: System MUST analyze the completed workflow state to determine contextually relevant next commands.

- **FR-017**: System MUST display next command suggestions via the primary interaction method (console output).

- **FR-018**: System MUST write next command suggestions to a fallback file when primary display fails.

- **FR-019**: System MUST base suggestions on: content generated, validation status, pending items, and workflow position.

#### Non-Interactive Mode

- **FR-020**: System MUST detect non-interactive execution environments and bypass interactive prompts automatically.

- **FR-021**: System MUST use predetermined defaults or scoring-based decisions in non-interactive mode.

---

### Key Entities

- **ContextVariableSet**: A structured collection of variables for prompt templating, containing account, style, channel, weekly, and content sub-objects. Each sub-object has defined schemas for its fields.

- **InteractionPoint**: A defined moment in the workflow where agent-operator communication occurs. Each point has: interaction_type (selection/notification/suggestion), primary_method, fallback_method, deadline (default: next-day lunchtime, configurable), reminder_interval (default: 2 hours, configurable), auto_action.

- **DraftOption**: A single generated content candidate. Contains: content_text, generation_metadata (model used, tokens), quality_score (algorithm TBD — context-aware scoring needed), preview_excerpt, selection_rank.

- **NotificationRecord**: A persistent record of a notification attempt. Contains: timestamp, notification_type, channel_used, success_status, message_content, retry_count.

- **WorkflowState**: Snapshot of the workflow at any point. Contains: completed_steps, pending_items, errors_encountered, suggested_next_commands, interaction_points_requiring_attention.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All generated content types (longform, packs, image) must include at least 5 context variables from the account/style/channel/weekly sources, verifiable by template variable presence in the prompt.

- **SC-002**: Draft selection workflow must reduce manual re-generation requests by at least 50% (measured by comparing before/after implementation metrics).

- **SC-003**: Operators must be able to select from generated drafts within the configured deadline window (default: by next-day lunchtime), with the selection recorded correctly.

- **SC-004**: Notification delivery success rate must exceed 95% across primary and fallback channels combined.

- **SC-005**: Next command suggestions must be contextually relevant (match operator's actual next action) in at least 80% of completed workflows.

- **SC-006**: Non-interactive mode must complete end-to-end without blocking, with all interaction points resolved automatically.

- **SC-007**: The system must handle missing context gracefully—content generation must not fail when optional context is unavailable, only log warnings.

- **SC-008**: Template variable injection must be consistent across both rendering paths (PromptComposer and PromptLoader), verified by identical variable presence in test prompts.

---

## Assumptions

1. **Account profiles** exist in `config/accounts/` with standard structure including `target_audience`, `pillars`, and `style_name` fields.

2. **Style profiles** exist in `config/reference_styles/{style_name}/profile.yml` with standard characteristic keys.

3. **Channel configurations** are defined in account profiles under a `channels` key with per-channel settings.

4. **Operators** have access to the system via CLI or can monitor log files for fallback notifications.

5. **Non-interactive detection** can be reliably performed via environment variables (CI=true) or TTY availability checks.

6. **Prompt templates** in `config/prompts/` will be updated to use the new structured variable naming convention.

---

## Dependencies

- Existing `picko/account_context.py` module for identity and style loading
- Existing `picko/prompt_composer.py` for multi-layer prompt composition
- Existing `picko/prompt_loader.py` for direct template rendering
- Existing `scripts/generate_content.py` for content generation orchestration
- Configuration files in `config/` directory (accounts, sources, prompts)
