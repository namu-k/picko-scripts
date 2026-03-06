# 013 Keyframe Image Prompt & Visual Stitching — Task Checklist

브랜치: `013-keyframe-stitching`
스펙: `specs/013-keyframe-stitching/spec.md`
설계: `specs/013-keyframe-stitching/design.md`

---

## 완료

- [x] 스펙 문서 작성 (`specs/013-keyframe-stitching/spec.md`)
- [x] 설계 문서 작성 (`specs/013-keyframe-stitching/design.md`)

## 진행 중

_없음_

## 대기

### Phase 1) 데이터 모델 확장

- [ ] `picko/video_plan.py` — `RunwayParams`에 `reference_image_url: str = ""` 추가
      - `to_dict()`에 `reference_image_url` 직렬화 추가
      - `from_dict()`에 `reference_image_url` 역직렬화 추가
- [ ] `picko/video_plan.py` — `VideoShot`에 `keyframe_image_prompt: str = ""` 추가
      - `to_dict()`에 `keyframe_image_prompt` 포함
      - `from_dict()`에서 누락 시 기본값 `""` 유지
- [ ] `picko/video_plan.py` — `VideoPlan`에 `visual_anchor: str = ""` 추가
      - `to_dict()`에 `visual_anchor` 포함
      - `from_dict()`에서 누락 시 기본값 `""` 유지
      - `to_markdown()`에 `## Visual Anchor` 섹션 출력 추가
      - `to_markdown()` 샷별 출력에 `keyframe_image_prompt` 블록쿼트 표시 추가 (design.md §3 마크다운 예시 참조)

### Phase 2) Generator 프롬프트/파싱 업데이트

- [ ] `picko/video/generator.py` — 브랜드 스타일 초기화 로직 수정
      - `_parse_response()` line 371의 `del identity` 제거 (identity를 BrandStyle 초기화에 재사용)
      - 현재 `BrandStyle(tone="")` 제거
      - `identity.tone_voice` 기반으로 tone/theme/aspect_ratio 주입
- [ ] `picko/video/generator.py` — `_build_prompt()`에 브랜드 톤 블록 추가
      - tone / forbidden / cta_style을 LLM 프롬프트에 노출
      - `visual_anchor` 생성 규칙(영문, 9:16, 모션 금지) 명시
      - `keyframe_image_prompt` 생성 규칙(앵커 복사 + 전경만 변경) 명시
- [ ] `picko/video/generator.py` — 출력 JSON 스키마 섹션 확장
      - 최상위에 `visual_anchor` 필드 추가 (schema_section 바깥, 상위 JSON 구조에 삽입)
      - 각 shot에 `keyframe_image_prompt` 필드 추가 (schema_section 바깥, shot 레벨에 삽입)
      - runway 스키마에 `reference_image_url` 필드 반영 (`_build_schema_section()` 경유)
      - 주의: `schema_section`은 services 블록만 담당하므로, `visual_anchor`와 `keyframe_image_prompt`는 `_build_prompt()` 리턴값의 JSON 템플릿에 직접 추가
- [ ] `picko/video/generator.py` — `_parse_response()` 확장
      - `plan.visual_anchor` 파싱 추가
      - `shot.keyframe_image_prompt` 파싱 추가
      - `shot.runway.reference_image_url` 파싱 추가
      - 미존재 필드 기본값 처리로 하위 호환 보장

### Phase 3) 서비스 템플릿/워크플로우 문서 업데이트

- [ ] `picko/video/prompt_templates.py` — `RUNWAY_CONFIG.optional_fields`에 `reference_image_url` 추가
- [ ] `picko/video/prompt_templates.py` — runway schema example에 `reference_image_url` 예시 추가
- [ ] `config/prompts/video/model_workflows.md` — Runway 섹션에 keyframe stitching 가이드 추가
      - `visual_anchor` 생성 규칙
      - `keyframe_image_prompt` 필수 태그 (`photorealistic`, `9:16 vertical`, `no text`, `no watermark`)
      - 금지 규칙 (모션 단어, 한글 프롬프트)

### Phase 4) 품질 게이트 확장

- [ ] `picko/video/quality_scorer.py` — `keyframe_completeness` 차원 추가 (Runway 포함 시만 활성)
      - `score()`의 `dimensions`에 조건부 포함
      - 신규 메서드 `_score_keyframe_completeness(plan, services)` 구현
      - 점검 항목 (design.md §5 스코어링 코드 기준):
        - `visual_anchor` 존재 (-30) 및 최소 길이 40자 (-10)
        - 각 shot의 `keyframe_image_prompt` 존재 (샷당 -15)
        - `9:16` 또는 `vertical` 키워드 존재 (-5)
        - 프롬프트 길이 40자 이상 (-5)
        - `visual_anchor` 핵심 키워드(상위 5개) 교차 검증 (-5)
      - 참고: `photorealistic` 태그 검증과 모션 금지어 체크는 MVP에서 제외 (향후 개선)
- [ ] `picko/video/quality_scorer.py` — 이슈/제안 메시지에 keyframe 관련 문구 추가
      - `_identify_issues()`에 keyframe 미완비 시 경고 추가
      - `_generate_suggestions()`에 stitching 가이드 제안 추가

### Phase 5) 테스트 보강 (TDD 우선)

- [ ] `tests/test_video_plan.py` — 신규 필드 직렬화/역직렬화 테스트 추가
      - `RunwayParams.reference_image_url`
      - `VideoShot.keyframe_image_prompt`
      - `VideoPlan.visual_anchor`
      - `to_markdown()`에 Visual Anchor 출력 검증
- [ ] `tests/test_video_plan.py` — 013 이전 JSON 하위 호환 테스트 추가
      - 새 필드 없는 레거시 JSON 로딩 시 기본값 보장
- [ ] `tests/test_video_generator.py` — prompt 생성 검증 테스트 추가
      - 브랜드 톤 주입 확인
      - visual_anchor/keyframe 규칙 문구 포함 확인
- [ ] `tests/test_video_generator.py` — `_parse_response()` 신규 필드 파싱 테스트 추가
      - `visual_anchor` 파싱
      - `keyframe_image_prompt` 파싱
      - `reference_image_url` 파싱
- [ ] `tests/test_prompt_templates.py` — Runway optional field/schema 검증 추가
      - `reference_image_url` 포함 여부 테스트
- [ ] `tests/test_quality_scorer.py` — keyframe completeness 스코어 테스트 추가
      - runway 포함 시 차원 활성화
      - runway 미포함 시 차원 비활성화
      - 누락/충족 케이스별 점수 차등 검증

### Phase 6) 최종 검증

- [ ] 단위 테스트 실행
      - `pytest tests/test_video_plan.py tests/test_video_generator.py tests/test_prompt_templates.py tests/test_quality_scorer.py -v`
- [ ] 영상 dry-run 시나리오 검증
      - `python -m picko video --account dawn_mood_call --intent ad --service runway --platform instagram_reel --dry-run`
      - `python -m picko video --account socialbuilders --intent brand --service runway --dry-run`
      - `python -m picko video --account dawn_mood_call --intent brand --service luma --dry-run`
- [ ] 산출물 확인 체크리스트
      - `visual_anchor` 생성됨
      - 모든 shot에 `keyframe_image_prompt` 존재
      - runway일 때 `reference_image_url` 기본값은 빈 문자열
      - runway 제외 서비스(luma 등) 동작 회귀 없음

---

## 보류 (Out of Scope 유지)

- [ ] FLUX.2 / Ideogram API 연동
- [ ] Runway API 자동 호출
- [ ] Remotion/FFmpeg 기반 최종 조립 자동화
- [ ] 신규 CLI 서브커맨드 추가

---

## 완료 기준 (Definition of Done)

- [ ] 데이터 모델 신규 필드가 JSON/Markdown roundtrip에서 보존된다.
- [ ] Generator가 브랜드 톤 + visual_anchor + keyframe_image_prompt를 안정적으로 생성한다.
- [ ] Runway 포함 플랜에서만 `keyframe_completeness` 품질 차원이 적용된다.
- [ ] 지정된 테스트와 dry-run 검증이 모두 통과한다.
