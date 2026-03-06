"""
Generate Content 스크립트
승인된 Digest 항목 → Longform/Packs/Image Prompts 생성
"""

import argparse
import re
from datetime import datetime
from typing import Any

from picko.account_context import WeeklySlot, get_identity, get_weekly_slot
from picko.config import get_config
from picko.llm_client import get_writer_client
from picko.logger import setup_logger
from picko.prompt_composer import get_effective_prompt
from picko.prompt_loader import get_prompt_loader
from picko.templates import get_renderer
from picko.vault_io import VaultIO
from scripts.validate_output import OutputValidator

logger = setup_logger("generate_content")


def smart_truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """
    텍스트를 max_length 이하로 자르되, 단어 경계에서 자릅니다.
    해시태그가 포함된 경우 해시태그를 보존합니다.
    """
    if len(text) <= max_length:
        return text

    # 해시태그 분리 (본문 끝에 있는 경우)
    lines = text.strip().split("\n")
    hashtags = []
    body_lines = []

    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith("#") and " " not in stripped:
            hashtags.insert(0, stripped)
        else:
            body_lines = lines[lines.index(line) :]
            break

    body = "\n".join(body_lines).strip()
    hashtag_str = " ".join(hashtags)

    # 본문 + 해시태그가 max_length를 넘으면 본문 자르기
    available_length = max_length - len(hashtag_str) - 1 if hashtag_str else max_length

    if len(body) > available_length:
        # 단어 경계에서 자르기
        truncated = body[: available_length - len(suffix)]
        last_space = truncated.rfind(" ")
        if last_space > available_length // 2:
            truncated = truncated[:last_space]
        body = truncated + suffix

    result = body
    if hashtag_str:
        result = f"{body}\n\n{hashtag_str}"

    return result[:max_length]  # 최종 보장


class ContentGenerator:
    """콘텐츠 생성기"""

    # Digest 파싱을 위한 정규식 패턴
    _CHECKBOX_PATTERN = r"##\s*\[([xX ])\]\s*(.+?)(?:\n|$)"
    _ID_PATTERN = r"\*\*ID\*\*:\s*(\S+)"
    _ACCOUNT_PATTERN = r"\*\*Account\*\*:\s*(\S+)"

    def __init__(self, dry_run: bool = False, weekly_slot: WeeklySlot | None = None):
        self.config = get_config()
        self.vault = VaultIO()
        # 글쓰기용 클라우드 LLM 사용
        self.llm = get_writer_client()
        self.renderer = get_renderer()
        self.prompt_loader = get_prompt_loader()
        self.dry_run = dry_run
        self.weekly_slot = weekly_slot
        self.validator = OutputValidator()  # 자동 검증용
        self.auto_validate = bool(getattr(self.config.generation, "auto_validate", True))
        logger.info("ContentGenerator initialized")

    def run(
        self,
        date: str | None = None,
        content_types: list[str] | None = None,
        force: bool = False,
        auto_all: bool = False,
        items: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        콘텐츠 생성 파이프라인 실행

        Args:
            date: Digest 날짜 (YYYY-MM-DD)
            content_types: 생성할 타입 (longform, packs, images)
            force: 이미 생성된 항목도 재생성
            auto_all: auto_ready 상태 항목 모두 처리
            items: 처리할 항목 ID 목록 (배치 처리용, 없으면 전체)

        Returns:
            실행 결과 요약
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        if content_types is None:
            content_types = ["longform", "packs", "images", "videos"]

        logger.info(f"Starting content generation for {date}, types: {content_types}")

        results: dict[str, Any] = {
            "date": date,
            "approved_items": 0,
            "longform_created": 0,
            "packs_created": 0,
            "image_prompts_created": 0,
            "video_prompts_created": 0,
            "errors": [],
        }

        try:
            # 1. 처리할 항목 결정
            if items:
                # 배치 모드: 지정된 항목만 처리
                approved_items = self._get_items_by_ids(items)
                logger.info(f"Batch mode: processing {len(approved_items)} specified items")
            else:
                # 일반 모드: Digest에서 승인된 항목 파싱
                approved_items = self._parse_digest(date, auto_all=auto_all)

            results["approved_items"] = len(approved_items)
            logger.info(f"Found {len(approved_items)} items to process")

            if not approved_items:
                logger.info("No items found")
                return results

            # 2. 각 항목에 대해 콘텐츠 생성
            for item in approved_items:
                self._process_item(item, content_types, force, date, results)

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            results["errors"].append(str(e))

        logger.info(f"Content generation complete: {results}")
        return results

    def _get_items_by_ids(self, item_ids: list[str]) -> list[dict[str, Any]]:
        """
        ID 목록으로 항목 정보 조회

        Args:
            item_ids: 항목 ID 목록

        Returns:
            항목 정보 목록
        """
        items = []
        for item_id in item_ids:
            # Input 파일에서 항목 정보 로드
            input_path = f"Inbox/Inputs/{item_id}.md"
            try:
                meta, content = self.vault.read_note(input_path)
                items.append(
                    {
                        "input_id": item_id,
                        "title": meta.get("title", ""),
                        "source_url": meta.get("source_url", ""),
                        "writing_status": meta.get("writing_status", "pending"),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to load item {item_id}: {e}")

        return items

    def _process_item(
        self,
        item: dict[str, Any],
        content_types: list[str],
        force: bool,
        date: str,
        results: dict[str, Any],
    ) -> None:
        """
        단일 항목 처리

        Args:
            item: 승인된 항목 정보
            content_types: 생성할 콘텐츠 타입 목록
            force: 강제 재생성 여부
            date: Digest 날짜
            results: 결과 집계 딕셔너리
        """
        try:
            if not self._should_process_item(item, force):
                return

            input_content = self._load_input(item["input_id"])
            if not input_content:
                return

            self._generate_content_types(item, input_content, content_types, results, force)

            # Digest 상태 업데이트
            if not self.dry_run:
                self._update_digest_status(date, item["input_id"])

        except Exception as e:
            logger.error(f"Failed to process {item.get('input_id')}: {e}")
            results["errors"].append(str(e))

    def _should_process_item(self, item: dict[str, Any], force: bool) -> bool:
        """
        항목 처리 여부 확인

        Args:
            item: 항목 정보
            force: 강제 재생성 여부

        Returns:
            처리해야 하면 True
        """
        # 이미 생성된 경우 스킵 (force가 아니면)
        if not force and item.get("status") == "generated":
            logger.debug(f"Skipping already generated: {item['input_id']}")
            return False

        return True

    def _generate_content_types(
        self,
        item: dict[str, Any],
        input_content: dict[str, Any],
        content_types: list[str],
        results: dict[str, Any],
        force: bool = False,
    ) -> None:
        """
        지정된 콘텐츠 타입들 생성

        Args:
            item: 항목 정보
            input_content: Input 노트 내용
            content_types: 생성할 타입 목록
            results: 결과 집계 딕셔너리
            force: 강제 재생성 여부
        """
        # writing_status 확인: force가 아니고 manual/completed이면 스킵
        writing_status = input_content.get("writing_status", "pending")
        if not force and writing_status in ["manual", "completed"]:
            logger.info(f"Skipping {writing_status} item: {item['input_id']}")
            return

        # Longform 생성
        if "longform" in content_types:
            if self._generate_longform(item, input_content):
                results["longform_created"] += 1

        # Packs 생성 (파생 승인 확인)
        if "packs" in content_types:
            packs_count = self._generate_packs_with_approval(item, input_content)
            results["packs_created"] += packs_count

        # Image Prompts 생성 (파생 승인 확인)
        if "images" in content_types:
            if self._generate_image_with_approval(item, input_content):
                results["image_prompts_created"] += 1

        # Video Prompts 생성 (파생 승인 확인)
        if "videos" in content_types:
            if self._generate_video_with_approval(item, input_content):
                results["video_prompts_created"] = results.get("video_prompts_created", 0) + 1

    # ─────────────────────────────────────────────────────────────
    # Digest 파싱
    # ─────────────────────────────────────────────────────────────

    def _parse_digest(self, date: str, auto_all: bool = False) -> list[dict[str, Any]]:
        """
        Digest에서 승인된 항목 파싱
        [x] 체크된 항목 추출 (auto_all=True면 미체크도 포함)

        Args:
            date: Digest 날짜
            auto_all: 미체크 항목도 모두 포함

        Returns:
            승인된 항목 리스트
        """
        digest_path = f"{self.config.vault.digests}/{date}.md"

        try:
            meta, content = self.vault.read_note(digest_path)
        except FileNotFoundError:
            logger.warning(f"Digest not found: {digest_path}")
            return []

        lines = content.split("\n")
        return self._parse_digest_lines(lines, auto_all)

    def _parse_digest_lines(self, lines: list[str], auto_all: bool) -> list[dict[str, Any]]:
        """
        Digest 라인들 파싱

        Args:
            lines: Digest 파일의 라인들
            auto_all: 미체크 항목도 모두 포함

        Returns:
            승인된 항목 리스트
        """
        approved = []
        current_item = None

        for line in lines:
            current_item = self._parse_line(line, current_item, auto_all, approved)

        # 마지막 항목 추가
        if current_item:
            approved.append(current_item)

        # input_id가 있는 항목만 반환
        return [item for item in approved if item.get("input_id")]

    def _parse_line(
        self,
        line: str,
        current_item: dict[str, Any] | None,
        auto_all: bool,
        approved: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        단일 라인 파싱

        Args:
            line: 파싱할 라인
            current_item: 현재 처리 중인 항목
            auto_all: 미체크 항목도 모두 포함
            approved: 승인된 항목 리스트

        Returns:
            업데이트된 current_item
        """
        # 새 항목 시작 체크
        checkbox_match = re.match(self._CHECKBOX_PATTERN, line)
        if checkbox_match:
            if current_item:
                approved.append(current_item)
            return self._create_item_from_checkbox(checkbox_match, auto_all)

        # 현재 항목의 세부 정보 파싱
        if current_item:
            return self._parse_item_detail(line, current_item)

        return current_item

    def _create_item_from_checkbox(self, match: re.Match[str], auto_all: bool) -> dict[str, Any] | None:
        """
        체크박스 매치에서 항목 생성

        Args:
            match: 정규식 매치 객체
            auto_all: 미체크 항목도 포함 여부

        Returns:
            생성된 항목 딕셔너리 또는 None
        """
        checkbox = match.group(1).strip()
        title = match.group(2).strip()

        # [x] 체크된 항목 또는 auto_all=True면 포함
        if checkbox.lower() == "x" or auto_all:
            return {
                "title": title,
                "input_id": None,
                "account_id": None,
                "checked": (checkbox.lower() == "x"),
            }
        return None

    def _parse_item_detail(self, line: str, current_item: dict[str, Any]) -> dict[str, Any]:
        """
        항목 세부 정보 파싱

        Args:
            line: 파싱할 라인
            current_item: 현재 항목

        Returns:
            업데이트된 항목
        """
        # ID 파싱
        id_match = re.search(self._ID_PATTERN, line)
        if id_match:
            current_item["input_id"] = id_match.group(1)
            return current_item

        # Account 파싱
        account_match = re.search(self._ACCOUNT_PATTERN, line)
        if account_match:
            current_item["account_id"] = account_match.group(1)

        return current_item

    def _load_input(self, input_id: str) -> dict[str, Any] | None:
        """Input 노트 로드"""
        input_path = f"{self.config.vault.inbox}/{input_id}.md"

        try:
            meta, content = self.vault.read_note(input_path)

            # writing_status 확인 (본문 체크박스도 확인)
            writing_status = meta.get("writing_status", "pending")

            # 본문에서 체크박스 상태 확인
            if writing_status == "pending":
                # 자동 작성 체크박스 확인
                if "[x] **자동 작성**" in content or "[x] 자동 작성" in content:
                    writing_status = "auto_ready"
                    # 메타데이터 업데이트
                    meta["writing_status"] = writing_status
                    self.vault.write_note(input_path, content, metadata=meta, overwrite=True)
                # 수동 작성 체크박스 확인
                elif "[x] **수동 작성**" in content or "[x] 수동 작성" in content:
                    writing_status = "manual"
                    meta["writing_status"] = writing_status
                    self.vault.write_note(input_path, content, metadata=meta, overwrite=True)

            return {
                "id": input_id,
                "meta": meta,
                "content": content,
                "title": meta.get("title", ""),
                "summary": self._extract_section(content, "요약"),
                "key_points": self._extract_list(content, "핵심 포인트"),
                "excerpt": self._extract_section(content, "원문 발췌"),
                "tags": meta.get("tags", []),
                "writing_status": writing_status,
            }
        except FileNotFoundError:
            logger.warning(f"Input not found: {input_path}")
            return None

    def _load_exploration(self, input_id: str) -> dict[str, Any] | None:
        """탐색 노트 로드 (있으면)"""
        exploration_path = f"{self.config.vault.explorations}/explore_{input_id}.md"

        try:
            meta, content = self.vault.read_note(exploration_path)
            logger.debug(f"Found exploration for: {input_id}")

            return {
                "topic_expansion": self._extract_section(content, "주제 확장"),
                "related_discussions": self._extract_section(content, "관련 논의와 반론"),
                "reader_insights": self._extract_section(content, "독자 인사이트"),
                "writing_guide": self._extract_section(content, "롱폼 작성 가이드"),
            }
        except FileNotFoundError:
            logger.debug(f"No exploration found for: {input_id}")
            return None

    def _extract_section(self, content: str, section_name: str) -> str:
        """마크다운에서 섹션 추출"""
        pattern = rf"##\s*{section_name}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_list(self, content: str, section_name: str) -> list[str]:
        """마크다운에서 리스트 섹션 추출"""
        section = self._extract_section(content, section_name)
        items = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                items.append(line.lstrip("-* ").strip())
        return items

    # ─────────────────────────────────────────────────────────────
    # 콘텐츠 생성
    # ─────────────────────────────────────────────────────────────

    def _generate_longform(self, item: dict[str, Any], input_content: dict[str, Any]) -> bool:
        """Longform 콘텐츠 생성"""
        logger.info(f"Generating longform for: {item['input_id']}")

        # 탐색 결과 로드 (있으면)
        exploration = self._load_exploration(item["input_id"])

        # WeeklySlot 컨텍스트 준비
        weekly_context = self._prepare_weekly_context()

        # 계정 ID (None인 경우 기본값 사용)
        account_id = item.get("account_id") or "socialbuilders"

        # 프롬프트 합성 (prompt_composer 사용)
        content_type = "longform_with_exploration" if exploration else "longform"
        prompt = get_effective_prompt(
            account_id=account_id,
            content_type=content_type,
            weekly_slot=self.weekly_slot,
            variables={
                "title": input_content.get("title", ""),
                "summary": input_content.get("summary", ""),
                "key_points": input_content.get("key_points", []),
                "excerpt": input_content.get("excerpt", ""),
                "exploration": exploration,
                **(weekly_context or {}),
            },
        )

        response = self.llm.generate(prompt, max_tokens=2000)

        # 섹션 파싱
        sections = self._parse_generated_sections(response)

        # 템플릿 렌더링을 위한 데이터 구성
        longform_data = {
            "id": f"longform_{item['input_id']}",
            "title": input_content["title"],
            "source_input_id": item["input_id"],
            "intro": sections.get("인트로", ""),
            "main_content": sections.get("메인 콘텐츠", response),
            "takeaways": sections.get("주요 시사점", ""),
            "cta": sections.get("마무리", ""),
            "tags": input_content.get("tags", []),
        }

        content = self.renderer.render_longform(longform_data)

        # 저장
        if not self.dry_run:
            output_path = f"{self.config.vault.longform}/{longform_data['id']}.md"
            meta = self._parse_frontmatter(content)
            body = content.split("---", 2)[2].strip() if content.startswith("---") else content
            self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
            logger.info(f"Created longform: {output_path}")

            self._run_validation_if_enabled(output_path, "Longform")

        return True

    def _parse_generated_sections(self, text: str) -> dict[str, Any]:
        """LLM 생성 텍스트에서 섹션 파싱"""
        sections = {}
        current_section = None
        current_content = []

        for line in text.split("\n"):
            # [섹션명] 패턴 확인
            match = re.match(r"\[(.+?)\]", line.strip())
            if match:
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = match.group(1)
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _parse_image_prompt_output(self, response: str) -> dict[str, str]:
        sections = self._parse_generated_sections(response)

        def pick(*keys: str, default: str = "") -> str:
            for key in keys:
                value = sections.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return default

        prompt = pick("MAIN_PROMPT", "메인 프롬프트", default=response.strip())
        negative_prompt = pick(
            "NEGATIVE_PROMPT",
            "네거티브 프롬프트",
            default="text, watermark, low quality",
        )
        style_keywords = pick("STYLE_KEYWORDS", "스타일", default="modern, clean")
        mood = pick("MOOD", "분위기", default="professional")
        color_palette = pick("COLOR_PALETTE", "색상", default="brand colors")
        focal_subject = pick("FOCAL_SUBJECT", "PRIMARY_MESSAGE_VISUAL", "HERO_FOCUS")
        composition = pick("COMPOSITION")

        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "style": style_keywords,
            "mood": mood,
            "colors": color_palette,
            "style_keywords": style_keywords,
            "color_palette": color_palette,
            "focal_subject": focal_subject,
            "composition": composition,
        }

    def _run_validation_if_enabled(self, output_path: str, content_type: str) -> None:
        """설정 기반 자동 검증 실행"""
        if self.dry_run:
            return

        auto_validate = bool(getattr(self, "auto_validate", True))
        if not auto_validate:
            logger.debug(f"Auto validation disabled, skipping: {output_path}")
            return

        validator = getattr(self, "validator", None)
        if validator is None:
            logger.debug(f"Validator not configured, skipping: {output_path}")
            return

        try:
            report = validator.validate_path(output_path, recursive=False)
            if report.results:
                result = report.results[0]
                if not result.valid:
                    logger.error(f"{content_type} validation FAILED: {result.errors}")
                else:
                    logger.debug(f"{content_type} validation passed: {output_path}")
        except Exception as e:
            logger.warning(f"{content_type} validation error: {e}")

    def _generate_packs(self, item: dict[str, Any], input_content: dict[str, Any]) -> int:
        """채널별 패키징 콘텐츠 생성"""
        logger.info(f"Generating packs for: {item['input_id']}")

        # 계정 프로필에서 채널 설정 로드 (None인 경우 기본값 사용)
        account_id = item.get("account_id") or "socialbuilders"
        account = self.config.get_account(account_id)
        channels = account.get("channels", {})

        # WeeklySlot 컨텍스트 준비
        weekly_context = self._prepare_weekly_context()

        # 계정 컨텍스트 준비
        account_context = self._prepare_account_context(account_id)

        created_count = 0

        for channel, channel_config in channels.items():
            try:
                # 프롬프트 로더를 통해 채널별 프롬프트 생성
                prompt = self.prompt_loader.get_pack_prompt(
                    channel=channel,
                    input_content=input_content,
                    channel_config=channel_config,
                    account_id=account_id,
                    weekly_context=weekly_context,
                    account_context=account_context,
                )

                text = self.llm.generate(prompt, max_tokens=500)

                # max_length 강제 적용
                max_length = channel_config.get("max_length", 280)
                original_len = len(text)
                if original_len > max_length:
                    logger.warning(
                        f"Pack text exceeded max_length ({original_len}/{max_length}), truncating: {channel}"
                    )
                    text = smart_truncate(text, max_length)

                # 해시태그 추출
                use_hashtags = channel_config.get("hashtags", True)
                hashtags = []
                if use_hashtags:
                    hashtags = [f"#{tag}" for tag in input_content.get("tags", [])[:3]]

                pack_data = {
                    "id": f"pack_{item['input_id']}_{channel}",
                    "source_longform_id": f"longform_{item['input_id']}",
                    "text": text.strip(),
                    "hashtags": hashtags,
                }

                content = self.renderer.render_pack(pack_data, channel, channel_config)

                # 저장
                if not self.dry_run:
                    output_path = f"{self.config.vault.packs}/{channel}/{pack_data['id']}.md"
                    self.vault.ensure_dir(f"{self.config.vault.packs}/{channel}")
                    meta = self._parse_frontmatter(content)
                    body = content.split("---", 2)[2].strip() if content.startswith("---") else content
                    self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
                    logger.info(f"Created pack: {output_path}")

                created_count += 1

            except Exception as e:
                logger.warning(f"Failed to create {channel} pack: {e}")

        return created_count

    def _generate_image_prompt(self, item: dict[str, Any], input_content: dict[str, Any]) -> bool:
        """이미지 프롬프트 생성"""
        logger.info(f"Generating image prompt for: {item['input_id']}")

        # 프롬프트 로더를 통해 이미지 프롬프트 생성 (None인 경우 기본값 사용)
        prompt = self.prompt_loader.get_image_prompt(
            input_content=input_content,
            account_id=item.get("account_id") or "socialbuilders",
        )

        response = self.llm.generate(prompt, max_tokens=500)
        parsed = self._parse_image_prompt_output(response)

        prompt_data = {
            "id": f"img_{item['input_id']}",
            "source_content_id": item["input_id"],
            "prompt": parsed["prompt"],
            "negative_prompt": parsed["negative_prompt"],
            "style": parsed["style"],
            "mood": parsed["mood"],
            "colors": parsed["colors"],
            "style_keywords": parsed["style_keywords"],
            "color_palette": parsed["color_palette"],
            "focal_subject": parsed["focal_subject"],
            "composition": parsed["composition"],
        }

        content = self.renderer.render_image_prompt(prompt_data)

        # 저장
        if not self.dry_run:
            output_path = f"{self.config.vault.images_prompts}/{prompt_data['id']}.md"
            meta = self._parse_frontmatter(content)
            body = content.split("---", 2)[2].strip() if content.startswith("---") else content
            self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
            logger.info(f"Created image prompt: {output_path}")

            self._run_validation_if_enabled(output_path, "Image prompt")

        return True

    def _generate_packs_with_approval(self, item: dict[str, Any], input_content: dict[str, Any]) -> int:
        """파생 승인 확인 후 팩 생성"""
        derivative_status = self._check_derivative_approval(item["input_id"])

        if derivative_status.get("status") != "approved":
            logger.debug(f"Skipping packs - derivative not approved: {item['input_id']}")
            return 0

        # 롱폼 본문을 소스로 사용
        longform_content = self._load_longform_content(item["input_id"])
        if longform_content:
            input_content = {**input_content, **longform_content}

        # 승인된 채널만 생성
        approved_channels = derivative_status.get("packs_channels", [])
        if not approved_channels:
            logger.debug(f"No packs channels approved: {item['input_id']}")
            return 0

        return self._generate_packs_for_channels(item, input_content, approved_channels)

    def _generate_image_with_approval(self, item: dict[str, Any], input_content: dict[str, Any]) -> bool:
        """파생 승인 확인 후 이미지 프롬프트 생성"""
        # 롱폼 노트에서 파생 승인 상태 확인
        derivative_status = self._check_derivative_approval(item["input_id"])

        if derivative_status.get("status") != "approved":
            logger.debug(f"Skipping images - derivative not approved: {item['input_id']}")
            return False

        if not derivative_status.get("images_approved", False):
            logger.debug(f"Images not approved: {item['input_id']}")
            return False

        # 롱폼 본문을 소스로 사용
        longform_content = self._load_longform_content(item["input_id"])
        if longform_content:
            input_content = {**input_content, **longform_content}

        return self._generate_image_prompt(item, input_content)

    def _generate_video_with_approval(self, item: dict[str, Any], input_content: dict[str, Any]) -> bool:
        """파생 승인 확인 후 영상 프롬프트 생성"""
        derivative_status = self._check_derivative_approval(item["input_id"])

        if derivative_status.get("status") != "approved":
            logger.debug(f"Skipping videos - derivative not approved: {item['input_id']}")
            return False

        if not derivative_status.get("videos_approved", False):
            logger.debug(f"Videos not approved: {item['input_id']}")
            return False

        longform_content = self._load_longform_content(item["input_id"])
        if longform_content:
            input_content = {**input_content, **longform_content}

        return self._generate_video_prompt(item, input_content)

    def _generate_video_prompt(self, item: dict[str, Any], input_content: dict[str, Any]) -> bool:
        """영상 프롬프트 생성 (VideoGenerator 사용)"""
        logger.info(f"Generating video prompt for: {item['input_id']}")

        try:
            from picko.video.generator import VideoGenerator

            account_id = item.get("account_id") or "socialbuilders"

            generator = VideoGenerator(
                account_id=account_id,
                services=["luma", "sora"],
                platforms=["instagram_reel", "youtube_short"],
                intent="ad",
                content_id=item["input_id"],
                week_of=self.weekly_slot.week_of if self.weekly_slot else "",
            )

            plan = generator.generate(validate=True)
            plan_dict = plan.to_dict()
            plan_dict["source_content_id"] = item["input_id"]

            content = self.renderer.render_video_prompt(plan_dict)

            if not self.dry_run:
                video_id = f"video_{item['input_id']}"
                output_path = f"{self.config.vault.videos_prompts}/{video_id}.md"
                meta = self._parse_frontmatter(content)
                body = content.split("---", 2)[2].strip() if content.startswith("---") else content
                self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
                logger.info(f"Created video prompt: {output_path}")
                self._run_validation_if_enabled(output_path, "Video prompt")

            return True

        except Exception as e:
            logger.error(f"Failed to generate video prompt: {e}")
            return False

    def _check_derivative_approval(self, input_id: str) -> dict[str, Any]:
        """롱폼 노트에서 파생 승인 상태 및 채널 선택 확인"""
        longform_path = f"{self.config.vault.longform}/longform_{input_id}.md"

        try:
            meta, content = self.vault.read_note(longform_path)

            # 채널별 체크박스 상태 확인
            selected_channels = []

            # 각 채널별 체크박스 확인
            channel_patterns = {
                "twitter": ["[x] **Twitter**", "[x] Twitter"],
                "linkedin": ["[x] **LinkedIn**", "[x] LinkedIn"],
                "newsletter": ["[x] **Newsletter**", "[x] Newsletter"],
                "instagram": ["[x] **Instagram**", "[x] Instagram"],
                "threads": ["[x] **Threads**", "[x] Threads"],
            }

            for channel, patterns in channel_patterns.items():
                if any(pattern in content for pattern in patterns):
                    selected_channels.append(channel)

            # 이미지 체크박스 확인
            images_approved = any(
                pattern in content
                for pattern in [
                    "[x] **이미지 프롬프트**",
                    "[x] 이미지 프롬프트",
                    "[x] **이미지 생성**",
                    "[x] 이미지 생성",
                ]
            )

            videos_approved = any(
                pattern in content
                for pattern in [
                    "[x] **영상 프롬프트**",
                    "[x] 영상 프롬프트",
                    "[x] **영상 생성**",
                    "[x] 영상 생성",
                ]
            )

            # frontmatter에서 채널 목록 확인 (체크박스보다 우선)
            packs_channels = meta.get("packs_channels", [])
            if not packs_channels:
                packs_channels = selected_channels

            # 승인 상태 결정
            status = (
                "approved"
                if (packs_channels or images_approved or videos_approved)
                else meta.get("derivative_status", "pending")
            )

            return {
                "status": status,
                "packs_channels": packs_channels,
                "images_approved": images_approved,
                "videos_approved": videos_approved,
            }
        except FileNotFoundError:
            logger.debug(f"Longform not found for derivative check: {input_id}")
            return {
                "status": "pending",
                "packs_channels": [],
                "images_approved": False,
                "videos_approved": False,
            }

    def _load_longform_content(self, input_id: str) -> dict[str, Any] | None:
        """롱폼 노트 내용 로드"""
        longform_path = f"{self.config.vault.longform}/longform_{input_id}.md"

        try:
            meta, content = self.vault.read_note(longform_path)
            return {
                "longform_title": meta.get("title", ""),
                "longform_body": content,
                "intro": self._extract_section(content, "인트로") or self._extract_section(content, ""),
                "main_content": self._extract_section(content, "핵심 내용"),
                "takeaways": self._extract_section(content, "주요 시사점"),
            }
        except FileNotFoundError:
            return None

    def _generate_packs_for_channels(
        self, item: dict[str, Any], input_content: dict[str, Any], channels: list[str]
    ) -> int:
        """지정된 채널에 대해서만 팩 생성"""
        # None인 경우 기본값 사용
        account_id = item.get("account_id") or "socialbuilders"
        account = self.config.get_account(account_id)
        all_channels = account.get("channels", {})

        # WeeklySlot 컨텍스트 준비
        weekly_context = self._prepare_weekly_context()

        # 계정 컨텍스트 준비
        account_context = self._prepare_account_context(account_id)

        created_count = 0

        for channel in channels:
            if channel not in all_channels:
                logger.warning(f"Channel not configured: {channel}")
                continue

            try:
                channel_config = all_channels[channel]

                # 프롬프트 로더를 통해 채널별 프롬프트 생성
                prompt = self.prompt_loader.get_pack_prompt(
                    channel=channel,
                    input_content=input_content,
                    channel_config=channel_config,
                    account_id=account_id,
                    weekly_context=weekly_context,
                    account_context=account_context,
                )

                text = self.llm.generate(prompt, max_tokens=500)

                # max_length 강제 적용
                max_length = channel_config.get("max_length", 280)
                original_len = len(text)
                if original_len > max_length:
                    logger.warning(
                        f"Pack text exceeded max_length ({original_len}/{max_length}), truncating: {channel}"
                    )
                    text = smart_truncate(text, max_length)

                # 해시태그 추출
                use_hashtags = channel_config.get("hashtags", True)
                hashtags = []
                if use_hashtags:
                    hashtags = [f"#{tag}" for tag in input_content.get("tags", [])[:3]]

                pack_data = {
                    "id": f"pack_{item['input_id']}_{channel}",
                    "source_longform_id": f"longform_{item['input_id']}",
                    "text": text.strip(),
                    "hashtags": hashtags,
                }

                content = self.renderer.render_pack(pack_data, channel, channel_config)

                # 저장
                if not self.dry_run:
                    output_path = f"{self.config.vault.packs}/{channel}/{pack_data['id']}.md"
                    self.vault.ensure_dir(f"{self.config.vault.packs}/{channel}")
                    meta = self._parse_frontmatter(content)
                    body = content.split("---", 2)[2].strip() if content.startswith("---") else content
                    self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
                    logger.info(f"Created pack: {output_path}")

                    self._run_validation_if_enabled(output_path, "Pack")

                created_count += 1  # Increment count after successful creation

            except Exception as e:
                logger.warning(f"Failed to create {channel} pack: {e}")

        return created_count

    def _update_digest_status(self, date: str, input_id: str) -> None:
        """Input 노트의 writing_status 업데이트"""
        input_path = f"{self.config.vault.inbox}/{input_id}.md"

        try:
            meta, content = self.vault.read_note(input_path)

            # writing_status 업데이트
            meta["writing_status"] = "completed"
            meta["generated_at"] = datetime.now().isoformat()

            # 다시 쓰기
            self.vault.write_note(input_path, content, metadata=meta, overwrite=True)
            logger.info(f"Updated writing_status to completed: {input_id}")
        except Exception as e:
            logger.warning(f"Failed to update status for {input_id}: {e}")

    def _prepare_weekly_context(self) -> dict[str, Any] | None:
        """
        WeeklySlot에서 CTA, customer_outcome 등 추출하여 프롬프트 컨텍스트 생성

        Returns:
            weekly_context 딕셔너리 또는 None
        """
        if not self.weekly_slot:
            return None

        return {
            "cta": self.weekly_slot.cta,
            "customer_outcome": self.weekly_slot.customer_outcome,
            "operator_kpi": self.weekly_slot.operator_kpi,
            "pillar_distribution": self.weekly_slot.pillar_distribution,
        }

    def _prepare_account_context(self, account_id: str) -> dict[str, Any] | None:
        """
        계정 정체성에서 target_audience, tone_voice, boundaries 추출

        Args:
            account_id: 계정 ID

        Returns:
            account_context 딕셔너리 또는 None
        """
        identity = get_identity(account_id)
        if not identity:
            return None

        return {
            "target_audience": identity.target_audience or [],
            "tone_voice": identity.tone_voice or {},
            "boundaries": identity.boundaries or [],
        }

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """frontmatter 파싱"""
        import yaml

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1]) or {}
        return {}


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Generate Content - 승인된 콘텐츠로부터 Longform/Packs/Image Prompts 생성"
    )
    parser.add_argument("--date", "-d", help="Digest 날짜 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument(
        "--type",
        "-t",
        nargs="+",
        choices=["longform", "packs", "images", "videos", "all"],
        default=["all"],
        help="생성할 콘텐츠 타입",
    )
    parser.add_argument("--force", "-f", action="store_true", help="이미 생성된 항목도 재생성")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 시뮬레이션")
    parser.add_argument(
        "--auto-all",
        action="store_true",
        help="체크되지 않은 항목도 자동으로 처리 (수동 작업 거부 시)",
    )
    parser.add_argument("--week-of", "-w", help="주간 슬롯 시작일 (YYYY-MM-DD, WeeklySlot 로드용)")

    args = parser.parse_args()

    # 타입 처리
    content_types = args.type
    if "all" in content_types:
        content_types = ["longform", "packs", "images", "videos"]

    # WeeklySlot 로드
    weekly_slot = None
    if args.week_of:
        try:
            weekly_slot = get_weekly_slot(args.week_of)
            if weekly_slot:
                logger.info(f"Loaded WeeklySlot for week: {args.week_of}")
                logger.info(f"  CTA: {weekly_slot.cta}")
                logger.info(f"  Customer Outcome: {weekly_slot.customer_outcome}")
            else:
                logger.warning(f"WeeklySlot not found for: {args.week_of}")
        except Exception as e:
            logger.warning(f"Failed to load WeeklySlot: {e}")

    generator = ContentGenerator(dry_run=args.dry_run, weekly_slot=weekly_slot)

    results = generator.run(
        date=args.date,
        content_types=content_types,
        force=args.force,
        auto_all=args.auto_all,
    )

    print(f"\n{'=' * 50}")
    print(f"Content Generation Results for {results['date']}")
    print(f"{'=' * 50}")
    print(f"Approved Items:      {results['approved_items']}")
    print(f"Longform Created:    {results['longform_created']}")
    print(f"Packs Created:       {results['packs_created']}")
    print(f"Image Prompts:       {results['image_prompts_created']}")
    if results["errors"]:
        print(f"Errors:              {len(results['errors'])}")
        for err in results["errors"]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
