"""
Regression tests for BTCAAAAA-26132: Sliding data window root cause — floor
end_date to midnight UTC in _on_quick_preview.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-26132
Component: src/strategy_builder/ui/strategy_builder_main_window.py
Root cause: end_date in _on_quick_preview() was computed as
datetime.now(timezone.utc) without the midnight floor.  This caused the
30-day preview data window to slide forward by wall-clock time on every
invocation, producing inconsistent backtest windows across the same day.

Fix: floor end_date to UTC midnight (00:00:00.000000) matching the pattern
from BacktestConfigPanel.get_config() (BTCAAAAA-25396).
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from datetime import datetime, timezone

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-26132"),
    pytest.mark.regression,
]


def _get_preview_source() -> list[str]:
    """Return the source lines of _on_quick_preview."""
    from src.strategy_builder.ui.strategy_builder_main_window import (
        StrategyBuilderMainWindow,
    )

    source = inspect.getsource(StrategyBuilderMainWindow._on_quick_preview)
    return source.splitlines()


class TestMidnightFloorInPreviewQuick:
    """Verifies _on_quick_preview floors end_date to midnight UTC."""

    def test_end_date_assignment_contains_midnight_floor(self):
        """end_date = ... must contain .replace(hour=0, minute=0, second=0, microsecond=0)."""
        lines = _get_preview_source()
        matching = [
            l for l in lines
            if "end_date" in l and "datetime.now" in l
        ]
        assert len(matching) >= 1, (
            "No end_date = datetime.now(...) assignment found in _on_quick_preview"
        )
        line = matching[0]
        assert "replace(hour=0, minute=0, second=0, microsecond=0)" in line, (
            f"end_date assignment missing midnight floor:\n  {line.strip()}"
        )

    def test_end_date_midnight_utc_invariant(self):
        """end_date produced by the midnight-floor idiom is
        00:00:00.000000 UTC on today's date."""
        end_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert end_date.tzinfo is not None
        assert end_date.tzinfo is timezone.utc
        assert end_date.hour == 0
        assert end_date.minute == 0
        assert end_date.second == 0
        assert end_date.microsecond == 0

    def test_end_date_is_ast_parsable_and_function_scoped(self):
        """Verify the end_date assignment is in the function body (not a
        module-level constant that was already evaluated)."""
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )

        source = textwrap.dedent(
            inspect.getsource(StrategyBuilderMainWindow._on_quick_preview)
        )
        tree = ast.parse(source)

        assigns = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "end_date"
                for t in n.targets
            )
        ]
        assert len(assigns) == 1, (
            f"Expected exactly 1 end_date assignment, found {len(assigns)}"
        )

        call = assigns[0].value
        assert isinstance(call, ast.Call), "RHS of end_date= must be a Call"
        assert isinstance(call.func, ast.Attribute), "RHS must be an attribute chain"
        assert call.func.attr == "replace", (
            f"RHS must end with .replace(...), got .{call.func.attr}"
        )

        keywords = {kw.arg: kw for kw in call.keywords}
        for expected_kw in ("hour", "minute", "second", "microsecond"):
            assert expected_kw in keywords, (
                f"Missing keyword {expected_kw} in .replace(...)"
            )
            assert isinstance(keywords[expected_kw].value, ast.Constant)
            assert keywords[expected_kw].value.value == 0, (
                f"{expected_kw} must be 0"
            )

    def test_preview_config_end_date_key_present(self):
        """Backtest config dict must reference the floored end_date."""
        lines = _get_preview_source()
        source = "\n".join(lines)
        assert "'end_date': end_date" in source, (
            "backtest_config dict must contain 'end_date': end_date"
        )
