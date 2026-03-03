# Longform 콘텐츠 작성 프롬프트 (탐색 컨텍스트 포함)

## 🎭 작성자 페르소나
{% if tone_voice %}{{ tone_voice.get("tone", "전문적이면서도 친근한") }}{% else %}전문적이면서도 친근한 톤{% endif %}

## 👥 타겟 독자
{% if target_audience and target_audience | length > 0 %}
{% for audience in target_audience %}
- {{ audience }}
{% endfor %}
{% else %}
- 해당 분야에 관심 있는 일반 독자
{% endif %}

## 📝 작성할 주제

**제목**: {{ title }}

**요약**:
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

## ✅ 작성 규칙

1. **문장 스타일**: 30자 이내의 짧은 문장 선호, 읽기 쉬운 구성
2. **구조**: 인트로(2-3문장) → 본문(3-5단락) → 시사점(3-4개) → 마무리
3. **어휘**: 전문 용어는 풀어서 설명, 구체적인 예시 활용
4. **가독성**: 각 단락은 하나의 핵심 메시지에 집중
5. **탐색 활용**: 위 탐색 결과에서 발견한 흥미로운 각도와 독자 인사이트 적극 활용
{% if boundaries and boundaries | length > 0 %}
6. **피해야 할 표현**: {{ boundaries | join(", ") }}
{% endif %}

## 🎯 이번 주 목표 (Weekly Context)
{% if weekly_cta %}- **CTA**: {{ weekly_cta }}{% endif %}
{% if weekly_outcome %}- **고객 Outcome**: {{ weekly_outcome }}{% endif %}

## 📋 품질 체크리스트
- [ ] 독자가 바로 행동할 수 있는 구체적인 인사이트 포함
- [ ] 복잡한 개념을 비유나 예시로 쉽게 설명
- [ ] 각 단락이 하나의 핵심 메시지를 명확히 전달
- [ ] 탐색 결과의 관련 논의나 반론도 언급
- [ ] 클릭베이트성 표현 지양, 실질적 가치 제공

---

## 📝 출력 형식

[인트로]
(2-3문장으로 독자의 관심을 끄는 도입부. 탐색 결과에서 발견한 흥미로운 각도 활용)

[메인 콘텐츠]
(3-5단락, 각 단락은 하나의 핵심 메시지. 구체적인 예시나 통계 포함. 관련 논의나 반론도 언급)

[주요 시사점]
- (독자가 얻을 수 있는 실질적 인사이트 3-4개. 탐색 결과의 독자 인사이트 활용)

[마무리]
(행동 촉구 또는 생각거리. 독자가 다음 단계를 취할 수 있도록 안내)
