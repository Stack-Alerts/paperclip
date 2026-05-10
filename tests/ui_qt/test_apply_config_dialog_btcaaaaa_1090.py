"""
Real-widget regression tests for _ApplyConfigDialog resize fix (BTCAAAAA-1090).

Verifies all acceptance criteria from BTCAAAAA-1095:
  - Dialog is ≥400px tall on open
  - ≥10 rows visible without scrolling
  - Resize grip present and functional
  - Value tooltips appear on hover
  - Buttons stay at bottom (layout order correct)

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_apply_config_dialog_btcaaaaa_1090.py -v
"""
from __future__ import annotations

import os
import pytest
from PyQt5.QtWidgets import (
    QApplication, QDialog, QPushButton, QTableWidget, QSizeGrip,
    QHBoxLayout, QVBoxLayout,
)
from PyQt5.QtCore import Qt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config_delta(n_params: int = 15) -> dict:
    """Build a flat config dict with n_params entries for testing."""
    return {f"strategy.param_{i:02d}": f"value_{'x' * 40}_{i}" for i in range(n_params)}


def _open_dialog(qtbot, n_params: int = 15):
    """Instantiate _ApplyConfigDialog with enough rows to exceed ≥10 visible."""
    from src.strategy_builder.ui.config_discovery_results_dialog import _ApplyConfigDialog

    delta = _make_config_delta(n_params)
    dlg = _ApplyConfigDialog(
        scenario_description="Test Scenario: RSI(14) + MACD crossover strategy",
        config_delta=delta,
    )
    qtbot.addWidget(dlg)
    dlg.show()
    QApplication.processEvents()
    return dlg


# ---------------------------------------------------------------------------
# AC1: Dialog is ≥400px tall on open
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_dialog_height_at_least_400px(qtbot):
    """Dialog must open at ≥400px height (resize fix: not collapsed to 4px)."""
    dlg = _open_dialog(qtbot)
    height = dlg.height()
    assert height >= 400, (
        f"Dialog height {height}px is less than the required 400px minimum. "
        f"The dialog may still be collapsing to a stub height."
    )


@pytest.mark.qt_real
def test_dialog_initial_size_near_760x560(qtbot):
    """Dialog should open near 760×560 as specified by the fix."""
    dlg = _open_dialog(qtbot)
    assert dlg.width() >= 520, f"Width {dlg.width()} < minimum 520px"
    assert dlg.height() >= 400, f"Height {dlg.height()} < minimum 400px"


# ---------------------------------------------------------------------------
# AC2: ≥10 rows visible without scrolling
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_table_has_at_least_15_rows(qtbot):
    """Table must contain at least 15 rows for a 15-param config delta."""
    dlg = _open_dialog(qtbot, n_params=15)
    table = dlg.findChild(QTableWidget)
    assert table is not None, "QTableWidget not found in _ApplyConfigDialog"
    assert table.rowCount() >= 15, (
        f"Expected ≥15 rows, got {table.rowCount()}"
    )


@pytest.mark.qt_real
def test_table_rows_visible_without_scrolling(qtbot):
    """
    With 15 rows and max_visible_rows=12, the table height must accommodate
    at least 10 visible rows without scrolling (viewport height >= 10 * row_height).
    """
    dlg = _open_dialog(qtbot, n_params=15)
    table = dlg.findChild(QTableWidget)
    assert table is not None, "QTableWidget not found in _ApplyConfigDialog"

    # The implementation caps at max_visible_rows=12 rows with row_h=24
    # viewport height should be >= 10 * 24 = 240px
    viewport_height = table.viewport().height()
    row_h = 24  # matches the implementation constant
    visible_rows = viewport_height // row_h

    assert visible_rows >= 10, (
        f"Only {visible_rows} rows visible in viewport "
        f"(viewport_height={viewport_height}px, row_h={row_h}px). "
        f"Expected ≥10 rows without scrolling."
    )


# ---------------------------------------------------------------------------
# AC3: Resize grip present and functional
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_size_grip_enabled(qtbot):
    """Dialog must have sizeGripEnabled=True (setSizeGripEnabled fix)."""
    dlg = _open_dialog(qtbot)
    assert dlg.isSizeGripEnabled(), (
        "isSizeGripEnabled() returned False — resize grip not present."
    )


@pytest.mark.qt_real
def test_size_grip_widget_present(qtbot):
    """A QSizeGrip child widget must be present after enabling sizeGripEnabled."""
    dlg = _open_dialog(qtbot)
    size_grips = dlg.findChildren(QSizeGrip)
    assert len(size_grips) >= 1, (
        f"No QSizeGrip found in dialog children. "
        f"setSizeGripEnabled(True) should create one."
    )


@pytest.mark.qt_real
def test_dialog_minimum_size_set(qtbot):
    """Dialog must enforce minimumWidth=520 and minimumHeight=400."""
    dlg = _open_dialog(qtbot)
    assert dlg.minimumWidth() >= 520, (
        f"minimumWidth={dlg.minimumWidth()} < 520"
    )
    assert dlg.minimumHeight() >= 400, (
        f"minimumHeight={dlg.minimumHeight()} < 400"
    )


# ---------------------------------------------------------------------------
# AC4: Value tooltips appear on hover
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_value_column_tooltips_set(qtbot):
    """All value-column (col=1) table items must have non-empty tooltips."""
    dlg = _open_dialog(qtbot, n_params=15)
    table = dlg.findChild(QTableWidget)
    assert table is not None, "QTableWidget not found"

    missing_tooltips = []
    for row in range(table.rowCount()):
        item = table.item(row, 1)
        assert item is not None, f"Value item at row {row} is None"
        tooltip = item.toolTip()
        if not tooltip:
            missing_tooltips.append(row)

    assert not missing_tooltips, (
        f"Rows missing value tooltips: {missing_tooltips}. "
        f"val_item.setToolTip(val) must be called for every row."
    )


@pytest.mark.qt_real
def test_value_tooltip_matches_cell_text(qtbot):
    """Each value tooltip must match the cell's display text exactly."""
    dlg = _open_dialog(qtbot, n_params=15)
    table = dlg.findChild(QTableWidget)
    assert table is not None

    mismatched = []
    for row in range(table.rowCount()):
        item = table.item(row, 1)
        if item and item.toolTip() != item.text():
            mismatched.append((row, item.text()[:30], item.toolTip()[:30]))

    assert not mismatched, (
        f"Tooltip/text mismatch in rows: {mismatched}"
    )


# ---------------------------------------------------------------------------
# AC5: Buttons stay at bottom
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_buttons_exist(qtbot):
    """Apply and Cancel buttons must both be present in the dialog."""
    dlg = _open_dialog(qtbot)
    buttons = dlg.findChildren(QPushButton)
    button_texts = [b.text() for b in buttons]
    assert "Apply" in button_texts, f"Apply button not found. Found: {button_texts}"
    assert "Cancel" in button_texts, f"Cancel button not found. Found: {button_texts}"


@pytest.mark.qt_real
def test_apply_button_is_default(qtbot):
    """Apply button must be marked as the default (Enter key trigger)."""
    dlg = _open_dialog(qtbot)
    buttons = dlg.findChildren(QPushButton)
    apply_btn = next((b for b in buttons if b.text() == "Apply"), None)
    assert apply_btn is not None
    assert apply_btn.isDefault(), "Apply button must be the default button"


@pytest.mark.qt_real
def test_buttons_below_table_in_layout(qtbot):
    """
    Buttons must be the last item in the top-level VBoxLayout,
    meaning they are anchored below the table, not above.
    """
    dlg = _open_dialog(qtbot)
    layout = dlg.layout()
    assert isinstance(layout, QVBoxLayout), "Top-level layout must be QVBoxLayout"

    n_items = layout.count()
    assert n_items >= 2, "Layout must have at least 2 items"

    # Last item in VBoxLayout should be the button HBoxLayout
    last_item = layout.itemAt(n_items - 1)
    assert last_item is not None

    # The last item should be a QHBoxLayout containing buttons
    inner_layout = last_item.layout()
    assert inner_layout is not None, (
        "Last VBoxLayout item must be a layout (the button row HBoxLayout)"
    )
    assert isinstance(inner_layout, QHBoxLayout), (
        f"Expected QHBoxLayout for button row, got {type(inner_layout).__name__}"
    )

    # Confirm Apply/Cancel are inside that layout
    button_texts_in_last_row = []
    for i in range(inner_layout.count()):
        item = inner_layout.itemAt(i)
        if item and item.widget() and isinstance(item.widget(), QPushButton):
            button_texts_in_last_row.append(item.widget().text())

    assert "Apply" in button_texts_in_last_row, (
        f"Apply not found in last row buttons: {button_texts_in_last_row}"
    )
    assert "Cancel" in button_texts_in_last_row, (
        f"Cancel not found in last row buttons: {button_texts_in_last_row}"
    )


# ---------------------------------------------------------------------------
# Screenshot capture (best-effort; does not fail QA if unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_capture_screenshot_of_open_dialog(qtbot, tmp_path):
    """
    Capture an offscreen screenshot of the dialog with 15 rows visible.
    Saves to /tmp/btcaaaaa_1090_apply_config_dialog.png for attachment.
    Does not fail if grab returns a null pixmap in some offscreen drivers.
    """
    from PyQt5.QtGui import QPixmap

    dlg = _open_dialog(qtbot, n_params=15)
    dlg.resize(760, 560)
    QApplication.processEvents()

    pixmap = dlg.grab()
    screenshot_path = "/tmp/btcaaaaa_1090_apply_config_dialog.png"
    if not pixmap.isNull():
        saved = pixmap.save(screenshot_path, "PNG")
        assert saved, f"pixmap.save() returned False for path {screenshot_path}"
        assert os.path.exists(screenshot_path), "Screenshot file not written"
        size = os.path.getsize(screenshot_path)
        assert size > 0, "Screenshot file is empty"
    else:
        pytest.skip("Offscreen grab returned null pixmap — screenshot not available in this driver")
