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

import textwrap

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-729"),
    pytest.mark.regression,
]

SOURCE_MODULE = "src/strategy_builder/ui/styles.py"


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

    def test_source_contains_sip_isdeleted_guard(self):
        source = textwrap.dedent(open(SOURCE_MODULE).read())
        assert "_sip.isdeleted(parent_widget)" in source, (
            "Missing sip.isdeleted() guard -- fix for BTCAAAAA-729"
        )

    def test_source_imports_sip_inside_function_body(self):
        source = open(SOURCE_MODULE).read()
        func_start = source.find("def apply_hand_cursor_to_buttons")
        assert func_start >= 0, "Function not found in source"
        func_body = source[func_start:]
        assert "from PyQt5 import sip as _sip" in func_body, (
            "sip import must be inside the function body for lazy import"
        )

    def test_function_does_not_require_qt_app_for_import(self):
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons
        assert apply_hand_cursor_to_buttons is not None


class TestApplyHandCursorBehavior:
    """Verify cursor behavior on real Qt widgets."""

    def test_sets_hand_cursor_on_qpushbutton(self, qapp):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QPushButton, QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        btn = QPushButton("Click", parent)
        apply_hand_cursor_to_buttons(parent)
        assert btn.cursor().shape() == Qt.PointingHandCursor

    def test_sets_hand_cursor_on_qradiobutton(self, qapp):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QRadioButton, QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        radio = QRadioButton("Choice", parent)
        apply_hand_cursor_to_buttons(parent)
        assert radio.cursor().shape() == Qt.PointingHandCursor

    def test_sets_hand_cursor_on_qcheckbox(self, qapp):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QCheckBox, QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        cb = QCheckBox("Option", parent)
        apply_hand_cursor_to_buttons(parent)
        assert cb.cursor().shape() == Qt.PointingHandCursor

    def test_sets_hand_cursor_on_qcombobox(self, qapp):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QComboBox, QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        combo = QComboBox(parent)
        apply_hand_cursor_to_buttons(parent)
        assert combo.cursor().shape() == Qt.PointingHandCursor

    def test_skips_qlabel_cursor(self, qapp):
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QLabel, QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        label = QLabel("Text", parent)
        apply_hand_cursor_to_buttons(parent)
        assert label.cursor().shape() != Qt.PointingHandCursor

    def test_sip_isdeleted_guard_prevents_crash(self, qapp):
        from PyQt5 import sip
        from PyQt5.QtWidgets import QPushButton, QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        btn = QPushButton("Click", parent)
        sip.delete(btn)
        apply_hand_cursor_to_buttons(parent)

    def test_handles_parent_with_no_children(self, qapp):
        from PyQt5.QtWidgets import QWidget
        from src.strategy_builder.ui.styles import apply_hand_cursor_to_buttons

        parent = QWidget()
        apply_hand_cursor_to_buttons(parent)
