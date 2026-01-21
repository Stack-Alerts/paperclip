"""
Log Viewer Window - Styled Log File Viewer

Professional log viewer with filtering and copy functionality.
Similar to Live Output panel but for viewing saved log files.

Features:
- Load and display log files
- Filter by log levels and categories
- Copy all or selected text
- Auto-scroll option
- Dark theme styling from styles.py

Author: Strategy Builder Team
Date: 2026-01-21
"""

from typing import Optional, Set
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QCheckBox, QLabel, QGroupBox, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor

from src.strategy_builder.ui.styles import (
    get_main_stylesheet,
    get_groupbox_header_stylesheet,
    get_primary_button_stylesheet,
    get_label_style,
    get_color
)

# Style constants (matching styles.py values)
SPACING_UNIT = 8
FONT_FAMILY = "Segoe UI"
FONT_SIZE_BASE = 14


class LogViewerWindow(QDialog):
    """
    Professional log viewer window.
    
    Displays log file content with filtering capabilities similar to Live Output panel.
    """
    
    def __init__(self, log_file_path: Path, parent=None):
        """
        Initialize log viewer window.
        
        Args:
            log_file_path: Path to the log file to display
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.log_file_path = log_file_path
        self.full_content = ""
        self.filtered_lines = []
        
        # Filter states (all enabled by default)
        self.level_filters = {
            'INFO': True,
            'DECISION': True,
            'WIN': True,
            'LOSS': True,
            'STOP LOSS': True
        }
        
        self.category_filters = {
            'SIGNAL': True,
            'TRADE': True,
            'RISK': True,
            'SYSTEM': True,
            'CONFIG': True
        }
        
        self.auto_scroll = True
        
        self._init_ui()
        self._load_log_file()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Window properties
        self.setWindowTitle(f"Log Viewer - {self.log_file_path.name}")
        self.setGeometry(100, 100, 1400, 900)
        
        # Apply dark theme from styles.py
        self.setStyleSheet(get_main_stylesheet())
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(SPACING_UNIT * 2, SPACING_UNIT * 2, 
                                       SPACING_UNIT * 2, SPACING_UNIT * 2)
        main_layout.setSpacing(SPACING_UNIT * 2)
        
        # Title
        title_label = QLabel(f"📄 Log Viewer - {self.log_file_path.name}")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {get_color('text')};")
        main_layout.addWidget(title_label)
        
        # Filters section
        filters_group = self._create_filters_section()
        main_layout.addWidget(filters_group)
        
        # Output section
        output_group = self._create_output_section()
        main_layout.addWidget(output_group, stretch=1)
        
        # Buttons section
        buttons_layout = self._create_buttons_section()
        main_layout.addLayout(buttons_layout)
        
        # Status bar
        self.status_label = QLabel("Messages: 0  |  Displayed: 0")
        self.status_label.setStyleSheet(get_label_style())
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
    
    def _create_filters_section(self) -> QGroupBox:
        """Create filters section similar to Live Output."""
        group = QGroupBox("Filters")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        layout.setContentsMargins(SPACING_UNIT * 2, SPACING_UNIT * 2, 
                                 SPACING_UNIT * 2, SPACING_UNIT * 2)
        
        # Levels row
        levels_layout = QHBoxLayout()
        levels_layout.setSpacing(SPACING_UNIT * 2)
        
        levels_label = QLabel("Levels:")
        levels_label.setStyleSheet(get_label_style())
        levels_layout.addWidget(levels_label)
        
        # Level checkboxes with colors
        level_colors = {
            'INFO': get_color('info'),
            'DECISION': get_color('warning'),
            'WIN': get_color('success'),
            'LOSS': get_color('error'),
            'STOP LOSS': get_color('error')
        }
        
        self.level_checkboxes = {}
        for level, color in level_colors.items():
            checkbox = QCheckBox(level)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(f"color: {color}; font-weight: 600;")
            checkbox.stateChanged.connect(lambda state, l=level: self._on_filter_changed(l, state, 'level'))
            self.level_checkboxes[level] = checkbox
            levels_layout.addWidget(checkbox)
        
        levels_layout.addStretch()
        layout.addLayout(levels_layout)
        
        # Categories row
        categories_layout = QHBoxLayout()
        categories_layout.setSpacing(SPACING_UNIT * 2)
        
        categories_label = QLabel("Categories:")
        categories_label.setStyleSheet(get_label_style())
        categories_layout.addWidget(categories_label)
        
        # Category checkboxes
        self.category_checkboxes = {}
        for category in ['SIGNAL', 'TRADE', 'RISK', 'SYSTEM', 'CONFIG']:
            checkbox = QCheckBox(category)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(f"color: {get_color('text')}; font-weight: 500;")
            checkbox.stateChanged.connect(lambda state, c=category: self._on_filter_changed(c, state, 'category'))
            self.category_checkboxes[category] = checkbox
            categories_layout.addWidget(checkbox)
        
        categories_layout.addStretch()
        
        # Unselect All button
        unselect_btn = QPushButton("Unselect All")
        unselect_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        unselect_btn.setFixedSize(130, 35)
        unselect_btn.clicked.connect(self._unselect_all_filters)
        categories_layout.addWidget(unselect_btn)
        
        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.setStyleSheet(f"color: {get_color('text')};")
        self.auto_scroll_checkbox.stateChanged.connect(self._on_auto_scroll_changed)
        categories_layout.addWidget(self.auto_scroll_checkbox)
        
        layout.addLayout(categories_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_output_section(self) -> QGroupBox:
        """Create output text area."""
        group = QGroupBox("Output")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING_UNIT, SPACING_UNIT, SPACING_UNIT, SPACING_UNIT)
        
        # Text edit for output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        
        # Set font
        font = QFont(FONT_FAMILY, FONT_SIZE_BASE)
        font.setStyleHint(QFont.Monospace)
        self.output_text.setFont(font)
        
        # Dark theme styling
        self.output_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {get_color('background_darker')};
                color: {get_color('text')};
                border: 1px solid {get_color('border')};
                border-radius: 4px;
                padding: {SPACING_UNIT}px;
            }}
        """)
        
        layout.addWidget(self.output_text)
        group.setLayout(layout)
        return group
    
    def _create_buttons_section(self) -> QHBoxLayout:
        """Create buttons section (Copy, Copy Selection, Close)."""
        layout = QHBoxLayout()
        layout.setSpacing(SPACING_UNIT * 2)
        
        layout.addStretch()
        
        # Copy button
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setStyleSheet(get_primary_button_stylesheet())
        copy_btn.setFixedSize(120, 45)
        copy_btn.clicked.connect(self._on_copy)
        copy_btn.setToolTip("Copy all visible log content to clipboard")
        layout.addWidget(copy_btn)
        
        # Copy Selection button
        copy_selection_btn = QPushButton("📋 Copy Selection")
        copy_selection_btn.setStyleSheet(get_primary_button_stylesheet())
        copy_selection_btn.setFixedSize(180, 45)
        copy_selection_btn.clicked.connect(self._on_copy_selection)
        copy_selection_btn.setToolTip("Copy selected text to clipboard")
        layout.addWidget(copy_selection_btn)
        
        # Close button
        close_btn = QPushButton("✖ Close")
        close_btn.setStyleSheet(get_primary_button_stylesheet())
        close_btn.setFixedSize(120, 45)
        close_btn.clicked.connect(self.close)
        close_btn.setToolTip("Close log viewer")
        layout.addWidget(close_btn)
        
        return layout
    
    def _load_log_file(self):
        """Load log file content."""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                self.full_content = f.read()
            
            # Apply filters and display
            self._apply_filters()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Log File",
                f"Failed to load log file:\n\n{str(e)}"
            )
            self.output_text.setPlainText(f"ERROR: Failed to load log file\n{str(e)}")
    
    def _apply_filters(self):
        """Apply current filters to log content."""
        lines = self.full_content.split('\n')
        
        # Filter lines based on current filter states
        filtered = []
        for line in lines:
            # Check if line should be displayed based on filters
            if self._line_matches_filters(line):
                filtered.append(line)
        
        self.filtered_lines = filtered
        
        # Update display
        self.output_text.setPlainText('\n'.join(filtered))
        
        # Auto-scroll to bottom if enabled
        if self.auto_scroll:
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_text.setTextCursor(cursor)
        
        # Update status
        total_lines = len(lines)
        displayed_lines = len(filtered)
        self.status_label.setText(f"Messages: {total_lines}  |  Displayed: {displayed_lines}")
    
    def _line_matches_filters(self, line: str) -> bool:
        """
        Check if a line matches current filter settings.
        
        Args:
            line: Log line to check
        
        Returns:
            True if line should be displayed
        """
        line_upper = line.upper()
        
        # If no filters are active, show everything
        if not any(self.level_filters.values()) and not any(self.category_filters.values()):
            return True
        
        # Check level filters
        level_match = False
        for level, enabled in self.level_filters.items():
            if enabled and level.upper() in line_upper:
                level_match = True
                break
        
        # Check category filters
        category_match = False
        for category, enabled in self.category_filters.items():
            if enabled and category.upper() in line_upper:
                category_match = True
                break
        
        # Additional keywords that should always pass
        always_show_keywords = ['ERROR', 'CRITICAL', 'WARNING', '═══', '───']
        for keyword in always_show_keywords:
            if keyword in line_upper:
                return True
        
        # Line passes if it matches at least one level OR one category
        # OR if it's a structural line (empty, separator, etc.)
        if not line.strip():  # Empty lines always show
            return True
        
        if '═' in line or '─' in line or '║' in line or '╔' in line or '╚' in line:  # Box drawing always shows
            return True
        
        return level_match or category_match
    
    def _on_filter_changed(self, filter_name: str, state: int, filter_type: str):
        """Handle filter checkbox change."""
        is_checked = state == Qt.Checked
        
        if filter_type == 'level':
            self.level_filters[filter_name] = is_checked
        elif filter_type == 'category':
            self.category_filters[filter_name] = is_checked
        
        # Reapply filters
        self._apply_filters()
    
    def _unselect_all_filters(self):
        """Unselect all filter checkboxes."""
        # Unselect all level filters
        for checkbox in self.level_checkboxes.values():
            checkbox.setChecked(False)
        
        # Unselect all category filters
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(False)
        
        # Filters will auto-apply via stateChanged signals
    
    def _on_auto_scroll_changed(self, state: int):
        """Handle auto-scroll checkbox change."""
        self.auto_scroll = state == Qt.Checked
    
    def _on_copy(self):
        """Copy all visible log content to clipboard."""
        content = self.output_text.toPlainText()
        
        if not content:
            QMessageBox.information(self, "Nothing to Copy", "No content to copy.")
            return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(content)
        
        # Show confirmation in status
        line_count = len(self.filtered_lines)
        self.status_label.setText(f"✅ Copied {line_count} lines to clipboard")
    
    def _on_copy_selection(self):
        """Copy selected text to clipboard."""
        cursor = self.output_text.textCursor()
        selected_text = cursor.selectedText()
        
        if not selected_text:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select text to copy.\n\nTip: Click and drag to select text."
            )
            return
        
        # Replace paragraph separator with newline
        selected_text = selected_text.replace('\u2029', '\n')
        
        clipboard = QApplication.clipboard()
        clipboard.setText(selected_text)
        
        # Show confirmation in status
        line_count = len(selected_text.split('\n'))
        self.status_label.setText(f"✅ Copied {line_count} selected lines to clipboard")
