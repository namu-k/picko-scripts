# Picko - Content Pipeline

[![Release](https://img.shields.io/github/v/release/namu-k/picko-scripts?label=version)](https://github.com/namu-k/picko-scripts/releases)
[![Test](https://github.com/namu-k/picko-scripts/actions/workflows/test.yml/badge.svg)](https://github.com/namu-k/picko-scripts/actions/workflows/test.yml)
[![Security](https://img.shields.io/badge/Security-Policy-blue)](SECURITY.md)

> RSS 피드와 웹 소스에서 콘텐츠를 자동 수집하고, AI를 활용해 블로그 포스트와 소셜 미디어 콘텐츠를 생성하는 파이프라인 시스템

## 📋 개요

Picko는 다음 작업을 자동화합니다:

- 🤖 **AI 기반 콘텐츠 분석**: 요약, 핵심 포인트 추출, 태깅
- 📊 **스마트 점수 매기기**: 참신도, 관련도, 품질 기반 자동 필터링
- ✍️ **다양한 형식 생성**: 블로그, 트위터, 링크드인, 뉴스레터
- 📝 **Obsidian 통합**: 마크다운 기반 콘텐츠 관리

## 🚀 빠른 시작

### 1. 사전 준비

- Python 3.13 이상
- OpenAI API 키 ([발급 방법](https://platform.openai.com/api-keys))

### 2. 설치

```bash
# 리포지토리 클론
git clone https://github.com/namu-k/picko-scripts.git
cd picko-scripts

# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt

# API 키 설정
set OPENAI_API_KEY=sk-your-key-here  # Windows
export OPENAI_API_KEY=sk-your-key-here  # macOS/Linux
```

> 💡 **Need help with API key setup?** See [**DEPLOYMENT.md**](DEPLOYMENT.md) for detailed instructions including GitHub Actions Secrets setup.

### 3. 설정

`config/config.yml`에서 본인의 Obsidian Vault 경로와 OpenAI 설정을 수정하세요.

### 4. 첫 실행

```bash
# 시스템 건강 확인
python -m scripts.health_check

# 콘텐츠 수집 (테스트용)
python -m scripts.daily_collector --dry-run

# 실제 콘텐츠 수집
python -m scripts.daily_collector

# 콘텐츠 생성 (Digest에서 승인 후)
python -m scripts.generate_content
```

## 📖 상세 가이드

처음 사용하시나요? [**USER_GUIDE.md**](USER_GUIDE.md)에서 다음을 확인하세요:

- 단계별 설치 및 설정 방법
- 콘텐츠 파이프라인 상세 설명
- 일일/주간 작업 흐름
- 문제 해결 가이드
- 팁과 모범 사례

## 🛠️ 주요 명령어

### 콘텐츠 수집

```bash
# 오늘 날짜로 수집
python -m scripts.daily_collector

# 특정 날짜로 수집
python -m scripts.daily_collector --date 2026-02-09

# 특정 소스만 수집
python -m scripts.daily_collector --sources techcrunch ai_news

# Dry-run (저장 없이 테스트)
python -m scripts.daily_collector --dry-run
```

### 콘텐츠 생성

```bash
# 오늘 승인된 콘텐츠 생성
python -m scripts.generate_content

# 특정 타입만 생성
python -m scripts.generate_content --type longform packs

# 강제 재생성
python -m scripts.generate_content --force
```

### 주제 탐색

```bash
# 특정 입력에 대한 주제 탐색
python -m scripts.explore_topic --input-id 7ce483b7a9e4

# 특정 계정 프로필로 탐색
python -m scripts.explore_topic --input-id 7ce483b7a9e4 --account socialbuilders
```

### 스타일 추출

```bash
# URL에서 스타일 분석 및 프롬프트 추출
python -m scripts.style_extractor --urls URL1 URL2 --name "style_name"

# 파일에서 URL 목록 읽기
python -m scripts.style_extractor --file urls.txt --name "style_name"

# 결과 미리보기 (저장 없이)
python -m scripts.style_extractor --urls URL1 --name "style_name" --dry-run
```

### 🖼️ 이미지 렌더링

```bash
# 입력 템플릿에서 이미지 렌더링
python -m scripts.render_media render --input Inbox/Multimedia/mm_xxx.md

# 파이프라인 상태 확인
python -m scripts.render_media status

# 대기 중인 제안 검토
python -m scripts.render_media review

# 결과물 검토
python -m scripts.render_media review --finals
```

> 💡 이미지 렌더링은 HTML 템플릿(quote, card, list)을 Playwright로 PNG 변환합니다.

### 검증 및 관리

```bash
# 생성된 콘텐츠 검증
python -m scripts.validate_output --path Content/ --recursive --verbose

# 시스템 상태 확인
python -m scripts.health_check

# 오래된 콘텐츠 아카이브
python -m scripts.archive_manager --days 30

# 실패한 항목 재시도
python -m scripts.retry_failed --date 2026-02-09
```

### Phase 3: 성과 분석 (선택)

```bash
# 플랫폼 성과 메트릭 동기화
python -m scripts.engagement_sync --days 7

# 점수 가중치 분석 및 조정 제안
python -m scripts.score_calibrator --days 30

# 중복 콘텐츠 탐지
python -m scripts.duplicate_checker --directory "Inbox/Inputs"
```

## 📁 프로젝트 구조

```
picko-scripts/
├── config/              # 설정 파일
│   ├── config.yml      # 메인 설정
│   ├── sources.yml     # RSS 소스
│   ├── prompts/        # LLM 프롬프트 템플릿
│   ├── accounts/       # 계정 프로필
│   └── reference_styles/  # 레퍼런스 스타일 분석
├── picko/              # 핵심 모듈
├── scripts/            # 실행 스크립트
├── logs/              # 실행 로그
├── cache/             # 임베딩 캐시
└── mock_vault/        # 테스트용 Obsidian Vault
```

## ⚙️ 설정

### 메인 설정 (`config/config.yml`)

- Vault 경로
- LLM 모델 및 API 설정
- 점수 계산 가중치
- 로깅 설정

### 소스 설정 (`config/sources.yml`)

- RSS 피드 URL
- 카테고리별 설정
- 활성화/비활성화

### 계정 프로필 (`config/accounts/*.yml`)

- 관심 주제
- 키워드 가중치
- 채널별 톤앤매너

## 💰 비용 안내

OpenAI API 사용에 따른 비용이 발생합니다:

- **GPT-4o**: 약 $0.005/1K토큰
- **text-embedding-3-small**: 약 $0.00002/1K토큰
- **예상 일일 비용**: 약 $0.15 (하루 10개 콘텐츠 기준)

## 🤝 기여

이 프로젝트에 기여하고 싶으시면 Pull Request를 제출해주세요.

## 📄 라이선스

Apache License 2.0

## 📞 지원

- 문제 신고: [GitHub Issues](https://github.com/namu-k/picko-scripts/issues)
- 📛 보안 취약점 신고: [SECURITY.md](SECURITY.md)
- 사용자 가이드: [USER_GUIDE.md](USER_GUIDE.md)
- 개발자 가이드: [CLAUDE.md](CLAUDE.md)
- 배포 가이드: [DEPLOYMENT.md](DEPLOYMENT.md)
- 변경 로그: [CHANGELOG.md](CHANGELOG.md)
- 코드 리뷰 체크리스트: [REVIEW_CHECKLIST.md](REVIEW_CHECKLIST.md)
- 모니터링: [MONITORING.md](MONITORING.md)
- 후속 작업: [FOLLOWUPS.md](FOLLOWUPS.md)
