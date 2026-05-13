"""
Regression tests for BTCAAAAA-245: Optimizer V3 UI — fix stale test file and
recommendation engine field naming.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-245
Component: src/optimizer_v3/ui/metrics_display_panel.py,
            src/optimizer_v3/core/intelligent_recommendation_engine.py

Root cause: The prior test file referenced removed production classes
(PerformanceMetrics/ConfigSnapshot) and used PyQt6 (production uses PyQt5).
IntegratedRecommendation used .action_type instead of .type, and the
ADD_RECHECK/ADD_TIMING handler methods were missing from MetricsDisplayPanel.

This file re-exports the existing unit tests from tests/optimizer_v3/ so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/optimizer_v3/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-245"),
    pytest.mark.regression,
]

from tests.optimizer_v3.ui.test_ui_components import (  # noqa: E402, F401
    TestModuleImports,
    TestMetricsDisplayPanelAttributes,
)
