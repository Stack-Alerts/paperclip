"""
Tests — PositionSizer (Section F)
===================================
Covers:
- Fixed-fraction sizing with ATR
- Fixed-fraction sizing with explicit stop distance
- Fixed-fraction fallback (default stop pct)
- Kelly Criterion sizing
- Kelly with negative edge (returns 0)
- Quantity clamping to MAX_QUANTITY and MIN_QUANTITY
- Config validation
- PositionSizeResult fields
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from src.itm.risk.position_sizer import (
    PositionSizer,
    PositionSizerConfig,
    SizingMode,
    MAX_QUANTITY,
    MIN_QUANTITY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sizer(
    mode=SizingMode.FIXED_FRACTION,
    risk_fraction="0.01",
    atr_multiplier="1.5",
    kelly_fraction="0.25",
    default_stop_pct="0.02",
):
    config = PositionSizerConfig(
        mode=mode,
        risk_fraction=Decimal(risk_fraction),
        atr_multiplier=Decimal(atr_multiplier),
        kelly_fraction=Decimal(kelly_fraction),
        default_stop_pct=Decimal(default_stop_pct),
    )
    return PositionSizer(config=config)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestPositionSizerConfig:

    def test_defaults_valid(self):
        cfg = PositionSizerConfig()
        assert cfg.risk_fraction == Decimal("0.01")
        assert cfg.mode == SizingMode.FIXED_FRACTION

    def test_zero_risk_fraction_rejected(self):
        with pytest.raises(ValueError, match="risk_fraction"):
            PositionSizerConfig(risk_fraction=Decimal("0"))

    def test_zero_atr_multiplier_rejected(self):
        with pytest.raises(ValueError, match="atr_multiplier"):
            PositionSizerConfig(atr_multiplier=Decimal("0"))

    def test_kelly_fraction_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="kelly_fraction"):
            PositionSizerConfig(kelly_fraction=Decimal("1.5"))


# ---------------------------------------------------------------------------
# Fixed-Fraction with ATR
# ---------------------------------------------------------------------------

class TestFixedFractionWithATR:

    def test_basic_sizing(self):
        # capital=25000, risk=1%, ATR=500, multiplier=1.5 → stop=750
        # qty = (25000 × 0.01) / 750 = 250 / 750 ≈ 0.333 BTC
        sizer = make_sizer(risk_fraction="0.01", atr_multiplier="1.5")
        result = sizer.size(
            capital=Decimal("25000"),
            entry_price=Decimal("45000"),
            atr=Decimal("500"),
        )
        expected_stop = Decimal("500") * Decimal("1.5")   # 750
        expected_qty = (Decimal("25000") * Decimal("0.01")) / expected_stop
        assert result.stop_distance == expected_stop
        assert result.quantity == expected_qty
        assert result.sizing_mode == SizingMode.FIXED_FRACTION
        assert result.capped is False

    def test_notional_computed(self):
        sizer = make_sizer()
        result = sizer.size(
            capital=Decimal("25000"),
            entry_price=Decimal("45000"),
            atr=Decimal("500"),
        )
        assert result.notional == result.quantity * Decimal("45000")

    def test_risk_amount_computed(self):
        sizer = make_sizer(risk_fraction="0.01", atr_multiplier="1.5")
        result = sizer.size(
            capital=Decimal("25000"),
            entry_price=Decimal("45000"),
            atr=Decimal("500"),
        )
        expected_risk = result.quantity * result.stop_distance
        assert result.risk_amount == expected_risk


# ---------------------------------------------------------------------------
# Fixed-Fraction with explicit stop distance
# ---------------------------------------------------------------------------

class TestFixedFractionExplicitStop:

    def test_explicit_stop_overrides_atr(self):
        sizer = make_sizer(risk_fraction="0.02", atr_multiplier="2.0")
        result = sizer.size(
            capital=Decimal("10000"),
            entry_price=Decimal("50000"),
            atr=Decimal("1000"),
            stop_distance_usdt=Decimal("500"),   # override
        )
        # Should use 500, not 2000
        assert result.stop_distance == Decimal("500")

    def test_zero_stop_distance_rejected(self):
        sizer = make_sizer()
        with pytest.raises(ValueError, match="positive"):
            sizer.size(
                capital=Decimal("10000"),
                entry_price=Decimal("50000"),
                stop_distance_usdt=Decimal("0"),
            )


# ---------------------------------------------------------------------------
# Default stop pct fallback
# ---------------------------------------------------------------------------

class TestDefaultStopPct:

    def test_fallback_when_no_atr_or_stop(self):
        # default_stop_pct=0.02; entry=50000 → stop_dist=1000
        sizer = make_sizer(default_stop_pct="0.02")
        result = sizer.size(
            capital=Decimal("10000"),
            entry_price=Decimal("50000"),
        )
        assert result.stop_distance == Decimal("1000")


# ---------------------------------------------------------------------------
# Quantity clamping
# ---------------------------------------------------------------------------

class TestQuantityClamping:

    def test_capped_at_max_quantity(self):
        # Very small risk_fraction results in large qty → should cap at 1.0 BTC
        # capital=1000000, risk=10%, stop=100 → qty = 100000/100 = 1000 → cap to 1.0
        sizer = make_sizer(risk_fraction="0.10")
        result = sizer.size(
            capital=Decimal("1000000"),
            entry_price=Decimal("50000"),
            stop_distance_usdt=Decimal("100"),
        )
        assert result.quantity == MAX_QUANTITY
        assert result.capped is True

    def test_min_quantity_floor(self):
        # Very large stop distance → qty rounds below min → should return MIN
        # capital=100, risk=1%, stop=10000 → qty = 1/10000 = 0.0001 < MIN 0.001 → floor
        sizer = make_sizer(risk_fraction="0.01")
        result = sizer.size(
            capital=Decimal("100"),
            entry_price=Decimal("50000"),
            stop_distance_usdt=Decimal("10000"),
        )
        assert result.quantity == MIN_QUANTITY

    def test_zero_capital_raises(self):
        sizer = make_sizer()
        with pytest.raises(ValueError, match="capital"):
            sizer.size(capital=Decimal("0"), entry_price=Decimal("50000"))

    def test_zero_entry_price_raises(self):
        sizer = make_sizer()
        with pytest.raises(ValueError, match="entry_price"):
            sizer.size(capital=Decimal("10000"), entry_price=Decimal("0"))


# ---------------------------------------------------------------------------
# Kelly Criterion
# ---------------------------------------------------------------------------

class TestKellySizing:

    def test_kelly_positive_edge(self):
        # win_rate=0.6, win_loss_ratio=2, loss_rate=0.4
        # full_kelly = (0.6×2 - 0.4) / 2 = (1.2 - 0.4)/2 = 0.4
        # frac_kelly = 0.4 × 0.25 = 0.10
        # qty = (10000 × 0.10) / 500 = 1000/500 = 2.0 → capped at 1.0
        sizer = make_sizer(mode=SizingMode.KELLY, kelly_fraction="0.25")
        result = sizer.size(
            capital=Decimal("10000"),
            entry_price=Decimal("50000"),
            stop_distance_usdt=Decimal("500"),
            win_rate=Decimal("0.6"),
            win_loss_ratio=Decimal("2"),
        )
        assert result.sizing_mode == SizingMode.KELLY
        assert result.quantity <= MAX_QUANTITY

    def test_kelly_negative_edge_returns_zero(self):
        # win_rate=0.3, win_loss_ratio=1 → full_kelly = (0.3×1 - 0.7)/1 = -0.4 → no trade
        sizer = make_sizer(mode=SizingMode.KELLY)
        result = sizer.size(
            capital=Decimal("10000"),
            entry_price=Decimal("50000"),
            stop_distance_usdt=Decimal("500"),
            win_rate=Decimal("0.3"),
            win_loss_ratio=Decimal("1"),
        )
        assert result.quantity == Decimal("0")

    def test_kelly_falls_back_without_win_rate(self):
        sizer = make_sizer(mode=SizingMode.KELLY, risk_fraction="0.01")
        # No win_rate provided → falls back to fixed-fraction
        result = sizer.size(
            capital=Decimal("10000"),
            entry_price=Decimal("50000"),
            stop_distance_usdt=Decimal("500"),
        )
        assert result.sizing_mode == SizingMode.FIXED_FRACTION

    def test_kelly_zero_win_loss_ratio_raises(self):
        sizer = make_sizer(mode=SizingMode.KELLY)
        with pytest.raises(ValueError, match="win_loss_ratio"):
            sizer.size(
                capital=Decimal("10000"),
                entry_price=Decimal("50000"),
                stop_distance_usdt=Decimal("500"),
                win_rate=Decimal("0.6"),
                win_loss_ratio=Decimal("0"),
            )
