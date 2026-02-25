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

위 탐색 결과를 참고하여 다음 형식으로 작성해주세요:

[인트로]
- 독자의 관심을 끄는 도입부 (2-3문장)
- 탐색 결과에서 발견한 흥미로운 각도 활용

[메인 콘텐츠]
- 핵심 내용을 자세히 설명 (3-5 단락)
- 구체적인 예시나 통계 포함
- 관련 논의나 반론도 언급

[주요 시사점]
- 독자가 얻을 수 있는 인사이트 (3-4개)
- 탐색 결과의 독자 인사이트 활용

[마무리]
- 행동 촉구 또는 생각거리
