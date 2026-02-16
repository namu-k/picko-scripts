# Picko 파이프라인 실제 데이터 테스트 리포트

- **테스트 일시**: 2026-02-16 (일) 11:10 ~ 11:22
- **테스트 환경**: Windows 10 (10.0.26100)
- **Python**: 3.13.5, 가상환경 `.venv` 사용

---

## 1. 환경 점검

### 1.1 소프트웨어 및 의존성

| 항목 | 상태 | 비고 |
|------|------|------|
| Python 3.13.5 | OK | pyproject.toml 요구사항 충족 |
| 가상환경 `.venv` | OK | 활성화 확인 |
| 핵심 패키지 (feedparser, httpx, jinja2, loguru, yaml) | OK | 모두 import 성공 |
| ollama 패키지 | OK | import 성공 |
| sentence-transformers 패키지 | OK | import 성공 |

### 1.2 API 키

| 키 | 상태 | 영향 |
|----|------|------|
| `OPENAI_API_KEY` | **미설정** | writer_llm 사용 불가, 폴백 불가 |
| `OPENROUTER_API_KEY` | **미설정** | OpenRouter 사용 불가 |

### 1.3 로컬 LLM (Ollama)

| 항목 | 상태 | 비고 |
|------|------|------|
| Ollama 서버 | OK (200) | `http://localhost:11434` 응답 |
| 설치된 모델 | `qwen2.5:3b`, `gemma3:4b`, `mxbai-embed-large`, `qwen3-embedding:0.6b` | |
| config 지정 모델 `deepseek-r1:7b` | **미설치** | 404 에러 발생 |

> **조치**: 테스트를 위해 `config.yml`의 `summary_llm.model`을 `qwen2.5:3b`으로 임시 변경 후 진행.
> 테스트 종료 후 원래 값(`deepseek-r1:7b`)으로 복원 완료.

---

## 2. Health Check (`scripts.health_check`)

```
============================================================
Health Check Report - 2026-02-16 11:10:33
============================================================

✅ Vault Access: Read/Write OK
   └─ c:\picko-scripts\mock_vault
❌ OpenAI API Key: Not set (OPENAI_API_KEY)
   └─ Set environment variable
✅ RSS Sources: All 3 sources accessible
✅ Directories: All 5 directories exist
✅ Disk Space: 98.2 GB available

============================================================
Summary: 4 passed, 1 failed
============================================================
```

| 체크 항목 | 결과 | 상세 |
|-----------|------|------|
| Vault Access | PASS | mock_vault 읽기/쓰기 정상 |
| OpenAI API Key | **FAIL** | 환경변수 미설정 |
| RSS Sources | PASS | 3개 소스 모두 접근 가능 |
| Directories | PASS | 5개 디렉터리 존재 |
| Disk Space | PASS | 98.2 GB 가용 |

---

## 3. daily_collector --dry-run (1차: 모델 미설치)

**명령어**: `python -m scripts.daily_collector --dry-run`

| 단계 | 결과 | 상세 |
|------|------|------|
| RSS 수집 | 52건 | techcrunch + hacker_news + ai_news |
| 중복 제거 후 | 52건 | 중복 0건 |
| Fetch (본문 추출) | 39건 성공 | 13건 실패 (timeout, 403 등) |
| NLP (요약/태깅) | **0건** | `deepseek-r1:7b` 미설치 → 404, 폴백도 API 키 없어 실패 |
| Embedding | 미실행 | NLP 실패로 도달 못함 |
| Export | 0건 | dry-run이므로 정상 |

**최종 결과**: Collected 52 / Processed 0 / Exported 0

---

## 4. daily_collector --dry-run (2차: 모델 변경 후)

**조치**: `summary_llm.model`을 `qwen2.5:3b`으로 변경
**명령어**: `python -m scripts.daily_collector --dry-run`
**소요 시간**: 약 4분 (236초)

| 단계 | 결과 | 상세 |
|------|------|------|
| RSS 수집 | 52건 | 동일 |
| 중복 제거 후 | 52건 | |
| Fetch | 39건 성공 | WashingtonPost timeout 포함 13건 실패 |
| NLP (요약/태깅) | **39건 성공** | qwen2.5:3b로 요약, 태깅, 핵심포인트 추출 |
| Embedding | **성공** | BAAI/bge-m3 로컬 모델 로딩 후 임베딩 완료 |
| Scoring | 39건 | novelty/relevance/quality 점수 산출 |
| Export | 0건 | dry-run이므로 정상 |

**최종 결과**: Collected 52 / Processed 39 / Exported 0

> **참고**: `OPENAI_API_KEY` 미설정 WARNING이 반복 출력되지만, 이는 폴백 설정 확인 시 발생하는 것으로 실제 동작에는 영향 없음 (Ollama가 정상 처리).

---

## 5. daily_collector 실제 수집

**명령어**: `python -m scripts.daily_collector --date 2026-02-16`
**소요 시간**: 약 69초

| 단계 | 결과 | 상세 |
|------|------|------|
| RSS 수집 | 40건 | 이전 실행 캐시로 일부 중복 제거됨 |
| Fetch | 39건 | |
| NLP + Embedding + Scoring | 39건 처리 | |
| Export (Input 노트 생성) | **33건** | mock_vault/Inbox/Inputs/에 33개 .md 파일 생성 |
| Digest 생성 | **성공** | `_digests/2026-02-16.md` 생성 |

**최종 결과**: Collected 40 / Processed 39 / Exported 33

### 생성된 파일 목록

**Digest**: `mock_vault/Inbox/Inputs/_digests/2026-02-16.md` (33개 항목 포함)

**Input 노트 (33건)**: `mock_vault/Inbox/Inputs/input_*.md`

### Digest 샘플 (상위 3개 항목)

| 순위 | 제목 | Score | 소스 |
|------|------|-------|------|
| 1 | As AI data centers hit power limits, Peak XV backs Indian startup C2i | 0.57 (N:1.0 R:0.3 Q:0.5) | techcrunch |
| 2 | Hideki Sato, designer of all Sega's consoles, has died | 0.51 (N:0.61 R:0.3 Q:0.7) | hacker_news |
| 3 | Pink noise reduces REM sleep and may harm sleep quality | 0.51 (N:0.58 R:0.3 Q:0.7) | hacker_news |

### Input 노트 구조 확인 (샘플: input_5a2c5ab9da1e)

```yaml
# Frontmatter
id: input_5a2c5ab9da1e
title: "As AI data centers hit power limits..."
source: techcrunch
source_url: "https://techcrunch.com/..."
score: { total: 0.57, novelty: 1.0, relevance: 0.3, quality: 0.5 }
tags: [ai, data_center, power_loss, sustainability, investment, c2i]
writing_status: pending
status: inbox
```

```markdown
# 본문 구조
- 소스 정보 callout
- 글쓰기 방법 선택 체크박스 (자동 작성 / 수동 작성)
- 요약 섹션
- 핵심 포인트 섹션
- 원문 (추출된 본문)
```

---

## 6. generate_content (콘텐츠 생성)

**명령어**: `python -m scripts.generate_content --date 2026-02-16 --auto-all`
**결과**: **전체 실패** (API 키 미설정)

| 항목 | 결과 |
|------|------|
| 대상 항목 | 33건 (--auto-all로 전체 시도) |
| 성공 | 0건 |
| 실패 | 33건 |
| 에러 | `401 Unauthorized` - "You didn't provide an API key" |

> **원인**: `writer_llm`이 `openai` provider로 설정되어 있으나 `OPENAI_API_KEY` 미설정.
> **해결 방법**: `OPENAI_API_KEY` 설정 후 재실행, 또는 `writer_llm`을 Ollama로 변경.

---

## 7. validate_output (콘텐츠 검증)

기존 mock_vault에 있던 샘플 콘텐츠로 검증 실행.

### Longform 검증

```
============================================================
Validation Report
============================================================
Total Files:   1
Valid:         1
Invalid:       0
============================================================

✓ mock_vault\Content\Longform\longform_input_7ce483b7a9e4.md
```

### Packs 검증

```
============================================================
Validation Report
============================================================
Total Files:   3
Valid:         3
Invalid:       0
============================================================

✓ mock_vault\Content\Packs\linkedin\pack_input_7ce483b7a9e4_linkedin.md
✓ mock_vault\Content\Packs\newsletter\pack_input_7ce483b7a9e4_newsletter.md
✓ mock_vault\Content\Packs\twitter\pack_input_7ce483b7a9e4_twitter.md
```

| 콘텐츠 유형 | 파일 수 | Valid | Invalid |
|-------------|---------|-------|---------|
| Longform | 1 | 1 | 0 |
| Packs | 3 | 3 | 0 |
| **합계** | **4** | **4** | **0** |

---

## 8. 전체 파이프라인 요약

```
                        상태        비고
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Health Check         4/5 PASS   API 키만 미설정
2. RSS 수집             ✅ 성공     52건 수집
3. 중복 제거            ✅ 성공     52 → 52 (중복 0)
4. Fetch (본문 추출)    ✅ 39건     일부 사이트 접근 불가 (13건)
5. NLP (요약/태깅)      ✅ 39건     qwen2.5:3b 로컬 사용
6. Embedding            ✅ 39건     BAAI/bge-m3 로컬 사용
7. Scoring              ✅ 39건     novelty/relevance/quality 산출
8. Export + Digest      ✅ 33건     Input 노트 + Digest 생성 완료
9. Content Generation   ❌ 실패     OPENAI_API_KEY 미설정 (401)
10. Validation          ✅ 4/4      기존 콘텐츠 전부 PASS
```

---

## 9. 발견된 이슈 및 권장 조치

### 즉시 조치 필요

| # | 이슈 | 심각도 | 해결 방법 |
|---|------|--------|----------|
| 1 | `OPENAI_API_KEY` 미설정 | **높음** | 환경변수 설정 또는 `.env` 파일 사용 |
| 2 | `deepseek-r1:7b` 미설치 | **중간** | `ollama pull deepseek-r1:7b` 실행, 또는 config에서 `qwen2.5:3b`로 변경 |

### 개선 권장

| # | 이슈 | 비고 |
|---|------|------|
| 3 | NLP 요약이 일부 일본어/중국어 혼재 | qwen2.5:3b 모델의 한국어 지시 따르기 한계. 더 큰 모델(7b+) 또는 프롬프트 개선 권장 |
| 4 | Fetch 실패 13건 (25%) | WashingtonPost 등 봇 차단 사이트. User-Agent 설정 또는 fallback 크롤러 고려 |
| 5 | `XMLParsedAsHTMLWarning` | `lxml` XML 파서 사용 권장 (코드에서 `features="xml"` 지정) |
| 6 | `validate_output` CLI에서 `--path` 플래그 미지원 | USER_GUIDE 문서와 실제 CLI 불일치 (positional argument임) |

---

## 10. 전체 파이프라인을 완주하려면?

현재 환경에서 **수집 → NLP → 임베딩 → 점수 → 내보내기**까지는 완벽히 동작합니다.
**콘텐츠 생성(generate_content)**만 API 키가 필요합니다.

```powershell
# 1. API 키 설정 (아래 중 택 1)
set OPENAI_API_KEY=sk-your-key-here
# 또는
set OPENROUTER_API_KEY=sk-or-your-key-here  # config에서 writer_llm.provider를 openrouter로 변경

# 2. (선택) 요약 모델 변경 - deepseek-r1:7b가 없으면
# config/config.yml에서 summary_llm.model을 "qwen2.5:3b"로 변경

# 3. 전체 파이프라인 실행
python -m scripts.daily_collector --date 2026-02-16
# → Digest에서 항목 체크 후
python -m scripts.generate_content --date 2026-02-16
python -m scripts.validate_output Content/Longform/ --recursive --verbose
```
