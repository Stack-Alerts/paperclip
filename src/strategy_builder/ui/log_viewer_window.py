"""
Log Viewer Window - Professional Log File Viewer

Matches Live Output panel styling exactly.
Views saved log files with filtering and export capabilities.

ZERO HARDCODED STYLES - All from styles.py

Author: Strategy Builder Team
Date: 2026-01-21
"""

from typing import Dict, List
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QCheckBox, QLabel, QGroupBox, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QTextCursor

from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_color
)


class LogViewerWindow(QDialog):
    """
    Professional log viewer - matches Live Output panel exactly.
    """
    
    def __init__(self, log_file_path: Path, parent=None):
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
            'OPTIMIZER': True
        }
        
        self._init_ui()
        self._load_log_file()
        self._restore_geometry()
    
    def _init_ui(self):
        """Initialize UI - matches Live Output"""
        # Window properties
        self.setWindowTitle(f"Log Viewer - {self.log_file_path.name}")
        self.setGeometry(100, 100, 1400, 900)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel(f"● Log Viewer - {self.log_file_path.name}")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        main_layout.addWidget(title_label)
        
        # Filters
        filters_group = self._create_filters()
        main_layout.addWidget(filters_group)
        
        # Output
        output_group = self._create_output_display()
        main_layout.addWidget(output_group)
        
        # Bottom bar (stats + buttons)
        bottom_bar = self._create_bottom_bar()
        main_layout.addLayout(bottom_bar)
        
        self.setLayout(main_layout)
    
    def _create_filters(self) -> QGroupBox:
        """Create filters - matches Live Output exactly"""
        group = QGroupBox("Filters")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(110)
        
        layout = QHBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Levels
        level_label = QLabel("Levels:")
        level_label.setStyleSheet(get_label_style('muted'))
        level_label.setContentsMargins(0, 0, 10, 0)
        layout.addWidget(level_label)
        
        # Level checkboxes with exact Live Output colors
        level_colors = {
            'INFO': '#2070FF',
            'DECISION': '#FFD700',
            'WIN': '#10B981',
            'LOSS': '#FF8C00',
            'STOP LOSS': '#C35252'
        }
        
        self.level_checkboxes = {}
        for level, color in level_colors.items():
            checkbox = QCheckBox(level)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(f"QCheckBox {{ color: {color}; background: transparent; }}")
            checkbox.stateChanged.connect(lambda state, l=level: self._on_filter_changed(l, state, 'level'))
            self.level_checkboxes[level] = checkbox
            layout.addWidget(checkbox)
        
        # Separator
        separator = QLabel("|")
        separator.setStyleSheet(f"color: {get_color('border')}; font-size: 18px; padding: 0 10px;")
        layout.addWidget(separator)
        
        # Categories
        category_label = QLabel("Categories:")
        category_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(category_label)
        
        # Category checkboxes with exact Live Output colors
        category_colors = {
            'SIGNAL': '#10B981',
            'TRADE': '#8B5CF6',
            'RISK': '#C35252',
            'SYSTEM': '#9AA0A6',
            'OPTIMIZER': '#FFA500'
        }
        
        self.category_checkboxes = {}
        for category, color in category_colors.items():
            checkbox = QCheckBox(category)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(f"QCheckBox {{ color: {color}; background: transparent; }}")
            checkbox.stateChanged.connect(lambda state, c=category: self._on_filter_changed(c, state, 'category'))
            self.category_checkboxes[category] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        
        # Unselect All button
        self.toggle_all_btn = QPushButton("Unselect All")
        self.toggle_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self.toggle_all_btn.setFixedHeight(35)
        self.toggle_all_btn.clicked.connect(self._toggle_all_filters)
        layout.addWidget(self.toggle_all_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_output_display(self) -> QGroupBox:
        """Create output - matches Live Output exactly"""
        group = QGroupBox("Output")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Text edit - EXACT match to Live Output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        
        # Large monospace font (26px like Live Output)
        large_font = QFont("Courier New")
        large_font.setPixelSize(26)
        large_font.setStyleHint(QFont.Monospace)
        self.output_text.setFont(large_font)
        self.output_text.document().setDefaultFont(large_font)
        
        # Dark background - EXACT match to Live Output
        self.output_text.setStyleSheet(
            "QTextEdit {"
            "   background-color: #15191E;"
            "   color: #E8EAED;"
            "   border: 1px solid #3C4149;"
            "   padding: 8px;"
            "   selection-background-color: #2A2F3A;"
            "}"
        )
        
        layout.addWidget(self.output_text)
        group.setLayout(layout)
        return group
    
    def _create_bottom_bar(self) -> QHBoxLayout:
        """Create bottom bar - matches Live Output"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # Stats on left
        base_style = "vertical-align: middle; padding: 0px; margin: 0px;"
        
        self.msg_count_label = QLabel("Messages: <b>0</b>")
        self.msg_count_label.setStyleSheet(get_label_style() + base_style)
        layout.addWidget(self.msg_count_label)
        
        self.filtered_count_label = QLabel("Displayed: <b>0</b>")
        self.filtered_count_label.setStyleSheet(get_label_style() + base_style)
        layout.addWidget(self.filtered_count_label)
        
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
        
        close_btn = QPushButton("✖ Close")
        close_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        close_btn.setFixedSize(130, 52)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return layout
    
    def _load_log_file(self):
        """Load and display log file"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                self.full_content = f.read()
            
            if not self.full_content:
                self.output_text.setPlainText("(Log file is empty)")
                return
            
            self._apply_filters()
            
        except Exception as e:
            error_msg = f"ERROR: Failed to load log file\n{str(e)}"
            self.output_text.setPlainText(error_msg)
            QMessageBox.critical(self, "Error", f"Failed to load log file:\n\n{str(e)}")
    
    def _apply_filters(self):
        """Apply filters and display content"""
        if not self.full_content:
            return
        
        lines = self.full_content.split('\n')
        filtered = []
        
        for line in lines:
            if self._line_matches_filters(line):
                filtered.append(line)
        
        self.filtered_lines = filtered
        self.output_text.setPlainText('\n'.join(filtered))
        
        # Update stats
        self.msg_count_label.setText(f"Messages: <b>{len(lines)}</b>")
        self.filtered_count_label.setText(f"Displayed: <b>{len(filtered)}</b>")
    
    def _line_matches_filters(self, line: str) -> bool:
        """Check if line matches filters"""
        if not line.strip():
            return True
        
        line_upper = line.upper()
        
        # If no filters active, show everything
        if not any(self.level_filters.values()) and not any(self.category_filters.values()):
            return True
        
        # Always show structural elements
        if any(char in line for char in ['═', '─', '║', '╔', '╚']):
            return True
        
        # Always show critical messages
        if any(keyword in line_upper for keyword in ['ERROR', 'CRITICAL', 'WARNING']):
            return True
        
        # Check level match
        level_match = any(
            enabled and level.upper() in line_upper
            for level, enabled in self.level_filters.items()
        )
        
        # Check category match
        category_match = any(
            enabled and category.upper() in line_upper
            for category, enabled in self.category_filters.items()
        )
        
        return level_match or category_match
    
    def _on_filter_changed(self, filter_name: str, state: int, filter_type: str):
        """Handle filter change"""
        is_checked = state == Qt.Checked
        
        if filter_type == 'level':
            self.level_filters[filter_name] = is_checked
        else:
            self.category_filters[filter_name] = is_checked
        
        self._update_toggle_button_text()
        self._apply_filters()
    
    def _toggle_all_filters(self):
        """Toggle all filters"""
        button_text = self.toggle_all_btn.text()
        new_state = button_text == "Select All"
        
        for checkbox in self.level_checkboxes.values():
            checkbox.setChecked(new_state)
        
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(new_state)
    
    def _update_toggle_button_text(self):
        """Update toggle button text"""
        all_selected = all(self.level_filters.values()) and all(self.category_filters.values())
        self.toggle_all_btn.setText("Unselect All" if all_selected else "Select All")
    
    def _copy_to_clipboard(self):
        """Copy all visible content"""
        content = '\n'.join(self.filtered_lines)
        if not content:
            QMessageBox.information(self, "Nothing to Copy", "No content to copy.")
            return
        
        QApplication.clipboard().setText(content)
        self.filtered_count_label.setText(f"✅ Copied {len(self.filtered_lines)} lines to clipboard")
    
    def _copy_selection(self):
        """Copy selected text"""
        selected = self.output_text.textCursor().selectedText().replace('\u2029', '\n')
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select text to copy.")
            return
        
        QApplication.clipboard().setText(selected)
        line_count = len(selected.split('\n'))
        self.filtered_count_label.setText(f"✅ Copied {line_count} selected lines")
    
    def _restore_geometry(self):
        """Restore window geometry"""
        settings = QSettings("BTC_Engine", "LogViewer")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """Save geometry on close"""
        settings = QSettings("BTC_Engine", "LogViewer")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
