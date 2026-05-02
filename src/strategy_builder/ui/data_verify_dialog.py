"""
Data Verify Dialog - Data Integrity Check UI

Shows per-symbol/timeframe gap analysis for stored Binance OHLCV data.
Called from Tools → Verify Data...

Verification uses verify_and_repair(dry_run=True) combined with
detect_gaps_in_binance_files() to show per-gap detail without modifying data.

Repair uses verify_and_repair(dry_run=False) to fetch and fill each specific
gap from Binance directly — NOT the general DataUpdateModal date-range download.

After repair completes the dialog automatically re-runs verification so the
user can confirm the data is now clean.

Author: Strategy Builder Team
Date: 2026-05-02
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from src.data_manager.unified_manager import UnifiedDataManager
from src.strategy_builder.ui.styles import (
    get_main_stylesheet,
    get_panel_title_stylesheet,
    get_label_style,
    get_status_label_style,
    get_primary_button_stylesheet,
    get_secondary_button_stylesheet,
    get_table_stylesheet,
    create_font,
    apply_hand_cursor_to_buttons,
    COLORS,
)


# ---------------------------------------------------------------------------
# Background threads
# ---------------------------------------------------------------------------

class DataVerifyThread(QThread):
    """
    Background thread: detect gaps without modifying any stored data.

    Calls detect_gaps_in_binance_files() for each timeframe to obtain the
    full per-gap detail list, then returns a structured report that the dialog
    uses to populate the results table.

    Signals:
        progress(int, int, str): (current, total, message)
        finished(bool, dict): (success, report)

    Report structure::

        {
            '15m': {
                'gaps': [
                    {
                        'gap_start': datetime,
                        'gap_end':   datetime,
                        'duration':  timedelta,
                        'missing_bars': int,
                        'timeframe': str,
                    },
                    ...
                ],
                'gaps_found': int,
                'total_missing_bars': int,
            },
            ...
            '_error': str,   # only present on exception
        }
    """

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, dict)

    _TIMEFRAMES = ['15m', '1h']

    def run(self):
        try:
            self.progress.emit(10, 100, "Initialising data manager…")
            manager = UnifiedDataManager(mode='live')

            report: Dict = {}
            steps = len(self._TIMEFRAMES)
            for i, tf in enumerate(self._TIMEFRAMES):
                pct_start = 20 + int(i * 70 / steps)
                pct_end = 20 + int((i + 1) * 70 / steps)
                self.progress.emit(pct_start, 100, f"Scanning {tf} data for gaps…")

                gaps: List[Dict] = manager.detect_gaps_in_binance_files(tf)
                total_missing = sum(g['missing_bars'] for g in gaps)
                report[tf] = {
                    'gaps': gaps,
                    'gaps_found': len(gaps),
                    'total_missing_bars': total_missing,
                }
                self.progress.emit(pct_end, 100, f"{tf}: {len(gaps)} gap(s) found.")

            self.progress.emit(100, 100, "Verification complete.")
            self.finished.emit(True, report)

        except Exception as exc:
            self.finished.emit(False, {'_error': str(exc)})


class DataRepairThread(QThread):
    """
    Background thread: repair detected gaps by fetching missing bars from Binance.

    Calls verify_and_repair(dry_run=False) which targets each specific gap
    range rather than a broad date-range download.

    Signals:
        progress(int, int, str): (current, total, message)
        finished(bool, dict): (success, repair_summary)
            repair_summary matches the verify_and_repair() return format.
    """

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, dict)

    def run(self):
        try:
            self.progress.emit(5, 100, "Starting gap repair via Binance…")
            manager = UnifiedDataManager(mode='live')

            # verify_and_repair with dry_run=False fetches each gap individually
            self.progress.emit(20, 100, "Fetching missing bars from Binance (this may take a moment)…")
            summary = manager.verify_and_repair(
                timeframes=['15m', '1h'],
                dry_run=False,
            )

            self.progress.emit(100, 100, "Repair complete.")
            self.finished.emit(True, summary)

        except Exception as exc:
            self.finished.emit(False, {'_error': str(exc)})


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class DataVerifyDialog(QDialog):
    """
    Dialog for verifying (and repairing) data integrity.

    States
    ------
    - idle       — initial / after close
    - verifying  — DataVerifyThread running
    - results    — table populated, Fix Gaps visible if gaps exist
    - repairing  — DataRepairThread running
    - done       — repair finished, re-verification auto-started

    Layout
    ------
    Header
    Subtitle
    [Summary GroupBox]  ← banner: green or amber
    [Results GroupBox]  ← QTableWidget
    ProgressBar + label (hidden when idle)
    [Run Verification] [Fix Gaps (conditional)] [Close]
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, parent=None):
        super().__init__(parent)
        self._verify_thread: Optional[DataVerifyThread] = None
        self._repair_thread: Optional[DataRepairThread] = None
        self._last_report: Dict = {}
        self._has_gaps: bool = False

        self._init_ui()
        self._start_verification()

    def _init_ui(self):
        self.setWindowTitle("Verify Data — Data Integrity Check")
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        )
        self.setModal(True)
        self.setMinimumWidth(860)
        self.setMinimumHeight(580)
        self.resize(940, 640)
        self.setStyleSheet(get_main_stylesheet())

        root = QVBoxLayout()
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Data Integrity Verification")
        header.setFont(create_font(size=14, bold=True))
        header.setStyleSheet(get_panel_title_stylesheet())
        root.addWidget(header)

        subtitle = QLabel(
            "Checking stored Binance OHLCV data for gaps across all symbols and timeframes."
        )
        subtitle.setFont(create_font(size=9))
        subtitle.setStyleSheet(get_label_style('muted'))
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # Summary banner
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(10, 4, 10, 8)
        summary_layout.setSpacing(2)

        self._summary_label = QLabel("Starting verification…")
        self._summary_label.setFont(create_font(size=10, bold=True))
        self._summary_label.setAlignment(Qt.AlignCenter)
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(get_status_label_style('default'))
        summary_layout.addWidget(self._summary_label)

        summary_group.setLayout(summary_layout)
        root.addWidget(summary_group)

        # Results table — 6 columns now includes Missing Bars with real counts
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(10, 10, 10, 10)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Timeframe", "Status", "Gaps Found", "Missing Bars", "Notes"]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setMinimumHeight(200)
        self._table.setStyleSheet(get_table_stylesheet())
        results_layout.addWidget(self._table)

        results_group.setLayout(results_layout)
        root.addWidget(results_group)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        root.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setFont(create_font(size=9))
        self._progress_label.setStyleSheet(
            get_label_style('muted') + " font-style: italic;"
        )
        self._progress_label.setVisible(False)
        root.addWidget(self._progress_label)

        root.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._run_btn = QPushButton("Run Verification")
        self._run_btn.setMinimumWidth(160)
        self._run_btn.setMinimumHeight(38)
        self._run_btn.setStyleSheet(get_secondary_button_stylesheet())
        self._run_btn.clicked.connect(self._start_verification)
        btn_row.addWidget(self._run_btn)

        self._fix_btn = QPushButton("Fix Gaps")
        self._fix_btn.setMinimumWidth(130)
        self._fix_btn.setMinimumHeight(38)
        self._fix_btn.setStyleSheet(get_primary_button_stylesheet())
        self._fix_btn.clicked.connect(self._start_repair)
        self._fix_btn.setVisible(False)
        btn_row.addWidget(self._fix_btn)

        self._close_btn = QPushButton("Close")
        self._close_btn.setMinimumWidth(100)
        self._close_btn.setMinimumHeight(38)
        self._close_btn.setStyleSheet(get_secondary_button_stylesheet())
        self._close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._close_btn)

        root.addLayout(btn_row)
        self.setLayout(root)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _start_verification(self):
        """Kick off DataVerifyThread (read-only gap scan)."""
        if (self._verify_thread and self._verify_thread.isRunning()) or \
           (self._repair_thread and self._repair_thread.isRunning()):
            return

        self._table.setRowCount(0)
        self._has_gaps = False
        self._fix_btn.setVisible(False)
        self._run_btn.setEnabled(False)
        self._summary_label.setText("Verification in progress…")
        self._summary_label.setStyleSheet(get_status_label_style('default'))
        self._show_progress(True, "Initialising…")

        self._verify_thread = DataVerifyThread()
        self._verify_thread.progress.connect(self._on_progress)
        self._verify_thread.finished.connect(self._on_verify_finished)
        self._verify_thread.start()

    def _on_verify_finished(self, success: bool, report: Dict):
        self._show_progress(False)
        self._run_btn.setEnabled(True)
        self._last_report = report

        if not success:
            error_msg = report.get('_error', 'Unknown error')
            self._summary_label.setText(f"Verification failed: {error_msg}")
            self._summary_label.setStyleSheet(get_status_label_style('error'))
            self._add_error_row(error_msg)
            return

        self._populate_table(report)

    def _populate_table(self, report: Dict):
        """Fill the results table from the DataVerifyThread report."""
        self._table.setRowCount(0)

        total_gaps = 0
        total_missing = 0
        affected_timeframes = 0

        for tf, tf_data in report.items():
            if tf.startswith('_'):
                continue

            gaps_found: int = tf_data.get('gaps_found', 0)
            missing_bars: int = tf_data.get('total_missing_bars', 0)
            gaps: List[Dict] = tf_data.get('gaps', [])

            total_gaps += gaps_found
            total_missing += missing_bars
            if gaps_found > 0:
                affected_timeframes += 1
                self._has_gaps = True

            # Status
            if gaps_found == 0:
                status_text = "Clean"
                status_color = COLORS['success']
                notes = "No action required"
            else:
                status_text = "Gaps Found"
                status_color = COLORS['error']
                # Show earliest gap date as a hint
                if gaps:
                    earliest = min(g['gap_start'] for g in gaps)
                    notes = f"Earliest: {earliest.strftime('%Y-%m-%d %H:%M')}"
                else:
                    notes = "Use Fix Gaps to repair"

            row = self._table.rowCount()
            self._table.insertRow(row)

            def cell(text: str, color: Optional[str] = None, bold: bool = False) -> QTableWidgetItem:
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                if color:
                    item.setForeground(QColor(color))
                if bold:
                    item.setFont(create_font(size=9, bold=True))
                return item

            self._table.setItem(row, 0, cell(tf))
            self._table.setItem(row, 1, cell(status_text, status_color, bold=True))
            self._table.setItem(row, 2, cell(str(gaps_found)))
            # Real missing bar count — was "see logs", now shows actual number
            self._table.setItem(row, 3, cell("—" if missing_bars == 0 else str(missing_bars)))
            self._table.setItem(row, 4, cell(notes))

        # Summary banner
        if total_gaps == 0:
            self._summary_label.setText(
                "All data is complete — no gaps found"
            )
            self._summary_label.setStyleSheet(get_status_label_style('success'))
            self._fix_btn.setVisible(False)
        else:
            self._summary_label.setText(
                f"{total_gaps} gap(s) found across {affected_timeframes} timeframe(s) "
                f"({total_missing} missing bars) — use Fix Gaps to repair"
            )
            self._summary_label.setStyleSheet(get_status_label_style('warning'))
            self._fix_btn.setVisible(True)

    # ------------------------------------------------------------------
    # Repair
    # ------------------------------------------------------------------

    def _start_repair(self):
        """
        Kick off DataRepairThread.

        Calls verify_and_repair(dry_run=False) which fetches each detected
        gap from Binance individually.  After repair finishes, automatically
        re-runs verification so the user can confirm the data is clean.
        """
        if self._repair_thread and self._repair_thread.isRunning():
            return

        self._fix_btn.setVisible(False)
        self._run_btn.setEnabled(False)
        self._summary_label.setText("Repairing gaps — fetching missing bars from Binance…")
        self._summary_label.setStyleSheet(get_status_label_style('info'))
        self._show_progress(True, "Starting repair…")

        self._repair_thread = DataRepairThread()
        self._repair_thread.progress.connect(self._on_progress)
        self._repair_thread.finished.connect(self._on_repair_finished)
        self._repair_thread.start()

    def _on_repair_finished(self, success: bool, summary: Dict):
        self._show_progress(False)

        if not success:
            error_msg = summary.get('_error', 'Unknown error')
            self._summary_label.setText(f"Repair failed: {error_msg}")
            self._summary_label.setStyleSheet(get_status_label_style('error'))
            self._run_btn.setEnabled(True)
            return

        # Build a quick human-readable repair result
        repaired = sum(v.get('gaps_repaired', 0) for k, v in summary.items() if not k.startswith('_'))
        too_old = sum(v.get('gaps_too_old', 0) for k, v in summary.items() if not k.startswith('_'))
        bars = sum(v.get('bars_fetched', 0) for k, v in summary.items() if not k.startswith('_'))
        errors = [e for k, v in summary.items() if not k.startswith('_') for e in v.get('errors', [])]

        if errors:
            self._summary_label.setText(
                f"Repair completed with warnings: {repaired} gap(s) fixed, "
                f"{len(errors)} error(s) — re-verifying…"
            )
            self._summary_label.setStyleSheet(get_status_label_style('warning'))
        elif too_old > 0 and repaired == 0:
            self._summary_label.setText(
                f"Gaps are older than the Binance API horizon — cannot auto-repair. "
                f"Re-verifying to confirm…"
            )
            self._summary_label.setStyleSheet(get_status_label_style('warning'))
        else:
            self._summary_label.setText(
                f"Repair done: {repaired} gap(s) fixed, {bars} bars fetched — re-verifying…"
            )
            self._summary_label.setStyleSheet(get_status_label_style('success'))

        # Always re-run verification so the user sees the current state
        self._start_verification()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _on_progress(self, current: int, total: int, message: str):
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._progress_label.setText(message)

    def _show_progress(self, visible: bool, message: str = ""):
        self._progress_bar.setVisible(visible)
        self._progress_label.setVisible(visible)
        if visible:
            self._progress_label.setText(message)
            self._progress_bar.setValue(0)

    def _add_error_row(self, error_msg: str):
        self._table.setRowCount(1)
        item = QTableWidgetItem(error_msg)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setForeground(QColor(COLORS['error']))
        self._table.setItem(0, 4, item)

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))

    def closeEvent(self, event):
        for thread in (self._verify_thread, self._repair_thread):
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(2000)
        super().closeEvent(event)
