# LinkedIn 이미지 프롬프트

다음 콘텐츠에 어울리는 LinkedIn용 이미지를 생성해주세요.

**제목**: {{ title }}
**요약**: {{ summary }}
**태그**: {{ tags | join(", ") }}

**이미지 스펙**:
- 비율: {{ image_specs.aspect_ratio }}
- 스타일: {{ image_specs.style }}
- 권장 크기: {{ image_specs.recommended_size }}

**레이아웃 힌트**:
{% for hint in image_specs.layout_hints %}
- {{ hint }}
{% endfor %}

---

다음 형식으로 작성해주세요:

[메인 프롬프트]
LinkedIn 피드에 최적화된 정사각형 이미지.
데이터 시각화나 인포그래픽 요소 활용 가능.
프로페셔널한 비즈니스 컨텍스트 고려.

[스타일]
깔끔하고 전문적인 디자인.
기업적이지만 딱딱하지 않은 느낌.

[분위기]
신뢰감 있고 전문적인 분위기.

[색상]
차분하고 세련된 비즈니스 컬러.
