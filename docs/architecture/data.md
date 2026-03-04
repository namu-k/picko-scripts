# 데이터 아키텍처

> **최종 수정**: 2026-03-04
> **대상 독자**: 개발자, 데이터 아키텍트
> **문서 성격**: 이 문서는 시스템의 **설계 개요**이며, 코드 메서드 시그니처와 정확히 일치하지 않을 수 있습니다. 정확한 API는 소스 코드를 참조하세요.

---

## 1. 개요

이 문서는 Picko 시스템의 데이터 아키텍처를 상세히 설명합니다. 데이터 모델, 저장소 아키텍처, 데이터 플로우를 다룹니다.

---

## 2. 데이터 모델

### 2.1 핵심 데이터 모델

#### 2.1.1 CollectedItem
**위치**: `picko/collectors/__init__.py`

```python
@dataclass
class CollectedItem:
    """수집된 콘텐츠의 표준화된 데이터 구조"""

    url: str
    title: str
    body: str
    source_id: str
    source_type: str          # "rss" | "perplexity" | "newsletter"
    published_at: str | None = None
    category: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)
```

**데이터 흐름**:
```
RSS/Perplexity → CollectedItem → Processing → Storage
```

#### 2.1.2 SourceMeta
**위치**: `picko/source_manager.py`

```python
@dataclass
class SourceMeta:
    """소스 메타데이터"""

    id: str                   # 소스 ID
    name: str                # 소스 이름
    type: str                # rss, perplexity, discovery
    url: str                 # 소스 URL
    category: str           # 카테고리 (tech, ai, startup)
    priority: int            # 우선순위 (1-5)
    last_collected: datetime # 마지막 수집 시간
    collect_config: dict     # 수집 설정
```

**소스 관리**:
```python
# 소스 예시
sources:
  - id: "techcrunch"
    name: "TechCrunch"
    type: "rss"
    url: "https://techcrunch.com/feed/"
    category: "tech"
    priority: 5
    collect_config:
      max_items: 10
      fetch_delay: 60
```

#### 2.1.3 VaultNote
**위치**: `picko/vault_io.py`

> **참고**: 현재 코드에는 `VaultNote` 데이터클래스가 없습니다. 실제 구현은 `VaultIO.read_note()`가 `tuple[dict, str]`(frontmatter, content)을 반환하는 방식입니다. 아래 모델은 설계 참고용 예시입니다.

```python
@dataclass
class VaultNote:
    """Obsidian Vault 노트 데이터 구조"""

    frontmatter: dict       # YAML 프론트매터
    content: str            # 마크다운 내용
    path: str               # 파일 경로

    # 계산된 속성
    word_count: int         # 단어 수
    reading_time: int      # 읽기 시간 (분)
    tags: List[str]         # 프론트매터 태그
```

**프론트매터 구조**:
```yaml
---
# Input 노트 예시
title: "AI가 미래를 바꾸는 방법"
url: "https://example.com/article"
source: "techcrunch"
published_at: "2026-03-04T10:00:00Z"
collected_at: "2026-03-04T10:05:00Z"
tags:
  - "AI"
  - "테크"
  - "미래"
writing_status: "auto_ready"
score:
  novelty: 0.8
  relevance: 0.9
  quality: 0.85
  final: 0.85
---
# 콘텐츠 내용
# ... 마크다운 내용 ...
```

#### 2.1.4 SourceCandidate
**위치**: `picko/discovery/base.py`

```python
@dataclass
class SourceCandidate:
    """발견된 새 소스 후보"""

    id: str                   # 후보 ID
    name: str                # 소스 이름
    url: str                 # 소스 URL
    platform: str            # 플랫폼 (reddit, mastodon, threads)
    description: str         # 설명
    relevance_score: float    # 관련도 점수
    confidence: float         # 신뢰도
    discovered_at: datetime  # 발견 시간
    metadata: dict           # 추가 정보
```

#### 2.1.5 VerificationResult
**위치**: `picko/quality/graph.py`

```python
@dataclass
class VerificationResult:
    """품질 검증 결과"""

    verdict: str             # approved, rejected, review
    confidence: float         # 신뢰도 (0.0-1.0)
    primary_score: float     # 1차 검증 점수
    cross_check_score: Optional[float]  # 2차 검증 점수
    feedback: str           # 피드백
    verified_at: datetime   # 검증 시간
```

---

## 3. 저장소 아키텍처

### 3.1 Obsidian Vault 기반 저장소

#### 3.1.1 Vault 구조

```
mock_vault/
├── Inbox/                    # 입력 저장소
│   ├── Inputs/              # 수집된 콘텐츠
│   │   ├── _digests/       # 일일 다이제스트
│   │   └── *.md            # 개별 아이템
│   ├── Perplexity/         # Perplexity 결과
│   │   ├── *.md
│   │   └── *.html
│   └── Processed/          # 처리된 파일 (아카이브)
├── Content/                 # 생성된 콘텐츠
│   ├── Longform/           # 롱폼 아티클
│   ├── Packs/              # 소셜 미디어 팩
│   └── Images/             # 생성된 이미지
├── Assets/                 # 자산
│   ├── Images/            # 이미지
│   │   ├── _prompts/      # 이미지 프롬프트
│   │   └── *.png          # 생성된 이미지
│   └── Videos/            # 동영상 (미래)
├── Archive/               # 아카이브
│   ├── Inputs/           # 오래된 입력
│   └── Content/          # 오래된 콘텐츠
├── Logs/                 # 로그
│   └── Publish/          # 게시 로그
└── Templates/           # 사용자 템플릿
```

#### 3.1.2 Vault 접근 패턴

```python
# 읽기 패턴
vault.read_note("Inbox/Inputs/item_001.md")
vault.list_notes("Inbox/Inputs", "*.md")
vault.find_notes_by_tag("Inbox/Inputs", "AI")

# 쓰기 패턴
vault.write_note("Content/Longform/article_001.md", content, frontmatter)
vault.update_frontmatter("Inbox/Inputs/item_001.md", {"writing_status": "auto_ready"})
vault.ensure_directory("Content/Packs/twitter")
```

### 3.2 임베딩 저장소

#### 3.2.1 임베딩 캐시 구조

```
cache/embeddings/
├── e3efcf0325e860f2.npy
├── b4b770fa8d4b3731.npy
├── f4c814ab12cdb1d5.npy
└── ...
```

현재 구현은 `EmbeddingManager`가 텍스트 해시 키 기반으로 `cache/embeddings/<hash>.npy` 파일을 직접 저장/조회합니다. `metadata/index.json` 구조는 사용하지 않습니다.

#### 3.2.2 임베딩 메타데이터 (설계 예시)

```json
{
  "index": {
    "total_embeddings": 1000,
    "dimensions": 1024,
    "last_updated": "2026-03-04T10:00:00Z",
    "sources": {
      "rss": 800,
      "perplexity": 200
    }
  },
  "stats": {
    "avg_similarity": 0.3,
    "max_similarity": 0.95,
    "min_similarity": 0.1
  }
}
```

### 3.3 캐시 시스템

#### 3.3.1 LLM 응답 캐시

```python
# 캐시 키 생성 패턴
cache_key = f"{prompt_hash}_{model}_{temperature}_{max_tokens}"

# 캐시 구조
cache/
├── llm_responses/
│   ├── {hash}.json
│   └── ...
└── ...
```

#### 3.3.2 설정 캐시

```python
# 설정 파일 캐시
cache/config/
├── config.yml.json
├── sources.json
└── accounts.json
```

---

## 4. 데이터 플로우

### 4.1 콘텐츠 파이프라인 데이터 플로우

```
1. 수집 단계
   RSS/Perplexity → CollectedItem → Vault/Inputs
   │
   ↓
2. 중복 제거
   EmbeddingManager → 유사도 계산 → 중복 아이템 필터링
   │
   ↓
3. NLP 처리
   LLMClient → 요약/태깅 → 프론트매터 업데이트
   │
   ↓
4. 스코어링
   ScoringCalculator → 다차원 평가 → 점수 계산
   │
   ↓
5. 품질 검증
   QualityGraph → 검증 상태 → Verdict
   │
   ↓
6. 생성 단계
   ContentGenerator → 다양한 형식 생성 → Content/
   │
   ↓
7. 게시 단계
   Publisher → 소셜 미디어 → Logs/Publish
```

### 4.2 데이터 상태 전이

```
CollectedItem 상태 전이:
collected → processed → scored → verified → generated → published

VaultNote 프론트매터 업데이트:
writing_status: pending → auto_ready → manual → completed
quality: null → scored → verified
```

### 4.3 배치 처리 데이터 플로우

```python
# 배치 처리 예시
batch_size = 10
delay = "10s"

items = vault.list("Inbox/Inputs", "writing_status=auto_ready")
batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]

for batch in batches:
    # 비동기 배치 처리
    await process_batch(batch)
    # 지연 시간 적용
    await asyncio.sleep(10)
```

---

## 5. 데이터 변환

### 5.1 원본 데이터 → 표준화 데이터

#### 5.1.1 RSS → CollectedItem

```python
# RSS 파싱 후 표준화
def rss_to_collected(rss_item: dict, source: str) -> CollectedItem:
    return CollectedItem(
        url=rss_item['link'],
        title=rss_item['title'],
        body=rss_item['description'],
        source_id=source,
        source_type='rss',
        published_at=rss_item.get('pubDate'),
        category='general',
        metadata={
            'author': rss_item.get('author'),
            'feed_category': rss_item.get('category'),
            'image_url': rss_item.get('image')
        }
    )
```

#### 5.1.2 Perplexity → CollectedItem

```python
# 파일에서 표준화
def file_to_collected(file_path: str) -> CollectedItem:
    content = read_file(file_path)
    metadata = extract_metadata(content)

    return CollectedItem(
        url=metadata.get('url', ''),
        title=metadata.get('title', 'Untitled'),
        body=content,
        source_id='perplexity',
        source_type='perplexity',
        published_at=datetime.now().strftime('%Y-%m-%d'),
        category='perplexity',
        metadata={
            'file_path': file_path,
            'file_type': get_file_type(file_path)
        }
    )
```

### 5.2 생성 데이터 → VaultNote

```python
# 생성된 콘텐츠 → VaultNote
def generated_to_vault(content: str, frontmatter: dict, path: str) -> VaultNote:
    return VaultNote(
        frontmatter=frontmatter,
        content=content,
        path=path,
        word_count=count_words(content),
        reading_time=calculate_reading_time(content),
        tags=frontmatter.get('tags', [])
    )
```

---

## 6. 데이터 일관성

### 6.1 ACID 원칙 적용

#### 6.1.1 원자성 (Atomicity)

```python
# 파일 쓰기 원자적 보장
def write_note_atomic(path: str, content: str, frontmatter: dict):
    temp_path = f"{path}.tmp"
    try:
        # 임시 파일에 쓰기
        write_file(temp_path, content, frontmatter)
        # 원자적으로 이동
        os.rename(temp_path, path)
    except Exception:
        # 실패 시 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
```

#### 6.1.2 일관성 (Consistency)

```python
# 프론트매터 유효성 검사
def validate_frontmatter(frontmatter: dict) -> bool:
    required_fields = ['title', 'url', 'source']
    return all(field in frontmatter for field in required_fields)
```

#### 6.1.3 격리성 (Isolation)

```python
# 파일 잠금
@contextmanager
def file_lock(path: str):
    lock_path = f"{path}.lock"
    lock = FileLock(lock_path)

    with lock.acquire(timeout=30):
        yield
```

#### 6.1.4 지속성 (Durability)

```python
# 백업 전략
def backup_file(path: str):
    if os.path.exists(path):
        backup_path = f"{path}.backup.{int(time.time())}"
        shutil.copy2(path, backup_path)
        return backup_path
```

### 6.2 데이터 정합성 검사

#### 6.2.1 정합성 검사 점검리스트

```python
# 데이터 정합성 점검
def check_data_integrity():
    checks = [
        # 파일 존재 여부
        check_file_exists,
        # 프론트매터 구조
        check_frontmatter_structure,
        # 중복 ID 확인
        check_duplicate_ids,
        # 임베딩 인덱스
        check_embedding_index,
        # 참조 무결성
        check_reference_integrity
    ]

    return all(check() for check in checks)
```

---

## 7. 데이터 보안

### 7.1 데이터 암호화

#### 7.1.1 정적 데이터 암호화

```python
# 민감 정보 암호화
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str) -> str:
    key = load_encryption_key()
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()
```

#### 7.1.2 전송 중 데이터 암호화

```python
# API 통신 암호화
async def secure_api_request(url: str, data: dict):
    # HTTPS 사용
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, ssl=True) as response:
            return await response.json()
```

### 7.2 접근 제어

#### 7.2.1 파일 시스템 접근 제어

```python
# Vault 접근 권한
class VaultAccessControl:
    def __init__(self, user: str):
        self.user = user
        self.permissions = self.load_permissions(user)

    def can_access(self, path: str) -> bool:
        return path.startswith(f"vault/{self.user}/") or \
               self.permissions.get('admin', False)
```

#### 7.2.2 API 접근 제어

```python
# LLM API 키 관리
class APIKeyManager:
    def __init__(self):
        self.keys = self.load_api_keys()

    def get_key(self, provider: str) -> str:
        key = self.keys.get(provider)
        if not key:
            raise APIKeyError(f"API key not found for {provider}")
        return key
```

---

## 8. 성능 고려사항

### 8.1 인덱싱 전략

#### 8.1.1 파일 시스템 인덱스

```python
# 빠른 파일 검색을 위한 인덱스
class FileSystemIndex:
    def __init__(self, vault_path: str):
        self.index = {}
        self.build_index(vault_path)

    def build_index(self, path: str):
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    self.index[file_path] = {
                        'modified': os.path.getmtime(file_path),
                        'size': os.path.getsize(file_path)
                    }
```

#### 8.1.2 메모리 캐싱

```python
# 메모리 캐시
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_note_cached(path: str) -> VaultNote:
    return vault_io.read_note(path)
```

### 8.2 쿼리 최적화

#### 8.2.1 Vault 쿼리 최적화

```python
# 복합 쿼리
def find_items_by_criteria(filters: dict) -> List[VaultNote]:
    # 1. 태그로 필터링
    items = self.find_by_tags(filters.get('tags', []))

    # 2. 날짜 범위로 필터링
    if 'date_range' in filters:
        items = [item for item in items
                if is_in_date_range(item.frontmatter['published_at'],
                                   filters['date_range'])]

    # 3. 점수로 필터링
    if 'min_score' in filters:
        items = [item for item in items
                if item.frontmatter.get('score', {}).get('final', 0)
                >= filters['min_score']]

    return items
```

### 8.3 메모리 관리

#### 8.3.1 대용량 파일 처리

```python
# 스트리밍 파일 읽기
def read_large_file(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            # 청크 단위 처리
            yield line
```

#### 8.3.2 메모리 풀링

```python
# 임베딩 벡터 풀링
class EmbeddingPool:
    def __init__(self, max_size=1000):
        self.pool = []
        self.max_size = max_size

    def get_embedding(self) -> np.ndarray:
        if self.pool:
            return self.pool.pop()
        else:
            return np.zeros((1024,))

    def return_embedding(self, embedding: np.ndarray):
        if len(self.pool) < self.max_size:
            self.pool.append(embedding)
```

---

## 9. 확장성

### 9.1 수평 확전을 위한 데이터 분할

#### 9.1.1 날짜 기반 분할

```python
# 날짜 기반 파일 시스템 구조
vault/
├── 2026/03/
│   ├── 01/
│   │   ├── Inputs/
│   │   └── Content/
│   └── 02/
│       ├── Inputs/
│       └── Content/
└── 2026/04/
    └── ...
```

#### 9.1.2 소스 기반 분할

```python
# 소스별 분할 구조
vault/
├── sources/
│   ├── techcrunch/
│   │   ├── Inputs/
│   │   └── Content/
│   ├── ai_news/
│   │   ├── Inputs/
│   │   └── Content/
```

### 9.2 분산 저장을 위한 데이터 레이아웃

```python
# 분산 저장을 위한 데이터 모델
@dataclass
class DistributedData:
    shard_id: str          # 샤드 ID
    node_id: str           # 노드 ID
    replication_factor: int  # 복제 인수
    data: dict             # 실제 데이터
```

---

*이 문서는 Picko 시스템의 데이터 아키텍처를 상세히 설명하며, 개발자가 데이터 모델과 플로우를 이해하고 최적화할 수 있도록 돕습니다.*
