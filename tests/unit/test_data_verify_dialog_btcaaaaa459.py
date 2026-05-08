"""
Unit tests for BTCAAAAA-459 / BTCAAAAA-468:
  Add last candle timestamp to Verify Data results table and resize window.

These tests validate the acceptance criteria:
  1. Last Candle column is present (6-column table with correct header)
  2. Timestamp is formatted as '%Y-%m-%d %H:%M UTC'
  3. Window minimum size is set to accommodate the new column (no clipping)
  4. Fallback '—' is rendered when last_candle_ts is None
  5. No regressions: existing columns still populated correctly

All tests run without a Qt event loop by directly testing the dialog's
_populate_table() helper logic in isolation via mock objects.

Author: QAEngineer
Task:   BTCAAAAA-468
"""

import sys
import types
from datetime import datetime
from typing import Optional, Dict
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Stub out Qt so we can import and test without a display / Qt install.
# ---------------------------------------------------------------------------

def _make_qt_stubs():
    """Return a minimal set of Qt stubs sufficient for data_verify_dialog.py."""

    # ---- PyQt5 stub package ------------------------------------------------
    pyqt5 = types.ModuleType("PyQt5")
    pyqt5.__path__ = []          # make it look like a package

    # QtWidgets
    widgets = types.ModuleType("PyQt5.QtWidgets")

    class _Item:
        def __init__(self, text="", *a, **kw):
            self._text = str(text)
            self._color = None
            self._bold = False
            self._alignment = 0
        def setTextAlignment(self, v):   self._alignment = v
        def setForeground(self, c):      self._color = c
        def setFont(self, f):            self._bold = True
        def text(self):                  return self._text

    class _Table:
        def __init__(self, rows=0, cols=0):
            self._rows = rows
            self._cols = cols
            self._items = {}          # (row, col) -> _Item
            self._row_heights = {}
            self._header = MagicMock()
            self._header.height.return_value = 26
        # interface used by _populate_table
        def setHorizontalHeaderLabels(self, labels): self._headers = labels
        def horizontalHeader(self):    return self._header
        def setRowCount(self, n):
            self._rows = n
            self._items.clear()
        def insertRow(self, idx):      self._rows += 1
        def rowCount(self):            return self._rows
        def setItem(self, r, c, item): self._items[(r, c)] = item
        def item(self, r, c):          return self._items.get((r, c))
        def setAlternatingRowColors(self, v): pass
        def setEditTriggers(self, v):  pass
        def setSelectionMode(self, v): pass
        def setMinimumHeight(self, v): self._min_height = v
        def setStyleSheet(self, v):    pass
        def resizeRowsToContents(self): pass
        def rowHeight(self, r):        return self._row_heights.get(r, 24)
        def viewport(self):            return MagicMock()

    class _Label:
        def __init__(self, text=""):
            self._text = text
            self._style = ""
            self._visible = True
        def setText(self, t):          self._text = t
        def setFont(self, f):          pass
        def setAlignment(self, v):     pass
        def setWordWrap(self, v):      pass
        def setStyleSheet(self, s):    self._style = s
        def setVisible(self, v):       self._visible = v
        def text(self):                return self._text

    class _Signal:
        def connect(self, fn): pass
        def emit(self, *a): pass

    class _Widget:
        def __init__(self, *a, **kw):
            self.clicked = _Signal()
        def setVisible(self, v):  pass
        def setEnabled(self, v):  pass
        def setMinimumWidth(self, v): pass
        def setMinimumHeight(self, v): pass
        def setStyleSheet(self, v): pass
        def setFont(self, v): pass
        def setToolTip(self, v): pass

    class _Layout:
        def addWidget(self, *a, **kw): pass
        def addLayout(self, *a, **kw): pass
        def addStretch(self): pass
        def setSpacing(self, v): pass
        def setContentsMargins(self, *a): pass

    class _Dialog:
        def __init__(self, parent=None):
            self._min_width = 0
            self._min_height = 0
        def setWindowTitle(self, t): pass
        def setWindowFlags(self, f): pass
        def setModal(self, v): pass
        def setMinimumWidth(self, v):  self._min_width = v
        def setMinimumHeight(self, v): self._min_height = v
        def resize(self, w, h):        self._size = (w, h)
        def setStyleSheet(self, v):    pass
        def setLayout(self, l):        pass
        def reject(self):              pass
        def exec_(self):               pass

    class _GroupBox:
        def __init__(self, title=""):  pass
        def setLayout(self, l):        pass

    class _ProgressBar:
        def setVisible(self, v):  pass
        def setMaximum(self, v):  pass
        def setValue(self, v):    pass

    class _PushButton(_Widget):
        def __init__(self, label=""):
            super().__init__()
            self.clicked = _Signal()

    class _HBoxLayout(_Layout):
        def addStretch(self): pass

    class _VBoxLayout(_Layout):
        pass

    for name in ("QDialog", "QVBoxLayout", "QHBoxLayout", "QLabel", "QPushButton",
                 "QProgressBar", "QTableWidget", "QTableWidgetItem", "QHeaderView",
                 "QGroupBox", "QAbstractItemView"):
        setattr(widgets, name, {
            "QDialog": _Dialog,
            "QVBoxLayout": _VBoxLayout,
            "QHBoxLayout": _HBoxLayout,
            "QLabel": _Label,
            "QPushButton": _PushButton,
            "QProgressBar": _ProgressBar,
            "QTableWidget": _Table,
            "QTableWidgetItem": _Item,
            "QHeaderView": type("QHeaderView", (), {
                "ResizeToContents": 3,
                "Stretch": 1,
                "setSectionResizeMode": lambda self, *a: None,
                "height": lambda self: 26,
            }),
            "QGroupBox": _GroupBox,
            "QAbstractItemView": type("QAbstractItemView", (), {
                "NoEditTriggers": 0,
                "SingleSelection": 1,
            }),
        }[name])

    # QtCore
    core = types.ModuleType("PyQt5.QtCore")
    core.Qt = type("Qt", (), {
        "AlignCenter": 4, "AlignLeft": 1, "AlignVCenter": 128,
        "Window": 1, "WindowTitleHint": 2, "WindowCloseButtonHint": 4,
        "WindowMinimizeButtonHint": 8, "WindowMaximizeButtonHint": 16,
    })
    core.QThread     = type("QThread", (), {"start": lambda s: None,
                                             "isRunning": lambda s: False,
                                             "quit": lambda s: None,
                                             "wait": lambda s, t: None})
    core.pyqtSignal  = lambda *a: MagicMock()
    core.QSettings   = type("QSettings", (), {"__init__": lambda s, *a: None,
                                               "value": lambda s, k: None,
                                               "setValue": lambda s, k, v: None})

    # QtGui
    gui = types.ModuleType("PyQt5.QtGui")
    gui.QColor = type("QColor", (), {"__init__": lambda s, *a: None})

    # Wire sub-modules
    pyqt5.QtWidgets = widgets
    pyqt5.QtCore    = core
    pyqt5.QtGui     = gui
    sys.modules["PyQt5"]            = pyqt5
    sys.modules["PyQt5.QtWidgets"]  = widgets
    sys.modules["PyQt5.QtCore"]     = core
    sys.modules["PyQt5.QtGui"]      = gui

    return widgets, core, gui


_QWidgets, _QCore, _QGui = _make_qt_stubs()


# ---------------------------------------------------------------------------
# Stub the heavy imports inside data_verify_dialog
# ---------------------------------------------------------------------------

# Stub UnifiedDataManager
_um_stub = types.ModuleType("src.data_manager.unified_manager")
_um_stub.UnifiedDataManager = MagicMock()
sys.modules["src.data_manager.unified_manager"] = _um_stub

# Stub styles module
_styles_stub = types.ModuleType("src.strategy_builder.ui.styles")
_styles_stub.get_main_stylesheet          = lambda: ""
_styles_stub.get_panel_title_stylesheet   = lambda: ""
_styles_stub.get_label_style              = lambda *a: ""
_styles_stub.get_italic_label_style       = lambda *a: ""
_styles_stub.get_status_label_style       = lambda *a: ""
_styles_stub.get_primary_button_stylesheet   = lambda: ""
_styles_stub.get_secondary_button_stylesheet = lambda: ""
_styles_stub.get_table_stylesheet         = lambda: ""
_styles_stub.create_font                  = lambda **kw: MagicMock()
_styles_stub.apply_hand_cursor_to_buttons = lambda w: None
_styles_stub.COLORS = {
    "success":        "#00ff00",
    "error":          "#ff0000",
    "warning":        "#ffaa00",
    "text_secondary": "#aaaaaa",
    "text_muted":     "#666666",
    "info":           "#0088ff",
}
sys.modules["src.strategy_builder.ui.styles"] = _styles_stub

# Now import the dialog (Qt objects are all stubs)
from src.strategy_builder.ui.data_verify_dialog import (  # noqa: E402
    DataVerifyDialog,
    DataVerifyThread,
    _BINANCE_HORIZON_DAYS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(
    timeframes=("15m", "1h", "1d"),
    last_candle_overrides: Optional[Dict] = None,
    gaps_override: Optional[Dict] = None,
) -> Dict:
    """Build a minimal, gap-free report dict for use in table tests."""
    last_candle_overrides = last_candle_overrides or {}
    gaps_override = gaps_override or {}
    report = {}
    for tf in timeframes:
        report[tf] = {
            "repairable":             [],
            "too_old":                [],
            "gaps_found":             gaps_override.get(tf, 0),
            "repairable_count":       0,
            "too_old_count":          0,
            "total_missing_bars":     0,
            "repairable_missing_bars": 0,
            "too_old_missing_bars":   0,
            "last_candle_ts":         last_candle_overrides.get(tf),
        }
    return report


def _make_dialog() -> DataVerifyDialog:
    """Construct dialog without triggering verification thread."""
    with patch.object(DataVerifyDialog, "_start_verification", return_value=None):
        dlg = DataVerifyDialog(parent=None)
    return dlg


# ---------------------------------------------------------------------------
# Tests: table structure (AC-1, AC-3)
# ---------------------------------------------------------------------------

class TestTableStructure:
    """The results table must have 6 columns including 'Last Candle'."""

    def test_table_has_six_columns(self):
        dlg = _make_dialog()
        assert dlg._table._cols == 6, (
            "Table must have 6 columns: Timeframe, Status, Gaps Found, "
            "Missing Bars, Last Candle, Notes"
        )

    def test_table_header_includes_last_candle(self):
        dlg = _make_dialog()
        # The header labels are set via setHorizontalHeaderLabels in _init_ui.
        assert "Last Candle" in dlg._table._headers, (
            "Column header 'Last Candle' not found in table headers"
        )

    def test_column_order(self):
        dlg = _make_dialog()
        expected = ["Timeframe", "Status", "Gaps Found", "Missing Bars", "Last Candle", "Notes"]
        assert dlg._table._headers == expected, (
            f"Column headers mismatch. Got: {dlg._table._headers}"
        )


# ---------------------------------------------------------------------------
# Tests: window size (AC-3)
# ---------------------------------------------------------------------------

class TestWindowSize:
    """Window must be wide/tall enough to not clip the new column."""

    def test_minimum_width_is_at_least_1000(self):
        dlg = _make_dialog()
        assert dlg._table._min_height >= 0  # sanity — table exists
        # Minimum width is set on the QDialog itself; check via the stub
        assert getattr(dlg, "_min_width", 1300) >= 1000, (
            "Dialog minimum width must be ≥ 1000 px to avoid clipping"
        )

    def test_minimum_width_set_to_1300(self):
        dlg = _make_dialog()
        assert dlg._min_width == 1300

    def test_minimum_height_set_to_720(self):
        dlg = _make_dialog()
        assert dlg._min_height == 720

    def test_initial_resize_to_1380(self):
        dlg = _make_dialog()
        assert dlg._size == (1380, 800), (
            f"Expected resize(1380, 800), got {dlg._size}"
        )


# ---------------------------------------------------------------------------
# Tests: Last Candle timestamp rendering (AC-1, AC-2)
# ---------------------------------------------------------------------------

class TestLastCandleRendering:
    """Last Candle column must render readable ISO-like timestamps."""

    def test_timestamp_format(self):
        """Timestamp is formatted as 'YYYY-MM-DD HH:MM UTC'."""
        ts = datetime(2026, 5, 8, 12, 30, 0)
        dlg = _make_dialog()
        report = _make_report(last_candle_overrides={"15m": ts, "1h": ts, "1d": ts})
        dlg._populate_table(report)

        # Row 0 = 15m, col 4 = Last Candle
        item = dlg._table.item(0, 4)
        assert item is not None, "No item at row 0, col 4 (Last Candle for 15m)"
        assert item.text() == "2026-05-08 12:30 UTC", (
            f"Unexpected timestamp format: '{item.text()}'"
        )

    def test_all_timeframes_get_last_candle(self):
        """All three timeframe rows should carry their respective timestamps."""
        ts_map = {
            "15m": datetime(2026, 5, 7, 23, 45),
            "1h":  datetime(2026, 5, 7, 23,  0),
            "1d":  datetime(2026, 5, 7,  0,  0),
        }
        dlg = _make_dialog()
        report = _make_report(last_candle_overrides=ts_map)
        dlg._populate_table(report)

        expected = {
            0: "2026-05-07 23:45 UTC",
            1: "2026-05-07 23:00 UTC",
            2: "2026-05-07 00:00 UTC",
        }
        for row, expected_text in expected.items():
            item = dlg._table.item(row, 4)
            assert item is not None, f"Missing Last Candle item at row {row}"
            assert item.text() == expected_text, (
                f"Row {row} Last Candle mismatch: expected '{expected_text}', "
                f"got '{item.text()}'"
            )

    def test_none_timestamp_renders_dash(self):
        """When last_candle_ts is None, the cell should show '—', not crash."""
        dlg = _make_dialog()
        report = _make_report()  # no overrides → all None
        dlg._populate_table(report)

        for row in range(3):
            item = dlg._table.item(row, 4)
            assert item is not None, f"Missing Last Candle cell at row {row}"
            assert item.text() == "—", (
                f"Row {row}: expected '—' for None timestamp, got '{item.text()}'"
            )

    def test_timestamp_uses_utc_suffix(self):
        """The format string must end in ' UTC' (not local time, not 'Z')."""
        ts = datetime(2026, 1, 1, 0, 0)
        dlg = _make_dialog()
        report = _make_report(last_candle_overrides={"15m": ts, "1h": ts, "1d": ts})
        dlg._populate_table(report)

        item = dlg._table.item(0, 4)
        assert item.text().endswith("UTC"), (
            f"Timestamp must end in 'UTC', got '{item.text()}'"
        )


# ---------------------------------------------------------------------------
# Tests: no regressions in existing columns (AC-4)
# ---------------------------------------------------------------------------

class TestNoRegressions:
    """Existing columns (Timeframe, Status, Gaps Found, Missing Bars, Notes)
    must still be populated correctly after the Last Candle column was added."""

    def test_timeframe_column_still_present(self):
        dlg = _make_dialog()
        report = _make_report()
        dlg._populate_table(report)

        tfs = {dlg._table.item(r, 0).text() for r in range(3)}
        assert tfs == {"15m", "1h", "1d"}, f"Timeframe column wrong: {tfs}"

    def test_status_column_clean_with_no_gaps(self):
        dlg = _make_dialog()
        report = _make_report()  # gap-free
        dlg._populate_table(report)

        for row in range(3):
            item = dlg._table.item(row, 1)
            assert item is not None
            assert item.text() == "Clean", (
                f"Row {row} Status should be 'Clean' with no gaps, got '{item.text()}'"
            )

    def test_notes_column_still_populated(self):
        dlg = _make_dialog()
        report = _make_report()
        dlg._populate_table(report)

        for row in range(3):
            item = dlg._table.item(row, 5)
            assert item is not None, f"Notes cell missing at row {row}"
            assert item.text() != "", f"Notes cell empty at row {row}"

    def test_six_items_set_per_row(self):
        """Every row must have all 6 cells populated (no NoneType errors)."""
        dlg = _make_dialog()
        ts = datetime(2026, 5, 8, 12, 0)
        report = _make_report(last_candle_overrides={"15m": ts, "1h": ts, "1d": ts})
        dlg._populate_table(report)

        for row in range(3):
            for col in range(6):
                item = dlg._table.item(row, col)
                assert item is not None, (
                    f"Cell ({row}, {col}) is None — some column was not set"
                )

    def test_row_count_equals_timeframe_count(self):
        """Gap-free report → exactly 3 rows (one per timeframe, no secondary rows)."""
        dlg = _make_dialog()
        report = _make_report()
        dlg._populate_table(report)

        assert dlg._table.rowCount() == 3, (
            f"Expected 3 rows for 3 gap-free timeframes, got {dlg._table.rowCount()}"
        )


# ---------------------------------------------------------------------------
# Tests: DataVerifyThread report structure
# ---------------------------------------------------------------------------

class TestDataVerifyThreadReportStructure:
    """The thread must include 'last_candle_ts' in each timeframe sub-dict."""

    def test_report_has_last_candle_ts_key(self):
        """Verify the docstring-declared report structure includes last_candle_ts."""
        import inspect
        doc = DataVerifyThread.__doc__ or ""
        assert "last_candle_ts" in doc, (
            "DataVerifyThread docstring must document the 'last_candle_ts' key"
        )

    def test_thread_calls_get_last_bar_timestamp(self):
        """Thread run() must call manager.get_last_bar_timestamp() per timeframe."""
        import inspect
        src = inspect.getsource(DataVerifyThread.run)
        assert "get_last_bar_timestamp" in src, (
            "DataVerifyThread.run() must call manager.get_last_bar_timestamp(tf)"
        )

    def test_thread_stores_result_as_last_candle_ts(self):
        """Thread run() must store result under the 'last_candle_ts' key."""
        import inspect
        src = inspect.getsource(DataVerifyThread.run)
        assert "'last_candle_ts'" in src or '"last_candle_ts"' in src, (
            "DataVerifyThread.run() must store the result as 'last_candle_ts' in the report"
        )


# ---------------------------------------------------------------------------
# Tests: mixed-gap secondary row still fills col 4 correctly
# ---------------------------------------------------------------------------

class TestMixedGapSecondaryRow:
    """When a timeframe has both repairable and too-old gaps, a secondary row
    is added.  Col 4 of that row should be '—' (no last-candle for sub-row)."""

    def _make_mixed_report(self):
        from datetime import timedelta
        now = datetime.utcnow()
        old = now - timedelta(days=_BINANCE_HORIZON_DAYS + 10)
        recent = now - timedelta(days=5)

        repairable = [{"gap_start": recent, "missing_bars": 3}]
        too_old    = [{"gap_start": old,    "missing_bars": 5}]

        return {
            "15m": {
                "repairable":              repairable,
                "too_old":                 too_old,
                "gaps_found":              2,
                "repairable_count":        1,
                "too_old_count":           1,
                "total_missing_bars":      8,
                "repairable_missing_bars": 3,
                "too_old_missing_bars":    5,
                "last_candle_ts":          datetime(2026, 5, 8, 12, 0),
            },
            "1h": {
                "repairable": [], "too_old": [], "gaps_found": 0,
                "repairable_count": 0, "too_old_count": 0,
                "total_missing_bars": 0, "repairable_missing_bars": 0,
                "too_old_missing_bars": 0,
                "last_candle_ts": datetime(2026, 5, 8, 12, 0),
            },
            "1d": {
                "repairable": [], "too_old": [], "gaps_found": 0,
                "repairable_count": 0, "too_old_count": 0,
                "total_missing_bars": 0, "repairable_missing_bars": 0,
                "too_old_missing_bars": 0,
                "last_candle_ts": datetime(2026, 5, 8, 0, 0),
            },
        }

    def test_secondary_row_col4_is_dash(self):
        """Secondary ('too old') row for 15m must show '—' in Last Candle."""
        dlg = _make_dialog()
        report = self._make_mixed_report()
        dlg._populate_table(report)

        # 15m primary = row 0, secondary = row 1
        sec_item = dlg._table.item(1, 4)
        assert sec_item is not None
        assert sec_item.text() == "—", (
            f"Secondary row Last Candle should be '—', got '{sec_item.text()}'"
        )

    def test_total_row_count_with_mixed_gap(self):
        """Mixed 15m + clean 1h + clean 1d → 4 rows total (primary + secondary)."""
        dlg = _make_dialog()
        report = self._make_mixed_report()
        dlg._populate_table(report)

        assert dlg._table.rowCount() == 4, (
            f"Expected 4 rows (15m primary, 15m secondary, 1h, 1d), "
            f"got {dlg._table.rowCount()}"
        )
