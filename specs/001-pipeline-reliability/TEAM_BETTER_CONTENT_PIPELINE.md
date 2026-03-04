# Better Content Pipeline 팀

> 브랜치: `improve/content-pipeline-ux`
> 목표: 콘텐츠 파이프라인 UX 개선 작업을 체계적으로 수행
> 시작일: 2026-02-16

---

## 1. 팀 구성

### 1.1 핵심 팀원

| 역할 | 담당자 | 책임 범위 |
|------|--------|-----------|
| **프로젝트 리드** | @primary | 전체 일정 관리, 의사결정, 이슈 우선순위 |
| **백엔드 개발자** | @backend | 파이프라인 로직 수정, 데이터 모델 변경, API 연동 |
| **프롬프트 엔지니어** | @prompt | 프롬프트 외부화, 레퍼런스 기반 문체 설계, 템플릿 작성 |
| **UX 설계자** | @ux | 승인 흐름 설계, 채널 선택 UI, 사용자 경험 개선 |

### 1.2 협력 인력 (필요시)

| 역할 | 업무 |
|------|------|
| **QA** | 변경사항 테스트, 회귀 테스트, 검증 |
| **테크니컬 라이터** | 문서화, 변경 로그, 사용자 가이드 |

---

## 2. 역할별 상세 책임

### 2.1 프로젝트 리드 (@primary)

**핵심 책임**:
- 주간 진행 상황 체크 및 블로커 해결
- PR 리뷰 및 머지 결정
- 이해관계자 커뮤니케이션

**필요 역량**:
- 콘텐츠 파이프라인 전체 흐름 이해
- Obsidian Vault 운영 경험
- 기본적인 Python 코드 리딩

---

### 2.2 백엔드 개발자 (@backend)

**핵심 책임**:
- `scripts/generate_content.py` 리팩토링
- 프롬프트 로더 모듈 구현 (`picko/prompt_loader.py`)
- 데이터 모델 확장 (frontmatter 필드 추가)
- 탐색 스크립트 구현 (`scripts/explore_topic.py`)

**주요 작업 영역**:
```
picko/
├── prompt_loader.py      # NEW: 프롬프트 파일 로드
├── templates.py          # 수정: 템플릿 로직 분리
└── vault_io.py           # 수정: 새 frontmatter 필드

scripts/
├── generate_content.py   # 대폭 수정
├── explore_topic.py      # NEW: 탐색 단계 스크립트
└── validate_output.py    # 수정: 새 필드 검증

config/prompts/           # NEW: 프롬프트 저장소
```

**필요 역량**:
- Python 3.13+ 숙련
- Jinja2 템플릿 엔진
- YAML/Markdown 파싱
- 비동기 프로그래밍 (LLM 호출)

---

### 2.3 프롬프트 엔지니어 (@prompt)

**핵심 책임**:
- 롱폼/팩/이미지 프롬프트 작성 및 최적화
- 레퍼런스 글 수집 및 분석
- 채널별 톤앤매너 정의
- 프롬프트 버전 관리

**주요 산출물**:
```
config/prompts/
├── longform/
│   ├── default.md
│   ├── reference_style.md
│   └── _variables.yml        # 공통 변수
├── packs/
│   ├── twitter.md
│   ├── linkedin.md
│   ├── newsletter.md
│   └── _channel_defaults.yml
└── image/
    ├── default.md
    └── channel_layouts.md
```

**필요 역량**:
- LLM 프롬프트 엔지니어링 경험
- 한국어 콘텐츠 작성 감각
- A/B 테스트 설계 능력
- 콘텐츠 마케팅 이해

---

### 2.4 UX 설계자 (@ux)

**핵심 책임**:
- 승인 흐름 사용자 여정 설계
- 다이제스트/롱폼 노트 내 체크리스트 UX
- 채널 선택 인터페이스 설계
- 에러/상태 메시지 정의

**주요 산출물**:
- 승인 흐름 다이어그램
- Frontmatter 필드 명세서
- Obsidian 템플릿 업데이트 가이드
- 사용자 스토리 문서

**필요 역량**:
- Obsidian 일일 사용자
- Markdown/YAML frontmatter 이해
- 사용자 흐름 설계 경험
- 콘텐츠 제작 워크플로 이해

---

## 3. 작업 단계별 팀원 배정

### Phase 1: 프롬프트 외부화 (1주차)

| 태스크 | 담당 | 협업 |
|--------|------|------|
| 프롬프트 파일 구조 설계 | @prompt | @backend |
| `prompt_loader.py` 구현 | @backend | - |
| 기존 프롬프트 추출 & 변환 | @prompt | - |
| `generate_content.py` 리팩토링 | @backend | @prompt |
| 통합 테스트 | @backend | @primary |

### Phase 2: 주제 탐색 단계 (2주차)

| 태스크 | 담당 | 협업 |
|--------|------|------|
| 탐색 결과물 포맷 설계 | @prompt | @ux |
| `explore_topic.py` 구현 | @backend | @prompt |
| 다이제스트 → 탐색 → 롱폼 흐름 연결 | @backend | @primary |
| 탐색 노트 템플릿 작성 | @prompt | - |

### Phase 3: 파생 승인 단계 (3주차)

| 태스크 | 담당 | 협업 |
|--------|------|------|
| 승인 흐름 설계 | @ux | @primary |
| Frontmatter 필드 확장 | @backend | @ux |
| 팩/이미지 생성 조건 로직 | @backend | - |
| 검증 스크립트 업데이트 | @backend | - |

### Phase 4: 레퍼런스 & 채널 (4주차)

| 태스크 | 담당 | 협업 |
|--------|------|------|
| 레퍼런스 글 수집 | @prompt | @primary |
| 채널별 프롬프트 최적화 | @prompt | - |
| 이미지/레이아웃 추천 로직 | @backend | @prompt |
| 채널 선택 UI 설계 | @ux | - |

---

## 4. 이슈 템플릿

### 4.1 프롬프트 외부화

```markdown
## 🎯 목표
롱폼/팩/이미지 프롬프트를 코드에서 분리하여 관리 용이성 확보

## 📦 산출물
- [ ] `config/prompts/` 디렉토리 구조
- [ ] `picko/prompt_loader.py` 모듈
- [ ] 마이그레이션된 프롬프트 파일들
- [ ] 수정된 `generate_content.py`

## ✅ 완료 조건
- [ ] 기존 기능 100% 호환
- [ ] 새 프롬프트 추가가 파일만으로 가능
- [ ] 테스트 커버리지 유지

## 🔗 관련
- docs/improvement-content-pipeline.md 섹션 2.2, 2.4
```

### 4.2 주제 탐색 단계

```markdown
## 🎯 목표
승인된 입력을 바탕으로 주제 확장, 인사이트 도출 단계 추가

## 📦 산출물
- [ ] `scripts/explore_topic.py`
- [ ] 탐색 노트 템플릿
- [ ] 롱폼 생성 시 탐색 결과 주입 로직

## ✅ 완료 조건
- [ ] 탐색 결과가 롱폼 품질에 긍정적 영향
- [ ] 선택적 실행 가능 (skip 옵션)

## 🔗 관련
- docs/improvement-content-pipeline.md 섹션 2.1
```

### 4.3 파생 승인 단계

```markdown
## 🎯 목표
롱폼 완성 후 팩/이미지 생성 여부를 별도 승인하도록 흐름 변경

## 📦 산출물
- [ ] 확장된 frontmatter 스키마
- [ ] 조건부 생성 로직
- [ ] 업데이트된 검증 스크립트

## ✅ 완료 조건
- [ ] 롱폼만 생성 가능
- [ ] 승인 후 팩/이미지 생성 가능
- [ ] 기존 데이터와 호환

## 🔗 관련
- docs/improvement-content-pipeline.md 섹션 2.3
```

---

## 5. 주간 리듬

| 요일 | 활동 |
|------|------|
| **월** | 주간 계획, 이슈 배정 |
| **수** | 중간 체크인, 블로커 공유 |
| **금** | PR 리뷰 데드라인, 회고 |

---

## 6. 커뮤니케이션 채널

- **진행 상황**: 이 문서 + docs/improvement-content-pipeline.md
- **이슈 트래킹**: GitHub Issues (라벨: `pipeline-improvement`)
- **즉각 논의**: 필요시 미팅 or async 논의

---

## 7. GitHub Issues

| Issue | 제목 | Phase | 상태 |
|-------|------|-------|------|
| [#3](https://github.com/namu-k/picko-scripts/issues/3) | [BCP-001] 프롬프트 외부화 | Phase 1 | 🔴 Open |
| [#4](https://github.com/namu-k/picko-scripts/issues/4) | [BCP-002] 주제 탐색 단계 | Phase 2 | 🔴 Open |
| [#5](https://github.com/namu-k/picko-scripts/issues/5) | [BCP-003] 파생 승인 단계 | Phase 3 | 🔴 Open |
| [#6](https://github.com/namu-k/picko-scripts/issues/6) | [BCP-004] 레퍼런스 기반 문체 | Phase 4 | 🔴 Open |
| [#7](https://github.com/namu-k/picko-scripts/issues/7) | [BCP-005] 채널별 이미지·레이아웃 | Phase 4 | 🔴 Open |
| [#8](https://github.com/namu-k/picko-scripts/issues/8) | [BCP-006] 채널 선택 옵션화 | Phase 4 | 🔴 Open |

**의존성 그래프**:
```
#3 (프롬프트 외부화)
  ↓
├── #4 (주제 탐색)
├── #5 (파생 승인) ─→ #8 (채널 선택)
├── #6 (레퍼런스 문체)
└── #7 (이미지/레이아웃)
```

**권장 진행 순서**:

```
1단계: #3 (프롬프트 외부화) ← 선행 없음, 가장 먼저

2단계: #3 완료 후 (순차 또는 병렬 가능)
   ├── #4 (주제 탐색)
   ├── #5 (파생 승인)  ← #8의 선행
   ├── #6 (레퍼런스 문체)
   └── #7 (이미지/레이아웃)

3단계: #5 완료 후
   └── #8 (채널 선택)
```

**병렬 진행 가능 조합**:
- Track A: #4 + #6 + #7 (탐색/문체/이미지)
- Track B: #5 → #8 (승인 흐름)

**참고**: #4, #5, #6, #7은 모두 #3에만 의존하므로, 담당자/리소스에 따라 유연하게 조정 가능

---

## 8. 다음 단계

1. [x] 팀원 확정 (역할 정의 완료)
2. [x] GitHub Issue 생성 (6개 이슈)
3. [ ] Phase 1 착수 (#3: 프롬프트 외부화)
4. [ ] 주간 체크인 리듬 확립
