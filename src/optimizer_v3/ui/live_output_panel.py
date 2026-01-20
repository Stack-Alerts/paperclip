"""
Live Output Panel - Real-time Progress Tracking

Displays real-time output from optimizer with filtering capabilities:
- Message level filtering (Info/Decision/Action/Warning/Error)
- Category filtering (Signal/Trade/Risk/System/Optimizer)
- Color-coded output
- Auto-scrolling
- Export functionality

ZERO HARDCODED STYLES - All from styles.py

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.4)
"""

from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QColor
from datetime import datetime
from enum import Enum

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_checkbox_style,
    get_color,
    COLORS
)


class MessageLevel(Enum):
    """Message level enumeration"""
    INFO = "INFO"
    DECISION = "DECISION"
    ACTION = "ACTION"
    WARNING = "WARNING"
    ERROR = "ERROR"


class MessageCategory(Enum):
    """Message category enumeration"""
    SIGNAL = "SIGNAL"
    TRADE = "TRADE"
    RISK = "RISK"
    SYSTEM = "SYSTEM"
    OPTIMIZER = "OPTIMIZER"


class LiveOutputPanel(QWidget):
    """
    Live Output Panel for real-time progress tracking.
    
    Features:
    - Real-time message streaming
    - Multi-level filtering
    - Category filtering
    - Color-coded output
    - Auto-scrolling
    - Export capability
    - Resource monitoring
    """
    
    # Signals
    message_received = pyqtSignal(str, str, str)  # timestamp, level, message
    
    def __init__(self, parent=None, strategy_name: Optional[str] = None):
        super().__init__(parent)
        self.messages: List[Dict] = []
        self.filtered_messages: List[Dict] = []
        self.auto_scroll = True
        self.message_count = 0
        self.strategy_name = strategy_name  # Store strategy name
        self.is_running = False  # Track if test is running
        
        # Filter states
        self.level_filters = {
            MessageLevel.INFO: True,
            MessageLevel.DECISION: True,
            MessageLevel.ACTION: True,
            MessageLevel.WARNING: True,
            MessageLevel.ERROR: True
        }
        
        self.category_filters = {
            MessageCategory.SIGNAL: True,
            MessageCategory.TRADE: True,
            MessageCategory.RISK: True,
            MessageCategory.SYSTEM: True,
            MessageCategory.OPTIMIZER: True
        }
        
        self._init_ui()
        
        # Update timer for stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(1000)  # Update every second
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title - Dynamic with strategy name
        if self.strategy_name:
            title_text = f"🔴 Live Output - {self.strategy_name}"
        else:
            title_text = "🔴 Live Output"
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(self.title_label)
        
        # Control bar
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        # Filters
        filters_group = self._create_filters()
        layout.addWidget(filters_group)
        
        # Output display
        output_group = self._create_output_display()
        layout.addWidget(output_group)
        
        # Stats bar
        stats_bar = self._create_stats_bar()
        layout.addLayout(stats_bar)
        
        self.setLayout(layout)
    
    def _create_control_bar(self) -> QHBoxLayout:
        """Create control button bar"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        layout.addStretch()
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_btn.setFixedSize(130, 36)  # Fixed width AND height for exact consistency
        clear_btn.clicked.connect(self._clear_output)
        clear_btn.setToolTip("Clear all messages")
        layout.addWidget(clear_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.setFixedSize(130, 36)  # Fixed width AND height for exact consistency
        export_btn.clicked.connect(self._export_output)
        export_btn.setToolTip("Export output to file")
        layout.addWidget(export_btn)
        
        return layout
    
    def _create_filters(self) -> QGroupBox:
        """Create filter controls - INLINE with separator"""
        group = QGroupBox("Filters")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(80)
        
        # Single horizontal layout for all filters
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # Level filters
        level_label = QLabel("Levels:")
        level_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(level_label)
        
        self.level_checkboxes = {}
        for level in MessageLevel:
            checkbox = QCheckBox(level.value)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(get_checkbox_style())
            checkbox.stateChanged.connect(lambda state, l=level: self._toggle_level_filter(l, state))
            layout.addWidget(checkbox)
            self.level_checkboxes[level] = checkbox
        
        # Separator between Levels and Categories
        separator = QLabel("|")
        separator.setStyleSheet(f"color: {COLORS['border']}; font-size: 18px; padding: 0 10px;")
        layout.addWidget(separator)
        
        # Category filters
        category_label = QLabel("Categories:")
        category_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(category_label)
        
        self.category_checkboxes = {}
        for category in MessageCategory:
            checkbox = QCheckBox(category.value)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(get_checkbox_style())
            checkbox.stateChanged.connect(lambda state, c=category: self._toggle_category_filter(c, state))
            layout.addWidget(checkbox)
            self.category_checkboxes[category] = checkbox
        
        layout.addStretch()
        
        # Auto-scroll checkbox at the very right
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.setStyleSheet(get_checkbox_style())
        self.auto_scroll_check.stateChanged.connect(self._toggle_auto_scroll)
        layout.addWidget(self.auto_scroll_check)
        
        group.setLayout(layout)
        return group
    
    def _create_output_display(self) -> QGroupBox:
        """Create output text display"""
        group = QGroupBox("Output")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Text edit for output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(
            f"QTextEdit {{"
            f"background-color: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"padding: 8px; "
            f"font-family: 'Consolas', 'Monaco', monospace; "
            f"font-size: 12px; "
            f"}}"
        )
        
        layout.addWidget(self.output_text)
        group.setLayout(layout)
        return group
    
    def _create_stats_bar(self) -> QHBoxLayout:
        """Create statistics bar"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Message count
        self.msg_count_label = QLabel("Messages: <b>0</b>")
        self.msg_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.msg_count_label)
        
        # Filtered count
        self.filtered_count_label = QLabel("Displayed: <b>0</b>")
        self.filtered_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.filtered_count_label)
        
        # Error count
        self.error_count_label = QLabel("⛔ Errors: <b>0</b>")
        self.error_count_label.setStyleSheet(f"color: {COLORS['error']};")
        layout.addWidget(self.error_count_label)
        
        # Warning count
        self.warning_count_label = QLabel("⚠️ Warnings: <b>0</b>")
        self.warning_count_label.setStyleSheet(f"color: {COLORS['warning']};")
        layout.addWidget(self.warning_count_label)
        
        layout.addStretch()
        return layout
    
    def add_message(self, message: str, level: str = "INFO", category: str = "SYSTEM") -> None:
        """
        Add message to output.
        
        Args:
            message: Message text
            level: Message level (INFO/DECISION/ACTION/WARNING/ERROR)
            category: Message category (SIGNAL/TRADE/RISK/SYSTEM/OPTIMIZER)
        """
        try:
            msg_level = MessageLevel(level)
            msg_category = MessageCategory(category)
        except ValueError:
            msg_level = MessageLevel.INFO
            msg_category = MessageCategory.SYSTEM
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        msg_data = {
            'timestamp': timestamp,
            'level': msg_level,
            'category': msg_category,
            'message': message
        }
        
        self.messages.append(msg_data)
        self.message_count += 1
        
        # Apply filters and display
        if self._should_display_message(msg_data):
            self.filtered_messages.append(msg_data)
            self._append_colored_message(msg_data)
        
        # Emit signal
        self.message_received.emit(timestamp, level, message)
    
    def _should_display_message(self, msg_data: Dict) -> bool:
        """Check if message should be displayed based on filters"""
        level_match = self.level_filters.get(msg_data['level'], True)
        category_match = self.category_filters.get(msg_data['category'], True)
        return level_match and category_match
    
    def _append_colored_message(self, msg_data: Dict) -> None:
        """Append message with color coding"""
        # Get color based on level
        color_map = {
            MessageLevel.INFO: COLORS['info'],
            MessageLevel.DECISION: COLORS['success'],
            MessageLevel.ACTION: COLORS['primary'],
            MessageLevel.WARNING: COLORS['warning'],
            MessageLevel.ERROR: COLORS['error']
        }
        
        color = color_map.get(msg_data['level'], COLORS['text_primary'])
        
        # Format message
        timestamp = msg_data['timestamp']
        level = msg_data['level'].value
        category = msg_data['category'].value
        message = msg_data['message']
        
        # Build HTML
        html = (
            f"<span style='color: {COLORS['text_muted']};'>{timestamp}</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{level}]</span> "
            f"<span style='color: {COLORS['secondary']};'>[{category}]</span> "
            f"<span style='color: {COLORS['text_primary']};'>{message}</span>"
        )
        
        self.output_text.append(html)
        
        # Auto-scroll if enabled
        if self.auto_scroll:
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.output_text.setTextCursor(cursor)
    
    def _toggle_auto_scroll(self, state: int) -> None:
        """Toggle auto-scroll"""
        self.auto_scroll = (state == Qt.Checked)
    
    def _toggle_level_filter(self, level: MessageLevel, state: int) -> None:
        """Toggle level filter"""
        self.level_filters[level] = (state == Qt.Checked)
        self._reapply_filters()
    
    def _toggle_category_filter(self, category: MessageCategory, state: int) -> None:
        """Toggle category filter"""
        self.category_filters[category] = (state == Qt.Checked)
        self._reapply_filters()
    
    def _reapply_filters(self) -> None:
        """Reapply all filters and redisplay"""
        self.output_text.clear()
        self.filtered_messages.clear()
        
        for msg_data in self.messages:
            if self._should_display_message(msg_data):
                self.filtered_messages.append(msg_data)
                self._append_colored_message(msg_data)
        
        self._update_stats()
    
    def _clear_output(self) -> None:
        """Clear all messages"""
        self.messages.clear()
        self.filtered_messages.clear()
        self.output_text.clear()
        self.message_count = 0
        self._update_stats()
    
    def _export_output(self) -> None:
        """Export output to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"optimizer_output_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write("=== Optimizer Live Output ===\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Messages: {len(self.messages)}\n")
                f.write("=" * 50 + "\n\n")
                
                for msg in self.messages:
                    f.write(
                        f"{msg['timestamp']} "
                        f"[{msg['level'].value}] "
                        f"[{msg['category'].value}] "
                        f"{msg['message']}\n"
                    )
            
            self.add_message(f"Output exported to {filename}", "INFO", "SYSTEM")
            
        except Exception as e:
            self.add_message(f"Export failed: {str(e)}", "ERROR", "SYSTEM")
    
    def _update_stats(self) -> None:
        """Update statistics labels"""
        total = len(self.messages)
        displayed = len(self.filtered_messages)
        errors = len([m for m in self.messages if m['level'] == MessageLevel.ERROR])
        warnings = len([m for m in self.messages if m['level'] == MessageLevel.WARNING])
        
        self.msg_count_label.setText(f"Messages: <b>{total}</b>")
        self.filtered_count_label.setText(f"Displayed: <b>{displayed}</b>")
        self.error_count_label.setText(f"⛔ Errors: <b>{errors}</b>")
        self.warning_count_label.setText(f"⚠️ Warnings: <b>{warnings}</b>")
    
    def get_messages(self) -> List[Dict]:
        """Get all messages"""
        return self.messages.copy()
    
    def get_filtered_messages(self) -> List[Dict]:
        """Get currently displayed messages"""
        return self.filtered_messages.copy()
    
    def set_running(self, running: bool) -> None:
        """
        Set running state and update icon.
        
        Args:
            running: True if test is running, False if idle
        """
        self.is_running = running
        self._update_title_icon()
    
    def _update_title_icon(self) -> None:
        """Update title icon based on running state"""
        icon = "🟢" if self.is_running else "🔴"
        
        if self.strategy_name:
            title_text = f"{icon} Live Output - {self.strategy_name}"
        else:
            title_text = f"{icon} Live Output"
        
        self.title_label.setText(title_text)
