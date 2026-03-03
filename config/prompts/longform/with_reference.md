# Longform 콘텐츠 작성 프롬프트 (레퍼런스 기반)

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

## 📚 레퍼런스 문체 분석

{{ style_analysis }}

---

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

## ✅ 작성 규칙

1. **레퍼런스 따르기**: 위 레퍼런스의 **톤, 문장 구조, 단어 선택, 구조적 특징**을 따라하면서 새로운 글 작성
2. **문장 스타일**: 레퍼런스의 문장 길이와 리듬 유지
3. **구조**: 레퍼런스의 전개 방식을 참고하여 인트로 → 본문 → 시사점 → 마무리 구성
4. **어휘**: 레퍼런스에서 사용하는 어휘 스타일 참고
{% if boundaries and boundaries | length > 0 %}
5. **피해야 할 표현**: {{ boundaries | join(", ") }}
{% endif %}

## 🎯 이번 주 목표 (Weekly Context)
{% if weekly_cta %}- **CTA**: {{ weekly_cta }}{% endif %}
{% if weekly_outcome %}- **고객 Outcome**: {{ weekly_outcome }}{% endif %}

## 📋 품질 체크리스트
- [ ] 레퍼런스의 톤과 스타일이 자연스럽게 녹아있는가?
- [ ] 독자가 바로 행동할 수 있는 구체적인 인사이트 포함
- [ ] 각 단락이 하나의 핵심 메시지를 명확히 전달
- [ ] 클릭베이트성 표현 지양, 실질적 가치 제공

---

## 📝 출력 형식

[인트로]
(레퍼런스의 도입부 스타일을 따라 작성. 호기심 유발 또는 공감 형성)

[메인 콘텐츠]
(레퍼런스의 본문 전개 방식을 따라 작성. 3-5단락)

[주요 시사점]
(레퍼런스의 결론 스타일을 참고. 독자가 얻을 수 있는 인사이트 3-4개)

[마무리]
(레퍼런스의 결론 스타일을 따라 작성. 행동 촉구 또는 생각거리)
