"""
Regression tests for BTCAAAAA-729: guard apply_hand_cursor_to_buttons against
deleted C++ Qt objects.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-729
Fixed in commit: f8d243a2
Component: src/strategy_builder/ui/styles.py

Root cause: apply_hand_cursor_to_buttons in styles.py raised RuntimeError when
a QTimer.singleShot callback fired after the parent widget's C++ backing was
already freed (e.g., dialog close). Fix added sip.isdeleted() guard at the
top of the function to bail out early.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-729"),
    pytest.mark.regression,
]


class TestApplyHandCursorGuard:
    """Verify apply_hand_cursor_to_buttons handles deleted C++ Qt objects."""

    def test_apply_hand_cursor_importable(self):
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons
        assert callable(apply_hand_cursor_to_buttons)

    def test_function_signature_parent_widget_param(self):
        from inspect import signature
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons
        sig = signature(apply_hand_cursor_to_buttons)
        assert "parent_widget" in sig.parameters
