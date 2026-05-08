"""
Unit-test conftest: inject PyQt5 stubs so tests that import Qt-dependent
source modules can run in headless CI environments without a display or
the PyQt5 package installed.

Only the minimal surface used by the modules under test is stubbed.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _make_pyqt5_stubs() -> None:
    """Register lightweight PyQt5 stub modules in sys.modules."""
    if "PyQt5" in sys.modules:
        return  # already present (real or stubbed)

    # Top-level package
    pyqt5 = ModuleType("PyQt5")

    # --- QtCore ---
    qt_core = ModuleType("PyQt5.QtCore")

    class _Qt:
        AlignCenter = 0x84
        AlignLeft = 0x01
        AlignRight = 0x02
        AlignTop = 0x20
        AlignBottom = 0x40
        AlignVCenter = 0x80
        Horizontal = 0x01
        Vertical = 0x02

    class _QThread(MagicMock):
        """Minimal QThread stub — subclasses just need to call run()."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def start(self):
            pass

        def quit(self):
            pass

        def wait(self):
            pass

    def _pyqtSignal(*args, **kwargs):
        """Return a MagicMock that behaves like a Qt signal."""
        sig = MagicMock()
        sig.emit = MagicMock()
        sig.connect = MagicMock()
        sig.disconnect = MagicMock()
        return sig

    qt_core.Qt = _Qt
    qt_core.QThread = _QThread
    qt_core.pyqtSignal = _pyqtSignal
    qt_core.QTimer = MagicMock()
    qt_core.QSettings = MagicMock()
    qt_core.QPoint = MagicMock()
    qt_core.QSize = MagicMock()

    # --- QtWidgets ---
    qt_widgets = ModuleType("PyQt5.QtWidgets")
    for _name in (
        "QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QPushButton",
        "QProgressBar", "QTextEdit", "QGroupBox", "QApplication",
        "QWidget", "QMainWindow",
    ):
        setattr(qt_widgets, _name, MagicMock)

    # --- QtGui ---
    qt_gui = ModuleType("PyQt5.QtGui")
    qt_gui.QFont = MagicMock()

    # Register all stubs
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtCore"] = qt_core
    sys.modules["PyQt5.QtWidgets"] = qt_widgets
    sys.modules["PyQt5.QtGui"] = qt_gui

    pyqt5.QtCore = qt_core
    pyqt5.QtWidgets = qt_widgets
    pyqt5.QtGui = qt_gui


# Install stubs immediately when conftest is loaded (before any test import)
_make_pyqt5_stubs()
