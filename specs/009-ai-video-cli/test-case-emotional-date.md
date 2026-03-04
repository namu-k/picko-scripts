# 감성통화데이트 앱 - 릴스 광고 테스트 케이스

## 개요

Picko의 VideoPlan 포맷을 검증하기 위한 첫 테스트 케이스.

**앱 개요**: 새벽 2시에 감성적인 시간에 이성과 통화를 하다가 맞는거같으면 대화를 이어나가는 서비스

## 목표

15-30초 감성/몽환적 릴스로 앱 다운로드 유도

## 타겟 플랫폼

- **1순위**: 인스타그램 릴스 (9:16)
- **재사용 가능**: 유튜브 숏츠, 틱톡 (동일 9:16 포맷)

## 핵심 메시지

1. 외로운 새벽, 누군가와 대화하고 싶은 순간
2. 그 연결이 운명적인 만남으로 이어진다

## 톤앤매너

- **분위기**: 감성/몽환적
- **시각**: 새벽 느낌, 부드러운 조명, 블루 아워
- **오디오**: 잔잔한 배경음악 (calm, ambient)

## CLI 명령어

```bash
python -m picko video \
  --account emotional-date \
  --intent ad \
  --service luma \
  --platform instagram_reel \
  --dry-run
```

## 서비스별 프롬프트 전략 메모 (공식 가이드 반영)

- **Luma**: 자연어 기반 장면 묘사 + 조명/무드/카메라 모션을 함께 명시
- **Runway**: 대화형/명령형 문장 대신 직접적 시각 묘사, 레퍼런스 이미지 사용 시 움직임 중심 서술
- **Pika**: 장면 맥락 + `pikaffect`/스타일을 함께 지정
- **Kling**: 카메라 모션/스타일/길이 제약을 함께 고정
- **Veo**: 오디오 생성 여부(`generate_audio`)와 오디오 무드(`audio_mood`)를 함께 설계

## 예상 VideoPlan JSON

```json
{
  "id": "video_emotional-date_20260305_001",
  "account": "emotional-date",
  "intent": "ad",
  "lang": "ko",
  "goal": "앱 다운로드 유도",
  "source": {
    "type": "account_only",
    "id": "",
    "summary": ""
  },
  "brand_style": {
    "tone": "감성/몽환적",
    "aspect_ratio": "9:16"
  },
  "target_services": ["luma"],
  "platforms": ["instagram_reel"],
  "duration_sec": 15,
  "quality_score": 85,
  "quality_issues": [],
  "quality_suggestions": [],
  "quality_warning": false,
  "shots": [
    {
      "index": 1,
      "duration_sec": 5,
      "shot_type": "intro",
      "script": "새벽 감성 배경 - 고요한 방, 창밖 블루 아워 도시",
      "caption": "새벽 2시, 잠이 오지 않는 밤",
      "luma": {
        "prompt": "Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving, single desk lamp warm glow, contemplative mood, 9:16 vertical format, cinematic lighting, no people visible",
        "negative_prompt": "text, watermark, people, bright colors, fast motion, cartoon",
        "aspect_ratio": "9:16",
        "duration_sec": 5,
        "camera_motion": "static",
        "motion_intensity": 2,
        "style_preset": "cinematic"
      },
      "audio": {
        "mood": "calm",
        "genre": "ambient",
        "bpm": 60,
        "voiceover_text": "",
        "sfx": []
      },
      "text_overlays": [
        {
          "text": "새벽 2시, 잠이 오지 않는 밤",
          "position": "bottom",
          "font_size": "medium",
          "font_color": "#FFFFFF",
          "background": "semi-transparent",
          "animation": "fade_in",
          "start_sec": 1.0,
          "end_sec": 4.5
        }
      ],
      "transition_in": "",
      "transition_out": "dissolve"
    },
    {
      "index": 2,
      "duration_sec": 5,
      "shot_type": "main",
      "script": "두 사람의 연결감 - 부드러운 빛, 연결된 실루엣",
      "caption": "누군가와 대화하고 싶을 때",
      "luma": {
        "prompt": "Two silhouettes facing each other connected by soft light beam, dark room with city lights background, romantic atmosphere, dreamlike quality, 9:16 vertical, slow camera push in, cinematic",
        "negative_prompt": "text, watermark, faces visible, bright colors",
        "aspect_ratio": "9:16",
        "duration_sec": 5,
        "camera_motion": "zoom_in",
        "motion_intensity": 2,
        "style_preset": "cinematic"
      },
      "audio": {
        "mood": "romantic",
        "genre": "ambient",
        "bpm": 70,
        "voiceover_text": "",
        "sfx": []
      },
      "text_overlays": [
        {
          "text": "누군가와 대화하고 싶을 때",
          "position": "center",
          "font_size": "medium",
          "font_color": "#FFFFFF",
          "background": "semi-transparent",
          "animation": "fade_in",
          "start_sec": 0.5,
          "end_sec": 4.5
        }
      ],
      "transition_in": "dissolve",
      "transition_out": "dissolve"
    },
    {
      "index": 3,
      "duration_sec": 5,
      "shot_type": "cta",
      "script": "앱 로고 노출 - 깔끔한 배경, 로고 공간 확보",
      "caption": "감성통화데이트\n지금 다운로드",
      "luma": {
        "prompt": "Clean minimalist background, soft gradient from dark blue to purple, empty center space for logo placement, subtle light particles floating, 9:16 vertical, cinematic, professional",
        "negative_prompt": "text, watermark, people, cluttered, busy",
        "aspect_ratio": "9:16",
        "duration_sec": 5,
        "camera_motion": "static",
        "motion_intensity": 1,
        "style_preset": "minimal"
      },
      "audio": {
        "mood": "hopeful",
        "genre": "ambient",
        "bpm": 80,
        "voiceover_text": "감성통화데이트, 지금 시작하세요",
        "voiceover_gender": "female",
        "voiceover_tone": "warm",
        "sfx": ["chime"]
      },
      "text_overlays": [
        {
          "text": "감성통화데이트",
          "position": "center",
          "font_size": "large",
          "font_color": "#FFFFFF",
          "background": "none",
          "animation": "fade_in",
          "start_sec": 0.5,
          "end_sec": 4.0
        },
        {
          "text": "지금 다운로드",
          "position": "bottom",
          "font_size": "medium",
          "font_color": "#FFFFFF",
          "background": "semi-transparent",
          "animation": "pulse",
          "start_sec": 1.5,
          "end_sec": 4.5
        }
      ],
      "transition_in": "dissolve",
      "transition_out": ""
    }
  ]
}
```

## 예상 마크다운 출력

```markdown
# 영상 기획서: video_emotional-date_20260305_001

**계정**: emotional-date | **목적**: ad | **길이**: 15초 | **품질점수**: 85

## 목표
앱 다운로드 유도

## 샷 구성

### 샷 1: intro (5초)
**장면**: 새벽 감성 배경 - 고요한 방, 창밖 블루 아워 도시
**자막**: 새벽 2시, 잠이 오지 않는 밤

**Luma 프롬프트** (복사해서 사용):
```
Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving, single desk lamp warm glow, contemplative mood, 9:16 vertical format, cinematic lighting, no people visible
```

**Negative Prompt**:
```
text, watermark, people, bright colors, fast motion, cartoon
```

**오디오**: calm / ambient / 60 BPM
**전환**: → dissolve

---

### 샷 2: main (5초)
**장면**: 두 사람의 연결감 - 부드러운 빛, 연결된 실루엣
**자막**: 누군가와 대화하고 싶을 때

**Luma 프롬프트** (복사해서 사용):
```
Two silhouettes facing each other connected by soft light beam, dark room with city lights background, romantic atmosphere, dreamlike quality, 9:16 vertical, slow camera push in, cinematic
```

**오디오**: romantic / ambient / 70 BPM
**전환**: dissolve → dissolve

---

### 샷 3: cta (5초)
**장면**: 앱 로고 노출 - 깔끔한 배경, 로고 공간 확보
**자막**: 감성통화데이트 / 지금 다운로드

**Luma 프롬프트** (복사해서 사용):
```
Clean minimalist background, soft gradient from dark blue to purple, empty center space for logo placement, subtle light particles floating, 9:16 vertical, cinematic, professional
```

**오디오**: hopeful / ambient / 80 BPM
**내레이션**: "감성통화데이트, 지금 시작하세요" (female, warm)

---

## 품질 정보
- **점수**: 85/100
- **제안**: 없음
```

## 검증 기준

- [ ] `quality_score` ≥ 70
- [ ] CTA 샷 존재 (`shot_type: cta`)
- [ ] 각 샷에 `luma` 파라미터 완전히 채워짐
- [ ] 총 길이 15-30초 범위
- [ ] 모든 샷 `aspect_ratio: 9:16`
- [ ] 텍스트 오버레이 타이밍이 샷 길이 내에 있음
- [ ] 오디오 사양이 각 샷에 포함됨

## 다음 단계

1. VideoPlan 검증 완료
2. 실제 Luma에서 각 샷 생성
3. 편집 소프트웨어에서 조합
4. 성과 측정 후 템플릿 개선
