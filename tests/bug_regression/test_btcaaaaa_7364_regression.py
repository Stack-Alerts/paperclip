"""
Regression tests for BTCAAAAA-7364: AND-logic signals not enforced at entry.

Root cause: evaluate_bar() in institutional_signal_evaluator.py checked only
`confluence >= min_confluence` at the entry gate, ignoring AND-logic signal
requirements declared in strategy config. check_required_signals() existed in
ConfluenceCalculator but was never called from the entry decision path.

Fix: wired self.confluence_calc.check_required_signals() into evaluate_bar()
at line 522-526. When require_all_and_signals=True on the strategy config,
entry is rejected when any AND signal is missing regardless of confluence score.
OR-logic signals remain optional (bonus points only).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.optimizer_v3.core.confluence_calculator import ConfluenceCalculator


pytestmark = [
    pytest.mark.bug("BTCAAAAA-7364"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dict_to_obj(d: Any) -> Any:
    """Recursively convert dicts to simple objects for test use."""
    if isinstance(d, dict):
        obj = type("MockObj", (), {})()
        for k, v in d.items():
            setattr(obj, k, _dict_to_obj(v))
        return obj
    if isinstance(d, list):
        return [_dict_to_obj(item) for item in d]
    return d


def _and_block_config() -> Any:
    return _dict_to_obj({
        "blocks": [
            {
                "name": "hod",
                "logic": "AND",
                "signals": [
                    {"name": "HOD_REJECTION", "logic": "AND", "weight": 25},
                    {"name": "BELOW_HOD", "logic": "AND", "weight": 30},
                    {"name": "BEARISH", "logic": "AND", "weight": 20},
                    {"name": "BEARISH_CROSS", "logic": "OR", "weight": 15},
                ],
            },
        ],
    })


def _mixed_blocks_config() -> Any:
    return _dict_to_obj({
        "blocks": [
            {
                "name": "hod",
                "logic": "AND",
                "signals": [
                    {"name": "HOD_REJECTION", "logic": "AND", "weight": 25},
                    {"name": "BELOW_HOD", "logic": "AND", "weight": 30},
                ],
            },
            {
                "name": "momentum",
                "logic": "OR",
                "signals": [
                    {"name": "RSI_DIVERGENCE", "logic": "OR", "weight": 10},
                    {"name": "MACD_CROSS", "logic": "OR", "weight": 10},
                ],
            },
        ],
    })


# ---------------------------------------------------------------------------
# Unit tests: ConfluenceCalculator.check_required_signals
# ---------------------------------------------------------------------------


class TestCheckRequiredSignalsUnit:
    """Direct unit tests of ConfluenceCalculator.check_required_signals."""

    def test_all_and_signals_present_returns_true(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD", "hod::BEARISH"],
        )
        assert result is True

    def test_missing_and_signal_returns_false(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BEARISH"],
        )
        assert result is False

    def test_or_signals_are_optional(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD", "hod::BEARISH"],
        )
        assert result is True

    def test_or_blocks_are_skipped(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _mixed_blocks_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD"],
        )
        assert result is True

    def test_no_fired_signals_returns_false(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(_and_block_config(), [])
        assert result is False

    def test_empty_blocks_returns_true(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(_dict_to_obj({"blocks": []}), [])
        assert result is True


# ---------------------------------------------------------------------------
# Integration: check_required_signals wired into evaluate_bar
# ---------------------------------------------------------------------------


class TestRequiredSignalsInEvaluateBar:
    """
    Verify that evaluate_bar() calls check_required_signals and enforces
    the AND-logic gate when require_all_and_signals=True.
    """

    def _make_evaluator(self, config):
        """Construct an InstitutionalSignalEvaluator with patched init-time methods."""
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )

        with (
            patch.object(InstitutionalSignalEvaluator, "_instantiate_building_blocks", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_organize_exit_conditions", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_log_strategy_config"),
        ):
            return InstitutionalSignalEvaluator(config)

    def test_check_required_signals_called_when_require_all_enabled(self):
        """verify check_required_signals is called when require_all_and_signals is True."""
        mock_calc = MagicMock(spec=ConfluenceCalculator)
        mock_calc.check_required_signals.return_value = False

        config = _dict_to_obj({"blocks": []})
        config.require_all_and_signals = True

        evaluator = self._make_evaluator(config)
        evaluator.confluence_calc = mock_calc

        from nautilus_trader.model.data import Bar, BarType, BarSpecification
        from nautilus_trader.model.objects import Price, Quantity
        from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
        from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
        from datetime import datetime

        bar_type = BarType(
            InstrumentId(Symbol("BTC"), Venue("BINANCE")),
            BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
        ts_ns = int(datetime(2025, 6, 1, 10, 0).timestamp() * 1e9)
        bar = Bar(
            bar_type=bar_type,
            open=Price(45000, 2),
            high=Price(45100, 2),
            low=Price(44900, 2),
            close=Price(45050, 2),
            volume=Quantity(10, 8),
            ts_event=ts_ns,
            ts_init=ts_ns,
        )

        evaluator.evaluate_bar(bar, 0, [], 1)

        mock_calc.check_required_signals.assert_called_once()

    def test_check_required_signals_not_called_when_require_all_disabled(self):
        """verify check_required_signals is NOT called when require_all_and_signals is False."""
        mock_calc = MagicMock(spec=ConfluenceCalculator)
        mock_calc.check_required_signals.return_value = False

        config = _dict_to_obj({"blocks": []})
        config.require_all_and_signals = False

        evaluator = self._make_evaluator(config)
        evaluator.confluence_calc = mock_calc

        from nautilus_trader.model.data import Bar, BarType, BarSpecification
        from nautilus_trader.model.objects import Price, Quantity
        from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
        from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
        from datetime import datetime

        bar_type = BarType(
            InstrumentId(Symbol("BTC"), Venue("BINANCE")),
            BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
        ts_ns = int(datetime(2025, 6, 1, 10, 0).timestamp() * 1e9)
        bar = Bar(
            bar_type=bar_type,
            open=Price(45000, 2),
            high=Price(45100, 2),
            low=Price(44900, 2),
            close=Price(45050, 2),
            volume=Quantity(10, 8),
            ts_event=ts_ns,
            ts_init=ts_ns,
        )

        evaluator.evaluate_bar(bar, 0, [], 1)

        mock_calc.check_required_signals.assert_not_called()
