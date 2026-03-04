# tests/test_orchestrator_expr.py
"""표현식 평가기 테스트"""

from picko.orchestrator.expr import ExprEvaluator


class TestExprEvaluator:
    def test_vault_count_expression(self):
        """${{ vault.count(...) > 0 }} 평가"""
        mock_vault = type(
            "V",
            (),
            {
                "count": lambda self, path, f: 3,
            },
        )()

        evaluator = ExprEvaluator(vault_adapter=mock_vault, step_outputs={})
        result = evaluator.evaluate("${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}")
        assert result is True

    def test_vault_count_zero(self):
        mock_vault = type(
            "V",
            (),
            {
                "count": lambda self, path, f: 0,
            },
        )()

        evaluator = ExprEvaluator(vault_adapter=mock_vault, step_outputs={})
        result = evaluator.evaluate("${{ vault.count('Inbox/Inputs', 'writing_status=auto_ready') > 0 }}")
        assert result is False

    def test_step_output_reference(self):
        evaluator = ExprEvaluator(
            vault_adapter=None,
            step_outputs={"collect": {"items": ["a", "b", "c"]}},
        )
        result = evaluator.evaluate("${{ steps.collect.outputs.items }}")
        assert result == ["a", "b", "c"]

    def test_plain_string_passthrough(self):
        evaluator = ExprEvaluator(vault_adapter=None, step_outputs={})
        result = evaluator.evaluate("just a string")
        assert result == "just a string"

    def test_vault_list_expression(self):
        mock_vault = type(
            "V",
            (),
            {
                "list": lambda self, path, f: ["/a.md", "/b.md"],
            },
        )()

        evaluator = ExprEvaluator(vault_adapter=mock_vault, step_outputs={})
        result = evaluator.evaluate("${{ vault.list('Content/Longform', 'derivative_status=approved') }}")
        assert result == ["/a.md", "/b.md"]

    def test_contains_topic_operator(self):
        evaluator = ExprEvaluator(
            vault_adapter=None,
            step_outputs={"collect": {"topics": ["AI", "startup", "tools"]}},
        )

        result = evaluator.evaluate("${{ contains_topic(steps.collect.outputs.topics, 'ai') }}")
        assert result is True

    def test_score_range_operator(self):
        evaluator = ExprEvaluator(
            vault_adapter=None,
            step_outputs={"quality": {"score": 0.86}},
        )

        in_range = evaluator.evaluate("${{ score_range(steps.quality.outputs.score, 0.8, 0.9) }}")
        out_of_range = evaluator.evaluate("${{ score_range(steps.quality.outputs.score, 0.9, 1.0) }}")
        assert in_range is True
        assert out_of_range is False

    def test_has_quality_flag_operator(self):
        evaluator = ExprEvaluator(
            vault_adapter=None,
            step_outputs={"verify": {"flags": {"needs_review": True, "safe": False}}},
        )

        has_flag = evaluator.evaluate("${{ has_quality_flag(steps.verify.outputs.flags, 'needs_review') }}")
        missing_flag = evaluator.evaluate("${{ has_quality_flag(steps.verify.outputs.flags, 'approved') }}")
        assert has_flag is True
        assert missing_flag is False
