"""
Regression tests for BTCAAAAA-24978: NautilusTrader v1.226.0 API drift in
optimizer_v3 modules — migrate deprecated single-string constructors to
from_str() / two-arg Price(float, precision).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-24978
Component: src/optimizer_v3/

Root cause: NautilusTrader 1.226.0 removed support for positional string args
in Price(), Quantity(), and Money() single-argument constructors. All callers
must use Price.from_str(), Quantity.from_str(), Money.from_str(), or the
two-argument form Price(float, precision) / Quantity(float, precision).

Fix: Migrated all 11 affected files across optimizer_v3 core, database, ui,
and tests. Verified via AST scan and import test.

This file re-exports the existing unit tests from test_institutional_metrics.py
and test_state_manager.py so the Impact Gate runner can discover them by bug ID.
The canonical tests live in tests/optimizer_v3/results/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-24978"),
    pytest.mark.regression,
]

from tests.optimizer_v3.results.test_institutional_metrics import (  # noqa: E402, F401
    TestInstitutionalMetrics,
)

from tests.optimizer_v3.results.test_state_manager import (  # noqa: E402, F401
    TestStateManager,
)
