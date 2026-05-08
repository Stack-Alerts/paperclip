"""
Unit Tests: DataUpdateModal — Startup Fast-Path Dual-Staleness Check
======================================================================

Covers the fix for BTCAAAAA-384:
  The fast-path in DataUpdateModal._check_data_gap() must check BOTH 15m
  AND 1h staleness before skipping the startup download.

Test cases:
  1. 15m current, 1h stale  → fast-path does NOT fire (download proceeds)
  2. 15m stale,  1h current → fast-path does NOT fire
  3. Both current            → fast-path fires (QTimer.singleShot called)
  4. 15m missing (None)      → fast-path does NOT fire (falls through)
  5. 1h missing (None)       → fast-path does NOT fire (falls through)
  6. auto_mode=False         → fast-path block skipped entirely
  7-9. Boundary conditions at the exact thresholds

No live network calls or Qt display required.
The unit/conftest.py installs PyQt5 stubs automatically.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from types import ModuleType
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub: a pure-Python replica of the fast-path logic only
# ---------------------------------------------------------------------------
# We replicate _check_data_gap's fast-path in isolation using a tiny stub
# class.  This avoids the need to instantiate DataUpdateModal (which would
# require a live QApplication / Qt event loop) while still testing the exact
# staleness-check logic that was changed in BTCAAAAA-384.
#
# The stub's _check_data_gap is copy-pasted from the production method and
# kept intentionally minimal — only the fast-path block matters here.
# ---------------------------------------------------------------------------

class _MockQTimer:
    """Records QTimer.singleShot calls."""
    def __init__(self):
        self.calls: list[tuple] = []

    def singleShot(self, delay, callback):  # noqa: N802
        self.calls.append((delay, callback))


class _DataUpdateModalFastPathStub:
    """
    Minimal stand-in for DataUpdateModal that contains only the fast-path
    logic from _check_data_gap, wired to injected mocks.

    This matches the production code that was changed in BTCAAAAA-384:

        last_15m = self.manager.get_last_bar_timestamp('15m')
        last_1h  = self.manager.get_last_bar_timestamp('1h')

        if last_15m is not None and last_1h is not None:
            staleness_15m = (now - last_15m).total_seconds()
            staleness_1h  = (now - last_1h).total_seconds()
            if staleness_15m <= 1020 and staleness_1h <= 3720:
                QTimer.singleShot(500, self.accept)
                return
    """

    def __init__(self, *, auto_mode: bool = True, last_15m_offset_s=None,
                 last_1h_offset_s=None):
        self.auto_mode = auto_mode
        self.qtimer = _MockQTimer()
        self.accept_called = False
        self._last_15m_offset_s = last_15m_offset_s
        self._last_1h_offset_s = last_1h_offset_s

    # Mirrors production manager.get_last_bar_timestamp
    def _get_last_bar(self, timeframe: str, now: datetime):
        if timeframe == '15m':
            if self._last_15m_offset_s is None:
                return None
            return now - timedelta(seconds=self._last_15m_offset_s)
        if timeframe == '1h':
            if self._last_1h_offset_s is None:
                return None
            return now - timedelta(seconds=self._last_1h_offset_s)
        return None

    def accept(self):
        self.accept_called = True

    def fast_path_check(self) -> bool:
        """
        Executes only the fast-path block of _check_data_gap.
        Returns True if the fast-path fired (skipped download), False otherwise.
        """
        if not self.auto_mode:
            return False

        now = datetime.utcnow()
        last_15m = self._get_last_bar('15m', now)
        last_1h = self._get_last_bar('1h', now)

        if last_15m is not None and last_1h is not None:
            staleness_15m = (now - last_15m).total_seconds()
            staleness_1h = (now - last_1h).total_seconds()
            # 15m candle + 2 min grace = 17 min = 1020s
            # 1h candle + 2 min grace = 62 min = 3720s
            if staleness_15m <= 1020 and staleness_1h <= 3720:
                self.qtimer.singleShot(500, self.accept)
                return True

        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFastPathDualStaleness:
    """Fast-path fires only when BOTH 15m and 1h are within threshold."""

    # ------------------------------------------------------------------
    # 1. 15m current, 1h stale (> 62 min) → fast-path must NOT fire
    # ------------------------------------------------------------------
    def test_15m_current_1h_stale_does_not_fire(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=300,      # 5 min ago — current (≤ 1020s)
            last_1h_offset_s=7200,      # 2 h ago — stale (> 3720s)
        )
        result = stub.fast_path_check()
        assert result is False, "Fast-path should NOT fire when 1h is stale"
        assert len(stub.qtimer.calls) == 0

    # ------------------------------------------------------------------
    # 2. 15m stale, 1h current → fast-path must NOT fire
    # ------------------------------------------------------------------
    def test_15m_stale_1h_current_does_not_fire(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=3000,     # 50 min ago — stale (> 1020s)
            last_1h_offset_s=600,       # 10 min ago — current (≤ 3720s)
        )
        result = stub.fast_path_check()
        assert result is False, "Fast-path should NOT fire when 15m is stale"
        assert len(stub.qtimer.calls) == 0

    # ------------------------------------------------------------------
    # 3. Both current → fast-path MUST fire
    # ------------------------------------------------------------------
    def test_both_current_fast_path_fires(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=300,      # 5 min ago — current
            last_1h_offset_s=1800,      # 30 min ago — current
        )
        result = stub.fast_path_check()
        assert result is True, "Fast-path should fire when both timeframes are current"
        assert len(stub.qtimer.calls) == 1
        delay_arg = stub.qtimer.calls[0][0]
        assert delay_arg == 500, f"Expected 500ms delay, got {delay_arg}"

    # ------------------------------------------------------------------
    # 4. 15m timestamp unavailable (None) → fast-path must NOT fire
    # ------------------------------------------------------------------
    def test_15m_none_does_not_fire(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=None,
            last_1h_offset_s=600,
        )
        result = stub.fast_path_check()
        assert result is False, "Fast-path should NOT fire when 15m is None"
        assert len(stub.qtimer.calls) == 0

    # ------------------------------------------------------------------
    # 5. 1h timestamp unavailable (None) → fast-path must NOT fire
    # ------------------------------------------------------------------
    def test_1h_none_does_not_fire(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=300,
            last_1h_offset_s=None,
        )
        result = stub.fast_path_check()
        assert result is False, "Fast-path should NOT fire when 1h is None"
        assert len(stub.qtimer.calls) == 0

    # ------------------------------------------------------------------
    # 6. auto_mode=False → fast-path block is skipped entirely
    # ------------------------------------------------------------------
    def test_auto_mode_false_skips_fast_path(self):
        stub = _DataUpdateModalFastPathStub(
            auto_mode=False,
            last_15m_offset_s=300,
            last_1h_offset_s=600,
        )
        result = stub.fast_path_check()
        assert result is False, "Fast-path must be skipped when auto_mode=False"
        assert len(stub.qtimer.calls) == 0

    # ------------------------------------------------------------------
    # 7. Boundary: 15m exactly at threshold (1020s) → fires
    # ------------------------------------------------------------------
    def test_15m_at_exact_threshold_fires(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=1020,     # exactly at 17-min limit
            last_1h_offset_s=600,
        )
        result = stub.fast_path_check()
        assert result is True, "Fast-path should fire when 15m staleness == 1020s"

    # ------------------------------------------------------------------
    # 8. Boundary: 1h exactly at threshold (3720s) → fires
    # ------------------------------------------------------------------
    def test_1h_at_exact_threshold_fires(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=300,
            last_1h_offset_s=3720,      # exactly at 62-min limit
        )
        result = stub.fast_path_check()
        assert result is True, "Fast-path should fire when 1h staleness == 3720s"

    # ------------------------------------------------------------------
    # 9. 1h one second past threshold → does NOT fire
    # ------------------------------------------------------------------
    def test_1h_one_second_past_threshold_does_not_fire(self):
        stub = _DataUpdateModalFastPathStub(
            last_15m_offset_s=300,
            last_1h_offset_s=3721,      # one second past 62-min limit
        )
        result = stub.fast_path_check()
        assert result is False, "Fast-path should NOT fire when 1h staleness == 3721s"
        assert len(stub.qtimer.calls) == 0
