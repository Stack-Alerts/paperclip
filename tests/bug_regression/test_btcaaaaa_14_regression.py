"""
Regression tests for BTCAAAAA-14: Data Manager — Data Integrity, Gap Detection
& Auto-Repair in UnifiedDataManager.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-14
Components: src/data_manager/unified_manager.py
            src/data_manager/binance/rest_client.py
            src/strategy_builder/ui/data_update_modal.py

Root cause: Gap detection in detect_gaps_in_binance_files() could fail to
detect missing bars when the last bar on disk was stale relative to end_date,
or when the scan anchor was set to session_start_time instead of the last
bar on disk.  The trailing-edge check and min_anchor fix (RC4b) resolved
the false-negative gap detection.

This file re-exports the existing data manager integrity tests from
tests/unit/test_data_manager_integrity.py so the Impact Gate runner can
discover them by bug ID.  The canonical tests live in tests/unit/ and must
not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-14"),
    pytest.mark.regression,
]

# Import fixtures and helpers so pytest can resolve them when the re-exported
# test classes reference them by name.
from tests.unit.test_data_manager_integrity import (  # noqa: E402
    manager,
    _make_ohlcv,
    _write_parquet,
    _write_month_file,
)

from tests.unit.test_data_manager_integrity import (  # noqa: E402, F401
    TestDetectGapsInBinanceFiles,
    TestVerifyAndRepair,
    TestStartupCheck,
    TestGetBarsRegression,
    TestSaveBinanceBars,
    TestOHLCVDataValidation,
    TestDownloadWithRetry1dStaleness,
    TestGetKlines1dNotFlaggedStale,
    TestTrailingEdgeGapDetection,
    TestDataUpdateThreadDownloads1d,
    TestDetermineSourceTzAwareness,
    TestGetBarsBinanceTzAwareRegression,
)
