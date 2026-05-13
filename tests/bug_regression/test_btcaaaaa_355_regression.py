"""
Regression tests for BTCAAAAA-355: AI Recommendations Panel — fix for P4 regression
that hid the Request Preview by default.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-355
Component: src/optimizer_v3/ui/ai_recommendations_panel.py

Root cause: BTCAAAAA-355 (commits e8a60286 / 132be884) reverted the P4 regression
introduced in BTCAAAAA-354 by restoring:
  1. preview_container.setVisible(True) — visible by default
  2. Button label "Hide Request Preview" — matches expanded state
  3. Comment: "Visible by default" / "collapsible, visible by default"

This file re-exports the existing source-contract regression tests from the
BTCAAAAA-354 test file so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/bug_regression/test_btcaaaaa_354_regression.py
and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-355"),
    pytest.mark.regression,
]

from tests.bug_regression.test_btcaaaaa_354_regression import (  # noqa: E402, F401
    TestPreviewContainerVisibleByDefault,
    TestToggleButtonLabel,
    TestToggleRequestPreviewMethod,
)
