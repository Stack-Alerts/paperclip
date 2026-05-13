"""
Regression tests for BTCAAAAA-25396: floor end_date to midnight UTC.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25396
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: end_date in BacktestConfigPanel.get_config() was timezone-aware
UTC but still carried the wall-clock time (hour/minute/second/microsecond)
of invocation. This caused batch runs and report grouping to produce
inconsistent date buckets.

Fix: floor the end_date to UTC midnight (00:00:00.000000) so that all
invocations on the same UTC date produce the same date boundary.

The canonical tests live in test_btcaaaaa_2186_regression.py
(TestUtcTimezonesInGetConfig.test_end_date_is_midnight_utc) and are
re-exported here so the Impact Gate runner can discover them by issue ID.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25396"),
    pytest.mark.regression,
]

from tests.bug_regression.test_btcaaaaa_2186_regression import (  # noqa: E402, F401
    TestUtcTimezonesInGetConfig,
)
