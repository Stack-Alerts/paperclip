"""
Data Verify Dialog - Data Integrity Check UI

Shows per-symbol/timeframe gap analysis for stored Binance OHLCV data.
Called from Tools → Verify Data...

Uses verify_and_repair(dry_run=True) to detect gaps without modifying any data.
If gaps are found, offers a "Fix Gaps" button that opens DataUpdateModal.

Author: Strategy Builder Team
Date: 2026-05-02
"""

from typing import Optional, Dict
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


class DataVerifyThread(QThread):
    """
    Background thread for running data integrity verification.

    Calls UnifiedDataManager.verify_and_repair(dry_run=True) — never modifies
    stored data; reports gaps only.

    Signals:
        progress(int, int, str): (current, total, message) incremental status
        finished(bool, dict): (success, report) where report is the dict from
            verify_and_repair or an empty dict on error, and success indicates
            whether the call completed without exception.
    """

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, dict)

    def run(self):
        """Execute dry-run verification in background."""
        try:
            self.progress.emit(10, 100, "Initializing data manager...")
            manager = UnifiedDataManager(mode='live')

            self.progress.emit(30, 100, "Scanning 15m data for gaps...")
            # dry_run=True → read-only; no files are written
            report = manager.verify_and_repair(
                timeframes=['15m', '1h'],
                dry_run=True,
            )

            self.progress.emit(100, 100, "Verification complete.")
            self.finished.emit(True, report)

        except Exception as exc:
            self.finished.emit(False, {'_error': str(exc)})


class DataVerifyDialog(QDialog):
    """
    Dialog for verifying data integrity across all stored timeframes.

    Layout
    ------
    - Header label
    - Summary banner (green = clean, amber = gaps found)
    - Results table  (Symbol | Timeframe | Status | Gaps Found | Missing Bars)
    - Progress bar   (visible during scan only)
    - Button row     (Run Verification | Fix Gaps [conditional] | Close)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._verify_thread: Optional[DataVerifyThread] = None
        self._last_report: Dict = {}
        self._has_gaps: bool = False

        self._init_ui()
        # Auto-start verification immediately on open
        self._start_verification()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        """Build the dialog widget hierarchy."""
        self.setWindowTitle("Verify Data — Data Integrity Check")
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
        )
        self.setModal(True)
        self.setMinimumWidth(820)
        self.setMinimumHeight(560)
        self.resize(900, 620)
        self.setStyleSheet(get_main_stylesheet())

        root = QVBoxLayout()
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # ── Header ──────────────────────────────────────────────────────
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

        # ── Summary banner ───────────────────────────────────────────────
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

        # ── Results table ────────────────────────────────────────────────
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(10, 10, 10, 10)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Timeframe", "Status", "Gaps Found", "Missing Bars", "Notes"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setMinimumHeight(200)
        self._table.setStyleSheet(get_table_stylesheet())
        results_layout.addWidget(self._table)

        results_group.setLayout(results_layout)
        root.addWidget(results_group)

        # ── Progress bar ─────────────────────────────────────────────────
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

        # ── Buttons ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._run_btn = QPushButton("Run Verification")
        self._run_btn.setMinimumWidth(150)
        self._run_btn.setMinimumHeight(38)
        self._run_btn.setStyleSheet(get_secondary_button_stylesheet())
        self._run_btn.clicked.connect(self._start_verification)
        btn_row.addWidget(self._run_btn)

        self._fix_btn = QPushButton("Fix Gaps")
        self._fix_btn.setMinimumWidth(130)
        self._fix_btn.setMinimumHeight(38)
        self._fix_btn.setStyleSheet(get_primary_button_stylesheet())
        self._fix_btn.clicked.connect(self._on_fix_gaps)
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
    # Verification logic
    # ------------------------------------------------------------------

    def _start_verification(self):
        """Kick off the background verification thread."""
        if self._verify_thread and self._verify_thread.isRunning():
            return

        # Reset UI
        self._table.setRowCount(0)
        self._has_gaps = False
        self._fix_btn.setVisible(False)
        self._run_btn.setEnabled(False)
        self._summary_label.setText("Verification in progress…")
        self._summary_label.setStyleSheet(get_status_label_style('default'))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_label.setText("Initializing…")

        self._verify_thread = DataVerifyThread()
        self._verify_thread.progress.connect(self._on_progress)
        self._verify_thread.finished.connect(self._on_finished)
        self._verify_thread.start()

    def _on_progress(self, current: int, total: int, message: str):
        """Handle incremental progress updates."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._progress_label.setText(message)

    def _on_finished(self, success: bool, report: Dict):
        """Populate results table and update summary banner."""
        self._progress_bar.setVisible(False)
        self._progress_label.setVisible(False)
        self._run_btn.setEnabled(True)
        self._last_report = report

        if not success:
            error_msg = report.get('_error', 'Unknown error')
            self._summary_label.setText(
                f"Verification failed: {error_msg}"
            )
            self._summary_label.setStyleSheet(get_status_label_style('error'))
            self._add_error_row(error_msg)
            return

        self._populate_table(report)

    def _populate_table(self, report: Dict):
        """Fill the QTableWidget from verify_and_repair's report dict."""
        self._table.setRowCount(0)

        total_gaps = 0
        total_missing = 0

        for tf, tf_data in report.items():
            if tf.startswith('_'):
                continue  # skip internal keys

            gaps_found: int = tf_data.get('gaps_found', 0)
            gaps_repaired: int = tf_data.get('gaps_repaired', 0)
            gaps_too_old: int = tf_data.get('gaps_too_old', 0)
            bars_fetched: int = tf_data.get('bars_fetched', 0)
            errors = tf_data.get('errors', [])

            total_gaps += gaps_found

            # Derive status label and colour
            if gaps_found == 0:
                status_text = "Clean"
                status_color = COLORS['success']
            elif gaps_too_old > 0 and gaps_found == gaps_too_old:
                status_text = "Gaps (too old to repair)"
                status_color = COLORS['warning']
                self._has_gaps = True
            else:
                status_text = "Gaps Found"
                status_color = COLORS['error']
                self._has_gaps = True

            # Notes column — surface repair hints or errors
            if errors:
                notes = "; ".join(errors[:2])
            elif gaps_too_old > 0:
                notes = f"{gaps_too_old} gap(s) older than Binance API horizon"
            elif gaps_found == 0:
                notes = "No action required"
            else:
                notes = "Use Fix Gaps to repair"

            row = self._table.rowCount()
            self._table.insertRow(row)

            def cell(text: str, color: Optional[str] = None) -> QTableWidgetItem:
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                if color:
                    item.setForeground(QColor(color))
                return item

            self._table.setItem(row, 0, cell(tf))
            status_item = cell(status_text, status_color)
            status_item.setFont(create_font(size=9, bold=True))
            self._table.setItem(row, 1, status_item)
            self._table.setItem(row, 2, cell(str(gaps_found)))
            self._table.setItem(row, 3, cell("—" if gaps_found == 0 else "see logs"))
            self._table.setItem(row, 4, cell(notes))

        # Update summary banner
        if total_gaps == 0:
            self._summary_label.setText(
                "All data is complete — no gaps found"
            )
            self._summary_label.setStyleSheet(get_status_label_style('success'))
        else:
            affected = sum(
                1 for tf, d in report.items()
                if not tf.startswith('_') and d.get('gaps_found', 0) > 0
            )
            self._summary_label.setText(
                f"{total_gaps} gap(s) found across {affected} timeframe(s) "
                "— use Fix Gaps to repair"
            )
            self._summary_label.setStyleSheet(get_status_label_style('warning'))
            self._fix_btn.setVisible(True)

    def _add_error_row(self, error_msg: str):
        """Insert a single error row into the table."""
        self._table.setRowCount(1)
        item = QTableWidgetItem(error_msg)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setForeground(QColor(COLORS['error']))
        self._table.setItem(0, 4, item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_fix_gaps(self):
        """Open the DataUpdateModal to repair detected gaps."""
        from src.strategy_builder.ui.data_update_modal import DataUpdateModal
        modal = DataUpdateModal(self.parent(), auto_mode=False)
        modal.exec_()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def showEvent(self, event):
        """Apply hand cursors to buttons after the dialog is shown."""
        super().showEvent(event)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))

    def closeEvent(self, event):
        """Stop the background thread if still running on close."""
        if self._verify_thread and self._verify_thread.isRunning():
            self._verify_thread.quit()
            self._verify_thread.wait(2000)
        super().closeEvent(event)
