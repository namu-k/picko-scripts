"""
주제 탐색 스크립트
승인된 Input 노트를 바탕으로 주제 확장, 인사이트 도출
"""

import argparse
import re
from datetime import datetime

from picko.config import get_config
from picko.llm_client import get_summary_client
from picko.logger import setup_logger
from picko.prompt_loader import get_prompt_loader
from picko.templates import get_renderer
from picko.vault_io import VaultIO

logger = setup_logger("explore_topic")


class TopicExplorer:
    """주제 탐색기"""

    def __init__(self, dry_run: bool = False):
        self.config = get_config()
        self.vault = VaultIO()
        # 탐색은 요약용 LLM 사용 (비용 효율적)
        self.llm = get_summary_client()
        self.prompt_loader = get_prompt_loader()
        self.renderer = get_renderer()
        self.dry_run = dry_run

        logger.info("TopicExplorer initialized")

    def run(self, date: str | None = None, input_id: str | None = None, force: bool = False) -> dict:
        """
        주제 탐색 실행

        Args:
            date: Digest 날짜 (YYYY-MM-DD)
            input_id: 특정 Input ID만 처리
            force: 이미 탐색된 항목도 재탐색

        Returns:
            실행 결과 요약
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Starting topic exploration for {date}")

        results = {
            "date": date,
            "explored_count": 0,
            "skipped_count": 0,
            "errors": [],
        }

        try:
            # 탐색 대상 수집
            targets = self._collect_targets(date, input_id)
            logger.info(f"Found {len(targets)} targets to explore")

            for target in targets:
                self._process_target(target, force, results)

        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            results["errors"].append(str(e))

        logger.info(f"Exploration complete: {results}")
        return results

    def _collect_targets(self, date: str, input_id: str | None) -> list[dict]:
        """탐색 대상 수집"""
        if input_id:
            # 특정 ID만 처리
            return [{"input_id": input_id, "account_id": None}]

        # Digest에서 승인된 항목 파싱
        return self._parse_digest_for_exploration(date)

    def _parse_digest_for_exploration(self, date: str) -> list[dict]:
        """Digest에서 탐색 대상 파싱"""
        digest_path = f"{self.config.vault.digests}/{date}.md"

        try:
            meta, content = self.vault.read_note(digest_path)
        except FileNotFoundError:
            logger.warning(f"Digest not found: {digest_path}")
            return []

        targets = []
        checkbox_pattern = r"##\s*\[([xX ])\]\s*(.+?)(?:\n|$)"
        id_pattern = r"\*\*ID\*\*:\s*(\S+)"

        current_item = None

        for line in content.split("\n"):
            checkbox_match = re.match(checkbox_pattern, line)
            if checkbox_match:
                if current_item and current_item.get("input_id"):
                    targets.append(current_item)
                checkbox = checkbox_match.group(1).strip()
                title = checkbox_match.group(2).strip()
                if checkbox.lower() == "x":
                    current_item = {"input_id": None, "account_id": None, "title": title}
                else:
                    current_item = None
            elif current_item:
                id_match = re.search(id_pattern, line)
                if id_match:
                    current_item["input_id"] = id_match.group(1)

        # 마지막 항목 추가
        if current_item and current_item.get("input_id"):
            targets.append(current_item)

        return targets

    def _process_target(self, target: dict, force: bool, results: dict) -> None:
        """단일 탐색 대상 처리"""
        input_id = target["input_id"]

        try:
            # 이미 탐색되었는지 확인
            exploration_path = f"{self.config.vault.explorations}/explore_{input_id}.md"
            if not force and self._exploration_exists(exploration_path):
                logger.debug(f"Skipping already explored: {input_id}")
                results["skipped_count"] += 1
                return

            # Input 노트 로드
            input_content = self._load_input(input_id)
            if not input_content:
                return

            # writing_status 확인
            if input_content.get("writing_status") in ["manual", "completed"]:
                logger.debug(f"Skipping {input_content.get('writing_status')} item: {input_id}")
                results["skipped_count"] += 1
                return

            # 탐색 실행
            exploration_data = self._explore(input_content, target.get("account_id"))

            # 탐색 노트 저장
            if not self.dry_run:
                self._save_exploration(exploration_data, input_id)
                logger.info(f"Created exploration: {exploration_path}")

            results["explored_count"] += 1

        except Exception as e:
            logger.error(f"Failed to explore {input_id}: {e}")
            results["errors"].append(f"{input_id}: {e}")

    def _exploration_exists(self, path: str) -> bool:
        """탐색 노트 존재 여부 확인"""
        try:
            self.vault.read_note(path)
            return True
        except FileNotFoundError:
            return False

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
                "tags": meta.get("tags", []),
                "writing_status": meta.get("writing_status", "pending"),
            }
        except FileNotFoundError:
            logger.warning(f"Input not found: {input_path}")
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

    def _explore(self, input_content: dict, account_id: str | None) -> dict:
        """주제 탐색 실행"""
        logger.info(f"Exploring topic: {input_content['id']}")

        # 프롬프트 생성
        prompt = self.prompt_loader.get_exploration_prompt(input_content, account_id=account_id)

        # LLM 호출
        response = self.llm.generate(prompt, max_tokens=2000)

        # 섹션 파싱
        sections = self._parse_exploration_sections(response)

        return {
            "id": f"explore_{input_content['id']}",
            "source_input_id": input_content["id"],
            "title": input_content["title"],
            "topic_expansion": sections.get("주제 확장", ""),
            "related_discussions": sections.get("관련 논의와 반론", ""),
            "reader_insights": sections.get("독자 인사이트", ""),
            "writing_guide": sections.get("롱폼 작성 가이드", ""),
            "tags": input_content.get("tags", []),
        }

    def _parse_exploration_sections(self, text: str) -> dict:
        """탐색 결과에서 섹션 파싱"""
        sections = {}
        current_section = None
        current_content = []

        for line in text.split("\n"):
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

    def _save_exploration(self, data: dict, input_id: str) -> None:
        """탐색 노트 저장"""
        # 탐색 디렉토리 확인
        explorations_dir = self.config.vault.explorations
        if explorations_dir is None:
            # 기본 경로 사용
            explorations_dir = f"{self.config.vault.inbox}/../Explorations"

        self.vault.ensure_dir(explorations_dir)

        # 템플릿 렌더링
        content = self.renderer.render_exploration(data)

        # 저장
        output_path = f"{explorations_dir}/explore_{input_id}.md"
        meta = self._parse_frontmatter(content)
        body = content.split("---", 2)[2].strip() if content.startswith("---") else content
        self.vault.write_note(output_path, body, metadata=meta, overwrite=True)

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
    parser = argparse.ArgumentParser(description="주제 탐색 - Input 노트에서 주제 확장 및 인사이트 도출")
    parser.add_argument("--date", "-d", help="Digest 날짜 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument("--input", "-i", help="특정 Input ID만 탐색")
    parser.add_argument("--force", "-f", action="store_true", help="이미 탐색된 항목도 재탐색")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 시뮬레이션")

    args = parser.parse_args()

    explorer = TopicExplorer(dry_run=args.dry_run)
    results = explorer.run(date=args.date, input_id=args.input, force=args.force)

    print(f"\n{'=' * 50}")
    print(f"Topic Exploration Results for {results['date']}")
    print(f"{'=' * 50}")
    print(f"Explored:    {results['explored_count']}")
    print(f"Skipped:     {results['skipped_count']}")
    if results["errors"]:
        print(f"Errors:      {len(results['errors'])}")
        for err in results["errors"]:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
