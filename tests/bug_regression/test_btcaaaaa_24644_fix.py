"""
Targeted tests for BTCAAAAA-24644 fix (commit 927c15ee):
  - OR blocks with AND-logic signals must be skipped
  - require_all_and_signals flag must gate the call
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.optimizer_v3.core.confluence_calculator import ConfluenceCalculator


pytestmark = [
    pytest.mark.bug("BTCAAAAA-24644"),
    pytest.mark.regression,
]


def _dict_to_obj(d: Any) -> Any:
    if isinstance(d, dict):
        obj = type("MockObj", (), {})()
        for k, v in d.items():
            setattr(obj, k, _dict_to_obj(v))
        return obj
    if isinstance(d, list):
        return [_dict_to_obj(item) for item in d]
    return d


# ---------------------------------------------------------------------------
# The REAL bug scenario: OR block containing AND-logic signals
# ---------------------------------------------------------------------------
# Before commit 927c15ee, check_required_signals scanned ALL blocks including
# OR blocks.  If an OR block had AND-logic signals, those were falsely required.
# After the fix, OR blocks are skipped entirely — their signals are always optional.


def _or_block_with_and_signals() -> Any:
    """OR block whose signals have signal-level logic=AND."""
    return _dict_to_obj({
        "blocks": [
            {
                "name": "must_have",
                "logic": "AND",
                "signals": [
                    {"name": "SIG_A", "logic": "AND", "weight": 20},
                ],
            },
            {
                "name": "optional_booster",
                "logic": "OR",
                "signals": [
                    # AND-level signals inside an OR block — must NOT be required
                    {"name": "BOOSTER_1", "logic": "AND", "weight": 15},
                    {"name": "BOOSTER_2", "logic": "OR", "weight": 10},
                ],
            },
        ],
    })


class TestCheckRequiredSignals_24644_Fix:
    """BTCAAAAA-24644: OR-block AND-signal fix verification."""

    def test_or_block_with_and_signals_not_required(self):
        """OR block with AND-logic signals: those signals must NOT be required."""
        calc = ConfluenceCalculator()
        # Only SIG_A fired — BOOSTER_1 (AND in OR block) did NOT fire → must still PASS
        result = calc.check_required_signals(
            _or_block_with_and_signals(),
            ["must_have::SIG_A"],
        )
        assert result is True

    def test_or_block_with_and_signals_all_missing_still_passes(self):
        """OR block entirely silent — still passes because OR block is skipped."""
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _or_block_with_and_signals(),
            ["must_have::SIG_A"],
        )
        assert result is True

    def test_and_block_and_signal_missing_still_fails(self):
        """AND block AND-signal missing → still returns False (not affected by fix)."""
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _or_block_with_and_signals(),
            [],  # SIG_A not fired — should fail
        )
        assert result is False

    def test_only_or_blocks_no_required(self):
        """Every block is OR → no signals required at all."""
        config = _dict_to_obj({
            "blocks": [
                {
                    "name": "opt_a",
                    "logic": "OR",
                    "signals": [
                        {"name": "A1", "logic": "AND", "weight": 10},
                    ],
                },
            ],
        })
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(config, [])
        assert result is True

    def test_mixed_blocks_and_missing_in_and_block_fails(self):
        """AND block missing AND-signal fails even with OR blocks present."""
        config = _dict_to_obj({
            "blocks": [
                {"name": "b1", "logic": "AND", "signals": [
                    {"name": "S1", "logic": "AND", "weight": 10},
                ]},
                {"name": "b2", "logic": "OR", "signals": [
                    {"name": "S2", "logic": "AND", "weight": 10},
                ]},
            ],
        })
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(config, [])
        assert result is False


class TestRequireAllAndSignalsFlag:
    """BTCAAAAA-24644: require_all_and_signals gate flag."""

    @pytest.fixture
    def _evaluator(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )
        # Minimal config with blocks needed for init
        config = _dict_to_obj({"blocks": []})
        with (
            patch.object(InstitutionalSignalEvaluator, "_instantiate_building_blocks", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_organize_exit_conditions", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_log_strategy_config"),
        ):
            yield config, InstitutionalSignalEvaluator(config)

    def test_default_flag_false_check_not_called(self, _evaluator):
        """require_all_and_signals defaults to False → check_required_signals NOT called."""
        config, evaluator = _evaluator
        mock_calc = MagicMock(spec=ConfluenceCalculator)
        mock_calc.check_required_signals.return_value = False
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
        bar = Bar(bar_type, Price(45000, 2), Price(45100, 2), Price(44900, 2),
                  Price(45050, 2), Quantity(10, 8), ts_event=ts_ns, ts_init=ts_ns)

        evaluator.evaluate_bar(bar, 0, [], 1)
        mock_calc.check_required_signals.assert_not_called()

    def test_flag_true_check_called(self):
        """require_all_and_signals=True → check_required_signals IS called."""
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )
        mock_calc = MagicMock(spec=ConfluenceCalculator)
        mock_calc.check_required_signals.return_value = True

        config = _dict_to_obj({"blocks": []})
        config.require_all_and_signals = True

        with (
            patch.object(InstitutionalSignalEvaluator, "_instantiate_building_blocks", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_organize_exit_conditions", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_log_strategy_config"),
        ):
            evaluator = InstitutionalSignalEvaluator(config)
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
        bar = Bar(bar_type, Price(45000, 2), Price(45100, 2), Price(44900, 2),
                  Price(45050, 2), Quantity(10, 8), ts_event=ts_ns, ts_init=ts_ns)

        evaluator.evaluate_bar(bar, 0, [], 1)
        mock_calc.check_required_signals.assert_called_once()
