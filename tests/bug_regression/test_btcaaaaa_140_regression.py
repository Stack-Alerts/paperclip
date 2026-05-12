"""
Regression tests for BTCAAAAA-140: fix EXIT_009 cross-level exit mode conflict
in _apply_exit_consolidation_fix.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-140
Component: src/strategy_builder/ui/validation_report_window.py

Root cause: EXIT_009 fired when the same signal_name had conflicting exit modes
(ABSOLUTE vs FLEXIBLE) across different binding levels (strategy, block, signal).
The previous per-level fix only looked at one level at a time, so cross-level
conflicts were never resolved and EXIT_009 persisted after re-validation.
The fix scans ALL levels for the same signal_name, determines the canonical
mode (ABSOLUTE beats FLEXIBLE), and mutates every matching condition in-place.

This file re-exports the existing Impact Gate Runner end-to-end tests from
tests/test_impact_gate/test_e2e.py so the Impact Gate runner can discover
them by bug ID.  The canonical tests live in tests/test_impact_gate/ and must
not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-140"),
    pytest.mark.regression,
]

from tests.test_impact_gate.test_e2e import (  # noqa: E402, F401
    TestImpactGateRunnerE2E,
    TestImpactGateRunnerCLI,
)
