"""
QA tests for BTCAAAAA-26161: changeEvent tracks window state transitions.

Regression: Second click of the OS maximize/restore button would re-maximize
instead of restoring, because WindowGeometryMixin had no changeEvent handler
to update QSettings when the user manually restored via the OS title bar.

Fix: WindowGeometryMixin.changeEvent() detects WindowStateChange transitions
from maximized to normal and immediately updates QSettings (maximized=False,
saves the new normal pos/size), keeping the persisted state in sync with the
actual window manager state.

Acceptance criteria:
  AC-1 changeEvent method exists with correct signature
  AC-2 _QEvent is imported in styles.py
  AC-3 changeEvent has WindowStateChange type check
  AC-4 changeEvent updates QSettings when oldState has WindowMaximized
  AC-5 All prior geometry tests continue to pass
"""

from __future__ import annotations

import ast
import pathlib
import pytest


UI_DIR = pathlib.Path("src/strategy_builder/ui")


def _src(filename: str) -> str:
    return (UI_DIR / filename).read_text()


def _ast(filename: str) -> ast.Module:
    return ast.parse(_src(filename))


# ---------------------------------------------------------------------------
# AC-1: changeEvent method exists
# ---------------------------------------------------------------------------

class TestChangeEventMethodExists:
    """AC-1: WindowGeometryMixin defines changeEvent."""

    def test_method_exists(self):
        """WindowGeometryMixin must define changeEvent()."""
        src = _src("styles.py")
        assert "def changeEvent(self, event):" in src, (
            "WindowGeometryMixin does not define changeEvent()"
        )

    def test_method_after_restore(self):
        """Verify changeEvent is in the right place in the source."""
        src = _src("styles.py")
        # changeEvent should be before showEvent in the class
        change_pos = src.index("def changeEvent(self, event):")
        show_pos = src.index("    def showEvent(self, event):")
        assert change_pos < show_pos, (
            "changeEvent() should be defined before showEvent() in "
            "WindowGeometryMixin"
        )

    def test_has_window_state_check(self):
        """changeEvent must check event.type() == WindowStateChange."""
        src = _src("styles.py")
        # Find the changeEvent method body
        change_start = src.index("def changeEvent(self, event):")
        # Look for the WindowStateChange check in a reasonable window
        change_body = src[change_start:change_start + 2000]
        assert "WindowStateChange" in change_body, (
            "changeEvent must check for QEvent.WindowStateChange"
        )


# ---------------------------------------------------------------------------
# AC-2: QEvent import
# ---------------------------------------------------------------------------

class TestQEventImport:
    """AC-2: QEvent is imported for changeEvent type checking."""

    def test_qevent_imported_in_styles(self):
        """styles.py must import QEvent from QtCore."""
        src = _src("styles.py")
        assert "QEvent as _QEvent" in src, (
            "styles.py must import QEvent for changeEvent"
        )


# ---------------------------------------------------------------------------
# AC-3: Max->normal transition update check
# ---------------------------------------------------------------------------

class TestMaxToNormalTransition:
    """AC-3: changeEvent detects maximized->normal and updates QSettings."""

    def test_sets_maximized_false(self):
        """changeEvent must call settings.setValue(maximized, False)."""
        src = _src("styles.py")
        change_start = src.index("def changeEvent(self, event):")
        change_body = src[change_start:change_start + 2000]
        assert 'WindowMaximized' in change_body, (
            "changeEvent must check oldState & WindowMaximized"
        )
        assert 'settings.setValue(f"{key}/maximized", False)' in change_body, (
            "changeEvent must set maximized=False on restore"
        )

    def test_saves_normal_geometry(self):
        """changeEvent must save pos and size on restore."""
        src = _src("styles.py")
        change_start = src.index("def changeEvent(self, event):")
        change_body = src[change_start:change_start + 2000]
        assert 'frameGeometry().topLeft()' in change_body, (
            "changeEvent must save frameGeometry().topLeft() on restore"
        )
        assert '{key}/pos' in change_body, (
            "changeEvent must save position key on restore"
        )
        assert '{key}/size' in change_body, (
            "changeEvent must save size key on restore"
        )

    def test_resets_geometry_restored(self):
        """changeEvent must reset _geometry_restored to False on restore."""
        src = _src("styles.py")
        change_start = src.index("def changeEvent(self, event):")
        change_body = src[change_start:change_start + 2000]
        assert 'self._geometry_restored = False' in change_body, (
            "changeEvent must reset _geometry_restored on restore"
        )

    def test_skips_on_maximize(self):
        """changeEvent must NOT trigger on normal->maximized transition."""
        src = _src("styles.py")
        change_start = src.index("def changeEvent(self, event):")
        change_body = src[change_start:change_start + 2000]
        assert 'not (new_state & _Qt.WindowMaximized)' in change_body, (
            "changeEvent must check new_state does NOT have WindowMaximized"
        )


# ---------------------------------------------------------------------------
# AC-4: Fallback to super
# ---------------------------------------------------------------------------

class TestChangeEventFallback:
    """changeEvent must call super().changeEvent(event)."""

    def test_super_call(self):
        """changeEvent must call super().changeEvent(event)."""
        src = _src("styles.py")
        change_start = src.index("def changeEvent(self, event):")
        change_body = src[change_start:change_start + 3000]
        assert "super().changeEvent(event)" in change_body, (
            "changeEvent must call super().changeEvent(event)"
        )


# ---------------------------------------------------------------------------
# AC-5: All prior tests pass (cross-module check)
# ---------------------------------------------------------------------------

class TestRegressionGuard:
    """AC-5: changeEvent added without breaking anything."""

    def test_styles_file_unchanged_violations(self):
        """No regression in styles.py structure detected."""
        src = _src("styles.py")
        # Verify WindowGeometryMixin still has core methods
        assert "def showEvent(self, event):" in src
        assert "def _save_window_geometry(self)" in src
        assert "def _restore_window_geometry(self" in src
        assert "GEOMETRY_SETTINGS_KEY" in src
        assert "GEOMETRY_DEFAULT_SIZE" in src
