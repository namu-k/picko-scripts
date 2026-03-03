# Data Contracts

This document defines the canonical frontmatter fields and data structures used across the Picko pipeline.

---

## Content Input (`Inbox/Inputs/*.md`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique content identifier (hash-based) |
| `title` | string | Yes | Content title |
| `source` | string | Yes | RSS feed source name |
| `source_url` | string | Yes | Original article URL |
| `publish_date` | datetime | Yes | Article publication date (ISO 8601) |
| `collected_at` | datetime | Yes | Collection timestamp (ISO 8601) |
| `writing_status` | enum | Yes | `pending` \| `auto_ready` \| `manual` \| `completed` |
| `score` | object | Yes | Score breakdown (see ContentScore) |
| `tags` | list | No | Auto-generated content tags |
| `summary` | string | No | AI-generated summary text |
| `key_points` | list | No | Extracted key points from content |

### Score Object

```yaml
score:
  novelty: 0.85      # 0-1, similarity to existing content
  relevance: 0.72    # 0-1, match to account profile
  quality: 0.68      # 0-1, content quality heuristics
  freshness: 0.95    # 0-1, time decay from publish_date
  total: 0.78        # weighted sum of all factors
```

---

## Publish Log (`Logs/Publish/*.md`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Log ID (format: `pub_{content_id}_{timestamp}`) |
| `type` | string | Yes | Always `publish_log` |
| `content_id` | string | Yes | Reference to source content |
| `platform` | enum | Yes | `twitter` \| `linkedin` \| `newsletter` \| `blog` \| `instagram` \| `youtube` |
| `status` | enum | Yes | `draft` \| `scheduled` \| `published` \| `cancelled` |
| `scheduled_at` | datetime | No | Planned publish time (ISO 8601) |
| `published_at` | datetime | No | Actual publish time (ISO 8601) |
| `published_url` | string | No | Platform-specific post URL |
| `platform_post_id` | string | No | Platform-specific post ID (e.g., tweet ID) |
| `metrics` | object | No | Engagement metrics (see Metrics Object) |
| `metrics_synced_at` | datetime | No | Last metrics sync timestamp |
| `metrics_source` | enum | No | `api` \| `manual` \| `unavailable` |

### Metrics Object

Standard platform-agnostic metrics:

```yaml
metrics:
  views: 1234
  likes: 56
  comments: 12
  shares: 8
  clicks: 234
  impressions: 5678
```

Platform-specific metrics can be added under `platform_specific`:

```yaml
metrics:
  views: 1234
  likes: 56
  shares: 12          # maps to retweets on Twitter
  platform_specific:
    retweets: 12      # Twitter-specific (optional)
    quote_tweets: 3   # Twitter-specific (optional)
    saves: 45         # Instagram/LinkedIn-specific (optional)
```

---

## Content Output (`Content/{Longform,Packs}/*.md`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique content identifier |
| `type` | enum | Yes | `longform` \| `twitter_pack` \| `linkedin_pack` \| `newsletter` |
| `input_id` | string | Yes | Reference to source input |
| `derivative_status` | enum | Yes | `draft` \| `approved` \| `published` |
| `image_status` | enum | No | `pending` \| `approved` \| `rendered` |
| `created_at` | datetime | Yes | Generation timestamp |
| `account` | string | Yes | Target account ID |

---

## Status Transitions

### writing_status
```
pending → auto_ready → completed
       ↘ manual → completed
```

### publish log status
```
draft → scheduled → published
     ↘ cancelled
```

### derivative_status
```
draft → approved → published
```

---

## Freshness Calculation

The freshness factor uses exponential decay:

```
freshness = 2^(-age_days / half_life_days)
```

Where:
- `age_days` = days since `publish_date`
- `half_life_days` = configurable (default: 7)

Examples (with half_life = 7):
- Today: freshness = 1.0
- 7 days old: freshness ≈ 0.5
- 14 days old: freshness ≈ 0.25
- 30 days old: freshness ≈ 0.06

---

## Scoring Weights

Default weights (sum should be ~1.0):

| Factor | Default Weight |
|--------|----------------|
| novelty | 0.30 |
| relevance | 0.40 |
| quality | 0.30 |
| freshness | 0.15 |

Note: Total weights can exceed 1.0; the system normalizes if needed.

---

## Platform Post URL Formats

| Platform | URL Format |
|----------|------------|
| Twitter/X | `https://twitter.com/{username}/status/{tweet_id}` or `https://x.com/{username}/status/{tweet_id}` |
| LinkedIn | `https://linkedin.com/posts/{post_id}` |
| Newsletter | Custom (depends on email platform) |

---

## Environment Variables

Required for platform integrations:

| Variable | Platforms | Description |
|----------|-----------|-------------|
| `TWITTER_BEARER_TOKEN` | Twitter | API v2 bearer token |
| `TWITTER_API_KEY` | Twitter | OAuth 1.0a consumer key |
| `TWITTER_API_SECRET` | Twitter | OAuth 1.0a consumer secret |
| `TWITTER_ACCESS_TOKEN` | Twitter | OAuth 1.0a access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter | OAuth 1.0a access token secret |
| `OPENAI_API_KEY` | All | LLM operations |
| `OPENROUTER_API_KEY` | All | Alternative LLM provider |
| `RELAY_API_KEY` | All | Alternative LLM provider |

---

## VideoPlan Output (`Content/Video/*.md`)

VideoPlan은 Picko가 외부 AI 동영상 서비스에 넘길 영상 기획서입니다.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | VideoPlan ID (format: `video_YYYY-MM-DD_NNN`) |
| `account` | string | Yes | Target account ID |
| `intent` | enum | Yes | `ad` \| `explainer` \| `brand` \| `trend` — 3축 유형 결정 (why) |
| `goal` | string | Yes | Video goal/message |
| `source` | object | Yes | VideoSource (see below) |
| `brand_style` | object | Yes | BrandStyle (see below) |
| `target_services` | list | No | AI video services: `runway`, `pika`, `kling`, `luma`, `veo`, `sora` |
| `platforms` | list | No | Target platforms: `instagram_reel`, `youtube_short`, `tiktok`, `twitter_video`, `linkedin_video` |
| `duration_sec` | int | No | Total duration (calculated from shots) |
| `created_at` | datetime | No | Creation timestamp (ISO 8601) |
| `shots` | list | Yes | List of VideoShot objects |

### 3축 유형 결정 (Three-Axis Type Decision)

VideoPlan은 세 가지 독립된 축의 조합으로 결정됩니다:

1. **소스 (what)**: `source.type` — account_only \| longform \| pack \| digest
2. **의도 (why)**: `intent` — ad \| explainer \| brand \| trend
3. **주간 맥락 (when)**: CLI `--week-of` 옵션 → WeeklySlot CTA 주입

### VideoSource Object

```yaml
source:
  type: longform      # account_only | longform | pack | digest
  id: lf_2026-03-01_001  # 참조 소스 ID (optional)
  summary: "..."         # 소스 내용 요약 (프롬프트 생성에 활용)
```

### BrandStyle Object

```yaml
brand_style:
  tone: "감성/몽환적"
  theme: "emotional-date"
  aspect_ratio: "9:16"
  colors: {}
  fonts: {}
```

### VideoShot Object

```yaml
shots:
  - index: 1
    duration_sec: 5
    shot_type: intro       # intro | main | cta | background | 자유 기입
    script: "장면 설명"
    caption: "화면 자막"
    background_prompt: "text-to-video prompt (English)"
    notes:
      luma: "서비스별 힌트"
```

### Intent별 특성

| intent | 용도 | 길이 | 샷 수 | 핵심 특성 |
|--------|------|------|-------|----------|
| `ad` (기본) | 전환/다운로드 유도 | 15-30초 | 3-5개 | CTA 필수, 첫 3초 훅 |
| `explainer` | 개념 설명/교육 | 45-120초 | 5-8개 | 인트로→본론→결론, 교육적 톤 |
| `brand` | 브랜드 인지도/분위기 | 15-60초 | 3-5개 | 시네마틱, 텍스트 최소화 |
| `trend` | 트렌드 반응/시의성 | 15-30초 | 3-4개 | 빠른 템포, 대화체 |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2 | 2026-03-04 | Add VideoPlan output schema with 3-axis type decision |
| 1.1 | 2026-02-28 | Add optional Content Input fields (tags, summary, key_points), platform_specific metrics |
| 1.0 | 2026-02-26 | Initial data contracts definition |
