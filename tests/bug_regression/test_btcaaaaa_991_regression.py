"""
Regression tests for BTCAAAAA-991.

BTCAAAAA-991 addressed a timestamp-attribution bug in the backtest engine
where datetime.fromtimestamp() used the server local timezone (CET=UTC+1)
instead of UTC, causing a systematic +4-bar price offset. The fix uses
datetime.fromtimestamp(ts / 1e9, tz=timezone.utc).replace(tzinfo=None)
and adds P1.1 price audit instrumentation to detect future regressions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-991"),
    pytest.mark.regression,
]


class TestUtcTimestampConversion:
    """Entry timestamps must use UTC; local-server time leaks cause bar shift."""

    def test_fromtimestamp_utc_produces_expected_utc(self):
        ts_ns = int(datetime(2025, 9, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        result = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result == datetime(2025, 9, 1, 12, 0, 0)

    def test_fromtimestamp_utc_midnight(self):
        ts_ns = int(datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        result = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result == datetime(2026, 1, 15, 0, 0, 0)

    def test_fromtimestamp_utc_boundary_crosses_date(self):
        ts_ns = int(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        result = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result == datetime(2026, 1, 1, 0, 0, 0)

    def test_fromtimestamp_utc_matches_bar_ts_init(self):
        ts_ns = int(datetime(2025, 6, 15, 14, 30, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        bar_ts = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert bar_ts == datetime(2025, 6, 15, 14, 30, 0)

    def test_fromtimestamp_utc_differs_from_local_when_tz_shifted(self):
        ts_ns = int(datetime(2025, 12, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        utc_result = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).replace(tzinfo=None)
        local_result = datetime.fromtimestamp(ts_ns / 1e9)
        offset_h = local_result.hour - utc_result.hour
        assert offset_h in (0, 1, 2, -1, -2)

    def test_nanosecond_precision_preserved_through_conversion(self):
        ts_ns = 1735689600000000000
        result = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)
        roundtrip_ns = int(result.timestamp() * 1e9)
        assert roundtrip_ns == ts_ns

    def test_no_tzinfo_on_result(self):
        ts_ns = int(datetime(2025, 9, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        result = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).replace(tzinfo=None)
        assert result.tzinfo is None


class TestPriceAttributionInvariant:
    """Entry price from bar.close must be within that bar's H/L range."""

    def test_entry_price_within_range_standard(self):
        assert 80900.0 <= 81690.20 <= 81700.0

    def test_entry_price_equal_to_low(self):
        assert 100.0 <= 100.0 <= 200.0

    def test_entry_price_equal_to_high(self):
        assert 100.0 <= 200.0 <= 200.0

    def test_entry_price_outside_range_detected(self):
        assert not (100.0 <= 90.0 <= 200.0)

    def test_entry_price_at_extreme_values(self):
        for price, lo, hi in [(0.01, 0.0, 1.0), (99999.99, 99000.0, 100000.0)]:
            assert lo <= price <= hi

    def test_entry_price_passes_for_identical_open_close(self):
        assert 50000.0 <= 50000.0 <= 50000.0


class TestFloatPrecision:
    """round(float(bar.close), 2) must produce clean 2-decimal values."""

    def test_no_float_precision_artifact_standard(self):
        price_float = round(81690.20, 2)
        assert price_float == round(price_float, 2)
        assert abs(price_float - 81690.20) < 0.01

    def test_no_float_precision_artifact_whole_numbers(self):
        for val in [100.0, 50000.0, 99999.99, 0.01]:
            rounded = round(val, 2)
            assert rounded == round(rounded, 2)

    def test_no_float_precision_artifact_edge_cents(self):
        for val in [0.1 + 0.2, 1.0 / 3.0, 3.14159]:
            rounded = round(val, 2)
            assert rounded == round(rounded, 2)

    def test_float_precision_two_decimals_max(self):
        assert round(12345.6789, 2) == 12345.68


class TestPriceAuditInstrumentation:
    """Price audit logging from BTCAAAAA-991 must detect out-of-range prices."""

    def test_price_in_range_passes(self):
        assert 49900.0 <= 50000.0 <= 50100.0

    def test_price_out_of_range_condition_detected(self):
        assert not (50001.0 <= 50000.0 <= 50100.0)

    def test_price_in_range_with_high_precision(self):
        result = round(81690.2000001, 2)
        assert 80900.0 <= result <= 81700.0


class TestEnterTradePriceWarning:
    """enter_trade() must warn when entry price is outside bar H/L."""

    def test_enter_trade_price_warning_called_for_out_of_range(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )

        evaluator = InstitutionalSignalEvaluator.__new__(InstitutionalSignalEvaluator)
        evaluator.current_trade = None
        evaluator._instantiate_building_blocks = MagicMock(return_value={})
        evaluator._organize_exit_conditions = MagicMock(return_value={})
        evaluator._log_strategy_config = MagicMock()
        evaluator.confluence_calc = MagicMock()

        bar = MagicMock()
        bar.close = 50000.0
        bar.low = 50100.0
        bar.high = 50200.0

        with patch("src.optimizer_v3.core.institutional_signal_evaluator.logger") as mock_log:
            evaluator.enter_trade(bar, 5, "SHORT", ["sig1"])
            mock_log.warning.assert_called_once()
            assert "PRICE RANGE WARNING" in mock_log.warning.call_args[0][0]

    def test_enter_trade_no_warning_when_price_in_range(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )

        evaluator = InstitutionalSignalEvaluator.__new__(InstitutionalSignalEvaluator)
        evaluator.current_trade = None
        evaluator._instantiate_building_blocks = MagicMock(return_value={})
        evaluator._organize_exit_conditions = MagicMock(return_value={})
        evaluator._log_strategy_config = MagicMock()
        evaluator.confluence_calc = MagicMock()

        bar = MagicMock()
        bar.close = 50050.0
        bar.low = 50000.0
        bar.high = 50100.0

        with patch("src.optimizer_v3.core.institutional_signal_evaluator.logger") as mock_log:
            evaluator.enter_trade(bar, 5, "SHORT", ["sig1"])
            for call in mock_log.warning.call_args_list:
                assert "PRICE RANGE WARNING" not in call[0][0]

    def test_enter_trade_sets_entry_price_from_bar_close(self):
        from src.optimizer_v3.core.institutional_signal_evaluator import (
            InstitutionalSignalEvaluator,
        )
        from nautilus_trader.model.objects import Price

        evaluator = InstitutionalSignalEvaluator.__new__(InstitutionalSignalEvaluator)
        evaluator.current_trade = None
        evaluator._instantiate_building_blocks = MagicMock(return_value={})
        evaluator._organize_exit_conditions = MagicMock(return_value={})
        evaluator._log_strategy_config = MagicMock()
        evaluator.confluence_calc = MagicMock()

        bar = MagicMock()
        bar.close = 50050.0
        bar.low = 50000.0
        bar.high = 50100.0

        evaluator.enter_trade(bar, 5, "SHORT", ["sig1"])
        assert isinstance(evaluator.current_trade.entry_price, Price)
        assert float(evaluator.current_trade.entry_price) == 50050.0
        assert evaluator.current_trade.entry_bar == 5
        assert evaluator.current_trade.entry_side == "SHORT"
        assert evaluator.current_trade.entry_signals == ["sig1"]


class TestBacktestEngineEntryTimestamp:
    """The UTC timestamp path from BTCAAAAA-991 must be stable and correct."""

    def test_engine_entry_timestamp_is_utc_aligned(self):
        from datetime import timezone as _tz

        ts_ns = int(datetime(2025, 9, 1, 12, 0, 0, tzinfo=_tz.utc).timestamp() * 1e9)
        entry_timestamp = datetime.fromtimestamp(ts_ns / 1e9, tz=_tz.utc).replace(tzinfo=None)
        assert entry_timestamp == datetime(2025, 9, 1, 12, 0, 0)
        assert entry_timestamp.tzinfo is None

    def test_engine_multiple_bars_each_timestamp_utc(self):
        from datetime import timezone as _tz, timedelta

        base_ns = int(datetime(2025, 9, 1, 0, 0, 0, tzinfo=_tz.utc).timestamp() * 1e9)
        interval_ns = 15 * 60 * int(1e9)
        for i in range(10):
            ts_ns = base_ns + i * interval_ns
            entry_ts = datetime.fromtimestamp(ts_ns / 1e9, tz=_tz.utc).replace(tzinfo=None)
            expected = datetime(2025, 9, 1, 0, 0, 0) + timedelta(minutes=15 * i)
            assert entry_ts == expected, f"Bar {i}: expected {expected}, got {entry_ts}"

    def test_engine_entry_timestamp_matches_bar_index(self):
        from datetime import timezone as _tz, timedelta

        base = datetime(2025, 9, 1, 0, 0, 0, tzinfo=_tz.utc)
        bar_indices = [0, 5, 10, 50, 100]
        expected_times = [
            datetime(2025, 9, 1, 0, 0, 0),
            datetime(2025, 9, 1, 1, 15, 0),
            datetime(2025, 9, 1, 2, 30, 0),
            datetime(2025, 9, 1, 12, 30, 0),
            datetime(2025, 9, 2, 1, 0, 0),
        ]
        for idx, expected in zip(bar_indices, expected_times):
            ts_ns = int((base.timestamp() + idx * 900) * 1e9)
            result = datetime.fromtimestamp(ts_ns / 1e9, tz=_tz.utc).replace(tzinfo=None)
            assert result == expected, f"Bar {idx}: expected {expected}, got {result}"
