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
