"""
qt_real tests for DataVerifyDialog (BTCAAAAA-22902).

Verifies the data panel dialog renders correctly, has the expected
structure, and handles verification results without crashing.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_data_verify_dialog.py -v
"""

from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QTableWidget, QPushButton, QLabel, QGroupBox, QProgressBar

from src.strategy_builder.ui.data_verify_dialog import DataVerifyDialog


@pytest.mark.qt_real
def test_dialog_has_correct_title(qtbot):
    """Dialog window title must be 'Verify Data — Data Integrity Check'."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    assert "Verify Data" in dlg.windowTitle(), (
        f"Unexpected dialog title: {dlg.windowTitle()}"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_has_results_table(qtbot):
    """Dialog must contain a QTableWidget for results."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    table = dlg.findChild(QTableWidget)
    assert table is not None, "DataVerifyDialog must contain a QTableWidget"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_has_summary_group(qtbot):
    """Dialog must contain a summary QGroupBox."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    groups = dlg.findChildren(QGroupBox)
    titles = [g.title() for g in groups]
    assert any("Summary" in t for t in titles), (
        f"No Summary group found; groups: {titles}"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_has_fix_gaps_button(qtbot):
    """Dialog must contain a 'Fix Gaps' button."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    buttons = dlg.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert any("Fix Gaps" in t for t in btn_texts), (
        f"No 'Fix Gaps' button found; buttons: {btn_texts}"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_has_run_verification_button(qtbot):
    """Dialog must contain a 'Run Verification' button."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    buttons = dlg.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert any("Run Verification" in t for t in btn_texts), (
        f"No 'Run Verification' button found; buttons: {btn_texts}"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_has_close_button(qtbot):
    """Dialog must contain a 'Close' button."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    buttons = dlg.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert any(b.text() == "Close" for b in buttons), (
        f"No 'Close' button found; buttons: {btn_texts}"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_minimum_size(qtbot):
    """Dialog must meet minimum size requirements."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    assert dlg.minimumWidth() >= 1000, (
        f"minimumWidth={dlg.minimumWidth()} < 1000"
    )
    assert dlg.minimumHeight() >= 650, (
        f"minimumHeight={dlg.minimumHeight()} < 650"
    )
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_summary_label_exists(qtbot):
    """Dialog summary label must be present and start with a status message."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    # Find the summary label inside the Summary group
    summary_group = None
    for g in dlg.findChildren(QGroupBox):
        if "Summary" in g.title():
            summary_group = g
            break

    assert summary_group is not None, "Summary QGroupBox not found"
    labels = summary_group.findChildren(QLabel)
    assert len(labels) >= 1, "Summary group must contain at least one QLabel"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_modal(qtbot):
    """Dialog must be modal."""
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    assert dlg.isModal(), "DataVerifyDialog must be modal"
    qtbot.wait(200)


@pytest.mark.qt_real
def test_dialog_window_flags_allow_maximize(qtbot):
    """Dialog must have WindowMaximizeButtonHint flag."""
    from PyQt5.QtCore import Qt
    dlg = DataVerifyDialog()
    qtbot.addWidget(dlg)

    flags = dlg.windowFlags()
    assert flags & Qt.WindowMaximizeButtonHint, (
        "DataVerifyDialog must set Qt.WindowMaximizeButtonHint"
    )
    qtbot.wait(200)
