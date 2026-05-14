"""
Institutional-Grade Log Viewer Window - Performance Fix

Multi-tabbed log viewer with event-based filtering across all log types.
- QPlainTextEdit + QSyntaxHighlighter for performant large-file rendering
- Lazy tab loading (content loaded on first activation)
- Background worker for directory scanning and tab metadata
- Event-based institutional-grade filtering
- Capped line reads per file to prevent UI freezes

ZERO HARDCODED STYLES - All from styles.py
"""

from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QCheckBox, QLabel, QGroupBox, QApplication, QMessageBox,
    QTabWidget, QWidget, QGridLayout,
)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_color,
    create_font,
    create_monospace_font,
    WindowGeometryMixin,
)

import logging
logger = logging.getLogger(__name__)

# Performant limits — prevents UI freeze with 3000+ log files
MAX_LINES_PER_FILE = 5000
MAX_FILES_ALL_LOGS = 100

# Event patterns — color values via get_color() keys, zero hardcoded hex
EVENT_PATTERNS: Dict[str, Tuple[str, str]] = {
    "TRADE_OPENED": (
        r"TRADE OPENED|trade.*opened|Opening trade|🟢.*TRADE",
        "success",
    ),
    "TRADE_CLOSED": (
        r"TRADE CLOSED|trade.*closed|Position closed|Closing trade|😘.*TRADE",
        "info",
    ),
    "TRADE_UPDATED": (r"TRADE UPDATED|trade.*updated|Update.*trade|🔄.*TRADE", "gold"),
    "POSITIONS_SNAPSHOT": (
        r"POSITIONS SNAPSHOT|OPEN POSITIONS|Position.*snapshot|📊",
        "purple",
    ),
    "TRADE_NOT_FOUND": (r"TRADE.*NOT FOUND|Trade.*not found|❌.*TRADE", "error"),
    "MULTIPLE_POSITIONS": (
        r"multiple.*position|Multiple.*open|Several.*position|🔀",
        "dark_orange",
    ),
    "CONFIG_INITIALIZED": (
        r"Logger initialized|BlockRegistryAdapter initialized|Institutional Logger initialized",
        "success",
    ),
    "CONFIG_READ": (r"Reading|Loading|load blocks|Calling.*search", "info"),
    "CONFIG_VALIDATED": (r"validated|validation.*pass|Config.*valid|Validation complete", "success"),
    "CONFIG_MISMATCH": (r"MISMATCH|mismatch|Config.*error|Invalid.*config", "error"),
    "CONFIG_MISSING": (r"not found|missing|Config.*missing|Cannot find", "dark_orange"),
    "STARTED": (r"Starting to load|Starting", "success"),
    "STOPPED": (r"Stopped|Stopping|Shutdown|Terminated|Ending", "text_muted"),
    "PROGRESS": (r"Processing|Working|Running|progress", "info"),
    "COMPLETED": (
        r"Successfully loaded|Successfully|Success|Finished",
        "success",
    ),
    "CRITICAL": (r"CRITICAL|FATAL", "error"),
    "ERROR": (r"ERROR", "dark_orange"),
    "WARNING": (r"WARNING", "gold"),
    "BLOCK_LOADED": (
        r"Successfully loaded \d+ blocks|loaded.*blocks|Processing first block",
        "purple",
    ),
    "BLOCK_ADDED": (r"Added.*block|Block.*added|Block.*config", "success"),
    "SEARCH_RESULTS": (r"Retrieved \d+ search results|Retrieved.*search", "info"),
    "DECISION": (r"decision|deciding|evaluate|Decision:", "gold"),
    "CONDITION_MET": (r"Condition.*met|Threshold.*met|Criteria.*met", "success"),
    "SIGNAL_DETECTED": (r"Signal.*detect|Pattern.*found|Signal.*found|Detected:", "success"),
}

_HEADER_SEP = "=" * 80


# --------------------------------------------------------------------------- #
# LogSyntaxHighlighter — QSyntaxHighlighter for colored log display
# --------------------------------------------------------------------------- #


class LogSyntaxHighlighter(QSyntaxHighlighter):
    """Applies color coding to log lines via QSyntaxHighlighter.

    Much faster than the previous QTextEdit.setHtml() approach because
    highlighting happens lazily as lines are painted, not upfront on the
    entire document.
    """

    def __init__(self, document):
        super().__init__(document)
        self._rules: List[Tuple[re.Pattern, QTextCharFormat]] = []
        for event_key, (pattern_str, color_key) in EVENT_PATTERNS.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(get_color(color_key)))
            self._rules.append((re.compile(pattern_str, re.IGNORECASE), fmt))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# --------------------------------------------------------------------------- #
# TabMetadata — lightweight tab definition (no loaded content)
# --------------------------------------------------------------------------- #


class TabMetadata:
    """Holds tab metadata without loaded content until first activation."""

    def __init__(self, name: str, files: List[Path]):
        self.name = name
        self.files = files
        self._content: Optional[str] = None

    @property
    def content(self) -> Optional[str]:
        return self._content

    def load_content(self) -> str:
        """Read and cache file contents (capped to MAX_LINES_PER_FILE per file).

        Uses streaming line-by-line reads to avoid loading huge files
        (e.g. 389MB wiring_test.log) into memory.
        """
        if self._content is not None:
            return self._content
        chunks: List[str] = []
        for f in self.files:
            chunks.append(f"\n{_HEADER_SEP}\n")
            chunks.append(f"LOG FILE: {f.name}\n")
            chunks.append(f"{_HEADER_SEP}\n\n")
            try:
                line_count = 0
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if line_count >= MAX_LINES_PER_FILE:
                            chunks.append(
                                f"... [truncated at {MAX_LINES_PER_FILE} lines]"
                            )
                            break
                        chunks.append(line)
                        line_count += 1
            except Exception as exc:
                chunks.append(f"ERROR: Could not read file - {exc}\n")
        self._content = "".join(chunks)
        return self._content


# --------------------------------------------------------------------------- #
# LogLoadWorker — background directory scanner + tab builder
# --------------------------------------------------------------------------- #


class LogLoadWorker(QObject):
    """Background worker that scans log directories and builds tab metadata."""

    finished = pyqtSignal(object)

    def __init__(self, logs_base_dir: Path, current_log_file: Optional[Path] = None):
        super().__init__()
        self.logs_base_dir = logs_base_dir
        self.current_log_file = current_log_file
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            result = self._build_tabs()
            if not self._cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.finished.emit({"error": str(e)})

    def _build_tabs(self):
        """Scan directory and build TabMetadata list."""
        tabs: List[TabMetadata] = []
        all_log_files: List[Path] = []
        log_directories: Set[str] = set()

        if not self.logs_base_dir.exists():
            tabs.append(TabMetadata("All Logs", []))
            return {"tabs": tabs, "focused_tab": 0}

        all_log_files = list(self.logs_base_dir.rglob("*.log"))

        for f in all_log_files:
            try:
                rel = f.relative_to(self.logs_base_dir)
                if len(rel.parts) > 1:
                    log_directories.add(rel.parts[0])
            except ValueError:
                pass

        # All Logs tab: capped to MAX_FILES_ALL_LOGS, newest first
        capped_all = sorted(all_log_files, key=lambda p: p.stat().st_mtime, reverse=True)[
            :MAX_FILES_ALL_LOGS
        ]
        tabs.append(TabMetadata("All Logs", capped_all))
        if self._cancelled:
            return None

        for log_type in sorted(log_directories):
            type_files = [f for f in all_log_files if log_type in str(f)]
            tabs.append(TabMetadata(log_type.replace("_", " ").title(), type_files))
            if self._cancelled:
                return None

        root_log_files = [f for f in all_log_files if f.parent == self.logs_base_dir]

        signal_log = next((f for f in root_log_files if f.name == "signal_evaluator.log"), None)
        if signal_log is not None and not self._cancelled:
            tabs.append(TabMetadata("🔍 Signal Evaluator", [signal_log]))

        ai_log = next(
            (f for f in root_log_files if f.name == "ai_recommendations.log"), None
        )
        if ai_log is None:
            ai_log = next(
                (f for f in root_log_files if f.name == "test_ai_recommendations.log"), None
            )
        if ai_log is not None and not self._cancelled:
            tabs.append(TabMetadata("🤖 AI Recommendations", [ai_log]))

        focused_tab = 0
        if self.current_log_file is not None and self.current_log_file.exists():
            cname = self.current_log_file.name
            if cname in ("ai_recommendations.log", "test_ai_recommendations.log"):
                for i, t in enumerate(tabs):
                    if "AI" in t.name or "🤖" in t.name:
                        focused_tab = i
                        break
            else:
                tab_name = "Session" if cname.startswith("session_") else f"📄 {cname}"
                tabs.append(TabMetadata(tab_name, [self.current_log_file]))
                focused_tab = len(tabs) - 1

        if self._cancelled:
            return None

        return {"tabs": tabs, "focused_tab": focused_tab}


# --------------------------------------------------------------------------- #
# LogViewerWindow — main viewer dialog
# --------------------------------------------------------------------------- #


class LogViewerWindow(WindowGeometryMixin, QDialog):
    """
    Institutional-grade log viewer with tabs and event-based filtering.

    Features:
      - QPlainTextEdit + QSyntaxHighlighter for performant rendering
      - Lazy tab loading: content loaded only when tab is first activated
      - Background worker for directory scanning
      - Event-based filtering with contextual detail lines
      - Window maximize support
      - Geometry persistence (via WindowGeometryMixin)
    """

    GEOMETRY_SETTINGS_KEY = "logViewerWindow"
    GEOMETRY_DEFAULT_SIZE = (1100, 700)

    def __init__(self, log_file_path: Path = None, parent=None):
        super().__init__(parent)

        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.logs_base_dir = project_root / "logs"

        self.current_log_file = log_file_path

        self.event_filters: Dict[str, bool] = {event: True for event in EVENT_PATTERNS}

        self._tabs_meta: List[TabMetadata] = []
        self._tab_widgets: Dict[int, QPlainTextEdit] = {}
        self._tab_content_loaded: Set[int] = set()

        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[LogLoadWorker] = None

        self._init_ui()
        QTimer.singleShot(0, self._start_loading)

    # =================================================================== #
    # UI Construction
    # =================================================================== #

    def _init_ui(self):
        """Initialize UI with tabs and filters."""
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )

        log_name = self.current_log_file.name if self.current_log_file else "All Logs"
        self.setWindowTitle(f"Log Viewer - {log_name}")
        self.setMinimumSize(1200, 700)
        self.resize(1600, 1000)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        self.title_label = QLabel(f"● Institutional Log Viewer - {log_name}")
        self.title_label.setStyleSheet(get_panel_title_stylesheet())
        main_layout.addWidget(self.title_label)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)

        filters_group = self._create_event_filters()
        main_layout.addWidget(filters_group)

        bottom_bar = self._create_bottom_bar()
        main_layout.addLayout(bottom_bar)

        self.setLayout(main_layout)

    def _create_log_panel(self) -> QWidget:
        """Create a log output panel with QPlainTextEdit + syntax highlighter."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)

        large_font = create_monospace_font(16)
        text_edit.setFont(large_font)
        text_edit.document().setDefaultFont(large_font)

        text_edit.setStyleSheet(
            "QPlainTextEdit {"
            "   background-color: " + get_color("bg_dark") + ";"
            "   color: " + get_color("text_primary") + ";"
            "   border: 1px solid " + get_color("border") + ";"
            "   padding: 8px;"
            "   selection-background-color: " + get_color("bg_light") + ";"
            "}"
        )

        highlighter = LogSyntaxHighlighter(text_edit.document())
        text_edit._highlighter = highlighter

        layout.addWidget(text_edit)
        widget.setLayout(layout)
        widget.text_edit = text_edit

        return widget

    def _display_content(self, tab_index: int, content: str):
        """Display plain text content in a tab's QPlainTextEdit."""
        if tab_index not in self._tab_widgets:
            return
        filtered = self._apply_event_filters(content)
        self._tab_widgets[tab_index].setPlainText(filtered)
        self._update_stats(content, filtered)

    def _create_event_filters(self) -> QGroupBox:
        """Create event-based filter checkboxes in a clean grid layout."""
        group = QGroupBox("📊 Event Filters")
        group.setStyleSheet(
            get_groupbox_header_stylesheet()
        )

        container = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(15, 20, 15, 15)

        all_events = [
            ("TRADE_OPENED", "🟢 Trade Opened"),
            ("TRADE_CLOSED", "😘 Trade Closed"),
            ("TRADE_UPDATED", "🔄 Trade Updated"),
            ("POSITIONS_SNAPSHOT", "📊 Positions"),
            ("TRADE_NOT_FOUND", "❌ Not Found"),
            ("MULTIPLE_POSITIONS", "🔀 Multi Pos"),
            ("CONFIG_INITIALIZED", "✓ Config Init"),
            ("CONFIG_READ", "📖 Config Read"),
            ("CONFIG_VALIDATED", "✓ Validated"),
            ("CONFIG_MISMATCH", "❌ Mismatch"),
            ("CONFIG_MISSING", "⚠ Missing"),
            ("STARTED", "▶ Started"),
            ("STOPPED", "⏹ Stopped"),
            ("PROGRESS", "⏳ Progress"),
            ("COMPLETED", "✅ Completed"),
            ("CRITICAL", "🔴 Critical"),
            ("ERROR", "❌ Error"),
            ("WARNING", "⚠ Warning"),
            ("BLOCK_LOADED", "📦 Block Loaded"),
            ("BLOCK_ADDED", "➕ Block Added"),
            ("SEARCH_RESULTS", "🔍 Search"),
            ("DECISION", "🎯 Decision"),
            ("CONDITION_MET", "✓ Condition"),
            ("SIGNAL_DETECTED", "📡 Signal"),
        ]

        self.event_checkboxes: Dict[str, QCheckBox] = {}

        col = 0
        row = 0
        max_cols = 6

        for event_key, display_name in all_events:
            if event_key in EVENT_PATTERNS:
                _, color_key = EVENT_PATTERNS[event_key]
                checkbox = QCheckBox(display_name)
                checkbox.setChecked(True)
                checkbox.setFont(create_font(11))
                checkbox.setFixedWidth(320)

                hex_color = get_color(color_key)
                checkbox.setStyleSheet(
                    "QCheckBox {"
                    "   color: " + hex_color + ";"
                    "   background: transparent;"
                    "   padding: 3px;"
                    "}"
                    "QCheckBox::indicator {"
                    "   width: 40px;"
                    "   height: 18px;"
                    "}"
                )
                checkbox.stateChanged.connect(
                    lambda state, e=event_key: self._on_event_filter_changed(e, state)
                )
                self.event_checkboxes[event_key] = checkbox

                grid_layout.addWidget(checkbox, row, col)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        row += 1
        self.toggle_all_btn = QPushButton("Toggle All")
        self.toggle_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self.toggle_all_btn.setFixedSize(140, 36)
        self.toggle_all_btn.setToolTip("Enable or disable all event filters at once")
        self.toggle_all_btn.clicked.connect(self._toggle_all_filters)
        grid_layout.addWidget(self.toggle_all_btn, row, 0, 1, 1)

        container.setLayout(grid_layout)

        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(container)
        group.setLayout(group_layout)

        return group

    def _create_bottom_bar(self) -> QHBoxLayout:
        """Create bottom bar with stats and buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(15)

        self.msg_count_label = QLabel("Total Lines: <b>0</b>")
        self.msg_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.msg_count_label)

        self.filtered_count_label = QLabel("Displayed: <b>0</b>")
        self.filtered_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.filtered_count_label)

        self.event_count_label = QLabel("Events: <b>0</b>")
        self.event_count_label.setStyleSheet(
            get_label_style("warning")
        )
        layout.addWidget(self.event_count_label)

        layout.addStretch()

        copy_btn = QPushButton("📋 Copy")
        copy_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_btn.setFixedSize(130, 52)
        copy_btn.setToolTip("Copy all visible log content to the clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(copy_btn)

        copy_selection_btn = QPushButton("📋 Copy Selection")
        copy_selection_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_selection_btn.setFixedSize(240, 52)
        copy_selection_btn.setToolTip("Copy only the currently selected text in the log viewer to the clipboard")
        copy_selection_btn.clicked.connect(self._copy_selection)
        layout.addWidget(copy_selection_btn)

        clear_logs_btn = QPushButton("🗑️ Clear All Logs")
        clear_logs_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_logs_btn.setFixedSize(220, 52)
        clear_logs_btn.clicked.connect(self._clear_all_logs)
        clear_logs_btn.setToolTip("Delete ALL log files from logs directory")
        layout.addWidget(clear_logs_btn)

        close_btn = QPushButton("✖ Close")
        close_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        close_btn.setFixedSize(130, 52)
        close_btn.setToolTip("Close the log viewer window")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return layout

    # =================================================================== #
    # Background Loading
    # =================================================================== #

    def _start_loading(self):
        """Start background worker to scan log directories and build tabs."""
        if self._worker_thread is not None:
            return

        self._worker_thread = QThread()
        self._worker = LogLoadWorker(self.logs_base_dir, self.current_log_file)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_logs_loaded)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.start()

    def _on_logs_loaded(self, result):
        """Handle tab metadata from background worker."""
        self._worker_thread = None
        self._worker = None

        if isinstance(result, dict) and "error" in result:
            self._show_error_tab(str(result["error"]))
            return

        if result is None:
            return

        self._tabs_meta = result.get("tabs", [])
        focused_tab = result.get("focused_tab", 0)

        for i, meta in enumerate(self._tabs_meta):
            panel = self._create_log_panel()
            self._tab_widgets[i] = panel.text_edit
            self.tabs.addTab(panel, meta.name)

        if focused_tab < self.tabs.count():
            self.tabs.setCurrentIndex(focused_tab)

        self._activate_tab(focused_tab)

    def _show_error_tab(self, error_msg: str):
        """Show an error tab when loading fails."""
        panel = self._create_log_panel()
        self._tab_widgets[0] = panel.text_edit
        self.tabs.addTab(panel, "Error")
        panel.text_edit.setPlainText(f"Error loading logs:\n{error_msg}")

    # =================================================================== #
    # Lazy Tab Activation
    # =================================================================== #

    def _on_tab_changed(self, index: int):
        """Handle tab change — load content lazily on first activation."""
        if index < 0:
            return
        if index not in self._tab_content_loaded:
            self._activate_tab(index)
        self._update_filter_visibility(index)
        self._refresh_current_tab()

    def _activate_tab(self, index: int):
        """Load content for a tab on first activation (lazy loading)."""
        if index in self._tab_content_loaded:
            return
        if index >= len(self._tabs_meta):
            return

        meta = self._tabs_meta[index]

        # For non-focused tabs, load content lazily (may block briefly for
        # a single tab's files, which is typically 1-10 files).
        try:
            content = meta.load_content()
            self._tab_content_loaded.add(index)
            self._display_content(index, content)
        except Exception as e:
            logger.error("Error loading tab %d: %s", index, e)
            if index in self._tab_widgets:
                self._tab_widgets[index].setPlainText(f"Error loading content: {e}")

    # =================================================================== #
    # Event Filtering
    # =================================================================== #

    def _apply_event_filters(self, content: str) -> str:
        """Apply event-based filters to content — WITH CONTEXT."""
        if not content:
            return ""

        current_tab_name = self.tabs.tabText(self.tabs.currentIndex()).lower()
        if "ai" in current_tab_name and "recommendation" in current_tab_name:
            return content

        lines = content.split("\n")
        filtered: List[str] = []

        if not any(self.event_filters.values()):
            return ""

        in_event_block = False

        for line in lines:
            if self._line_matches_event_filters(line):
                filtered.append(line)
                in_event_block = True
            elif in_event_block and (
                line.startswith("  ")
                or line.startswith("\t")
                or line.startswith("Location:")
                or line.startswith("Timestamp:")
                or line.startswith("Trade ID:")
                or line.startswith("Side:")
                or line.startswith("Size:")
                or line.startswith("Entry Price:")
                or line.startswith("Status:")
            ):
                filtered.append(line)
            elif not line.strip():
                if in_event_block:
                    filtered.append(line)
                in_event_block = False
            else:
                in_event_block = False

        return "\n".join(filtered)

    def _line_matches_event_filters(self, line: str) -> bool:
        """Check if line matches any enabled event filter."""
        if not line.strip():
            return False

        for event, enabled in self.event_filters.items():
            if enabled and event in EVENT_PATTERNS:
                pattern_str, _ = EVENT_PATTERNS[event]
                if re.search(pattern_str, line, re.IGNORECASE):
                    return True

        return False

    def _on_event_filter_changed(self, event: str, state: int):
        """Handle event filter checkbox change."""
        self.event_filters[event] = state == Qt.Checked
        self._update_toggle_button_text()
        self._refresh_current_tab()

    def _update_filter_visibility(self, tab_index: int):
        """Show only relevant filters for the selected tab."""
        tab_name = self.tabs.tabText(tab_index).replace("📄 ", "").lower()

        tab_event_map = {
            "all logs": list(EVENT_PATTERNS.keys()),
            "trades": [
                "TRADE_OPENED",
                "TRADE_CLOSED",
                "TRADE_UPDATED",
                "POSITIONS_SNAPSHOT",
                "TRADE_NOT_FOUND",
                "MULTIPLE_POSITIONS",
                "CRITICAL",
                "ERROR",
                "WARNING",
            ],
            "strategy builder": [
                "CONFIG_INITIALIZED",
                "CONFIG_READ",
                "CONFIG_VALIDATED",
                "CONFIG_MISMATCH",
                "CONFIG_MISSING",
                "STARTED",
                "STOPPED",
                "PROGRESS",
                "COMPLETED",
                "CRITICAL",
                "ERROR",
                "WARNING",
                "BLOCK_LOADED",
                "BLOCK_ADDED",
                "SEARCH_RESULTS",
            ],
            "session": [
                "CONFIG_INITIALIZED",
                "CONFIG_READ",
                "CONFIG_VALIDATED",
                "STARTED",
                "STOPPED",
                "COMPLETED",
                "ERROR",
                "WARNING",
                "BLOCK_LOADED",
                "SEARCH_RESULTS",
            ],
            "optimizer": [
                "STARTED",
                "STOPPED",
                "PROGRESS",
                "COMPLETED",
                "CRITICAL",
                "ERROR",
                "WARNING",
            ],
            "backtest": [
                "TRADE_OPENED",
                "TRADE_CLOSED",
                "TRADE_UPDATED",
                "STARTED",
                "STOPPED",
                "PROGRESS",
                "COMPLETED",
                "CRITICAL",
                "ERROR",
                "WARNING",
            ],
        }

        relevant_events: Optional[List[str]] = None
        for key, events in tab_event_map.items():
            if key in tab_name:
                relevant_events = events
                break
        if relevant_events is None:
            relevant_events = list(EVENT_PATTERNS.keys())

        filter_group: Optional[QGroupBox] = None
        for i in range(self.layout().count()):
            w = self.layout().itemAt(i).widget()
            if isinstance(w, QGroupBox) and "Event Filters" in w.title():
                filter_group = w
                break

        if not filter_group:
            return

        container = filter_group.layout().itemAt(0).widget()
        grid_layout = container.layout()

        if not isinstance(grid_layout, QGridLayout):
            return

        for checkbox in self.event_checkboxes.values():
            grid_layout.removeWidget(checkbox)
            checkbox.hide()

        col = 0
        row = 0
        max_cols = 6

        all_events_ordered = [
            "TRADE_OPENED",
            "TRADE_CLOSED",
            "TRADE_UPDATED",
            "POSITIONS_SNAPSHOT",
            "TRADE_NOT_FOUND",
            "MULTIPLE_POSITIONS",
            "CONFIG_INITIALIZED",
            "CONFIG_READ",
            "CONFIG_VALIDATED",
            "CONFIG_MISMATCH",
            "CONFIG_MISSING",
            "STARTED",
            "STOPPED",
            "PROGRESS",
            "COMPLETED",
            "CRITICAL",
            "ERROR",
            "WARNING",
            "BLOCK_LOADED",
            "BLOCK_ADDED",
            "SEARCH_RESULTS",
            "DECISION",
            "CONDITION_MET",
            "SIGNAL_DETECTED",
        ]

        for event_key in all_events_ordered:
            if event_key in relevant_events and event_key in self.event_checkboxes:
                checkbox = self.event_checkboxes[event_key]
                checkbox.show()
                grid_layout.addWidget(checkbox, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

    def _refresh_current_tab(self):
        """Re-apply event filters to the current tab's cached content."""
        index = self.tabs.currentIndex()
        if index < 0:
            return
        if index in self._tab_content_loaded and index < len(self._tabs_meta):
            content = self._tabs_meta[index].content
            if content is not None:
                self._display_content(index, content)

    def _toggle_all_filters(self):
        """Toggle all event filters on/off."""
        new_state = self.toggle_all_btn.text() == "Select All"
        for checkbox in self.event_checkboxes.values():
            checkbox.setChecked(new_state)

    def _update_toggle_button_text(self):
        """Update toggle button text based on current state."""
        all_selected = all(self.event_filters.values())
        self.toggle_all_btn.setText("Unselect All" if all_selected else "Select All")

    def _update_stats(self, original: str, filtered: str):
        """Update statistics labels."""
        total_lines = len(original.split("\n"))
        displayed_lines = len(filtered.split("\n"))

        event_count = 0
        for line in filtered.split("\n"):
            for pattern_str, _ in EVENT_PATTERNS.values():
                if re.search(pattern_str, line, re.IGNORECASE):
                    event_count += 1
                    break

        self.msg_count_label.setText(f"Total Lines: <b>{total_lines:,}</b>")
        self.filtered_count_label.setText(f"Displayed: <b>{displayed_lines:,}</b>")
        self.event_count_label.setText(f"Events: <b>{event_count:,}</b>")

    # =================================================================== #
    # Actions
    # =================================================================== #

    def _copy_to_clipboard(self):
        """Copy all visible content from current tab to clipboard."""
        index = self.tabs.currentIndex()
        if index not in self._tab_widgets:
            return

        content = self._tab_widgets[index].toPlainText()
        if not content:
            QMessageBox.information(self, "Nothing to Copy", "No content to copy.")
            return

        QApplication.clipboard().setText(content)
        line_count = len(content.split("\n"))
        self.filtered_count_label.setText(
            f"✅ Copied {line_count:,} lines to clipboard"
        )

    def _copy_selection(self):
        """Copy selected text from current tab."""
        index = self.tabs.currentIndex()
        if index not in self._tab_widgets:
            return

        selected = (
            self._tab_widgets[index]
            .textCursor()
            .selectedText()
            .replace("\u2029", "\n")
        )
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select text to copy.")
            return

        QApplication.clipboard().setText(selected)
        line_count = len(selected.split("\n"))
        self.filtered_count_label.setText(
            f"✅ Copied {line_count:,} selected lines"
        )

    def _clear_all_logs(self):
        """Delete ALL log files from logs directory and reset the viewer."""
        try:
            if not self.logs_base_dir.exists():
                QMessageBox.critical(
                    self, "Directory Not Found",
                    f"Logs directory does not exist:\n{self.logs_base_dir}",
                )
                return

            fresh_log_files = list(self.logs_base_dir.rglob("*.log"))

            if not fresh_log_files:
                QMessageBox.warning(self, "No Logs", "No log files found to delete.")
                return

            reply = QMessageBox.question(
                self,
                "Clear All Logs",
                f"⚠️  DELETE {len(fresh_log_files)} log files?"
                f"\n\nThis action cannot be undone.\n\n"
                f"Are you sure you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                return

            deleted_count = 0
            total_size = 0
            failed_files: List[str] = []

            for log_file in fresh_log_files:
                try:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    total_size += file_size
                except Exception as e:
                    failed_files.append(f"{log_file.name}: {e}")
                    logger.error("Error deleting %s: %s", log_file, e)

            size_mb = total_size / (1024 * 1024)
            QMessageBox.information(
                self,
                "Logs Cleared",
                f"Successfully deleted {deleted_count} log files."
                f"\n\nSpace freed: {size_mb:.2f} MB",
            )

            self._tabs_meta.clear()
            self._tab_widgets.clear()
            self._tab_content_loaded.clear()

            while self.tabs.count() > 0:
                self.tabs.removeTab(0)

            empty_meta = TabMetadata("All Logs", [])
            self._tabs_meta.append(empty_meta)
            panel = self._create_log_panel()
            self._tab_widgets[0] = panel.text_edit
            self.tabs.addTab(panel, "All Logs")
            self._tab_content_loaded.add(0)
            panel.text_edit.setPlainText("(No logs available)")

            self.filtered_count_label.setText(
                f"✅ Cleared {deleted_count} log files ({size_mb:.1f} MB)"
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error clearing logs:\n\n{str(e)}"
            )

    def _restore_last_tab(self):
        """Restore last active tab from settings."""
        settings = QSettings("BTC_Engine", "LogViewer")
        last_tab = settings.value("lastTab", 0, type=int)
        if 0 <= last_tab < self.tabs.count():
            self.tabs.setCurrentIndex(last_tab)

    def _restore_geometry(self):
        """Deprecated: geometry is now restored via WindowGeometryMixin in showEvent."""
        self._restore_last_tab()

    def showEvent(self, event):
        """Called when window is shown."""
        super().showEvent(event)
        self._restore_window_geometry(event)
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))

    def closeEvent(self, event):
        """Save geometry and last tab on close."""
        self._save_window_geometry()
        settings = QSettings("BTC_Engine", "LogViewer")
        settings.setValue("lastTab", self.tabs.currentIndex())
        super().closeEvent(event)


# Late import to avoid circular dependency in the class definition
from .styles import apply_hand_cursor_to_buttons
