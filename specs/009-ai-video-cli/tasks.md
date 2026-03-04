# 009 AI Video CLI — Task Checklist

브랜치: `009-ai-video-services`
스펙: `specs/009-ai-video-cli/spec.md`
디자인: `specs/009-ai-video-cli/design.md`
구현 플랜: `specs/009-ai-video-cli/plan.md`

---

## 완료

- [x] 설계 문서 정리 (`design.md`)
- [x] `picko/video_plan.py` — VideoPlan 기본 데이터 모델
- [x] `specs/009-ai-video-cli/spec.md` — 산출물 사용성 및 품질 보증 요구사항 추가
- [x] `specs/009-ai-video-cli/design.md` — 서비스별 상세 스펙 및 품질 체계 추가
- [x] `specs/009-ai-video-cli/plan.md` — 8개 Task로 재구성 (품질 시스템 포함)
- [x] `specs/009-ai-video-cli/tasks.md` — Task 체크리스트 업데이트

---

## 진행 중

_없음_

---

## 대기 (우선순위 순)

### Phase 1: 기반 구축

- [ ] **Task 1: video_plan.py 확장** — 서비스별 파라미터(LumaParams 등), AudioSpec, TextOverlay, 품질 필드 추가
  - `picko/video_plan.py` 수정
  - `tests/test_video_plan.py` 생성

- [ ] **Task 2: constraints.py** — 서비스/플랫폼 제약 정의
  - `picko/video/constraints.py` 생성
  - `tests/test_constraints.py` 생성

- [ ] **Task 3: validator.py** — 제약 검증 로직
  - `picko/video/validator.py` 생성
  - `tests/test_validator.py` 생성

### Phase 2: 품질 시스템

- [ ] **Task 4: prompt_templates.py** — 서비스별 프롬프트 템플릿 (Few-shot 포함)
  - `picko/video/prompt_templates.py` 생성
  - `tests/test_prompt_templates.py` 생성

- [ ] **Task 5: quality_scorer.py** — 5차원 품질 평가
  - `picko/video/quality_scorer.py` 생성
  - `tests/test_quality_scorer.py` 생성

- [ ] **Task 6: generator.py** — 핵심 로직 + 품질 게이트
  - `picko/video/generator.py` 생성
  - `tests/test_video_generator.py` 생성

### Phase 3: CLI

- [ ] **Task 7: __main__.py** — CLI 디스패처
  - `picko/__main__.py` 생성
  - `pyproject.toml` 수정 (엔트리포인트)
  - `tests/test_main.py` 생성

- [ ] **Task 8: __init__.py** — 패키지 마커
  - `picko/video/__init__.py` 생성

---

## 검증 기준

### 단위 테스트
```bash
pytest tests/test_video_plan.py tests/test_constraints.py tests/test_validator.py \
       tests/test_prompt_templates.py tests/test_quality_scorer.py \
       tests/test_video_generator.py tests/test_main.py -v
```

### E2E 테스트
```bash
# 1. ad + account-only (기본)
python -m picko video --dry-run

# 2. explainer + longform
python -m picko video --intent explainer --content lf_001 --service runway --dry-run

# 3. ad + weekly context
python -m picko video --intent ad --week-of 2026-03-03 --service pika --dry-run
# 4. 검증 없이
python -m picko video --no-validate --dry-run
```

### 완료 기준
- [ ] 모든 단위 테스트 통과
- [ ] 4가지 E2E 시나리오 에러 없이 실행
- [ ] 생성된 VideoPlan의 `quality_score` ≥ 70
- [ ] 각 샷에 서비스별 파라미터(`luma`, `runway` 등) 완전히 채워짐
- [ ] Negative prompt 자동 생성 확인
- [ ] LLM 파싱 예외 처리 확인 (```json 블록 처리)
- [ ] 복수 서비스 지정 시 모든 서비스 파라미터 생성 확인
- [ ] 품질 게이트 재시도 로직 확인

---

## 보류 (다음 브랜치로)

- [ ] 계정 설정 video_settings 스키마 (`config/accounts/*.yml`)
- [ ] 서비스별 어댑터 실제 API 연동 (`export_video_luma.py` 등)
- [ ] 배치 생성 (`--batch` 옵션)
- [ ] 피드백 루프 (생성된 영상 기반 개선)
- [ ] `picko image` 서브커맨드
- [ ] `picko copy` 서브커맨드

---

## 파일 요약

| 파일 | 상태 | Task |
|------|------|------|
| `picko/video_plan.py` | ⚠️ 확장필요 | Task 1 |
| `picko/video/constraints.py` | 🔲 미구현 | Task 2 |
| `picko/video/validator.py` | 🔲 미구현 | Task 3 |
| `picko/video/prompt_templates.py` | 🔲 미구현 | Task 4 |
| `picko/video/quality_scorer.py` | 🔲 미구현 | Task 5 |
| `picko/video/generator.py` | 🔲 미구현 | Task 6 |
| `picko/__main__.py` | 🔲 미구현 | Task 7 |
| `picko/video/__init__.py` | 🔲 미구현 | Task 8 |
| `pyproject.toml` | 🔲 수정필요 | Task 7 |
| `tests/test_video_plan.py` | 🔲 미구현 | Task 1 |
| `tests/test_constraints.py` | 🔲 미구현 | Task 2 |
| `tests/test_validator.py` | 🔲 미구현 | Task 3 |
| `tests/test_prompt_templates.py` | 🔲 미구현 | Task 4 |
| `tests/test_quality_scorer.py` | 🔲 미구현 | Task 5 |
| `tests/test_video_generator.py` | 🔲 미구현 | Task 6 |
| `tests/test_main.py` | 🔲 미구현 | Task 7 |
