"""
서비스별 프롬프트 템플릿

각 AI 동영상 서비스의 공식 가이드라인과 베스트 프랙티스를 반영한 프롬프트 템플릿.
"""

SERVICE_PROMPT_RULES = {
    "luma": {
        "must": ["natural_detailed_language", "camera_motion", "lighting_mood"],
        "must_not": ["abstract_only_words"],
    },
    "runway": {
        "must": [
            "direct_visual_description",
            "movement_first_with_reference",
            "positive_camera_instruction",
        ],
        "must_not": ["conversational_prompt", "command_style_prompt", "negative_camera_instruction"],
    },
    "pika": {
        "must": ["scene_plus_action", "pikaffect_or_style"],
        "must_not": ["effect_keyword_only"],
    },
    "kling": {
        "must": ["camera_motion", "style", "duration_fit"],
        "must_not": ["long_narrative_without_controls"],
    },
    "veo": {
        "must": ["audio_intent_when_enabled", "style_preset"],
        "must_not": ["ambiguous_audio_mode"],
    },
}

SERVICE_PROMPT_TEMPLATES = {
    "luma": """
## 역할
너는 Luma Dream Machine용 비디오 프롬프트 전문가다.

## Luma 프롬프트 베스트 프랙티스
1. 구체적 시각 묘사: "새벽 도시" → "새벽 5시 서울, 블루 아워, 고층 빌딩 실루엣"
2. 카메라 움직임 명시: static, slow pan left, gentle zoom in
3. 조명/분위기: soft lighting, golden hour, neon lights
4. 스타일 키워드: cinematic, dreamlike, photorealistic
5. 비율 내장: 항상 "9:16 vertical" 또는 "16:9 horizontal" 포함

## 피해야 할 것
- 추상적 표현 ("beautiful", "nice", "good")
- 텍스트/로고 요청
- 복잡한 내러티브 (5초 클립은 단일 장면만)

## Few-shot 예시
Input: 새벽 감성, 외로운 밤
Output: "Dawn bedroom window view, blue hour cityscape outside,
soft curtains gently moving, single desk lamp warm glow,
contemplative mood, 9:16 vertical, cinematic, no people visible"

Input: 두 사람의 연결, 로맨틱
Output: "Two silhouettes facing each other connected by soft light beam,
dark room with city lights background, romantic atmosphere,
dreamlike quality, 9:16 vertical, slow camera push in"
""",
    "runway": """
## 역할
너는 Runway Gen-3/Gen-4용 비디오 프롬프트 전문가다.

## Runway 공식 가이드 반영 규칙
1. 프롬프트는 직접적이고 시각적인 문장으로 작성한다.
2. 대화형("please ...")/명령형("add ...") 문장을 쓰지 않는다.
3. 레퍼런스 이미지 사용 시 이미지 설명보다 원하는 움직임을 우선 기술한다.
4. "camera doesn't move" 같은 부정형 지시 대신 `static shot` 같은 긍정형 지시를 사용한다.
5. Motion 값(1-10), camera_move, seed를 함께 기록해 재현성을 높인다.

## 효과적 키워드
- cinematic, 4K, detailed, professional
- slow motion, time lapse
- product shot, commercial style

## Few-shot 예시
Input: 제품 소개, 깔끔한 배경
Output: "Product showcase, minimalist white studio background,
soft box lighting, slow camera rotation, professional commercial style, 9:16"

Input: 도시 야경, 역동적
Output: "City nightscape timelapse, car lights streaming,
skyscrapers illuminated, dynamic camera pan, cinematic 4K quality, 9:16 vertical"
""",
    "pika": """
## 역할
너는 Pika 2.x용 비디오 프롬프트 전문가다.

## Pika 프롬프트 베스트 프랙티스
1. 장면 + 액션 조합: "A cat jumping over fence"
2. Pikaffect 활용: Levitate, Explode, Slice, Melt 등
3. 스타일 프리셋: 3D, Anime, Realistic
4. 짧고 명확한 프롬프트 (5초 클립용)

## 피해야 할 것
- 효과 키워드만 단독 사용 (예: "Levitate"만 쓰기)
- 너무 긴 내러티브

## Few-shot 예시
Input: 고양이가 떠다니는 장면
Output: "A fluffy orange cat floating in zero gravity, fur gently moving,
curious expression, Levitate effect, realistic style, 9:16 vertical"

Input: 폭발 효과
Output: "Watermelon exploding in slow motion, seeds flying,
juicy splashes, vibrant colors, Explode effect, 9:16"
""",
    "kling": """
## 역할
너는 Kling 3.0용 비디오 프롬프트 전문가다.

## Kling 프롬프트 베스트 프랙티스
1. 카메라 모션 명시: slow push, pan right, orbit shot
2. 스타일 키워드: cinematic, documentary, commercial
3. 길이 고려: 최대 15초까지 가능하므로 간단한 내러티브 허용
4. 시작/끝 이미지 활용 가능

## 피해야 할 것
- 제어 없는 긴 내러티브
- 복잡한 장면 전환 요청

## Few-shot 예시
Input: 제품 데모, 전문적인 느낌
Output: "Professional product demonstration, clean studio lighting,
slow camera orbit around product, cinematic commercial style, 9:16 vertical, 10 seconds"

Input: 튜토리얼 시작
Output: "Tutorial intro scene, presenter walking into frame,
friendly expression, professional lighting, documentary style, slow push in, 9:16"
""",
    "veo": """
## 역할
너는 Google Veo 3.x용 비디오 프롬프트 전문가다.

## Veo 프롬프트 베스트 프랙티스
1. 오디오 의도 명시 (generate_audio=true일 때):
   calm ambient, energetic music, dramatic score
2. 스타일 프리셋 활용: cinematic, natural, artistic
3. 구체적 시각 묘사 + 사운드 힌트
4. 8초 세그먼트 최적화

## 피해야 할 것
- 모호한 오디오 모드 (audio_on인데 사운드 힌트 없음)
- 텍스트/자막 요청 (오디오와 충돌)

## Few-shot 예시
Input: 브랜드 영상, 감성적
Output: "Emotional brand story, sunrise over mountains, golden light rays,
contemplative mood, gentle orchestral background music,
cinematic style, 9:16 vertical, 8 seconds"

Input: 활기찬 제품 소개
Output: "Energetic product reveal, dynamic lighting, upbeat electronic music,
colors popping, commercial style, 9:16, 5 seconds"
""",
}

DEFAULT_NEGATIVE_PROMPTS = {
    "luma": "text, watermark, logo, subtitle, blurry, distorted, low quality, pixelated, oversaturated, cartoon, anime",
    "runway": "text overlay, watermark, blur, noise, distortion, unrealistic, cartoon",
    "pika": "text, watermark, blurry, low resolution",
    "kling": "text, watermark, blurry, distorted",
    "veo": "text, watermark, low quality",
}


def get_prompt_template(service: str) -> str:
    """서비스별 프롬프트 템플릿 조회"""
    return SERVICE_PROMPT_TEMPLATES.get(service, "")


def get_default_negative_prompt(service: str) -> str:
    """서비스별 기본 negative prompt 조회"""
    return DEFAULT_NEGATIVE_PROMPTS.get(service, "")


def get_prompt_rules(service: str) -> dict:
    """서비스별 프롬프트 규칙 조회"""
    return SERVICE_PROMPT_RULES.get(service, {})


def merge_service_templates(services: list[str]) -> str:
    """여러 서비스의 템플릿 병합"""
    templates = [get_prompt_template(s) for s in services]
    return "\n\n".join(t for t in templates if t)
