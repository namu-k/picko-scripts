# Quickstart: Context-Driven Content Quality & Agent Interaction Protocol

**Feature**: 001-context-interaction
**Date**: 2026-02-17

## 개요 (Overview)

이 기능은 두 가지 영역을 개선합니다:

1. **품질 (Quality)**: 계정, 채널, 스타일, 주간 컨텍스트 변수를 프롬프트에 주입하여 브랜드 일관성 확보
2. **인터랙션 (Interaction)**: 에이전트-운영자 간 소통 프로토콜로 초안 선택, 알림, 다음 명령 제안

---

## 빠른 시작 (Quick Start)

### 1. 기본 사용법 (Basic Usage)

기존과 동일하게 작동합니다:

```bash
python -m scripts.generate_content
```

### 2. 초안 생성 (Draft Generation)

여러 초안을 생성하여 선택할 수 있습니다:

```bash
# 3개 초안 생성 + 대화형 선택
python -m scripts.generate_content --drafts 3

# 5개 초안 생성 (최대)
python -m scripts.generate_content --drafts 5

# 초안 생성 후 특정 초안 선택 (비대화형)
python -m scripts.generate_content --drafts 3 --select-draft 2
```

### 3. 비대화형 모드 (Non-Interactive Mode)

CI/CD 또는 스케줄 작업에서 사용:

```bash
# 자동 모드 감지 (CI=true 환경 변수)
export CI=true
python -m scripts.generate_content --drafts 3

# 명시적 비대화형 모드
python -m scripts.generate_content --non-interactive --drafts 3
```

### 4. 알림 설정 (Notifications)

```bash
# 콘솔 + 로그 파일 알림
python -m scripts.generate_content --notify both

# 로그 파일만
python -m scripts.generate_content --notify log

# 알림 비활성화
python -m scripts.generate_content --no-notify
```

### 5. 다음 명령 제안 (Command Suggestions)

```bash
# 제안 활성화 (기본값)
python -m scripts.generate_content --suggest

# 제안 비활성화
python -m scripts.generate_content --no-suggest
```

---

## 설정 (Configuration)

### config.yml에 추가

```yaml
# config/config.yml
interaction:
  draft:
    max_count: 5                    # 최대 초안 수
    deadline_hours: 24              # 선택 마감 시간
    deadline_time: "12:00"          # 구체적 마감 시간 (다음 날 점심)
    reminder_interval_hours: 2      # 리마인더 간격
    auto_select_on_deadline: true   # 마감 시 자동 선택
    scoring_algorithm: "default"    # 스코어링 알고리즘

  notification:
    primary: "console"              # console | log | both
    fallback: "log"                 # log | file
    include_details: true           # 상세 정보 포함

  suggestion:
    primary: "terminal"             # terminal | file | both
    fallback_file: "logs/suggestions.txt"
    context_aware: true             # 워크플로우 상태 기반
```

---

## 컨텍스트 변수 (Context Variables)

### 프롬프트에서 사용 가능한 변수

```jinja2
{# 계정 정보 #}
{{ account.one_liner }}
{{ account.target_audience | join(', ') }}
{{ account.value_proposition }}
{{ account.pillars | join(', ') }}
{{ account.tone_voice.formal }}

{# 스타일 정보 #}
{{ style.tone }}
{{ style.sentence_style }}
{{ style.structure_patterns | first }}
{{ style.vocabulary | random }}
{{ style.hooks | first }}
{{ style.closings | first }}

{# 채널 정보 (팩/이미지용) #}
{{ channel.name }}
{{ channel.max_length }}
{{ channel.format }}
{{ channel.use_hashtags }}

{# 주간 슬롯 #}
{{ weekly.cta }}
{{ weekly.customer_outcome }}
{{ weekly.operator_kpi }}
{{ weekly.pillar_distribution.P1 }}

{# 콘텐츠 데이터 #}
{{ content.title }}
{{ content.summary }}
{{ content.key_points | join('\n- ') }}
```

### 프롬프트 템플릿 예시

```markdown
# 롱폼 프롬프트 템플릿

## 타겟 오디언스
{{ account.target_audience | join(', ') }}

## 글쓰기 스타일
- 톤: {{ style.tone }}
- 문장 스타일: {{ style.sentence_style }}

## 이번 주 목표
- CTA: {{ weekly.cta }}
- 고객 성과: {{ weekly.customer_outcome }}

## 작성할 내용
제목: {{ content.title }}
요약: {{ content.summary }}
```

---

## 워크플로우 (Workflow)

### 일반적인 워크플로우

```
1. 콘텐츠 수집
   └── python -m scripts.daily_collector

2. 다이제스트 검토
   └── Inbox/Inputs/_digests/YYYY-MM-DD.md

3. 초안 생성 (예: 3개)
   └── python -m scripts.generate_content --drafts 3

4. 초안 선택
   ├── 대화형: 터미널에서 선택
   └── 비대화형: --select-draft N

5. 검증
   └── python -m scripts.validate_output --path Content/

6. 발행 로그 생성
   └── python -m scripts.publish_log --date YYYY-MM-DD
```

### 비대화형 워크플로우 (CI/CD)

```bash
# 전체 파이프라인
python -m scripts.daily_collector --date 2026-02-17
python -m scripts.generate_content --non-interactive --drafts 3 --notify log
python -m scripts.validate_output --path Content/ --json
```

---

## 파일 위치 (File Locations)

| 항목 | 위치 |
|------|------|
| 대기 중인 초안 선택 | `Inbox/Drafts/{selection_id}.md` |
| 알림 로그 | `logs/notifications_YYYY-MM-DD.jsonl` |
| 제안 파일 | `logs/suggestions_{timestamp}.txt` |
| 컨텍스트 설정 | `config/config.yml` (interaction 섹션) |

---

## 문제 해결 (Troubleshooting)

### 초안 선택 마감 초과

```bash
# 마감 초과된 선택 확인
ls Inbox/Drafts/

# 초안 재생성
python -m scripts.generate_content --force --drafts 3
```

### 비대화형 모드 자동 감지 안 됨

```bash
# 명시적 설정
export PICKO_NON_INTERACTIVE=true
# 또는
export CI=true
```

### 알림이 로그에만 기록됨

```bash
# 콘솔 알림 활성화
python -m scripts.generate_content --notify console
# 또는
python -m scripts.generate_content --notify both
```

---

## 다음 단계 (Next Steps)

1. **설정 확인**: `config/config.yml`에 `interaction` 섹션 추가
2. **프롬프트 업데이트**: 기존 프롬프트에 새 변수 이름 적용
3. **테스트**: `--drafts 2`로 간단히 테스트
4. **CI/CD 통합**: 비대화형 플래그로 자동화

---

## 관련 문서 (Related Docs)

- [Feature Spec](./spec.md)
- [Implementation Plan](./plan.md)
- [Data Model](./data-model.md)
- [CLI Contract](./contracts/cli-interface.md)
- [Research](./research.md)
