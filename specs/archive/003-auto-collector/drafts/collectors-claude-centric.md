# Draft: Collectors.md Claude-Centric Rewrite

## Goal
- Update `C:\picko-scripts\Collectors.md` to align with the local-first workflow in `C:\picko-scripts\mock_vault\config\Folders_to_operate_social-media_copied_from_Vault\0. 프레임워크\Collector_automation.md`.
- Make Claude the primary “processor”: Claude Code (CLI) + optional Picko scripts.
- Demote/mark as optional anything that conflicts (Make as “email-to-file only”, Notion/Placid/Bannerbear as optional).

## Conflict Map (what must change)
- Collectors.md currently: Make trigger(RSS) -> Claude API -> Placid/Bannerbear -> Notion 저장.
- Collector_automation.md: RSS는 로컬 파일로 떨어뜨리기(파이썬) + Perplexity는 이메일->파일( Make/Zapier ) + 로컬 동기화 + Claude Code가 폴더를 읽고 결과 작성.

## Proposed Collectors.md Replacement (ready-to-paste)

# 로컬 기반 글로벌 레퍼런스 수집 및 Claude 처리 워크플로우

이 문서는 해외 뉴스레터/블로그/커뮤니티 레퍼런스를 **로컬 폴더에 파일로 누적**하고,
**Claude Code(CLI)** 또는 Picko 파이프라인으로 요약/추출/콘텐츠 제작까지 연결하는 운영 가이드입니다.

## 0) 폴더 구조(정본) — 반드시 하나로 통일

권장(프레임워크 기준):
- 작업 루트: `C:\MyAIWorker\`
- 입력(원천 파일): `C:\MyAIWorker\inputs\`
  - `rss\` / `perplexity\`
- 출력(요약/리포트): `C:\MyAIWorker\outputs\`

Picko(Obsidian Vault)로 운영할 경우 정본:
- Vault root: (사용자 환경의 Vault 경로)
- Inputs 노트: `Inbox/Inputs/`
- Digest: `Inbox/Inputs/_digests/`
- 생성물: `Content/Longform/`, `Content/Packs/`, `Assets/Images/_prompts/`

중요:
- `simple_rss_collector.py` 기본 출력은 `./inbox/rss`이므로, Vault 기반 운영이라면 반드시 `--output`으로 Vault 하위 폴더를 지정한다.

## 1) 수집 (Inputs를 파일로 떨어뜨리기)

핵심 원칙:
- AI가 바로 처리할 수 있도록, 먼저 레퍼런스를 **파일(.md/.txt)** 로 저장한다.
- 수집은 자동화하되, 처리는 Claude가 로컬 폴더를 읽는 구조로 단순화한다.

### 1.1 RSS 수집 (Python)

- 가장 단순한 방법(가벼운 수집, 로컬 폴더에 누적):
  - 스크립트: `C:\picko-scripts\scripts\simple_rss_collector.py`
  - 예시:
    - `python scripts/simple_rss_collector.py --output "C:\MyAIWorker\inputs\rss" --hours 24 --max-items 20`
    - 기본값: 날짜별 폴더 생성(YYYY-MM-DD) / 비활성화: `--no-by-date`

- Vault에 바로 떨어뜨리기(선택):
  - `python scripts/simple_rss_collector.py --output "<VAULT_ROOT>\Inbox\Inputs" --hours 24 --max-items 20`

- Picko 파이프라인을 쓰는 방법(권장, Vault/디듀프/다이제스트 포함):
  - `python -m scripts.daily_collector --dry-run`
  - `python -m scripts.daily_collector --sources techcrunch ai_news --max-items 10`

### 1.2 RSS가 없는 사이트(선택)

- RSS가 없는 사이트는 RSS.app/FetchRSS 같은 도구로 **피드를 생성**할 수 있다.
- 단, 운영의 중심은 “로컬 파일 축적 + Claude 처리”이며, 피드 생성 도구는 보조 수단이다.

### 1.3 Perplexity Tasks 결과 수집 (이메일 -> 파일)

Perplexity Tasks 결과는 이메일로 오므로, 아래 중 하나로 파일로 저장한다.

- Make(추천) 또는 Zapier: 이메일 수신 -> Google Drive/Dropbox에 `.md` 저장 -> 로컬 동기화
- 구체 설정법: `C:\picko-scripts\mock_vault\config\Folders_to_operate_social-media_copied_from_Vault\0. 프레임워크\Perplexity_email_setup.md`

운영 규칙(최소):
- 파일명은 `YYYY-MM-DD_HH-mm-ss_perplexity.md`처럼 시간 포함(중복 방지)
- 본문은 가능한 `text/plain`을 저장(HTML은 파싱 이슈)
- 저장 인코딩은 UTF-8

## 2) 처리 (Claude 중심)

### 2.1 Claude Code(CLI)로 폴더 처리

- Claude Code는 실행된 폴더의 파일을 읽고, 결과를 파일로 남기는 데 강하다.

예시 프롬프트:
> "inputs 폴더의 새 RSS 파일 + Perplexity 리포트를 읽고, 중복 제거 후 오늘의 핵심 3개만 뽑아서 daily_report.md로 작성해줘."

실행 규칙:
- 권장 실행 위치: `C:\MyAIWorker\`
- 입력: `C:\MyAIWorker\inputs\`
- 출력: `C:\MyAIWorker\outputs\daily_report_YYYY-MM-DD.md`

### 2.2 Picko로 생성 단계까지 연결(선택)

- 승인된 다이제스트 기반으로 롱폼/팩/이미지 프롬프트 생성:
  - `python -m scripts.generate_content`
  - `python -m scripts.generate_content --type longform packs`

## 3) 자동화 (스케줄링)

- RSS 수집은 Windows 작업 스케줄러로 주기 실행
- Perplexity는 이메일->파일 변환(Make/Zapier) + 클라우드 앱 로컬 동기화
- Claude 처리는 (1) 수동 실행 또는 (2) 일정 주기로 CLI 실행(원하면 후속으로 자동화)

동기화(Vault가 Google Drive/Dropbox일 때) 주의:
- 기존 파일에 append보다 “새 파일 생성”이 안전
- 대량 생성은 배치 처리(동기화 충돌 감소)
- DB/인덱스(있다면)는 동기화 폴더 밖 로컬 경로 권장

## 4) 출력/저장 (선택)

- 기본은 로컬 Markdown 파일로 보존(검색/히스토리 관리)
- Notion/DB 저장은 “추가 모듈”로만 취급한다(핵심 경로에서 분리)

## 5) 디자인 자동화 (선택)

- 이미지/썸네일 렌더링은 별도 파이프라인로 분리하는 것을 권장
- Placid/Bannerbear는 옵션, 로컬 HTML 템플릿 + Playwright 렌더링도 옵션

---

## Notes
- Collectors.md에 남아 있던 "Make 트리거(RSS) -> Claude API -> Placid/Bannerbear -> Notion" 흐름은 본 문서의 기본 아키텍처에서 제외(충돌 방지).
- Make/Zapier는 Perplexity 이메일을 파일로 떨어뜨리는 용도로만 우선 사용.

## Acceptance Criteria (자동 검증 기준)

1) RSS 수집 파일 생성
- 실행:
  - `python scripts/simple_rss_collector.py --output "C:\MyAIWorker\inputs\rss" --hours 24 --max-items 1`
- 기대:
  - `C:\MyAIWorker\inputs\rss\` 하위에 `.md` 파일이 1개 이상 생성됨

2) Perplexity 이메일→파일 드롭 확인(동기화 포함)
- 기대:
  - `C:\MyAIWorker\inputs\perplexity\` 하위에 `*_perplexity.md` 파일이 생성됨(파일명에 타임스탬프 포함)

3) Claude 처리 결과 생성
- 실행(예시):
  - `cd C:\MyAIWorker` 후 `claude "inputs 폴더 읽고 outputs에 daily_report_YYYY-MM-DD.md 작성"`
- 기대:
  - `C:\MyAIWorker\outputs\daily_report_YYYY-MM-DD.md` 파일이 생성됨
