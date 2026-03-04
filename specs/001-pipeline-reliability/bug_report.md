# 버그 리포트 — 벤치마크 시나리오 테스트

> **실행 일시**: 2026-02-18  
> **테스트 환경**: Windows 11, Python 3.13.5  
> **테스트 범위**: E2E 시나리오 S1-S8, Feature 시나리오 F1-F9  
> **픽스 지시문**: [bug_fix_instructions.md](./bug_fix_instructions.md)

---

## 1. 테스트 결과 요약

### 1.1 통과한 시나리오

| 시나리오 | 상태 | 비고 |
|---------|------|------|
| F4 (프롬프트 로더) | ✅ 통과 | longform, image, Jinja2 렌더링 정상 |
| F6 (헬스체크) | ✅ 통과 | 모든 항목 통과 |
| F7 (스코어링) | ✅ 통과 | 16개 단위 테스트 전부 통과 |
| F8 (임베딩·캐시) | ✅ 통과 | Ollama + 폴백 정상 동작 |
| F3 (style_extractor) | ✅ 통과 | 스크립트 정상 실행 (URL 필요) |
| S4 (단일 소스) | ✅ 통과 | 40개 항목 수집 성공 |
| S5 (전체 소스) | ✅ 통과 | dry-run 정상 완료 |
| S6 (재생성) | ✅ 통과 | --force로 5개 항목 재생성 성공 |
| S7 (주간 슬롯) | ✅ 통과 | WeeklySlot 로드 및 CTA 적용 확인 |

### 1.2 문제 발견 시나리오

| 시나리오 | 상태 | 버그 ID |
|---------|------|---------|
| S1 (고밀도 기술) | ⚠️ 타임아웃 | BUG-002 |
| F1 (레퍼런스 계정) | ❌ 실패 | BUG-003, BUG-004 |
| F5 (validate_output) | ⚠️ 문서 불일치 | BUG-001 |
| generate_content | ⚠️ 경고 | BUG-005 |

---

## 2. 발견된 버그 상세

### BUG-001: validate_output.py CLI 인자 문서 불일치

**심각도**: 🟡 Low (문서/호환성)

**증상**:
```bash
$ python -m scripts.validate_output --path Content/Longform/ --recursive
validate_output.py: error: unrecognized arguments: --path
```

**원인**:
- 시나리오 YAML 파일들(`f5-validate-output.yml`, `f9-digest-input-structure.yml` 등)에서 `--path` 옵션 사용
- 실제 `validate_output.py`는 위치 인자(positional argument)로 `path`를 받음

**영향받는 파일**:
- `tests/benchmarks/scenarios/features/f5-validate-output.yml`
- `tests/benchmarks/scenarios/features/f9-digest-input-structure.yml`
- `tests/benchmarks/scenarios/e2e/s1-high-density-tech.yml` (validate 명령어)
- 기타 모든 시나리오의 validate 명령어 섹션

**해결 방안**:
1. **옵션 A**: `validate_output.py`에 `--path` 옵션 추가 (권장 - 기존 문서 호환)
2. **옵션 B**: 모든 시나리오 YAML 파일에서 `--path`를 위치 인자로 변경

**수정 예시 (옵션 A)**:
```python
# scripts/validate_output.py
parser.add_argument('--path', '-p', dest='path', help='검증할 경로')
parser.add_argument('path_arg', nargs='?', help='검증할 경로 (위치 인자)')

# 인자 처리
path = args.path or args.path_arg
```

---

### BUG-002: S1 고밀도 기술 기사 시나리오 타임아웃

**심각도**: 🟠 Medium (성능)

**증상**:
```bash
$ python -m scripts.daily_collector --date 2026-02-16 --sources techcrunch ai_news hacker_news --dry-run
# 120초 후 타임아웃으로 종료
<bash_metadata>
bash tool terminated command after exceeding timeout 120000 ms
</bash_metadata>
```

**원인 추정**:
- 3개 소스(`techcrunch`, `ai_news`, `hacker_news`) 동시 수집 시 처리 시간 과다
- NLP 처리(요약/태깅) 또는 콘텐츠 추출 단계에서 지연

**영향**:
- S1 시나리오 벤치마크 실행 불가
- 대규모 수집 시 전체 파이프라인 지연

**해결 방안**:
1. 타임아웃 증가 (임시 조치)
2. 소스별 순차 처리 옵션 추가
3. NLP 처리 병렬화 개선
4. 수집 항목 수 제한 옵션(`--max-items`) 추가

---

### BUG-003: 계정 프로필 account_id 불일치

**심각도**: 🔴 High (기능 손상)

**증상**:
```python
>>> from picko.account_context import get_style_for_account
>>> style = get_style_for_account('builders_social_club')
[WARNING] Account profile not found: builders_social_club
>>> print(style)
None
```

**원인**:
- 테스트/문서에서 사용하는 계정 ID: `builders_social_club`
- 실제 계정 프로필 파일명: `socialbuilders.yml`
- `config.get_account(account_id)`가 `{account_id}.yml` 파일을 찾음

**영향받는 파일**:
- `tests/benchmarks/scenarios/features/f1-reference-account.yml` (계정 ID: `builders_social_club`)
- `picko/account_context.py` → `get_style_for_account()` 함수

**해결 방안**:
1. **옵션 A**: 파일명을 `builders_social_club.yml`로 변경
2. **옵션 B**: 시나리오 YAML의 계정 ID를 `socialbuilders`로 변경
3. **옵션 C**: 계정 프로필 파일 내 `account_id` 필드로 매핑 (검색 로직 변경 필요)

**현재 상태**:
```
mock_vault/config/accounts/
└── socialbuilders.yml  ← 실제 파일

테스트에서 찾는 파일:
mock_vault/config/accounts/builders_social_club.yml  ← 존재하지 않음
```

---

### BUG-004: 계정 프로필 YAML 파싱 문제

**심각도**: 🔴 High (기능 손상)

**증상**:
```python
>>> from picko.config import get_config
>>> config = get_config()
>>> account = config.get_account('socialbuilders')  # 파일은 찾음
>>> print('account_id:', account.get('account_id'))
account_id: None
>>> print('style_name:', account.get('style_name'))
style_name: None
```

**원인**:
- `socialbuilders.yml` 파일이 YAML 형식이지만, 최상위 키 구조가 예상과 다를 수 있음
- `yaml.safe_load()` 결과가 제대로 딕셔너리로 반환되지 않음

**파일 내용 분석**:
```yaml
# socialbuilders.yml 구조
account_id: socialbuilders
name: "빌더스소셜클럽"
style_name: founder_tech_brief
interests:
  primary: [...]
  secondary: [...]
...
```

**원인 분석**:
- YAML 파일 자체는 정상적으로 보임
- `config.get_account()` 호출 시 파일이 로드되지만 반환값이 비어있음
- 가능성: 캐시 문제 또는 파일 경로 문제

**검증 필요**:
```python
import yaml
with open('mock_vault/config/accounts/socialbuilders.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
    print(data)  # 직접 로드 테스트
```

---

### BUG-005: generate_content 기본 계정 프로필 없음

**심각도**: 🟡 Low (경고)

**증상**:
```bash
$ python -m scripts.generate_content --date 2026-02-16 --force
[WARNING] Account profile not found: default
```

**원인**:
- `generate_content.py`에서 계정 ID를 지정하지 않으면 `default` 사용
- `default.yml` 계정 프로필 파일이 존재하지 않음

**영향**:
- 기본 계정으로 콘텐츠 생성 시 스타일/톤 일관성 보장 안 됨
- 명시적 오류는 아니지만, 의도치 않은 동작 가능성

**해결 방안**:
1. `config/accounts/default.yml` 기본 계정 프로필 생성
2. 또는 `--account` 인자를 필수로 변경

---

## 3. 단위 테스트 결과

### 3.1 전체 테스트 통과

```
============================= 274 passed in 1.32s ==============================
```

- `test_account_context.py`: 17 passed
- `test_config.py`: 17 passed
- `test_daily_collector.py`: 21 passed
- `test_generate_content.py`: 24 passed
- `test_llm_client.py`: 29 passed
- `test_prompt_loader.py`: 35 passed
- `test_scoring.py`: 16 passed
- `test_validate_output.py`: 23 passed
- 기타: 모두 통과

### 3.2 통합 테스트 (제외됨)

- `test_integration.py`: 제외 (외부 의존성)
- `test_e2e_dryrun.py`: 제외 (실제 API 호출)

---

## 4. 권장 조치 사항

### 4.1 즉시 수정 필요 (High Priority)

| 버그 ID | 조치 | 담당 |
|---------|------|------|
| BUG-003 | 계정 ID 일치시키기 (파일명 또는 코드) | - |
| BUG-004 | YAML 파싱 문제 원인 파악 및 수정 | - |

### 4.2 개선 권장 (Medium Priority)

| 버그 ID | 조치 | 담당 |
|---------|------|------|
| BUG-001 | `--path` 옵션 추가 또는 문서 수정 | - |
| BUG-002 | 수집 성능 최적화 또는 타임아웃 조정 | - |

### 4.3 향후 고려 (Low Priority)

| 버그 ID | 조치 | 담당 |
|---------|------|------|
| BUG-005 | 기본 계정 프로필 생성 | - |

---

## 5. 테스트 실행 로그 (발췌)

### 5.1 Health Check
```json
[
  {"name": "Vault Access", "passed": true, "message": "Read/Write OK"},
  {"name": "OpenAI API Key", "passed": true, "message": "Configured"},
  {"name": "RSS Sources", "passed": true, "message": "All 3 sources accessible"},
  {"name": "Directories", "passed": true, "message": "All 5 directories exist"},
  {"name": "Disk Space", "passed": true, "message": "52.4 GB available"}
]
```

### 5.2 S6 Force Regenerate
```
Content Generation Results for 2026-02-16
Approved Items:      5
Longform Created:    5
Packs Created:       10
Image Prompts:       5
```

### 5.3 S7 Week-of
```
[INFO] Loaded WeeklySlot for week: 2026-02-16
  CTA: 댓글로 질문/상황 남기기
  Customer Outcome: 0→1→10 실행 로드맵(검증→출시→성장→스케일업)
```

---

## 6. 추가 발견 사항 (LSP 정적 분석)

### 6.1 tweepy 모듈 미설치

**파일**: `scripts/engagement_sync.py:247`
```
ERROR: Import "tweepy" could not be resolved
```

**원인**: `tweepy` 패키지가 설치되지 않음 (Twitter API 연동용)

**영향**: `engagement_sync.py`의 Twitter 메트릭 수집 기능 사용 불가

### 6.2 타입 힌트 불일치

**파일**: `tests/test_score_calibrator.py:311`
```
ERROR: Argument of type "dict[str, int]" cannot be assigned to parameter "correlations"
of type "dict[str, float]" in function "_suggest_weights"
```

**원인**: 테스트 코드에서 `dict[str, int]`를 전달하지만 함수는 `dict[str, float]`를 기대

**영향**: 타입 검사 실패 (런타임 동작에는 영향 없을 가능성 높음)

---

## 7. 첨부

- 테스트 시나리오 정의: `tests/benchmarks/scenarios/`
- 벤치마크 가이드: `specs/001-pipeline-reliability/benchmarks.md`
- 단위 테스트: `tests/`
