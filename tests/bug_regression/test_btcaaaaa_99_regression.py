"""
Regression tests for BTCAAAAA-99.

Bug identified by Blast Radius Touch Index as sharing modified files
with BTCAAAAA-7364 (institutional_signal_evaluator.py + confluence_calculator.py).
These tests exercise the core confluence scoring, signal gating, and
entry-decision logic that both bugs depend on.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.optimizer_v3.core.confluence_calculator import ConfluenceCalculator


pytestmark = [
    pytest.mark.bug("BTCAAAAA-99"),
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


def _or_block_config() -> Any:
    return _dict_to_obj({
        "blocks": [
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
# ConfluenceCalculator.calculate
# ---------------------------------------------------------------------------


class TestCalculate:
    """ConfluenceCalculator.calculate() scoring."""

    def test_all_and_signals_present_full_score(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD", "hod::BEARISH"],
        )
        assert score == 75  # 25 + 30 + 20

    def test_partial_signals_lower_score(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BEARISH"],
        )
        assert score == 45  # 25 + 20

    def test_or_signals_add_bonus_points(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD", "hod::BEARISH", "hod::BEARISH_CROSS"],
        )
        assert score == 90  # 25 + 30 + 20 + 15

    def test_recheck_confirmations_apply_bonus(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(
            _and_block_config(),
            [
                "hod::HOD_REJECTION",
                "hod::BELOW_HOD",
                "hod::BELOW_HOD::CONFIRMED_1X",
                "hod::BELOW_HOD::CONFIRMED_2X",
                "hod::BEARISH",
            ],
        )
        hod_rej = 25
        below_hod = int(30 * 1.10)  # 2 confirmations = 1.10x
        bearish = 20
        assert score == hod_rej + below_hod + bearish

    def test_triple_recheck_caps_at_1_20(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(
            _and_block_config(),
            [
                "hod::HOD_REJECTION",
                "hod::BELOW_HOD",
                "hod::BELOW_HOD::CONFIRMED_1X",
                "hod::BELOW_HOD::CONFIRMED_2X",
                "hod::BELOW_HOD::CONFIRMED_3X",
            ],
        )
        hod_rej = 25
        below_hod = int(30 * 1.20)  # 3+ confirmations = 1.20x
        assert score == hod_rej + below_hod

    def test_mixed_blocks_combine_score(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(
            _mixed_blocks_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD", "momentum::RSI_DIVERGENCE"],
        )
        assert score == 65  # 25 + 30 + 10

    def test_no_fired_signals_returns_zero(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(_and_block_config(), [])
        assert score == 0

    def test_empty_blocks_returns_zero(self):
        calc = ConfluenceCalculator()
        score = calc.calculate(_dict_to_obj({"blocks": []}), [])
        assert score == 0

    def test_default_weight_when_missing(self):
        config = _dict_to_obj({
            "blocks": [
                {
                    "name": "hod",
                    "logic": "AND",
                    "signals": [
                        {"name": "SIGNAL_A", "logic": "AND"},
                    ],
                },
            ],
        })
        calc = ConfluenceCalculator()
        score = calc.calculate(config, ["hod::SIGNAL_A"])
        assert score == 10  # default weight

    def test_none_weight_uses_default(self):
        config = _dict_to_obj({
            "blocks": [
                {
                    "name": "hod",
                    "logic": "AND",
                    "signals": [
                        {"name": "SIGNAL_A", "logic": "AND", "weight": None},
                    ],
                },
            ],
        })
        calc = ConfluenceCalculator()
        score = calc.calculate(config, ["hod::SIGNAL_A"])
        assert score == 10  # None weight → default


# ---------------------------------------------------------------------------
# ConfluenceCalculator.check_required_signals
# ---------------------------------------------------------------------------


class TestCheckRequiredSignals:
    """AND-signal gating."""

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

    def test_only_or_block_no_required_signals(self):
        calc = ConfluenceCalculator()
        result = calc.check_required_signals(
            _or_block_config(),
            [],
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
# ConfluenceCalculator.get_signal_breakdown
# ---------------------------------------------------------------------------


class TestGetSignalBreakdown:
    """Signal breakdown dict."""

    def test_breakdown_contains_all_fired_signals(self):
        calc = ConfluenceCalculator()
        breakdown = calc.get_signal_breakdown(
            _and_block_config(),
            ["hod::HOD_REJECTION", "hod::BELOW_HOD"],
        )
        assert "hod::HOD_REJECTION" in breakdown
        assert "hod::BELOW_HOD" in breakdown
        assert breakdown["hod::HOD_REJECTION"] == 25

    def test_breakdown_excludes_unfired_signals(self):
        calc = ConfluenceCalculator()
        breakdown = calc.get_signal_breakdown(
            _and_block_config(),
            ["hod::HOD_REJECTION"],
        )
        assert "hod::BEARISH" not in breakdown
        assert "hod::BEARISH_CROSS" not in breakdown

    def test_breakdown_empty_when_no_signals(self):
        calc = ConfluenceCalculator()
        breakdown = calc.get_signal_breakdown(_and_block_config(), [])
        assert breakdown == {}

    def test_breakdown_reflects_recheck_bonus(self):
        calc = ConfluenceCalculator()
        breakdown = calc.get_signal_breakdown(
            _and_block_config(),
            [
                "hod::HOD_REJECTION",
                "hod::BELOW_HOD",
                "hod::BELOW_HOD::CONFIRMED_1X",
            ],
        )
        assert breakdown["hod::BELOW_HOD"] == int(30 * 1.05)  # 1 confirmation


# ---------------------------------------------------------------------------
# InstitutionalSignalEvaluator._signal_exists_in_config
# ---------------------------------------------------------------------------


class TestSignalExistsInConfig:
    """Signal lookup in strategy config."""

    def _make_evaluator(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )

        def _stub_init(self_, strategy_config):
            self_.strategy_config = strategy_config
            self_.building_blocks = {}
            self_.exit_conditions = {}
            self_.logger = MagicMock()

        with patch.object(InstitutionalSignalEvaluator, "__init__", _stub_init):
            return InstitutionalSignalEvaluator(None)

    def test_entry_signal_found(self):
        evaluator = self._make_evaluator()
        evaluator.strategy_config = _and_block_config()
        result = evaluator._signal_exists_in_config("hod", "HOD_REJECTION")
        assert result is True

    def test_exit_signal_found_via_block_exit_conditions(self):
        config = _dict_to_obj({
            "blocks": [
                {
                    "name": "hod",
                    "logic": "AND",
                    "signals": [],
                    "exit_conditions": [{"signal_name": "BEARISH_SWEEP"}],
                }
            ],
        })
        evaluator = self._make_evaluator()
        evaluator.strategy_config = config
        result = evaluator._signal_exists_in_config("hod", "BEARISH_SWEEP")
        assert result is True

    def test_nonexistent_signal_returns_false(self):
        evaluator = self._make_evaluator()
        evaluator.strategy_config = _and_block_config()
        result = evaluator._signal_exists_in_config("hod", "NONEXISTENT")
        assert result is False

    def test_nonexistent_block_returns_false(self):
        evaluator = self._make_evaluator()
        evaluator.strategy_config = _and_block_config()
        result = evaluator._signal_exists_in_config("nonexistent_block", "HOD_REJECTION")
        assert result is False


# ---------------------------------------------------------------------------
# InstitutionalSignalEvaluator.evaluate_bar entry decision
# ---------------------------------------------------------------------------


class TestEvaluateBarEntryDecision:
    """Entry gate in evaluate_bar()."""

    def _make_evaluator(self, config):
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )

        with (
            patch.object(InstitutionalSignalEvaluator, "_instantiate_building_blocks", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_organize_exit_conditions", return_value={}),
            patch.object(InstitutionalSignalEvaluator, "_log_strategy_config"),
        ):
            evaluator = InstitutionalSignalEvaluator(config)
        # Patch _evaluate_building_blocks to return mock signals so that
        # evaluate_bar has fired signals to score against the config.
        evaluator._evaluate_building_blocks = lambda bar, lookback, bar_index=0: {
            "hod::HOD_REJECTION": {"name": "HOD_REJECTION", "value": 1},
            "hod::BELOW_HOD": {"name": "BELOW_HOD", "value": 1},
            "hod::BEARISH": {"name": "BEARISH", "value": 1},
        }
        return evaluator

    def _make_bar(self):
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
        return Bar(
            bar_type=bar_type,
            open=Price(45000, 2),
            high=Price(45100, 2),
            low=Price(44900, 2),
            close=Price(45050, 2),
            volume=Quantity(10, 8),
            ts_event=ts_ns,
            ts_init=ts_ns,
        )

    def test_entry_allowed_when_confluence_meets_threshold(self):
        config = _and_block_config()
        config.confluence_threshold = 40
        config.require_all_and_signals = False
        evaluator = self._make_evaluator(config)

        bar = self._make_bar()
        from nautilus_trader.model.data import Bar
        lookback: list[Bar] = []

        result = evaluator.evaluate_bar(bar, 0, lookback)
        assert result.should_enter is True
        assert result.should_exit is False

    def test_entry_blocked_when_confluence_below_threshold(self):
        config = _and_block_config()
        config.confluence_threshold = 200
        config.require_all_and_signals = False
        evaluator = self._make_evaluator(config)

        bar = self._make_bar()
        result = evaluator.evaluate_bar(bar, 0, [])
        assert result.should_enter is False

    def test_entry_blocked_by_required_signals_gate(self):
        """When require_all_and_signals is True, missing AND signal blocks entry."""
        config = _and_block_config()
        config.confluence_threshold = 40
        config.require_all_and_signals = True
        evaluator = self._make_evaluator(config)

        mock_calc = MagicMock(spec=ConfluenceCalculator)
        mock_calc.calculate.return_value = 100
        mock_calc.check_required_signals.return_value = False
        evaluator.confluence_calc = mock_calc

        bar = self._make_bar()
        result = evaluator.evaluate_bar(bar, 0, [])
        assert result.should_enter is False
        mock_calc.check_required_signals.assert_called_once()

    def test_results_contain_fired_signals(self):
        config = _and_block_config()
        config.confluence_threshold = 40
        config.require_all_and_signals = False
        evaluator = self._make_evaluator(config)

        bar = self._make_bar()
        result = evaluator.evaluate_bar(bar, 0, [])
        assert hasattr(result, "signals_fired")
        assert hasattr(result, "confluence_score")
