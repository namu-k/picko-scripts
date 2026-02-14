"""
Duplicate Checker 스크립트
임베딩 기반 유사도 검사로 중복 콘텐츠 탐지
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from picko.config import get_config
from picko.embedding import get_embedding_manager
from picko.logger import setup_logger
from picko.vault_io import VaultIO

logger = setup_logger("duplicate_checker")


@dataclass
class DuplicateMatch:
    """중복 매치 결과"""
    content_id: str
    content_path: str
    similarity: float
    title: str
    source: str


@dataclass
class CheckResult:
    """체크 결과"""
    content_id: str
    has_duplicates: bool
    duplicates: list[DuplicateMatch]
    max_similarity: float
    checked_at: str


class DuplicateChecker:
    """중복 콘텐츠 검사기"""

    DEFAULT_THRESHOLD = 0.85  # 유사도 임계값

    def __init__(self, threshold: float = None):
        self.config = get_config()
        self.vault = VaultIO()
        self.embedding_manager = get_embedding_manager()
        self.threshold = threshold or self.DEFAULT_THRESHOLD
        self._cache: dict[str, list[float]] = {}
        logger.info(f"DuplicateChecker initialized (threshold: {self.threshold})")

    def check_content(
        self,
        content_path: str,
        compare_paths: list[str] = None
    ) -> CheckResult:
        """
        단일 콘텐츠 중복 검사

        Args:
            content_path: 검사할 콘텐츠 경로
            compare_paths: 비교 대상 경로들 (None이면 전체 검사)

        Returns:
            체크 결과
        """
        logger.info(f"Checking content: {content_path}")

        try:
            # 콘텐츠 로드
            meta, content = self.vault.read_note(content_path)
            content_id = meta.get("id", Path(content_path).stem)

            # 임베딩 생성
            text = self._extract_text(meta, content)
            embedding = self.embedding_manager.embed(text)

            # 비교 대상 경로 결정
            if compare_paths is None:
                compare_paths = self._get_comparison_targets(content_path)

            # 유사도 검사
            duplicates = self._find_duplicates(
                content_id,
                embedding,
                compare_paths
            )

            max_sim = max([d.similarity for d in duplicates]) if duplicates else 0.0

            return CheckResult(
                content_id=content_id,
                has_duplicates=len(duplicates) > 0,
                duplicates=duplicates,
                max_similarity=max_sim,
                checked_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Failed to check {content_path}: {e}")
            return CheckResult(
                content_id=Path(content_path).stem,
                has_duplicates=False,
                duplicates=[],
                max_similarity=0.0,
                checked_at=datetime.now().isoformat()
            )

    def check_directory(
        self,
        directory: str,
        recursive: bool = False
    ) -> list[CheckResult]:
        """
        디렉토리 내 모든 콘텐츠 중복 검사

        Args:
            directory: 검사할 디렉토리
            recursive: 하위 디렉토리 포함

        Returns:
            체크 결과 리스트
        """
        logger.info(f"Checking directory: {directory}")

        # 캐시 미리 로드
        self._preload_embeddings(directory, recursive)

        results = []
        notes = self.vault.list_notes(directory, recursive=recursive)

        for note_path in notes:
            result = self.check_content(str(note_path))
            results.append(result)

            # 진행률 표시
            if result.has_duplicates:
                print(f"⚠️  Found duplicate: {result.content_id} (max sim: {result.max_similarity:.2f})")

        return results

    def check_pair(
        self,
        path1: str,
        path2: str
    ) -> float:
        """
        두 콘텐츠 간 유사도 계산

        Args:
            path1: 첫 번째 콘텐츠 경로
            path2: 두 번째 콘텐츠 경로

        Returns:
            유사도 (0~1)
        """
        emb1 = self._get_embedding(path1)
        emb2 = self._get_embedding(path2)

        if emb1 is None or emb2 is None:
            return 0.0

        similarity = self.embedding_manager.cosine_similarity(emb1, emb2)
        return similarity

    def _extract_text(self, meta: dict, content: str) -> str:
        """유사도 비교용 텍스트 추출"""
        # 제목 + 요약 + 핵심 포인트 조합
        parts = []

        if title := meta.get("title"):
            parts.append(title)

        # 본문에서 요약 섹션 추출
        if "## 요약" in content:
            summary_start = content.index("## 요약")
            summary_end = content.find("##", summary_start + 1)
            if summary_end == -1:
                summary_end = len(content)
            summary = content[summary_start:summary_end].replace("## 요약", "").strip()
            parts.append(summary)

        # 본문에서 핵심 포인트 추출
        if "## 핵심 포인트" in content:
            points_start = content.index("## 핵심 포인트")
            points_end = content.find("##", points_start + 1)
            if points_end == -1:
                points_end = len(content)
            points = content[points_start:points_end].replace("## 핵심 포인트", "").strip()
            parts.append(points)

        return " | ".join(parts)

    def _get_comparison_targets(self, exclude_path: str) -> list[str]:
        """비교 대상 경로들 가져오기"""
        targets = []

        # Inbox/Inputs에서 모든 항목
        notes = self.vault.list_notes("Inbox/Inputs", recursive=False)

        for note_path in notes:
            if str(note_path) != exclude_path:
                targets.append(str(note_path))

        # Content/Longform도 포함
        longform_notes = self.vault.list_notes("Content/Longform", recursive=False)
        for note_path in longform_notes:
            if str(note_path) != exclude_path:
                targets.append(str(note_path))

        return targets

    def _find_duplicates(
        self,
        content_id: str,
        embedding: list[float],
        compare_paths: list[str]
    ) -> list[DuplicateMatch]:
        """중복 항목 찾기"""
        duplicates = []

        for compare_path in compare_paths:
            try:
                compare_emb = self._get_embedding(compare_path)
                if compare_emb is None:
                    continue

                similarity = self.embedding_manager.cosine_similarity(embedding, compare_emb)

                if similarity >= self.threshold:
                    meta = self.vault.read_frontmatter(compare_path)

                    duplicates.append(DuplicateMatch(
                        content_id=meta.get("id", Path(compare_path).stem),
                        content_path=compare_path,
                        similarity=similarity,
                        title=meta.get("title", "Untitled"),
                        source=meta.get("source", "unknown")
                    ))

            except Exception as e:
                logger.debug(f"Error comparing {compare_path}: {e}")

        # 유사도 내림차순 정렬
        duplicates.sort(key=lambda d: d.similarity, reverse=True)
        return duplicates

    def _get_embedding(self, path: str) -> list[float] | None:
        """경로의 임베딩 가져오기 (캐시 활용)"""
        if path in self._cache:
            return self._cache[path]

        try:
            meta, content = self.vault.read_note(path)
            text = self._extract_text(meta, content)
            embedding = self.embedding_manager.embed(text)
            self._cache[path] = embedding
            return embedding
        except Exception as e:
            logger.debug(f"Error getting embedding for {path}: {e}")
            return None

    def _preload_embeddings(self, directory: str, recursive: bool):
        """임베딩 캐시 미리 로드"""
        notes = self.vault.list_notes(directory, recursive=recursive)

        for note_path in notes:
            self._get_embedding(str(note_path))

        logger.debug(f"Preloaded {len(self._cache)} embeddings")


def print_result(result: CheckResult, verbose: bool = False):
    """결과 출력"""
    if result.has_duplicates:
        print(f"\n⚠️  {result.content_id} - Found {len(result.duplicates)} duplicate(s)")

        for dup in result.duplicates:
            print(f"   📄 {dup.title[:40]}...")
            print(f"      ID: {dup.content_id}")
            print(f"      Similarity: {dup.similarity:.1%}")
            if verbose:
                print(f"      Path: {dup.content_path}")
                print(f"      Source: {dup.source}")
    else:
        print(f"✅ {result.content_id} - No duplicates (max similarity: {result.max_similarity:.1%})")


def main():
    """CLI 엔트리포인트"""
    parser = argparse.ArgumentParser(
        description="Duplicate Checker - 임베딩 기반 중복 콘텐츠 탐지"
    )

    parser.add_argument(
        "--content", "-c",
        help="검사할 단일 콘텐츠 경로"
    )
    parser.add_argument(
        "--directory", "-d",
        help="검사할 디렉토리 경로"
    )
    parser.add_argument(
        "--pair",
        nargs=2,
        metavar=("PATH1", "PATH2"),
        help="두 콘텐츠 간 유사도 비교"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.85,
        help="유사도 임계값 (0~1, 기본: 0.85)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="하위 디렉토리 포함"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 출력"
    )

    args = parser.parse_args()

    checker = DuplicateChecker(threshold=args.threshold)

    if args.pair:
        # 두 콘텐츠 비교
        path1, path2 = args.pair
        similarity = checker.check_pair(path1, path2)

        print(f"\n{'='*60}")
        print(f"Similarity Comparison")
        print(f"{'='*60}\n")
        print(f"Path 1: {path1}")
        print(f"Path 2: {path2}")
        print(f"\nSimilarity: {similarity:.1%}")

        if similarity >= args.threshold:
            print(f"⚠️  Above threshold ({args.threshold:.1%}) - Potential duplicate!")
        else:
            print(f"✅ Below threshold ({args.threshold:.1%}) - Likely unique")

    elif args.content:
        # 단일 콘텐츠 검사
        result = checker.check_content(args.content)
        print_result(result, verbose=args.verbose)

    elif args.directory:
        # 디렉토리 검사
        results = checker.check_directory(args.directory, recursive=args.recursive)

        print(f"\n{'='*60}")
        print(f"Duplicate Check Results: {args.directory}")
        print(f"{'='*60}\n")

        duplicate_count = sum(1 for r in results if r.has_duplicates)
        print(f"Total checked: {len(results)}")
        print(f"Duplicates found: {duplicate_count}")
        print(f"Unique: {len(results) - duplicate_count}")

        if args.verbose:
            for result in results:
                print_result(result, verbose=True)

    else:
        # 기본: Inbox/Inputs 검사
        results = checker.check_directory("Inbox/Inputs", recursive=False)

        print(f"\n{'='*60}")
        print(f"Duplicate Check Results: Inbox/Inputs")
        print(f"{'='*60}\n")

        for result in results:
            print_result(result, verbose=args.verbose)

        duplicate_count = sum(1 for r in results if r.has_duplicates)
        print(f"\n{'='*60}")
        print(f"Summary: {duplicate_count} potential duplicate(s) found")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
