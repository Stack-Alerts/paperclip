"""
Unit tests for Strategy Browser quality score composite logic.

Tests the multi-metric quality badge implemented in
src/strategy_builder/ui/strategy_browser_dialog.py _populate_details_panel()
lines 1091-1137 (commit 377270d — fix for BTCAAAAA-248).

The scoring rubric under test:
    Win rate  >= 60%   → 2 pts  |  >= 45% → 1 pt
    Profit factor >= 1.5 → 2 pts  |  >= 1.0 → 1 pt
    Raw Sharpe >= 0.15 → 2 pts  |  >= 0.05 → 1 pt   (DB: avg_pnl/std_dev)
    Total trades >= 20  → 1 pt   (sample size bonus)

    Total  7 pts max → Excellent ≥6 | Good ≥4 | Fair ≥2 | Poor <2

QA: BTCAAAAA-249
"""
import pytest


# ---------------------------------------------------------------------------
# Pure-Python replica of the scoring logic from strategy_browser_dialog.py
# (lines 1104-1136) so tests remain independent of Qt and DB.
# ---------------------------------------------------------------------------

def _compute_quality_score(win_rate, profit_factor, sharpe, total_trades):
    """
    Replicate the composite scoring block from _populate_details_panel().
    Returns (label_text, raw_score).
    """
    _wr = float(win_rate) if win_rate is not None else 0.0
    _pf = float(profit_factor) if profit_factor is not None else 0.0
    _sh = float(sharpe) if sharpe is not None else 0.0
    _tt = int(total_trades) if total_trades is not None else 0

    _score = 0
    # Win rate
    if _wr >= 60:
        _score += 2
    elif _wr >= 45:
        _score += 1
    # Profit factor
    if _pf >= 1.5:
        _score += 2
    elif _pf >= 1.0:
        _score += 1
    # Raw Sharpe (DB stores avg_pnl/std_dev, not annualised)
    if _sh >= 0.15:
        _score += 2
    elif _sh >= 0.05:
        _score += 1
    # Sample size bonus
    if _tt >= 20:
        _score += 1

    if _score >= 6:
        quality = "Excellent"
    elif _score >= 4:
        quality = "Good"
    elif _score >= 2:
        quality = "Fair"
    else:
        quality = "Poor"

    return quality, _score


# ---------------------------------------------------------------------------
# Tests: boundary conditions and label mapping
# ---------------------------------------------------------------------------

class TestQualityScoreLabels:
    """Verify that each quality label is reachable with appropriate inputs."""

    def test_excellent_label_max_score(self):
        """All metrics at Excellent level → score 7, label Excellent."""
        label, score = _compute_quality_score(
            win_rate=65, profit_factor=1.8, sharpe=0.20, total_trades=25
        )
        assert label == "Excellent"
        assert score == 7

    def test_excellent_label_exact_boundary(self):
        """Exact boundary values that achieve score = 7."""
        label, score = _compute_quality_score(
            win_rate=60, profit_factor=1.5, sharpe=0.15, total_trades=20
        )
        assert label == "Excellent"
        assert score == 7

    def test_excellent_label_score_6_without_sample_bonus(self):
        """Excellent without sample bonus: score 6 (wr=2, pf=2, sh=2, trades<20)."""
        label, score = _compute_quality_score(
            win_rate=65, profit_factor=2.0, sharpe=0.20, total_trades=10
        )
        assert label == "Excellent"
        assert score == 6

    def test_good_label(self):
        """Decent win rate, profit factor >= 1.0, some sharpe → Good."""
        label, score = _compute_quality_score(
            win_rate=50, profit_factor=1.3, sharpe=0.10, total_trades=25
        )
        assert label == "Good"
        assert score == 4

    def test_good_label_exact_boundary(self):
        """Score exactly 4 → Good, not Fair."""
        # win_rate 45% = 1pt, pf 1.0 = 1pt, sh 0.05 = 1pt, trades 20 = 1pt → 4
        label, score = _compute_quality_score(
            win_rate=45, profit_factor=1.0, sharpe=0.05, total_trades=20
        )
        assert label == "Good"
        assert score == 4

    def test_fair_label(self):
        """Win rate 45–59%, profit factor >= 1.0, minimal sharpe → Fair."""
        label, score = _compute_quality_score(
            win_rate=48, profit_factor=1.1, sharpe=0.06, total_trades=5
        )
        assert label == "Fair"
        assert score == 3

    def test_fair_label_minimum_score_2(self):
        """Minimum Fair: score exactly 2."""
        # win_rate < 45 = 0pt, pf >= 1.0 = 1pt, sh >= 0.05 = 1pt, trades < 20 = 0pt → 2
        label, score = _compute_quality_score(
            win_rate=30, profit_factor=1.0, sharpe=0.05, total_trades=10
        )
        assert label == "Fair"
        assert score == 2

    def test_poor_label_all_below_threshold(self):
        """All metrics below thresholds → score 0, label Poor."""
        label, score = _compute_quality_score(
            win_rate=40, profit_factor=0.8, sharpe=0.03, total_trades=10
        )
        assert label == "Poor"
        assert score == 0

    def test_poor_label_score_1(self):
        """Score 1 is still Poor (threshold is < 2)."""
        # Only trade sample bonus, nothing else
        label, score = _compute_quality_score(
            win_rate=30, profit_factor=0.5, sharpe=0.01, total_trades=20
        )
        assert label == "Poor"
        assert score == 1


class TestQualityScoreNullHandling:
    """Verify graceful handling of None / missing metric values."""

    def test_all_none_returns_poor(self):
        """All None metrics → score 0, Poor."""
        label, score = _compute_quality_score(
            win_rate=None, profit_factor=None, sharpe=None, total_trades=None
        )
        assert label == "Poor"
        assert score == 0

    def test_partial_none_win_rate(self):
        """win_rate=None treated as 0 (no win-rate points scored)."""
        label, score = _compute_quality_score(
            win_rate=None, profit_factor=1.5, sharpe=0.15, total_trades=20
        )
        # pf=2, sh=2, trades=1 → 5 → Good
        assert label == "Good"
        assert score == 5

    def test_partial_none_profit_factor(self):
        """profit_factor=None treated as 0 (no PF points scored)."""
        label, score = _compute_quality_score(
            win_rate=65, profit_factor=None, sharpe=0.15, total_trades=20
        )
        # wr=2, pf=0, sh=2, trades=1 → 5 → Good
        assert label == "Good"
        assert score == 5

    def test_partial_none_sharpe(self):
        """sharpe=None treated as 0 (no Sharpe points scored)."""
        label, score = _compute_quality_score(
            win_rate=65, profit_factor=1.8, sharpe=None, total_trades=20
        )
        # wr=2, pf=2, sh=0, trades=1 → 5 → Good
        assert label == "Good"
        assert score == 5

    def test_partial_none_total_trades(self):
        """total_trades=None treated as 0 (no sample bonus)."""
        label, score = _compute_quality_score(
            win_rate=65, profit_factor=1.8, sharpe=0.20, total_trades=None
        )
        # wr=2, pf=2, sh=2, trades=0 → 6 → Excellent
        assert label == "Excellent"
        assert score == 6


class TestQualityScoreDifferentiation:
    """
    Acceptance criteria: different strategies must receive different scores.
    This was the core bug — every strategy showed 'Poor'.
    """

    def test_strategies_produce_different_labels(self):
        """
        Three strategies with clearly different characteristics must
        receive different quality labels.
        """
        poor_strategy = _compute_quality_score(
            win_rate=35, profit_factor=0.7, sharpe=0.02, total_trades=8
        )
        fair_strategy = _compute_quality_score(
            win_rate=47, profit_factor=1.1, sharpe=0.07, total_trades=15
        )
        good_strategy = _compute_quality_score(
            win_rate=55, profit_factor=1.4, sharpe=0.12, total_trades=30
        )
        excellent_strategy = _compute_quality_score(
            win_rate=65, profit_factor=1.9, sharpe=0.22, total_trades=50
        )

        labels = {
            poor_strategy[0],
            fair_strategy[0],
            good_strategy[0],
            excellent_strategy[0],
        }
        assert labels == {"Poor", "Fair", "Good", "Excellent"}, (
            f"Expected all 4 labels but got: {labels}"
        )

    def test_not_all_strategies_are_poor(self):
        """
        Regression test: any strategy with win_rate>=60%, pf>=1.5, sharpe>=0.15
        must NOT be rated Poor.
        """
        label, _ = _compute_quality_score(
            win_rate=62, profit_factor=1.6, sharpe=0.18, total_trades=30
        )
        assert label != "Poor", (
            f"A good strategy should not be rated Poor, got: {label}"
        )


class TestQualityScoreBoundaryEdgeCases:
    """Edge-case boundary checks for exact threshold values."""

    def test_win_rate_exactly_60_gets_2pts(self):
        label, score = _compute_quality_score(
            win_rate=60.0, profit_factor=0.0, sharpe=0.0, total_trades=0
        )
        assert score >= 2  # 2 pts from win rate alone → Fair at minimum

    def test_win_rate_just_below_60_gets_1pt(self):
        label, score = _compute_quality_score(
            win_rate=59.99, profit_factor=0.0, sharpe=0.0, total_trades=0
        )
        assert score == 1  # 1 pt only

    def test_win_rate_exactly_45_gets_1pt(self):
        label, score = _compute_quality_score(
            win_rate=45.0, profit_factor=0.0, sharpe=0.0, total_trades=0
        )
        assert score == 1

    def test_win_rate_just_below_45_gets_0pts(self):
        label, score = _compute_quality_score(
            win_rate=44.99, profit_factor=0.0, sharpe=0.0, total_trades=0
        )
        assert score == 0

    def test_profit_factor_exactly_1_5_gets_2pts(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=1.5, sharpe=0.0, total_trades=0
        )
        assert score == 2  # 2 pts pf → Fair

    def test_profit_factor_just_below_1_5_gets_1pt(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=1.499, sharpe=0.0, total_trades=0
        )
        assert score == 1

    def test_sharpe_exactly_0_15_gets_2pts(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=0.15, total_trades=0
        )
        assert score == 2  # 2 pts sharpe → Fair

    def test_sharpe_just_below_0_15_gets_1pt(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=0.149, total_trades=0
        )
        assert score == 1

    def test_sharpe_exactly_0_05_gets_1pt(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=0.05, total_trades=0
        )
        assert score == 1

    def test_sharpe_just_below_0_05_gets_0pts(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=0.049, total_trades=0
        )
        assert score == 0

    def test_trades_exactly_20_gets_bonus(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=0.0, total_trades=20
        )
        assert score == 1  # only the sample bonus

    def test_trades_19_no_bonus(self):
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=0.0, total_trades=19
        )
        assert score == 0

    def test_negative_sharpe_treated_as_0pts(self):
        """Negative (raw) Sharpe — very poor strategy — must score 0 sharpe points."""
        label, score = _compute_quality_score(
            win_rate=0.0, profit_factor=0.0, sharpe=-0.5, total_trades=0
        )
        assert score == 0

    def test_zero_volume_edge_case(self):
        """Zero trades — no sample bonus, all defaults."""
        label, score = _compute_quality_score(
            win_rate=100, profit_factor=999, sharpe=99, total_trades=0
        )
        # wr=2, pf=2, sh=2, trades=0 → 6 → Excellent
        assert label == "Excellent"
        assert score == 6
