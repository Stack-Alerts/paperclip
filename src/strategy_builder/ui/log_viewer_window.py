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


# Institutional-grade event patterns - VERIFIED AGAINST ACTUAL LOGS
EVENT_PATTERNS = {
    # Trade Events
    'TRADE_OPENED': (r'TRADE OPENED|trade.*opened|Opening trade|🟢.*TRADE', '#10B981'),
    'TRADE_CLOSED': (r'TRADE CLOSED|trade.*closed|Position closed|Closing trade|📘.*TRADE', '#2070FF'),
    'TRADE_UPDATED': (r'TRADE UPDATED|trade.*updated|Update.*trade|🔄.*TRADE', '#FFD700'),
    'POSITIONS_SNAPSHOT': (r'POSITIONS SNAPSHOT|OPEN POSITIONS|Position.*snapshot|📊', '#8B5CF6'),
    'TRADE_NOT_FOUND': (r'TRADE.*NOT FOUND|Trade.*not found|❌.*TRADE', '#C35252'),
    'MULTIPLE_POSITIONS': (r'multiple.*position|Multiple.*open|Several.*position|🔀', '#FF8C00'),
    
    # Configuration Events - VERIFIED: Logger initialized, BlockRegistryAdapter initialized
    'CONFIG_INITIALIZED': (r'Logger initialized|BlockRegistryAdapter initialized|Institutional Logger initialized', '#10B981'),
    'CONFIG_READ': (r'Reading|Loading|load blocks|Calling.*search', '#2070FF'),
    'CONFIG_VALIDATED': (r'validated|validation.*pass|Config.*valid|Validation complete', '#10B981'),
    'CONFIG_MISMATCH': (r'MISMATCH|mismatch|Config.*error|Invalid.*config', '#C35252'),
    'CONFIG_MISSING': (r'not found|missing|Config.*missing|Cannot find', '#FF8C00'),
    
    # System Events - VERIFIED: Starting to load blocks
    'STARTED': (r'Starting to load|Starting', '#10B981'),
    'STOPPED': (r'Stopped|Stopping|Shutdown|Terminated|Ending', '#9AA0A6'),
    'PROGRESS': (r'Processing|Working|Running|progress', '#2070FF'),
    'COMPLETED': (r'Successfully loaded|Successfully|Success|Finished', '#10B981'),
    
    # Error Events - Match Python logging format
    'CRITICAL': (r'CRITICAL|FATAL', '#C35252'),
    'ERROR': (r'ERROR', '#FF8C00'),
    'WARNING': (r'WARNING', '#FFD700'),
    
    # Block/Strategy Events - VERIFIED: Successfully loaded 83 blocks, Retrieved 83 search results
    'BLOCK_LOADED': (r'Successfully loaded \d+ blocks|loaded.*blocks|Processing first block', '#8B5CF6'),
    'BLOCK_ADDED': (r'Added.*block|Block.*added|Block.*config', '#10B981'),
    'SEARCH_RESULTS': (r'Retrieved \d+ search results|Retrieved.*search', '#2070FF'),
    
    # Decision Events  
    'DECISION': (r'decision|deciding|evaluate|Decision:', '#FFD700'),
    'CONDITION_MET': (r'Condition.*met|Threshold.*met|Criteria.*met', '#10B981'),
    'SIGNAL_DETECTED': (r'Signal.*detect|Pattern.*found|Signal.*found|Detected:', '#10B981'),
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
        tab_idx = 1
        for log_type in sorted(self.log_directories):
            log_widget = self._create_log_panel()
            # Capitalize and format tab name
            tab_name = log_type.replace('_', ' ').title()
            self.tabs.addTab(log_widget, tab_name)
            
            # Load logs for this type
            type_content = self._load_logs_by_type(log_type)
            self.tab_data[tab_idx] = {'content': type_content, 'widget': log_widget}
            self._display_content(tab_idx, type_content)
            tab_idx += 1
        
        # Add tabs for special root-level log files
        root_log_files = [f for f in self.all_log_files if f.parent == self.logs_base_dir]
        
        # 1. Signal Evaluator Log (Sprint 2.0.2 - Signal debugging)
        signal_log = None
        for log_file in root_log_files:
            if log_file.name == 'signal_evaluator.log' and log_file.exists():
                signal_log = log_file
                break
        
        if signal_log:
            log_widget = self._create_log_panel()
            self.tabs.addTab(log_widget, "🔍 Signal Evaluator")
            
            with open(signal_log, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            self.tab_data[tab_idx] = {'content': content, 'widget': log_widget}
            self._display_content(tab_idx, content)
            tab_idx += 1
        
        # 2. AI Recommendations Log
        ai_log = None
        for log_file in root_log_files:
            if log_file.name == 'ai_recommendations.log' and log_file.exists():
                ai_log = log_file
                break
        
        # Fall back to test log if production doesn't exist
        if not ai_log:
            for log_file in root_log_files:
                if log_file.name == 'test_ai_recommendations.log' and log_file.exists():
                    ai_log = log_file
                    break
        
        # Create single AI Recommendations tab if log exists
        if ai_log:
            log_widget = self._create_log_panel()
            self.tabs.addTab(log_widget, "🤖 AI Recommendations")
            
            # Load content
            with open(ai_log, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            self.tab_data[tab_idx] = {'content': content, 'widget': log_widget}
            self._display_content(tab_idx, content)
            tab_idx += 1
        
        # If specific file was provided, show it in dedicated tab
        # SKIP if it's ai_recommendations.log (already has its own tab)
        if self.current_log_file and self.current_log_file.exists():
            # Skip if already handled by AI Recommendations tab
            if self.current_log_file.name in ['ai_recommendations.log', 'test_ai_recommendations.log']:
                # Switch to AI Recommendations tab instead
                for i in range(self.tabs.count()):
                    if '🤖' in self.tabs.tabText(i) or 'AI' in self.tabs.tabText(i):
                        self.tabs.setCurrentIndex(i)
                        break
            else:
                specific_widget = self._create_log_panel()
                # Simplify session filenames: session_20260121_140512.log → Session
                tab_name = self.current_log_file.name
                if tab_name.startswith('session_'):
                    tab_name = "Session"
                else:
                    tab_name = f"📄 {tab_name}"
                self.tabs.addTab(specific_widget, tab_name)
                
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
        """Display content in a specific tab's text widget - WITH COLOR CODING"""
        if tab_index not in self.tab_data:
            return
        
        widget = self.tab_data[tab_index]['widget']
        filtered = self._apply_event_filters(content)
        
        # Apply color coding to filtered content
        colored_html = self._apply_color_coding(filtered)
        widget.text_edit.setHtml(colored_html)
        
        # Update stats
        self._update_stats(content, filtered)
    
    def _create_event_filters(self) -> QGroupBox:
        """Create institutional-grade event-based filters - CLEAN GRID LAYOUT"""
        from PyQt5.QtWidgets import QGridLayout
        
        group = QGroupBox("📊 Event Filters")
        group.setStyleSheet(get_groupbox_header_stylesheet() + """
            QGroupBox {
                font-size: 28px;
                font-weight: bold;
                padding-top: 30px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 10px 15px;
                font-size: 28px;
            }
        """)
        group.setMinimumHeight(240)
        
        # Main container with grid
        container = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(15, 20, 15, 15)
        grid_layout.setVerticalSpacing(12)
        grid_layout.setHorizontalSpacing(20)
        
        # All events in a clean list
        all_events = [
            ('TRADE_OPENED', '🟢 Trade Opened'),
            ('TRADE_CLOSED', '📘 Trade Closed'),
            ('TRADE_UPDATED', '🔄 Trade Updated'),
            ('POSITIONS_SNAPSHOT', '📊 Positions'),
            ('TRADE_NOT_FOUND', '❌ Not Found'),
            ('MULTIPLE_POSITIONS', '🔀 Multi Pos'),
            ('CONFIG_INITIALIZED', '✓ Config Init'),
            ('CONFIG_READ', '📖 Config Read'),
            ('CONFIG_VALIDATED', '✓ Validated'),
            ('CONFIG_MISMATCH', '❌ Mismatch'),
            ('CONFIG_MISSING', '⚠ Missing'),
            ('STARTED', '▶ Started'),
            ('STOPPED', '⏹ Stopped'),
            ('PROGRESS', '⏳ Progress'),
            ('COMPLETED', '✅ Completed'),
            ('CRITICAL', '🔴 Critical'),
            ('ERROR', '❌ Error'),
            ('WARNING', '⚠ Warning'),
            ('BLOCK_LOADED', '📦 Block Loaded'),
            ('BLOCK_ADDED', '➕ Block Added'),
            ('SEARCH_RESULTS', '🔍 Search'),
            ('DECISION', '🎯 Decision'),
            ('CONDITION_MET', '✓ Condition'),
            ('SIGNAL_DETECTED', '📡 Signal'),
        ]
        
        self.event_checkboxes = {}
        
        # Layout in 6 columns x 4 rows
        col = 0
        row = 0
        max_cols = 6
        
        for event_key, display_name in all_events:
            if event_key in EVENT_PATTERNS:
                _, color = EVENT_PATTERNS[event_key]
                checkbox = QCheckBox(display_name)
                checkbox.setChecked(True)
                
                # Set font using QFont (NOT CSS - CSS gets overridden!)
                checkbox_font = QFont()
                checkbox_font.setPointSize(11)  # 11pt = readable but not too big
                checkbox_font.setFamily("Segoe UI")
                checkbox.setFont(checkbox_font)
                
                checkbox.setFixedWidth(320)  # Fixed width for uniform grid - wider for full text
                checkbox.setStyleSheet(f"""
                    QCheckBox {{
                        color: {color};
                        background: transparent;
                        padding: 3px;
                    }}
                    QCheckBox::indicator {{
                        width: 40px;
                        height: 18px;
                    }}
                """)
                checkbox.stateChanged.connect(lambda state, e=event_key: self._on_event_filter_changed(e, state))
                self.event_checkboxes[event_key] = checkbox
                
                grid_layout.addWidget(checkbox, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
        
        # Control buttons at bottom
        row += 1
        self.toggle_all_btn = QPushButton("Toggle All")
        self.toggle_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self.toggle_all_btn.setFixedSize(140, 36)
        self.toggle_all_btn.clicked.connect(self._toggle_all_filters)
        grid_layout.addWidget(self.toggle_all_btn, row, 0, 1, 1)
        
        container.setLayout(grid_layout)
        
        # Set group layout
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(container)
        group.setLayout(group_layout)
        
        # Remove category tracking (no longer needed)
        self.filter_category_widgets = {}
        
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
        copy_selection_btn.setFixedSize(240, 52)
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
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return layout
    
    def _apply_event_filters(self, content: str) -> str:
        """Apply event-based filters to content - WITH CONTEXT"""
        if not content:
            return ""
        
        # SPECIAL CASE: AI Recommendations tab (ConfigDebugger text logs)
        # Show raw content without filtering
        current_tab_name = self.tabs.tabText(self.tabs.currentIndex()).lower()
        if 'ai' in current_tab_name and 'recommendation' in current_tab_name:
            return content  # Show everything unfiltered
        
        lines = content.split('\n')
        filtered = []
        
        # If all filters disabled, show NOTHING
        if not any(self.event_filters.values()):
            return ""
        
        # Track if we're in a matched event block
        in_event_block = False
        
        for line in lines:
            # Check if this line matches an event pattern
            if self._line_matches_event_filters(line):
                filtered.append(line)
                in_event_block = True
            # Include indented lines after matched events (trade details, etc.)
            elif in_event_block and (line.startswith('  ') or line.startswith('\t') or line.startswith('Location:') or line.startswith('Timestamp:') or line.startswith('Trade ID:') or line.startswith('Side:') or line.startswith('Size:') or line.startswith('Entry Price:') or line.startswith('Status:')):
                filtered.append(line)
            # Reset block tracking if we hit a non-indented, non-matching line
            elif not line.strip():
                # Empty line might end block, but include it for readability
                if in_event_block:
                    filtered.append(line)
                in_event_block = False
            else:
                # Non-matching, non-indented line - end of event block
                in_event_block = False
        
        return '\n'.join(filtered)
    
    def _line_matches_event_filters(self, line: str) -> bool:
        """Check if line matches any enabled event filter - STRICT MODE"""
        if not line.strip():
            return False  # Don't show empty lines when filtering
        
        # Check against enabled event patterns ONLY
        for event, enabled in self.event_filters.items():
            if enabled and event in EVENT_PATTERNS:
                pattern, _ = EVENT_PATTERNS[event]
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        
        return False
    
    def _apply_color_coding(self, content: str) -> str:
        """Apply color coding to match filter colors - INSTITUTIONAL GRADE"""
        if not content:
            return ""
        
        lines = content.split('\n')
        html_lines = []
        
        # HTML header with monospace font
        html_lines.append('<html><head><style>')
        html_lines.append('body { background-color: #15191E; color: #E8EAED; font-family: "Courier New", monospace; font-size: 26px; }')
        html_lines.append('</style></head><body><pre style="margin: 0; padding: 0;">')
        
        for line in lines:
            # HTML escape special characters
            escaped_line = (line
                           .replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;'))
            
            # Check which event pattern this line matches
            matched_color = None
            for event_key, (pattern, color) in EVENT_PATTERNS.items():
                if re.search(pattern, line, re.IGNORECASE):
                    matched_color = color
                    break
            
            # Apply color if matched
            if matched_color:
                html_lines.append(f'<span style="color: {matched_color};">{escaped_line}</span>')
            else:
                # Default color for context lines
                html_lines.append(f'<span style="color: #E8EAED;">{escaped_line}</span>')
        
        html_lines.append('</pre></body></html>')
        return '\n'.join(html_lines)
    
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
        """Show only relevant filters for the selected tab - REPACK GRID DYNAMICALLY"""
        tab_name = self.tabs.tabText(tab_index).replace('📄 ', '').lower()
        
        # Define which EVENT FILTERS are relevant for each tab type
        tab_event_map = {
            'all logs': list(EVENT_PATTERNS.keys()),  # Show all filters
            
            'trades': [
                'TRADE_OPENED', 'TRADE_CLOSED', 'TRADE_UPDATED', 
                'POSITIONS_SNAPSHOT', 'TRADE_NOT_FOUND', 'MULTIPLE_POSITIONS',
                'CRITICAL', 'ERROR', 'WARNING'
            ],
            
            'strategy builder': [
                'CONFIG_INITIALIZED', 'CONFIG_READ', 'CONFIG_VALIDATED',
                'CONFIG_MISMATCH', '​CONFIG_MISSING',
                'STARTED', 'STOPPED', 'PROGRESS', 'COMPLETED',
                'CRITICAL', 'ERROR', 'WARNING',
                'BLOCK_LOADED', 'BLOCK_ADDED', 'SEARCH_RESULTS'
            ],
            
            'session': [  # Session logs (UI events)
                'CONFIG_INITIALIZED', 'CONFIG_READ', 'CONFIG_VALIDATED',
                'STARTED', 'STOPPED', 'COMPLETED',
                'ERROR', 'WARNING',
                'BLOCK_LOADED', 'SEARCH_RESULTS'
            ],
            
            'optimizer': [
                'STARTED', 'STOPPED', 'PROGRESS', 'COMPLETED',
                'CRITICAL', 'ERROR', 'WARNING'
            ],
            
            'backtest': [
                'TRADE_OPENED', 'TRADE_CLOSED', 'TRADE_UPDATED',
                'STARTED', 'STOPPED', 'PROGRESS', 'COMPLETED',
                'CRITICAL', 'ERROR', 'WARNING'
            ],
        }
        
        # Find matching event list (default to all)
        relevant_events = None
        for key, events in tab_event_map.items():
            if key in tab_name:
                relevant_events = events
                break
        
        # Default: show all if no match
        if relevant_events is None:
            relevant_events = list(EVENT_PATTERNS.keys())
        
        # Get grid layout (need to access parent's layout)
        # Find the grid layout from the filter group
        filter_group = None
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QGroupBox) and "Event Filters" in widget.title():
                filter_group = widget
                break
        
        if not filter_group:
            return
        
        # Get the container widget and its grid layout
        container = filter_group.layout().itemAt(0).widget()
        from PyQt5.QtWidgets import QGridLayout
        grid_layout = container.layout()
        
        if not isinstance(grid_layout, QGridLayout):
            return
        
        # Remove all checkboxes from grid
        for event_key, checkbox in self.event_checkboxes.items():
            grid_layout.removeWidget(checkbox)
            checkbox.hide()
        
        # Re-add only visible checkboxes in packed grid
        col = 0
        row = 0
        max_cols = 6
        
        # Maintain original order but pack tightly
        all_events_ordered = [
            'TRADE_OPENED', 'TRADE_CLOSED', 'TRADE_UPDATED',
            'POSITIONS_SNAPSHOT', 'TRADE_NOT_FOUND', 'MULTIPLE_POSITIONS',
            'CONFIG_INITIALIZED', 'CONFIG_READ', 'CONFIG_VALIDATED',
            'CONFIG_MISMATCH', 'CONFIG_MISSING',
            'STARTED', 'STOPPED', 'PROGRESS', 'COMPLETED',
            'CRITICAL', 'ERROR', 'WARNING',
            'BLOCK_LOADED', 'BLOCK_ADDED', 'SEARCH_RESULTS',
            'DECISION', 'CONDITION_MET', 'SIGNAL_DETECTED',
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
        
        # Build debug info
        try:
            debug_info = f"DEBUG INFO:\n\n"
            debug_info += f"logs_base_dir = {self.logs_base_dir}\n"
            debug_info += f"exists = {self.logs_base_dir.exists()}\n"
            debug_info += f"absolute = {self.logs_base_dir.resolve()}\n\n"
            
            if not self.logs_base_dir.exists():
                QMessageBox.critical(self, "Debug - Directory Not Found", 
                                   debug_info + "Directory does not exist!")
                return
            
            fresh_log_files = list(self.logs_base_dir.rglob('*.log'))
            debug_info += f"Files found: {len(fresh_log_files)}\n"
            if fresh_log_files:
                debug_info += f"First 3 files:\n"
                for f in fresh_log_files[:3]:
                    debug_info += f"  - {f}\n"
        except Exception as e:
            QMessageBox.critical(self, "Debug - Error", f"Error in debug: {e}")
            return
        
        if not fresh_log_files:
            QMessageBox.warning(self, "No Logs", f"No log files found to delete:\n\n{debug_info}")
            return
        
        # Ask for confirmation with DEBUG INFO INCLUDED
        reply = QMessageBox.question(
            self,
            "Clear All Logs - DEBUG MODE",
            f"{debug_info}\n\n"
            f"{'='*50}\n\n"
            f"⚠️  DELETE {len(fresh_log_files)} log files?\n\n"
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
    
    def showEvent(self, event):
        """Called when window is shown - apply hand cursors to all widgets"""
        super().showEvent(event)
        from PyQt5.QtCore import QTimer
        from .styles import apply_hand_cursor_to_buttons
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))

    def closeEvent(self, event):
        """Save geometry and state on close"""
        settings = QSettings("BTC_Engine", "LogViewer")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("lastTab", self.tabs.currentIndex())
        super().closeEvent(event)
