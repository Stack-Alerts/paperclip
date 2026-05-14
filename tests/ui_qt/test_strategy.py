"""
E2E tests for strategy setup — select strategy, edit parameters, validate
bad input produces correct widget state (button gating and signal emission).

Happy-path: valid name entry enables Create button, signals fire correctly.
Error-path: empty name disables Create button; exclusive radio selection enforced.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_strategy.py -v
"""

import pytest
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPushButton, QRadioButton
from PyQt5.QtCore import QTimer

from src.strategy_builder.ui.new_strategy_dialog import NewStrategyDialog
from src.strategy_builder.ui.strategy_info_panel import StrategyInfoPanel
from src.strategy_builder.ui.strategy_browser_dialog import StrategyBrowserDialog


# ---------------------------------------------------------------------------
# Minimal stub orchestrator — StrategyInfoPanel stores the reference and may
# call get_current_config() during signal refresh.
# ---------------------------------------------------------------------------

class _StubOrchestrator:
    """Minimal orchestrator stub satisfying StrategyInfoPanel's interface."""

    current_strategy_id = None
    current_version_id = None

    def get_current_config(self):
        return None

    def validate_strategy(self):
        return None


# ---------------------------------------------------------------------------
# NewStrategyDialog tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_new_strategy_dialog_title(qtbot):
    """Dialog window title must be 'New Strategy'."""
    dlg = NewStrategyDialog()
    qtbot.addWidget(dlg)

    assert dlg.windowTitle() == "New Strategy"


@pytest.mark.qt_real
def test_new_strategy_create_btn_disabled_on_empty_name(qtbot):
    """
    Error path: Create button must be disabled when name field is empty.

    This validates the live _validate() gating introduced to prevent
    empty-name submissions.
    """
    dlg = NewStrategyDialog()
    qtbot.addWidget(dlg)

    assert hasattr(dlg, "name_input"), "NewStrategyDialog must expose name_input"
    dlg.name_input.clear()

    assert not dlg.create_btn.isEnabled(), (
        "Create button must be disabled when strategy name is empty"
    )


@pytest.mark.qt_real
def test_new_strategy_create_btn_enables_after_name_entry(qtbot):
    """Happy path: Create button enables once a non-blank name is typed."""
    dlg = NewStrategyDialog()
    qtbot.addWidget(dlg)

    dlg.name_input.clear()
    qtbot.keyClicks(dlg.name_input, "Asia Rejection Simple")

    assert dlg.create_btn.isEnabled(), (
        "Create button must enable after a non-blank name is typed"
    )


@pytest.mark.qt_real
def test_new_strategy_create_btn_disables_again_on_clear(qtbot):
    """
    Error path: Clearing the name after typing must disable Create again.
    Verifies the _validate() listener re-evaluates on every change.
    """
    dlg = NewStrategyDialog()
    qtbot.addWidget(dlg)

    qtbot.keyClicks(dlg.name_input, "Temporary Name")
    assert dlg.create_btn.isEnabled()

    dlg.name_input.clear()
    assert not dlg.create_btn.isEnabled(), (
        "Create button must disable again when name is cleared"
    )


@pytest.mark.qt_real
def test_new_strategy_desc_field_accepts_multiline_text(qtbot):
    """Description text area accepts and preserves multi-line input."""
    dlg = NewStrategyDialog()
    qtbot.addWidget(dlg)

    assert hasattr(dlg, "desc_input"), "NewStrategyDialog must expose desc_input"
    dlg.desc_input.setPlainText("Line one.\nLine two.")

    assert "Line one." in dlg.desc_input.toPlainText()
    assert "Line two." in dlg.desc_input.toPlainText()


# ---------------------------------------------------------------------------
# StrategyInfoPanel tests (parameter editing & signal verification)
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_strategy_info_panel_renders_name_input(qtbot):
    """StrategyInfoPanel exposes a QLineEdit at self.name_input."""
    panel = StrategyInfoPanel(orchestrator=_StubOrchestrator())
    qtbot.addWidget(panel)

    assert panel.name_input is not None
    assert isinstance(panel.name_input, QLineEdit)


@pytest.mark.qt_real
def test_strategy_info_panel_name_change_emits_signal(qtbot):
    """
    Happy path: Setting the strategy name emits strategy_name_changed.

    This validates that the signal plumbing is connected correctly so
    dependent panels (blocks, validation) react to name edits.
    """
    panel = StrategyInfoPanel(orchestrator=_StubOrchestrator())
    qtbot.addWidget(panel)

    emitted = []
    panel.strategy_name_changed.connect(emitted.append)

    panel.name_input.setText("Alpha Reversal Strategy")

    assert len(emitted) > 0, "strategy_name_changed was not emitted after setText()"
    assert emitted[-1] == "Alpha Reversal Strategy"


@pytest.mark.qt_real
def test_strategy_info_panel_type_radio_buttons_are_exclusive(qtbot):
    """
    Error path: selecting Bearish when Bullish is active must deselect Bullish.

    Verifies the QButtonGroup enforces mutual exclusion — only one strategy
    direction can be active at a time.
    """
    panel = StrategyInfoPanel(orchestrator=_StubOrchestrator())
    qtbot.addWidget(panel)

    bullish = panel.bullish_radio
    bearish = panel.bearish_radio

    assert bullish is not None, "bullish_radio not found on StrategyInfoPanel"
    assert bearish is not None, "bearish_radio not found on StrategyInfoPanel"

    bullish.setChecked(True)
    assert bullish.isChecked()
    assert not bearish.isChecked()

    bearish.setChecked(True)
    assert bearish.isChecked()
    assert not bullish.isChecked()


@pytest.mark.qt_real
def test_strategy_info_panel_type_change_emits_signal(qtbot):
    """
    Happy path: toggling the strategy type radio emits strategy_type_changed.
    """
    panel = StrategyInfoPanel(orchestrator=_StubOrchestrator())
    qtbot.addWidget(panel)

    emitted = []
    panel.strategy_type_changed.connect(emitted.append)

    current = panel.bearish_radio.isChecked()
    if not current:
        panel.bearish_radio.setChecked(True)
    else:
        panel.bullish_radio.setChecked(True)

    assert len(emitted) > 0, "strategy_type_changed was not emitted after radio toggle"


# ---------------------------------------------------------------------------
# StrategyBrowserDialog close tests (BTCAAAAA-26209 — RuntimeError when
# closing strategy browser, QPushButton deleted)
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_strategy_browser_reject_no_runtime_error(qtbot):
    """
    Closing the strategy browser via reject() (Cancel button) must not
    raise RuntimeError("underlying C/C++ object has been deleted").

    The showEvent() installs a QTimer.singleShot(200ms, ...) that can fire
    after the dialog is already closed; verifies no stale C++ reference crash.
    """
    dlg = StrategyBrowserDialog(mode='open')
    qtbot.addWidget(dlg)
    dlg.show()

    # Let the 200 ms hand-cursor timer start
    qtbot.wait(50)

    # Close via reject path (Cancel button or programmatic)
    dlg.reject()

    # After close, the dialog should be hidden.  Force pending Qt events
    # (including any delayed timer callbacks) to confirm they don't crash.
    qtbot.wait(300)

    # At minimum the Python wrapper must not have raised RuntimeError
    # from a signal firing after its C++ children were destroyed.
    assert not dlg.isVisible()


@pytest.mark.qt_real
def test_strategy_browser_accept_no_runtime_error(qtbot):
    """
    Closing the strategy browser via accept() (double-click / Open button)
    must not raise RuntimeError even when no row is selected (edge case).
    """
    dlg = StrategyBrowserDialog(mode='open')
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.wait(100)

    dlg.accept()
    qtbot.wait(300)
    assert not dlg.isVisible()


@pytest.mark.qt_real
def test_strategy_browser_rapid_open_close(qtbot):
    """
    Rapidly opening and closing the strategy browser must not trigger
    RuntimeError.  Repeated show/close cycles exercise timer races and
    stale C++ widget access patterns (BTCAAAAA-26209).
    """
    for _ in range(3):
        dlg = StrategyBrowserDialog(mode='open')
        qtbot.addWidget(dlg)
        dlg.show()
        qtbot.wait(50)
        dlg.close()
        qtbot.wait(100)


@pytest.mark.qt_real
def test_strategy_browser_close_event_no_runtime_error(qtbot):
    """
    Closing the strategy browser via the native window close (closeEvent)
    must not raise RuntimeError.  The closeEvent chain saves settings,
    closes the DB connection, and calls super().closeEvent().
    """
    dlg = StrategyBrowserDialog(mode='open')
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.wait(100)

    # Simulate native window close
    dlg.close()
    qtbot.wait(300)
    assert not dlg.isVisible()
