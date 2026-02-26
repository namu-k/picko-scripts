"""
오케스트레이션 배치 처리 테스트
BatchProcessor, embedding.check_duplicate 액션, WorkflowEngine 배치 처리
"""

import time
from unittest.mock import MagicMock, patch

from picko.orchestrator import BatchProcessor
from picko.orchestrator.actions import ActionRegistry, ActionResult
from picko.orchestrator.default_actions import register_default_actions


class TestBatchProcessor:
    """BatchProcessor 테스트"""

    def test_init_defaults(self):
        """기본값 초기화"""
        processor = BatchProcessor()
        assert processor.size == 10
        assert processor.delay_seconds == 0

    def test_init_custom(self):
        """커스텀 값 초기화"""
        processor = BatchProcessor(size=5, delay_seconds=2.0)
        assert processor.size == 5
        assert processor.delay_seconds == 2.0

    def test_init_min_size(self):
        """최소 size 검증"""
        processor = BatchProcessor(size=0)
        assert processor.size == 1

        processor = BatchProcessor(size=-5)
        assert processor.size == 1

    def test_run_empty_items(self):
        """빈 아이템 목록 처리"""
        processor = BatchProcessor()
        result = processor.run([], lambda x: x)

        assert result.total_items == 0
        assert result.total_batches == 0
        assert result.success

    def test_run_single_batch(self):
        """단일 배치 처리"""
        processor = BatchProcessor(size=10)
        items = list(range(5))

        result = processor.run(items, lambda batch: sum(batch))

        assert result.total_items == 5
        assert result.total_batches == 1
        assert result.results == [10]  # 0+1+2+3+4
        assert result.success

    def test_run_multiple_batches(self):
        """다중 배치 처리"""
        processor = BatchProcessor(size=3)
        items = list(range(10))

        result = processor.run(items, lambda batch: len(batch))

        assert result.total_items == 10
        assert result.total_batches == 4  # 3+3+3+1
        assert result.results == [3, 3, 3, 1]
        assert result.success

    def test_run_with_delay(self):
        """delay가 있는 배치 처리"""
        processor = BatchProcessor(size=2, delay_seconds=0.1)
        items = list(range(6))

        start = time.time()
        result = processor.run(items, lambda batch: sum(batch))
        elapsed = time.time() - start

        assert result.total_batches == 3
        # 3개 배치 = 2번 대기 = 최소 0.2초
        assert elapsed >= 0.2

    def test_run_with_errors(self):
        """에러 처리"""
        processor = BatchProcessor(size=2)

        def failing_action(batch):
            if sum(batch) > 5:
                raise ValueError("Too large")
            return sum(batch)

        items = list(range(8))  # [0,1], [2,3], [4,5], [6,7]
        result = processor.run(items, failing_action)

        assert result.total_batches == 4
        assert len(result.errors) == 2  # [4,5]=9, [6,7]=13
        assert not result.success

    def test_run_with_progress_callback(self):
        """진행 상황 콜백"""
        processor = BatchProcessor(size=2)
        items = list(range(6))
        progress_calls = []

        result = processor.run_with_progress(
            items,
            lambda batch: sum(batch),
            lambda current, total: progress_calls.append((current, total)),
        )

        assert len(progress_calls) == 3
        assert progress_calls == [(1, 3), (2, 3), (3, 3)]
        assert result.total_batches == 3


class TestEmbeddingCheckDuplicate:
    """embedding.check_duplicate 액션 테스트"""

    def test_action_registered(self):
        """액션 등록 확인"""
        registry = ActionRegistry()
        register_default_actions(registry)

        assert "embedding.check_duplicate" in registry._actions

    @patch("picko.embedding.get_embedding_manager")
    def test_check_duplicate_basic(self, mock_get_embedding_manager):
        """기본 중복 검사"""
        # Mock embedding manager
        mock_manager = MagicMock()
        mock_manager.embed.side_effect = lambda text: [0.1] * 384  # Dummy embedding
        mock_get_embedding_manager.return_value = mock_manager

        registry = ActionRegistry()
        register_default_actions(registry)

        # 텍스트 리스트로 테스트
        texts = ["Hello world", "Hello world", "Different text"]
        result = registry.execute(
            "embedding.check_duplicate",
            {"source": texts, "threshold": 0.9},
        )

        assert result.success
        assert "duplicates" in result.outputs
        assert "unique" in result.outputs
        assert result.outputs["total"] == 3

    @patch("picko.embedding.get_embedding_manager")
    def test_check_duplicate_all_unique(self, mock_get_embedding_manager):
        """모든 항목이 유니크"""
        import numpy as np

        mock_manager = MagicMock()
        # 각 텍스트마다 다른 임베딩 반환
        mock_manager.embed.side_effect = lambda text: np.random.rand(384).tolist()
        mock_get_embedding_manager.return_value = mock_manager

        registry = ActionRegistry()
        register_default_actions(registry)

        texts = ["Text 1", "Text 2", "Text 3"]
        result = registry.execute(
            "embedding.check_duplicate",
            {"source": texts, "threshold": 0.99},  # 매우 높은 임계값
        )

        assert result.success
        assert result.outputs["unique_count"] == 3
        assert result.outputs["duplicate_count"] == 0


class TestWorkflowEngineBatch:
    """WorkflowEngine 배치 처리 테스트"""

    def test_parse_delay(self):
        """delay 파싱"""
        from picko.orchestrator.engine import WorkflowEngine

        engine = WorkflowEngine(vault_adapter=MagicMock(), action_registry=MagicMock())

        assert engine._parse_delay("10s") == 10.0
        assert engine._parse_delay("1m") == 60.0
        assert engine._parse_delay("500ms") == 0.5
        assert engine._parse_delay("0") == 0.0
        assert engine._parse_delay("") == 0.0
        assert engine._parse_delay("invalid") == 0.0

    @patch("picko.orchestrator.batch.BatchProcessor")
    def test_execute_step_with_batch(self, mock_batch_processor):
        """배치 step 실행"""
        from picko.orchestrator.engine import WorkflowEngine

        # Mock setup
        mock_registry = MagicMock()
        mock_registry.execute.return_value = ActionResult(success=True, outputs={"result": "ok"})

        mock_vault = MagicMock()

        mock_bp_instance = MagicMock()
        mock_bp_instance.run.return_value = MagicMock(
            total_items=10,
            total_batches=2,
            results=[{"success": True, "outputs": {}, "error": None}] * 2,
        )
        mock_batch_processor.return_value = mock_bp_instance

        engine = WorkflowEngine(vault_adapter=mock_vault, action_registry=mock_registry)

        step_def = {
            "name": "test_batch",
            "action": "test.action",
            "args": {"param": "value"},
            "batch": {
                "source": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "size": 5,
                "delay": "1s",
            },
        }

        result = engine._execute_step_with_batch(step_def)

        assert result.name == "test_batch"
        assert result.success
        assert "batch_results" in result.outputs
