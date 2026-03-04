# 버그 픽스 지시문

> **참조**: [bug_report.md](./bug_report.md)  
> **목적**: 버그 리포트에 기재된 이슈를 재현 가능하고 검증 가능한 순서로 수정하기 위한 정밀 지시문.

---

## 적용 원칙

- **우선순위**: High(BUG-003, BUG-004) → Medium(BUG-001, BUG-002) → Low(BUG-005) → 부가(LSP 이슈).
- **의존성**: BUG-003/004 수정 후 F1 시나리오 재검증. BUG-001 수정 후 모든 시나리오의 `validate` 명령 재실행 가능.
- **검증**: 각 수정 항목마다 "검증 방법"을 수행하고, 필요 시 단위 테스트 또는 벤치마크 시나리오 한 개 이상 실행으로 회귀 확인.

---

## Phase 1: High Priority

### BUG-003: 계정 프로필 account_id 불일치

**목표**: `get_style_for_account(account_id)` 호출 시 실제 계정 프로필 파일과 ID가 일치하도록 한다.

**선택한 해결 방안**: **옵션 B** — 시나리오·문서에서 사용하는 계정 ID를 실제 파일명(stem)과 동일하게 `socialbuilders`로 통일. (파일명 변경 없음.)

**수정 작업**:

1. **벤치마크 시나리오 YAML**
   - 파일: `tests/benchmarks/scenarios/features/f1-reference-account.yml`
   - 작업: 문서 및 `command` 내 모든 `builders_social_club`를 `socialbuilders`로 치환.
   - 대상 예시:
     - `input` 설명의 "예: builders_social_club" → "예: socialbuilders"
     - `steps` 내 Python 코드의 `'builders_social_club'` → `'socialbuilders'` (두 곳: get_identity, get_style_for_account 인자)

2. **기타 문서**
   - `specs/001-pipeline-reliability/` 및 `tests/benchmarks/README.md` 등에서 "builders_social_club"가 계정 ID 예시로 쓰인 곳이 있으면 `socialbuilders`로 통일.

**검증 방법**:

```bash
python -c "
from picko.account_context import get_identity, get_style_for_account
identity = get_identity('socialbuilders')
style = get_style_for_account('socialbuilders')
assert identity is not None, 'identity should load'
assert style is not None, 'style should load'
print('OK:', identity.one_liner[:50], '...')
print('Style keys:', list(style.keys())[:5])
"
```

- F1 시나리오의 "계정 프로필 로드 확인" 단계 명령을 위와 같이 `socialbuilders`로 바꾼 뒤 실행해 경고/None이 없어야 함.

---

### BUG-004: 계정 프로필 YAML 파싱·경로 문제

**목표**: `config.get_account(account_id)`가 올바른 경로에서 YAML을 읽고, `account_id`·`style_name` 등 최상위 키를 정상 반환하도록 한다.

**원인 후보** (버그 리포트 및 코드 기준):

- `get_account()`가 `Path(config.vault.root) / config.accounts_dir / f"{account_id}.yml"`만 참조함.
- 프로젝트 기본 구조는 **프로젝트 루트** `config/accounts/socialbuilders.yml`이고, `vault.root`는 `mock_vault` 등 별도 디렉터리일 수 있음.
- 따라서 vault 루트 아래에 `config/accounts/`가 없거나 파일이 없으면 빈 dict가 반환되고, `.get('account_id')`는 None이 됨.

**수정 작업**:

1. **계정 프로필 로드 경로: 프로젝트 루트 우선 (fallback)**
   - 파일: `picko/config.py`
   - 위치: `get_account(self, account_id: str) -> dict` 메서드.
   - 요구 사항:
     - 1) 기존과 동일하게 `Path(self.vault.root) / self.accounts_dir / f"{account_id}.yml"` 경로를 먼저 시도.
     - 2) 해당 경로에 파일이 **없으면** 프로젝트 루트 기준 `config/accounts/{account_id}.yml`을 시도. (프로젝트 루트는 `Path(__file__).resolve().parent.parent` 또는 기존 프로젝트 루트 정의가 있으면 그 값 사용.)
     - 3) 두 경로 모두 없으면 기존과 동일하게 경고 로그 후 빈 dict 반환.
   - 구현 시 유의: `self._accounts[account_id]` 캐시는 한 번 로드된 계정을 그대로 두면 됨. 경로 1 실패 시 경로 2로 열어서 로드한 결과를 캐시에 넣음.

2. **YAML 파싱 결과 보장**
   - 같은 메서드에서 `yaml.safe_load(f)` 결과가 `None`이면 `{}`로 대체하는 것은 이미 있음. 유지.
   - 로드된 값이 dict가 아니면(예: 리스트) `{}`로 폴백하고 로그 경고를 남기도록 처리 권장.

**검증 방법**:

```bash
python -c "
from picko.config import get_config
c = get_config()
acc = c.get_account('socialbuilders')
assert isinstance(acc, dict), 'account should be dict'
assert acc.get('account_id') is not None, 'account_id key should exist'
assert acc.get('style_name') is not None, 'style_name key should exist'
print('account_id:', acc.get('account_id'))
print('style_name:', acc.get('style_name'))
"
```

- 위 assertion이 모두 통과해야 함.  
- 필요 시 `mock_vault/config/accounts/socialbuilders.yml`이 없는 환경에서도, 프로젝트 루트 `config/accounts/socialbuilders.yml`만으로 위 검증이 통과하는지 확인.

---

## Phase 2: Medium Priority

### BUG-001: validate_output.py CLI 인자 문서 불일치

**목표**: 벤치마크 시나리오에서 사용하는 `--path` 옵션을 CLI에서 지원하여 `python -m scripts.validate_output --path Content/Longform/ --recursive` 형태로 실행 가능하게 한다.

**선택한 해결 방안**: **옵션 A** — `validate_output.py`에 `--path`(단축 `-p`) 옵션을 추가하고, `--path`가 있으면 그 값을 사용, 없으면 기존 위치 인자(또는 기본값 `Content/`)를 사용.

**수정 작업**:

1. **scripts/validate_output.py**
   - `main()` 내부, 기존:
     - `parser.add_argument("path", nargs="?", default="Content/", help="...")`
   - 변경:
     - 위치 인자 이름을 `path_positional` 또는 그대로 `path`로 두되, `nargs="?"`, `default=None`으로 두고,
     - `parser.add_argument("--path", "-p", dest="path_opt", default=None, help="검증할 경로")` 추가.
     - 파싱 후: `path = args.path_opt if args.path_opt is not None else (args.path if hasattr(args, 'path') else "Content/")`.  
       (또는 단순히 위치 인자를 `path_arg`로 바꾸고 `path = getattr(args, 'path_opt', None) or getattr(args, 'path_arg', None) or "Content/"`.)
   - 구현 시 주의: `argparse`에서 positional과 optional이 같은 `dest`를 쓰면 충돌할 수 있으므로,  
     - 예: positional은 `dest='path_arg'`, optional `--path`는 `dest='path'`로 두고,  
     - `path = args.path or args.path_arg or "Content/"` 로 결정.

2. **벤치마크 시나리오 YAML**
   - 수정하지 않아도 됨. 이미 `--path ... --recursive` 형태이므로, 위 수정만으로 동작해야 함.

**검증 방법**:

```bash
python -m scripts.validate_output --path Content/Longform/ --recursive
python -m scripts.validate_output --path Content/Packs/ -r -v
python -m scripts.validate_output Content/Longform/
```

- 세 명령 모두 `unrecognized arguments` 없이 실행되어야 함.  
- 기존 위치 인자만 쓰는 호출(`validate_output Content/`)도 그대로 동작해야 함.

---

### BUG-002: S1 고밀도 기술 기사 시나리오 타임아웃

**목표**: 3개 소스 동시 수집 시 120초 내에 완료되거나, 타임아웃을 넘기지 않고 실행할 수 있는 옵션을 제공한다.

**선택한 해결 방안**: 단기적으로 **타임아웃 완화**와 **수집 항목 수 제한 옵션**을 조합. 중장기적으로 소스별 순차 처리·NLP 병렬화는 별도 이슈로 다룸.

**수정 작업**:

1. **수집 항목 수 제한 옵션 (권장)**
   - 파일: `scripts/daily_collector.py`
   - 작업: `argparse`에 `--max-items`(또는 `--limit`) 옵션 추가.  
     - 의미: 전체 수집 대상 중 최대 N개만 처리하고 나머지는 스킵. (RSS fetch는 하되, 이후 NLP/export 단계에서 상위 N개만 사용.)
   - 기본값: `None`(제한 없음). 예: `--max-items 15`로 S1 벤치마크 시 15건만 처리해 120초 내 완료 가능하도록.

2. **벤치마크 시나리오**
   - 파일: `tests/benchmarks/scenarios/e2e/s1-high-density-tech.yml`
   - 작업: `commands.dry_run` 및 `commands.collect`에 `--max-items 20`(또는 동일한 옵션명) 추가.  
     - 예: `python -m scripts.daily_collector --date 2026-02-16 --sources techcrunch ai_news hacker_news --max-items 20 --dry-run`

3. **타임아웃 (실행 환경)**
   - CI/스크립트에서 `daily_collector`를 호출할 때 타임아웃을 120초에서 300초(5분) 등으로 늘리는 것은 **지시문 범위 외**(환경 설정). 필요 시 해당 실행 스크립트·CI 설정에서만 조정.

**검증 방법**:

- `python -m scripts.daily_collector --date 2026-02-16 --sources techcrunch ai_news hacker_news --max-items 20 --dry-run` 을 실행해 120초 이내에 정상 종료되는지 확인.
- `--max-items` 없이 실행하는 기존 시나리오(S5 등)는 동작이 바뀌지 않아야 함.

---

## Phase 3: Low Priority

### BUG-005: generate_content 기본 계정 프로필 없음

**목표**: `account_id`가 없을 때 `default`를 쓰지 않고, 실제 존재하는 계정을 기본값으로 사용하여 "Account profile not found: default" 경고를 제거한다.

**수정 작업**:

1. **scripts/generate_content.py**
   - 위치: 롱폼 생성 경로에서 `account_id = item.get("account_id") or "default"` 로 설정하는 부분 (약 469행 근처).
   - 변경: `"default"` → `"socialbuilders"` 로 변경. (이미 팩/이미지 생성 경로에서는 `socialbuilders`를 쓰고 있으므로 통일.)

**검증 방법**:

```bash
python -m scripts.generate_content --date 2026-02-16 --type longform
```

- 로그에 `Account profile not found: default` 가 없어야 함.  
- (이미 생성된 항목이 있으면 스킵될 수 있으므로, 필요 시 `--force` 또는 승인 1건만 두고 실행.)

---

## Phase 4: 부가 수정 (LSP / 타입·의존성)

### LSP: tweepy 미설치

- **파일**: `scripts/engagement_sync.py` (예: 247행 인근)
- **조치**:  
  - **옵션 A**: `requirements.txt`에 `tweepy`를 추가하고, Twitter 연동을 사용할 경우에만 설치하도록 문서화.  
  - **옵션 B**: 해당 import를 try/except로 감싸고, 실패 시 `tweepy = None` 등으로 두어 선택적 사용만 가능하게 함.  
- 지시문에서는 **옵션 B**를 권장. (의존성 최소화.)  
  - 상단: `try:\n    import tweepy\nexcept ImportError:\n    tweepy = None`  
  - tweepy를 사용하는 블록에서 `if tweepy is None:` 일 때 경고 로그 후 스킵 또는 적절한 fallback.

**검증**: `python -c "from scripts.engagement_sync import ..."` 또는 해당 스크립트 `--help` 실행 시 import 에러가 나지 않아야 함.

---

### LSP: test_score_calibrator.py 타입 불일치

- **파일**: `tests/test_score_calibrator.py`
- **위치**: `_suggest_weights(correlations)`에 넘기는 인자. `correlations`가 `dict[str, float]`를 기대하는데 테스트에서 `dict[str, int]`를 넘김.
- **조치**: 테스트 내 `correlations` 리터럴의 값을 정수에서 float으로 변경.
  - 예: `{"novelty": 0, "relevance": 0, "quality": 0}` → `{"novelty": 0.0, "relevance": 0.0, "quality": 0.0}`
  - 동일한 패턴이 있는 다른 테스트(positive/negative correlation)도 `0.5`, `-0.5` 등은 이미 float이면 유지, 정수면 `0.0` 등으로 float 리터럴로 통일.

**검증**: `pytest tests/test_score_calibrator.py -v` 및 `mypy tests/test_score_calibrator.py` (해당 인자 타입 검사 통과).

---

## 수정 후 통합 검증

1. **단위 테스트**
   - `pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_e2e_dryrun.py` (또는 프로젝트 기본 제외 규칙)  
   - 274 passed 수준 유지. 새로 추가한 테스트가 있다면 함께 통과.

2. **벤치마크 시나리오 샘플**
   - BUG-001: `python -m scripts.validate_output --path Content/Longform/ --recursive` (F5 시나리오 일부).
   - BUG-003/004: F1 시나리오의 계정 로드 단계 (위 Phase 1 검증 명령).
   - BUG-005: `generate_content --date ... --type longform` 1회 실행 후 로그에 default 경고 없음 확인.
   - BUG-002: S1 시나리오 `--max-items 20` 포함 명령으로 타임아웃 없이 완료 확인.

3. **문서**
   - `bug_report.md`에 "수정 완료" 섹션을 추가하거나, 이 지시문(`bug_fix_instructions.md`)을 참조로 남겨, 적용한 Phase와 검증 결과를 한 줄씩 기록해 두면 이후 추적에 유리함.

---

## 체크리스트 (픽스 적용 시)

| Phase | 버그 ID | 수정 파일 | 검증 통과 |
|-------|---------|-----------|-----------|
| 1 | BUG-003 | f1-reference-account.yml 등 | get_style_for_account('socialbuilders') ≠ None |
| 1 | BUG-004 | picko/config.py | get_account('socialbuilders')에 account_id, style_name 존재 |
| 2 | BUG-001 | scripts/validate_output.py | --path 사용 시 에러 없음 |
| 2 | BUG-002 | daily_collector.py, s1-high-density-tech.yml | --max-items 20 시 120초 내 완료 |
| 3 | BUG-005 | scripts/generate_content.py | default 경고 없음 |
| 4 | LSP tweepy | scripts/engagement_sync.py | import 에러 없음 |
| 4 | LSP type | tests/test_score_calibrator.py | float 리터럴, mypy/pytest 통과 |
