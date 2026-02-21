# Data Model: Context-Driven Content Quality & Agent Interaction Protocol

**Feature**: 001-context-interaction
**Date**: 2026-02-17

## Overview

This document defines the data entities for four functional areas:
1. **프롬프트/계정/채널/스타일** (Prompts/Account/Channel/Style) - Context variables
2. **에이전트-운영자 소통** (Agent-Operator Communication) - Interaction points
3. **초안** (Drafts) - Draft selection workflow
4. **알림** (Notifications) - Notification system

---

## 1. Context Variables Module (프롬프트/계정/채널/스타일)

### 1.1 ContextVariableSet

Root container for all template variables injected into prompts.

```python
@dataclass
class ContextVariableSet:
    """Complete set of context variables for prompt rendering."""

    account: AccountVariables          # 계정 컨텍스트
    style: StyleVariables              # 스타일 컨텍스트
    channel: ChannelVariables | None   # 채널 컨텍스트 (optional)
    weekly: WeeklyVariables | None     # 주간 슬롯 컨텍스트 (optional)
    content: ContentVariables          # 콘텐츠 데이터

    def to_dict(self) -> dict:
        """Convert to flat dict for Jinja2 rendering."""
        return {
            "account": self.account.to_dict(),
            "style": self.style.to_dict(),
            "channel": self.channel.to_dict() if self.channel else None,
            "weekly": self.weekly.to_dict() if self.weekly else None,
            "content": self.content.to_dict(),
        }
```

### 1.2 AccountVariables

계정 identity 정보를 프롬프트 변수로 변환한 구조체.

```python
@dataclass
class AccountVariables:
    """Account identity context variables."""

    one_liner: str                     # 계정 한 줄 소개
    target_audience: list[str]         # 타겟 오디언스 목록
    value_proposition: str             # 가치 제안
    pillars: list[str]                 # 핵심 기둥 (P1, P2, P3, P4)
    tone_voice: dict[str, str]         # 톤앤매너 설정
    bio: str                           # 상세 소개
    bio_secondary: str | None          # 추가 소개
    link_purpose: str                  # 링크 목적
    account_id: str                    # 계정 식별자

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_identity(cls, identity: AccountIdentity) -> "AccountVariables":
        """Create from AccountIdentity dataclass."""
        return cls(
            one_liner=identity.one_liner or "",
            target_audience=identity.target_audience or [],
            value_proposition=identity.value_proposition or "",
            pillars=identity.pillars or [],
            tone_voice=identity.tone_voice or {},
            bio=identity.bio or "",
            bio_secondary=identity.bio_secondary,
            link_purpose=identity.link_purpose or "",
            account_id=identity.account_id,
        )
```

### 1.3 StyleVariables

스타일 프로필을 프롬프트 변수로 변환한 구조체.

```python
@dataclass
class StyleVariables:
    """Style profile context variables."""

    name: str                          # 스타일 이름
    tone: str                          # 글 톤 (예: "professional", "casual")
    sentence_style: str                # 문장 스타일
    structure_patterns: list[str]      # 구조 패턴
    vocabulary: list[str]              # 자주 사용하는 어휘
    hooks: list[str]                   # 도입부 후크 패턴
    closings: list[str]                # 마무리 패턴

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_profile(cls, profile: StyleProfile) -> "StyleVariables":
        """Create from StyleProfile dataclass."""
        chars = profile.characteristics or {}
        return cls(
            name=profile.name or "default",
            tone=chars.get("tone", ""),
            sentence_style=chars.get("sentence_style", ""),
            structure_patterns=chars.get("structure_patterns", []),
            vocabulary=chars.get("vocabulary", []),
            hooks=chars.get("hooks", []),
            closings=chars.get("closings", []),
        )
```

### 1.4 ChannelVariables

채널별 설정을 프롬프트 변수로 변환한 구조체.

```python
@dataclass
class ChannelVariables:
    """Channel-specific context variables."""

    name: str                          # 채널명 (twitter, linkedin, newsletter)
    max_length: int                    # 최대 길이
    format: str                        # 포맷 요구사항
    platform_conventions: list[str]    # 플랫폼 관례
    use_hashtags: bool                 # 해시태그 사용 여부
    image_specs: dict | None           # 이미지 스펙 (이미지 프롬프트용)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_config(cls, channel: str, config: dict) -> "ChannelVariables":
        """Create from channel configuration dict."""
        return cls(
            name=channel,
            max_length=config.get("max_length", 280),
            format=config.get("format", "standard"),
            platform_conventions=config.get("platform_conventions", []),
            use_hashtags=config.get("use_hashtags", True),
            image_specs=config.get("image_specs"),
        )
```

### 1.5 WeeklyVariables

주간 슬롯 정보를 프롬프트 변수로 변환한 구조체.

```python
@dataclass
class WeeklyVariables:
    """Weekly slot context variables."""

    week_of: str                       # 주 시작일 (YYYY-MM-DD)
    cta: str                           # 이번 주 CTA
    customer_outcome: str              # 고객 성과 목표
    operator_kpi: str                  # 운영자 KPI
    pillar_distribution: dict[str, int] # 기둥별 할당 (P1: 2, P2: 2, ...)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_slot(cls, slot: WeeklySlot) -> "WeeklyVariables":
        """Create from WeeklySlot dataclass."""
        return cls(
            week_of=slot.week_of,
            cta=slot.cta or "",
            customer_outcome=slot.customer_outcome or "",
            operator_kpi=slot.operator_kpi or "",
            pillar_distribution=slot.pillar_distribution or {},
        )
```

### 1.6 ContentVariables

생성할 콘텐츠의 입력 데이터.

```python
@dataclass
class ContentVariables:
    """Input content data for prompt rendering."""

    title: str                         # 콘텐츠 제목
    summary: str                       # 요약
    key_points: list[str]              # 핵심 포인트
    excerpt: str                       # 발췌
    tags: list[str]                    # 태그
    source_url: str | None             # 원본 URL
    exploration: dict | None           # 탐색 결과 (롱폼용)

    def to_dict(self) -> dict:
        return asdict(self)
```

---

## 2. Agent-Operator Communication Module (에이전트-운영자 소통)

### 2.1 InteractionConfig

인터랙션 전체 설정.

```python
@dataclass
class InteractionConfig:
    """Configuration for agent-operator interactions."""

    draft: "DraftConfig"
    notification: "NotificationConfig"
    suggestion: "SuggestionConfig"

    @classmethod
    def from_yaml(cls, config_dict: dict) -> "InteractionConfig":
        """Load from config.yml interaction section."""
        return cls(
            draft=DraftConfig(**config_dict.get("draft", {})),
            notification=NotificationConfig(**config_dict.get("notification", {})),
            suggestion=SuggestionConfig(**config_dict.get("suggestion", {})),
        )
```

### 2.2 InteractionPoint (Base)

모든 인터랙션 지점의 기본 클래스.

```python
@dataclass
class InteractionPoint:
    """Base definition for an interaction point in the workflow."""

    interaction_type: str              # "selection" | "notification" | "suggestion"
    primary_method: str                # "interactive" | "console" | "terminal"
    fallback_method: str               # "cli_flag" | "log" | "file"
    deadline: datetime | None          # 응답 마감시간 (None = 즉시)
    reminder_interval: timedelta | None # 리마인더 간격
    auto_action: str | None            # "auto_select" | "skip" | "default"

    def is_expired(self) -> bool:
        """Check if deadline has passed."""
        if self.deadline is None:
            return False
        return datetime.now() > self.deadline

    def should_send_reminder(self, last_reminder: datetime | None) -> bool:
        """Check if reminder should be sent."""
        if self.reminder_interval is None or last_reminder is None:
            return False
        return datetime.now() - last_reminder >= self.reminder_interval
```

### 2.3 InteractionResult

인터랙션 실행 결과.

```python
@dataclass
class InteractionResult:
    """Result of an interaction point execution."""

    success: bool                      # 성공 여부
    method_used: str                   # "primary" | "fallback"
    response: Any | None               # 사용자 응답 (있는 경우)
    error: str | None                  # 에러 메시지
    timestamp: datetime                # 실행 시간
    metadata: dict                     # 추가 메타데이터

    @classmethod
    def primary_success(cls, response: Any = None, **metadata) -> "InteractionResult":
        return cls(
            success=True,
            method_used="primary",
            response=response,
            error=None,
            timestamp=datetime.now(),
            metadata=metadata,
        )

    @classmethod
    def fallback_used(cls, response: Any = None, error: str = None, **metadata) -> "InteractionResult":
        return cls(
            success=True,
            method_used="fallback",
            response=response,
            error=error,
            timestamp=datetime.now(),
            metadata=metadata,
        )

    @classmethod
    def failed(cls, error: str, **metadata) -> "InteractionResult":
        return cls(
            success=False,
            method_used="primary",
            response=None,
            error=error,
            timestamp=datetime.now(),
            metadata=metadata,
        )
```

### 2.4 WorkflowState

워크플로우 상태 스냅샷.

```python
@dataclass
class WorkflowState:
    """Snapshot of workflow state for context-aware suggestions."""

    completed_steps: list[str]         # 완료된 단계들
    pending_items: list[str]           # 대기 중인 항목들
    errors_encountered: list[str]      # 발생한 에러들
    generated_files: list[str]         # 생성된 파일 경로들
    validation_status: str | None      # "passed" | "failed" | "pending" | None
    pending_selections: list[str]      # 대기 중인 선택들 (draft IDs)

    def suggest_next_commands(self) -> list[str]:
        """Generate context-aware command suggestions."""
        suggestions = []

        if self.generated_files and self.validation_status is None:
            suggestions.append("python -m scripts.validate_output --path {output}")

        if self.validation_status == "passed":
            suggestions.append("python -m scripts.publish_log --date {date}")

        if self.validation_status == "failed":
            suggestions.append("python -m scripts.retry_failed --date {date}")

        if self.pending_selections:
            suggestions.append("python -m scripts.select_draft --list")

        return suggestions
```

---

## 3. Draft Module (초안)

### 3.1 DraftConfig

초안 생성 설정.

```python
@dataclass
class DraftConfig:
    """Configuration for draft generation and selection."""

    max_count: int = 5                 # 최대 초안 수 (FR-007)
    deadline_hours: int = 24           # 마감까지 시간
    deadline_time: str = "12:00"       # 구체적 마감 시간
    reminder_interval_hours: int = 2   # 리마인더 간격 (FR-010)
    auto_select_on_deadline: bool = True  # 마감 시 자동 선택
    scoring_algorithm: str = "default" # 스코어링 알고리즘

    def calculate_deadline(self, created_at: datetime) -> datetime:
        """Calculate absolute deadline from creation time."""
        # Parse deadline_time (e.g., "12:00")
        hour, minute = map(int, self.deadline_time.split(":"))

        # Next day at deadline_time
        next_day = created_at + timedelta(days=1)
        deadline = next_day.replace(hour=hour, minute=minute, second=0, microsecond=0)

        return deadline
```

### 3.2 DraftOption

개별 초안 옵션.

```python
@dataclass
class DraftOption:
    """A single generated content candidate."""

    id: str                            # 초안 식별자 (UUID)
    rank: int                          # 순위 (1 = 최고 점수)
    content_text: str                  # 생성된 텍스트
    quality_score: float               # 품질 점수 (0.0 - 1.0)
    preview_excerpt: str               # 미리보기 (첫 200자)
    generation_metadata: "GenerationMetadata"
    created_at: datetime

    def to_preview(self, max_length: int = 200) -> str:
        """Generate preview text for display."""
        preview = self.content_text[:max_length]
        if len(self.content_text) > max_length:
            preview += "..."
        return preview

    @classmethod
    def from_llm_response(
        cls,
        response: str,
        score: float,
        rank: int,
        model: str,
        tokens_used: int
    ) -> "DraftOption":
        """Create from LLM generation response."""
        return cls(
            id=str(uuid.uuid4())[:8],
            rank=rank,
            content_text=response,
            quality_score=score,
            preview_excerpt=response[:200] + "..." if len(response) > 200 else response,
            generation_metadata=GenerationMetadata(
                model=model,
                tokens_used=tokens_used,
                temperature=0.7,
            ),
            created_at=datetime.now(),
        )
```

### 3.3 GenerationMetadata

초안 생성 메타데이터.

```python
@dataclass
class GenerationMetadata:
    """Metadata about how a draft was generated."""

    model: str                         # 사용된 모델
    tokens_used: int                   # 사용된 토큰 수
    temperature: float                 # Temperature 설정
    prompt_hash: str | None            # 프롬프트 해시 (재현용)
    generation_time_seconds: float | None  # 생성 소요 시간
```

### 3.4 DraftSelection

초안 선택 상태 및 기록.

```python
@dataclass
class DraftSelection:
    """Record of a draft selection process."""

    id: str                            # 선택 세션 ID
    content_type: str                  # "longform" | "pack" | "image"
    account_id: str                    # 계정 ID
    input_id: str                      # 입력 콘텐츠 ID
    options: list[DraftOption]         # 초안 옵션들

    status: str                        # "pending" | "selected" | "expired"
    selected_option_id: str | None     # 선택된 초안 ID
    selected_at: datetime | None       # 선택 시간

    created_at: datetime               # 생성 시간
    deadline: datetime                 # 마감 시간
    last_reminder_at: datetime | None  # 마지막 리마인더 시간
    reminder_count: int = 0            # 리마인더 횟수

    def select(self, option_id: str) -> bool:
        """Record selection of a draft option."""
        if option_id not in [o.id for o in self.options]:
            return False
        self.selected_option_id = option_id
        self.selected_at = datetime.now()
        self.status = "selected"
        return True

    def auto_select_best(self) -> str:
        """Auto-select highest-scored draft."""
        best = max(self.options, key=lambda o: o.quality_score)
        self.select(best.id)
        return best.id

    def is_expired(self) -> bool:
        """Check if selection deadline has passed."""
        return datetime.now() > self.deadline

    def needs_reminder(self, interval_hours: int) -> bool:
        """Check if reminder should be sent."""
        if self.status != "pending":
            return False
        if self.last_reminder_at is None:
            return True
        elapsed = datetime.now() - self.last_reminder_at
        return elapsed >= timedelta(hours=interval_hours)

    @classmethod
    def create(
        cls,
        content_type: str,
        account_id: str,
        input_id: str,
        options: list[DraftOption],
        deadline_hours: int = 24,
        deadline_time: str = "12:00",
    ) -> "DraftSelection":
        """Create new draft selection session."""
        now = datetime.now()
        config = DraftConfig(deadline_hours=deadline_hours, deadline_time=deadline_time)
        return cls(
            id=str(uuid.uuid4())[:8],
            content_type=content_type,
            account_id=account_id,
            input_id=input_id,
            options=options,
            status="pending",
            selected_option_id=None,
            selected_at=None,
            created_at=now,
            deadline=config.calculate_deadline(now),
            last_reminder_at=None,
            reminder_count=0,
        )
```

### 3.5 DraftSelectionFile

파일 기반 초안 선택 저장소.

```python
@dataclass
class DraftSelectionFile:
    """File storage format for pending draft selections."""

    # YAML frontmatter fields
    type: str = "draft_selection"
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    deadline: datetime = None
    last_reminder: datetime | None = None
    reminder_interval_hours: int = 2
    account_id: str = ""
    content_type: str = ""
    input_id: str = ""

    # Markdown body contains draft options

    def to_markdown(self, options: list[DraftOption]) -> str:
        """Convert to Obsidian-compatible markdown."""
        frontmatter = yaml.dump({
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "last_reminder": self.last_reminder.isoformat() if self.last_reminder else None,
            "reminder_interval_hours": self.reminder_interval_hours,
            "account_id": self.account_id,
            "content_type": self.content_type,
            "input_id": self.input_id,
        }, default_flow_style=False)

        body = "\n# Draft Options\n\n"
        for opt in options:
            body += f"## Option {opt.rank} (Score: {opt.quality_score:.2f})\n\n"
            body += f"{opt.to_preview(500)}\n\n"
            body += f"*ID: `{opt.id}`*\n\n---\n\n"

        return f"---\n{frontmatter}---\n{body}"
```

---

## 4. Notification Module (알림)

### 4.1 NotificationConfig

알림 설정.

```python
@dataclass
class NotificationConfig:
    """Configuration for notification system."""

    primary: str = "console"           # "console" | "log" | "both"
    fallback: str = "log"              # "log" | "file"
    include_details: bool = True       # 상세 정보 포함 여부
    fallback_file: str = "logs/notifications.jsonl"  # 폴백 파일 경로
```

### 4.2 NotificationRecord

알림 기록.

```python
@dataclass
class NotificationRecord:
    """Persistent record of a notification attempt."""

    id: str                            # 알림 ID
    timestamp: datetime                # 전송 시도 시간
    notification_type: str             # "completion" | "error" | "reminder" | "suggestion"
    channel_used: str                  # "console" | "log" | "file"
    success: bool                      # 전송 성공 여부
    message_content: str               # 메시지 내용 (요약)
    retry_count: int                   # 재시도 횟수
    error: str | None                  # 에러 메시지 (실패 시)

    # Payload
    task_status: str | None            # "success" | "failure"
    items_processed: int | None        # 처리된 항목 수
    output_location: str | None        # 출력 위치
    errors_encountered: list[str] | None  # 발생한 에러들

    def to_json(self) -> str:
        """Convert to JSON line for log file."""
        return json.dumps({
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "notification_type": self.notification_type,
            "channel_used": self.channel_used,
            "success": self.success,
            "message_content": self.message_content[:500],  # Truncate
            "retry_count": self.retry_count,
            "error": self.error,
            "task_status": self.task_status,
            "items_processed": self.items_processed,
            "output_location": self.output_location,
            "errors_encountered": self.errors_encountered,
        })

    @classmethod
    def completion(
        cls,
        items_processed: int,
        output_location: str,
        duration_seconds: float,
    ) -> "NotificationRecord":
        """Create completion notification record."""
        return cls(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            notification_type="completion",
            channel_used="",  # Set during send
            success=True,
            message_content=f"Completed: {items_processed} items to {output_location}",
            retry_count=0,
            error=None,
            task_status="success",
            items_processed=items_processed,
            output_location=output_location,
            errors_encountered=None,
        )

    @classmethod
    def error(
        cls,
        error_message: str,
        context: dict | None = None,
    ) -> "NotificationRecord":
        """Create error notification record."""
        return cls(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            notification_type="error",
            channel_used="",  # Set during send
            success=True,
            message_content=f"Error: {error_message}",
            retry_count=0,
            error=error_message,
            task_status="failure",
            items_processed=None,
            output_location=None,
            errors_encountered=[error_message],
        )
```

### 4.3 NotificationPayload

알림 메시지 페이로드.

```python
@dataclass
class NotificationPayload:
    """Structured notification message content."""

    title: str                         # 알림 제목
    status: str                        # "success" | "failure" | "warning"
    summary: str                       # 한 줄 요약
    details: dict                      # 상세 정보

    # Standard details
    items_processed: int | None = None
    output_path: str | None = None
    duration_seconds: float | None = None
    errors: list[str] | None = None
    next_steps: list[str] | None = None

    def to_console_output(self) -> str:
        """Format for console display."""
        icon = "✅" if self.status == "success" else "❌" if self.status == "failure" else "⚠️"

        lines = [
            f"{icon} {self.title}",
            f"   {self.summary}",
        ]

        if self.items_processed is not None:
            lines.append(f"   Items: {self.items_processed}")
        if self.output_path:
            lines.append(f"   Output: {self.output_path}")
        if self.duration_seconds:
            lines.append(f"   Duration: {self.duration_seconds:.1f}s")

        return "\n".join(lines)

    def to_json_dict(self) -> dict:
        """Format for JSON logging."""
        return {
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "items_processed": self.items_processed,
            "output_path": self.output_path,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "next_steps": self.next_steps,
            "timestamp": datetime.now().isoformat(),
        }
```

### 4.4 SuggestionConfig

다음 명령 제안 설정.

```python
@dataclass
class SuggestionConfig:
    """Configuration for next command suggestions."""

    primary: str = "terminal"          # "terminal" | "file" | "both"
    fallback_file: str = "logs/suggestions.txt"
    context_aware: bool = True         # 워크플로우 상태 기반 제안
```

### 4.5 CommandSuggestion

다음 명령 제안.

```python
@dataclass
class CommandSuggestion:
    """A suggested next command."""

    rank: int                          # 우선순위
    command: str                       # 실행할 명령어
    description: str                   # 명령어 설명
    condition: str | None              # 제안 조건 (로그용)

    def to_display(self) -> str:
        """Format for display."""
        return f"{self.rank}. {self.description}:\n   {self.command}"
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTEXT VARIABLES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ContextVariableSet                                                          │
│  ├── AccountVariables ──────────── AccountIdentity (existing)               │
│  ├── StyleVariables ────────────── StyleProfile (existing)                  │
│  ├── ChannelVariables ──────────── config/accounts/*.yml                    │
│  ├── WeeklyVariables ───────────── WeeklySlot (existing)                    │
│  └── ContentVariables ──────────── Input content data                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          AGENT-OPERATOR INTERACTION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  InteractionConfig                                                           │
│  ├── DraftConfig                                                             │
│  ├── NotificationConfig                                                      │
│  └── SuggestionConfig                                                        │
│                                                                              │
│  InteractionPoint (base)                                                     │
│  └── InteractionResult                                                       │
│                                                                              │
│  WorkflowState                                                               │
│  └── CommandSuggestion[]                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                               DRAFT MODULE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DraftSelection                                                              │
│  ├── DraftOption[]                                                           │
│  │   └── GenerationMetadata                                                  │
│  └── DraftSelectionFile (storage format)                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           NOTIFICATION MODULE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  NotificationRecord                                                          │
│  └── NotificationPayload                                                     │
│                                                                              │
│  CommandSuggestion                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Storage Locations

| Entity | Storage Location | Format |
|--------|------------------|--------|
| ContextVariableSet | In-memory (built at runtime) | Python dataclass |
| DraftSelection | `Inbox/Drafts/{selection_id}.md` | Markdown + YAML frontmatter |
| NotificationRecord | `logs/notifications_{date}.jsonl` | JSON Lines |
| CommandSuggestion | `logs/suggestions_{timestamp}.txt` | Plain text |
| WorkflowState | In-memory (built at runtime) | Python dataclass |

---

## Validation Rules

### ContextVariableSet
- `account` is REQUIRED for all content generation
- `style` defaults to "default" style if not specified
- `channel` is REQUIRED for pack/image generation
- `content.title` must be non-empty string

### DraftSelection
- `options` must contain 1-5 DraftOption instances
- `deadline` must be in the future when created
- `selected_option_id` must match one of `options[].id` if set

### NotificationRecord
- `notification_type` must be one of: "completion", "error", "reminder", "suggestion"
- `timestamp` is auto-set on creation
- `retry_count` starts at 0, incremented on each retry attempt

---

## State Transitions

### DraftSelection Status

```
pending ──[operator selects]──► selected
    │
    └──[deadline passes]──► expired (if auto_select_on_deadline=false)
              │
              └──[auto-select]──► selected (if auto_select_on_deadline=true)
```

### NotificationRecord Success Flow

```
[create] ──► [try primary channel]
                 │
                 ├──[success]──► done (success=true)
                 │
                 └──[failure]──► [try fallback channel]
                                      │
                                      ├──[success]──► done (success=true)
                                      │
                                      └──[failure]──► done (success=false, log error)
```
