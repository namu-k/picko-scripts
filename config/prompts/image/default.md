# 이미지 프롬프트 생성기

## 📥 콘텐츠 정보
- **제목**: {{ title }}
- **요약**: {{ summary }}
- **태그**: {{ tags | join(", ") }}

## ✅ 작성 규칙

1. **목적**: 콘텐츠의 핵심 메시지를 시각화
2. **스타일**: 미니멀, 깔끔, 텍스트 가독성 우선
3. **플랫폼**: SNS 공유 최적화 (16:9 비율)
4. **일관성**: 브랜드 톤과 맞는 색상 및 분위기

## 📋 품질 체크리스트
- [ ] 콘텐츠 핵심 메시지가 시각적으로 표현되는가?
- [ ] 텍스트 오버레이가 필요한 경우 가독성이 확보되는가?
- [ ] SNS 공유에 적합한 비율과 구성인가?

## 💡 예시 (Few-Shot)

**입력**: AI 스타트업 투자 유치
**출력**:
[메인 프롬프트]
A minimalist infographic showing startup growth metrics, with ascending bar charts and a rocket icon, clean white background with subtle gradient blue accents, professional business presentation style, flat design, no text

[스타일]
minimalist, corporate, data-visualization, flat-design

[분위기]
optimistic, professional, achievement-focused

[색상]
white background, navy blue primary, accent gold

---

**입력**: PMF 찾기 전략
**출력**:
[메인 프롬프트]
A clean diagram showing product-market fit concept, with puzzle pieces connecting perfectly, simple geometric shapes, modern tech aesthetic, soft shadows, professional illustration style

[스타일]
minimalist, isometric, infographic

[분위기]
analytical, strategic, clear

[색상]
white background, teal primary, coral accent

---

## 📝 출력 형식

[메인 프롬프트]
(DALL-E/Midjourney용 상세 이미지 설명, 영어로 작성. 텍스트 없이 시각적 요소만 묘사)

[스타일]
(아트 스타일: minimalist, isometric, photorealistic, flat-design 등)

[분위기]
(이미지의 전반적인 느낌: optimistic, professional, analytical 등)

[색상]
(주요 색상 팔레트: background, primary, accent)
