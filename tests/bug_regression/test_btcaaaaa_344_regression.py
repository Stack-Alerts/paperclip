"""
Regression tests for BTCAAAAA-344: implement one-click apply recommendations
end-to-end.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-344
Component: src/optimizer_v3/core/intelligent_recommendation_engine.py,
            src/optimizer_v3/ui/metrics_display_panel.py

Root cause: The optimizer v3 lacked a one-click mechanism to apply
recommendations end-to-end across ADD_BLOCK, ADJUST_PARAM, ADD_RECHECK, and
ADD_TIMING config mutation types.

This file re-exports the existing unit tests from tests/optimizer_v3/ so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/optimizer_v3/ and must not drift.
"""

from __future__ import annotations

import pytest

from src.optimizer_v3.core.intelligent_recommendation_engine import (
    IntelligentRecommendationEngine,
)


@pytest.fixture(scope="module")
def engine():
    """Create a single engine instance shared across tests in this module."""
    return IntelligentRecommendationEngine()


pytestmark = [
    pytest.mark.bug("BTCAAAAA-344"),
    pytest.mark.regression,
]

from tests.optimizer_v3.test_apply_recommendations import (  # noqa: E402, F401
    TestApplyAddBlock,
    TestApplyAdjustParam,
    TestApplyAddRecheck,
    TestApplyAddTiming,
    TestApplyEdgeCases,
)
