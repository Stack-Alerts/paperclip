"""
Regression tests for BTCAAAAA-668: persist trades in single-core backtest path
+ fix missing compact block signals key.

Bug 1 — TradeRegistry syncs 0 trades (CRITICAL):
  Single-core backtest worker was emitting trade data to UI via Qt signals
  but never calling registry.add_trade().  Added call after trade_data_emit.

Bug 2 — Compact blocks missing signals key (MODERATE):
  _extract_available_blocks() omitted the signals key from the compact format
  dict for non-strategy blocks, causing downstream "NO signals" errors.
  Added signals: [] to the compact format dict.

Issue: BTCAAAAA-668
Fix commit: b44cc681
Components:
  - src/strategy_builder/ui/backtest_config_panel.py
  - src/optimizer_v3/core/comprehensive_ai_request_builder.py

This file is the canonical regression location.  The authoritative test suite
is imported from the QA test file so it cannot drift from the original
fix verification.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-668"),
    pytest.mark.regression,
]

# Re-export existing test classes unchanged.  This keeps the canonical logic
# in one place (tests/strategy_builder/ui/) while registering the tests in this
# module so the Impact Gate runner can find them by bug ID.
from tests.strategy_builder.ui.test_btcaaaaa_668_trade_registry_and_signals_key import (  # noqa: E402, F401
    TestBacktestWorkerSingleCoreTradeRegistry,
    TestCompactBlockSignalsKey,
    TestMulticorePathRegistryRegression,
    TestTradeRegistryDeduplication,
)
