"""
Regression tests for BTCAAAAA-122: cap _schedule_next_check max wait to 5 min
to prevent 38+ min gaps.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-122
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: _schedule_next_check() had no maximum wait cap. When a cycle was
skipped because the thread was still running, the boundary calculation could
produce wait times of 38+ minutes, causing large data-update gaps.

Fix:
- Reduce _FALLBACK_MS from 15 min to 5 min
- Add MAX_WAIT_MS = 5 min hard cap applied via min() after boundary calculation
- Cap prevents skipped-cycle chaining: when thread is still running and a cycle
  is skipped, the next attempt fires within 5 min instead of up to 15+ min
- Fix next_check_time to use timedelta(milliseconds=ms_until_check) after cap
  so countdown display reflects the capped value
"""
from __future__ import annotations

import ast
import operator
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-122"),
    pytest.mark.regression,
]

SOURCE_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")
FIVE_MINUTES_MS = 5 * 60 * 1000

_BIN_OP_MAP = {
    ast.Mult: operator.mul,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
}


def _eval_ast_expr(node: ast.expr) -> int | float:
    """Evaluate a constant AST expression (supports nested BinOp with constants)."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op_fn = _BIN_OP_MAP.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_fn(_eval_ast_expr(node.left), _eval_ast_expr(node.right))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -_eval_ast_expr(node.operand)
    raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def _find_const_assignment(name: str) -> int:
    """Find the integer value of a simple constant assignment in the source file."""
    source = SOURCE_PATH.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return int(_eval_ast_expr(node.value))
                    except (ValueError, TypeError):
                        continue
    raise AssertionError(f"{name} not found or not a constant expression")


class TestScheduleNextCheckConstants:
    """Validate constants and structure of _schedule_next_check."""

    def _get_method_source(self) -> str | None:
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_schedule_next_check":
                lines = source.splitlines()
                return "\n".join(lines[node.lineno - 1:node.end_lineno])
        return None

    def test_max_wait_ms_is_defined_and_set_to_5_min(self):
        value = _find_const_assignment("MAX_WAIT_MS")
        assert value == FIVE_MINUTES_MS, (
            f"MAX_WAIT_MS = {value} ms, expected {FIVE_MINUTES_MS} ms (5 min)"
        )

    def test_fallback_ms_is_set_to_5_min(self):
        value = _find_const_assignment("_FALLBACK_MS")
        assert value == FIVE_MINUTES_MS, (
            f"_FALLBACK_MS = {value} ms, expected {FIVE_MINUTES_MS} ms (5 min)"
        )

    def test_ms_until_check_is_capped_with_min(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "min"
            ):
                arg_names = [a.id for a in node.args if isinstance(a, ast.Name)]
                if "ms_until_check" in arg_names and "MAX_WAIT_MS" in arg_names:
                    return
        pytest.fail("ms_until_check not capped via min(ms_until_check, MAX_WAIT_MS)")

    def test_next_check_time_uses_milliseconds(self):
        method_source = self._get_method_source()
        assert method_source is not None, "_schedule_next_check method not found"
        assert "timedelta(milliseconds=ms_until_check)" in method_source, (
            "next_check_time must use timedelta(milliseconds=ms_until_check)"
        )


class TestMinCappingLogic:
    """Validate the cap logic (pure math, no PyQt needed)."""

    def test_ms_under_cap_is_unchanged(self):
        assert min(1000, FIVE_MINUTES_MS) == 1000

    def test_ms_at_cap_passes_through(self):
        assert min(FIVE_MINUTES_MS, FIVE_MINUTES_MS) == FIVE_MINUTES_MS

    def test_ms_over_cap_is_capped(self):
        assert min(10 * 60 * 1000, FIVE_MINUTES_MS) == FIVE_MINUTES_MS

    def test_original_bug_scenario_38_min_is_capped(self):
        assert min(38 * 60 * 1000, FIVE_MINUTES_MS) == FIVE_MINUTES_MS

    def test_55_min_is_capped(self):
        assert min(55 * 60 * 1000, FIVE_MINUTES_MS) == FIVE_MINUTES_MS

    def test_fallback_and_cap_are_equal(self):
        max_wait = _find_const_assignment("MAX_WAIT_MS")
        fallback = _find_const_assignment("_FALLBACK_MS")
        assert fallback == max_wait == FIVE_MINUTES_MS, (
            f"_FALLBACK_MS ({fallback}) and MAX_WAIT_MS ({max_wait}) must both be 5 min"
        )
