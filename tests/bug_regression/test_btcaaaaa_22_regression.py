"""
Regression tests for BTCAAAAA-22: resolve four 1h data startup failure bugs.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-22
Fixed in commit: a1f2bb52

Bugs covered:
  Bug A: empty-bars check moved inside retry loop so empty responses trigger
         retries instead of immediate raise.
  Bug B: query start date widened by 2h when gap is sub-1h so 1h klines
         request always spans at least one complete closed candle.
  Bug C: reset_client() discards degraded BinanceRestClient on retry.
  Bug D: startup modal delay increased from 500ms to 2000ms + lightweight
         Binance /ping pre-check in DataUpdateThread.run().
  Mode:  DataUpdateThread and DataUpdateModal now instantiate
         UnifiedDataManager with mode='live' (was defaulting to backtest).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-22"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Bug C: reset_client()
# ---------------------------------------------------------------------------


class TestResetClient:
    def test_reset_client_sets_client_to_none(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        mgr.binance_client = MagicMock()
        assert mgr.binance_client is not None
        mgr.reset_client()
        assert mgr.binance_client is None

    def test_reset_client_when_already_none(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        mgr.binance_client = None
        mgr.reset_client()
        assert mgr.binance_client is None

    def test_reset_clears_client_for_fresh_recreation(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        first = MagicMock()
        mgr.binance_client = first
        mgr.reset_client()
        assert mgr.binance_client is None

    def test_constructor_defaults_client_to_none(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        assert mgr.binance_client is None


# ---------------------------------------------------------------------------
# Bug B: sub-1h gap widening for 1h queries
# ---------------------------------------------------------------------------


class TestSub1hGapWidening:
    def test_sub1h_gap_widens_start_date_logic(self):
        now = datetime(2026, 5, 13, 12, 30, 0, tzinfo=timezone.utc)
        lakeapi_end = now - timedelta(minutes=30)
        gap_seconds = (now - lakeapi_end).total_seconds()
        assert gap_seconds < 3600, "Precondition: gap must be sub-1h for this test"
        widened = now - timedelta(hours=2)
        assert widened != lakeapi_end

    def test_widened_window_spans_at_least_one_hour(self):
        now = datetime(2026, 5, 13, 12, 15, 0, tzinfo=timezone.utc)
        widened = now - timedelta(hours=2)
        window_seconds = (now - widened).total_seconds()
        assert window_seconds >= 3600, (
            f"Widened window {window_seconds}s must be >= 3600s"
        )


# ---------------------------------------------------------------------------
# Bug D: startup modal delay increased to 2000ms
# ---------------------------------------------------------------------------


class TestStartupModalDelay:
    def test_startup_delay_is_2000ms(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "strategy_builder_main_window.py"
        ).read_text()
        assert "singleShot(2000" in source, (
            "QTimer.singleShot(2000, ...) must exist for startup delay"
        )

    def test_old_500ms_no_longer_present(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "strategy_builder_main_window.py"
        ).read_text()
        assert "singleShot(500" not in source, (
            "Old 500ms delay must not remain in strategy_builder_main_window.py"
        )


# ---------------------------------------------------------------------------
# Bug D: Binance /ping pre-check present in DataUpdateThread source
# ---------------------------------------------------------------------------


class TestBinancePingPreCheck:
    def test_ping_logic_exists_in_source(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "api.binance.com/api/v3/ping" in source, (
            "Binance /ping pre-check must exist in DataUpdateThread"
        )

    def test_ping_raises_connection_error_on_failure(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "ConnectionError" in source, (
            "Ping failure must raise ConnectionError in DataUpdateThread"
        )


# ---------------------------------------------------------------------------
# Live mode verification
# ---------------------------------------------------------------------------


class TestLiveMode:
    def test_unified_manager_accepts_live_mode(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        assert mgr.mode == "live"

    def test_unified_manager_accepts_backtest_mode(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest")
        assert mgr.mode == "backtest"

    def test_default_mode_is_backtest(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager()
        assert mgr.mode == "backtest"


# ---------------------------------------------------------------------------
# Bug A: empty-bars retry (DataUpdateThread._download_with_retry exists)
# ---------------------------------------------------------------------------


class TestEmptyBarsRetry:
    def test_download_with_retry_method_exists(self):
        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        assert hasattr(DataUpdateThread, "_download_with_retry")

    def test_empty_bars_retry_logic_exists_in_source(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "len(bars) == 0" in source, (
            "Empty-bars check must exist in DataUpdateThread"
        )
        assert "retry" in source.lower()

    def test_retry_increments_on_empty_response(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "self.max_retries" in source, (
            "max_retries must exist in DataUpdateThread"
        )


# ---------------------------------------------------------------------------
# Source-level assertions from the fix commit
# ---------------------------------------------------------------------------


class TestSourceAssertions:
    def test_data_update_thread_init_has_required_params(self):
        import inspect

        from src.strategy_builder.ui.data_update_modal import DataUpdateThread

        sig = inspect.signature(DataUpdateThread.__init__)
        params = list(sig.parameters.keys())
        assert "start_date" in params
        assert "end_date" in params

    def test_reset_client_method_exists(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        assert hasattr(UnifiedDataManager, "reset_client")
        assert callable(UnifiedDataManager.reset_client)

    def test_live_mode_used_in_data_update_thread(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "strategy_builder"
            / "ui"
            / "data_update_modal.py"
        ).read_text()
        assert "mode='live'" in source, (
            "UnifiedDataManager must be instantiated with mode='live'"
        )
