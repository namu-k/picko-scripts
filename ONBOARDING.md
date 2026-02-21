# Picko 온보딩 가이드

**새 팀원을 위한 30분 퀵스타트**

---

## 목차

1. [Picko가 뭔가요?](#picko가-뭔가요) (2분)
2. [어떻게 작동하나요?](#어떻게-작동하나요) (3분)
3. [설치하기](#설치하기) (10분)
4. [첫 실행](#첫-실행) (10분)
5. [일일 워크플로우](#일일-워크플로우) (5분)
6. [필수 파일](#필수-파일)
7. [FAQ](#faq)

---

## Picko가 뭔가요?

**한 문장 요약**: RSS 피드에서 콘텐츠를 자동 수집하고, AI가 블로그/소셜미디어용 콘텐츠를 생성하는 시스템입니다.

### 무엇을 자동화하나요?

```
📦 수집 (자동)  →  🧠 분석 (AI)  →  👀 검토 (사람)  →  ✍️ 생성 (AI)
   RSS 피드         요약/점수        체크박스 승인      블로그/소셜
```

### 주요 산출물

| 산출물 | 위치 | 예시 |
|--------|------|------|
| Input 노트 | `Inbox/Inputs/` | 수집된 원본 콘텐츠 |
| Digest | `Inbox/Inputs/_digests/` | 일일 요약 (승인용) |
| Longform | `Content/Longform/` | 블로그 포스트 |
| Packs | `Content/Packs/` | 트위터/링크드인/뉴스레터 |
| Image Prompt | `Assets/Images/_prompts/` | AI 이미지 프롬프트 |

---

## 어떻게 작동하나요?

### 파이프라인 플로우

```
1. daily_collector.py 실행
   ↓
2. RSS 피드에서 새 글 수집
   ↓
3. 로컬 LLM으로 요약/태깅
   ↓
4. 임베딩으로 유사도 계산
   ↓
5. 점수 계산 (참신도 + 관련도 + 품질)
   ↓
6. Input 노트 + Digest 생성
   ↓
7. 👤 사람이 Digest에서 승인 (체크박스)
   ↓
8. generate_content.py 실행
   ↓
9. 승인된 항목 → 블로그/소셜 콘텐츠 생성
```

### 점수 시스템

각 콘텐츠는 0~1점으로 평가됩니다:

- **0.85+**: 자동 승인 후보
- **0.4~0.85**: 사람이 검토 필요
- **0.4 미만**: 자동 제외

---

## 설치하기

### 1. 저장소 클론

```bash
git clone https://github.com/namu-k/picko-scripts.git
cd picko-scripts
```

### 2. Python 가상환경

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. API 키 설정

`.env` 파일 생성:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

`.env` 내용:

```env
OPENAI_API_KEY=sk-your-key-here
# 또는
RELAY_API_KEY=your-relay-key
```

> 💡 **API 키 발급**: [OpenAI](https://platform.openai.com/api-keys) 또는 [OpenRouter](https://openrouter.ai/)

### 5. 설정 파일 확인

**config/config.yml**에서 Vault 경로 확인:

```yaml
vault:
  root: "c:/picko-scripts/mock_vault"  # 이 경로가 존재해야 함
```

### 6. 로컬 LLM 설치 (선택, 비용 절감용)

```bash
# Ollama 설치: https://ollama.ai/download

# 모델 다운로드
ollama pull qwen2.5:3b        # 요약/태깅용 (3B, 가벼움)
ollama pull qwen3-embedding:0.6b  # 임베딩용
```

---

## 첫 실행

### Step 1: 시스템 체크

```bash
python -m scripts.health_check
```

**성공 시 출력:**
```
✅ Vault Access: Read/Write OK
✅ OpenAI API Key: Configured
✅ RSS Sources: All sources accessible
```

**실패 시**: 에러 메시지에 따라 설정 수정

---

### Step 2: 테스트 수집 (dry-run)

```bash
python -m scripts.daily_collector --dry-run
```

실제로 저장하지 않고 시뮬레이션만 실행합니다.

---

### Step 3: 실제 수집

```bash
python -m scripts.daily_collector
```

**생성되는 파일:**
- `Inbox/Inputs/input_xxx.md` - 개별 콘텐츠들
- `Inbox/Inputs/_digests/2026-02-21.md` - 일일 요약

---

### Step 4: 승인하기

1. Obsidian으로 `mock_vault/` 열기
2. `Inbox/Inputs/_digests/오늘날짜.md` 열기
3. 승인할 항목 체크:

```markdown
## [ ] OpenAI의 새로운 모델 발표
      ↑ 체크하세요
```

---

### Step 5: 콘텐츠 생성

```bash
python -m scripts.generate_content
```

**생성되는 파일:**
- `Content/Longform/longform_xxx.md`
- `Content/Packs/twitter/pack_xxx_twitter.md`
- `Content/Packs/linkedin/pack_xxx_linkedin.md`

---

## 일일 워크플로우

### 매일 아침 (15분)

```
1. 수집 실행
   $ python -m scripts.daily_collector

2. Obsidian에서 Digest 열기
   Inbox/Inputs/_digests/YYYY-MM-DD.md

3. 승인할 항목 체크

4. 생성 실행
   $ python -m scripts.generate_content

5. 생성된 콘텐츠 검토
   Content/Longform/
   Content/Packs/
```

### CLI 치트시트

| 명령어 | 설명 |
|--------|------|
| `python -m scripts.daily_collector` | 오늘 수집 |
| `python -m scripts.daily_collector --dry-run` | 테스트 수집 |
| `python -m scripts.daily_collector --sources techcrunch` | 특정 소스만 |
| `python -m scripts.generate_content` | 승인 항목 생성 |
| `python -m scripts.generate_content --auto-all` | 모든 항목 생성 |
| `python -m scripts.health_check` | 시스템 상태 확인 |

---

## 필수 파일

### 자주 수정하는 파일

| 파일 | 용도 | 수정 시점 |
|------|------|----------|
| `config/config.yml` | 메인 설정 | 초기 설정, LLM 변경 |
| `config/sources.yml` | RSS 소스 | 새 소스 추가/제거 |
| `config/accounts/*.yml` | 계정 프로필 | 관심사, 키워드 변경 |

### 프롬프트 템플릿

| 위치 | 용도 |
|------|------|
| `config/prompts/longform/` | 블로그 포스트 생성 |
| `config/prompts/packs/` | 소셜 미디어 생성 |
| `config/prompts/image/` | 이미지 프롬프트 |

### 폴더 구조

```
picko-scripts/
├── config/           # 설정 파일들
├── picko/            # 핵심 Python 모듈
├── scripts/          # 실행 스크립트
├── logs/             # 실행 로그
├── cache/            # 임베딩 캐시
└── mock_vault/       # Obsidian Vault (콘텐츠 저장소)
    ├── Inbox/
    │   └── Inputs/   # 수집된 콘텐츠
    │       └── _digests/  # 일일 요약
    ├── Content/      # 생성된 콘텐츠
    │   ├── Longform/ # 블로그
    │   └── Packs/    # 소셜 미디어
    └── Assets/
        └── Images/_prompts/  # 이미지 프롬프트
```

---

## FAQ

### Q: API 키 에러가 나요

```
Error: OPENAI_API_KEY not found
```

**해결:**
1. `.env` 파일이 프로젝트 루트에 있는지 확인
2. 키 앞에 공백이 없는지 확인
3. `OPENAI_API_KEY=` 뒤에 실제 키 입력

---

### Q: Vault 경로 에러가 나요

```
FileNotFoundError: Vault root not found
```

**해결:**
`config/config.yml`의 `vault.root`를 실제 경로로 수정

---

### Q: 로컬 LLM을 사용하고 싶어요

**단계:**
1. Ollama 설치: https://ollama.ai/download
2. 모델 설치: `ollama pull qwen2.5:3b`
3. `config/config.yml` 수정:
```yaml
summary_llm:
  provider: "ollama"
  model: "qwen2.5:3b"
```

---

### Q: 생성된 콘텐츠 품질이 낮아요

**해결 방법들:**
1. 승인 임계값 높이기:
   ```yaml
   scoring:
     thresholds:
       auto_approve: 0.90  # 0.85 → 0.90
   ```
2. 관심 키워드 구체화: `config/accounts/*.yml`
3. 더 나은 모델 사용: `gpt-4o` (비용 ↑ 품질 ↑)

---

### Q: 새 RSS 소스를 추가하고 싶어요

**`config/sources.yml`에 추가:**
```yaml
sources:
  - id: "my_source"
    type: "rss"
    url: "https://example.com/feed"
    category: "custom"
    enabled: true
```

---

### Q: 로그를 확인하고 싶어요

```bash
# 오늘 로그
cat logs/2026-02-21/daily_collector.log

# 에러만
cat logs/2026-02-21/errors.log
```

---

## 다음 단계

- [USER_GUIDE.md](USER_GUIDE.md) - 상세 사용법
- [CLAUDE.md](CLAUDE.md) - 개발자 문서
- [config/sources.yml](config/sources.yml) - 소스 커스터마이징
- [config/accounts/](config/accounts/) - 계정 페르소나 설정

---

## 도움이 필요하면

- **이슈 등록**: [GitHub Issues](https://github.com/namu-k/picko-scripts/issues)
- **기존 이슈 검색**: 먼저 비슷한 문제가 있었는지 확인

---

*환영합니다! 질문이 있으면 언제든 이슈를 등록하세요.*
