"""
Perplexity 컬렉터
Perplexity Tasks 결과를 지정된 폴더에서 수집
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from picko.collectors import BaseCollector, CollectedItem
from picko.logger import setup_logger

logger = setup_logger("perplexity_collector")


class PerplexityCollector(BaseCollector):
    """
    Perplexity Tasks 결과 수집.
    지정된 입력 폴더에서 .md/.html 파일을 읽어 파싱.
    """

    def __init__(
        self,
        input_dir: Path | str,
        archive_dir: Path | str,
        file_patterns: list[str] | None = None,
    ):
        """
        Args:
            input_dir: Perplexity 결과 드롭 폴더 (예: Inbox/Perplexity)
            archive_dir: 처리 완료 후 이동할 폴더
            file_patterns: 처리할 파일 패턴 (기본: ["*.md", "*.html"])
        """
        self.input_dir = Path(input_dir)
        self.archive_dir = Path(archive_dir)
        self.file_patterns = file_patterns or ["*.md", "*.html"]

        # 디렉토리 생성
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"PerplexityCollector initialized: input={self.input_dir}, archive={self.archive_dir}")

    def collect(self, account_id: str) -> list[CollectedItem]:
        """
        미처리 파일 스캔 → 파싱 → CollectedItem 변환

        Args:
            account_id: 계정 ID

        Returns:
            수집된 아이템 리스트
        """
        items = []

        # 파일 스캔
        files = self._scan_files()
        logger.info(f"Found {len(files)} files to process")

        for file_path in files:
            try:
                item = self._parse_file(file_path, account_id)
                if item:
                    items.append(item)
                    logger.debug(f"Parsed: {file_path.name}")

                    # 처리 완료 파일을 archive로 이동
                    self._archive_file(file_path)

            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

        logger.info(f"Collected {len(items)} items from Perplexity")
        return items

    def _scan_files(self) -> list[Path]:
        """입력 폴더에서 미처리 파일 스캔"""
        files = []
        for pattern in self.file_patterns:
            files.extend(self.input_dir.glob(pattern))
        return sorted(files)

    def _parse_file(self, file_path: Path, account_id: str) -> CollectedItem | None:
        """파일 파싱"""
        suffix = file_path.suffix.lower()

        if suffix == ".md":
            return self._parse_perplexity_md(file_path, account_id)
        elif suffix == ".html":
            return self._parse_perplexity_html(file_path, account_id)
        else:
            logger.warning(f"Unsupported file type: {suffix}")
            return None

    def _parse_perplexity_md(self, file_path: Path, account_id: str) -> CollectedItem:
        """
        Perplexity 결과 마크다운 파싱.

        - 제목: 첫 번째 # 헤딩 또는 파일명
        - 본문: 전체 텍스트
        - 링크: 본문 내 URL 추출
        - 출처: source_type='perplexity'
        """
        content = file_path.read_text(encoding="utf-8")

        # 제목 추출 (첫 번째 # 헤딩)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = file_path.stem

        # 본문 정리 (frontmatter 제거 등)
        body = self._clean_content(content)

        # URL 추출 (첫 번째 외부 링크)
        url_match = re.search(r"https?://[^\s\)]+", body)
        url = url_match.group(0) if url_match else f"perplexity://{file_path.stem}"

        # 본문 내 모든 URL 추출
        all_urls = re.findall(r"https?://[^\s\)]+", body)

        # 발행일 추출 (있는 경우)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", content)
        published_at = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

        return CollectedItem(
            url=url,
            title=title,
            body=body,
            source_id="perplexity",
            source_type="perplexity",
            published_at=published_at,
            category="perplexity",
            metadata={
                "file_name": file_path.name,
                "account_id": account_id,
                "all_urls": all_urls,
                "collected_at": datetime.now().isoformat(),
            },
        )

    def _parse_perplexity_html(self, file_path: Path, account_id: str) -> CollectedItem:
        """Perplexity 결과 HTML 파싱"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not installed, skipping HTML parsing")
            return None

        content = file_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "lxml")

        # 제목 추출
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else file_path.stem

        # 본문 추출
        body_tag = soup.find("main") or soup.find("article") or soup.body
        if body_tag:
            # 스크립트/스타일 제거
            for tag in body_tag.find_all(["script", "style", "nav", "footer"]):
                tag.decompose()
            body = body_tag.get_text(separator="\n", strip=True)
        else:
            body = soup.get_text(separator="\n", strip=True)

        # URL 추출
        url_match = re.search(r"https?://[^\s\)]+", body)
        url = url_match.group(0) if url_match else f"perplexity://{file_path.stem}"

        return CollectedItem(
            url=url,
            title=title,
            body=body[:5000],  # 최대 5000자
            source_id="perplexity",
            source_type="perplexity",
            published_at=datetime.now().strftime("%Y-%m-%d"),
            category="perplexity",
            metadata={
                "file_name": file_path.name,
                "account_id": account_id,
                "collected_at": datetime.now().isoformat(),
            },
        )

    def _clean_content(self, content: str) -> str:
        """콘텐츠 정리 (frontmatter 등 제거)"""
        # YAML frontmatter 제거
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]

        # 연속된 빈 줄 정리
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def _archive_file(self, file_path: Path) -> None:
        """처리 완료 파일을 archive로 이동"""
        # 타임스탬프 추가로 중복 방지
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        archive_path = self.archive_dir / archive_name

        try:
            shutil.move(str(file_path), str(archive_path))
            logger.debug(f"Archived: {file_path.name} -> {archive_path.name}")
        except Exception as e:
            logger.warning(f"Failed to archive {file_path}: {e}")

    def name(self) -> str:
        return "perplexity"

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PerplexityCollector":
        """설정 딕셔너리에서 PerplexityCollector 생성"""
        return cls(
            input_dir=config.get("input_dir", "Inbox/Perplexity"),
            archive_dir=config.get("archive_dir", "Archive/Perplexity"),
            file_patterns=config.get("file_patterns", ["*.md", "*.html"]),
        )
