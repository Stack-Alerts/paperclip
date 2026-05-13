"""
Regression tests for BTCAAAAA-2187: Mode 1 data window math — include
training_days + testing_days in start_date.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-2187
Fixed in commit: c051bec
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause:
  get_config() always computed start_date = end_date - lookback_days,
  ignoring training_days and testing_days. In Mode 1 this caused the
  testing window to be silently truncated/expanded when lookback_days
  != training_days + testing_days.

Fix:
  Mode 1: start_date = end_date - (training_days + testing_days)
  Mode 2: start_date = end_date - lookback_days (unchanged)
"""
from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2187"),
    pytest.mark.regression,
]


def _make_get_config_stub():
    """Return a MagicMock stub with get_config() bound from the real class."""
    from src.strategy_builder.ui.backtest_config_panel import (
        BacktestConfigPanel,
    )

    fn = BacktestConfigPanel.get_config

    stub = MagicMock()

    # Wire up spinbox mocks
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

    # Mode selector mock
    stub.mode_group = MagicMock()
    stub.mode_group.checkedId.return_value = 1  # default Mode 1

    stub.get_config = types.MethodType(fn, stub)
    return stub


class TestMode1DataWindowMath:
    """Verifies get_config() computes start_date correctly for Mode 1 vs 2."""

    def _approx_now(self, dt: datetime) -> datetime:
        return dt.replace(microsecond=0)

    def test_mode1_start_date_uses_training_plus_testing(self):
        """
        Mode 1 with training_days=30, testing_days=30 yields
        start_date = end_date - 60 days.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 30
        stub.testing_spin.value.return_value = 30
        stub.lookback_spin.value.return_value = 90  # deliberately different
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=60)
        )
        actual_start = self._approx_now(config["start_date"])

        assert config["mode"] == 1
        assert actual_start == expected_start, (
            f"Mode 1: expected start_date={expected_start} "
            f"but got {actual_start}"
        )
        assert config["training_end"] == config["testing_start"]
        assert config["training_end"] == config["start_date"] + timedelta(
            days=30
        )

    def test_mode2_start_date_uses_lookback_days(self):
        """
        Mode 2 with lookback_days=30 yields start_date = end_date - 30 days
        (unchanged behaviour).
        """
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 30
        stub.training_spin.value.return_value = 60
        stub.testing_spin.value.return_value = 60
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=30)
        )
        actual_start = self._approx_now(config["start_date"])

        assert config["mode"] == 2
        assert actual_start == expected_start, (
            f"Mode 2: expected start_date={expected_start} "
            f"but got {actual_start}"
        )
        assert "training_window" not in config, (
            "Mode 2 must not include training_window"
        )
        assert "testing_window" not in config, (
            "Mode 2 must not include testing_window"
        )

    def test_mode1_with_mismatched_lookback(self):
        """
        Mode 1: start_date is NOT affected by lookback_days.
        Even when lookback_days is set to 10, start_date is derived from
        training_days + testing_days (= 60).
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 40
        stub.testing_spin.value.return_value = 20
        stub.lookback_spin.value.return_value = 10  # much smaller
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=60)
        )
        actual_start = self._approx_now(config["start_date"])

        assert actual_start == expected_start, (
            f"Mode 1 with mismatched lookback: expected start_date="
            f"{expected_start} but got {actual_start}"
        )
        assert config["training_window"] == 40
        assert config["testing_window"] == 20

    def test_mode1_training_end_testing_start_are_identical(self):
        """
        The split point between training and testing is contiguous:
        training_end == testing_start, and testing_start + testing_days
        lands at end_date.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 45
        stub.testing_spin.value.return_value = 15
        stub.lookback_spin.value.return_value = 999
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        assert config["training_end"] == config["testing_start"]
        actual_testing_days = (
            config["end_date"] - config["testing_start"]
        ).days
        assert actual_testing_days == 15, (
            f"Testing window should be exactly 15 days, "
            f"but got {actual_testing_days}"
        )

    def test_mode1_zero_training_days(self):
        """
        Mode 1 with training_days=0: start_date = end_date - testing_days.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 0
        stub.testing_spin.value.return_value = 30
        stub.lookback_spin.value.return_value = 100
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=30)
        )
        actual_start = self._approx_now(config["start_date"])

        assert config["mode"] == 1
        assert actual_start == expected_start
        assert config["training_window"] == 0
        assert config["testing_window"] == 30

    def test_mode1_zero_testing_days(self):
        """
        Mode 1 with testing_days=0: start_date = end_date - training_days.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 60
        stub.testing_spin.value.return_value = 0
        stub.lookback_spin.value.return_value = 100
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=60)
        )
        actual_start = self._approx_now(config["start_date"])

        assert actual_start == expected_start
        assert config["training_window"] == 60
        assert config["testing_window"] == 0

    def test_mode1_both_zero(self):
        """
        Mode 1 with training_days=0 and testing_days=0:
        start_date == end_date.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 0
        stub.testing_spin.value.return_value = 0
        stub.lookback_spin.value.return_value = 50
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        assert self._approx_now(config["start_date"]) == self._approx_now(config["end_date"])
        assert config["training_window"] == 0
        assert config["testing_window"] == 0
        assert config["training_end"] == config["start_date"]
        assert config["testing_start"] == config["start_date"]

    def test_mode1_large_date_window(self):
        """
        Mode 1 with large training + testing days (e.g. 365 each).
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 365
        stub.testing_spin.value.return_value = 365
        stub.lookback_spin.value.return_value = 30
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=730)
        )
        actual_start = self._approx_now(config["start_date"])

        assert config["mode"] == 1
        assert actual_start == expected_start
        assert config["training_window"] == 365
        assert config["testing_window"] == 365

    def test_mode2_ignores_training_testing_values(self):
        """
        Mode 2: start_date uses lookback_days even when
        training_days and testing_days are set.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 100
        stub.testing_spin.value.return_value = 100
        stub.lookback_spin.value.return_value = 15
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=15)
        )
        actual_start = self._approx_now(config["start_date"])

        assert config["mode"] == 2
        assert actual_start == expected_start
        assert "training_window" not in config
        assert "testing_window" not in config
        assert "training_end" not in config
        assert "testing_start" not in config

    def test_mode1_training_plus_testing_equals_lookback(self):
        """
        When training_days + testing_days == lookback_days in Mode 1,
        start_date is identical regardless, but the formula uses
        training + testing (not lookback).
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 40
        stub.testing_spin.value.return_value = 20
        stub.lookback_spin.value.return_value = 60
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        expected_start = self._approx_now(
            config["end_date"] - timedelta(days=60)
        )
        actual_start = self._approx_now(config["start_date"])

        assert actual_start == expected_start
        assert config["lookback_days"] == 60
        assert config["training_window"] == 40
        assert config["testing_window"] == 20

    def test_config_contains_expected_keys_mode1(self):
        """
        Mode 1 config dict contains all mandatory keys.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 30
        stub.testing_spin.value.return_value = 30
        stub.lookback_spin.value.return_value = 90
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        for key in ("mode", "start_date", "end_date", "lookback_days",
                     "training_window", "testing_window",
                     "training_end", "testing_start"):
            assert key in config, f"Missing key in mode 1 config: {key}"

    def test_config_omits_training_keys_in_mode2(self):
        """
        Mode 2 config dict must NOT contain training/testing keys.
        """
        stub = _make_get_config_stub()
        stub.lookback_spin.value.return_value = 30
        stub.training_spin.value.return_value = 60
        stub.testing_spin.value.return_value = 60
        stub.mode_group.checkedId.return_value = 2

        config = stub.get_config()

        for key in ("training_window", "testing_window",
                     "training_end", "testing_start"):
            assert key not in config, (
                f"Key {key} should NOT be present in mode 2 config"
            )

    def test_end_date_is_timezone_aware_utc(self):
        """
        end_date must be timezone-aware and in UTC.
        """
        stub = _make_get_config_stub()
        stub.training_spin.value.return_value = 30
        stub.testing_spin.value.return_value = 30
        stub.lookback_spin.value.return_value = 90
        stub.mode_group.checkedId.return_value = 1

        config = stub.get_config()

        assert config["end_date"].tzinfo is not None
        assert config["end_date"].tzinfo.utcoffset(config["end_date"]) is not None
        assert config["end_date"].tzinfo is timezone.utc or (
            config["end_date"].tzinfo.utcoffset(config["end_date"]).total_seconds() == 0
        )
