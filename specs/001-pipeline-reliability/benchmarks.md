# 파이프라인 벤치마크·테스트 시나리오

> 공통 평가지표와 시나리오 목록을 정의합니다. 시나리오 YAML은 `tests/benchmarks/scenarios/` 에 있습니다.

---

## 1. 시나리오 목록

### 1.1 엔드투엔드 작업 시나리오 (E2E)

| ID  | 이름                     | 정의 파일                          | 목적 |
|-----|--------------------------|------------------------------------|------|
| S1  | 고밀도 기술 기사         | `e2e/s1-high-density-tech.yml`     | 기술 블로그/리서치 성격 피드로 롱폼·구조·소셜 길이 검증 |
| S2  | 엣지/저품질 소스         | `e2e/s2-edge-low-quality.yml`     | 클릭베이트·짧은 본문에서 요약/점수/생성 품질 검증 |
| S3  | 다국어·혼합 언어         | `e2e/s3-multilingual.yml`         | 한/영 혼합 등에서 언어 일관성·이미지 프롬프트 검증 |
| S4  | 단일 소스 집중           | `e2e/s4-single-source.yml`         | 한 소스만 사용해 소스별 볼륨·에러 패턴 검증 |
| S5  | 전체 소스·전체 타입      | `e2e/s5-full-pipeline.yml`         | sources 생략 전체 수집·전체 타입 생성, 부하·안정성 검증 |
| S6  | 재생성(force)            | `e2e/s6-force-regenerate.yml`      | 이미 생성된 콘텐츠 --force 덮어쓰기 동작·일관성 검증 |
| S7  | 주간 슬롯(week-of)       | `e2e/s7-week-slot.yml`             | WeeklySlot 적용 생성, CTA·필러 분포 반영 검증 |
| S8  | 최소 승인 경로           | `e2e/s8-minimal-approval.yml`      | 1건만 승인 후 생성, 최소 경로 정상 동작 검증 |

### 1.2 기능 패키지별 시나리오 (Features)

| ID  | 이름                     | 정의 파일                              | 목적 |
|-----|--------------------------|----------------------------------------|------|
| F1  | 레퍼런스 계정 문체       | `features/f1-reference-account.yml`    | 계정 프로필/레퍼런스에 따른 톤·CTA 일관성 검증 |
| F2  | 이미지 프롬프트·레이아웃 | `features/f2-image-prompts.yml`       | 롱폼→채널별 이미지 프롬프트·레이아웃 추천 품질 |
| F3  | 글→프롬프트 추출         | `features/f3-prompt-extraction.yml`    | 레퍼런스 글에서 톤/구조 프롬프트 추출·재현도 검증 |
| F4  | 외부 프롬프트 로더       | `features/f4-prompt-loader.yml`       | config/prompts/ 로드·Jinja2·계정 오버라이드 검증 |
| F5  | 검증 스크립트            | `features/f5-validate-output.yml`      | validate_output 필수 필드·섹션·재귀 검증 동작 |
| F6  | 헬스체크                 | `features/f6-health-check.yml`        | API·vault·RSS·캐시 등 전제조건 점검 |
| F7  | 점수·스코어링            | `features/f7-scoring.yml`             | scoring 가중치·임계값·점수 분포 검증 |
| F8  | 임베딩·캐시              | `features/f8-embedding-cache.yml`     | embedding provider·캐시·폴백 동작 검증 |
| F9  | 다이제스트·입력 구조     | `features/f9-digest-input-structure.yml` | 다이제스트/입력 노트 frontmatter·필수 필드 검증 |

---

## 2. 공통 평가지표

모든 시나리오에서 공통으로 참조하는 지표입니다.

### 2.1 정량 지표

| 지표 ID      | 설명 | 수집 방법 |
|-------------|------|-----------|
| `success_rate` | 생성 성공률 (대상 중 정상 완료 비율) | 로그/출력 파일 개수로 계산 |
| `error_retry_rate` | LLM·API 에러·재시도 비율 | 로그에서 에러/재시도 카운트 |
| `length_compliance` | 롱폼·팩 길이 vs 설정(max_length 등) 준수 여부 | 생성물 메타·텍스트 길이 측정 |
| `duration` | 시나리오 전체 실행 시간(초) | 수동 측정 또는 로그 타임스탬프 |

### 2.2 반정량·정성 지표 (체크리스트 / 1–5점)

| 지표 ID        | 설명 |
|----------------|------|
| `content_quality` | 주제 명확성, 독자 인사이트, AI 티 정도 (1=매우 인위적, 5=자연스러움) |
| `account_consistency` | 레퍼런스·계정 톤/CTA와의 일치도 (1–5) |
| `image_prompt_quality` | 이미지 프롬프트가 본문·채널 가이드와 맞는지, 실사용 가능성 (1–5) |
| `extraction_fidelity` | 추출된 프롬프트가 원문 스타일을 잘 반영하는지 (1–5, F3 전용) |

---

## 3. 평가 템플릿 (실행 후 복사해 사용)

아래 블록을 복사해 실행별로 채우면 됩니다.

```markdown
## 실행 기록 — [시나리오 ID] [날짜 YYYY-MM-DD]

- **시나리오**: (예: S1 고밀도 기술 기사)
- **실행 일시**: 
- **변경 사항**(있을 경우): (예: writer_llm 모델 변경, 프롬프트 수정)

### 정량
- success_rate: 
- error_retry_rate: 
- length_compliance: (준수 / 일부 초과 / 미달)
- duration:  초

### 정성 (1–5)
- content_quality: 
- account_consistency: (해당 시)
- image_prompt_quality: (해당 시)
- extraction_fidelity: (F3만)

### 비고·이슈
- 
```

---

## 4. 시나리오별 상세

상세 명령·입력 조건은 각 YAML을 참고하세요.

- `tests/benchmarks/scenarios/e2e/*.yml`
- `tests/benchmarks/scenarios/features/*.yml`

자동 러너나 리포트 스크립트를 도입할 때도 이 YAML을 입력으로 사용할 수 있습니다.
