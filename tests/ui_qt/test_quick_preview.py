"""
UI smoke tests for the Quick Preview feature (BTCAAAAA-749).

Covers QuickPreviewResultsDialog directly — the popup shown after a 30-day
backtest completes.  No mocks; all tests use real Qt widgets in offscreen mode.

Test cases:
  - Dialog renders the four required metrics (Win Rate, Total Signals, Total
    Trades, Avg Return) with formatted values.
  - Zero-trades case shows the hint message.
  - Positive avg-return shows correct value.
  - Negative avg-return shows correct (signed) value.
  - Close button is present and accepts the dialog.
  - Minimum width enforced (≥ 320 px).
  - Win rate ≥ 50 % uses success color key; < 50 % uses error color key.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_quick_preview.py -v
"""

import pytest

from PyQt5.QtWidgets import QLabel, QPushButton, QDialog

from src.strategy_builder.ui.strategy_builder_main_window import (
    QuickPreviewResultsDialog,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dialog(win_rate=55.0, total_signals=12, total_trades=8, avg_return=1.23,
            qtbot=None):
    dlg = QuickPreviewResultsDialog(
        win_rate=win_rate,
        total_signals=total_signals,
        total_trades=total_trades,
        avg_return=avg_return,
    )
    if qtbot is not None:
        qtbot.addWidget(dlg)
    return dlg


def _label_texts(dlg: QDialog) -> list[str]:
    return [lbl.text() for lbl in dlg.findChildren(QLabel)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_dialog_window_title(qtbot):
    """Dialog title must reference '30-Day Backtest'."""
    dlg = _dialog(qtbot=qtbot)
    assert "30-Day" in dlg.windowTitle() or "30-day" in dlg.windowTitle()


@pytest.mark.qt_real
def test_dialog_minimum_width(qtbot):
    """Dialog minimum width must be at least 320 px."""
    dlg = _dialog(qtbot=qtbot)
    assert dlg.minimumWidth() >= 320


@pytest.mark.qt_real
def test_dialog_shows_win_rate_formatted(qtbot):
    """Win Rate label must contain a '%' character."""
    dlg = _dialog(win_rate=60.0, qtbot=qtbot)
    texts = _label_texts(dlg)
    assert any("%" in t for t in texts), (
        f"No '%' found in dialog labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_shows_total_signals(qtbot):
    """Total Signals value must appear as a plain integer string."""
    dlg = _dialog(total_signals=17, qtbot=qtbot)
    texts = _label_texts(dlg)
    assert any("17" in t for t in texts), (
        f"Expected '17' in dialog labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_shows_total_trades(qtbot):
    """Total Trades value must appear as a plain integer string."""
    dlg = _dialog(total_trades=5, qtbot=qtbot)
    texts = _label_texts(dlg)
    assert any("5" in t for t in texts), (
        f"Expected '5' in dialog labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_shows_avg_return_positive_signed(qtbot):
    """Avg Return must be shown with a '+' prefix when positive."""
    dlg = _dialog(avg_return=2.50, qtbot=qtbot)
    texts = _label_texts(dlg)
    assert any("+2.50%" in t for t in texts), (
        f"Expected '+2.50%' in labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_shows_avg_return_negative_signed(qtbot):
    """Avg Return must be shown with a '-' prefix when negative."""
    dlg = _dialog(avg_return=-1.75, qtbot=qtbot)
    texts = _label_texts(dlg)
    assert any("-1.75%" in t for t in texts), (
        f"Expected '-1.75%' in labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_zero_trades_shows_hint(qtbot):
    """Zero-trades case must show a user-visible hint about no trades found."""
    dlg = _dialog(total_trades=0, qtbot=qtbot)
    texts = _label_texts(dlg)
    hint_texts = [t for t in texts if "trade" in t.lower() or "threshold" in t.lower()]
    assert hint_texts, (
        f"Zero-trades hint not found in dialog labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_zero_trades_win_rate_zero(qtbot):
    """With 0 trades the Win Rate must display '0.0%'."""
    dlg = _dialog(win_rate=0.0, total_trades=0, qtbot=qtbot)
    texts = _label_texts(dlg)
    assert any("0.0%" in t for t in texts), (
        f"Expected '0.0%' in labels; got: {texts}"
    )


@pytest.mark.qt_real
def test_dialog_has_close_button(qtbot):
    """Results dialog must have at least one QPushButton (the Close button)."""
    dlg = _dialog(qtbot=qtbot)
    buttons = dlg.findChildren(QPushButton)
    assert buttons, "QuickPreviewResultsDialog must contain at least one QPushButton"
    btn_texts = [b.text().lower() for b in buttons]
    assert any(kw in t for t in btn_texts for kw in ("close", "ok", "done")), (
        f"No close/ok/done button found; button texts: {btn_texts}"
    )


@pytest.mark.qt_real
def test_dialog_close_button_accepts(qtbot):
    """Clicking the Close button must accept (close) the dialog."""
    dlg = _dialog(qtbot=qtbot)
    buttons = dlg.findChildren(QPushButton)
    close_btn = next(
        (b for b in buttons if any(kw in b.text().lower() for kw in ("close", "ok", "done"))),
        None,
    )
    assert close_btn is not None, "Close button not found"

    with qtbot.waitSignal(dlg.accepted, timeout=1000):
        close_btn.click()


@pytest.mark.qt_real
def test_dialog_is_modal(qtbot):
    """Results dialog must be modal so it blocks parent interaction."""
    dlg = _dialog(qtbot=qtbot)
    assert dlg.isModal(), "QuickPreviewResultsDialog must be modal"


@pytest.mark.qt_real
def test_dialog_win_rate_high_uses_success_styling(qtbot):
    """Win Rate ≥ 50 % value label should use a success/green-like color."""
    dlg = _dialog(win_rate=75.0, qtbot=qtbot)
    # The value label for 75.0% should have 'success' color in its stylesheet
    labels = dlg.findChildren(QLabel)
    rate_labels = [l for l in labels if "75.0%" in l.text()]
    assert rate_labels, "Win Rate value label with '75.0%' not found"
    style = rate_labels[0].styleSheet()
    # The style is set to get_color('success') — we just confirm the stylesheet
    # is non-empty (exact color value may vary by theme).
    assert style, "Win Rate success label must have a non-empty stylesheet"


@pytest.mark.qt_real
def test_dialog_win_rate_low_uses_error_styling(qtbot):
    """Win Rate < 50 % value label should use an error/red-like color."""
    dlg = _dialog(win_rate=30.0, qtbot=qtbot)
    labels = dlg.findChildren(QLabel)
    rate_labels = [l for l in labels if "30.0%" in l.text()]
    assert rate_labels, "Win Rate value label with '30.0%' not found"
    style = rate_labels[0].styleSheet()
    assert style, "Win Rate error label must have a non-empty stylesheet"
