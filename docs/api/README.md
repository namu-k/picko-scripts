# Picko API 명세서

> **버전**: 1.0.0
> **최종 수정**: 2026-03-04
> **대상 독자**: 개발자, 시스템 통합 담당자
> **구현 상태**: 이 API 명세는 **설계 문서**입니다.
> 현재 Picko는 CLI 기반으로 동작하며, HTTP REST API 서버는 아직 구현되지 않았습니다.
> 향후 웹 UI 백엔드 구현 시 이 명세를 기반으로 API를 구축할 예정입니다.

---

## 개요

Picko는 콘텐츠 파이프라인 자동화 시스템으로, RESTful API를 통해 다양한 기능을 제공합니다. 모든 API 요청은 HTTPS를 사용하며, JSON 형식의 요청/응답을 처리합니다.

## 인증

API 요청 시 다음 방식 중 하나로 인증해야 합니다.

### 환경 변수 인증 (권장)

```bash
# .env 파일에 설정
RELAY_API_KEY=your_api_key_here
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_api_key_here
```

### Bearer Token 인증

```http
Authorization: Bearer your_api_key_here
```

## 베이스 URL

```
https://api.picko.local:8000  # 개발 환경
https://api.picko.com        # 운영 환경
```

---

## 1. 콘텐츠 수집 API

### 1.1 RSS 피드 수집

```http
POST /api/v1/collect/rss
Content-Type: application/json

{
  "urls": ["https://techcrunch.com/feed/", "https://ai-news.com/rss"],
  "account": "socialbuilders",
  "dry_run": false
}
```

**응답**:
```json
{
  "success": true,
  "collected_count": 15,
  "duplicates_removed": 3,
  "items": [
    {
      "id": "item_123",
      "title": "AI Breakthrough in Natural Language Processing",
      "url": "https://techcrunch.com/2026/03/04/ai-breakthrough",
      "summary": "Researchers have developed a new AI model...",
      "tags": ["AI", "NLP", "Breakthrough"],
      "source_url": "https://techcrunch.com/feed/",
      "collected_at": "2026-03-04T10:00:00Z"
    }
  ]
}
```

### 1.2 Perplexity Tasks 수집

```http
POST /api/v1/collect/perplexity
Content-Type: application/json

{
  "account": "socialbuilders",
  "input_dir": "Inbox/Perplexity",
  "file_patterns": ["*.md", "*.html"]
}
```

**응답**:
```json
{
  "success": true,
  "processed_count": 8,
  "archived_count": 8,
  "items": [...]
}
```

---

## 2. 콘텐츠 생성 API

### 2.1 롱폼 아티클 생성

```http
POST /api/v1/generate/longform
Content-Type: application/json

{
  "account": "socialbuilders",
  "item_id": "item_123",
  "options": {
    "use_exploration": true,
    "apply_reference_style": true,
    "target_length": "2000"
  }
}
```

**응답**:
```json
{
  "success": true,
  "content_id": "content_456",
  "title": "AI Breakthrough in Natural Language Processing",
  "content": "## 개요\n\n...",
  "sections": ["개요", "상세 설명", "결론"],
  "word_count": 2150,
  "generated_at": "2026-03-04T10:30:00Z"
}
```

### 2.2 소셜 미디어 팩 생성

```http
POST /api/v1/generate/packs
Content-Type: application/json

{
  "account": "socialbuilders",
  "content_id": "content_456",
  "types": ["twitter", "linkedin", "newsletter"],
  "options": {
    "twitter": {
      "max_length": 280,
      "hashtag_count": 3
    }
  }
}
```

**응답**:
```json
{
  "success": true,
  "packs": {
    "twitter": {
      "content": "🚀 AI breakthrough: New model achieves...",
      "hashtags": ["#AI", "#NLP", "#Tech"],
      "character_count": 275
    },
    "linkedin": {
      "content": "New breakthrough in natural language processing...",
      "character_count": 2980
    }
  }
}
```

---

## 3. 품질 검증 API

### 3.1 품질 검증 실행

```http
POST /api/v1/quality/verify
Content-Type: application/json

{
  "account": "socialbuilders",
  "items": ["item_123", "item_124"],
  "threshold": 0.85,
  "enhanced_mode": false
}
```

**응답**:
```json
{
  "results": {
    "item_123": {
      "verdict": "approved",
      "confidence": 0.92,
      "primary_score": 0.90,
      "cross_check_score": 0.95,
      "reason": "High quality and relevant content"
    },
    "item_124": {
      "verdict": "review",
      "confidence": 0.65,
      "primary_score": 0.70,
      "cross_check_score": 0.60,
      "reason": "Quality score below threshold"
    }
  }
}
```

### 3.2 QualityGraph 상태 확인

```http
GET /api/v1/quality/graph/{item_id}
```

**응답**:
```json
{
  "item_id": "item_123",
  "current_state": "primary_validation",
  "states": {
    "primary_validation": {
      "status": "completed",
      "confidence": 0.90,
      "timestamp": "2026-03-04T10:15:00Z"
    },
    "cross_check": {
      "status": "pending",
      "confidence": null,
      "timestamp": null
    }
  },
  "estimated_completion": "2026-03-04T10:20:00Z"
}
```

---

## 4. 소스 발견 API

### 4.1 새 소스 발견

```http
POST /api/v1/discover/sources
Content-Type: application/json

{
  "account": "socialbuilders",
  "keywords": ["AI", "startup", "technology"],
  "platforms": ["reddit", "mastodon"],
  "max_results": 10
}
```

**응답**:
```json
{
  "discovered_count": 8,
  "candidates": [
    {
      "id": "candidate_456",
      "platform": "reddit",
      "handle": "r/technology",
      "name": "Technology News",
      "description": "Latest technology news and updates",
      "url": "https://reddit.com/r/technology",
      "relevance_score": 0.85,
      "quality_score": 0.80,
      "requires_review": true
    }
  ]
}
```

### 4.2 소스 등록

```http
POST /api/v1/discover/register
Content-Type: application/json

{
  "candidate_id": "candidate_456",
  "source_type": "rss",
  "auto_approve": false
}
```

**응답**:
```json
{
  "success": true,
  "source_id": "source_789",
  "registered_at": "2026-03-04T11:00:00Z"
}
```

---

## 5. 멀티미디어 렌더링 API

### 5.1 이미지 렌더링

```http
POST /api/v1/media/render/image
Content-Type: application/json

{
  "template": "twitter",
  "content": {
    "title": "AI Breakthrough",
    "summary": "New AI model achieves breakthrough",
    "hashtags": ["#AI", "#Tech"]
  },
  "layout": {
    "preset": "minimal_dark",
    "theme": "tech_startup"
  },
  "output_format": "png"
}
```

**응답**:
```json
{
  "success": true,
  "image_url": "https://assets.picko.com/images/render_123.png",
  "dimensions": {
    "width": 1200,
    "height": 675
  },
  "file_size": 245678
}
```

### 5.2 배치 렌더링 요청

```http
POST /api/v1/media/render/batch
Content-Type: application/json

{
  "account": "socialbuilders",
  "source_path": "Content/Packs/twitter",
  "template": "twitter",
  "filter": "derivative_status=approved",
  "batch_size": 5
}
```

---

## 6. 워크플로우 실행 API

### 6.1 워크플로우 실행

```http
POST /api/v1/workflows/{workflow_name}/run
Content-Type: application/json

{
  "workflow_name": "daily_pipeline",
  "args": {
    "account": "socialbuilders"
  },
  "dry_run": false,
  "timeout_seconds": 3600
}
```

**응답**:
```json
{
  "execution_id": "exec_123",
  "status": "running",
  "started_at": "2026-03-04T12:00:00Z",
  "estimated_duration": "15 minutes",
  "steps": [
    {
      "name": "collect",
      "status": "completed",
      "duration": "2m 30s"
    },
    {
      "name": "dedup",
      "status": "running",
      "started_at": "2026-03-04T12:02:30Z"
    }
  ]
}
```

### 6.2 실행 상태 확인

```http
GET /api/v1/workflows/executions/{execution_id}
```

**응답**:
```json
{
  "execution_id": "exec_123",
  "status": "completed",
  "completed_at": "2026-03-04T12:15:00Z",
  "results": {
    "total_items": 12,
    "processed_items": 10,
    "failed_items": 2
  },
  "logs": [
    {
      "timestamp": "2026-03-04T12:10:00Z",
      "step": "generate_longform",
      "message": "Generated 5 longform articles",
      "status": "success"
    }
  ]
}
```

---

## 7. 검색 및 조회 API

### 7.1 콘텐츠 검색

```http
GET /api/v1/content/search?
  q=AI breakthrough&
  account=socialbuilders&
  type=longform&
  limit=10&
  offset=0
```

**응답**:
```json
{
  "total_count": 25,
  "items": [
    {
      "id": "content_123",
      "title": "AI Breakthrough in NLP",
      "summary": "New model achieves state-of-the-art...",
      "tags": ["AI", "NLP"],
      "published_at": "2026-03-04T10:00:00Z",
      "score": 0.85
    }
  ]
}
```

### 7.2 Vault 내용 조회

```http
GET /api/v1/vault/notes?
  path=Inbox/Inputs&
  filter=writing_status=auto_ready&
  limit=20
```

**응답**:
```json
{
  "count": 15,
  "notes": [
    {
      "path": "Inbox/Inputs/ai_breakthrough.md",
      "frontmatter": {
        "title": "AI Breakthrough",
        "writing_status": "auto_ready",
        "score": 0.85
      },
      "modified_at": "2026-03-04T09:00:00Z"
    }
  ]
}
```

---

## 8. 알림 API

### 8.1 리뷰 알림 발송

```http
POST /api/v1/notifications/review-required
Content-Type: application/json

{
  "account": "socialbuilders",
  "items": ["item_123", "item_124"],
  "channel": "telegram",
  "timeout_hours": 72
}
```

**응답**:
```json
{
  "success": true,
  "message_ids": ["msg_456", "msg_457"],
  "sent_at": "2026-03-04T13:00:00Z"
}
```

---

## 9. 배치 처리 API

### 9.1 대량 아이템 처리

```http
POST /api/v1/batch/process
Content-Type: application/json

{
  "action": "generate_content",
  "items": ["item_1", "item_2", ..., "item_100"],
  "batch_size": 10,
  "delay_seconds": 30,
  "account": "socialbuilders"
}
```

**응답**:
```json
{
  "batch_id": "batch_123",
  "total_items": 100,
  "batches": [
    {
      "batch_number": 1,
      "items": ["item_1", "item_2", ..., "item_10"],
      "status": "pending",
      "estimated_start": "2026-03-04T14:00:00Z"
    }
  ]
}
```

---

## 10. 상태 및 모니터링 API

### 10.1 시스템 상태 확인

```http
GET /api/v1/system/status
```

**응답**:
```json
{
  "status": "healthy",
  "components": {
    "llm_client": {
      "status": "healthy",
      "provider": "ollama",
      "latency_ms": 450
    },
    "vault": {
      "status": "healthy",
      "disk_usage": "65%"
    },
    "embedding": {
      "status": "healthy",
      "cache_hits": 85
    }
  },
  "timestamp": "2026-03-04T15:00:00Z"
}
```

### 10.2 워크플로우 실행 이력

```http
GET /api/v1/workflows/executions?
  workflow_name=daily_pipeline&
  limit=10&
  start_date=2026-03-01
```

**응답**:
```json
{
  "executions": [
    {
      "id": "exec_456",
      "workflow_name": "daily_pipeline",
      "status": "completed",
      "started_at": "2026-03-04T12:00:00Z",
      "completed_at": "2026-03-04T12:15:00Z",
      "duration_seconds": 900
    }
  ]
}
```

---

## 11. 오류 처리

### 오류 코드

| 코드 | 설명 |
|------|------|
| 400 | Bad Request - 요청 형식 오류 |
| 401 | Unauthorized - 인증 실패 |
| 403 | Forbidden - 접근 권한 없음 |
| 404 | Not Found - 리소스 없음 |
| 429 | Too Many Requests - 요청 한도 초과 |
| 500 | Internal Server Error - 서버 내부 오류 |
| 503 | Service Unavailable - 서비스 불가능 |

### 오류 응답 예시

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid account ID",
    "details": {
      "account_id": "invalid_account",
      "valid_accounts": ["socialbuilders", "tech_news"]
    },
    "timestamp": "2026-03-04T15:30:00Z"
  }
}
```

---

## 12. 속도 제한

- API 요당 1,000회 (분당)
- 배치 처리: 요청당 최대 1,000개 아이템
- 워크플로우 실행: 최대 동시 실행 10개

---

## 13. SDK 예시 (Python)

```python
import requests
from picko.api import PickoClient

# 클라이언트 초기화
client = PickoClient(api_key="your_api_key", base_url="https://api.picko.com")

# RSS 수집
result = client.collect_rss(
    urls=["https://techcrunch.com/feed/"],
    account="socialbuilders"
)

# 콘텐츠 생성
content = client.generate_longform(
    account="socialbuilders",
    item_id="item_123"
)

# 워크플로우 실행
execution = client.run_workflow(
    workflow_name="daily_pipeline",
    args={"account": "socialbuilders"}
)

# 상태 확인
status = client.check_workflow_status(execution_id="exec_123")
```

---

*API 문서에 대한 문의나 개선 제안은 GitHub Issues에 등록해 주세요.*
