# 벤치마크·테스트 시나리오

파이프라인 변경 전후 비교와 품질 추적을 위한 **고정된 테스트 시나리오** 정의가 들어 있는 폴더입니다.

## 구조

```
tests/benchmarks/
├── README.md                 # 이 파일
├── scenarios/
│   ├── e2e/                  # 엔드투엔드 작업 시나리오 (수집 → 다이제스트 → 생성)
│   │   ├── s1-high-density-tech.yml
│   │   ├── s2-edge-low-quality.yml
│   │   ├── s3-multilingual.yml
│   │   ├── s4-single-source.yml
│   │   ├── s5-full-pipeline.yml
│   │   ├── s6-force-regenerate.yml
│   │   ├── s7-week-slot.yml
│   │   └── s8-minimal-approval.yml
│   └── features/             # 기능 패키지별 테스트 시나리오
│       ├── f1-reference-account.yml
│       ├── f2-image-prompts.yml
│       ├── f3-prompt-extraction.yml
│       ├── f4-prompt-loader.yml
│       ├── f5-validate-output.yml
│       ├── f6-health-check.yml
│       ├── f7-scoring.yml
│       ├── f8-embedding-cache.yml
│       └── f9-digest-input-structure.yml
```

- **e2e**: 전체 플로우(수집 → 다이제스트 → 롱폼/팩/이미지)를 한 번에 돌리는 시나리오. 같은 입력(날짜·소스)으로 반복 실행해 비교.
- **features**: 특정 기능만 격리해서 검증하는 시나리오(레퍼런스 계정, 이미지 프롬프트, 글→프롬프트 추출 등).

## 시나리오 정의 형식

각 YAML 파일은 다음을 포함합니다.

- `id`, `name`, `type`(e2e | feature), `description`
- 실행에 필요한 옵션(날짜, 소스, 스크립트 인자 등)
- 적용할 **공통 평가지표** 참조(지표 정의는 `docs/001-pipeline-reliability/benchmarks.md` 참고)

## 실행 방법

시나리오는 **수동 실행**을 전제로 합니다. 각 시나리오 YAML에 적힌 `run` 또는 `steps`를 따라 스크립트를 실행하세요.

- 엔드투엔드: `scripts.daily_collector` → (다이제스트 승인) → `scripts.generate_content`
- 기능 패키지: 시나리오별로 명시된 스크립트/단계 실행

자동 러너 스크립트는 추후 추가할 수 있습니다.

## 평가 및 기록

- 공통 평가지표·평가 템플릿: **`docs/001-pipeline-reliability/benchmarks.md`**
- 실행 결과·점수·이슈는 해당 문서의 평가 템플릿을 복사해 기록하거나, `docs/001-pipeline-reliability/` 아래에 실행별 노트로 남기면 됩니다.
