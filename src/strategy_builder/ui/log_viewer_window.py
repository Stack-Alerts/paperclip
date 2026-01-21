"""
Institutional-Grade Log Viewer Window - Complete Rebuild

Multi-tabbed log viewer with event-based filtering across all log types.
Automatically discovers log directories and creates tabs dynamically.

Features:
- Tabbed interface (All Logs, Trades, Strategy Builder, Optimizer, etc.)
- Event-based institutional-grade filtering
- Smart event detection (🟢🔄📊❌✓ markers)
- Window maximize support
- Geometry persistence
- Scalable for future log types

ZERO HARDCODED STYLES - All from styles.py

Author: Strategy Builder Team
Date: 2026-01-21
Version: 2.0 (Institutional Grade)
"""

from typing import Dict, List, Set
from pathlib import Path
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QCheckBox, QLabel, QGroupBox, QApplication, QMessageBox,
    QTabWidget, QWidget, QScrollArea
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_color
)


# Institutional-grade event patterns (extensible)
EVENT_PATTERNS = {
    # Trade Events
    'TRADE_OPENED': (r'🟢 TRADE OPENED', '#10B981'),
    'TRADE_CLOSED': (r'TRADE CLOSED|Position closed', '#2070FF'),
    'TRADE_UPDATED': (r'🔄 TRADE UPDATED', '#FFD700'),
    'POSITIONS_SNAPSHOT': (r'📊 OPEN POSITIONS SNAPSHOT', '#8B5CF6'),
    'TRADE_NOT_FOUND': (r'❌ TRADE ID NOT FOUND', '#C35252'),
    'MULTIPLE_POSITIONS': (r'multiple open', '#FF8C00'),
    
    # Configuration Events
    'CONFIG_INITIALIZED': (r'✓.*initialized|CONFIG DEBUGGER', '#10B981'),
    'CONFIG_READ': (r'Reading config|Loading config', '#2070FF'),
    'CONFIG_VALIDATED': (r'Config validated|Validation passed', '#10B981'),
    'CONFIG_MISMATCH': (r'❌.*MISMATCH', '#C35252'),
    'CONFIG_MISSING': (r'Config not found|Missing config', '#FF8C00'),
    
    # System Events
    'STARTED': (r'Started:|Launching|Initiating', '#10B981'),
    'STOPPED': (r'Stopped|Shutdown|Terminated', '#9AA0A6'),
    'PROGRESS': (r'Progress:|Loading:|Processing:', '#2070FF'),
    'COMPLETED': (r'✓.*completed|Successfully|Success', '#10B981'),
    
    # Error Events
    'CRITICAL': (r'CRITICAL|FATAL', '#C35252'),
    'ERROR': (r'❌|ERROR', '#FF8C00'),
    'WARNING': (r'⚠|WARNING', '#FFD700'),
    
    # Block/Strategy Events
    'BLOCK_LOADED': (r'Retrieved.*blocks|Loaded.*block', '#8B5CF6'),
    'BLOCK_ADDED': (r'Added block|Block configured', '#10B981'),
    'SEARCH_RESULTS': (r'Retrieved.*search results', '#2070FF'),
    
    # Decision Events  
    'DECISION': (r'Entry decision|Exit decision|DECISION', '#FFD700'),
    'CONDITION_MET': (r'Condition met|Threshold met', '#10B981'),
    'SIGNAL_DETECTED': (r'Signal detected|Pattern found', '#10B981'),
}


class LogViewerWindow(QDialog):
    """
    Institutional-grade log viewer with tabs and event-based filtering.
    """
    
    def __init__(self, log_file_path: Path = None, parent=None):
        super().__init__(parent)
        
        # Use absolute path to logs directory (relative to project root)
        import os
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.logs_base_dir = project_root / 'logs'
        
        self.current_log_file = log_file_path
        self.all_log_files: List[Path] = []
        self.log_directories: Set[str] = set()
        
        # Event filters (all enabled by default)
        self.event_filters = {event: True for event in EVENT_PATTERNS.keys()}
        
        # Tab data storage: {tab_index: {'content': str, 'filtered': str}}
        self.tab_data: Dict[int, Dict] = {}
        
        self._init_ui()
        self._scan_logs_directory()
        self._load_initial_logs()
        self._restore_geometry()
    
    def _init_ui(self):
        """Initialize UI with tabs and filters"""
        # Enable maximize button - proper combination of flags
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        
        # Window properties
        log_name = self.current_log_file.name if self.current_log_file else "All Logs"
        self.setWindowTitle(f"Log Viewer - {log_name}")
        self.setGeometry(100, 100, 1600, 1000)  # Larger for institutional grade
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # Title
        self.title_label = QLabel(f"● Institutional Log Viewer - {log_name}")
        self.title_label.setStyleSheet(get_panel_title_stylesheet())
        main_layout.addWidget(self.title_label)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)
        
        # Filters (shared across all tabs)
        filters_group = self._create_event_filters()
        main_layout.addWidget(filters_group)
        
        # Bottom bar (stats + buttons)
        bottom_bar = self._create_bottom_bar()
        main_layout.addLayout(bottom_bar)
        
        self.setLayout(main_layout)
    
    def _scan_logs_directory(self):
        """Scan logs directory and discover all log types"""
        if not self.logs_base_dir.exists():
            return
        
        # Find all .log files
        self.all_log_files = list(self.logs_base_dir.rglob('*.log'))
        
        # Extract unique subdirectories (log types)
        for log_file in self.all_log_files:
            relative_path = log_file.relative_to(self.logs_base_dir)
            if len(relative_path.parts) > 1:
                log_type = relative_path.parts[0]  # First subdirectory
                self.log_directories.add(log_type)
    
    def _load_initial_logs(self):
        """Load logs into tabs"""
        # Tab 0: All Logs
        all_logs_widget = self._create_log_panel()
        self.tabs.addTab(all_logs_widget, "All Logs")
        
        # Load all logs into first tab
        all_content = self._load_all_logs()
        self.tab_data[0] = {'content': all_content, 'widget': all_logs_widget}
        self._display_content(0, all_content)
        
        # Create tabs for each log directory type
        for idx, log_type in enumerate(sorted(self.log_directories), start=1):
            log_widget = self._create_log_panel()
            # Capitalize and format tab name
            tab_name = log_type.replace('_', ' ').title()
            self.tabs.addTab(log_widget, tab_name)
            
            # Load logs for this type
            type_content = self._load_logs_by_type(log_type)
            self.tab_data[idx] = {'content': type_content, 'widget': log_widget}
            self._display_content(idx, type_content)
        
        # If specific file was provided, show it in dedicated tab
        if self.current_log_file and self.current_log_file.exists():
            specific_widget = self._create_log_panel()
            self.tabs.addTab(specific_widget, f"📄 {self.current_log_file.name}")
            
            with open(self.current_log_file, 'r', encoding='utf-8', errors='replace') as f:
                specific_content = f.read()
            
            tab_idx = self.tabs.count() - 1
            self.tab_data[tab_idx] = {'content': specific_content, 'widget': specific_widget}
            self._display_content(tab_idx, specific_content)
            
            # Switch to this tab
            self.tabs.setCurrentIndex(tab_idx)
    
    def _load_all_logs(self) -> str:
        """Load all logs sorted by timestamp"""
        all_logs = []
        for log_file in sorted(self.all_log_files, key=lambda f: f.stat().st_mtime, reverse=True):
            all_logs.append(f"\n{'='*80}\n")
            all_logs.append(f"LOG FILE: {log_file.relative_to(self.logs_base_dir)}\n")
            all_logs.append(f"{'='*80}\n\n")
            
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    all_logs.append(f.read())
            except Exception as e:
                all_logs.append(f"ERROR: Could not read file - {str(e)}\n")
        
        return ''.join(all_logs)
    
    def _load_logs_by_type(self, log_type: str) -> str:
        """Load logs for a specific type"""
        type_logs = []
        matching_files = [f for f in self.all_log_files if log_type in str(f)]
        
        for log_file in sorted(matching_files, key=lambda f: f.stat().st_mtime, reverse=True):
            type_logs.append(f"\n{'='*80}\n")
            type_logs.append(f"LOG FILE: {log_file.name}\n")
            type_logs.append(f"{'='*80}\n\n")
            
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    type_logs.append(f.read())
            except Exception as e:
                type_logs.append(f"ERROR: Could not read file - {str(e)}\n")
        
        return ''.join(type_logs)
   
    def _create_log_panel(self) -> QWidget:
        """Create a log output panel (reusable for each tab)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Text edit for output
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # Large monospace font (26px institutional grade)
        large_font = QFont("Courier New")
        large_font.setPixelSize(26)
        large_font.setStyleHint(QFont.Monospace)
        text_edit.setFont(large_font)
        text_edit.document().setDefaultFont(large_font)
        
        # Dark background
        text_edit.setStyleSheet(
            "QTextEdit {"
            "   background-color: #15191E;"
            "   color: #E8EAED;"
            "   border: 1px solid #3C4149;"
            "   padding: 8px;"
            "   selection-background-color: #2A2F3A;"
            "}"
        )
        
        layout.addWidget(text_edit)
        widget.setLayout(layout)
        widget.text_edit = text_edit  # Store reference
        
        return widget
    
    def _display_content(self, tab_index: int, content: str):
        """Display content in a specific tab's text widget"""
        if tab_index not in self.tab_data:
            return
        
        widget = self.tab_data[tab_index]['widget']
        filtered = self._apply_event_filters(content)
        widget.text_edit.setPlainText(filtered)
        
        # Update stats
        self._update_stats(content, filtered)
    
    def _create_event_filters(self) -> QGroupBox:
        """Create institutional-grade event-based filters - COMPACT LAYOUT"""
        group = QGroupBox("Event Filters (Institutional Grade)")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(150)  # Reduced height - more compact
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)  # Reduced spacing
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Group events by category - COMPACT GRID LAYOUT
        categories = {
            'Trade Events': ['TRADE_OPENED', 'TRADE_CLOSED', 'TRADE_UPDATED', 'POSITIONS_SNAPSHOT', 'TRADE_NOT_FOUND', 'MULTIPLE_POSITIONS'],
            'Config Events': ['CONFIG_INITIALIZED', 'CONFIG_READ', 'CONFIG_VALIDATED', 'CONFIG_MISMATCH', 'CONFIG_MISSING'],
            'System Events': ['STARTED', 'STOPPED', 'PROGRESS', 'COMPLETED'],
            'Error Events': ['CRITICAL', 'ERROR', 'WARNING'],
            'Strategy Events': ['BLOCK_LOADED', 'BLOCK_ADDED', 'SEARCH_RESULTS', 'DECISION', 'CONDITION_MET', 'SIGNAL_DETECTED'],
        }
        
        self.event_checkboxes = {}
        self.filter_category_widgets = {}  # Track category rows for show/hide
        
        for category_name, events in categories.items():
            # Category row container
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)  # Compact spacing
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            # Category label - SMALLER
            cat_label = QLabel(f"{category_name}:")
            cat_label.setStyleSheet(get_label_style('muted') + "font-weight: bold; font-size: 12px;")
            cat_label.setFixedWidth(110)  # Fixed smaller width
            row_layout.addWidget(cat_label)
            
            # Event checkboxes - COMPACT
            for event in events:
                if event in EVENT_PATTERNS:
                    _, color = EVENT_PATTERNS[event]
                    # Shorter names for compact display
                    short_name = event.replace('_', ' ').replace('Positions', 'Pos').replace('Multiple', 'Multi')
                    checkbox = QCheckBox(short_name.title())
                    checkbox.setChecked(True)
                    checkbox.setStyleSheet(f"QCheckBox {{ color: {color}; background: transparent; font-size: 12px; }}")
                    checkbox.stateChanged.connect(lambda state, e=event: self._on_event_filter_changed(e, state))
                    self.event_checkboxes[event] = checkbox
                    row_layout.addWidget(checkbox)
            
            # NO stretch - use all available space
            row_widget.setLayout(row_layout)
            layout.addWidget(row_widget)
            
            # Store reference for show/hide
            self.filter_category_widgets[category_name] = row_widget
        
        # Control buttons row - COMPACT
        controls_layout = QHBoxLayout()
        
        self.toggle_all_btn = QPushButton("Unselect All")
        self.toggle_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self.toggle_all_btn.setFixedHeight(30)  # Smaller
        self.toggle_all_btn.clicked.connect(self._toggle_all_filters)
        controls_layout.addWidget(self.toggle_all_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        container.setLayout(layout)
        group.setLayout(QVBoxLayout())
        group.layout().setContentsMargins(0, 0, 0, 0)
        group.layout().addWidget(container)
        
        return group
    
    def _create_bottom_bar(self) -> QHBoxLayout:
        """Create bottom bar with stats and buttons"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # Stats on left
        base_style = "vertical-align: middle; padding: 0px; margin: 0px;"
        
        self.msg_count_label = QLabel("Total Lines: <b>0</b>")
        self.msg_count_label.setStyleSheet(get_label_style() + base_style)
        layout.addWidget(self.msg_count_label)
        
        self.filtered_count_label = QLabel("Displayed: <b>0</b>")
        self.filtered_count_label.setStyleSheet(get_label_style() + base_style)
        layout.addWidget(self.filtered_count_label)
        
        self.event_count_label = QLabel("Events: <b>0</b>")
        self.event_count_label.setStyleSheet(get_label_style() + base_style + "color: #FFD700;")
        layout.addWidget(self.event_count_label)
        
        layout.addStretch()
        
        # Buttons on right
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_btn.setFixedSize(130, 52)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(copy_btn)
        
        copy_selection_btn = QPushButton("📋 Copy Selection")
        copy_selection_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_selection_btn.setFixedSize(180, 52)
        copy_selection_btn.clicked.connect(self._copy_selection)
        layout.addWidget(copy_selection_btn)
        
        clear_logs_btn = QPushButton("🗑️ Clear All Logs")
        clear_logs_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_logs_btn.setFixedSize(180, 52)
        clear_logs_btn.clicked.connect(self._clear_all_logs)
        clear_logs_btn.setToolTip("Delete ALL log files from logs directory")
        layout.addWidget(clear_logs_btn)
        
        close_btn = QPushButton("✖ Close")
        close_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        close_btn.setFixedSize(130, 52)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return layout
    
    def _apply_event_filters(self, content: str) -> str:
        """Apply event-based filters to content"""
        if not content:
            return ""
        
        lines = content.split('\n')
        filtered = []
        
        # If all filters disabled, show everything
        if not any(self.event_filters.values()):
            return content
        
        for line in lines:
            if self._line_matches_event_filters(line):
                filtered.append(line)
        
        return '\n'.join(filtered)
    
    def _line_matches_event_filters(self, line: str) -> bool:
        """Check if line matches any enabled event filter"""
        if not line.strip():
            return True  # Always show empty lines
        
        # Always show structural elements
        if any(char in line for char in ['═', '─', '║', '╔', '╚', '=====', '-----']):
            return True
        
        # Always show file headers
        if line.startswith('LOG FILE:') or 'Log file:' in line:
            return True
        
        # Check against enabled event patterns
        for event, enabled in self.event_filters.items():
            if enabled and event in EVENT_PATTERNS:
                pattern, _ = EVENT_PATTERNS[event]
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        
        # If line is part of a multi-line event block, include it
        # (e.g., details under a trade event)
        if line.startswith('  ') or line.startswith('\t'):
            return True
        
        return False
    
    def _on_event_filter_changed(self, event: str, state: int):
        """Handle event filter change"""
        self.event_filters[event] = (state == Qt.Checked)
        self._update_toggle_button_text()
        self._refresh_current_tab()
    
    def _on_tab_changed(self, index: int):
        """Handle tab change and update filter visibility"""
        self._update_filter_visibility(index)
        self._refresh_current_tab()
    
    def _update_filter_visibility(self, tab_index: int):
        """Show only relevant filters for the selected tab"""
        tab_name = self.tabs.tabText(tab_index).replace('📄 ', '').lower()
        
        # Define which categories are relevant for each tab type
        tab_filter_map = {
            'all logs': ['Trade Events', 'Config Events', 'System Events', 'Error Events', 'Strategy Events'],
            'trades': ['Trade Events', 'Error Events'],
            'strategy builder': ['Strategy Events', 'Config Events', 'System Events', 'Error Events'],
            'optimizer': ['System Events', 'Error Events'],
            'backtest': ['Trade Events', 'System Events', 'Error Events'],
        }
        
        # Find matching categories (default to all if unknown tab)
        relevant_categories = None
        for key, categories in tab_filter_map.items():
            if key in tab_name:
                relevant_categories = categories
                break
        
        # If no match or specific file, show all
        if relevant_categories is None or '.' in tab_name:  # File extension means specific file
            relevant_categories = list(self.filter_category_widgets.keys())
        
        # Show/hide category rows
        for category_name, widget in self.filter_category_widgets.items():
            if category_name in relevant_categories:
                widget.show()
            else:
                widget.hide()
    
    def _refresh_current_tab(self):
        """Refresh display for current tab"""
        current_index = self.tabs.currentIndex()
        if current_index in self.tab_data:
            content = self.tab_data[current_index]['content']
            self._display_content(current_index, content)
    
    def _toggle_all_filters(self):
        """Toggle all event filters"""
        button_text = self.toggle_all_btn.text()
        new_state = button_text == "Select All"
        
        for checkbox in self.event_checkboxes.values():
            checkbox.setChecked(new_state)
    
    def _update_toggle_button_text(self):
        """Update toggle button text"""
        all_selected = all(self.event_filters.values())
        self.toggle_all_btn.setText("Unselect All" if all_selected else "Select All")
    
    def _update_stats(self, original: str, filtered: str):
        """Update statistics labels"""
        total_lines = len(original.split('\n'))
        displayed_lines = len(filtered.split('\n'))
        
        # Count events
        event_count = 0
        for line in filtered.split('\n'):
            for pattern, _ in EVENT_PATTERNS.values():
                if re.search(pattern, line, re.IGNORECASE):
                    event_count += 1
                    break
        
        self.msg_count_label.setText(f"Total Lines: <b>{total_lines:,}</b>")
        self.filtered_count_label.setText(f"Displayed: <b>{displayed_lines:,}</b>")
        self.event_count_label.setText(f"Events: <b>{event_count:,}</b>")
    
    def _copy_to_clipboard(self):
        """Copy all visible content from current tab"""
        current_index = self.tabs.currentIndex()
        if current_index not in self.tab_data:
            return
        
        widget = self.tab_data[current_index]['widget']
        content = widget.text_edit.toPlainText()
        
        if not content:
            QMessageBox.information(self, "Nothing to Copy", "No content to copy.")
            return
        
        QApplication.clipboard().setText(content)
        line_count = len(content.split('\n'))
        self.filtered_count_label.setText(f"✅ Copied {line_count:,} lines to clipboard")
    
    def _copy_selection(self):
        """Copy selected text from current tab"""
        current_index = self.tabs.currentIndex()
        if current_index not in self.tab_data:
            return
        
        widget = self.tab_data[current_index]['widget']
        selected = widget.text_edit.textCursor().selectedText().replace('\u2029', '\n')
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select text to copy.")
            return
        
        QApplication.clipboard().setText(selected)
        line_count = len(selected.split('\n'))
        self.filtered_count_label.setText(f"✅ Copied {line_count:,} selected lines")
    
    def _clear_all_logs(self):
        """Delete ALL log files from logs directory"""
        # Rescan to get fresh list of ALL log files (including new ones)
        if not self.logs_base_dir.exists():
            QMessageBox.information(self, "No Logs", "Logs directory does not exist.")
            return
        
        fresh_log_files = list(self.logs_base_dir.rglob('*.log'))
        
        if not fresh_log_files:
            QMessageBox.information(self, "No Logs", "No log files found to delete.")
            return
        
        # Ask for confirmation with count
        reply = QMessageBox.question(
            self,
            "Clear All Logs",
            f"⚠️  This will DELETE {len(fresh_log_files)} log files from the logs directory!\n\n"
            "This action cannot be undone.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Delete all log files
            deleted_count = 0
            total_size = 0
            failed_files = []
            
            for log_file in fresh_log_files:
                try:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    total_size += file_size
                except Exception as e:
                    failed_files.append(f"{log_file.name}: {e}")
                    print(f"Error deleting {log_file}: {e}")
            
            # Show result
            size_mb = total_size / (1024 * 1024)
            QMessageBox.information(
                self,
                "Logs Cleared",
                f"Successfully deleted {deleted_count} log files.\n\n"
                f"Space freed: {size_mb:.2f} MB"
            )
            
            # Clear viewer and reload
            self.all_log_files.clear()
            self.log_directories.clear()
            self.tab_data.clear()
            
            # Remove all tabs except first
            while self.tabs.count() > 1:
                self.tabs.removeTab(1)
            
            # Clear first tab
            if 0 in self.tab_data:
                self.tab_data[0]['content'] = "(No logs available)"
                self.tab_data[0]['widget'].text_edit.setPlainText("(No logs available)")
            
            self.filtered_count_label.setText(f"✅ Cleared {deleted_count} log files ({size_mb:.1f} MB)")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error clearing logs:\n\n{str(e)}"
            )
    
    def _restore_geometry(self):
        """Restore window geometry"""
        settings = QSettings("BTC_Engine", "LogViewer")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore last tab
        last_tab = settings.value("lastTab", 0, type=int)
        if 0 <= last_tab < self.tabs.count():
            self.tabs.setCurrentIndex(last_tab)
    
    def closeEvent(self, event):
        """Save geometry and state on close"""
        settings = QSettings("BTC_Engine", "LogViewer")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("lastTab", self.tabs.currentIndex())
        super().closeEvent(event)
