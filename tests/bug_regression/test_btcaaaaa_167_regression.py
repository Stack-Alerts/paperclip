"""
Regression tests for BTCAAAAA-167: RC1b UTC timestamp normalization + RC4c/RC6 fixes.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-167
Component: src/data_manager/unified_manager.py

Root cause: Naive datetimes in Binance candle fetching were being interpreted as
local time (CEST) instead of UTC, causing incorrect startTime/endTime parameters
in API requests (off by -2h). RC6 introduced _to_ms_utc() to fix this. RC4c
fixed 15m-only scan anchor logic so it does not fall back to the 1h bar timestamp.

This file re-exports the existing unit tests from test_rc4c_rc6_fixes.py so the
Impact Gate runner can discover them by bug ID. The canonical tests live in
tests/unit/test_rc4c_rc6_fixes.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-167"),
    pytest.mark.regression,
]

from tests.unit.test_rc4c_rc6_fixes import (  # noqa: E402, F401
    TestToMsUtc,
    TestRC4cScanAnchor,
    TestFetchBinanceRangeUtcParams,
)
