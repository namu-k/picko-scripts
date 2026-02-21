# Longform 프롬프트 (탐색 컨텍스트 포함)

다음 콘텐츠와 탐색 결과를 바탕으로 블로그 포스트 형식의 긴 글을 작성해주세요.

**제목**: {{ title }}

**원본 요약**:
{{ summary }}

**핵심 포인트**:
{% for point in key_points %}
- {{ point }}
{% endfor %}

**원문 발췌**:
{{ excerpt }}

---

## 📋 주제 탐색 결과

**주제 확장**:
{{ exploration.topic_expansion }}

**관련 논의와 반론**:
{{ exploration.related_discussions }}

**독자 인사이트**:
{{ exploration.reader_insights }}

**롱폼 작성 가이드**:
{{ exploration.writing_guide }}

---

{% set outcome = customer_outcome | default('') %}
{% set cta_text = cta | default('') %}
{% if outcome or cta_text %}
주간 목표 컨텍스트(있을 때만 반영):
{% if outcome %}
- 고객 성과 목표: {{ outcome }}
{% endif %}
{% if cta_text %}
- 마무리 CTA: {{ cta_text }}
{% endif %}

{% endif %}

작성 규칙:
- 출력은 아래 4개의 대괄호 섹션만 사용하세요.
- `[인트로]`, `[메인 콘텐츠]`, `[주요 시사점]`, `[마무리]` 외의 마크다운 제목(`#`, `##` 등)이나 추가 섹션을 만들지 마세요.
- 탐색 결과를 활용하되, 주장/해석은 반드시 제목·요약·핵심 포인트·탐색 텍스트에 근거하세요.

위 탐색 결과를 참고하여 다음 형식으로 작성해주세요:

[인트로]
- 2-3문장
- 제목/요약에 기반한 사실형 호기심 훅으로 시작
- 탐색 결과의 흥미로운 각도를 활용하고, 필요하면 반직관적(contrarian) 관점을 근거와 함께 제시

[메인 콘텐츠]
- 핵심 내용을 자세히 설명 (3-5 단락)
- 구체적인 예시나 통계 포함
- 관련 논의나 반론도 언급
{% if outcome %}
- 고객 성과 목표(`{{ outcome }}`)가 있으면 본문 전개를 그 목표 달성과 연결
{% endif %}

[주요 시사점]
- 독자가 얻을 수 있는 인사이트 (3-4개)
- 탐색 결과의 독자 인사이트 활용
- 실행 가능한 문장으로 작성

[마무리]
- 핵심 메시지를 한 문장으로 정리
{% if cta_text %}
- `{{ cta_text }}` CTA로 마무리
{% else %}
- 자연스러운 다음 행동 제안으로 마무리
{% endif %}
