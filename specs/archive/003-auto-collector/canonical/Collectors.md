# 로컬 기반 글로벌 레퍼런스 수집 및 Claude 처리 가이드

이 문서는 해외 뉴스레터/블로그/커뮤니티 레퍼런스를 **로컬 폴더에 파일로 누적**하고,
**Claude Code(CLI)** 로 요약/추출/리포트 작성까지 연결하는 운영 가이드입니다.

관련 프레임워크 문서(로컬 Vault):
- `mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0. 프레임워크/Collector_automation.md`

---

## 0) 폴더 구조(정본) — 반드시 하나로 통일

로컬-first 운영(권장):
- 작업 루트: `C:\MyAIWorker\`
- 입력(원천 파일): `C:\MyAIWorker\inputs\`
  - `rss\` / `perplexity\`
- 출력(요약/리포트): `C:\MyAIWorker\outputs\`

Picko/Vault로 운영(선택):
- Vault root: (사용자 환경의 Vault 경로)
- Inputs 노트: `Inbox/Inputs/`
- Digest: `Inbox/Inputs/_digests/`

중요:
- 자동화의 1단계는 “AI 처리”가 아니라 “파일로 떨어뜨리기”다.

---

## 1) 수집 (Inputs를 파일로 떨어뜨리기)

### 1.1 RSS 수집 (Python)

가벼운 수집(로컬 폴더에 누적):
- 스크립트: `scripts/simple_rss_collector.py`
- 예시:
  - `python scripts/simple_rss_collector.py --output "C:\MyAIWorker\inputs\rss" --hours 24 --max-items 20`
- 기본값: 날짜별 폴더 생성(YYYY-MM-DD)
- 한 폴더에 누적하려면: `--no-by-date`

Picko 파이프라인을 쓰는 방법(옵션, Vault/디듀프/다이제스트 포함):
- `python -m scripts.daily_collector --dry-run`
- `python -m scripts.daily_collector --sources techcrunch ai_news --max-items 10`

### 1.2 RSS가 없는 사이트(선택)

- RSS.app/FetchRSS로 피드를 “생성”해서 RSS 수집기로 받는다.
- 운영의 중심은 “로컬 파일 축적 + Claude 처리”이며, 피드 생성 도구는 보조 수단이다.

### 1.3 Perplexity Tasks 결과 수집 (이메일 -> 파일)

Perplexity Tasks 결과는 이메일로 오므로, 이메일을 파일로 저장해야 Claude가 처리하기 쉽다.

- Make(추천) 또는 Zapier: 이메일 수신 -> Google Drive/Dropbox에 `.md` 저장 -> 로컬 동기화
- 구체 설정: `mock_vault/config/Folders_to_operate_social-media_copied_from_Vault/0. 프레임워크/Perplexity_email_setup.md`

운영 규칙(최소):
- 파일명에 시간 포함(중복 방지): `YYYY-MM-DD_HH-mm-ss_perplexity.md`
- 본문은 가능하면 `text/plain` 위주로 저장(HTML은 파싱 이슈)
- 저장 인코딩은 UTF-8

---

## 2) 처리 (Claude 중심)

### 2.1 Claude Code(CLI)로 폴더 처리

핵심 개념:
- Claude는 "디자이너"나 "수집기"가 아니라, **폴더에 모인 파일을 읽고 결과를 만들어내는 처리자**로 둔다.

권장 실행 규칙:
- 실행 위치: `C:\MyAIWorker\`
- 입력: `C:\MyAIWorker\inputs\`
- 출력: `C:\MyAIWorker\outputs\daily_report_YYYY-MM-DD.md`

예시 프롬프트:
> "inputs/rss 와 inputs/perplexity의 새 파일을 읽고 중복 제거 후 오늘 핵심 3개만 뽑아 outputs/daily_report_YYYY-MM-DD.md 로 작성해줘."

### 2.2 Picko로 생성 단계까지 연결(선택)

- 승인된 다이제스트 기반으로 롱폼/팩/이미지 프롬프트 생성:
  - `python -m scripts.generate_content`
  - `python -m scripts.generate_content --type longform packs`

---

## 3) 자동화 (스케줄링)

- RSS 수집: Windows 작업 스케줄러로 주기 실행
- Perplexity: 이메일->파일 변환(Make/Zapier) + 클라우드 앱 로컬 동기화
- Claude 처리: 수동 실행부터 시작(원하면 이후 CLI 스케줄링으로 확장)

동기화(Drive/Dropbox) 주의:
- 기존 파일 append보다 “새 파일 생성”이 안전
- 대량 생성은 배치 처리(동기화 충돌 감소)

---

## 4) 옵션: 저장/디자인 자동화

- Notion/DB 저장은 “추가 모듈”로 분리(핵심 흐름에서 제외)
- 이미지/썸네일 렌더링도 별도 파이프라인로 분리 권장

---

## Acceptance Criteria (자동 검증 기준)

1) RSS 수집 파일 생성
- 실행:
  - `python scripts/simple_rss_collector.py --output "C:\MyAIWorker\inputs\rss" --hours 24 --max-items 1`
- 기대:
  - `C:\MyAIWorker\inputs\rss\` 하위에 `.md` 파일이 1개 이상 생성됨

2) Perplexity 이메일->파일 드롭 확인(동기화 포함)
- 기대:
  - `C:\MyAIWorker\inputs\perplexity\` 하위에 `*_perplexity.md` 파일이 생성됨

3) Claude 처리 결과 생성
- 실행(예시):
  - `cd C:\MyAIWorker` 후 `claude "inputs 폴더 읽고 outputs에 daily_report_YYYY-MM-DD.md 작성"`
- 기대:
  - `C:\MyAIWorker\outputs\daily_report_YYYY-MM-DD.md` 파일이 생성됨
