# Picko Agent Guide

> 이 문서는 다른 코딩 CLI 에이전트가 Picko 프로젝트의 콘텐츠 파이프라인을 모사할 수 있도록 작성된 가이드입니다.

---

## 개요

Picko는 RSS 피드와 웹 소스에서 콘텐츠를 자동 수집하고, AI를 활용해 다양한 형식의 콘텐츠를 생성하는 파이프라인 시스템입니다.

### 핵심 원칙

1. **Obsidian Vault 기반**: 모든 콘텐츠는 마크다운 + YAML frontmatter 형식
2. **작업별 LLM 분리**: 요약/태깅(로컬) vs 글쓰기(클라우드)
3. **승인 기반 생성**: 수동 승인 후에만 콘텐츠 생성
4. **계정 프로필 기반**: 계정별로 다른 관련도/스타일 적용

---

## 파이프라인 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PICKO CONTENT PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1: COLLECTION                                                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │   RSS    │ -> │  Dedupe  │ -> │   NLP    │ -> │  Score   │              │
│  │  Feeds   │    │  & Fetch │    │ Process  │    │  & Rank  │              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       │                                                              │       │
│       v                                                              v       │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  Inbox/Inputs/{id}.md (개별 입력) + _digests/{date}.md (다이제스트) │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Phase 2: CURATION (수동 승인)                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  사용자가 다이제스트에서 [x] 체크 -> writing_status: auto_ready     │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Phase 3: GENERATION                                                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                              │
│  │ Longform │    │  Packs   │    │  Image   │                              │
│  │ Article  │    │(Twitter/ │    │ Prompts  │                              │
│  │          │    │ LinkedIn)│    │          │                              │
│  └──────────┘    └──────────┘    └──────────┘                              │
│       │              │               │                                      │
│       v              v               v                                      │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  Content/Longform/ + Content/Packs/ + Assets/Images/_prompts/    │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Phase 4: VALIDATION                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  프론트매터 검증 + 섹션 검증 + 위키링크 검증                        │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  Phase 5: PUBLISHING (선택)                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  Twitter/LinkedIn/Newsletter 발행 + 메트릭 수집                    │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Collection (수집)

### 목표
RSS 피드에서 콘텐츠를 수집하고, NLP 처리 후 점수를 매겨 다이제스트 생성

### CLI 명령어

```bash
# 기본 수집 (오늘 날짜)
python -m scripts.daily_collector

# 특정 날짜 수집
python -m scripts.daily_collector --date 2026-02-28

# 특정 소스만 수집
python -m scripts.daily_collector --sources techcrunch ai_news

# Dry-run (저장 없이 테스트)
python -m scripts.daily_collector --dry-run

# 특정 계정 프로필로 수집
python -m scripts.daily_collector --account socialbuilders
```

### 처리 단계

1. **Ingest**: `config/sources.yml`에서 RSS 피드 URL 로드
2. **Dedupe**: URL 정규화 + 해시 기반 중복 제거
3. **Fetch**: 본문/제목/발행일 추출 (trafilatura)
4. **NLP**: LLM으로 요약/핵심/태깅 (summary_llm)
5. **Embed**: 임베딩 생성 (local/ollama/openai)
6. **Score**: novelty/relevance/quality/freshness/total 계산
7. **Export**: `Inbox/Inputs/{id}.md` 생성
8. **Digest**: `Inbox/Inputs/_digests/{date}.md` 생성

### 출력 파일 구조

```
Inbox/Inputs/
├── abc123def456.md          # 개별 입력 노트
├── def789ghi012.md
└── _digests/
    └── 2026-02-28.md       # 일별 다이제스트
```

### Input 노트 프론트매터

```yaml
---
id: abc123def456
title: "기사 제목"
source: techcrunch
source_url: https://example.com/article
publish_date: 2026-02-28T10:00:00Z
collected_at: 2026-02-28T15:30:00Z
writing_status: pending  # pending | auto_ready | manual | completed
score:
  novelty: 0.85
  relevance: 0.72
  quality: 0.68
  freshness: 0.95
  total: 0.78
tags: [ai, startup, technology]
summary: "요약 텍스트"
key_points: ["핵심1", "핵심2"]
---
```

---

## Phase 2: Curation (큐레이션)

### 목표
사용자가 다이제스트에서 승인할 항목 선택

### 수동 작업 (Obsidian)

1. `Inbox/Inputs/_digests/{date}.md` 열기
2. 승인할 항목의 체크박스 `[ ]` -> `[x]` 변경
3. `writing_status`가 `pending` -> `auto_ready`로 자동 변경

### writing_status 값

| 값 | 의미 |
|----|------|
| `pending` | 아직 승인하지 않음 (기본값) |
| `auto_ready` | 자동 생성 승인 |
| `manual` | 수동 작성 예정 |
| `completed` | 생성 완료 |

---

## Phase 3: Generation (생성)

### 목표
승인된 항목에서 롱폼/팩/이미지 프롬프트 생성

### CLI 명령어

```bash
# auto_ready 항목만 생성
python -m scripts.generate_content

# 특정 날짜 생성
python -m scripts.generate_content --date 2026-02-28

# 모든 항목 강제 생성
python -m scripts.generate_content --auto-all

# 특정 타입만 생성
python -m scripts.generate_content --type longform packs

# 이미 생성된 항목 재생성
python -m scripts.generate_content --force
```

### 생성물

| 타입 | 출력 경로 | 설명 |
|------|-----------|------|
| Longform | `Content/Longform/longform_{id}.md` | 블로그 글 |
| Twitter Pack | `Content/Packs/twitter/pack_{id}_twitter.md` | 트윗 스레드 |
| LinkedIn Pack | `Content/Packs/linkedin/pack_{id}_linkedin.md` | 링크드인 포스트 |
| Newsletter | `Content/Packs/newsletter/pack_{id}_newsletter.md` | 뉴스레터 |
| Image Prompt | `Assets/Images/_prompts/img_{id}.md` | 이미지 생성용 프롬프트 |

### Longform 노트 구조

```markdown
---
id: longform_abc123def456
type: longform
input_id: abc123def456
derivative_status: draft
created_at: 2026-02-28T16:00:00Z
account: socialbuilders
---

# 제목

## 개요
...

## 핵심 내용
...

## 결론
...

## 관련 링크
- [[abc123def456]]  # 원본 Input 노트
```

---

## Phase 4: Validation (검증)

### 목표
생성된 콘텐츠의 품질 검증

### CLI 명령어

```bash
# 특정 경로 검증
python -m scripts.validate_output --path Content/Longform/

# 재귀 검증
python -m scripts.validate_output --path Content/ --recursive

# 상세 출력
python -m scripts.validate_output --path Content/ --recursive --verbose
```

### 검증 항목

1. **프론트매터 필수 필드**: id, type, input_id, created_at
2. **섹션 구조**: 개요/핵심/결론 섹션 존재
3. **위키링크**: 원본 Input 노트 참조 존재

### 시스템 헬스 체크

```bash
python -m scripts.health_check
python -m scripts.health_check --json
```

---

## Phase 5: Publishing (발행, 선택)

### 목표
소셜 미디어 플랫폼에 콘텐츠 발행

### CLI 명령어

```bash
# 워크플로우 실행
python -m scripts.run_workflow --workflow config/workflows/twitter_publish.yml

# 발행 로그 생성
python -m scripts.publish_log --content-id abc123def456 --platform twitter
```

### 발행 로그 구조

```yaml
---
id: pub_abc123def456_20260228
type: publish_log
content_id: abc123def456
platform: twitter
status: published
published_at: 2026-02-28T17:00:00Z
published_url: https://twitter.com/user/status/123456789
metrics:
  views: 1234
  likes: 56
  retweets: 12
---
```

---

## 데이터 구조

### 디렉토리 구조

```
mock_vault/
├── Inbox/
│   └── Inputs/
│       ├── {id}.md              # 개별 입력 노트
│       └── _digests/
│           └── {date}.md        # 일별 다이제스트
├── Content/
│   ├── Longform/
│   │   └── longform_{id}.md
│   └── Packs/
│       ├── twitter/
│       ├── linkedin/
│       └── newsletter/
├── Assets/
│   └── Images/
│       └── _prompts/
│           └── img_{id}.md
└── Logs/
    └── Publish/
        └── pub_{id}_{timestamp}.md
```

### 설정 파일

```
config/
├── config.yml           # 메인 설정
├── sources.yml          # RSS 소스 목록
├── collectors.yml       # 수집기 설정
├── accounts/            # 계정 프로필
│   └── socialbuilders.yml
├── prompts/             # LLM 프롬프트
│   ├── longform/
│   ├── packs/
│   └── image/
└── layouts/             # 이미지 레이아웃
    ├── presets/
    └── themes/
```

---

## 에이전트 작업 규칙

### 1. 파일 작업

- **읽기**: 항상 `picko/vault_io.py`의 함수 사용
- **쓰기**: `write_note()` 함수로 프론트매터 자동 처리
- **경로**: `config/config.yml`의 `vault.root` 기준 상대 경로

### 2. LLM 호출

```python
from picko.llm_client import get_summary_client, get_writer_client

# 요약/태깅용 (로컬 우선)
summary_client = get_summary_client()
result = summary_client.chat("요약해줘: " + content)

# 글쓰기용 (클라우드)
writer_client = get_writer_client()
article = writer_client.chat("블로그 글 작성: " + summary)
```

### 3. 점수 계산

```python
from picko.scoring import ContentScorer

scorer = ContentScorer(config)
score = scorer.score(
    content=item,
    existing_embeddings=cache,
    account_identity=identity
)
# Returns: {"novelty": 0.85, "relevance": 0.72, "quality": 0.68, "freshness": 0.95, "total": 0.78}
```

### 4. 템플릿 렌더링

```python
from picko.templates import get_longform_renderer, get_pack_renderer

renderer = get_longform_renderer()
output = renderer.render_longform(
    title=title,
    summary=summary,
    key_points=key_points,
    account=account
)
```

### 5. 에러 처리

- API 실패 시 자동 폴백 (`fallback_provider` 설정)
- 로그는 `logs/{date}/`에 일별 저장
- 실패 항목은 `scripts/retry_failed.py`로 재시도

---

## 검증 체크리스트

### 수집 완료 확인

- [ ] `Inbox/Inputs/`에 새 노트 생성됨
- [ ] 각 노트에 `score` 필드 존재
- [ ] `writing_status: pending`으로 설정됨
- [ ] 다이제스트 파일 생성됨

### 생성 완료 확인

- [ ] `Content/Longform/`에 롱폼 생성됨
- [ ] 프론트매터 필수 필드 모두 존재
- [ ] 원본 Input 노트로 위키링크 존재
- [ ] `derivative_status: draft` 설정됨

### 검증 통과 확인

- [ ] `validate_output` 에러 0건
- [ ] 모든 섹션 존재 (개요/핵심/결론)
- [ ] 위키링크 유효

---

## 빠른 참조

### 주요 스크립트

| 스크립트 | 용도 | 명령어 |
|----------|------|--------|
| `daily_collector.py` | 콘텐츠 수집 | `python -m scripts.daily_collector` |
| `generate_content.py` | 콘텐츠 생성 | `python -m scripts.generate_content` |
| `validate_output.py` | 품질 검증 | `python -m scripts.validate_output` |
| `health_check.py` | 시스템 점검 | `python -m scripts.health_check` |
| `explore_topic.py` | 주제 탐색 | `python -m scripts.explore_topic` |
| `render_media.py` | 이미지 렌더링 | `python -m scripts.render_media` |

### 환경 변수

| 변수 | 용도 |
|------|------|
| `OPENAI_API_KEY` | OpenAI LLM |
| `OPENROUTER_API_KEY` | OpenRouter LLM |
| `RELAY_API_KEY` | Relay LLM |
| `ANTHROPIC_API_KEY` | Anthropic LLM |
| `UNSPLASH_ACCESS_KEY` | 이미지 소스 |

---

## 최근 변경사항

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-02-28 | CHANGELOG.md 업데이트 (테스트 커버리지, repo cleanup) |
| 2026-02-28 | specs/006-multimedia-styles/tasks.md 정렬 |
| 2026-02-26 | v0.4.0 릴리스 (Auto Collector V2, Orchestration Layer) |

---

*Created: 2026-02-28*
*Version: 1.0*
