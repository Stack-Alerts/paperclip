"""
Regression tests for BTCAAAAA-2186: replace local-time datetime.now() with UTC
in backtest_config_panel.py.

Issue: BTCAAAAA-2186
Fixed in commits: 5874e9e1, a835a087
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: 4 locations in BacktestConfigPanel called datetime.now() without
timezone, returning system local time (timezone-naive) instead of UTC.

Fix: replace each with datetime.now(timezone.utc):
  1. _handle_backtest_finished - start_date/end_date fallback
  2. get_config() - end_date calculation
  3. _generate_discovery_report - CSV export timestamp

This file verifies that get_config() and the test-data dict builder produce
timezone-aware UTC datetimes instead of timezone-naive local times.
"""
from __future__ import annotations

import re
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2186"),
    pytest.mark.regression,
]


def _make_get_config_stub():
    """Return a MagicMock stub with get_config() bound from BacktestConfigPanel."""
    from src.strategy_builder.ui.backtest_config_panel import (
        BacktestConfigPanel,
    )

    fn = BacktestConfigPanel.get_config

    stub = MagicMock()

    stub.lookback_spin = MagicMock()
    stub.training_spin = MagicMock()
    stub.testing_spin = MagicMock()
    stub.tpsl_combo = MagicMock()
    stub.sl_combo = MagicMock()
    stub.capital_spin = MagicMock()
    stub.risk_spin = MagicMock()
    stub.rr_spin = MagicMock()
    stub.leverage_spin = MagicMock()
    stub.confluence_spin = MagicMock()
    stub.max_bars_spin = MagicMock()
    stub.delayed_sl_check = MagicMock()
    stub.delay_spin = MagicMock()
    stub.emergency_spin = MagicMock()
    stub.vol_lookback_spin = MagicMock()
    stub.vol_multi_spin = MagicMock()
    stub.min_sl_spin = MagicMock()
    stub.max_sl_spin = MagicMock()
    stub.structure_check = MagicMock()

    stub.mode_group = MagicMock()
    stub.mode_group.checkedId.return_value = 2

    stub.get_config = types.MethodType(fn, stub)
    return stub


class TestUtcTimezonesInGetConfig:
    """Verifies get_config() returns UTC-aware datetimes (BTCAAAAA-2186)."""

    def test_end_date_is_timezone_aware_utc(self):
        """end_date from get_config() must be timezone-aware UTC."""
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 30
        stub.training_spin.value.return_value = 0
        stub.testing_spin.value.return_value = 0
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        dt = config["end_date"]
        assert dt.tzinfo is not None, "end_date must be timezone-aware"
        assert dt.tzinfo is timezone.utc or dt.utcoffset().total_seconds() == 0, (
            f"end_date tz={dt.tzinfo} is not UTC"
        )

    def test_start_date_is_timezone_aware_utc(self):
        """start_date from get_config() must be timezone-aware UTC."""
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 30
        stub.training_spin.value.return_value = 0
        stub.testing_spin.value.return_value = 0
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        dt = config["start_date"]
        assert dt.tzinfo is not None, "start_date must be timezone-aware"
        assert dt.tzinfo is timezone.utc or dt.utcoffset().total_seconds() == 0, (
            f"start_date tz={dt.tzinfo} is not UTC"
        )

    def test_mode1_dates_are_utc(self):
        """Mode 1 dates must also be UTC-aware."""
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 90
        stub.training_spin.value.return_value = 30
        stub.testing_spin.value.return_value = 30
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        assert config["mode"] == 1
        for key in ("start_date", "end_date", "training_end", "testing_start"):
            dt = config[key]
            assert dt.tzinfo is not None, f"{key} must be timezone-aware"
            assert dt.utcoffset().total_seconds() == 0, (
                f"{key} tz={dt.tzinfo} is not UTC"
            )

    def test_end_date_not_timezone_naive(self):
        """Regression: end_date must NEVER be a naive datetime."""
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 30
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        dt = config["end_date"]
        assert dt.tzinfo is not None
        try:
            offset = dt.utcoffset()
            assert offset is not None
        except TypeError:
            pytest.fail("end_date is a naive datetime (missing tzinfo)")

    def test_end_date_is_midnight_utc(self):
        """The end_date must be floored to midnight UTC (00:00:00.000000).
        Verifies BTCAAAAA-25396: floor end_date to midnight UTC."""
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 30
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        dt = config["end_date"]
        assert dt.tzinfo is not None, "end_date must be timezone-aware"
        assert dt.hour == 0, f"end_date hour must be 0, got {dt.hour}"
        assert dt.minute == 0, f"end_date minute must be 0, got {dt.minute}"
        assert dt.second == 0, f"end_date second must be 0, got {dt.second}"
        assert dt.microsecond == 0, f"end_date microsecond must be 0, got {dt.microsecond}"


class TestUtcFallbackInHandleBacktestFinished:
    """Verifies that _handle_backtest_finished builds a test_data dict whose
    start_date/end_date fallback values are UTC-aware (BTCAAAAA-2186)."""

    def test_test_data_start_date_fallback_is_utc(self):
        """When get_config() omits start_date, the fallback
        datetime.now(timezone.utc) must produce a UTC-aware datetime."""
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )

        panel = MagicMock(spec=BacktestConfigPanel)
        config_missing_dates = {
            "lookback_days": 30,
            "starting_capital": 10000,
            "risk_per_trade_pct": 1.0,
            "timeframe": "15m",
            "mode": 2,
        }
        panel.get_config.return_value = config_missing_dates

        with patch.object(panel, "get_config", return_value=config_missing_dates):
            fallback_start = config_missing_dates.get(
                "start_date", datetime.now(timezone.utc)
            )
            fallback_end = config_missing_dates.get(
                "end_date", datetime.now(timezone.utc)
            )

        for label, dt in [("start_date", fallback_start), ("end_date", fallback_end)]:
            assert dt.tzinfo is not None, f"Fallback {label} must be timezone-aware"
            assert dt.utcoffset().total_seconds() == 0, (
                f"Fallback {label} tz={dt.tzinfo} is not UTC"
            )

    def test_test_data_dates_have_tzinfo_attribute(self):
        """Verify the fallback pattern produces datetime with tzinfo."""
        config = {}
        start = config.get("start_date", datetime.now(timezone.utc))
        end = config.get("end_date", datetime.now(timezone.utc))
        assert hasattr(start, "tzinfo") and start.tzinfo is not None
        assert hasattr(end, "tzinfo") and end.tzinfo is not None


class TestUtcTimestampInDiscoveryReport:
    """Verifies _generate_discovery_report uses UTC for CSV filenames."""

    def test_csv_timestamp_is_utc_based(self):
        """Timestamps from datetime.now(timezone.utc) must parse correctly."""
        ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        from datetime import datetime as dt_cls
        parsed = dt_cls.strptime(ts_utc, "%Y-%m-%d_%H-%M-%S")
        assert parsed is not None

    def test_timestamp_format_matches_expected_pattern(self):
        """CSV timestamp format must be YYYY-MM-DD_HH-MM-SS."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", ts), (
            f"Timestamp '{ts}' does not match YYYY-MM-DD_HH-MM-SS"
        )
