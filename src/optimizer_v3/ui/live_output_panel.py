"""
Live Output Panel - Window 2 Tab 2

Real-time output streaming for backtest/optimization execution:
- Message display with filtering
- Color-coded output levels
- Category filtering
- Auto-scrolling
- Zero hardcoded styles (uses styles.py)

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.4)
"""

from typing import List, Dict, Optional, Set
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QTextEdit, QComboBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont
from datetime import datetime
from enum import Enum

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_checkbox_style,
    get_primary_button_stylesheet,
    get_color,
    COLORS
)


class OutputLevel(Enum):
    """Output message levels"""
    INFO = "info"
    DECISION = "decision"
    ACTION = "action"
    WARNING = "warning"
    ERROR = "error"


class OutputCategory(Enum):
    """Output message categories"""
    SIGNAL = "signal"
    TRADE = "trade"
    RISK = "risk"
    SYSTEM = "system"
    OPTIMIZER = "optimizer"


class LiveOutputPanel(QWidget):
    """
    Live Output Panel for real-time execution monitoring.
    
    Provides:
    - Real-time message streaming
    - Message filtering by level and category
    - Color-coded output
    - Auto-scrolling
    - Message export
    """
    
    # Signals
    message_received = pyqtSignal(dict)  # Emits new messages
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages: List[Dict] = []
        self.auto_scroll = True
        self.max_messages = 10000  # Limit to prevent memory issues
        
        # Filter settings
        self.active_levels: Set[OutputLevel] = set(OutputLevel)
        self.active_categories: Set[OutputCategory] = set(OutputCategory)
        
        self._init_ui()
        
        # Update timer for batching messages
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._flush_pending_messages)
        self.update_timer.setInterval(100)  # Update every 100ms
        self.pending_messages: List[Dict] = []
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("💚 Live Output")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title_label)
        
        # Control bar
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        # Filter panel
        filter_panel = self._create_filter_panel()
        layout.addWidget(filter_panel)
        
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
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_btn.clicked.connect(self._clear_output)
        clear_btn.setToolTip("Clear all output messages")
        layout.addWidget(clear_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.clicked.connect(self._export_output)
        export_btn.setToolTip("Export output to file")
        layout.addWidget(export_btn)
        
        # Auto-scroll checkbox
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setStyleSheet(get_checkbox_style())
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.stateChanged.connect(self._toggle_autoscroll)
        self.autoscroll_check.setToolTip("Automatically scroll to show latest messages")
        layout.addWidget(self.autoscroll_check)
        
        layout.addStretch()
        
        # Message count
        self.count_label = QLabel("Messages: <b>0</b>")
        self.count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.count_label)
        
        return layout
    
    def _create_filter_panel(self) -> QGroupBox:
        """Create message filter panel"""
        group = QGroupBox("Message Filters")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(120)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Level filters
        level_layout = QHBoxLayout()
        level_layout.setSpacing(15)
        
        level_label = QLabel("Levels:")
        level_label.setStyleSheet(get_label_style('muted'))
        level_layout.addWidget(level_label)
        
        self.level_checks: Dict[OutputLevel, QCheckBox] = {}
        for level in OutputLevel:
            checkbox = QCheckBox(level.value.capitalize())
            checkbox.setStyleSheet(get_checkbox_style())
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, l=level: self._toggle_level_filter(l, state))
            self.level_checks[level] = checkbox
            level_layout.addWidget(checkbox)
        
        level_layout.addStretch()
        layout.addLayout(level_layout)
        
        # Category filters
        category_layout = QHBoxLayout()
        category_layout.setSpacing(15)
        
        category_label = QLabel("Categories:")
        category_label.setStyleSheet(get_label_style('muted'))
        category_layout.addWidget(category_label)
        
        self.category_checks: Dict[OutputCategory, QCheckBox] = {}
        for category in OutputCategory:
            checkbox = QCheckBox(category.value.capitalize())
            checkbox.setStyleSheet(get_checkbox_style())
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, c=category: self._toggle_category_filter(c, state)
            )
            self.category_checks[category] = checkbox
            category_layout.addWidget(checkbox)
        
        category_layout.addStretch()
        layout.addLayout(category_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_output_display(self) -> QGroupBox:
        """Create output text display"""
        group = QGroupBox("Output Stream")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Text edit for output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Use monospace font for better readability
        font = QFont("Courier New", 10)
        self.output_text.setFont(font)
        
        # Set text color from styles
        text_color = COLORS['text_primary']
        bg_color = COLORS['bg_dark']
        self.output_text.setStyleSheet(
            f"QTextEdit {{ "
            f"color: {text_color}; "
            f"background-color: {bg_color}; "
            f"border: 1px solid {COLORS['border']}; "
            f"border-radius: 4px; "
            f"padding: 8px; "
            f"}}"
        )
        
        layout.addWidget(self.output_text)
        group.setLayout(layout)
        return group
    
    def _create_stats_bar(self) -> QHBoxLayout:
        """Create stats bar"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Info count
        self.info_count_label = QLabel("ℹ️ Info: <b>0</b>")
        self.info_count_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.info_count_label)
        
        # Decision count
        self.decision_count_label = QLabel("🔵 Decision: <b>0</b>")
        self.decision_count_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.decision_count_label)
        
        # Action count
        self.action_count_label = QLabel("✅ Action: <b>0</b>")
        self.action_count_label.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(self.action_count_label)
        
        # Warning count
        self.warning_count_label = QLabel("⚠️ Warning: <b>0</b>")
        self.warning_count_label.setStyleSheet(f"color: {COLORS['warning']};")
        layout.addWidget(self.warning_count_label)
        
        # Error count
        self.error_count_label = QLabel("❌ Error: <b>0</b>")
        self.error_count_label.setStyleSheet(f"color: {COLORS['error']};")
        layout.addWidget(self.error_count_label)
        
        layout.addStretch()
        return layout
    
    def add_message(self,
                   level: OutputLevel,
                   category: OutputCategory,
                   message: str,
                   details: Optional[Dict] = None,
                   source: Optional[str] = None) -> None:
        """
        Add message to output stream.
        
        Args:
            level: Message level
            category: Message category
            message: Message text
            details: Optional details dictionary
            source: Optional source identifier
        """
        msg = {
            'timestamp': datetime.now(),
            'level': level,
            'category': category,
            'message': message,
            'details': details or {},
            'source': source or 'system'
        }
        
        # Add to pending messages
        self.pending_messages.append(msg)
        
        # Start timer if not running
        if not self.update_timer.isActive():
            self.update_timer.start()
    
    def _flush_pending_messages(self) -> None:
        """Flush pending messages to display"""
        if not self.pending_messages:
            self.update_timer.stop()
            return
        
        # Process messages
        for msg in self.pending_messages:
            self.messages.append(msg)
            
            # Apply filters
            if (msg['level'] in self.active_levels and 
                msg['category'] in self.active_categories):
                self._display_message(msg)
        
        # Clear pending
        self.pending_messages.clear()
        
        # Trim messages if over limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # Update stats
        self._update_stats()
    
    def _display_message(self, msg: Dict) -> None:
        """Display a single message"""
        # Format timestamp
        time_str = msg['timestamp'].strftime('%H:%M:%S.%f')[:-3]
        
        # Get color for level
        level_colors = {
            OutputLevel.INFO: COLORS['text_primary'],
            OutputLevel.DECISION: COLORS['info'],
            OutputLevel.ACTION: COLORS['success'],
            OutputLevel.WARNING: COLORS['warning'],
            OutputLevel.ERROR: COLORS['error']
        }
        color = level_colors.get(msg['level'], COLORS['text_primary'])
        
        # Format message
        html = (
            f"<span style='color: {COLORS['text_muted']};'>[{time_str}]</span> "
            f"<span style='color: {COLORS['text_secondary']};'>[{msg['category'].value.upper()}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>{msg['message']}</span>"
        )
        
        # Add details if present
        if msg['details']:
            details_str = ' | '.join(
                f"{k}: {v}" for k, v in msg['details'].items()
            )
            html += f"<span style='color: {COLORS['text_secondary']};'> ({details_str})</span>"
        
        # Append to text edit
        self.output_text.append(html)
        
        # Auto-scroll if enabled
        if self.auto_scroll:
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.output_text.setTextCursor(cursor)
    
    def _update_stats(self) -> None:
        """Update statistics display"""
        counts = {
            OutputLevel.INFO: 0,
            OutputLevel.DECISION: 0,
            OutputLevel.ACTION: 0,
            OutputLevel.WARNING: 0,
            OutputLevel.ERROR: 0
        }
        
        for msg in self.messages:
            level = msg['level']
            if level in counts:
                counts[level] += 1
        
        # Update labels
        self.info_count_label.setText(f"ℹ️ Info: <b>{counts[OutputLevel.INFO]}</b>")
        self.decision_count_label.setText(f"🔵 Decision: <b>{counts[OutputLevel.DECISION]}</b>")
        self.action_count_label.setText(f"✅ Action: <b>{counts[OutputLevel.ACTION]}</b>")
        self.warning_count_label.setText(f"⚠️ Warning: <b>{counts[OutputLevel.WARNING]}</b>")
        self.error_count_label.setText(f"❌ Error: <b>{counts[OutputLevel.ERROR]}</b>")
        self.count_label.setText(f"Messages: <b>{len(self.messages)}</b>")
    
    def _toggle_level_filter(self, level: OutputLevel, state: int) -> None:
        """Toggle level filter"""
        if state == Qt.CheckState.Checked.value:
            self.active_levels.add(level)
        else:
            self.active_levels.discard(level)
        
        # Refresh display
        self._refresh_display()
    
    def _toggle_category_filter(self, category: OutputCategory, state: int) -> None:
        """Toggle category filter"""
        if state == Qt.CheckState.Checked.value:
            self.active_categories.add(category)
        else:
            self.active_categories.discard(category)
        
        # Refresh display
        self._refresh_display()
    
    def _refresh_display(self) -> None:
        """Refresh display with current filters"""
        self.output_text.clear()
        
        for msg in self.messages:
            if (msg['level'] in self.active_levels and 
                msg['category'] in self.active_categories):
                self._display_message(msg)
    
    def _toggle_autoscroll(self, state: int) -> None:
        """Toggle auto-scroll"""
        self.auto_scroll = (state == Qt.CheckState.Checked.value)
    
    def _clear_output(self) -> None:
        """Clear all output"""
        self.messages.clear()
        self.output_text.clear()
        self._update_stats()
    
    def _export_output(self) -> None:
        """Export output to file"""
        # TODO: Implement file dialog and export
        from datetime import datetime
        
        filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(filename, 'w') as f:
                for msg in self.messages:
                    time_str = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    f.write(
                        f"[{time_str}] [{msg['category'].value.upper()}] "
                        f"[{msg['level'].value.upper()}] {msg['message']}\n"
                    )
                    if msg['details']:
                        f.write(f"  Details: {msg['details']}\n")
                    f.write("\n")
            
            # Add success message
            self.add_message(
                OutputLevel.INFO,
                OutputCategory.SYSTEM,
                f"Output exported to {filename}"
            )
        except Exception as e:
            self.add_message(
                OutputLevel.ERROR,
                OutputCategory.SYSTEM,
                f"Export failed: {str(e)}"
            )
    
    def get_messages(self) -> List[Dict]:
        """
        Get all messages.
        
        Returns:
            List of message dictionaries
        """
        return self.messages.copy()
    
    def clear(self) -> None:
        """Clear all messages"""
        self._clear_output()
