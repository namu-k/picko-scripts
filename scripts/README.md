# Scripts 사용 가이드

이 디렉터리에는 Picko 프로젝트를 관리하기 위한 다양한 스크립트들이 포함되어 있습니다.

## 📋 문서 관리 스크립트

### 문서 목록 관리

#### `docs_manager.py` - 문서 관리 메인 스크립트

문서 목록을 생성하고 관리하는 핵심 스크립트입니다.

**사용법:**
```bash
# 문서 목록 생성 및 README 업데이트
python scripts/docs_manager.py generate

# 문서 상태 점검
python scripts/docs_manager.py check

# 문서 목록 간단히 보기
python scripts/docs_manager.py list

# 상세 모드로 실행
python scripts/docs_manager.py generate --verbose

# 특정 디렉터리에서 실행
python scripts/docs_manager.py generate --docs-dir ./my-docs
```

#### `docs_list_generator.py` - 문서 목록 생성 자동화

`docs/README.md`에 포함될 문서 목록을 자동으로 생성합니다.

**주요 기능:**
- 모든 markdown 파일 스캔
- 파일 크기, 수정일, 상태 수집
- 섹션별 분류 및 정렬
- 자동 목차 생성

#### `docs_status_checker.py` - 문서 상태 점검

문서의 상태를 점검하고 보고서를 생성합니다.

**점검 항목:**
- 깨진 링크 확인
- 누락된 섹션 확인
- 문서 포맷 검사
- 용어 일관성 검사

**출력:**
- `docs/docs_status_report.md`에 상세 보고서 생성

### CI/CD 통합

문서 관리는 GitHub Actions를 통해 자동화됩니다.

#### `.github/workflows/docs_management.yml`

**트리거:**
- main/develop 브랜치 푸시 시
- PR 생성 시
- 수동 실행 시

**수행 작업:**
1. 문서 목록 자동 생성
2. 상태 점검 실행
3. 포맷 검사
4. GitHub Actions Summary에 결과 출력

### 설정 파일

#### `docs/.docs-config.yml`

문서 구조와 관리 규칙을 정의하는 설정 파일입니다.

**정의 내용:**
- 섹션별 경로 및 패턴
- 필수 파일 목록
- 상태 아이콘 매핑
- CI/CD 설정
- 통계 설정

## 🎯 사용 시나리오

### 1. 새 문서 추가 시

```bash
# 1. 새 문서 생성
echo "# 새 문서" > docs/new-section/new-doc.md

# 2. 문서 목록 업데이트
python scripts/docs_manager.py generate

# 3. 상태 점검
python scripts/docs_manager.py check
```

### 2. 문서 상태 확인

```bash
# 상세 점검 보고서 생성
python scripts/docs_status_checker.py

# 결과는 docs/docs_status_report.md에 저장됨
```

### 3. CI/CD에서 자동 관리

문서 관리는 PR 생성 시 자동으로 수행됩니다.

- PR 시 자동으로 깨진 링크 점검
- 포맷 검사
- 문서 완성도 검사

## 🔧 고급 사용법

### 커스텀 설정 사용

```python
from docs_list_generator import DocsListGenerator

# 커스텀 디렉터리 사용
generator = DocsListGenerator("custom-docs-dir")
generator.update_readme()
```

### 자동화된 문서 관리 파이프라인

```bash
# 로컬에서 모든 작업 실행
./scripts/manage-docs.sh all

# 특정 작업만 실행
./scripts/manage-docs.sh check-links
./scripts/manage-docs.sh format-docs
```

## 📊 통합 관리

### 문서 관리 워크플로우

```
1. 문서 작성
   ↓
2. 로컬 테스트
   python scripts/docs_manager.py check
   ↓
3. Git 커밋 및 푸시
   ↓
4. CI/CD 자동 검사
   ↓
5. 자동 목록 업데이트
   ↓
6. 문서 배포
```

### 모니터링 대시보드

- GitHub Actions Summary에서 실시간 결과 확인
- `docs/docs_status_report.md`에서 상세 보고서 확인
- Slack 알림 설정 가능 (`.docs-config.yml`)

## 🚀 향후 계획

- [ ] 자동 문서 생성 템플릿
- [ ] 더 스마트한 링크 검사
- [ ] 자동 번역 기능
- [ ] 문서 버전 관리 시스템
- [ ] 실시간 협업 기능

## 🤝 기여 가이드

문서 관리 스크립트 개선을 위한 기여는 언제나 환영합니다!

1. 이슈 생성: 개선사항 이슈 생성
2. PR 제출: 직접 수정 후 PR
3. 테스트: 변경 후 로컬에서 테스트
   ```bash
   python scripts/docs_manager.py check
   ```

## 📞 문의사항

스크립트 관련 문의사항은 GitHub Issues에 등록해 주세요.
