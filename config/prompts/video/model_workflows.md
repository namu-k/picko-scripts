## 모델별 생성 워크플로우 레퍼런스 (문서 기반)
아래 워크플로우는 `docs/video/model_workflows.md`의 요약본이다.
선택된 서비스에 대해서만 적용하고, 서비스별 단계 순서를 지켜 샷을 구성하라.

### 공통 실행 순서
1) 목표와 훅 정의: intent에 맞는 첫 3초 훅을 먼저 확정
2) 샷 단위 분해: intro/main/cta 흐름으로 shot_type을 고정
3) 카메라/모션 지정: 서비스별 제어 필드를 반드시 채움
4) 네거티브 제약 적용: artifact, text, watermark 방지
5) 자가 QA: shot 간 비율/길이/CTA 구조를 점검

{% if "luma" in target_services %}
### Luma Workflow
- 단계 1: 장면 핵심 피사체 + 환경 + 조명/시간대를 먼저 고정
- 단계 2: `camera_motion`을 shot별로 명시하고 `motion_intensity`(1-5)를 설정
- 단계 3: 이미지 레퍼런스가 있으면 `start_image_url`/`end_image_url` 사용, 없으면 텍스트 기반으로 생성
- 단계 4: cinematic/natural 등 `style_preset`으로 톤 일관성 유지
{% endif %}

{% if "runway" in target_services %}
### Runway Workflow
- 단계 1: 주체 동작을 1문장으로 고정하고 카메라 이동 의도를 명시
- 단계 2: `camera_move` + `motion`(1-10)로 운동량을 수치화
- 단계 3: seed 재현성이 필요하면 `seed`를 지정
- 단계 4: 모델 모드가 image-to-video면 시작 이미지를 필수 입력으로 취급
- 단계 5: visual_anchor를 먼저 1문장으로 정의 (영문, 장소/조명/분위기/`9:16 vertical` 포함)
- 단계 6: 각 샷의 keyframe_image_prompt는 visual_anchor 환경을 복사하고 전경만 변경
- 단계 7: keyframe_image_prompt는 정지 이미지 전용으로 작성 (`photorealistic`, `9:16 vertical`, `no text`, `no watermark` 포함)
- 단계 8: keyframe_image_prompt에는 모션 단어(moving, walking, panning 등)와 한글 프롬프트를 사용하지 않음
{% endif %}

{% if "pika" in target_services %}
### Pika Workflow
- 단계 1: 짧고 선명한 장면 목표를 설정 (social clip 우선)
- 단계 2: 필요 시 `pikaffect`를 1개만 선택해 과도한 효과 중첩을 방지
- 단계 3: `motion_intensity`로 움직임 강도를 조절하고 `style_preset`으로 질감 통일
- 단계 4: shot 전환마다 시각적 키워드를 반복해 일관성 유지
{% endif %}

{% if "kling" in target_services %}
### Kling Workflow
- 단계 1: 샷 시작 문장에 카메라 관점(와이드/클로즈/트래킹)을 먼저 선언
- 단계 2: `camera_motion`과 `motion_intensity`(1-5)를 함께 지정
- 단계 3: `style`을 고정해 shot 간 룩 변동을 억제
- 단계 4: narrative를 길게 쓰기보다 샷당 단일 동작 중심으로 기술
{% endif %}

{% if "veo" in target_services %}
### Veo Workflow
- 단계 1: 사실적인 장면 요소와 물리적 움직임을 먼저 명시
- 단계 2: `generate_audio` 필요 여부를 샷 의도에 맞춰 결정
- 단계 3: 오디오 사용 시 `audio_mood`를 장면 감정과 동기화
- 단계 4: `style_preset`을 통일해 전체 영상 톤 일관성 유지
{% endif %}

{% if "sora" in target_services %}
### Sora Workflow
- 단계 1: 샷 목적을 명확히 쓰고 장면 내 동작 순서를 간결히 명시
- 단계 2: `style`과 `camera_motion`을 함께 지정해 시네마 문법 고정
- 단계 3: 멀티샷 구성 시 shot 간 상태 연속성을 유지하는 표현을 반복
- 단계 4: 텍스트/자막 삽입 지시는 배제하고 시각 묘사 중심으로 작성
{% endif %}

### intent별 보정 규칙
{% if intent == "ad" %}
- ad: 첫 샷에 훅, 마지막 샷에 CTA를 반드시 포함
{% elif intent == "explainer" %}
- explainer: intro-main-main-cta 구조를 유지하고 정보 전달 우선
{% elif intent == "brand" %}
- brand: 감정/무드 일관성을 우선하고 텍스트 의존도를 낮춤
{% elif intent == "trend" %}
- trend: 짧은 템포, 강한 첫 장면, 빠른 시각 전개 유지
{% endif %}
