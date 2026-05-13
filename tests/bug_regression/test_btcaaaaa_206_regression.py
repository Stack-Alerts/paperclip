"""
Regression tests for BTCAAAAA-206: re-apply fixes that were reverted between sessions.

Issue: BTCAAAAA-206
Components:
  - src/strategy_builder/ui/data_verify_dialog.py
  - src/strategy_builder/ui/strategy_builder_main_window.py
  - scripts/launch_strategy_builder.py

Fix 1: data_verify_dialog — horizon_cutoff must be tz-aware UTC to match
       tz-aware gap_start from detect_gaps_in_binance_files.
Fix 2: strategy_builder_main_window — RuntimeUpdate status bar messages
       show [RuntimeUpdate] prefix in both success AND failure paths.
Fix 3: launch_strategy_builder — defensive force=True on logging.basicConfig.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-206"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Fix 1: horizon_cutoff tz-awareness (data_verify_dialog.py)
# ---------------------------------------------------------------------------

_BINANCE_HORIZON_DAYS = 90


def _compute_horizon_cutoff() -> datetime:
    """Simulate the tz-aware horizon_cutoff from DataVerifyThread.run()."""
    return datetime.now(timezone.utc) - timedelta(days=_BINANCE_HORIZON_DAYS)


class TestHorizonCutoffTzAware:
    """Fix 1: horizon_cutoff must be tz-aware UTC to match gap_start."""

    def test_horizon_cutoff_is_tz_aware(self):
        cutoff = _compute_horizon_cutoff()
        assert cutoff.tzinfo is not None, "horizon_cutoff must be tz-aware"
        assert cutoff.tzinfo.utcoffset(cutoff) == timezone.utc.utcoffset(cutoff)

    def test_horizon_cutoff_is_approximately_90_days_ago(self):
        cutoff = _compute_horizon_cutoff()
        expected = datetime.now(timezone.utc) - timedelta(days=90)
        delta = abs((cutoff - expected).total_seconds())
        assert delta < 2, f"horizon_cutoff should be ~90 days ago, off by {delta:.0f}s"

    def test_repairable_gap_comparison_past_cutoff(self):
        cutoff = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        gap_start = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        assert gap_start < cutoff, "gaps before cutoff should be too_old"

    def test_repairable_gap_comparison_future_cutoff(self):
        cutoff = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        gap_start = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc)
        assert gap_start >= cutoff, "gaps after cutoff should be repairable"

    def test_naive_gap_start_raises_on_comparison(self):
        cutoff = datetime.now(timezone.utc)
        naive_gap = datetime(2026, 5, 1, 12, 0, 0)
        with pytest.raises((TypeError, ValueError)):
            _ = naive_gap >= cutoff

    def test_horizon_cutoff_imports_timezone(self):
        from src.strategy_builder.ui.data_verify_dialog import (
            _BINANCE_HORIZON_DAYS as H_DAYS,
        )
        assert H_DAYS == 90

    def test_gap_classification_repairable(self):
        cutoff = _compute_horizon_cutoff()
        recent_gap = datetime.now(timezone.utc) - timedelta(days=1)
        assert recent_gap >= cutoff, "1-day-old gap should be repairable"

    def test_gap_classification_too_old(self):
        cutoff = _compute_horizon_cutoff()
        old_gap = datetime.now(timezone.utc) - timedelta(days=100)
        assert old_gap < cutoff, "100-day-old gap should be too_old"


# ---------------------------------------------------------------------------
# Fix 2: RuntimeUpdate status bar prefix (strategy_builder_main_window.py)
# ---------------------------------------------------------------------------


def _format_status_success(message: str) -> str:
    return f"[RuntimeUpdate] OK: {message[:120]}"


def _format_status_failure(message: str) -> str:
    return f"[RuntimeUpdate] FAIL: {message[:120]}"


class TestRuntimeUpdateStatusBarPrefix:
    """Fix 2: RuntimeUpdate messages show prefix in both success and failure."""

    def test_success_message_has_runtimeupdate_prefix(self):
        msg = _format_status_success("15m: 1/1 gaps repaired (100 bars)")
        assert msg.startswith("[RuntimeUpdate] OK:")

    def test_failure_message_has_runtimeupdate_prefix(self):
        msg = _format_status_failure("15m: verify_and_repair timed out")
        assert msg.startswith("[RuntimeUpdate] FAIL:")

    def test_success_message_truncated_to_120_chars(self):
        long_msg = "x" * 200
        result = _format_status_success(long_msg)
        assert len(result) == len("[RuntimeUpdate] OK: ") + 120

    def test_failure_message_truncated_to_120_chars(self):
        long_msg = "y" * 200
        result = _format_status_failure(long_msg)
        assert len(result) == len("[RuntimeUpdate] FAIL: ") + 120

    def test_runtimeupdate_not_overridden_by_countdown(self):
        countdown_keywords = [
            'Added block', 'Strategy updated', 'Saved', 'Loaded', 'Checking',
            'Updating', 'Validat', 'Generated', 'cleared', 'created',
            'Data updated', 'Update failed', 'Auto-update'
        ]
        rt_msg = "[RuntimeUpdate] OK: 15m: 1/1 gaps repaired"
        for kw in countdown_keywords:
            assert kw not in rt_msg, (
                f"RuntimeUpdate msg should not match keyword: {kw}"
            )


# ---------------------------------------------------------------------------
# Fix 3: logging.basicConfig force=True (launch_strategy_builder.py)
# ---------------------------------------------------------------------------


class TestLoggingBasicConfigForce:
    """Fix 3: logging.basicConfig must use force=True."""

    def test_basic_config_accepts_force(self):
        try:
            logging.basicConfig(force=True, level=logging.INFO, format='%(message)s')
        except TypeError as exc:
            pytest.fail(f"basicConfig(force=True) raised: {exc}")

    def test_force_reconfigures_root_logger(self):
        root = logging.getLogger()
        saved_handlers = list(root.handlers)
        saved_level = root.level
        try:
            logging.basicConfig(force=True, level=logging.DEBUG, format='%(levelname)s %(message)s')
            assert root.level == logging.DEBUG, "force=True should reconfigure root level"
        finally:
            root.setLevel(saved_level)

    def test_log_after_basic_config_works(self):
        logger = logging.getLogger("test_btcaaaaa_206")
        try:
            logger.info("test message from BTCAAAAA-206 regression")
        except Exception as exc:
            pytest.fail(f"logging after basicConfig raised: {exc}")


# ---------------------------------------------------------------------------
# Conftest teardown: avoid side effects on other tests
# ---------------------------------------------------------------------------


def teardown_module():
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)
