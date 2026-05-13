"""
Regression tests for BTCAAAAA-732 — unreachable confluence threshold repair.

Root cause: strategy loaded from database had only 2 blocks (max 30pts), while the
confluence threshold was 40pts → guaranteed 0 trades.  _repair_if_unreachable detects
this and merges missing blocks from user_strategies/current_strategy.json.

Also covers the AI request preview "no signals" warning scope fix.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-732
Component: src/strategy_builder/ui/backtest_config_panel.py
"""
from __future__ import annotations

import sys

import pytest

from PyQt5.QtWidgets import QApplication

pytestmark = [
    pytest.mark.bug("BTCAAAAA-732"),
    pytest.mark.regression,
]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


from tests.strategy_builder.ui.test_confluence_repair import (  # noqa: E402, F401
    TestRepairIfUnreachable,
    TestAIPreviewWindowNoSignalsWarning,
)
