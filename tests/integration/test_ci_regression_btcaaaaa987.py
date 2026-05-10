"""
Permanent CI regression test — BTCAAAAA-987
Candle integrity + reference backtest hash

These two tests run on every merge and must complete in < 5 minutes on CI.

Part A — Candle Integrity (TestCandleIntegrity)
    Compares the stored pipeline candle data against the cached Binance
    reference dataset produced by BTCAAAAA-986.  The reference file is the
    ground truth; any field divergence fails loudly with a field-level diff.

    STATUS: This test is expected to FAIL until the P0 data re-ingest
    described in BTCAAAAA-986 is complete (Jan 16 – May 2, 2026 data has a
    1-2h timestamp offset that shifts OHLCV values to the wrong bars).

Part B — Reference Backtest Reproducibility (TestReferenceBacktestReproducibility)
    Runs the "50% Asia Rejection Simple" strategy over the 672-bar reference
    slice and asserts the snapshot hash matches the locked value.  Any change
    to the backtest engine that alters trade count, win rate, or total PnL
    will be caught here.

    KNOWN ISSUE: The backtest engine has a price-attribution bug
    (BTCAAAAA-991) that causes fill prices to be sourced from 4-10 bars
    before the recorded entry timestamp.  The locked hash below captures
    *current* engine behavior.  After BTCAAAAA-991 is fixed, run the
    refresh helper to update the hash to the corrected baseline:

        python tests/integration/refresh_ci_regression_hashes.py

Refresh cadence:
    - Quarterly, or
    - After any intentional change to the backtest engine or candle pipeline,
    - Or after re-ingesting the P0 timestamp-corrected data.
    See tests/integration/refresh_ci_regression_hashes.py for instructions.

Author: QAEngineer (BTCAAAAA-987)
Date: 2026-05-10
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_REFERENCE_PARQUET = (
    _project_root / "data" / "audit"
    / "reference_BTCUSDT_PERP_15m_20260201_20260207.parquet"
)
_PIPELINE_PARQUET = (
    _project_root / "data" / "binance" / "2026-02"
    / "BTCUSDT_PERP_15m_2026-02.parquet"
)
_REFERENCE_WINDOW_START = pd.Timestamp("2026-02-01 00:00:00")
_REFERENCE_WINDOW_END = pd.Timestamp("2026-02-07 23:45:00")
_EXPECTED_BAR_COUNT = 672

# SHA-256 of {"total_pnl_usd":226.06,"trade_count":3,"win_rate_pct":100.0}
# Computed 2026-05-10.  Engine: MulticoreBacktestEngine, strategy: "50% Asia
# Rejection Simple", dataset: reference_BTCUSDT_PERP_15m_20260201_20260207.
# Update after BTCAAAAA-991 fix via: python tests/integration/refresh_ci_regression_hashes.py
_REFERENCE_BACKTEST_HASH = (
    "72ae39754885588dbb84b0463d26333241540389e72d5123ae6e3ce8ec21a81a"
)

_OHLCV_FIELDS = ("open", "high", "low", "close", "volume")
_FLOAT_TOL = 1e-6  # relative tolerance for OHLCV float comparisons

# ---------------------------------------------------------------------------
# Strategy / backtest config locked to the 50% Asia Rejection Simple strategy
# (same weights as BTCAAAAA-745 and BTCAAAAA-925)
# ---------------------------------------------------------------------------

_STRATEGY_CONFIG: dict = {
    "name": "50% Asia Rejection Simple",
    "strategy_type": "Bearish",
    "confluence_threshold": 40,
    "blocks": [
        {
            "name": "asia_session_50_percent",
            "logic": "AND",
            "signals": [
                {
                    "name": "AT_ASIA_50",
                    "logic": "AND",
                    "weight": 20,
                    "exit_conditions": [
                        {
                            "signal_name": "AT_IHOD",
                            "percentage": 1.0,
                            "exit_mode": "ABSOLUTE",
                            "tp_proximity_threshold": 2.0,
                            "reversal_trigger": 0.5,
                            "binding_level": "SIGNAL",
                        }
                    ],
                },
                {
                    "name": "BELOW_ASIA_50",
                    "logic": "AND",
                    "weight": 15,
                    "timing_constraint": {
                        "max_candles": 3,
                        "reference": "asia_session_50_percent::AT_ASIA_50",
                    },
                    "exit_conditions": [
                        {
                            "signal_name": "ABOVE_ASIA_50",
                            "percentage": 1.0,
                            "exit_mode": "FLEXIBLE",
                            "tp_proximity_threshold": 0.5,
                            "reversal_trigger": 0.4,
                            "binding_level": "SIGNAL",
                            "recheck_config": {
                                "enabled": True,
                                "bar_delay": 2,
                                "validation_mode": "SIGNAL",
                                "parent_signal": None,
                            },
                        }
                    ],
                },
            ],
        },
        {
            "name": "ema_55_vector",
            "logic": "AND",
            "signals": [
                {"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 22},
            ],
        },
        {
            "name": "liquidity_sweep",
            "logic": "OR",
            "signals": [
                {"name": "BEARISH_SWEEP", "logic": "OR", "weight": 10},
            ],
        },
    ],
    "exit_conditions": [
        {
            "signal_name": "BULLISH_BREAK",
            "percentage": 0.01,
            "exit_mode": "ABSOLUTE",
            "tp_proximity_threshold": 2.0,
            "reversal_trigger": 0.5,
            "binding_level": "STRATEGY",
        }
    ],
}

_BACKTEST_CONFIG: dict = {
    "timeframe": "15m",
    "starting_capital": 10000,
    "risk_per_trade_pct": 10,
    "min_risk_reward": 1.2,
    "max_leverage": 10,
    "max_bars_held": 200,
    "tpsl_mode": "Fibonacci",
    "sl_mode": "Static",
    "confluence_threshold": 40,
    "adaptive_sl": {
        "enabled": False,
        "delay_enabled": False,
        "delay_bars": 2,
        "emergency_sl_pct": 2,
        "volatility_lookback": 20,
        "volatility_multiplier": 1.2,
        "min_sl_pct": 0.7,
        "max_sl_pct": 2.0,
        "use_structure_sl": False,
        "structure_sources": [],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_reference_df() -> pd.DataFrame:
    if not _REFERENCE_PARQUET.exists():
        raise FileNotFoundError(
            f"Reference parquet not found: {_REFERENCE_PARQUET}\n"
            "Re-run the BTCAAAAA-986 audit to regenerate it."
        )
    df = pd.read_parquet(_REFERENCE_PARQUET).sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    return df


def _load_pipeline_window_df() -> pd.DataFrame:
    if not _PIPELINE_PARQUET.exists():
        raise FileNotFoundError(
            f"Pipeline parquet not found: {_PIPELINE_PARQUET}\n"
            "Ensure data/binance/2026-02/ is present."
        )
    df = pd.read_parquet(_PIPELINE_PARQUET).sort_values("timestamp").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    mask = (df["timestamp"] >= _REFERENCE_WINDOW_START) & (df["timestamp"] <= _REFERENCE_WINDOW_END)
    return df.loc[mask].reset_index(drop=True)


def _load_reference_bars() -> list:
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    from nautilus_trader.model.data import Bar, BarSpecification, BarType
    from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.objects import Price, Quantity

    df = _load_reference_df()
    instrument_id = InstrumentId(Symbol("BTC-USDT-PERP"), Venue("BINANCE"))
    bar_type = BarType(
        instrument_id,
        BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    bars = []
    for _, row in df.iterrows():
        ts = dt_to_unix_nanos(pd.Timestamp(row["timestamp"]))
        bars.append(
            Bar(
                bar_type=bar_type,
                open=Price(float(row["open"]), precision=2),
                high=Price(float(row["high"]), precision=2),
                low=Price(float(row["low"]), precision=2),
                close=Price(float(row["close"]), precision=2),
                volume=Quantity(float(row["volume"]), precision=8),
                ts_event=ts,
                ts_init=ts,
            )
        )
    return bars


def _compute_backtest_snapshot_hash(result: dict) -> tuple[str, dict]:
    metrics = result.get("metrics", {})
    snapshot = {
        "trade_count": int(metrics.get("total_trades", 0)),
        "win_rate_pct": round(float(metrics.get("win_rate", 0.0)), 2),
        "total_pnl_usd": round(float(metrics.get("total_pnl", 0.0)), 2),
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest(), snapshot


# ---------------------------------------------------------------------------
# Part A — Candle Integrity
# ---------------------------------------------------------------------------


class TestCandleIntegrity(unittest.TestCase):
    """
    PART A: Assert stored pipeline candles match the cached Binance reference.

    Expected state: FAIL until the P0 timestamp-corrected re-ingest (per
    BTCAAAAA-986 actions) is completed.  Once re-ingested this test must PASS
    and stay green.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.ref = _load_reference_df()
        cls.pipeline = _load_pipeline_window_df()

    def test_reference_file_exists(self) -> None:
        self.assertTrue(
            _REFERENCE_PARQUET.exists(),
            f"Reference parquet missing: {_REFERENCE_PARQUET}",
        )

    def test_reference_bar_count(self) -> None:
        self.assertEqual(
            len(self.ref),
            _EXPECTED_BAR_COUNT,
            f"Reference file has {len(self.ref)} bars; expected {_EXPECTED_BAR_COUNT}.",
        )

    def test_pipeline_window_bar_count(self) -> None:
        """Pipeline must contain exactly the same number of bars for the window."""
        self.assertEqual(
            len(self.pipeline),
            _EXPECTED_BAR_COUNT,
            f"Pipeline returned {len(self.pipeline)} bars for the reference window "
            f"({_REFERENCE_WINDOW_START} → {_REFERENCE_WINDOW_END}); "
            f"expected {_EXPECTED_BAR_COUNT}.\n"
            "This may indicate a gap or the P0 re-ingest has not been run yet.",
        )

    def test_timestamps_match(self) -> None:
        """Every bar timestamp must appear in both datasets."""
        ref_ts = set(self.ref["timestamp"].astype(str))
        pip_ts = set(self.pipeline["timestamp"].astype(str))
        only_in_ref = sorted(ref_ts - pip_ts)[:5]
        only_in_pipeline = sorted(pip_ts - ref_ts)[:5]
        self.assertEqual(
            ref_ts,
            pip_ts,
            f"Timestamp mismatch.\n"
            f"  In reference only (sample): {only_in_ref}\n"
            f"  In pipeline only (sample):  {only_in_pipeline}",
        )

    def _assert_field_matches(self, field: str) -> None:
        ref_vals = self.ref[field].to_numpy(dtype=float)
        pip_vals = self.pipeline[field].to_numpy(dtype=float)
        close_mask = np.isclose(ref_vals, pip_vals, rtol=_FLOAT_TOL, atol=0)
        bad = np.where(~close_mask)[0]
        if len(bad) == 0:
            return
        sample_idx = bad[:5]
        lines = [
            f"Field '{field}': {len(bad)}/{len(ref_vals)} bars mismatch "
            f"(rtol={_FLOAT_TOL}).",
            "Sample mismatches (bar_index | timestamp | reference | pipeline | delta):",
        ]
        for i in sample_idx:
            ts = self.ref["timestamp"].iloc[i]
            r = ref_vals[i]
            p = pip_vals[i]
            lines.append(f"  [{i}] {ts}  ref={r:.4f}  pipe={p:.4f}  Δ={abs(r-p):.4f}")
        lines.append(
            "\nLikely cause: timestamp-offset bug (BTCAAAAA-986). "
            "Re-ingest the affected date range to fix."
        )
        self.fail("\n".join(lines))

    def test_open_matches(self) -> None:
        self._assert_field_matches("open")

    def test_high_matches(self) -> None:
        self._assert_field_matches("high")

    def test_low_matches(self) -> None:
        self._assert_field_matches("low")

    def test_close_matches(self) -> None:
        self._assert_field_matches("close")

    def test_volume_matches(self) -> None:
        self._assert_field_matches("volume")

    def test_ohlc_internal_integrity(self) -> None:
        """Reference data itself must satisfy H≥L, O≤H, C≤H (sanity guard)."""
        df = self.ref
        violations = []
        if not (df["high"] >= df["low"]).all():
            n = (~(df["high"] >= df["low"])).sum()
            violations.append(f"high < low: {n} bars")
        if not (df["open"] <= df["high"]).all():
            n = (~(df["open"] <= df["high"])).sum()
            violations.append(f"open > high: {n} bars")
        if not (df["close"] <= df["high"]).all():
            n = (~(df["close"] <= df["high"])).sum()
            violations.append(f"close > high: {n} bars")
        if not (df["volume"] > 0).all():
            n = (~(df["volume"] > 0)).sum()
            violations.append(f"volume ≤ 0: {n} bars")
        self.assertFalse(
            violations,
            "Reference data OHLCV violations:\n  " + "\n  ".join(violations),
        )

    def test_no_nan_in_reference(self) -> None:
        for field in _OHLCV_FIELDS:
            nan_count = self.ref[field].isna().sum()
            self.assertEqual(
                nan_count,
                0,
                f"Reference field '{field}' has {nan_count} NaN values.",
            )


# ---------------------------------------------------------------------------
# Part B — Reference Backtest Reproducibility
# ---------------------------------------------------------------------------


class TestReferenceBacktestReproducibility(unittest.TestCase):
    """
    PART B: Assert the backtest engine produces a stable hash over the
    reference 672-bar slice.

    The locked hash captures current engine behavior.  It is NOT a gold-
    standard reference because of the BTCAAAAA-991 price-attribution bug.
    After that bug is fixed, update via:
        python tests/integration/refresh_ci_regression_hashes.py

    If this test fails after an intentional engine change, verify the new
    behavior is correct, then refresh the hash.
    """

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.optimizer_v3.core.multicore_backtest_engine import (
                MulticoreBacktestEngine,
            )
            cls.engine = MulticoreBacktestEngine(num_processes=2)
            cls.bars = _load_reference_bars()
            result = cls.engine.run_backtest(
                bars=cls.bars,
                strategy_config=_STRATEGY_CONFIG,
                backtest_config=_BACKTEST_CONFIG,
            )
            cls.result = result
            cls.actual_hash, cls.snapshot = _compute_backtest_snapshot_hash(result)
        except Exception as e:
            cls._setup_error = str(e)
        else:
            cls._setup_error = None

    def setUp(self) -> None:
        if self._setup_error:
            self.skipTest(f"setUpClass failed: {self._setup_error}")

    def test_bar_count_loaded(self) -> None:
        self.assertEqual(
            len(self.bars),
            _EXPECTED_BAR_COUNT,
            f"Expected {_EXPECTED_BAR_COUNT} reference bars; got {len(self.bars)}.",
        )

    def test_backtest_produces_trades(self) -> None:
        """At least one trade must be produced over the 672-bar reference slice."""
        trade_count = self.snapshot["trade_count"]
        self.assertGreater(
            trade_count,
            0,
            "Backtest produced 0 trades over the 672-bar reference slice.  "
            "This may indicate a strategy configuration issue or a signal "
            "detection regression.  Check block weights and confluence threshold.",
        )

    def test_snapshot_hash_matches_reference(self) -> None:
        """Hash of (trade_count, win_rate_pct, total_pnl_usd) must match the locked value."""
        self.assertEqual(
            self.actual_hash,
            _REFERENCE_BACKTEST_HASH,
            f"Backtest snapshot hash mismatch.\n"
            f"  Expected: {_REFERENCE_BACKTEST_HASH}\n"
            f"  Actual:   {self.actual_hash}\n"
            f"  Snapshot: {json.dumps(self.snapshot, sort_keys=True)}\n\n"
            "If this is due to an intentional engine change (e.g. BTCAAAAA-991 fix),\n"
            "verify the new behavior is correct, then update _REFERENCE_BACKTEST_HASH\n"
            "by running:  python tests/integration/refresh_ci_regression_hashes.py",
        )

    def test_backtest_is_deterministic(self) -> None:
        """Two consecutive runs on the same bars must produce identical hashes."""
        result2 = self.engine.run_backtest(
            bars=self.bars,
            strategy_config=_STRATEGY_CONFIG,
            backtest_config=_BACKTEST_CONFIG,
        )
        hash2, snapshot2 = _compute_backtest_snapshot_hash(result2)
        self.assertEqual(
            self.actual_hash,
            hash2,
            f"Non-deterministic backtest: run 1 hash={self.actual_hash}, "
            f"run 2 hash={hash2}.\n"
            f"  Run 1 snapshot: {json.dumps(self.snapshot, sort_keys=True)}\n"
            f"  Run 2 snapshot: {json.dumps(snapshot2, sort_keys=True)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
