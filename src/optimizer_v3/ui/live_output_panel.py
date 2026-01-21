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
    QGroupBox, QTextEdit, QCheckBox, QScrollArea, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCursor, QColor, QFont, QTextCharFormat, QTextBlockFormat
from datetime import datetime
from enum import Enum

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_checkbox_style,
    get_text_edit_stylesheet,
    get_color
)


class HoverHighlightTextEdit(QTextEdit):
    """
    Custom QTextEdit with line hover highlighting.
    
    When mouse hovers over a line, that line's background darkens
    to provide visual feedback.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)  # Enable mouse tracking for hover
        self.current_hover_block = None  # Track currently hovered block
    
    def mouseMoveEvent(self, event):
        """Handle mouse move to highlight line under cursor"""
        # Get cursor position at mouse coordinates
        cursor = self.cursorForPosition(event.pos())
        block = cursor.block()
        
        # If we're hovering over a different block, update highlight
        if block != self.current_hover_block:
            # Clear previous highlight
            if self.current_hover_block and self.current_hover_block.isValid():
                self._clear_block_highlight(self.current_hover_block)
            
            # Apply new highlight
            if block.isValid() and block.text().strip():  # Only highlight non-empty lines
                self._highlight_block(block)
                self.current_hover_block = block
            else:
                self.current_hover_block = None
        
        # Call parent implementation
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        """Clear highlight when mouse leaves widget"""
        if self.current_hover_block and self.current_hover_block.isValid():
            self._clear_block_highlight(self.current_hover_block)
            self.current_hover_block = None
        super().leaveEvent(event)
    
    def _highlight_block(self, block):
        """Apply darker teal background to entire row (full width) for hover visibility"""
        cursor = QTextCursor(block)
        
        # Use block format to highlight the ENTIRE row (full width)
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(QColor("#053336"))  # Darker teal - clearly visible against #15191E
        cursor.setBlockFormat(block_fmt)
    
    def _clear_block_highlight(self, block):
        """Remove highlight from entire row"""
        cursor = QTextCursor(block)
        
        # Reset to transparent background (uses stylesheet default)
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(Qt.transparent)
        cursor.setBlockFormat(block_fmt)


class MessageLevel(Enum):
    """Message level enumeration"""
    INFO = "INFO"
    DECISION = "DECISION"
    WIN = "WIN"             # Winning trades (new)
    LOSS = "LOSS"           # Losing trades (was WARNING)
    STOP_LOSS = "STOP LOSS" # Stop loss triggers (was ERROR)
    
    # Backward compatibility aliases
    ACTION = "WIN"          # ACTION now maps to WIN
    WARNING = "LOSS"
    ERROR = "STOP LOSS"


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
            MessageLevel.WIN: True,
            MessageLevel.LOSS: True,
            MessageLevel.STOP_LOSS: True,
            # Backward compatibility
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
            title_text = f"● Live Output - {self.strategy_name}"
        else:
            title_text = "● Live Output"
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(self.title_label)
        
        # Filters (buttons moved to bottom)
        filters_group = self._create_filters()
        layout.addWidget(filters_group)
        
        # Output display
        output_group = self._create_output_display()
        layout.addWidget(output_group)
        
        # Stats + Control bar combined at bottom
        bottom_bar = self._create_bottom_bar()
        layout.addLayout(bottom_bar)
        
        self.setLayout(layout)
    
    def _create_bottom_bar(self) -> QHBoxLayout:
        """Create combined bottom bar: stats on left, buttons on right"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Stats on the left
        self.msg_count_label = QLabel("Messages: <b>0</b>")
        self.msg_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.msg_count_label)
        
        self.filtered_count_label = QLabel("Displayed: <b>0</b>")
        self.filtered_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.filtered_count_label)
        
        self.error_count_label = QLabel("⛔ Errors: <b>0</b>")
        self.error_count_label.setStyleSheet(f"color: {get_color('error')};")
        layout.addWidget(self.error_count_label)
        
        self.warning_count_label = QLabel("⚠️ Warnings: <b>0</b>")
        self.warning_count_label.setStyleSheet(f"color: {get_color('warning')};")
        layout.addWidget(self.warning_count_label)
        
        # Stretch pushes buttons to the right
        layout.addStretch()
        
        # Buttons on the right
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_btn.setFixedSize(130, 52)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        copy_btn.setToolTip("Copy filtered output to clipboard")
        layout.addWidget(copy_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_btn.setFixedSize(130, 52)
        clear_btn.clicked.connect(self._clear_output)
        clear_btn.setToolTip("Clear all messages")
        layout.addWidget(clear_btn)
        
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.setFixedSize(130, 52)
        export_btn.clicked.connect(self._export_output)
        export_btn.setToolTip("Export output to file")
        layout.addWidget(export_btn)
        
        return layout
    
    def _create_filters(self) -> QGroupBox:
        """Create filter controls - INLINE with separator - SPACIOUS READABLE LAYOUT"""
        group = QGroupBox("Filters")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(110)  # Increased to 110px for breathing room
        
        # Single horizontal layout for all filters
        layout = QHBoxLayout()
        layout.setSpacing(25)  # Increased spacing between elements from 15 to 25
        layout.setContentsMargins(15, 20, 15, 15)  # More padding: left, top, right, bottom
        
        # Level filters
        level_label = QLabel("Levels:")
        level_label.setStyleSheet(get_label_style('muted'))
        level_label.setContentsMargins(0, 0, 10, 0)  # Add right margin before checkboxes
        layout.addWidget(level_label)
        
        # Level filter checkboxes - UNIQUE COLOR for each level (no duplicates)
        level_colors = {
            MessageLevel.INFO: '#2070FF',      # Blue
            MessageLevel.DECISION: '#10B981',  # Green
            MessageLevel.WIN: '#14B8A6',       # Cyan/Teal (WIN trades)
            MessageLevel.LOSS: '#FFA500',      # Orange (LOSS trades)
            MessageLevel.STOP_LOSS: '#C35252', # Red (Stop loss)
            # Backward compatibility
            MessageLevel.ACTION: '#14B8A6',
            MessageLevel.WARNING: '#FFA500',
            MessageLevel.ERROR: '#C35252'
        }
        
        # Only show main levels (not backward compatibility aliases)
        main_levels = [MessageLevel.INFO, MessageLevel.DECISION, MessageLevel.WIN, 
                      MessageLevel.LOSS, MessageLevel.STOP_LOSS]
        
        self.level_checkboxes = {}
        for level in main_levels:
            checkbox = QCheckBox(level.value)
            checkbox.setChecked(True)
            # Apply color-coded style
            color = level_colors.get(level, get_color('text_primary'))
            checkbox.setStyleSheet(f"QCheckBox {{ color: {color}; background: transparent; }}")
            checkbox.stateChanged.connect(lambda state, l=level: self._toggle_level_filter(l, state))
            layout.addWidget(checkbox)
            self.level_checkboxes[level] = checkbox
        
        # Separator between Levels and Categories
        separator = QLabel("|")
        separator.setStyleSheet(f"color: {get_color('border')}; font-size: 18px; padding: 0 10px;")
        layout.addWidget(separator)
        
        # Category filters
        category_label = QLabel("Categories:")
        category_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(category_label)
        
        # Category filter checkboxes - UNIQUE COLOR for each category (no duplicates)
        category_colors = {
            MessageCategory.SIGNAL: '#10B981',   # Green (trading signals)
            MessageCategory.TRADE: '#8B5CF6',    # Purple/Violet (distinct color)
            MessageCategory.RISK: '#C35252',     # Red (risk management)
            MessageCategory.SYSTEM: '#9AA0A6',   # Gray (system messages)
            MessageCategory.OPTIMIZER: '#FFA500' # Orange (optimizer)
        }
        
        self.category_checkboxes = {}
        for category in MessageCategory:
            checkbox = QCheckBox(category.value)
            checkbox.setChecked(True)
            # Apply color-coded style
            color = category_colors.get(category, get_color('text_primary'))
            checkbox.setStyleSheet(f"QCheckBox {{ color: {color}; background: transparent; }}")
            checkbox.stateChanged.connect(lambda state, c=category: self._toggle_category_filter(c, state))
            layout.addWidget(checkbox)
            self.category_checkboxes[category] = checkbox
        
        layout.addStretch()
        
        # Unselect All / Select All button
        self.toggle_all_btn = QPushButton("Unselect All")
        self.toggle_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self.toggle_all_btn.setFixedHeight(35)
        self.toggle_all_btn.clicked.connect(self._toggle_all_filters)
        layout.addWidget(self.toggle_all_btn)
        
        # Auto-scroll checkbox at the very right
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.setStyleSheet(get_checkbox_style())
        self.auto_scroll_check.stateChanged.connect(self._toggle_auto_scroll)
        layout.addWidget(self.auto_scroll_check)
        
        group.setLayout(layout)
        return group
    
    def _create_output_display(self) -> QGroupBox:
        """Create output text display - WITH PROPER PADDING FOR LABEL VISIBILITY"""
        group = QGroupBox("Output")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 10)  # Increased top margin for label visibility
        
        # Text edit for output - HUGE FONT (26px) + DARK BACKGROUND + HOVER HIGHLIGHTING
        self.output_text = HoverHighlightTextEdit()  # Use custom hover-enabled widget
        self.output_text.setReadOnly(True)
        
        # TRIPLE FONT PROTECTION - 26 PIXELS (much larger)
        # 1. Create LARGE monospace font - Use PIXEL SIZE (not points) to avoid DPI scaling
        large_font = QFont("Courier New")
        large_font.setPixelSize(26)  # 26 PIXELS - 44% larger than before
        large_font.setStyleHint(QFont.Monospace)
        large_font.setBold(False)
        
        # 2. Set on widget itself
        self.output_text.setFont(large_font)
        
        # 3. Set on document
        self.output_text.document().setDefaultFont(large_font)
        
        # DARK BACKGROUND - correct color from styles.py (#15191E)
        # WITH HOVER HIGHLIGHTING - darker background on line hover
        self.output_text.setStyleSheet(
            "QTextEdit {"
            "   background-color: #15191E;"  # Correct dark background (bg_dark from styles.py)
            "   color: #E8EAED;"              # Light text
            "   border: 1px solid #3C4149;"  # Dark border
            "   padding: 8px;"
            "   selection-background-color: #2A2F3A;"  # Darker background for selection
            "}"
        )
        
        layout.addWidget(self.output_text)
        group.setLayout(layout)
        return group
    
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
        """Append message with color coding - Uses document default font (14pt Courier New)"""
        # Get color based on level - UNIQUE colors matching filter checkboxes
        level_color_map = {
            MessageLevel.INFO: '#2070FF',      # Blue
            MessageLevel.DECISION: '#10B981',  # Green
            MessageLevel.WIN: '#14B8A6',       # Cyan/Teal (WIN trades)
            MessageLevel.LOSS: '#FFA500',      # Orange (LOSS trades)
            MessageLevel.STOP_LOSS: '#C35252', # Red (Stop loss)
            # Backward compatibility
            MessageLevel.ACTION: '#14B8A6',
            MessageLevel.WARNING: '#FFA500',
            MessageLevel.ERROR: '#C35252'
        }
        
        # Get color based on category - UNIQUE colors matching filter checkboxes
        category_color_map = {
            MessageCategory.SIGNAL: '#10B981',   # Green
            MessageCategory.TRADE: '#8B5CF6',    # Purple/Violet
            MessageCategory.RISK: '#C35252',     # Red
            MessageCategory.SYSTEM: '#9AA0A6',   # Gray
            MessageCategory.OPTIMIZER: '#FFA500' # Orange
        }
        
        level_color = level_color_map.get(msg_data['level'], get_color('text_primary'))
        category_color = category_color_map.get(msg_data['category'], get_color('secondary'))
        
        # Format message
        timestamp = msg_data['timestamp']
        level = msg_data['level'].value
        category = msg_data['category'].value
        message = msg_data['message']
        
        # Build HTML - Colors match filter checkboxes exactly
        html = (
            f"<span style='color: {get_color('text_muted')};'>{timestamp}</span> "
            f"<span style='color: {level_color}; font-weight: bold;'>[{level}]</span> "
            f"<span style='color: {category_color}; font-weight: bold;'>[{category}]</span> "
            f"<span style='color: {get_color('text_primary')};'>{message}</span>"
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
    
    def _toggle_all_filters(self) -> None:
        """Toggle all filters on/off"""
        # Check if any filter is currently checked
        any_checked = any(self.level_filters.values()) or any(self.category_filters.values())
        
        # If any checked, unselect all. Otherwise, select all.
        new_state = not any_checked
        
        # Update all level filters
        for level in self.level_filters:
            self.level_filters[level] = new_state
            if level in self.level_checkboxes:
                self.level_checkboxes[level].setChecked(new_state)
        
        # Update all category filters
        for category in self.category_filters:
            self.category_filters[category] = new_state
            if category in self.category_checkboxes:
                self.category_checkboxes[category].setChecked(new_state)
        
        # Update button text
        self.toggle_all_btn.setText("Unselect All" if new_state else "Select All")
        
        # Reapply filters
        self._reapply_filters()
    
    def _copy_to_clipboard(self) -> None:
        """Copy filtered output to clipboard"""
        if not self.filtered_messages:
            self.add_message("No messages to copy", "INFO", "SYSTEM")
            return
        
        # Build plain text from filtered messages
        lines = []
        for msg in self.filtered_messages:
            lines.append(
                f"{msg['timestamp']} "
                f"[{msg['level'].value}] "
                f"[{msg['category'].value}] "
                f"{msg['message']}"
            )
        
        text = "\n".join(lines)
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        self.add_message(f"Copied {len(self.filtered_messages)} messages to clipboard", "INFO", "SYSTEM")
    
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
        stop_losses = len([m for m in self.messages if m['level'] in [MessageLevel.STOP_LOSS, MessageLevel.ERROR]])
        losses = len([m for m in self.messages if m['level'] in [MessageLevel.LOSS, MessageLevel.WARNING]])
        
        self.msg_count_label.setText(f"Messages: <b>{total}</b>")
        self.filtered_count_label.setText(f"Displayed: <b>{displayed}</b>")
        self.error_count_label.setText(f"⛔ Stop Loss: <b>{stop_losses}</b>")
        self.warning_count_label.setText(f"📉 Losses: <b>{losses}</b>")
    
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
        icon = "▶" if self.is_running else "●"  # Play symbol when running, circle when stopped
        
        if self.strategy_name:
            title_text = f"{icon} Live Output - {self.strategy_name}"
        else:
            title_text = f"{icon} Live Output"
        
        self.title_label.setText(title_text)
