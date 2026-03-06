"""
서비스별 프롬프트 템플릿

각 AI 동영상 서비스의 공식 가이드라인과 실제 베스트 프랙티스를 기반으로
서비스별 최적화된 프롬프트 생성을 위한 템플릿 시스템.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ServicePromptConfig:
    """서비스별 프롬프트 설정"""

    name: str
    prompt_pattern: str  # 프롬프트 작성 패턴
    required_fields: list[str]  # JSON에서 필수인 필드
    optional_fields: list[str]  # 선택적 필드
    field_examples: dict[str, str]  # 각 필드의 예시값
    few_shots: list[dict[str, Any]]  # Few-shot 예시 (input, output)
    must_keywords: list[str]  # 프롬프트에 포함되어야 하는 키워드 유형
    must_not_patterns: list[str]  # 프롬프트에 포함되면 안 되는 패턴
    negative_prompt_default: str  # 기본 negative prompt


# =============================================================================
# LUMA DREAM MACHINE
# =============================================================================
LUMA_CONFIG = ServicePromptConfig(
    name="Luma Dream Machine",
    prompt_pattern="[Scene with specific details], [Lighting/Time], [Camera Motion], [Mood/Style], [Aspect Ratio]",
    required_fields=["prompt", "negative_prompt"],
    optional_fields=[
        "camera_motion",
        "motion_intensity",
        "style_preset",
        "start_image_url",
        "end_image_url",
        "loop",
    ],
    field_examples={
        "prompt": "Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving, single desk lamp warm glow",
        "negative_prompt": "text, watermark, logo, subtitle, blurry, distorted, low quality, oversaturated",
        "camera_motion": "slow_pan_left",
        "motion_intensity": "3",
        "style_preset": "cinematic",
        "loop": "false",
    },
    few_shots=[
        {
            "input": "새벽 감성, 외로운 밤",
            "output": {
                "prompt": "Dawn bedroom window view, blue hour cityscape outside, soft curtains gently moving, single desk lamp warm glow, contemplative mood, 9:16 vertical, cinematic, no people visible",
                "negative_prompt": "text, watermark, logo, subtitle, blurry, distorted",
                "camera_motion": "slow_push_in",
                "motion_intensity": "2",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "두 사람의 연결, 로맨틱",
            "output": {
                "prompt": "Two silhouettes facing each other connected by soft light beam, dark room with city lights background, romantic atmosphere, dreamlike quality, 9:16 vertical, slow camera push in",
                "negative_prompt": "text, faces visible, watermark",
                "camera_motion": "slow_push_in",
                "motion_intensity": "2",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "제품 소개, 깔끔한 배경",
            "output": {
                "prompt": "Minimalist white studio background, soft box lighting from above, clean product display, professional commercial style, 9:16 vertical, static shot",
                "negative_prompt": "text, watermark, cluttered background, shadows",
                "camera_motion": "static",
                "motion_intensity": "1",
                "style_preset": "minimal",
            },
        },
        {
            "input": "도시 야경, 역동적",
            "output": {
                "prompt": "City nightscape timelapse, car lights streaming through streets, skyscrapers illuminated, neon reflections on wet pavement, dynamic energy, 9:16 vertical, slow pan right",
                "negative_prompt": "text, watermark, daytime, people visible",
                "camera_motion": "slow_pan_right",
                "motion_intensity": "4",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "자연 속 평화, 명상",
            "output": {
                "prompt": "Misty forest at dawn, sun rays filtering through tall trees, gentle fog rolling, birds flying in distance, peaceful meditation mood, 9:16 vertical, slow tilt up",
                "negative_prompt": "text, watermark, people, buildings",
                "camera_motion": "slow_tilt_up",
                "motion_intensity": "2",
                "style_preset": "natural",
            },
        },
        {
            "input": "커피 한 잔, 아침",
            "output": {
                "prompt": "Morning coffee cup on wooden table, steam rising gently, soft window light, cozy cafe atmosphere, warm tones, 9:16 vertical, static close-up shot",
                "negative_prompt": "text, watermark, people, clutter",
                "camera_motion": "static",
                "motion_intensity": "1",
                "style_preset": "natural",
            },
        },
        {
            "input": "운동, 에너지",
            "output": {
                "prompt": "Gym interior, dynamic lighting, equipment in background, energetic atmosphere, motivational mood, 9:16 vertical, subtle zoom in",
                "negative_prompt": "text, watermark, people faces, crowded",
                "camera_motion": "slow_zoom_in",
                "motion_intensity": "3",
                "style_preset": "natural",
            },
        },
        {
            "input": "책 읽는 공간, 집중",
            "output": {
                "prompt": "Cozy reading nook by window, afternoon golden light, open book on cushion, plants nearby, peaceful study mood, 9:16 vertical, static shot",
                "negative_prompt": "text on pages visible, watermark, people",
                "camera_motion": "static",
                "motion_intensity": "1",
                "style_preset": "natural",
            },
        },
        {
            "input": "비 오는 날, 감성",
            "output": {
                "prompt": "Rain drops on window pane, blurred city lights outside, cozy interior reflection, melancholic mood, blue tones, 9:16 vertical, static shot with rain motion",
                "negative_prompt": "text, watermark, people visible, sunny",
                "camera_motion": "static",
                "motion_intensity": "2",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "여행, 모험",
            "output": {
                "prompt": "Mountain peak at sunrise, golden hour light on snow, clouds below, adventurous spirit, epic scale, 9:16 vertical, slow drone push forward",
                "negative_prompt": "text, watermark, people, buildings",
                "camera_motion": "slow_push_in",
                "motion_intensity": "3",
                "style_preset": "cinematic",
            },
        },
    ],
    must_keywords=["camera", "lighting", "mood", "9:16"],
    must_not_patterns=["please", "create", "make", "show me", "can you"],
    negative_prompt_default="text, watermark, logo, subtitle, blurry, distorted, low quality, pixelated, oversaturated, cartoon, anime",
)


# =============================================================================
# RUNWAY GEN-3/GEN-4
# =============================================================================
RUNWAY_CONFIG = ServicePromptConfig(
    name="Runway Gen-3/Gen-4",
    prompt_pattern="[Subject + Action in detail], [Camera Movement], [Style/Quality], [Aspect Ratio]",
    required_fields=["prompt", "negative_prompt", "motion", "camera_move"],
    optional_fields=["seed", "upscale", "reference_image_url"],
    field_examples={
        "prompt": "Product rotating slowly on white pedestal, professional studio lighting, commercial style",
        "negative_prompt": "text overlay, watermark, blur, noise",
        "motion": "5",
        "camera_move": "orbit",
        "seed": "0",
        "upscale": "false",
        "reference_image_url": "https://example.com/keyframe-shot1.png",
    },
    few_shots=[
        {
            "input": "제품 소개, 회전",
            "output": {
                "prompt": "Sleek smartphone rotating 360 degrees on minimalist white pedestal, soft rim lighting, professional product photography, commercial style, 9:16 vertical",
                "negative_prompt": "text, watermark, hands, reflection, blur",
                "motion": "6",
                "camera_move": "orbit",
            },
        },
        {
            "input": "도시 야경 타임랩스",
            "output": {
                "prompt": "Urban nightscape timelapse, car light trails on highway, skyscrapers glowing, dynamic city energy, cinematic 4K quality, 9:16 vertical",
                "negative_prompt": "text, watermark, daytime, static",
                "motion": "8",
                "camera_move": "static",
            },
        },
        {
            "input": "자연 다큐멘터리",
            "output": {
                "prompt": "Ocean waves crashing on rocky shore, golden hour light, spray mist, nature documentary style, 9:16 vertical",
                "negative_prompt": "text, watermark, people, buildings",
                "motion": "7",
                "camera_move": "static",
            },
        },
        {
            "input": "인테리어 소개",
            "output": {
                "prompt": "Modern living room interior, slow camera pan across furniture, natural window light, architectural photography style, 9:16 vertical",
                "negative_prompt": "text, watermark, people, clutter",
                "motion": "4",
                "camera_move": "pan_left",
            },
        },
        {
            "input": "음식 촬영",
            "output": {
                "prompt": "Gourmet dish on elegant plate, steam rising, soft overhead lighting, food photography style, shallow depth of field, 9:16 vertical",
                "negative_prompt": "text, watermark, hands, utensils, messy",
                "motion": "3",
                "camera_move": "static",
            },
        },
        {
            "input": "패션 룩북",
            "output": {
                "prompt": "Fashion clothing on hanger, subtle fabric movement, studio backlighting, editorial style, 9:16 vertical",
                "negative_prompt": "text, watermark, people, face, background noise",
                "motion": "4",
                "camera_move": "static",
            },
        },
        {
            "input": "기술 데모",
            "output": {
                "prompt": "Laptop screen displaying app interface, subtle reflection, clean desk background, tech product demo style, 9:16 vertical",
                "negative_prompt": "text readable, watermark, hands, clutter",
                "motion": "3",
                "camera_move": "zoom_in",
            },
        },
        {
            "input": "워크아웃 모티베이션",
            "output": {
                "prompt": "Dumbbells on gym floor, dramatic side lighting, motivational atmosphere, fitness content style, 9:16 vertical",
                "negative_prompt": "text, watermark, people, sweat",
                "motion": "5",
                "camera_move": "tilt_up",
            },
        },
        {
            "input": "북크리에이터 콘텐츠",
            "output": {
                "prompt": "Aesthetic desk setup, morning light through window, plants and stationery, productivity vibe, 9:16 vertical",
                "negative_prompt": "text, watermark, people, messy",
                "motion": "3",
                "camera_move": "pan_right",
            },
        },
        {
            "input": "브랜드 스토리",
            "output": {
                "prompt": "Abstract light particles floating in dark space, cinematic reveal, brand story atmosphere, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, people",
                "motion": "6",
                "camera_move": "push_in",
            },
        },
    ],
    must_keywords=["camera", "lighting", "style"],
    must_not_patterns=[
        "please",
        "create",
        "make",
        "show me",
        "can you",
        "add a",
        "I want",
    ],
    negative_prompt_default="text overlay, watermark, blur, noise, distortion, unrealistic, cartoon",
)


# =============================================================================
# PIKA 2.x
# =============================================================================
PIKA_CONFIG = ServicePromptConfig(
    name="Pika 2.x",
    prompt_pattern="[Subject + Action], [Pikaffect if applicable], [Style Preset], [Aspect Ratio]",
    required_fields=["prompt", "negative_prompt"],
    optional_fields=["pikaffect", "style_preset", "motion_intensity"],
    field_examples={
        "prompt": "A fluffy orange cat floating in zero gravity, curious expression",
        "negative_prompt": "text, watermark, blurry",
        "pikaffect": "Levitate",
        "style_preset": "Realistic",
        "motion_intensity": "3",
    },
    few_shots=[
        {
            "input": "고양이가 떠다니는 장면",
            "output": {
                "prompt": "A fluffy orange cat floating in zero gravity, fur gently moving, curious expression looking around, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, low resolution",
                "pikaffect": "Levitate",
                "style_preset": "Realistic",
            },
        },
        {
            "input": "수박 폭발 슬로우모션",
            "output": {
                "prompt": "Watermelon exploding in slow motion, seeds flying in all directions, juicy splashes, vibrant red and green colors, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry",
                "pikaffect": "Explode",
                "style_preset": "Realistic",
            },
        },
        {
            "input": "종이가 잘라지는 효과",
            "output": {
                "prompt": "White paper being sliced diagonally, clean edges, floating paper pieces, minimalist composition, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, hands",
                "pikaffect": "Slice",
                "style_preset": "3D",
            },
        },
        {
            "input": "아이스크림이 녹는 장면",
            "output": {
                "prompt": "Colorful ice cream cone melting, drips running down, creamy texture, summer vibe, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, people",
                "pikaffect": "Melt",
                "style_preset": "Realistic",
            },
        },
        {
            "input": "일반 장면 - 이펙트 없이",
            "output": {
                "prompt": "Coffee cup on cafe table, steam rising, cozy atmosphere, warm lighting, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry",
                "pikaffect": "",
                "style_preset": "Realistic",
            },
        },
        {
            "input": "애니메이션 스타일 캐릭터",
            "output": {
                "prompt": "Cute character waving hello, big expressive eyes, colorful background, friendly mood, 9:16 vertical",
                "negative_prompt": "text, watermark, realistic",
                "pikaffect": "",
                "style_preset": "Anime",
            },
        },
        {
            "input": "3D 제품 렌더링 느낌",
            "output": {
                "prompt": "Futuristic sneaker rotating slowly, holographic elements, neon accents, product showcase, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, realistic photo",
                "pikaffect": "",
                "style_preset": "3D",
            },
        },
        {
            "input": "꽃이 피어나는 장면",
            "output": {
                "prompt": "Pink rose blooming, petals unfolding gracefully, morning dew drops, romantic atmosphere, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, wilted",
                "pikaffect": "",
                "style_preset": "Realistic",
            },
        },
        {
            "input": "불꽃놀이",
            "output": {
                "prompt": "Fireworks exploding in night sky, colorful sparks spreading, celebration mood, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, daytime",
                "pikaffect": "Explode",
                "style_preset": "Realistic",
            },
        },
        {
            "input": "책장이 넘어가는 모습",
            "output": {
                "prompt": "Book pages flipping in slow motion, words blurring, magical particles, study aesthetic, 9:16 vertical",
                "negative_prompt": "text readable, watermark, blurry",
                "pikaffect": "",
                "style_preset": "Realistic",
            },
        },
    ],
    must_keywords=["subject", "action"],
    must_not_patterns=["only effect keyword", "no scene description"],
    negative_prompt_default="text, watermark, blurry, low resolution",
)


# =============================================================================
# KLING 3.0
# =============================================================================
KLING_CONFIG = ServicePromptConfig(
    name="Kling 3.0",
    prompt_pattern="[Detailed Scene], [Camera Motion], [Style], [Duration Hint], [Aspect Ratio]",
    required_fields=["prompt", "negative_prompt"],
    optional_fields=["camera_motion", "motion_intensity", "style"],
    field_examples={
        "prompt": "Professional product demonstration, clean studio lighting, cinematic commercial style, 10 seconds",
        "negative_prompt": "text, watermark, blurry, distorted",
        "camera_motion": "slow_push_in",
        "motion_intensity": "3",
        "style": "cinematic",
    },
    few_shots=[
        {
            "input": "제품 데모, 전문적인 느낌",
            "output": {
                "prompt": "Professional product demonstration, clean studio lighting, slow camera orbit around product, cinematic commercial style, 10 seconds, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, distorted",
                "camera_motion": "orbit",
                "motion_intensity": "3",
                "style": "cinematic",
            },
        },
        {
            "input": "튜토리얼 시작",
            "output": {
                "prompt": "Tutorial intro scene, presenter walking into frame, friendly expression, professional lighting, documentary style, slow push in, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry",
                "camera_motion": "slow_push_in",
                "motion_intensity": "2",
                "style": "documentary",
            },
        },
        {
            "input": "브랜드 스토리텔링",
            "output": {
                "prompt": "Brand story opening, sunrise over city, golden light spreading, inspirational mood, cinematic quality, 15 seconds, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, people",
                "camera_motion": "slow_pan_right",
                "motion_intensity": "2",
                "style": "cinematic",
            },
        },
        {
            "input": "인터뷰 배경",
            "output": {
                "prompt": "Professional interview background, blurred office interior, soft natural light, corporate style, static shot, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, distracting elements",
                "camera_motion": "static",
                "motion_intensity": "1",
                "style": "documentary",
            },
        },
        {
            "input": "이벤트 하이라이트",
            "output": {
                "prompt": "Event highlights montage, dynamic camera movements, energetic atmosphere, fast cuts style, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, static",
                "camera_motion": "dynamic",
                "motion_intensity": "5",
                "style": "commercial",
            },
        },
        {
            "input": "교육 콘텐츠",
            "output": {
                "prompt": "Educational content background, clean desk setup, books and laptop, study mood, slow zoom in, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, clutter",
                "camera_motion": "slow_zoom_in",
                "motion_intensity": "2",
                "style": "documentary",
            },
        },
        {
            "input": "모먼트 캡처",
            "output": {
                "prompt": "Lifestyle moment capture, cozy morning scene, soft window light, authentic mood, documentary style, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, staged",
                "camera_motion": "static",
                "motion_intensity": "1",
                "style": "documentary",
            },
        },
        {
            "input": "테크 리뷰",
            "output": {
                "prompt": "Tech product review setup, dark background with accent lighting, gadget on display, review style, orbit shot, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, hands",
                "camera_motion": "orbit",
                "motion_intensity": "3",
                "style": "commercial",
            },
        },
        {
            "input": "뷰티 샷",
            "output": {
                "prompt": "Beauty product showcase, soft pink lighting, elegant composition, cosmetic photography style, slow push in, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, harsh shadows",
                "camera_motion": "slow_push_in",
                "motion_intensity": "2",
                "style": "cinematic",
            },
        },
        {
            "input": "음악 비주얼",
            "output": {
                "prompt": "Music visual background, abstract light waves, rhythmic motion, artistic style, dynamic camera, 9:16 vertical",
                "negative_prompt": "text, watermark, blurry, realistic",
                "camera_motion": "dynamic",
                "motion_intensity": "5",
                "style": "artistic",
            },
        },
    ],
    must_keywords=["camera", "style"],
    must_not_patterns=["long narrative without controls", "complex scene transitions"],
    negative_prompt_default="text, watermark, blurry, distorted",
)


# =============================================================================
# GOOGLE VEO 3.x
# =============================================================================
VEO_CONFIG = ServicePromptConfig(
    name="Google Veo 3.x",
    prompt_pattern="[Visual Scene Description], [Audio Mood Hint], [Style Preset], [Aspect Ratio]",
    required_fields=["prompt", "negative_prompt"],
    optional_fields=["generate_audio", "audio_mood", "style_preset"],
    field_examples={
        "prompt": "Emotional brand story, sunrise over mountains, golden light rays, contemplative mood",
        "negative_prompt": "text, watermark, low quality",
        "generate_audio": "true",
        "audio_mood": "calm",
        "style_preset": "cinematic",
    },
    few_shots=[
        {
            "input": "브랜드 영상, 감성적",
            "output": {
                "prompt": "Emotional brand story, sunrise over mountains, golden light rays piercing through clouds, contemplative mood, cinematic style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality",
                "generate_audio": "true",
                "audio_mood": "calm",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "활기찬 제품 소개",
            "output": {
                "prompt": "Energetic product reveal, dynamic lighting effects, vibrant colors popping, upbeat mood, commercial style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, dark",
                "generate_audio": "true",
                "audio_mood": "energetic",
                "style_preset": "natural",
            },
        },
        {
            "input": "다큐멘터리 오프닝",
            "output": {
                "prompt": "Documentary opening, vast landscape aerial view, dramatic clouds, epic scale, serious tone, cinematic style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality",
                "generate_audio": "true",
                "audio_mood": "dramatic",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "라이프스타일 브랜드",
            "output": {
                "prompt": "Lifestyle brand moment, morning routine scene, soft natural light, authentic mood, natural style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, staged",
                "generate_audio": "true",
                "audio_mood": "calm",
                "style_preset": "natural",
            },
        },
        {
            "input": "기술 혁신",
            "output": {
                "prompt": "Tech innovation showcase, futuristic cityscape, neon lights, data streams, inspiring mood, cinematic style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, retro",
                "generate_audio": "true",
                "audio_mood": "energetic",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "여행 브랜드",
            "output": {
                "prompt": "Travel brand destination, tropical beach sunset, palm trees swaying, wanderlust mood, natural style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, crowds",
                "generate_audio": "true",
                "audio_mood": "calm",
                "style_preset": "natural",
            },
        },
        {
            "input": "피트니스 모티베이션",
            "output": {
                "prompt": "Fitness motivation scene, gym environment, dramatic lighting, powerful energy, intense mood, natural style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality",
                "generate_audio": "true",
                "audio_mood": "energetic",
                "style_preset": "natural",
            },
        },
        {
            "input": "푸드 브랜드",
            "output": {
                "prompt": "Food brand story, fresh ingredients arrangement, bright natural light, appetizing mood, natural style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, messy",
                "generate_audio": "true",
                "audio_mood": "calm",
                "style_preset": "natural",
            },
        },
        {
            "input": "패션 룩북",
            "output": {
                "prompt": "Fashion lookbook scene, minimalist studio, soft directional light, elegant mood, cinematic style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, clutter",
                "generate_audio": "true",
                "audio_mood": "calm",
                "style_preset": "cinematic",
            },
        },
        {
            "input": "스타트업 피치",
            "output": {
                "prompt": "Startup pitch background, modern office space, inspiring atmosphere, professional mood, natural style, 9:16 vertical",
                "negative_prompt": "text, watermark, low quality, traditional",
                "generate_audio": "true",
                "audio_mood": "dramatic",
                "style_preset": "natural",
            },
        },
    ],
    must_keywords=["visual", "audio mood"],
    must_not_patterns=["ambiguous audio mode", "text request"],
    negative_prompt_default="text, watermark, low quality",
)


# =============================================================================
# OPENAI SORA 2
# =============================================================================
SORA_CONFIG = ServicePromptConfig(
    name="OpenAI Sora 2",
    prompt_pattern="[Detailed Visual Description], [Camera Work], [Mood/Atmosphere], [Time/Lighting], [Aspect Ratio]",
    required_fields=["prompt", "negative_prompt"],
    optional_fields=["style", "camera_motion"],
    field_examples={
        "prompt": "Dawn cityscape, soft blue hour light, empty streets glistening, distant skyscrapers silhouette, contemplative mood, slow camera pan",
        "negative_prompt": "text, watermark, logo, subtitle, blurry, distorted",
        "style": "cinematic",
        "camera_motion": "slow_pan",
    },
    few_shots=[
        {
            "input": "새벽 감성, 도시 전망",
            "output": {
                "prompt": "Dawn cityscape, soft blue hour light, empty streets glistening with dew, distant skyscrapers silhouette, contemplative mood, slow camera pan, photorealistic, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, subtitle, blurry, distorted",
                "style": "cinematic",
                "camera_motion": "slow_pan",
            },
        },
        {
            "input": "몽환적 숲",
            "output": {
                "prompt": "Misty forest at dawn, sun rays filtering through ancient trees, ethereal atmosphere, dreamlike quality, soft focus, slow push in, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry, distorted",
                "style": "cinematic",
                "camera_motion": "slow_push_in",
            },
        },
        {
            "input": "바다 일출",
            "output": {
                "prompt": "Ocean sunrise, golden light reflecting on calm water, gentle waves, peaceful meditation mood, drone view slowly rising, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry",
                "style": "natural",
                "camera_motion": "drone",
            },
        },
        {
            "input": "도시 네온",
            "output": {
                "prompt": "Cyberpunk city night, neon signs reflecting on wet streets, rain falling, futuristic atmosphere, tracking shot, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, daylight",
                "style": "artistic",
                "camera_motion": "tracking",
            },
        },
        {
            "input": "산 정상",
            "output": {
                "prompt": "Mountain peak above clouds, golden hour light, epic scale, adventurous spirit, static drone view, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry",
                "style": "cinematic",
                "camera_motion": "static",
            },
        },
        {
            "input": "카페 무드",
            "output": {
                "prompt": "Cozy cafe interior, warm afternoon light through window, coffee steam rising, intimate atmosphere, slow pan right, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry, crowded",
                "style": "natural",
                "camera_motion": "slow_pan",
            },
        },
        {
            "input": "사막 황혼",
            "output": {
                "prompt": "Desert dunes at sunset, orange and purple sky, sand patterns, serene vastness, slow aerial push forward, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry, people",
                "style": "cinematic",
                "camera_motion": "drone",
            },
        },
        {
            "input": "빗방울",
            "output": {
                "prompt": "Rain drops falling on window, blurred city lights outside, melancholic mood, blue tones, static close-up, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry, sunny",
                "style": "cinematic",
                "camera_motion": "static",
            },
        },
        {
            "input": "우주",
            "output": {
                "prompt": "Deep space nebula, swirling colors, distant stars, cosmic scale, awe-inspiring mood, slow push through, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry, planets visible",
                "style": "artistic",
                "camera_motion": "slow_push_in",
            },
        },
        {
            "input": "정원",
            "output": {
                "prompt": "Secret garden at golden hour, flowers swaying gently, butterflies floating, magical atmosphere, slow tilt up, 9:16 vertical",
                "negative_prompt": "text, watermark, logo, blurry, people",
                "style": "natural",
                "camera_motion": "slow_tilt_up",
            },
        },
    ],
    must_keywords=["visual detail", "camera", "mood"],
    must_not_patterns=["complex narrative", "text request", "subtitle", "dialogue"],
    negative_prompt_default="text, watermark, logo, subtitle, blurry, distorted, low quality, cartoon, anime, unrealistic",
)


# =============================================================================
# 서비스 설정 매핑
# =============================================================================
SERVICE_CONFIGS: dict[str, ServicePromptConfig] = {
    "luma": LUMA_CONFIG,
    "runway": RUNWAY_CONFIG,
    "pika": PIKA_CONFIG,
    "kling": KLING_CONFIG,
    "veo": VEO_CONFIG,
    "sora": SORA_CONFIG,
}


# =============================================================================
# API 함수
# =============================================================================
def get_service_config(service: str) -> ServicePromptConfig | None:
    """서비스별 설정 조회"""
    return SERVICE_CONFIGS.get(service)


def get_service_schema_with_examples(service: str) -> str:
    """서비스별 JSON 스키마 + 예시값을 문자열로 반환"""
    config = SERVICE_CONFIGS.get(service)
    if not config:
        return ""

    # 필수 필드
    required_parts = []
    for field in config.required_fields:
        example = config.field_examples.get(field, "")
        required_parts.append(f'"{field}": "{example}"')

    # 선택 필드
    optional_parts = []
    for field in config.optional_fields:
        example = config.field_examples.get(field, "")
        optional_parts.append(f'"{field}": "{example}"')

    schema = "{\n"
    schema += "  // 필수 필드\n"
    schema += ",\n".join(f"    {p}" for p in required_parts)
    if optional_parts:
        schema += ",\n\n  // 선택 필드\n"
        schema += ",\n".join(f"    {p} (optional)" for p in optional_parts)
    schema += "\n  }"

    return schema


def get_few_shots_section(service: str, count: int = 5) -> str:
    """서비스별 Few-shot 예시 섹션 생성"""
    config = SERVICE_CONFIGS.get(service)
    if not config:
        return ""

    import json

    shots = config.few_shots[:count]
    lines = [f"### {config.name} Few-shot 예시\n"]

    for i, shot in enumerate(shots, 1):
        lines.append(f"**예시 {i}**")
        lines.append(f"- Input: {shot['input']}")
        lines.append("- Output:")
        output_json = json.dumps(shot["output"], ensure_ascii=False, indent=2)
        lines.append(f"```json\n{output_json}\n```")
        lines.append("")

    return "\n".join(lines)


def build_service_instruction(service: str) -> str:
    """서비스별 프롬프트 작성 지침 생성"""
    config = SERVICE_CONFIGS.get(service)
    if not config:
        return ""

    instruction = f"""
## {config.name} 프롬프트 작성 가이드

### 프롬프트 패턴
{config.prompt_pattern}

### 필수 포함 요소
"""
    for kw in config.must_keywords:
        instruction += f"- {kw}\n"

    instruction += "\n### 금지 패턴\n"
    for pattern in config.must_not_patterns:
        instruction += f"- {pattern}\n"

    instruction += f"""
### 기본 Negative Prompt
`{config.negative_prompt_default}`

### JSON 스키마
{get_service_schema_with_examples(service)}

{get_few_shots_section(service, count=5)}
"""
    return instruction


def merge_service_instructions(services: list[str]) -> str:
    """여러 서비스의 지침 병합"""
    instructions = [build_service_instruction(s) for s in services if s in SERVICE_CONFIGS]
    return "\n\n---\n\n".join(instructions)


# 하위 호환성 유지
SERVICE_PROMPT_RULES = {
    svc: {
        "must": config.must_keywords,
        "must_not": config.must_not_patterns,
    }
    for svc, config in SERVICE_CONFIGS.items()
}

SERVICE_PROMPT_TEMPLATES = {svc: build_service_instruction(svc) for svc in SERVICE_CONFIGS.keys()}

DEFAULT_NEGATIVE_PROMPTS = {svc: config.negative_prompt_default for svc, config in SERVICE_CONFIGS.items()}


def get_prompt_template(service: str) -> str:
    """서비스별 프롬프트 템플릿 조회"""
    return SERVICE_PROMPT_TEMPLATES.get(service, "")


def get_default_negative_prompt(service: str) -> str:
    """서비스별 기본 negative prompt 조회"""
    return DEFAULT_NEGATIVE_PROMPTS.get(service, "")


def get_prompt_rules(service: str) -> dict[str, list[str]]:
    """서비스별 프롬프트 규칙 조회"""
    return SERVICE_PROMPT_RULES.get(service, {"must": [], "must_not": []})


def merge_service_templates(services: list[str]) -> str:
    """여러 서비스의 템플릿 병합"""
    templates = [get_prompt_template(s) for s in services]
    return "\n\n".join(t for t in templates if t)
