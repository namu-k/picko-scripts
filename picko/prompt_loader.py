"""
프롬프트 로더 모듈
외부 파일에서 프롬프트를 로드하고 렌더링
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .logger import get_logger

logger = get_logger("prompt_loader")

# 기본 프롬프트 디렉토리
DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


class PromptLoader:
    """프롬프트 로더 - 파일에서 프롬프트를 로드하고 Jinja2로 렌더링"""

    def __init__(self, prompts_dir: str | Path | None = None, account_overrides_dir: str | Path | None = None):
        """
        프롬프트 로더 초기화

        Args:
            prompts_dir: 프롬프트 기본 디렉토리 (기본: config/prompts/)
            account_overrides_dir: 계정별 오버라이드 루트 디렉토리 (기본: config/accounts/)
        """
        if prompts_dir is None:
            prompts_dir = DEFAULT_PROMPTS_DIR

        self.prompts_dir = Path(prompts_dir)
        self.account_overrides_dir = Path(account_overrides_dir) if account_overrides_dir else None

        # Jinja2 환경 설정
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        logger.debug(f"PromptLoader initialized: {self.prompts_dir}")

    def load(self, prompt_type: str, name: str = "default", account_id: str | None = None) -> str:
        """
        프롬프트 로드

        Args:
            prompt_type: 프롬프트 타입 (longform, packs, image)
            name: 프롬프트 이름 (기본: default)
            account_id: 계정 ID (오버라이드용)

        Returns:
            프롬프트 템플릿 문자열

        Raises:
            FileNotFoundError: 프롬프트 파일을 찾을 수 없음
        """
        # 1. 계정별 오버라이드 확인
        if account_id and self.account_overrides_dir:
            override_path = self.account_overrides_dir / account_id / "prompts" / prompt_type / f"{name}.md"
            if override_path.exists():
                logger.debug(f"Using account override prompt: {override_path}")
                return override_path.read_text(encoding="utf-8")

        # 2. 기본 프롬프트 로드
        prompt_path = self.prompts_dir / prompt_type / f"{name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")

        logger.debug(f"Loading prompt: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def render(self, prompt_type: str, name: str = "default", account_id: str | None = None, **variables) -> str:
        """
        프롬프트 로드 후 렌더링

        Args:
            prompt_type: 프롬프트 타입 (longform, packs, image)
            name: 프롬프트 이름 (기본: default)
            account_id: 계정 ID (오버라이드용)
            **variables: 템플릿 변수

        Returns:
            렌더링된 프롬프트 문자열
        """
        template_string = self.load(prompt_type, name, account_id)
        template = self.env.from_string(template_string)
        result = template.render(**variables)
        logger.debug(f"Rendered prompt: {prompt_type}/{name}")
        return result

    def render_template(self, template_string: str, **variables) -> str:
        """
        문자열 템플릿 직접 렌더링

        Args:
            template_string: 템플릿 문자열
            **variables: 템플릿 변수

        Returns:
            렌더링된 문자열
        """
        template = self.env.from_string(template_string)
        return template.render(**variables)

    def get_longform_prompt(
        self,
        input_content: dict,
        name: str = "default",
        account_id: str | None = None,
        exploration: dict | None = None,
    ) -> str:
        """
        롱폼용 프롬프트 생성

        Args:
            input_content: 입력 콘텐츠 (title, summary, key_points, excerpt 등)
            name: 프롬프트 이름
            account_id: 계정 ID
            exploration: 탐색 결과 (선택적, 있으면 with_exploration 템플릿 사용)

        Returns:
            렌더링된 프롬프트
        """
        # 탐색 결과가 있으면 with_exploration 템플릿 사용
        if exploration:
            name = "with_exploration"

        return self.render(
            "longform",
            name=name,
            account_id=account_id,
            title=input_content.get("title", ""),
            summary=input_content.get("summary", ""),
            key_points=input_content.get("key_points", []),
            excerpt=input_content.get("excerpt", ""),
            tags=input_content.get("tags", []),
            exploration=exploration or {},
        )

    def get_pack_prompt(
        self, channel: str, input_content: dict, channel_config: dict | None = None, account_id: str | None = None
    ) -> str:
        """
        채널별 팩용 프롬프트 생성

        Args:
            channel: 채널명 (twitter, linkedin, newsletter)
            input_content: 입력 콘텐츠
            channel_config: 채널 설정 (max_length, tone, hashtags)
            account_id: 계정 ID

        Returns:
            렌더링된 프롬프트
        """
        channel_config = channel_config or {}

        return self.render(
            "packs",
            name=channel,
            account_id=account_id,
            channel=channel,
            title=input_content.get("title", ""),
            summary=input_content.get("summary", ""),
            max_length=channel_config.get("max_length", 280),
            tone=channel_config.get("tone", "casual"),
            use_hashtags=channel_config.get("hashtags", True),
            tags=input_content.get("tags", []),
        )

    def get_image_prompt(self, input_content: dict, name: str = "default", account_id: str | None = None) -> str:
        """
        이미지 프롬프트 생성

        Args:
            input_content: 입력 콘텐츠
            name: 프롬프트 이름
            account_id: 계정 ID

        Returns:
            렌더링된 프롬프트
        """
        return self.render(
            "image",
            name=name,
            account_id=account_id,
            title=input_content.get("title", ""),
            summary=input_content.get("summary", ""),
            tags=input_content.get("tags", []),
        )

    def get_exploration_prompt(self, input_content: dict, name: str = "default", account_id: str | None = None) -> str:
        """
        주제 탐색용 프롬프트 생성

        Args:
            input_content: 입력 콘텐츠
            name: 프롬프트 이름
            account_id: 계정 ID

        Returns:
            렌더링된 프롬프트
        """
        return self.render(
            "exploration",
            name=name,
            account_id=account_id,
            title=input_content.get("title", ""),
            summary=input_content.get("summary", ""),
            key_points=input_content.get("key_points", []),
            tags=input_content.get("tags", []),
        )

    def list_prompts(self, prompt_type: str) -> list[str]:
        """
        특정 타입의 사용 가능한 프롬프트 목록 반환

        Args:
            prompt_type: 프롬프트 타입

        Returns:
            프롬프트 이름 목록
        """
        type_dir = self.prompts_dir / prompt_type
        if not type_dir.exists():
            return []

        return [f.stem for f in type_dir.glob("*.md")]


# 편의 함수 - 싱글톤 패턴
_default_loader: PromptLoader | None = None


def get_prompt_loader() -> PromptLoader:
    """기본 PromptLoader 반환"""
    global _default_loader
    if _default_loader is None:
        # config/accounts를 오버라이드 루트로 설정
        accounts_dir = Path(__file__).parent.parent / "config" / "accounts"
        _default_loader = PromptLoader(account_overrides_dir=accounts_dir)
    return _default_loader


def load_prompt(prompt_type: str, name: str = "default", account_id: str | None = None) -> str:
    """프롬프트 로드 편의 함수"""
    return get_prompt_loader().load(prompt_type, name, account_id)


def render_prompt(prompt_type: str, name: str = "default", account_id: str | None = None, **variables) -> str:
    """프롬프트 렌더링 편의 함수"""
    return get_prompt_loader().render(prompt_type, name, account_id, **variables)
