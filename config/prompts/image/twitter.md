# Twitter 이미지 프롬프트

다음 콘텐츠에 어울리는 Twitter용 카드 이미지를 생성해주세요.

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
Twitter 카드에 최적화된 이미지 설명.
텍스트 오버레이가 가능하도록 여백 확보.
스크롤을 멈추게 하는 시각적 요소 포함.

[스타일]
미니멀하고 깔끔한 디자인.
브랜드 컬러 활용.

[분위기]
전문적이면서도 친근한 느낌.

[색상]
주요 색상 팔레트 (최대 3-4색).
