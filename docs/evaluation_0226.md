현황 판단

"스크립트 모음"과 "프로덕트"를 가르는 기준은 크게 세 가지입니다. 구조의 견고함, 확장 가능성, 운영 가능성. Picko는 세 가지 모두 충족합니다.

① 아키텍처가 모듈화되어 있습니다
단순 스크립트라면 기능이 한 파일에 뭉쳐있거나, 파일 간 의존성이 뒤엉킵니다. Picko는 역할별로 명확히 분리되어 있습니다.
picko/             ← 핵심 비즈니스 로직 (import 가능한 패키지)
  config.py        ← 설정 로딩 (dataclass 타입 보장)
  llm_client.py    ← LLM 추상화 레이어
  scoring.py       ← 채점 알고리즘
  vault_io.py      ← 스토리지 레이어
  prompt_composer.py ← 프롬프트 조합 레이어
  ...
scripts/           ← 실행 진입점 (CLI)
config/            ← 설정값 (코드와 완전 분리)
tests/             ← 검증 레이어
어떤 모듈 하나를 교체해도 다른 모듈에 영향이 최소화되는 구조입니다.

② 설정이 코드와 완전히 분리되어 있습니다
스크립트 수준이라면 LLM 모델명, API 키, 점수 가중치 등이 코드 안에 박혀있습니다. Picko는 모든 동작을 YAML로 제어합니다. 코드를 한 줄도 건드리지 않고 전혀 다른 계정, 다른 AI 모델, 다른 채점 기준으로 운영 가능합니다.

③ LLM 추상화 레이어가 있습니다
OpenAI, Anthropic, OpenRouter, Relay, Ollama — 5개 프로바이더를 단일 인터페이스로 교체 가능하고, 각각 fallback_provider와 fallback_model이 설정되어 있습니다. 특정 API가 다운되거나 키가 만료돼도 다른 프로바이더로 자동 전환됩니다. 이 정도 설계는 프로덕션 운영을 염두에 둔 구조입니다.

④ 테스트 인프라가 체계적으로 갖춰져 있습니다
테스트 파일 30개, 총 9,232줄의 테스트 코드가 있습니다. 단순 기능 확인용 테스트가 아닙니다.

unit / integration / slow 마커로 테스트 종류 분리
conftest.py의 공유 픽스처 (temp_vault_dir, mock_config 등)
e2e dry-run 테스트 (test_e2e_dryrun.py)
GitHub Actions CI에 linting(flake8), 타입 체크(mypy), 보안 감사(safety + pip-audit)까지 포함


⑤ 운영에 필요한 기반 시스템이 있습니다
기능구현 내용로깅loguru, 일별 로테이션, 보존 기간 설정캐싱임베딩 캐시 (cache/embeddings/)재시도retry_failed.py — 실패 단계별 재처리dry-run 모드모든 주요 스크립트에 --dry-run 지원자동화Windows Task Scheduler 설정 스크립트 포함타입 안전성dataclass 기반 Config, mypy 타입 체크코드 품질black, isort, flake8, pre-commit 설정 완비

⑥ 멀티 계정 구조를 처음부터 설계했습니다
계정별 프로필(config/accounts/)로 완전히 다른 타겟 독자, 채널 설정, 톤, 금지 주제를 분리 관리합니다. 단일 사용자용 스크립트라면 이런 추상화가 필요 없습니다. 여러 고객을 운영하는 에이전시나 SaaS 확장까지 고려한 설계입니다.


부족한 부분 (솔직하게)
크게 두 가지로 나뉩니다. 구현이 아직 안 된 것과 구조적 한계.

구현이 미완성인 것들
① LinkedIn 성과 연동이 없습니다
engagement_sync.py에 Twitter API 연동은 구현되어 있지만, LinkedIn·Newsletter·Instagram·YouTube·Blog는 코드에 TODO 주석만 남아있고 실제로는 빈 값을 반환합니다. Score Calibrator가 성과 데이터를 분석해서 가중치를 자동 조정하는 기능도, 분석까지는 되지만 config.yml에 실제로 쓰는 부분이 미구현 상태입니다("Auto-config update not implemented" 경고 출력).
② 신선도(Freshness) 점수가 없습니다
scoring.py의 품질 점수 계산에 날짜 기반 신선도 로직이 주석 처리된 채로 남아있습니다. 3일 된 기사와 3년 된 기사가 같은 점수를 받습니다.
③ 영상 렌더링이 없습니다
스타일 추출에서 video_prompt.md를 생성하고, 계정 프로필에도 영상 관련 설정이 있지만, 실제로 영상을 만드는 코드는 없습니다. 이미지(PNG) 렌더링만 완성되어 있습니다.
④ 자동 퍼블리시가 없습니다
콘텐츠를 생성하고 이미지를 만드는 것까지는 자동화되지만, 실제로 플랫폼에 올리는 것은 사용자가 직접 해야 합니다. "자동화 시스템"이라는 포지셔닝에서 마지막 한 발이 빠져있습니다.

구조적 한계
① UI가 없습니다
전체 인터페이스가 CLI(명령줄)입니다. 개발자라면 문제없지만, 일반 개인사업자가 직접 터미널을 열고 명령어를 입력하는 것은 진입 장벽이 높습니다. Obsidian이 사실상 유일한 GUI인데, 이것도 별도 설치와 학습이 필요합니다.
② Windows 중심입니다
자동화 스케줄러 설정이 PowerShell + Windows Task Scheduler로만 구현되어 있습니다. Mac이나 Linux 사용자를 위한 cron 설정 스크립트가 없습니다.
③ 로컬 실행 환경이 필수입니다
Python 3.13, Ollama 설치, 가상환경 설정, API 키 설정 — 첫 세팅에 기술적 허들이 있습니다. 일반 사업자가 혼자 세팅하기는 어렵습니다.

요약
완성도 약 85~90%의 프로덕트급 백엔드 시스템.
핵심 파이프라인(수집→큐레이션→생성)은 완성.
분석·성과 연동 레이어가 미완성.
UI 레이어가 전무.
판매 시 현재 타겟은 "CLI에 익숙한 1인 크리에이터 / 마케터"가 현실적입니다. 일반 개인사업자 대상으로 판매하려면 온보딩 지원이나 세팅 서비스를 함께 제공하거나, 장기적으로 웹 UI가 필요합니다.