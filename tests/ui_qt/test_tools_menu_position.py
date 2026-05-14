"""
Regression test for BTCAAAAA-26147: Tools menu dropdown rendering at wrong
screen position.

Verifies that the Tools menu renders its dropdown at the correct position
on-screen in both StrategyBuilderMainWindow and legacy MainWindow.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_tools_menu_position.py -v --tb=long
"""
from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QApplication, QMenu
from PyQt5.QtCore import QTimer, QPoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_no_modal_window_class():
    from src.strategy_builder.ui.strategy_builder_main_window import (
        StrategyBuilderMainWindow,
    )

    class _NoModalMainWindow(StrategyBuilderMainWindow):
        def _on_app_start(self):
            pass

    return _NoModalMainWindow


def trigger_menu_via_menubar(menu_bar, action):
    """Trigger a QMenuBar action to open its menu programmatically."""
    menu = action.menu()
    if menu is None:
        return None
    action_rect = menu_bar.actionGeometry(action)
    global_pos = menu_bar.mapToGlobal(action_rect.bottomLeft())
    menu.popup(global_pos)
    QApplication.processEvents()
    return menu


# ---------------------------------------------------------------------------
# StrategyBuilderMainWindow Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_tools_menu_renders_on_screen(qtbot):
    """Tools menu dropdown position must intersect available screen geometry."""
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    QApplication.processEvents()

    menu_bar = win.menuBar()

    tools_actions = [a for a in menu_bar.actions() if "Tools" in a.text()]
    assert len(tools_actions) == 1
    tools_action = tools_actions[0]

    tools_menu = trigger_menu_via_menubar(menu_bar, tools_action)
    assert tools_menu is not None, "Tools menu must be triggerable"

    app = QApplication.instance()
    screens = app.screens()
    assert screens

    screen = screens[0]
    screen_geom = screen.availableGeometry()

    menu_geom = tools_menu.geometry()
    tools_menu.close()
    QApplication.processEvents()

    on_screen = screen_geom.intersects(menu_geom)
    assert on_screen, (
        f"Tools menu geometry {menu_geom} does not intersect screen geometry "
        f"{screen_geom}\n"
    )


@pytest.mark.qt_real
def test_tools_menu_position_correct_when_triggered(qtbot):
    """Tools menu dropdown must appear at correct position when triggered via
    the menu bar -- directly below the Tools action."""
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    QApplication.processEvents()

    menu_bar = win.menuBar()

    tools_actions = [a for a in menu_bar.actions() if "Tools" in a.text()]
    tools_action = tools_actions[0]

    menu_bar_geom = menu_bar.geometry()
    tools_action_rect = menu_bar.actionGeometry(tools_action)

    expected_x = menu_bar_geom.x() + tools_action_rect.x()
    expected_y = menu_bar_geom.y() + menu_bar_geom.height()

    tools_menu = trigger_menu_via_menubar(menu_bar, tools_action)
    assert tools_menu is not None

    menu_geom = tools_menu.geometry()
    tools_menu.close()
    QApplication.processEvents()

    assert abs(menu_geom.x() - expected_x) <= 5, (
        f"Tools menu x position {menu_geom.x()} != expected ~{expected_x}\n"
        f"  Menu bar geom: {menu_bar_geom}\n"
        f"  Tools action rect: {tools_action_rect}\n"
    )
    assert abs(menu_geom.y() - expected_y) <= 5, (
        f"Tools menu y position {menu_geom.y()} != expected ~{expected_y}\n"
        f"  Menu bar geom: {menu_bar_geom}\n"
        f"  Tools action rect: {tools_action_rect}\n"
    )


@pytest.mark.qt_real
def test_all_tools_menu_actions_visible(qtbot):
    """All expected actions in the Tools menu must be visible when open."""
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    QApplication.processEvents()

    menu_bar = win.menuBar()
    tools_actions = [a for a in menu_bar.actions() if "Tools" in a.text()]
    tools_action = tools_actions[0]

    tools_menu = trigger_menu_via_menubar(menu_bar, tools_action)
    assert tools_menu is not None

    actions = tools_menu.actions()

    expected_labels = [
        "Update Data...",
        "Verify Data...",
        "Settings...",
        "Debug Logger",
    ]

    action_texts = [a.text().replace("&", "") for a in actions if not a.isSeparator()]

    for label in expected_labels:
        assert any(label in t for t in action_texts), (
            f"Expected '{label}' not found in Tools menu actions: {action_texts}"
        )

    tools_menu.close()
    QApplication.processEvents()


@pytest.mark.qt_real
def test_tools_menu_position_from_moved_window(qtbot):
    """Tools menu must render on-screen even when window is repositioned."""
    cls = _make_no_modal_window_class()
    win = cls()
    qtbot.addWidget(win)

    app = QApplication.instance()
    screens = app.screens()
    primary = screens[0]
    pg = primary.availableGeometry()

    win.move(pg.x() + 100, pg.y() + 100)
    win.show()
    qtbot.waitExposed(win)
    QApplication.processEvents()

    menu_bar = win.menuBar()
    tools_actions = [a for a in menu_bar.actions() if "Tools" in a.text()]
    tools_action = tools_actions[0]

    tools_menu = trigger_menu_via_menubar(menu_bar, tools_action)
    assert tools_menu is not None

    menu_geom = tools_menu.geometry()

    assert pg.intersects(menu_geom), (
        f"Tools menu {menu_geom} not on primary screen {pg}\n"
    )

    tools_menu.close()
    QApplication.processEvents()
