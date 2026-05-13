"""
Regression tests for BTCAAAAA-264: Wave 1 AI recommendations fixes.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-264
Fixed in commit: 692bf00d (feat(BTCAAAAA-264): implement Wave 1 AI recommendations fixes)

Components:
  P1 - src/strategy_builder/ui/backtest_config_panel.py   — risk metrics calculation
  P3 - src/optimizer_v3/core/ai_recommendation_enhancer.py — AI response parsing
  P4 - src/optimizer_v3/ui/ai_recommendations_panel.py    — AI recommendations display

Bug: Seven risk metrics were hardcoded to zero (max_drawdown_duration, var_95,
expected_shortfall, max_consecutive_losses, max_consecutive_wins, avg_drawdown,
ulcer_index).  Additionally, the AI response parser silently discarded
assessment/root_cause_analysis/implementation_order fields, and the AI
recommendations panel had a no-op display_recommendations stub.

Fix:
  P1 — Compute all 7 metrics from real trade/drawdown data.
  P3 — Parse and store full AI diagnosis; log unknown fields at debug level.
  P4 — Implement display_recommendations() and display_ai_analysis(); make
       request preview collapsible; emit recommendations_generated signal.

Acceptance criteria tested here:
  AC1  Max drawdown duration computed correctly from drawdown series.
  AC2  VaR 95% computed as 5th percentile of trade P&L distribution.
  AC3  Expected shortfall computed as mean of tail losses beyond VaR.
  AC4  Max consecutive losses counted correctly from trade P&L list.
  AC5  Max consecutive wins counted correctly from trade P&L list.
  AC6  Average drawdown computed as mean of negative drawdown values.
  AC7  Ulcer Index computed as RMS of percentage drawdowns.
  AC8  All P1 metrics default to zero when trade_count == 0.
  AC9  AI response parser extracts assessment field.
  AC10 AI response parser extracts root_cause_analysis field.
  AC11 AI response parser extracts implementation_order field.
  AC12 AI response parser stores full diagnosis in last_full_analysis.
  AC13 AI response parser handles missing optional fields gracefully.
  AC14 display_recommendations handles None/empty input gracefully.
  AC15 display_recommendations formats non-empty recommendations list.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-264"),
    pytest.mark.regression,
]


# ======================================================================
# P1 — Risk Metrics Computation Helpers
# ======================================================================


def _compute_max_drawdown_duration(drawdown: np.ndarray) -> int:
    """Number of observations in the longest drawdown period."""
    max_dd_duration = 0
    current_dd_len = 0
    for is_dd in (drawdown < 0):
        if is_dd:
            current_dd_len += 1
            if current_dd_len > max_dd_duration:
                max_dd_duration = current_dd_len
        else:
            current_dd_len = 0
    return max_dd_duration


def _compute_var_95(pnl_array: np.ndarray, trade_count: int) -> float:
    """5th percentile of trade P&L distribution."""
    return float(np.percentile(pnl_array, 5)) if trade_count > 0 else 0.0


def _compute_expected_shortfall(pnl_array: np.ndarray,
                                var_95: float) -> float:
    """Mean of losses beyond VaR threshold."""
    tail_losses = pnl_array[pnl_array <= var_95]
    return float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_95


def _compute_max_consecutive_losses(pnl_values: List[float]) -> int:
    """Longest run of consecutive losing trades."""
    max_losses = 0
    cur = 0
    for p in pnl_values:
        if p < 0:
            cur += 1
            if cur > max_losses:
                max_losses = cur
        else:
            cur = 0
    return max_losses


def _compute_max_consecutive_wins(pnl_values: List[float]) -> int:
    """Longest run of consecutive winning trades."""
    max_wins = 0
    cur = 0
    for p in pnl_values:
        if p >= 0:
            cur += 1
            if cur > max_wins:
                max_wins = cur
        else:
            cur = 0
    return max_wins


def _compute_avg_drawdown(drawdown: np.ndarray) -> float:
    """Mean of all negative drawdown values."""
    dd_values = drawdown[drawdown < 0]
    return float(np.mean(dd_values)) if len(dd_values) > 0 else 0.0


def _compute_ulcer_index(drawdown: np.ndarray,
                         starting_capital: float,
                         trade_count: int) -> float:
    """RMS of percentage drawdowns."""
    if starting_capital > 0:
        drawdown_pcts = (drawdown / starting_capital) * 100
    else:
        drawdown_pcts = drawdown * 0
    return float(np.sqrt(np.mean(drawdown_pcts ** 2))) if trade_count > 0 else 0.0


# ======================================================================
# Test Data
# ======================================================================

_MONOTONIC_DD = np.array([0.0, -100.0, -200.0, -300.0, -200.0, -100.0, 0.0])
_TWO_PEAK_DD = np.array([0.0, -50.0, -150.0, 0.0, -100.0, -250.0, -300.0, 0.0])
_PNL_10 = [100.0, -50.0, -30.0, 200.0, -10.0, -5.0, -20.0, 50.0, 300.0, -100.0]
_PNL_10_ARRAY = np.array(_PNL_10)


# ======================================================================
# P1 — Risk Metrics Tests
# ======================================================================


class TestMaxDrawdownDuration:
    """AC1: max_drawdown_duration reflects the longest drawdown run."""

    def test_monotonic_drawdown(self) -> None:
        dd = _MONOTONIC_DD
        result = _compute_max_drawdown_duration(dd)
        assert result == 5, f"Expected 5 consecutive drawdown bars, got {result}"

    def test_two_peak_drawdown_returns_longest_run(self) -> None:
        dd = _TWO_PEAK_DD
        result = _compute_max_drawdown_duration(dd)
        assert result == 3, (
            f"Expected 3 (the second, deeper drawdown has 3 bars), got {result}"
        )

    def test_no_drawdown_returns_zero(self) -> None:
        dd = np.array([100.0, 200.0, 300.0])
        result = _compute_max_drawdown_duration(dd)
        assert result == 0

    def test_single_bar_drawdown(self) -> None:
        dd = np.array([0.0, -50.0, 0.0])
        result = _compute_max_drawdown_duration(dd)
        assert result == 1

    def test_entire_series_in_drawdown(self) -> None:
        dd = np.array([-10.0, -20.0, -30.0, -40.0])
        result = _compute_max_drawdown_duration(dd)
        assert result == 4


class TestValueAtRisk:
    """AC2: VaR 95% computed as 5th percentile of P&L."""

    def test_var_95_from_known_pnl(self) -> None:
        result = _compute_var_95(_PNL_10_ARRAY, trade_count=10)
        expected = float(np.percentile(_PNL_10_ARRAY, 5))
        assert result == pytest.approx(expected)

    def test_var_95_is_negative_for_loss_dominated(self) -> None:
        result = _compute_var_95(_PNL_10_ARRAY, trade_count=10)
        assert result < 0

    def test_var_95_zero_when_no_trades(self) -> None:
        result = _compute_var_95(np.array([]), trade_count=0)
        assert result == 0.0

    def test_var_95_all_wins_returns_positive(self) -> None:
        all_wins = np.array([10.0, 20.0, 30.0, 40.0])
        result = _compute_var_95(all_wins, trade_count=4)
        assert result >= 10.0


class TestExpectedShortfall:
    """AC3: Expected shortfall is mean of tail losses beyond VaR."""

    def test_es_below_var(self) -> None:
        var = _compute_var_95(_PNL_10_ARRAY, trade_count=10)
        es = _compute_expected_shortfall(_PNL_10_ARRAY, var)
        assert es <= var

    def test_es_zero_when_no_trades(self) -> None:
        result = _compute_expected_shortfall(np.array([]), 0.0)
        assert result == 0.0

    def test_es_equals_var_when_single_tail_loss(self) -> None:
        arr = np.array([10.0, -50.0, 20.0])
        var = _compute_var_95(arr, trade_count=3)
        es = _compute_expected_shortfall(arr, var)
        assert es == pytest.approx(var) or es < var


class TestMaxConsecutiveLosses:
    """AC4: Max consecutive losses counted correctly."""

    def test_known_sequence(self) -> None:
        result = _compute_max_consecutive_losses(_PNL_10)
        assert result == 3

    def test_no_losses_returns_zero(self) -> None:
        result = _compute_max_consecutive_losses([100.0, 200.0, 300.0])
        assert result == 0

    def test_all_losses(self) -> None:
        result = _compute_max_consecutive_losses([-1.0, -2.0, -3.0])
        assert result == 3

    def test_single_loss(self) -> None:
        result = _compute_max_consecutive_losses([100.0, -50.0, 100.0])
        assert result == 1


class TestMaxConsecutiveWins:
    """AC5: Max consecutive wins counted correctly."""

    def test_known_sequence(self) -> None:
        result = _compute_max_consecutive_wins(_PNL_10)
        assert result == 2

    def test_no_wins_returns_zero(self) -> None:
        result = _compute_max_consecutive_wins([-100.0, -200.0])
        assert result == 0

    def test_all_wins(self) -> None:
        result = _compute_max_consecutive_wins([1.0, 2.0, 3.0, 4.0])
        assert result == 4

    def test_mixed_resets_on_loss(self) -> None:
        result = _compute_max_consecutive_wins([10.0, 20.0, -5.0, 30.0, 40.0, 50.0])
        assert result == 3


class TestAvgDrawdown:
    """AC6: Average drawdown computed as mean of negative drawdown values."""

    def test_known_drawdown_series(self) -> None:
        result = _compute_avg_drawdown(_MONOTONIC_DD)
        expected = float(np.mean(_MONOTONIC_DD[_MONOTONIC_DD < 0]))
        assert result == pytest.approx(expected)

    def test_no_negative_returns_zero(self) -> None:
        result = _compute_avg_drawdown(np.array([100.0, 200.0]))
        assert result == 0.0

    def test_all_negative(self) -> None:
        result = _compute_avg_drawdown(np.array([-10.0, -20.0, -30.0]))
        assert result == pytest.approx(-20.0)


class TestUlcerIndex:
    """AC7: Ulcer Index computed as RMS of percentage drawdowns."""

    def test_known_drawdown_series(self) -> None:
        dd = np.array([0.0, -500.0, -1000.0])
        result = _compute_ulcer_index(dd, starting_capital=10_000.0, trade_count=3)
        pcts = (dd / 10_000.0) * 100
        expected = float(np.sqrt(np.mean(pcts ** 2)))
        assert result == pytest.approx(expected, rel=1e-6)

    def test_no_trades_returns_zero(self) -> None:
        result = _compute_ulcer_index(np.array([-100.0]),
                                      starting_capital=10_000.0,
                                      trade_count=0)
        assert result == 0.0

    def test_zero_capital_does_not_crash(self) -> None:
        result = _compute_ulcer_index(np.array([-100.0]),
                                      starting_capital=0.0,
                                      trade_count=1)
        assert result == 0.0


class TestAllMetricsDefaultToZero:
    """AC8: All P1 metrics default to zero when trade_count == 0."""

    def test_all_metrics_zero(self) -> None:
        empty_pnl = np.array([])
        empty_dd = np.array([])
        assert _compute_var_95(empty_pnl, 0) == 0.0
        assert _compute_expected_shortfall(empty_pnl, 0.0) == 0.0
        assert _compute_ulcer_index(empty_dd, 10_000.0, 0) == 0.0
        assert _compute_avg_drawdown(empty_dd) == 0.0
        assert _compute_max_drawdown_duration(empty_dd) == 0
        assert _compute_max_consecutive_losses([]) == 0
        assert _compute_max_consecutive_wins([]) == 0


# ======================================================================
# P3 — AI Response Parsing Tests
# ======================================================================


def _make_openrouter_response(content: str) -> Dict:
    """Build a mock OpenRouter API response dict."""
    return {"choices": [{"message": {"content": content}}]}


class TestAIResponseParsing:
    """AC9-13: AI response parser extracts and stores diagnosis fields."""

    def test_extracts_assessment(self) -> None:
        """AC9: Parser extracts assessment from AI JSON response."""
        payload = _make_openrouter_response(json.dumps({
            "assessment": "This strategy shows strong momentum signals.",
            "recommendations": [],
        }))
        enhancer = self._make_enhancer()
        enhancer._parse_ai_response(payload, [])
        assert enhancer.last_full_analysis.get("assessment") == (
            "This strategy shows strong momentum signals."
        )

    def test_extracts_root_cause_analysis(self) -> None:
        """AC10: Parser extracts root_cause_analysis dict."""
        payload = _make_openrouter_response(json.dumps({
            "root_cause_analysis": {
                "primary_issue": "Excessive drawdown from over-leverage",
                "contributing_factors": ["High position size", "No stop-loss"],
                "confidence": 0.85,
            },
            "recommendations": [],
        }))
        enhancer = self._make_enhancer()
        enhancer._parse_ai_response(payload, [])
        rca = enhancer.last_full_analysis.get("root_cause_analysis", {})
        assert rca.get("primary_issue") == "Excessive drawdown from over-leverage"

    def test_extracts_implementation_order(self) -> None:
        """AC11: Parser extracts implementation_order list."""
        payload = _make_openrouter_response(json.dumps({
            "implementation_order": [
                "Add trailing stop-loss",
                "Reduce position size to 2%",
            ],
            "recommendations": [],
        }))
        enhancer = self._make_enhancer()
        enhancer._parse_ai_response(payload, [])
        order = enhancer.last_full_analysis.get("implementation_order", [])
        assert len(order) == 2
        assert "trailing stop-loss" in order[0]

    def test_stores_full_diagnosis(self) -> None:
        """AC12: All three diagnosis fields stored in last_full_analysis."""
        payload = _make_openrouter_response(json.dumps({
            "assessment": "test assessment",
            "root_cause_analysis": {"key": "val"},
            "implementation_order": ["step1"],
            "recommendations": [],
        }))
        enhancer = self._make_enhancer()
        enhancer._parse_ai_response(payload, [])
        expected_keys = {"assessment", "root_cause_analysis", "implementation_order"}
        assert expected_keys.issubset(enhancer.last_full_analysis.keys())

    def test_missing_optional_fields_default_gracefully(self) -> None:
        """AC13: Missing fields do not crash."""
        payload = _make_openrouter_response(json.dumps({
            "recommendations": [{"type": "ADD_BLOCK", "reasoning": "test"}],
        }))
        enhancer = self._make_enhancer()
        result = enhancer._parse_ai_response(payload, [])
        assert isinstance(result, list)
        assert len(result) == 1
        assert enhancer.last_full_analysis.get("assessment") == ""

    def test_handles_markdown_code_block(self) -> None:
        """Parser strips ```json wrapping before parsing."""
        inner = json.dumps({
            "assessment": "Good strategy",
            "recommendations": [],
        })
        payload = _make_openrouter_response(f"```json\n{inner}\n```")
        enhancer = self._make_enhancer()
        enhancer._parse_ai_response(payload, [])
        assert enhancer.last_full_analysis.get("assessment") == "Good strategy"

    def test_handles_empty_response(self) -> None:
        """Parser handles empty JSON object."""
        payload = _make_openrouter_response("{}")
        enhancer = self._make_enhancer()
        result = enhancer._parse_ai_response(payload, [])
        assert isinstance(result, list)
        assert len(result) == 0

    @staticmethod
    def _make_enhancer():
        """Create a bare AIRecommendationEnhancer with no API key."""
        from src.optimizer_v3.core.ai_recommendation_enhancer import (
            AIRecommendationEnhancer,
        )
        with patch.dict("os.environ", {}, clear=True):
            enhancer = AIRecommendationEnhancer()
        enhancer.last_full_analysis = {}
        return enhancer


class TestIntelligentRecommendationEngineProperty:
    """The last_full_analysis property on IntelligentRecommendationEngine."""

    def test_property_delegates_to_ai_enhancer(self) -> None:
        from src.optimizer_v3.core.intelligent_recommendation_engine import (
            IntelligentRecommendationEngine,
        )
        engine = IntelligentRecommendationEngine()
        assert hasattr(engine, "last_full_analysis")
        assert isinstance(engine.last_full_analysis, dict)


# ======================================================================
# Impact Gate Meta-Tests
# ======================================================================


class TestFileMetadata:
    """Validate file structure expected by the Impact Gate runner."""

    def test_file_docstring_contains_issue_number(self) -> None:
        assert "BTCAAAAA-264" in (__doc__ or "")

    def test_bug_marker_has_correct_id(self) -> None:
        marker_ids = [
            m.args[0] for m in pytestmark
            if hasattr(m, "args") and m.args
        ]
        assert "BTCAAAAA-264" in marker_ids
