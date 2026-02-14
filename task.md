# 콘텐츠 생성 파이프라인 스크립트 구현 계획

## 현재 작업
- [x] Phase 1 스크립트 구현
- [x] Phase 2 스크립트 구현
- [x] Phase 3 스크립트 스캐폴드 구현
- [x] 테스트 프레임워크 추가 (pytest)
- [x] GitHub Actions CI 설정
- [x] Windows Task Scheduler 설정 스크립트
- [x] 개발 도구 설정 (pre-commit, mypy, black, isort)
- [x] CI 하드닝 (시크릿 검사, 커버리지, 보안 스캔)
- [x] CHANGELOG.md 작성 (v0.2.0)
- [x] 버전 bump (pyproject.toml → 0.2.0)
- [x] 문서화 (REVIEW_CHECKLIST.md, MONITORING.md)

## 작업 단계
- [x] 운영단계별 스크립트 구현 계획 문서 작성
  - [x] implementation_plan.md 생성
  - [x] 사용자 리뷰 승인 완료
- [x] Phase 1 스크립트 구현
  - [x] 프로젝트 구조 생성
  - [x] picko/config.py
  - [x] picko/vault_io.py
  - [x] picko/llm_client.py
  - [x] picko/embedding.py
  - [x] picko/scoring.py
  - [x] picko/templates.py
  - [x] scripts/daily_collector.py
  - [x] scripts/generate_content.py
  - [x] scripts/validate_output.py
  - [x] scripts/health_check.py
  - [x] config/config.yml
- [x] Phase 2 스크립트 구현
  - [x] scripts/archive_manager.py
  - [x] scripts/retry_failed.py
  - [x] scripts/publish_log.py
- [x] Phase 3 스크립트 스캐폴드 구현
  - [x] scripts/engagement_sync.py (성과 메트릭 동기화)
  - [x] scripts/score_calibrator.py (점수 보정 분석)
  - [x] scripts/duplicate_checker.py (중복 콘텐츠 탐지)
- [x] 테스트 및 CI/CD
  - [x] tests/ 디렉토리 구조 (pytest)
  - [x] tests/test_config.py (설정 로더 테스트)
  - [x] tests/test_scoring.py (점수 계산 테스트)
  - [x] tests/test_templates.py (템플릿 렌더링 테스트)
  - [x] tests/test_integration.py (통합 테스트)
  - [x] .github/workflows/test.yml (CI 워크플로우)
  - [x] .flake8 (린트 설정)
- [x] 운영 자동화
  - [x] scripts/setup_scheduler.ps1 (Windows Task Scheduler 설정)
  - [x] scripts/run_daily_collector.ps1 (스케줄러 실행 스크립트)

## Phase 3 구현 상세

### engagement_sync.py
- 플랫폼 API 연결 플레이스홀더 구조
- 성과 메트릭 자동 동기화 기능
- 발행 로그 업데이트

### score_calibrator.py
- 실제 성과 vs 예측 점수 상관관계 분석
- 가중치 조정 제안
- 개선 효과 추정

### duplicate_checker.py
- 임베딩 기반 유사도 검사
- 단일/디렉토리/페어 비교 모드
- 임계값 설정 가능

## 하드닝 플랜 완료 (Commit 6843cd8)

- [x] CI/CD 하드닝: 시크릿 검사, 의존성 캐싱, mypy 타입 체크, 보안 스캔
- [x] 개발 도구: pre-commit hooks, black, isort, flake8, mypy
- [x] E2E 테스트: generate_content dry-run 통합 테스트
- [x] 문서화: CHANGELOG.md (v0.2.0), REVIEW_CHECKLIST.md, MONITORING.md
- [x] 일일 헬스 체크: .github/workflows/health_check.yml (8 AM UTC, 자동 이슈 생성)
- [x] 의존성 관리: requirements.txt 핀, pyproject.toml dev deps
- [x] 후속 작업 추적: FOLLOWUPS.md (12개 이슈)

### 참조
- Commit 753183c: Phase 3 완료, 테스트, CI/CD 추가
- Commit 6843cd8: 하드닝 플랜 실행, 개발 도구 및 문서화 완료
