# picko/orchestrator/batch.py
"""배치 처리 유틸리티 — 대량 아이템을 배치 단위로 처리"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from picko.logger import get_logger

logger = get_logger("orchestrator.batch")


@dataclass
class BatchResult:
    """배치 처리 결과"""

    total_items: int = 0
    total_batches: int = 0
    results: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class BatchProcessor:
    """배치 단위로 아이템을 처리

    대량의 아이템을 지정된 크기의 배치로 분할하여 처리합니다.
    LLM API의 rate limit 대응을 위해 배치 간 대기 시간을 설정할 수 있습니다.

    Example:
        >>> processor = BatchProcessor(size=5, delay_seconds=1.0)
        >>> items = list(range(20))
        >>> results = processor.run(items, lambda batch: sum(batch))
        >>> print(results.total_batches)  # 4
    """

    def __init__(
        self,
        size: int = 10,
        delay_seconds: float = 0,
    ):
        """
        Args:
            size: 배치 크기 (한 번에 처리할 아이템 수)
            delay_seconds: 배치 간 대기 시간 (초)
        """
        self.size = max(1, size)
        self.delay_seconds = max(0, delay_seconds)

    def run(
        self,
        items: list[Any],
        action_fn: Callable[[list[Any]], Any],
    ) -> BatchResult:
        """아이템을 배치 단위로 처리

        Args:
            items: 처리할 아이템 목록
            action_fn: 배치를 처리하는 함수. 배치 아이템 리스트를 받아 결과를 반환.

        Returns:
            BatchResult: 배치 처리 결과
        """
        result = BatchResult(total_items=len(items))

        if not items:
            logger.debug("No items to process")
            return result

        total_batches = (len(items) + self.size - 1) // self.size
        result.total_batches = total_batches

        logger.info(
            f"Starting batch processing: {len(items)} items, "
            f"{total_batches} batches, size={self.size}, delay={self.delay_seconds}s"
        )

        for i in range(0, len(items), self.size):
            batch_num = i // self.size + 1
            batch = items[i : i + self.size]

            logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

            try:
                batch_result = action_fn(batch)
                result.results.append(batch_result)

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                result.results.append(None)

            # 마지막 배치가 아니면 대기
            if self.delay_seconds > 0 and i + self.size < len(items):
                logger.debug(f"Waiting {self.delay_seconds}s before next batch")
                time.sleep(self.delay_seconds)

        logger.info(f"Batch processing complete: {len(result.results)} batches, " f"{len(result.errors)} errors")

        return result

    def run_with_progress(
        self,
        items: list[Any],
        action_fn: Callable[[list[Any]], Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BatchResult:
        """진행 상황 콜백과 함께 배치 처리

        Args:
            items: 처리할 아이템 목록
            action_fn: 배치를 처리하는 함수
            progress_callback: 진행 상황 콜백 (current_batch, total_batches)

        Returns:
            BatchResult: 배치 처리 결과
        """
        result = BatchResult(total_items=len(items))

        if not items:
            return result

        total_batches = (len(items) + self.size - 1) // self.size
        result.total_batches = total_batches

        for i in range(0, len(items), self.size):
            batch_num = i // self.size + 1
            batch = items[i : i + self.size]

            try:
                batch_result = action_fn(batch)
                result.results.append(batch_result)

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {e}"
                logger.error(error_msg)
                result.errors.append(error_msg)
                result.results.append(None)

            # 진행 상황 콜백 호출
            if progress_callback:
                progress_callback(batch_num, total_batches)

            # 대기
            if self.delay_seconds > 0 and i + self.size < len(items):
                time.sleep(self.delay_seconds)

        return result
