# Newsletter 이미지 프롬프트

다음 콘텐츠에 어울리는 뉴스레터용 히어로 이미지를 생성해주세요.

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
이메일 뉴스레터 상단 히어로 이미지.
헤드라인 텍스트 오버레이를 위한 충분한 여백.
일관된 브랜딩 요소 포함.

[스타일]
에디토리얼 스타일의 세련된 디자인.
잡지 커버처럼 눈길을 끄는 구성.

[분위기]
전문적이고 신뢰감 있는 분위기.

[색상]
브랜드 아이덴티티에 맞는 일관된 색상.
