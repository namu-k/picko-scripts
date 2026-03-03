# PR #10 리뷰: feature/pipeline-reliability

> 브랜치: `feature/pipeline-reliability` → `main`  
> 변경 규모: 43 files, +4,478 / -119 lines

---

## 요약

파이프라인 안정화를 위한 대규모 PR입니다. **계정 fallback·캐시·스코어·프롬프트 로더 개선**, **daily_collector `max_items` 추가**, **engagement_sync Twitter API 연동 및 tweepy optional 처리**, **타입 힌트 정리**, **scripts/ 전반에 대한 단위 테스트 추가**가 잘 반영되어 있습니다. 머지 전에 몇 가지 정리하면 좋겠습니다.

---

## 잘된 점

### 1. 테스트 추가
- `test_daily_collector.py`, `test_generate_content.py`, `test_validate_output.py`, `test_engagement_sync.py`, `test_score_calibrator.py` 추가로 **scripts/ 구간 테스트 커버리지**가 크게 개선됨.
- Mock 기반 단위 테스트로 파이프라인 단계별 동작이 검증 가능해짐.
- `tests/benchmarks/` 시나리오 YAML로 e2e/feature 시나리오가 문서화됨.

### 2. picko 코어 개선
- **config.py**: 계정 프로필을 vault 루트 → 프로젝트 루트 순으로 fallback 로드하고, `loaded`가 dict가 아닐 때 경고 후 빈 dict로 폴백하는 방어 로직이 추가됨.
- **prompt_loader.py**: `prompt_type`에 전체 경로(`longform/default.md` 형태) 지원, `weekly_context` 인자로 롱폼/팩 프롬프트에 주간 슬롯(CTA, outcome 등) 주입.
- **scoring.py**: relevance 정규화를 매칭 소스 수에 따라 동적으로 조정하고, `interests`를 list/dict 둘 다 처리해 mock_vault·정식 config 호환성 확보.

### 3. 스크립트 개선
- **daily_collector**: `max_items`로 상위 N개만 처리 가능해 부하·테스트 제어에 유리함.
- **engagement_sync**: tweepy optional import, Twitter API v2 연동(`_fetch_twitter_metrics`, `_get_twitter_client`), 타입 힌트 정리.
- **generate_content / validate_output**: 타입·포매팅 정리.

### 4. 타입·도구
- `dict` → `dict[str, Any]` 등 타입 힌트 정리.
- `pyproject.toml`에 pyright 설정 추가.

---

## 수정 권장 사항

### 1. mock_vault에 포함된 생성물 제거 권장
- **파일**: `mock_vault/Content/Longform/longform_input_7ce483b7a9e4.md`
- `.gitignore`에 `mock_vault/Content/`가 있는데, 위 파일이 PR에 포함되어 있음. 테스트/실행으로 생성된 산출물이 실수로 올라온 것으로 보임.
- **권장**: 해당 파일을 커밋에서 제거하고, 필요하면 `tests/fixtures/` 등에 의도된 fixture만 두는 편이 좋음.

### 2. 테스트 실행 확인
- 리뷰 시점에 `pytest`가 설치된 환경에서 전체 테스트를 실행하지 못했음.
- **권장**: CI 또는 로컬에서  
  `pytest tests/test_daily_collector.py tests/test_generate_content.py tests/test_validate_output.py tests/test_engagement_sync.py tests/test_score_calibrator.py -v`  
  실행해 모두 통과하는지 확인 후 머지.

### 3. engagement_sync – Twitter API 키 문서화
- `TWITTER_BEARER_TOKEN` 등 환경 변수 사용이 코드에만 있음.
- **권장**: `CLAUDE.md` 또는 `.env.example`에  
  `# Optional: Twitter engagement sync`  
  `# TWITTER_BEARER_TOKEN=...`  
  등 한 줄이라도 추가해 두면 운영 시 혼란이 줄어듦.

### 4. score_calibrator 기대값 float 통일
- `test(score_calibrator): 기대값을 float으로 통일` 커밋이 반영되어 있어, 테스트와 구현이 맞춰진 상태로 보임. 별도 이슈 없음.

---

## 선택 사항

- **config/scoring thresholds**: `ScoringConfig.thresholds`가 여러 줄로 포맷된 것은 가독성에 좋음.
- **prompt_loader**: `is_full_path`로 `prompt_type`이 경로인지 판별하는 방식이 명확함.
- **scoring 동적 정규화**: `base = max(2.0, 3.5 - (matches * 0.5))` 식은 의도가 주석으로 잘 드러남. 나중에 가중치를 config로 빼도 됨.

---

## 체크리스트 (머지 전)

- [ ] `mock_vault/Content/Longform/longform_input_7ce483b7a9e4.md` 제거 또는 fixture로 이전
- [ ] 새로 추가된 5개 테스트 파일 전체 pytest 통과 확인
- [ ] (선택) Twitter 관련 env 예시를 `.env.example` 또는 문서에 추가

---

**결론**: 전반적으로 파이프라인 안정성과 테스트·타입 정리가 잘 이루어진 PR입니다. 위 항목만 정리하면 머지해도 좋을 것 같습니다.
