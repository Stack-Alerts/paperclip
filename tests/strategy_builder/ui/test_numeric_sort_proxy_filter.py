"""
Unit Tests for NumericSortProxyModel.filterAcceptsRow() — BTCAAAAA-195

Verifies that the min-trades filter lives on NumericSortProxyModel (the
QSortFilterProxyModel subclass) rather than on ConfigDiscoveryResultsDialog,
and that it correctly excludes rows whose trade-count value is below the
configured threshold.

Author: UIEngineer (BTCAAAAA-195)
Date: 2026-05-06
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Determine whether real PyQt5 is available
# ---------------------------------------------------------------------------

def _real_pyqt5_available() -> bool:
    try:
        import PyQt5.QtCore  # noqa: F401
        return True
    except ImportError:
        return False


_HAS_REAL_QT = _real_pyqt5_available()


# ---------------------------------------------------------------------------
# Minimal PyQt5 stubs — used only when real PyQt5 is NOT importable
# ---------------------------------------------------------------------------

def _install_pyqt5_stubs() -> None:
    if _HAS_REAL_QT:
        return  # leave the real package alone

    def _pyqtSignal(*a, **kw):
        sig = MagicMock()
        sig.emit = MagicMock()
        sig.connect = MagicMock()
        sig.disconnect = MagicMock()
        return sig

    class _Qt:
        UserRole = 256
        AlignRight = 0x02
        AlignLeft = 0x01
        AlignVCenter = 0x80
        AlignCenter = 0x84
        WindowModal = 0
        Horizontal = 1
        Vertical = 2
        DescendingOrder = 1
        Window = 0x00000001

    class _QSortFilterProxyModel:
        def __init__(self, parent=None):
            self._source = None

        def setSourceModel(self, model):
            self._source = model

        def sourceModel(self):
            return self._source

        def invalidateFilter(self):
            pass

        def setFilterKeyColumn(self, col):
            pass

        def setFilterRole(self, role):
            pass

        def setFilterWildcard(self, pattern):
            pass

        def lessThan(self, left, right):
            return False

        def sort(self, col, order):
            pass

    pyqt5 = types.ModuleType("PyQt5")
    qt_core = types.ModuleType("PyQt5.QtCore")
    qt_core.Qt = _Qt
    qt_core.QThread = MagicMock
    qt_core.pyqtSignal = _pyqtSignal
    qt_core.QTimer = MagicMock
    qt_core.QEventLoop = MagicMock
    qt_core.QSortFilterProxyModel = _QSortFilterProxyModel

    qt_widgets = types.ModuleType("PyQt5.QtWidgets")
    for _name in (
        "QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QPushButton",
        "QProgressBar", "QTextEdit", "QGroupBox", "QApplication",
        "QWidget", "QMainWindow", "QSpinBox", "QDoubleSpinBox",
        "QComboBox", "QCheckBox", "QRadioButton", "QButtonGroup",
        "QMessageBox", "QProgressDialog", "QTabWidget", "QScrollArea",
        "QSplitter", "QFrame", "QSizePolicy", "QAbstractItemView",
        "QHeaderView", "QTableView", "QSlider",
    ):
        setattr(qt_widgets, _name, MagicMock)

    qt_gui = types.ModuleType("PyQt5.QtGui")
    qt_gui.QFont = MagicMock
    qt_gui.QColor = MagicMock
    qt_gui.QStandardItem = MagicMock
    qt_gui.QStandardItemModel = MagicMock

    sys.modules.update({
        "PyQt5": pyqt5,
        "PyQt5.QtCore": qt_core,
        "PyQt5.QtWidgets": qt_widgets,
        "PyQt5.QtGui": qt_gui,
    })
    pyqt5.QtCore = qt_core
    pyqt5.QtWidgets = qt_widgets
    pyqt5.QtGui = qt_gui


_install_pyqt5_stubs()


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

try:
    from src.strategy_builder.ui.config_discovery_results_dialog import (
        NumericSortProxyModel,
        ConfigDiscoveryResultsDialog,
        COL_TRADES,
    )
    _MODULE_AVAILABLE = True
    _IMPORT_ERR = ""
except ImportError as _e:
    _MODULE_AVAILABLE = False
    _IMPORT_ERR = str(_e)

_skip_if_missing = pytest.mark.skipif(
    not _MODULE_AVAILABLE,
    reason=f"config_discovery_results_dialog import failed: {_IMPORT_ERR}",
)


# ---------------------------------------------------------------------------
# Helpers: build a source model populated with trade-count values
#
# When real PyQt5 is available we use QStandardItemModel + QStandardItem so
# the proxy's Qt C++ internals are satisfied.
# When running with stubs we fall back to a lightweight Python fake.
# ---------------------------------------------------------------------------

def _make_source_model_with_counts(trade_counts):
    """
    Return a (model, parent_index) pair where column COL_TRADES carries
    the given trade counts stored in Qt.UserRole.
    """
    if _HAS_REAL_QT:
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QStandardItem, QStandardItemModel
        num_cols = COL_TRADES + 1  # only need columns up to COL_TRADES
        model = QStandardItemModel(len(trade_counts), num_cols)
        for row, count in enumerate(trade_counts):
            item = QStandardItem()
            item.setData(count, Qt.UserRole)
            item.setText(str(count))
            model.setItem(row, COL_TRADES, item)
        return model, None  # no QModelIndex parent needed
    else:
        # Stub path — plain Python fake is fine
        class _FakeIndex:
            def __init__(self, value):
                self._value = value
            def data(self, role):
                return self._value

        class _FakeModel:
            def __init__(self, counts):
                self._rows = counts
            def index(self, row, col, parent=None):
                return _FakeIndex(self._rows[row])
            def rowCount(self, parent=None):
                return len(self._rows)

        return _FakeModel(trade_counts), None


def _proxy_with_counts(trade_counts):
    """Convenience: create NumericSortProxyModel wired to a model of trade counts."""
    proxy = NumericSortProxyModel()
    model, _ = _make_source_model_with_counts(trade_counts)
    proxy.setSourceModel(model)
    return proxy


# ---------------------------------------------------------------------------
# QApplication fixture (required for QStandardItemModel on real Qt)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qt_app():
    if _HAS_REAL_QT:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app
    else:
        yield None


# ---------------------------------------------------------------------------
# Tests — class-placement contract
# ---------------------------------------------------------------------------

class TestFilterAcceptsRowPlacement:

    @_skip_if_missing
    def test_filterAcceptsRow_is_on_proxy_not_dialog(self):
        """
        filterAcceptsRow MUST be defined directly on NumericSortProxyModel,
        NOT on ConfigDiscoveryResultsDialog.
        """
        assert "filterAcceptsRow" in NumericSortProxyModel.__dict__, (
            "filterAcceptsRow() must be defined on NumericSortProxyModel, "
            "not inherited or absent"
        )
        assert "filterAcceptsRow" not in ConfigDiscoveryResultsDialog.__dict__, (
            "filterAcceptsRow() must NOT be defined on ConfigDiscoveryResultsDialog"
        )

    @_skip_if_missing
    def test_dialog_has_no_filterAcceptsRow_in_own_dict(self):
        """Confirms the method was removed from the dialog."""
        assert "filterAcceptsRow" not in vars(ConfigDiscoveryResultsDialog)


# ---------------------------------------------------------------------------
# Tests — NumericSortProxyModel.filterAcceptsRow behaviour
# ---------------------------------------------------------------------------

class TestNumericSortProxyModelFilter:

    @_skip_if_missing
    def test_default_min_trades_is_zero(self, qt_app):
        proxy = NumericSortProxyModel()
        assert proxy.min_trades == 0

    @_skip_if_missing
    def test_zero_threshold_accepts_all_rows(self, qt_app):
        proxy = _proxy_with_counts([0, 1, 5, 100])
        proxy.min_trades = 0
        for row in range(4):
            assert proxy.filterAcceptsRow(row, None) is True, (
                f"Row {row} should be accepted when min_trades=0"
            )

    @_skip_if_missing
    def test_rows_below_threshold_excluded(self, qt_app):
        """Rows with trade_count < min_trades must be filtered out."""
        proxy = _proxy_with_counts([2, 5, 10, 50])
        proxy.min_trades = 5

        # row 0 (count=2) is below threshold
        assert proxy.filterAcceptsRow(0, None) is False, (
            "Row with trade_count=2 should be excluded when min_trades=5"
        )

    @_skip_if_missing
    def test_rows_at_threshold_included(self, qt_app):
        """Rows with trade_count == min_trades must pass the filter."""
        proxy = _proxy_with_counts([5])
        proxy.min_trades = 5
        assert proxy.filterAcceptsRow(0, None) is True

    @_skip_if_missing
    def test_rows_above_threshold_included(self, qt_app):
        proxy = _proxy_with_counts([10, 20, 100])
        proxy.min_trades = 5
        for row in range(3):
            assert proxy.filterAcceptsRow(row, None) is True

    @_skip_if_missing
    def test_mixed_rows_correct_accept_reject(self, qt_app):
        """Only rows meeting or exceeding threshold pass."""
        trade_counts = [1, 3, 5, 7, 10]
        proxy = _proxy_with_counts(trade_counts)
        proxy.min_trades = 5

        expected = [False, False, True, True, True]
        for row, (count, should_pass) in enumerate(zip(trade_counts, expected)):
            result = proxy.filterAcceptsRow(row, None)
            assert result == should_pass, (
                f"Row {row} (count={count}, min={proxy.min_trades}): "
                f"expected {should_pass}, got {result}"
            )

    @_skip_if_missing
    def test_no_source_model_accepts_row(self, qt_app):
        """Without a source model, filterAcceptsRow must not crash."""
        proxy = NumericSortProxyModel()
        proxy.min_trades = 10
        result = proxy.filterAcceptsRow(0, None)
        assert result is True

    @_skip_if_missing
    def test_threshold_update_changes_filter_behaviour(self, qt_app):
        """After updating min_trades, filter results reflect the new threshold."""
        proxy = _proxy_with_counts([3])
        proxy.min_trades = 2
        assert proxy.filterAcceptsRow(0, None) is True

        proxy.min_trades = 10
        assert proxy.filterAcceptsRow(0, None) is False
