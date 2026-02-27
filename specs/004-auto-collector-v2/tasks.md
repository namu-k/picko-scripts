# Auto Collector V2 - 구현 태스크

## 의존성 맵

```
┌────────────┬──────────────────┐
│    Task    │       의존       │
├────────────┼──────────────────┤
│ 0a, 0b, 0c │ 없음 (병렬 가능) │
├────────────┼──────────────────┤
│ 1          │ 0a               │
├────────────┼──────────────────┤
│ 1a         │ 1                │
├────────────┼──────────────────┤
│ 1b         │ 1                │
├────────────┼──────────────────┤
│ 2          │ 0b               │
├────────────┼──────────────────┤
│ 2a         │ 2                │
├────────────┼──────────────────┤
│ 3          │ 0a               │
├────────────┼──────────────────┤
│ 3a         │ 3                │
├────────────┼──────────────────┤
│ 4          │ 0b, 2, 2a        │
├────────────┼──────────────────┤
│ 5          │ 0a~4 전체        │
├────────────┼──────────────────┤
│ 5a         │ 5                │
├────────────┼──────────────────┤
│ 6          │ 4                │
└────────────┴──────────────────┘
```

---

## Phase 0: 기반 작업

### Task 0a: SourceManager 구현
**파일:** `picko/source_manager.py`
**의존성:** 없음

**단계:**
1. `SourceMeta` dataclass 정의 (기존 필드 + V2 확장 필드)
2. `SourceManager` 클래스 구현:
   - `load()` - sources.yml 로드 (기존 형식/V2 형식 모두 지원)
   - `save()` - 소스 저장 (불필요한 null 필드 제거)
   - `add_candidate()` - pending 상태로 후보 추가
   - `approve()` / `reject()` - 승인/거부
   - `update_stats()` - 메타데이터 갱신
3. 기존 `config/sources.yml` 구조와 호환되는지 확인

**검증:**
```bash
python -c "from picko.source_manager import SourceManager; sm = SourceManager(Path('config/sources.yml')); print(len(sm.load()))"
```

---

### Task 0b: BaseCollector 인터페이스 + RSSCollector 추출
**파일:** `picko/collectors/__init__.py`, `picko/collectors/rss.py`
**의존성:** 없음

**단계:**
1. `picko/collectors/` 디렉토리 생성
2. `picko/collectors/__init__.py`:
   - `CollectedItem` dataclass 정의
   - `BaseCollector` ABC 정의 (`collect()`, `name()`)
3. `picko/collectors/rss.py`:
   - `RSSCollector` 클래스 구현
   - 기존 `DailyCollector._ingest()` 로직 추출
   - `feedparser` 사용하여 RSS 파싱
4. 기존 `daily_collector.py`에 임시로 RSSCollector 사용하도록 수정 (점진적)
5. 하위호환 검증:
   - 기존 `daily_collector.py`를 RSSCollector 사용하도록 수정 후
   - 기존 `--account socialbuilders` 실행 결과가 수정 전과 동일한지 확인

**검증:**
```bash
# 인터페이스 임포트 확인
python -c "from picko.collectors import BaseCollector, CollectedItem; from picko.collectors.rss import RSSCollector; print('OK')"

# 하위호환: 기존 daily_collector 정상 동작 확인
python -m scripts.daily_collector --account socialbuilders --dry-run
```

---

### Task 0c: _load_existing_embeddings TODO 수정
**파일:** `scripts/daily_collector.py`
**의존성:** 없음

**단계:**
1. `_load_existing_embeddings()` 메서드 분석
2. `.npy` 캐시 파일 위치 확인 (`data/embeddings/` 또는 유사 경로)
3. 실제 임베딩 로드 로직 구현
4. 빈 리스트 반환 문제 수정

**검증:**
```bash
python -c "
from scripts.daily_collector import DailyCollector
# 임베딩 파일이 있는 경우 실제 로드 확인
collector = DailyCollector('socialbuilders')
embeddings = collector._load_existing_embeddings()
print(f'Loaded {len(embeddings)} embeddings')
"
```

---

## Phase 1: 소스 자동 발견

### Task 1: source_discovery.py 핵심 로직
**파일:** `scripts/source_discovery.py`
**의존성:** Task 0a (SourceManager)

**단계:**
1. `SourceDiscovery` 클래스 구현:
   - `__init__()` - AccountContextLoader, SourceManager, LLMClient 초기화
   - `run()` - 전체 발견 파이프라인 실행
2. `_search_google_news_rss()`:
   - Google News RSS에서 키워드 검색
   - 결과 기사들의 원본 도메인 추출
   - `/feed`, `/rss` 경로 프로빙
3. `_search_tavily()`:
   - Tavily API로 '{keyword} RSS feed' 검색
   - RSS 피드 링크 추출
   - 레이트 리밋: 1 req/sec
4. `_probe_rss_url()`:
   - 도메인에서 RSS 피드 URL 자동 탐지
5. `_evaluate_batch()`:
   - LLM으로 관련성 평가 (배치 처리)
   - 임계값 0.6 이상만 후보로 추가
6. 중복 제거 로직 (기존 소스 URL과 비교)
7. 레이트 리밋 구현:
   - Tavily: `time.sleep(1)` + 일일 카운터 (최대 1000회)
   - Google News RSS: 키워드당 최대 1회 요청, 결과를 메모리 캐싱
   - 모든 외부 호출에 timeout 설정 (10초)

**검증:**
```bash
python -m scripts.source_discovery --account socialbuilders --dry-run --keywords "스타트업"
```

---

### Task 1a: Substack 뉴스레터 발견 추가
**파일:** `scripts/source_discovery.py`
**의존성:** Task 1

**단계:**
1. `_search_substack()` 메서드 추가:
   - Substack 검색 페이지 스크래핑
   - `/feed` 경로에서 RSS URL 생성
   - `type='newsletter'`로 분류
2. try/except + 로깅 (비공식 API 대응)
3. 5초 간격 레이트 리밋

**검증:**
```bash
python -m scripts.source_discovery --account socialbuilders --dry-run --keywords "PMF,product"
```

---

### Task 1b: 발견 결과 저장 및 CLI
**파일:** `scripts/source_discovery.py`, `data/discovery/`
**의존성:** Task 1

**단계:**
1. `data/discovery/` 디렉토리 구조 생성
2. `latest_run.yml` 저장 로직
3. 날짜별 로그 파일 저장 + 30일 초과 로그 자동 삭제:
   - `data/discovery/logs/YYYY-MM-DD.log` 형식
   - 실행 시 30일 이전 로그 파일 glob → 삭제
4. CLI 인터페이스 구현:
   - `--account` (필수)
   - `--dry-run`
   - `--keywords`
   - `--review` (pending 후보 목록 출력)
   - `--approve SOURCE_ID [...]`
   - `--reject SOURCE_ID [...]`

**검증:**
```bash
python -m scripts.source_discovery --account socialbuilders
python -m scripts.source_discovery --review --account socialbuilders
python -m scripts.source_discovery --approve candidate_001
```

---

## Phase 2: Perplexity 결과 수집

### Task 2a: collectors.yml 설정
**파일:** `config/collectors.yml`
**의존성:** 없음

**단계:**
1. `config/collectors.yml` 생성
2. Perplexity 설정 추가:
   - `enabled`
   - `input_dir`
   - `archive_dir`
   - `file_patterns`

**검증:**
```bash
python -c "import yaml; print(yaml.safe_load(open('config/collectors.yml')))"
```

---

### Task 2: PerplexityCollector 구현
**파일:** `picko/collectors/perplexity.py`
**의존성:** Task 0b, Task 2a (collectors.yml 먼저 생성 권장)

**단계:**
1. `PerplexityCollector` 클래스 구현:
   - `__init__(input_dir, archive_dir)` — config/collectors.yml의 perplexity 섹션에서 경로를 받음
   - `collect()` - 미처리 파일 스캔 → 파싱 → CollectedItem 변환
   - `name()` - "perplexity" 반환
2. `_parse_perplexity_md()`:
   - 마크다운 파싱
   - 제목: 첫 번째 # 헤딩 또는 파일명
   - 본문: 전체 텍스트
   - 링크: 본문 내 URL 추출
3. 처리 완료 파일을 archive_dir로 이동

**검증:**
```bash
# 테스트 파일 생성
mkdir -p Inbox/Perplexity
echo "# Test Perplexity Result\n\nContent here with https://example.com" > Inbox/Perplexity/test.md

python -c "
from picko.collectors.perplexity import PerplexityCollector
from pathlib import Path
collector = PerplexityCollector(Path('Inbox/Perplexity'), Path('Archive/Perplexity'))
items = collector.collect('socialbuilders')
print(f'Collected {len(items)} items')
"
```

---

## Phase 3: 소스 품질 관리

### Task 3: source_curator.py 구현
**파일:** `scripts/source_curator.py`
**의존성:** Task 0a (SourceManager)

**단계:**
1. `SourceCurator` 클래스 구현:
   - `__init__(source_manager, config)`
   - `evaluate_all()` - 모든 활성 소스 품질 메트릭 계산
   - `apply_rules()` - 규칙 적용 ("disable" | "review" | "trusted" | None)
   - `report()` - 소스별 품질 리포트 생성
   - `cleanup()` - 저품질 소스 비활성화
2. 메트릭 계산:
   - `relevance_score` - ContentScorer.relevance 재사용
   - `quality_score` - ContentScorer.quality 재사용
   - `freshness` - last_collected 기반
   - `signal_noise_ratio` - exported_count / total_fetched

**검증:**
```bash
python -m scripts.source_curator --report
python -m scripts.source_curator --cleanup --dry-run
```

---

### Task 3a: 품질 규칙 설정
**파일:** `config/collectors.yml` (quality_rules 섹션)
**의존성:** Task 3

**단계:**
1. `quality_rules` 섹션 추가:
   - `min_relevance_score: 0.6`
   - `min_quality_score: 0.5`
   - `max_inactive_days: 30`
   - `min_signal_noise_ratio: 0.2`
   - `trusted_threshold_quality: 0.9`
   - `trusted_threshold_count: 50`
2. CLI 인터페이스:
   - `--report`
   - `--cleanup [--dry-run]`
   - `--status`
   - `--approve SOURCE_ID`
   - `--reject SOURCE_ID`

**검증:**
```bash
python -m scripts.source_curator --status
```

---

## Phase 4: 통합 수집 파이프라인

### Task 4: daily_collector.py 컬렉터 통합
**파일:** `scripts/daily_collector.py`
**의존성:** Task 0b, Task 2, Task 2a

**단계:**
1. `_load_collectors()` 메서드 추가:
   - collectors.yml 기반 활성 컬렉터 로드
   - `_is_enabled(collector_name)` 헬퍼: collectors.yml에서 enabled 플래그 확인
   - 없으면 기존 RSS 전용 동작 (하위호환)
2. `_ingest()` 수정:
   - 모든 컬렉터 실행 후 통합
   - 한 컬렉터 실패해도 나머지 계속 실행
3. 기존 8단계 파이프라인 유지:
   - `_ingest()`만 BaseCollector 기반으로 교체
   - `_dedupe`, `_fetch`, `_nlp_process`, `_embed`, `_score`, `_export`, `_create_digest` 유지

**검증:**
```bash
python -m scripts.daily_collector --account socialbuilders
# RSS + Perplexity 통합 수집 확인
```

---

## Phase 5: 테스트

### Task 5: 단위 테스트 작성
**파일:** `tests/`
**의존성:** Task 0a~4 전체

**단계:**
1. `tests/test_source_manager.py`:
   - CRUD 테스트 — `tmp_path` fixture로 임시 sources.yml 생성
   - 하위호환 로딩 테스트 — V2 필드 없는 YAML fixture
   - V2 필드 optional 테스트
2. `tests/test_collectors.py`:
   - RSSCollector 테스트 — `responses` 라이브러리로 HTTP mock
   - PerplexityCollector 테스트 — `tmp_path`에 테스트 .md 파일 생성
   - BaseCollector 인터페이스 테스트
3. `tests/test_source_discovery.py`:
   - 키워드 추출 테스트 — `unittest.mock.patch` on AccountContextLoader
   - 중복 제거 테스트
   - LLM 평가 mock 테스트 — `unittest.mock.patch` on LLMClient
   - 외부 API mock — `responses`로 Google News RSS, Tavily HTTP mock
4. `tests/test_source_curator.py`:
   - 규칙 적용 테스트 — 다양한 SourceMeta fixture (경계값 포함)
   - 리포트 생성 테스트

**검증:**
```bash
pytest tests/ -v --cov=picko --cov=scripts --cov-report=term-missing
```

---

### Task 5a: 통합 테스트 작성
**파일:** `tests/integration/`
**의존성:** Task 5

**단계:**
1. 기존 sources.yml 하위호환 테스트
2. 발견 → 승인 → 수집 플로우 테스트
3. 컬렉터 실패 격리 테스트

**검증:**
```bash
pytest tests/integration/ -v
```

---

## Phase 6: CI/CD

### Task 6: GitHub Actions 워크플로우
**파일:** `.github/workflows/auto_collect.yml`
**의존성:** Task 4

**단계:**
1. `.github/workflows/auto_collect.yml` 생성
2. daily-collect job:
   - 트리거: cron `0 23 * * *` (매일 08:00 KST) + workflow_dispatch
   - Python 3.13 + `pip install -e .`
   - `python -m scripts.daily_collector --account socialbuilders`
   - 환경변수: OPENAI_API_KEY, TAVILY_API_KEY
3. weekly-discover job:
   - 트리거: cron `0 21 * * 0` (매주 일요일 06:00 KST)
   - `python -m scripts.source_discovery --account socialbuilders --dry-run`
   - 환경변수: TAVILY_API_KEY
4. Secrets 설정 필요 목록: OPENAI_API_KEY, TAVILY_API_KEY

**검증:**
```bash
# 워크플로우 문법 확인
python -c "import yaml; yaml.safe_load(open('.github/workflows/auto_collect.yml'))"
```

---

## MVP 범위 외 (의도적 제외)

- `picko/collectors/newsletter.py` — Plan §2.1에 Phase 3+ 예정으로 명시, 본 태스크 범위 아님
- Gmail API 직접 연동
- feedly/RSSHub 통합
- 팟캐스트 트랜스크립션
- 자동 승인 (항상 수동 승인 필요)
- consistency_score (히스토리 데이터 축적 후)

---

## 체크리스트

### 구현 전
- [x] 현재 브랜치가 `004-auto-collector-v2`인지 확인
- [x] 기존 `config/sources.yml` 백업
- [x] 기존 테스트 통과 확인 (`pytest`)

### Phase 0 완료 후
- [x] SourceManager로 기존 sources.yml 로드/저장 확인
- [x] RSSCollector 단독 실행 확인
- [x] _load_existing_embeddings 수정 확인
- [x] 하위호환: 기존 daily_collector 정상 동작 확인

### Phase 1 완료 후
- [x] dry-run으로 소스 발견 실행
- [x] pending 후보가 sources.yml에 추가되는지 확인
- [x] 승인/거부 CLI 동작 확인
- [x] 30일 로그 자동 삭제 동작 확인

### Phase 2 완료 후
- [x] Perplexity 폴더에 테스트 파일 넣고 수집 확인
- [x] 처리 완료 파일이 archive로 이동하는지 확인

### Phase 3 완료 후
- [x] 품질 리포트 생성 확인
- [x] cleanup --dry-run으로 저품질 소스 식별

### Phase 4 완료 후
- [x] 통합 daily_collector 실행
- [x] 기존 동작과 동일한지 확인 (하위호환)
- [x] 컬렉터 1개 실패 시 나머지 정상 동작 확인

### Phase 5 완료 후
- [x] 전체 테스트 통과
- [x] 테스트 커버리지 85% 이상

- [x] Secrets 설정 문서화
- [x] workflow_dispatch 수동 실행 테스트 (DEPLOYMENT.md에 절차 문서화, YAML 검증 완료)
- [x] Secrets 설정 문서화 (DEPLOYMENT.md Auto Collection Workflow 섹션 추가)
