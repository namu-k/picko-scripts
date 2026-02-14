"""
Obsidian Vault 읽기/쓰기 모듈
마크다운 노트 CRUD 및 YAML frontmatter 처리
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter

from .config import get_config
from .logger import get_logger

logger = get_logger("vault_io")


class VaultIO:
    """Obsidian Vault 파일 입출력 클래스"""

    def __init__(self, vault_root: str | Path = None):
        """
        Args:
            vault_root: Vault 루트 경로 (기본: config에서 로드)
        """
        if vault_root is None:
            config = get_config()
            vault_root = config.vault.root

        self.root = Path(vault_root)
        if not self.root.exists():
            raise FileNotFoundError(f"Vault root not found: {self.root}")

        logger.debug(f"VaultIO initialized with root: {self.root}")

    def get_path(self, relative_path: str | Path) -> Path:
        """상대 경로를 절대 경로로 변환"""
        return self.root / relative_path

    def ensure_dir(self, dir_path: str | Path) -> Path:
        """디렉토리 생성 (없으면)"""
        full_path = self.get_path(dir_path)
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    # ─────────────────────────────────────────────────────────────
    # 노트 읽기
    # ─────────────────────────────────────────────────────────────

    def read_note(self, path: str | Path) -> tuple[dict, str]:
        """
        마크다운 노트 읽기

        Args:
            path: 노트 경로 (상대 또는 절대)

        Returns:
            (frontmatter dict, content string) 튜플
        """
        full_path = self._resolve_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {full_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        logger.debug(f"Read note: {full_path}")
        return dict(post.metadata), post.content

    def read_frontmatter(self, path: str | Path) -> dict:
        """frontmatter만 읽기"""
        meta, _ = self.read_note(path)
        return meta

    def read_content(self, path: str | Path) -> str:
        """본문만 읽기"""
        _, content = self.read_note(path)
        return content

    # ─────────────────────────────────────────────────────────────
    # 노트 쓰기
    # ─────────────────────────────────────────────────────────────

    def write_note(self, path: str | Path, content: str, metadata: dict = None, overwrite: bool = False) -> Path:
        """
        마크다운 노트 쓰기

        Args:
            path: 노트 경로 (상대 또는 절대)
            content: 본문 내용
            metadata: frontmatter 메타데이터
            overwrite: 기존 파일 덮어쓰기 허용

        Returns:
            저장된 파일 경로
        """
        full_path = self._resolve_path(path)

        if full_path.exists() and not overwrite:
            raise FileExistsError(f"Note already exists: {full_path}")

        # 디렉토리 생성
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # frontmatter 포스트 생성
        post = frontmatter.Post(content)
        if metadata:
            post.metadata = metadata

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        logger.info(f"Wrote note: {full_path}")
        return full_path

    def update_frontmatter(self, path: str | Path, updates: dict, merge: bool = True) -> Path:
        """
        frontmatter 업데이트

        Args:
            path: 노트 경로
            updates: 업데이트할 필드
            merge: True면 기존 필드 유지하며 병합, False면 교체

        Returns:
            저장된 파일 경로
        """
        meta, content = self.read_note(path)

        if merge:
            meta.update(updates)
        else:
            meta = updates

        return self.write_note(path, content, meta, overwrite=True)

    # ─────────────────────────────────────────────────────────────
    # 노트 검색 / 목록
    # ─────────────────────────────────────────────────────────────

    def list_notes(self, dir_path: str | Path, pattern: str = "*.md", recursive: bool = False) -> list[Path]:
        """
        디렉토리 내 노트 목록

        Args:
            dir_path: 검색할 디렉토리
            pattern: 파일 패턴 (기본: *.md)
            recursive: 하위 디렉토리 포함 여부

        Returns:
            노트 경로 리스트
        """
        full_path = self._resolve_path(dir_path)

        if not full_path.exists():
            return []

        if recursive:
            return list(full_path.rglob(pattern))
        else:
            return list(full_path.glob(pattern))

    def find_by_frontmatter(self, dir_path: str | Path, key: str, value: Any, recursive: bool = False) -> list[Path]:
        """
        frontmatter 필드로 노트 검색

        Args:
            dir_path: 검색할 디렉토리
            key: frontmatter 키
            value: 찾을 값
            recursive: 하위 디렉토리 포함 여부

        Returns:
            일치하는 노트 경로 리스트
        """
        results = []
        for note_path in self.list_notes(dir_path, recursive=recursive):
            try:
                meta = self.read_frontmatter(note_path)
                if meta.get(key) == value:
                    results.append(note_path)
            except Exception as e:
                logger.warning(f"Error reading {note_path}: {e}")

        return results

    # ─────────────────────────────────────────────────────────────
    # 노트 이동 / 삭제
    # ─────────────────────────────────────────────────────────────

    def move_note(self, src: str | Path, dest: str | Path) -> Path:
        """
        노트 이동

        Args:
            src: 원본 경로
            dest: 대상 경로

        Returns:
            이동된 파일 경로
        """
        src_path = self._resolve_path(src)
        dest_path = self._resolve_path(dest)

        if not src_path.exists():
            raise FileNotFoundError(f"Source note not found: {src_path}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.rename(dest_path)

        logger.info(f"Moved note: {src_path} -> {dest_path}")
        return dest_path

    def delete_note(self, path: str | Path) -> bool:
        """
        노트 삭제

        Args:
            path: 노트 경로

        Returns:
            삭제 성공 여부
        """
        full_path = self._resolve_path(path)

        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted note: {full_path}")
            return True

        return False

    # ─────────────────────────────────────────────────────────────
    # 내부 링크 처리
    # ─────────────────────────────────────────────────────────────

    def extract_wikilinks(self, content: str) -> list[str]:
        """
        본문에서 [[wikilink]] 추출

        Args:
            content: 마크다운 본문

        Returns:
            링크된 노트 이름 리스트
        """
        # [[Note Name]] 또는 [[Note Name|Alias]] 패턴
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        matches = re.findall(pattern, content)
        return matches

    def resolve_wikilink(self, link_name: str) -> Path | None:
        """
        wikilink를 실제 파일 경로로 해석

        Args:
            link_name: 링크 이름 (확장자 없이)

        Returns:
            파일 경로 또는 None (찾지 못함)
        """
        # 전체 vault에서 검색
        candidates = list(self.root.rglob(f"{link_name}.md"))

        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            logger.warning(f"Multiple notes found for [[{link_name}]]: {candidates}")
            return candidates[0]  # 첫 번째 반환

        return None

    # ─────────────────────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────────────────────

    def _resolve_path(self, path: str | Path) -> Path:
        """경로를 절대 경로로 해석"""
        path = Path(path)
        if path.is_absolute():
            return path
        return self.root / path

    def generate_note_id(self, prefix: str = "") -> str:
        """
        유니크 노트 ID 생성

        Args:
            prefix: ID 접두사

        Returns:
            타임스탬프 기반 ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if prefix:
            return f"{prefix}_{timestamp}"
        return timestamp


# 편의 함수
def get_vault() -> VaultIO:
    """기본 VaultIO 인스턴스 반환"""
    return VaultIO()
