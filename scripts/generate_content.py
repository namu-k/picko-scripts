"""
Generate Content 스크립트
승인된 Digest 항목 → Longform/Packs/Image Prompts 생성
"""

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from picko.config import get_config
from picko.vault_io import VaultIO
from picko.llm_client import get_llm_client
from picko.templates import get_renderer
from picko.logger import setup_logger

logger = setup_logger("generate_content")


class ContentGenerator:
    """콘텐츠 생성기"""
    
    def __init__(self, dry_run: bool = False):
        self.config = get_config()
        self.vault = VaultIO()
        self.llm = get_llm_client()
        self.renderer = get_renderer()
        self.dry_run = dry_run
        
        logger.info("ContentGenerator initialized")
    
    def run(
        self,
        date: str = None,
        content_types: list[str] = None,
        force: bool = False
    ) -> dict:
        """
        콘텐츠 생성 파이프라인 실행
        
        Args:
            date: Digest 날짜 (YYYY-MM-DD)
            content_types: 생성할 타입 (longform, packs, images)
            force: 이미 생성된 항목도 재생성
        
        Returns:
            실행 결과 요약
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if content_types is None:
            content_types = ["longform", "packs", "images"]
        
        logger.info(f"Starting content generation for {date}, types: {content_types}")
        
        results = {
            "date": date,
            "approved_items": 0,
            "longform_created": 0,
            "packs_created": 0,
            "image_prompts_created": 0,
            "errors": []
        }
        
        try:
            # 1. Digest에서 승인된 항목 파싱
            approved_items = self._parse_digest(date)
            results["approved_items"] = len(approved_items)
            logger.info(f"Found {len(approved_items)} approved items")
            
            if not approved_items:
                logger.info("No approved items found")
                return results
            
            # 2. 각 승인 항목에 대해 콘텐츠 생성
            for item in approved_items:
                try:
                    # Input 노트 로드
                    input_content = self._load_input(item["input_id"])
                    if not input_content:
                        continue
                    
                    # 이미 생성된 경우 스킵 (force가 아니면)
                    if not force and item.get("status") == "generated":
                        logger.debug(f"Skipping already generated: {item['input_id']}")
                        continue
                    
                    # Longform 생성
                    if "longform" in content_types:
                        if self._generate_longform(item, input_content):
                            results["longform_created"] += 1
                    
                    # Packs 생성
                    if "packs" in content_types:
                        packs_count = self._generate_packs(item, input_content)
                        results["packs_created"] += packs_count
                    
                    # Image Prompts 생성
                    if "images" in content_types:
                        if self._generate_image_prompt(item, input_content):
                            results["image_prompts_created"] += 1
                    
                    # Digest 상태 업데이트
                    if not self.dry_run:
                        self._update_digest_status(date, item["input_id"])
                    
                except Exception as e:
                    logger.error(f"Failed to process {item.get('input_id')}: {e}")
                    results["errors"].append(str(e))
        
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            results["errors"].append(str(e))
        
        logger.info(f"Content generation complete: {results}")
        return results
    
    # ─────────────────────────────────────────────────────────────
    # Digest 파싱
    # ─────────────────────────────────────────────────────────────
    
    def _parse_digest(self, date: str) -> list[dict]:
        """
        Digest에서 승인된 항목 파싱
        [x] 체크된 항목 추출
        
        Args:
            date: Digest 날짜
        
        Returns:
            승인된 항목 리스트
        """
        digest_path = f"{self.config.vault.digests}/{date}.md"
        
        try:
            meta, content = self.vault.read_note(digest_path)
        except FileNotFoundError:
            logger.warning(f"Digest not found: {digest_path}")
            return []
        
        approved = []
        
        # [x] 패턴 매칭
        # ## [x] Title 또는 ## [ ] Title
        pattern = r'##\s*\[([xX])\]\s*(.+?)(?:\n|$)'
        
        # ID 패턴: **ID**: input_xxx
        id_pattern = r'\*\*ID\*\*:\s*(\S+)'
        
        # Account 패턴: **Account**: xxx
        account_pattern = r'\*\*Account\*\*:\s*(\S+)'
        
        lines = content.split("\n")
        current_item = None
        
        for i, line in enumerate(lines):
            # 새 항목 시작
            match = re.match(pattern, line)
            if match:
                if current_item:
                    approved.append(current_item)
                
                checked = match.group(1).lower() == 'x'
                title = match.group(2).strip()
                
                if checked:
                    current_item = {
                        "title": title,
                        "input_id": None,
                        "account_id": None
                    }
                else:
                    current_item = None
                continue
            
            # 현재 항목의 세부 정보 파싱
            if current_item:
                id_match = re.search(id_pattern, line)
                if id_match:
                    current_item["input_id"] = id_match.group(1)
                
                account_match = re.search(account_pattern, line)
                if account_match:
                    current_item["account_id"] = account_match.group(1)
        
        # 마지막 항목
        if current_item:
            approved.append(current_item)
        
        return [item for item in approved if item.get("input_id")]
    
    def _load_input(self, input_id: str) -> dict | None:
        """Input 노트 로드"""
        input_path = f"{self.config.vault.inbox}/{input_id}.md"
        
        try:
            meta, content = self.vault.read_note(input_path)
            return {
                "id": input_id,
                "meta": meta,
                "content": content,
                "title": meta.get("title", ""),
                "summary": self._extract_section(content, "요약"),
                "key_points": self._extract_list(content, "핵심 포인트"),
                "excerpt": self._extract_section(content, "원문 발췌"),
                "tags": meta.get("tags", [])
            }
        except FileNotFoundError:
            logger.warning(f"Input not found: {input_path}")
            return None
    
    def _extract_section(self, content: str, section_name: str) -> str:
        """마크다운에서 섹션 추출"""
        pattern = rf'##\s*{section_name}\s*\n(.*?)(?=\n##|\Z)'
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
    
    def _generate_longform(self, item: dict, input_content: dict) -> bool:
        """Longform 콘텐츠 생성"""
        logger.info(f"Generating longform for: {item['input_id']}")
        
        # LLM으로 Longform 콘텐츠 생성
        prompt = f"""다음 콘텐츠를 바탕으로 블로그 포스트 형식의 긴 글을 작성해주세요.

제목: {input_content['title']}

원본 요약:
{input_content['summary']}

핵심 포인트:
{chr(10).join('- ' + p for p in input_content['key_points'])}

원문 발췌:
{input_content['excerpt']}

---

다음 형식으로 작성해주세요:

[인트로]
- 독자의 관심을 끄는 도입부 (2-3문장)

[메인 콘텐츠]
- 핵심 내용을 자세히 설명 (3-5 단락)
- 구체적인 예시나 통계 포함

[주요 시사점]
- 독자가 얻을 수 있는 인사이트 (3-4개)

[마무리]
- 행동 촉구 또는 생각거리
"""
        
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
            "tags": input_content.get("tags", [])
        }
        
        content = self.renderer.render_longform(longform_data)
        
        # 저장
        if not self.dry_run:
            output_path = f"{self.config.vault.longform}/{longform_data['id']}.md"
            meta = self._parse_frontmatter(content)
            body = content.split("---", 2)[2].strip() if content.startswith("---") else content
            self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
            logger.info(f"Created longform: {output_path}")
        
        return True
    
    def _parse_generated_sections(self, text: str) -> dict:
        """LLM 생성 텍스트에서 섹션 파싱"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in text.split("\n"):
            # [섹션명] 패턴 확인
            match = re.match(r'\[(.+?)\]', line.strip())
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
    
    def _generate_packs(self, item: dict, input_content: dict) -> int:
        """채널별 패키징 콘텐츠 생성"""
        logger.info(f"Generating packs for: {item['input_id']}")
        
        # 계정 프로필에서 채널 설정 로드
        account_id = item.get("account_id", "socialbuilders")
        account = self.config.get_account(account_id)
        channels = account.get("channels", {})
        
        created_count = 0
        
        for channel, channel_config in channels.items():
            try:
                max_length = channel_config.get("max_length", 280)
                tone = channel_config.get("tone", "casual")
                use_hashtags = channel_config.get("hashtags", True)
                
                # LLM으로 채널별 콘텐츠 생성
                prompt = f"""다음 콘텐츠를 {channel} 채널용으로 변환해주세요.

원본:
제목: {input_content['title']}
요약: {input_content['summary']}

요구사항:
- 최대 {max_length}자
- 톤: {tone}
- 해시태그: {'필요' if use_hashtags else '불필요'}

{channel} 포스트:"""
                
                text = self.llm.generate(prompt, max_tokens=500)
                
                # 해시태그 추출
                hashtags = []
                if use_hashtags:
                    hashtags = [f"#{tag}" for tag in input_content.get("tags", [])[:3]]
                
                pack_data = {
                    "id": f"pack_{item['input_id']}_{channel}",
                    "source_longform_id": f"longform_{item['input_id']}",
                    "text": text.strip(),
                    "hashtags": hashtags
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
    
    def _generate_image_prompt(self, item: dict, input_content: dict) -> bool:
        """이미지 프롬프트 생성"""
        logger.info(f"Generating image prompt for: {item['input_id']}")
        
        # LLM으로 이미지 프롬프트 생성
        prompt = f"""다음 콘텐츠에 어울리는 이미지 프롬프트를 생성해주세요.

제목: {input_content['title']}
요약: {input_content['summary']}
태그: {', '.join(input_content.get('tags', []))}

다음 형식으로 작성해주세요:

[메인 프롬프트]
(DALL-E나 Midjourney에서 사용할 수 있는 상세한 이미지 설명)

[스타일]
(아트 스타일, 예: minimalist, isometric, photorealistic)

[분위기]
(이미지의 전반적인 느낌)

[색상]
(주요 색상 팔레트)"""
        
        response = self.llm.generate(prompt, max_tokens=500)
        sections = self._parse_generated_sections(response)
        
        prompt_data = {
            "id": f"img_{item['input_id']}",
            "source_content_id": item["input_id"],
            "prompt": sections.get("메인 프롬프트", response),
            "style": sections.get("스타일", "modern, clean"),
            "mood": sections.get("분위기", "professional"),
            "colors": sections.get("색상", "brand colors")
        }
        
        content = self.renderer.render_image_prompt(prompt_data)
        
        # 저장
        if not self.dry_run:
            output_path = f"{self.config.vault.images_prompts}/{prompt_data['id']}.md"
            meta = self._parse_frontmatter(content)
            body = content.split("---", 2)[2].strip() if content.startswith("---") else content
            self.vault.write_note(output_path, body, metadata=meta, overwrite=True)
            logger.info(f"Created image prompt: {output_path}")
        
        return True
    
    def _update_digest_status(self, date: str, input_id: str) -> None:
        """Digest 항목 상태 업데이트"""
        # TODO: Digest 파일에서 해당 항목의 status를 generated로 업데이트
        pass
    
    def _parse_frontmatter(self, content: str) -> dict:
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
    parser.add_argument(
        "--date", "-d",
        help="Digest 날짜 (YYYY-MM-DD, 기본: 오늘)"
    )
    parser.add_argument(
        "--type", "-t",
        nargs="+",
        choices=["longform", "packs", "images", "all"],
        default=["all"],
        help="생성할 콘텐츠 타입"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="이미 생성된 항목도 재생성"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="저장 없이 시뮬레이션"
    )
    
    args = parser.parse_args()
    
    # 타입 처리
    content_types = args.type
    if "all" in content_types:
        content_types = ["longform", "packs", "images"]
    
    generator = ContentGenerator(dry_run=args.dry_run)
    
    results = generator.run(
        date=args.date,
        content_types=content_types,
        force=args.force
    )
    
    print(f"\n{'='*50}")
    print(f"Content Generation Results for {results['date']}")
    print(f"{'='*50}")
    print(f"Approved Items:      {results['approved_items']}")
    print(f"Longform Created:    {results['longform_created']}")
    print(f"Packs Created:       {results['packs_created']}")
    print(f"Image Prompts:       {results['image_prompts_created']}")
    if results['errors']:
        print(f"Errors:              {len(results['errors'])}")
        for err in results['errors']:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
