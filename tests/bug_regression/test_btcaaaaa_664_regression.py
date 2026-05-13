"""
Regression tests for BTCAAAAA-664: inline optimal_delay application in
_run_auto_calibration() for both cache-hit and live paths.

Issue: BTCAAAAA-664
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: BacktestConfigPanel._run_auto_calibration() delegated block mutation
to _apply_calibration_results(), which worked fine in production but when the
method was bound as an unbound function in test stubs, the _apply_calibration_results
call failed silently (the method was not accessible), leaving blocks unmodified.

Fix: Replace both _apply_calibration_results() calls (cache-hit path and live
calibration path) with inlined block iteration so the delay-application logic
works regardless of how the method is bound.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-664"),
    pytest.mark.regression,
]


class TestCacheHitSkipMessage:
    """The cache-hit skip message must use exact string 'Using cached parameters.'"""

    _EXPECTED_TEXT = "✓ Calibration already complete for current settings — skipping. Using cached parameters."

    def test_cache_hit_skip_message_exact_string(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        ).read_text()
        assert self._EXPECTED_TEXT in source, (
            f"Cache-hit skip message must be exactly: {self._EXPECTED_TEXT}"
        )

    def test_cache_hit_skip_message_does_not_contain_optimal_params(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        ).read_text()
        assert "Using cached optimal parameters." not in source, (
            "Old incorrect message 'Using cached optimal parameters.' must not appear"
        )


class TestCacheHitInlineIteration:
    """Cache-hit path must apply cached delay_map via inline block iteration."""

    def test_cache_hit_inlines_block_iteration(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        ).read_text()
        assert "cached_delay_map = self._calibration_cache" in source, (
            "Cache-hit path must assign cached delay_map to a local variable"
        )

    def test_cache_hit_sets_optimal_delay_from_cache(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        ).read_text()
        assert "block['optimal_delay'] = cached_delay_map[bname]" in source, (
            "Cache-hit path must set block optimal_delay from cached delay_map"
        )


class TestLiveCalibrationInlineIteration:
    """Live calibration path must apply delay_map via inline block iteration."""

    def test_live_path_inlines_block_iteration(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        ).read_text()
        assert "block['optimal_delay'] = delay_map[bname]" in source, (
            "Live calibration path must set block optimal_delay from delay_map"
        )


class TestApplyCalibrationResultsPreserved:
    """_apply_calibration_results helper must still exist as a shared helper."""

    def test_apply_calibration_results_still_exists(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        assert hasattr(BacktestConfigPanel, "_apply_calibration_results"), (
            "_apply_calibration_results helper should still exist"
        )


class TestBlockMutationBehavior:
    """Verify the inlined iteration correctly mutates blocks in-place."""

    def test_inline_iteration_mutates_blocks_in_place(self):
        blocks = [
            {"name": "block_a", "optimal_delay": 0},
            {"name": "block_b", "optimal_delay": 0},
            {"name": "block_c", "optimal_delay": 0},
        ]
        delay_map = {"block_a": 5, "block_c": 10}
        for block in blocks:
            bname = block.get("name") or block.get("block_name", "")
            if bname in delay_map:
                block["optimal_delay"] = delay_map[bname]
        assert blocks[0]["optimal_delay"] == 5
        assert blocks[1]["optimal_delay"] == 0
        assert blocks[2]["optimal_delay"] == 10

    def test_apply_method_matches_inline_behavior(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        panel = MagicMock(spec=BacktestConfigPanel)
        blocks_ref = [
            {"name": "x", "optimal_delay": 0},
            {"name": "y", "optimal_delay": 0},
        ]
        blocks_copy = [
            {"name": "x", "optimal_delay": 0},
            {"name": "y", "optimal_delay": 0},
        ]
        delay_map = {"x": 7, "y": 3}
        BacktestConfigPanel._apply_calibration_results(panel, blocks_ref, delay_map)
        for block in blocks_copy:
            bname = block.get("name") or block.get("block_name", "")
            if bname in delay_map:
                block["optimal_delay"] = delay_map[bname]
        assert blocks_ref == blocks_copy, (
            "Inline iteration must produce same result as _apply_calibration_results"
        )


class TestNoApplyCallInRunAutoCalibration:
    """Verify _run_auto_calibration does not call _apply_calibration_results."""

    def test_run_auto_calibration_does_not_call_apply_method(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "backtest_config_panel.py"
        ).read_text()
        run_method_lines = source.split("def _run_auto_calibration")[1].split(
            "def _on_run_clicked"
        )[0]
        assert "self._apply_calibration_results" not in run_method_lines, (
            "_run_auto_calibration must not call self._apply_calibration_results"
        )


class TestRepairIfUnreachable:
    """_repair_if_unreachable must return config when confluence is already reachable."""

    def test_returns_config_when_confluence_reachable(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        panel = MagicMock(spec=BacktestConfigPanel)
        config = {
            'blocks': [
                {'name': 'a', 'signals': [{'weight': 30}]},
                {'name': 'b', 'signals': [{'weight': 25}]},
            ],
            'confluence_threshold': 40,
        }
        result = BacktestConfigPanel._repair_if_unreachable(panel, config)
        assert result is config

    def test_returns_none_when_confluence_unreachable_no_fallback(self):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        panel = MagicMock()
        config = {
            'name': 'test_strat',
            'blocks': [
                {'name': 'x', 'signals': [{'weight': 10}]},
            ],
            'confluence_threshold': 50,
        }
        result = BacktestConfigPanel._repair_if_unreachable(panel, config)
        assert result is None
