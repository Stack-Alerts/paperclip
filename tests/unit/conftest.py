"""
Unit-test conftest: inject PyQt5 stub modules so tests that import Qt-dependent
source modules can run in headless CI environments without a display or the
PyQt5 package installed.

Covers all Qt symbols imported by source code under test, plus the subset
required by the pytest-qt plugin (QtTest, PYQT_VERSION, pyqtSlot, etc.).
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

    # ------------------------------------------------------------------ #
    # QtCore                                                               #
    # ------------------------------------------------------------------ #
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
        # Additional flags used by source modules
        WA_TranslucentBackground = 120
        FramelessWindowHint = 0x00000800
        WindowStaysOnTopHint = 0x00040000
        CustomizeWindowHint = 0x02000000
        WindowCloseButtonHint = 0x08000000
        TextWordWrap = 0x10
        ElideRight = 0x0100
        DisplayRole = 0
        EditRole = 2
        UserRole = 0x0100
        ToolTipRole = 3
        ForegroundRole = 9
        BackgroundRole = 8
        CheckStateRole = 10
        ItemIsEnabled = 0x20
        ItemIsSelectable = 0x01
        ItemIsEditable = 0x02
        KeepAspectRatio = 1
        ScrollBarAlwaysOff = 1
        ScrollBarAsNeeded = 0
        NoPen = 0
        SolidLine = 1
        RoundCap = 0x20
        RoundJoin = 0x80
        transparent = 0

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

        def isRunning(self):
            return False

        def isFinished(self):
            return True

    def _pyqtSignal(*args, **kwargs):
        """Return a MagicMock that behaves like a Qt signal descriptor."""
        sig = MagicMock()
        sig.emit = MagicMock()
        sig.connect = MagicMock()
        sig.disconnect = MagicMock()
        return sig

    def _pyqtSlot(*args, **kwargs):
        """Decorator stub — just returns the decorated function unchanged."""
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator

    def _pyqtProperty(*args, **kwargs):
        """Property stub — returns a MagicMock."""
        return MagicMock()

    qt_core.Qt = _Qt
    qt_core.QThread = _QThread
    qt_core.pyqtSignal = _pyqtSignal
    qt_core.pyqtSlot = _pyqtSlot
    qt_core.pyqtProperty = _pyqtProperty
    qt_core.QTimer = MagicMock()
    qt_core.QSettings = MagicMock()
    qt_core.QPoint = MagicMock()
    qt_core.QSize = MagicMock()
    qt_core.QRect = MagicMock()
    qt_core.QEvent = MagicMock()
    qt_core.QEventLoop = MagicMock()
    qt_core.QModelIndex = MagicMock()
    qt_core.QRectF = MagicMock()

    # Version constant required by pytest-qt (must be >= 5.11.0 = 0x050B00)
    qt_core.PYQT_VERSION = 0x050F02  # 5.15.2
    qt_core.PYQT_VERSION_STR = "5.15.2"
    qt_core.QT_VERSION = 0x050F02
    qt_core.QT_VERSION_STR = "5.15.2"

    # Version query function required by pytest-qt header hook
    qt_core.qVersion = lambda: "5.15.2"

    # Logging functions required by pytest-qt
    qt_core.qDebug = MagicMock()
    qt_core.qWarning = MagicMock()
    qt_core.qCritical = MagicMock()
    qt_core.qFatal = MagicMock()
    qt_core.qInfo = MagicMock()

    _previous_message_handler = [None]

    def _qInstallMessageHandler(handler):
        prev = _previous_message_handler[0]
        _previous_message_handler[0] = handler
        return prev

    qt_core.qInstallMessageHandler = _qInstallMessageHandler

    # ------------------------------------------------------------------ #
    # QtWidgets                                                            #
    # ------------------------------------------------------------------ #
    qt_widgets = ModuleType("PyQt5.QtWidgets")

    class _QApplication(MagicMock):
        """QApplication stub with a working instance() classmethod."""
        _current_instance = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            _QApplication._current_instance = self

        @classmethod
        def instance(cls):
            return cls._current_instance

        def exec_(self):
            return 0

        def quit(self):
            pass

        def processEvents(self):
            pass

        def setStyle(self, style):
            pass

        def setPalette(self, palette):
            pass

    qt_widgets.QApplication = _QApplication

    for _name in (
        "QButtonGroup",
        "QCheckBox",
        "QComboBox",
        "QDialog",
        "QDialogButtonBox",
        "QFileDialog",
        "QFrame",
        "QGridLayout",
        "QGroupBox",
        "QHBoxLayout",
        "QLabel",
        "QLineEdit",
        "QListWidget",
        "QListWidgetItem",
        "QMainWindow",
        "QMessageBox",
        "QProgressBar",
        "QProgressDialog",
        "QPushButton",
        "QRadioButton",
        "QScrollArea",
        "QSizePolicy",
        "QSlider",
        "QSpinBox",
        "QSplitter",
        "QStackedWidget",
        "QStatusBar",
        "QStyle",
        "QStyledItemDelegate",
        "QTabWidget",
        "QTableWidget",
        "QTableWidgetItem",
        "QTextEdit",
        "QToolBar",
        "QToolButton",
        "QTreeWidget",
        "QTreeWidgetItem",
        "QVBoxLayout",
        "QWidget",
    ):
        setattr(qt_widgets, _name, MagicMock)

    # ------------------------------------------------------------------ #
    # QtGui                                                                #
    # ------------------------------------------------------------------ #
    qt_gui = ModuleType("PyQt5.QtGui")
    for _name in (
        "QAbstractTextDocumentLayout",
        "QBrush",
        "QColor",
        "QContextMenuEvent",
        "QCursor",
        "QFont",
        "QFontMetrics",
        "QGuiApplication",
        "QIcon",
        "QImage",
        "QKeySequence",
        "QMouseEvent",
        "QPainter",
        "QPalette",
        "QPen",
        "QPixmap",
        "QStandardItem",
        "QStandardItemModel",
        "QTextBlockFormat",
        "QTextCharFormat",
        "QTextCursor",
        "QTextDocument",
        "QTextOption",
        "QWheelEvent",
    ):
        setattr(qt_gui, _name, MagicMock)

    # ------------------------------------------------------------------ #
    # QtTest — required by pytest-qt plugin during configuration           #
    # ------------------------------------------------------------------ #
    qt_test = ModuleType("PyQt5.QtTest")
    qt_test.QTest = MagicMock()
    qt_test.QAbstractItemModelTester = MagicMock()

    # ------------------------------------------------------------------ #
    # sip — imported by styles.py as `from PyQt5 import sip`              #
    # ------------------------------------------------------------------ #
    sip = ModuleType("PyQt5.sip")
    sip.isdeleted = MagicMock(return_value=False)
    sip.wrappertype = type

    # ------------------------------------------------------------------ #
    # Register all stubs in sys.modules                                   #
    # ------------------------------------------------------------------ #
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtCore"] = qt_core
    sys.modules["PyQt5.QtWidgets"] = qt_widgets
    sys.modules["PyQt5.QtGui"] = qt_gui
    sys.modules["PyQt5.QtTest"] = qt_test
    sys.modules["PyQt5.sip"] = sip

    pyqt5.QtCore = qt_core
    pyqt5.QtWidgets = qt_widgets
    pyqt5.QtGui = qt_gui
    pyqt5.QtTest = qt_test
    pyqt5.sip = sip


# Install stubs immediately when conftest is loaded (before any test import)
_make_pyqt5_stubs()
