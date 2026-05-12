"""
Regression tests for BTCAAAAA-736: Mode 2 (Live Replay) produces 0 trades.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-736
Fixed in commit: ad3b0b1
Component: src/optimizer_v3/core/institutional_signal_evaluator.py

Root cause: two bugs in InstitutionalSignalEvaluator blocked entry signals:
  Bug 1 — hasattr crash: _organize_exit_conditions raised TypeError on
           DictWrapper strategy configs lacking __exit_conditions__ attribute.
  Bug 2 — reference key: timing-chain lookup used 'reference_signal' but
           the config stored the key as 'reference', capping confluence at
           35 pts and preventing entry (threshold: 40 pts).

This file is the canonical regression location.  The full scenario (mocked
building blocks, bar-by-bar Mode 2 loop, all three assertions) is imported
from the authoritative integration test so it cannot drift from the original
fix verification.
"""
from __future__ import annotations

import pytest

# Module-level markers bind every test here to bug BTCAAAAA-736 and the
# regression suite.
pytestmark = [
    pytest.mark.bug("BTCAAAAA-736"),
    pytest.mark.regression,
]

# Re-export the existing integration test class unchanged.  This keeps the
# canonical logic in one place (tests/integration/) while registering the
# tests in this module so the runner can find them by bug ID.
from tests.integration.test_btcaaaaa_736_mode2_regression import (  # noqa: E402, F401
    TestMode2BarByBarLoop,
)
