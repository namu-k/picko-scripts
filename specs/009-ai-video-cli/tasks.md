# 009 AI Video CLI — Task Checklist

브랜치: `009-ai-video-services`
스펙: `specs/009-ai-video-cli/spec.md`
구현 플랜: `specs/009-ai-video-cli/plan.md`

---

## 완료

- [x] 설계 문서 정리 (`specs/009-ai-video-cli/design.md` — 3.2, 3.3 삭제 및 3.1 통합)
- [x] `picko/video_plan.py` — VideoPlan 데이터 모델 (intent 필드 포함 완료)

## 진행 중

_없음_

## 대기

- [ ] `picko/video/__init__.py` — 패키지 마커 (Plan Task 2)
- [ ] `tests/test_video_generator.py` — 3축 generator 테스트 TDD (Plan Task 3)
      - account-only + ad (기본)
      - intent=explainer 프롬프트 변화
      - week-of WeeklySlot CTA 주입
- [ ] `picko/video/generator.py` — 3축 지원 생성 로직 (Plan Task 4)
      - `_INTENT_CONFIGS`: intent별 샷 수·길이·톤 가이드
      - `get_weekly_slot()` 연결
- [ ] content-based 테스트 + 구현 (Plan Task 5)
      - Vault longform 로드
      - 없으면 account-only 폴백
- [ ] `picko/__main__.py` + `pyproject.toml` — CLI 디스패처 (Plan Task 6)
      - `--intent`, `--week-of`, `--content` 인자 전달
- [ ] `specs/009-ai-video-cli/design.md` 섹션 4 업데이트 (Plan Task 7)

## 보류 (다음 브랜치로)

- [ ] 계정 설정 video_settings 스키마 (`config/accounts/*.yml`)
- [ ] 서비스별 어댑터 (`export_video_luma.py` 등) — 실제 API 연동
- [ ] `picko image` 서브커맨드
- [ ] `picko copy` 서브커맨드

---

## 검증 기준

```bash
# 전체 테스트
pytest tests/test_video_plan.py tests/test_video_generator.py tests/test_main.py -v

# E2E — 4가지 축 조합
python -m picko video --dry-run                                                          # ad + account-only
python -m picko video --intent explainer --content lf_2026-03-01_001 --service runway --dry-run  # explainer + longform
python -m picko video --intent ad --week-of 2026-03-03 --service pika --dry-run          # ad + weekly
python -m picko video --intent brand --service luma --dry-run                            # brand
```

모든 테스트 통과 + 4가지 E2E 조합 에러 없이 실행되면 009 브랜치 완료.
