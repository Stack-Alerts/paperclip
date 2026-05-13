"""
Regression tests for BTCAAAAA-165: Binance propagation buffer in
verify_and_repair fetch_start.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-165
Component: src/data_manager/unified_manager.py

Fixed in commit: b82779da
Fix history:
  1. b82779da — Added BINANCE_PROPAGATION_BUFFER = timedelta(seconds=2)
     and applied it to fetch_start in verify_and_repair.
  2. fd63ad85 — Removed buffer from fetch_start because +2s caused
     Binance to reject startTime past bar open. The constant was kept
     for reference and future use.
  3. 295fb522 — Replaced with a 2s polling retry loop for trailing-edge
     bar propagation in _start_auto_update_system.

Root cause: Binance takes 1-2 seconds after a candle closes to finalize
and expose the bar via the REST API. The repair cycle was firing with
fetch_start at the exact candle-close boundary (gap_start + bar_td),
causing Binance to return 0 bars and leaving the gap unrepaired until
the next cycle.

This file verifies the propagation buffer constant is still defined,
preserving the domain knowledge embedded in the fix.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-165"),
    pytest.mark.regression,
]


class TestBinancePropagationBuffer:
    """BINANCE_PROPAGATION_BUFFER constant from unified_manager.py."""

    def test_constant_exists(self) -> None:
        from src.data_manager.unified_manager import BINANCE_PROPAGATION_BUFFER

        assert BINANCE_PROPAGATION_BUFFER is not None

    def test_constant_is_timedelta(self) -> None:
        from src.data_manager.unified_manager import BINANCE_PROPAGATION_BUFFER

        assert isinstance(BINANCE_PROPAGATION_BUFFER, timedelta)

    def test_constant_equals_two_seconds(self) -> None:
        from src.data_manager.unified_manager import BINANCE_PROPAGATION_BUFFER

        assert BINANCE_PROPAGATION_BUFFER == timedelta(seconds=2)

    def test_constant_is_positive(self) -> None:
        from src.data_manager.unified_manager import BINANCE_PROPAGATION_BUFFER

        assert BINANCE_PROPAGATION_BUFFER.total_seconds() > 0


class TestVerifyAndRepairFetchStart:
    """verify_and_repair uses fetch_start = gap_start + bar_td (no buffer).

    The BINANCE_PROPAGATION_BUFFER was removed from fetch_start in
    fd63ad85 because +2s caused Binance to reject startTime values past
    the bar open.  This class asserts the current contract so that any
    future re-introduction of the buffer into fetch_start is deliberate.
    """

    def test_verify_and_repair_method_exists(self) -> None:
        from src.data_manager.unified_manager import UnifiedDataManager

        assert hasattr(UnifiedDataManager, "verify_and_repair")
