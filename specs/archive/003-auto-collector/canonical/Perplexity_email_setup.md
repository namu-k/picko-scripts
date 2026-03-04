# Perplexity 이메일 → 파일 변환 설정 가이드

> Perplexity Tasks의 결과를 이메일로 받아, 자동으로 로컬 폴더에 파일로 저장하는 방법

Perplexity는 스케줄된 태스크 결과를 **이메일로 전송**합니다. 이를 자동으로 파일로 변환하려면 **Make(구 Integromat)** 또는 **Zapier**를 사용해야 합니다.

---

## 개요

```
Perplexity Tasks → 이메일 발송 → Make/Zapier 수신 → 클라우드 저장 → 로컬 동기화
```

---

## 방법 1: Make (Integromat) 사용 (추천)

### 1단계: Make 계정 생성

1. https://www.make.com 접속
2. 무료 계정 생성 (월 1,000회 무료)

### 2단계: 시나리오 생성

**새 시나리오 생성:**

1. "Create a new scenario" 클릭
2. 검색창에 "Gmail" 입력 → Gmail 모듈 추가
3. "Watch emails" 선택

**Gmail 설정:**

```
Connection: [Google 계정 연결]
Folder: Inbox
Filter type: Gmail filter
Query: from:perplexity.ai subject:"Perplexity"
Maximum number of results: 10
```

### 3단계: 파일 저장 모듈 추가

**Google Drive 또는 Dropbox 선택:**

**Google Drive 옵션:**
1. "+" 버튼 → "Google Drive" 검색
2. "Upload a file" 선택
3. 설정:
   ```
   Connection: [Google 계정 연결]
   Destination: Select "My Drive"
   Folder: "AIWorker/perplexity" (폴더 생성)
   File name: {{formatDate(now; "YYYY-MM-DD_HH-mm-ss")}}_perplexity.md
   Data: {{text}}
   ```

**Dropbox 옵션:**
1. "+" 버튼 → "Dropbox" 검색
2. "Create/upload a file" 선택
3. 설정:
   ```
   Connection: [Dropbox 계정 연결]
   Folder: /Apps/AIWorker/perplexity
   File name: {{formatDate(now; "YYYY-MM-DD_HH-mm-ss")}}.md
   Data: {{text}}
   ```

### 4단계: 스케줄 설정

1. 시나리오 하단의 "Scheduling" 클릭
2. "Run scenario" 설정:
   ```
   Every: 15 minutes (또는 1 hour)
   ```

### 5단계: 로컬 동기화

**Google Drive Desktop:**
1. https://www.google.com/drive/download/ 설치
2. 설정에서 "Mirror files" 선택
3. `C:\Users\[사용자]\My Drive\AIWorker\perplexity` 폴더 확인

**Dropbox Desktop:**
1. https://www.dropbox.com/install 설치
2. `C:\Users\[사용자]\Dropbox\Apps\AIWorker\perplexity` 폴더 확인

---

## 방법 2: Zapier 사용

### 1단계: Zapier 계정 생성

1. https://zapier.com 접속
2. 무료 계정 생성 (월 100회 무료)

### 2단계: Zap 생성

**Trigger 설정:**

```
App: Gmail
Event: New Email Matching Search
Connection: [Google 계정 연결]
Search String: from:perplexity.ai
```

**Action 설정 (Google Drive):**

```
App: Google Drive
Event: Create File from Text
Connection: [Google 계정 연결]
Drive: My Google Drive
Folder: AIWorker/perplexity
File Name: {{zap_meta_human_now}}_perplexity.md
File Content: {{body_plain}}
```

### 3단계: Zap 활성화

1. "Test trigger" 클릭하여 테스트
2. "Publish" 클릭하여 활성화

---

## 방법 3: Python 스크립트 직접 사용 (고급)

Make/Zapier 없이 이메일을 직접 모니터링하는 방법:

### Gmail API 사용

```python
# scripts/perplexity_email_collector.py

import base64
import os
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Gmail API 서비스 가져오기"""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_perplexity_emails(service, max_results=10):
    """Perplexity에서 온 이메일 가져오기"""
    query = "from:perplexity.ai"
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()

        # 이메일 본문 추출
        body = ""
        if "payload" in msg_data:
            parts = msg_data["payload"].get("parts", [])
            for part in parts:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break

        # 제목 추출
        subject = ""
        for header in msg_data["payload"].get("headers", []):
            if header["name"] == "Subject":
                subject = header["value"]
                break

        emails.append({"id": msg["id"], "subject": subject, "body": body})

    return emails


def save_to_file(email, output_dir: Path):
    """이메일을 마크다운 파일로 저장"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"perplexity_{timestamp}_{email['id'][:8]}.md"
    filepath = output_dir / filename

    content = f"""---
source: "Perplexity Tasks"
collected_at: "{datetime.now().isoformat()}"
email_id: "{email['id']}"
---

# {email['subject']}

{email['body']}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main():
    output_dir = Path("./inbox/perplexity")
    output_dir.mkdir(parents=True, exist_ok=True)

    service = get_gmail_service()
    emails = get_perplexity_emails(service)

    for email in emails:
        filepath = save_to_file(email, output_dir)
        print(f"Saved: {filepath.name}")


if __name__ == "__main__":
    main()
```

**설정:**
1. Google Cloud Console에서 Gmail API 활성화
2. OAuth 2.0 클라이언트 ID 생성 → `credentials.json` 다운로드
3. `pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client`
4. `python scripts/perplexity_email_collector.py` 실행

---

## 로컬 동기화 확인

동기화가 완료되면 다음 폴더에서 파일을 확인할 수 있습니다:

```
# Google Drive
C:\Users\[사용자]\My Drive\AIWorker\perplexity\

# Dropbox
C:\Users\[사용자]\Dropbox\Apps\AIWorker\perplexity\
```

---

## Windows 작업 스케줄러 설정 (주기적 실행)

### RSS 수집기 자동 실행

1. `Win + R` → `taskschd.msc` 입력
2. "작업 만들기" 클릭
3. **일반 탭:**
   - 이름: `Picko RSS Collector`
   - "사용자가 로그온했는지 여부에 관계없이 실행" 체크
4. **트리거 탭:**
   - "새로 만들기" → "매일" → "반복 간격: 1일"
   - 시작 시간: 오전 6:00
5. **동작 탭:**
   - "프로그램 시작"
   - 프로그램: `python`
   - 인수: `C:\picko-scripts\scripts\simple_rss_collector.py --output C:\MyAIWorker\inputs\rss --hours 24`
   - 시작 위치: `C:\picko-scripts`

### Perplexity 이메일 수집 (Python 방식)

동일한 방식으로 `perplexity_email_collector.py` 스케줄 등록

---

## 파일 구조 예시

```
C:\MyAIWorker\
├── inputs\
│   ├── rss\
│   │   └── 2024-01-15\
│   │       ├── TechCrunch_Article_Title_abc123.md
│   │       └── Hacker_News_Post_def456.md
│   └── perplexity\
│       ├── perplexity_2024-01-15_08-30-00_ghi789.md
│       └── perplexity_2024-01-15_14-45-00_jkl012.md
└── outputs\
    └── daily_report_2024-01-15.md
```

---

## 비용 비교

| 서비스 | 무료 한도 | 유료 플랜 |
|--------|----------|----------|
| Make | 1,000회/월 | $9/월 (10,000회) |
| Zapier | 100회/월 | $19.99/월 (750회) |
| Python 직접 | 무제한 | - |

---

## 문제 해결

### 이메일이 수신되지 않음
1. Perplexity에서 이메일 알림이 켜져 있는지 확인
2. Gmail 스팸 폴더 확인
3. Make/Zapier 연결 상태 확인

### 파일이 동기화되지 않음
1. Google Drive/Dropbox 동기화 앱이 실행 중인지 확인
2. 동기화 폴더 설정 확인
3. 인터넷 연결 상태 확인

### 한글 깨짐
- 모든 파일은 UTF-8로 저장되어야 함
- Make에서 "Data" 필드에 `{{utf8encode(text)}}` 사용

---

## 참고 링크

- [Make Documentation](https://www.make.com/en/help)
- [Zapier Gmail Integration](https://zapier.com/apps/gmail/integrations)
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
