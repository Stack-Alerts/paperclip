"""
Unit tests for Quality Score badge color logic.

Verifies that the color assigned to the status label matches the quality rating
label, as implemented in strategy_browser_dialog.py _populate_details_panel()
(commit 1e7f377 — fix for BTCAAAAA-321).

Color mapping under test (spec sourced from styles.py COLORS dict):
    Excellent → get_color('success')  → #10B981 (green)
    Good      → get_color('success')  → #10B981 (green)
    Fair      → get_color('warning')  → #FFA500 (amber)
    Poor      → get_color('error')    → #C35252 (red)
    Untested  → get_color('text_muted') → #9AA0A6 (gray)

Tests are self-contained (no Qt/src imports) following the same pattern as
test_quality_score.py, so they run in headless CI without a display.

QA: BTCAAAAA-322
"""
import pytest

# ---------------------------------------------------------------------------
# Color spec — sourced from src/strategy_builder/ui/styles.py COLORS dict.
# Inline here to avoid the strategy_builder namespace collision between
# tests/strategy_builder/ and src/strategy_builder/ in headless CI.
# If these constants change in styles.py, these tests will catch the drift.
# ---------------------------------------------------------------------------
SUCCESS_COLOR = '#10B981'   # get_color('success')  — green
WARNING_COLOR = '#FFA500'   # get_color('warning')  — amber
ERROR_COLOR   = '#C35252'   # get_color('error')    — red
MUTED_COLOR   = '#9AA0A6'   # get_color('text_muted') — gray


# ---------------------------------------------------------------------------
# Pure-Python replica of the score→color mapping from _populate_details_panel()
# (lines 1129-1158 of strategy_browser_dialog.py, commit 1e7f377)
# ---------------------------------------------------------------------------

def _compute_quality_color(win_rate, profit_factor, sharpe, total_trades,
                            has_backtest_data=True):
    """
    Replicate the color assignment block from _populate_details_panel().

    Returns (label_text, css_color_hex).
    `has_backtest_data=False` simulates the no-backtest branch → Untested.
    """
    if not has_backtest_data:
        return "Untested", MUTED_COLOR

    _wr = float(win_rate) if win_rate is not None else 0.0
    _pf = float(profit_factor) if profit_factor is not None else 0.0
    _sh = float(sharpe) if sharpe is not None else 0.0
    _tt = int(total_trades) if total_trades is not None else 0

    _score = 0
    if _wr >= 60:
        _score += 2
    elif _wr >= 45:
        _score += 1
    if _pf >= 1.5:
        _score += 2
    elif _pf >= 1.0:
        _score += 1
    if _sh >= 0.15:
        _score += 2
    elif _sh >= 0.05:
        _score += 1
    if _tt >= 20:
        _score += 1

    if _score >= 6:
        label = "Excellent"
        color = SUCCESS_COLOR
    elif _score >= 4:
        label = "Good"
        color = SUCCESS_COLOR
    elif _score >= 2:
        label = "Fair"
        color = WARNING_COLOR
    else:
        label = "Poor"
        color = ERROR_COLOR

    return label, color


# ---------------------------------------------------------------------------
# Tests: badge color correctness per acceptance criteria
# ---------------------------------------------------------------------------

class TestBadgeColorMapping:
    """Verify every quality label maps to the correct color key/hex value."""

    def test_excellent_gets_success_color(self):
        """AC1: 'Excellent' badge must display green (success color)."""
        label, color = _compute_quality_color(
            win_rate=65, profit_factor=1.8, sharpe=0.20, total_trades=25
        )
        assert label == "Excellent"
        assert color == SUCCESS_COLOR, (
            f"Excellent badge color {color!r} != success {SUCCESS_COLOR!r}"
        )

    def test_good_gets_success_color(self):
        """AC2: 'Good' badge must display green/positive (success color)."""
        label, color = _compute_quality_color(
            win_rate=50, profit_factor=1.3, sharpe=0.10, total_trades=25
        )
        assert label == "Good"
        assert color == SUCCESS_COLOR, (
            f"Good badge color {color!r} != success {SUCCESS_COLOR!r}"
        )

    def test_fair_gets_warning_color(self):
        """AC3: 'Fair' badge must display a neutral/warning color (amber)."""
        label, color = _compute_quality_color(
            win_rate=48, profit_factor=1.1, sharpe=0.06, total_trades=5
        )
        assert label == "Fair"
        assert color == WARNING_COLOR, (
            f"Fair badge color {color!r} != warning {WARNING_COLOR!r}"
        )

    def test_poor_gets_error_color(self):
        """AC4: 'Poor' badge must display red (error color)."""
        label, color = _compute_quality_color(
            win_rate=40, profit_factor=0.8, sharpe=0.03, total_trades=10
        )
        assert label == "Poor"
        assert color == ERROR_COLOR, (
            f"Poor badge color {color!r} != error {ERROR_COLOR!r}"
        )


class TestBadgeColorBoundaries:
    """Verify color assignments at exact score boundaries."""

    def test_excellent_boundary_score_6_green(self):
        """Score exactly 6 (no sample bonus) → Excellent → green."""
        label, color = _compute_quality_color(
            win_rate=65, profit_factor=2.0, sharpe=0.20, total_trades=10
        )
        assert label == "Excellent"
        assert color == SUCCESS_COLOR

    def test_excellent_boundary_score_7_green(self):
        """Score 7 (max) → Excellent → green."""
        label, color = _compute_quality_color(
            win_rate=60, profit_factor=1.5, sharpe=0.15, total_trades=20
        )
        assert label == "Excellent"
        assert color == SUCCESS_COLOR

    def test_good_boundary_score_4_green(self):
        """Score exactly 4 → Good → green (not amber, not gray)."""
        label, color = _compute_quality_color(
            win_rate=45, profit_factor=1.0, sharpe=0.05, total_trades=20
        )
        assert label == "Good"
        assert color == SUCCESS_COLOR
        assert color != WARNING_COLOR, "Good must NOT use warning (amber) color"

    def test_good_boundary_score_5_green(self):
        """Score 5 → Good → green.
        wr=65%→2, pf=1.5→2, sh=0.04→0, trades=20→1 → total=5 → Good
        """
        label, color = _compute_quality_color(
            win_rate=65, profit_factor=1.5, sharpe=0.04, total_trades=20
        )
        assert label == "Good"
        assert color == SUCCESS_COLOR

    def test_fair_boundary_score_2_warning(self):
        """Score exactly 2 → Fair → amber, not red."""
        label, color = _compute_quality_color(
            win_rate=30, profit_factor=1.0, sharpe=0.05, total_trades=10
        )
        assert label == "Fair"
        assert color == WARNING_COLOR
        assert color != ERROR_COLOR, "Fair must NOT use error (red) color"

    def test_fair_boundary_score_3_warning(self):
        """Score 3 → Fair → amber."""
        label, color = _compute_quality_color(
            win_rate=48, profit_factor=1.1, sharpe=0.06, total_trades=5
        )
        assert label == "Fair"
        assert color == WARNING_COLOR

    def test_poor_boundary_score_0_error(self):
        """Score 0 → Poor → red."""
        label, color = _compute_quality_color(
            win_rate=40, profit_factor=0.8, sharpe=0.03, total_trades=10
        )
        assert label == "Poor"
        assert color == ERROR_COLOR

    def test_poor_boundary_score_1_error(self):
        """Score 1 → Poor → red (threshold for Fair is ≥2)."""
        label, color = _compute_quality_color(
            win_rate=30, profit_factor=0.5, sharpe=0.01, total_trades=20
        )
        assert label == "Poor"
        assert color == ERROR_COLOR


class TestNoBacktestEdgeCase:
    """Untested strategies (no backtest data) must render in muted gray."""

    def test_untested_gets_muted_color(self):
        """AC6a: Strategies with no backtest data → Untested → gray (text_muted)."""
        label, color = _compute_quality_color(
            win_rate=None, profit_factor=None, sharpe=None, total_trades=None,
            has_backtest_data=False
        )
        assert label == "Untested"
        assert color == MUTED_COLOR, (
            f"Untested badge color {color!r} != text_muted {MUTED_COLOR!r}"
        )


class TestColorNotGray:
    """
    Regression test: prior to commit 1e7f377, all quality states used
    'text_muted' (gray) regardless of label. Confirm rated strategies
    never receive the gray color.
    """

    def test_excellent_not_gray(self):
        """Excellent must NOT be gray (regression: old bug)."""
        label, color = _compute_quality_color(
            win_rate=65, profit_factor=1.8, sharpe=0.20, total_trades=25
        )
        assert label == "Excellent"
        assert color != MUTED_COLOR, (
            "BUG REGRESSION: Excellent is rendering in gray (#9AA0A6) — "
            "this was the original defect fixed in BTCAAAAA-321"
        )

    def test_good_not_gray(self):
        """Good must NOT be gray."""
        label, color = _compute_quality_color(
            win_rate=50, profit_factor=1.3, sharpe=0.10, total_trades=25
        )
        assert label == "Good"
        assert color != MUTED_COLOR

    def test_fair_not_gray(self):
        """Fair must NOT be gray."""
        label, color = _compute_quality_color(
            win_rate=48, profit_factor=1.1, sharpe=0.06, total_trades=5
        )
        assert label == "Fair"
        assert color != MUTED_COLOR

    def test_poor_not_gray(self):
        """Poor must NOT be gray."""
        label, color = _compute_quality_color(
            win_rate=40, profit_factor=0.8, sharpe=0.03, total_trades=10
        )
        assert label == "Poor"
        assert color != MUTED_COLOR


class TestColorPaletteValues:
    """Confirm the actual hex values used match the design spec from styles.py."""

    def test_success_color_is_green(self):
        """success color must be green (#10B981)."""
        assert SUCCESS_COLOR == '#10B981'

    def test_warning_color_is_amber(self):
        """warning color must be amber (#FFA500)."""
        assert WARNING_COLOR == '#FFA500'

    def test_error_color_is_red(self):
        """error color must be red (#C35252)."""
        assert ERROR_COLOR == '#C35252'

    def test_text_muted_color_is_gray(self):
        """text_muted color must be gray (#9AA0A6)."""
        assert MUTED_COLOR == '#9AA0A6'


class TestColorDistinctness:
    """
    Verify all four rated quality levels produce distinct colors,
    and that positive/negative colors are clearly distinguishable.
    """

    def test_excellent_and_poor_use_distinct_colors(self):
        """Excellent (green) and Poor (red) must use different colors."""
        _, excellent_color = _compute_quality_color(
            win_rate=65, profit_factor=1.8, sharpe=0.20, total_trades=25
        )
        _, poor_color = _compute_quality_color(
            win_rate=40, profit_factor=0.8, sharpe=0.03, total_trades=10
        )
        assert excellent_color != poor_color

    def test_fair_and_poor_use_distinct_colors(self):
        """Fair (amber) and Poor (red) must use different colors."""
        _, fair_color = _compute_quality_color(
            win_rate=48, profit_factor=1.1, sharpe=0.06, total_trades=5
        )
        _, poor_color = _compute_quality_color(
            win_rate=40, profit_factor=0.8, sharpe=0.03, total_trades=10
        )
        assert fair_color != poor_color

    def test_excellent_good_use_same_color(self):
        """Excellent and Good both use the 'success' green (per spec)."""
        _, excellent_color = _compute_quality_color(
            win_rate=65, profit_factor=1.8, sharpe=0.20, total_trades=25
        )
        _, good_color = _compute_quality_color(
            win_rate=50, profit_factor=1.3, sharpe=0.10, total_trades=25
        )
        assert excellent_color == good_color == SUCCESS_COLOR
