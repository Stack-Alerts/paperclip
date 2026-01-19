"""
Custom Alert Dialog - Matching Data Update Modal Design

Replaces standard QMessageBox with institutional-grade styled alerts.
Matches the size and design of Data Update Modal for consistency.

Author: Strategy Builder Team
Date: 2026-01-19
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.strategy_builder.ui.styles import (
    get_main_stylesheet, get_panel_title_stylesheet,
    get_primary_button_stylesheet, get_secondary_button_stylesheet
)


class AlertDialog(QDialog):
    """
    Custom alert dialog matching Data Update Modal design.
    
    Replaces standard QMessageBox for consistent institutional-grade UI.
    Size: 600x400 (large enough to be readable but not overwhelming)
    """
    
    def __init__(
        self,
        title: str,
        heading: str,
        message: str,
        icon: str = "⚠️",
        parent: Optional['QWidget'] = None
    ):
        """
        Initialize the alert dialog.
        
        Args:
            title: Window title
            heading: Bold heading text
            message: Main message text (supports HTML)
            icon: Emoji icon (⚠️, ✅, ❌, ℹ️)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # Make dialog independent and draggable (matching Data Update Modal)
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint
        )
        self.setModal(True)
        
        # Large size matching Data Update Modal style (25% taller, 50% wider per user request)
        self.setMinimumSize(900, 500)
        self.resize(900, 550)
        
        # Apply centralized dark theme
        self.setStyleSheet(get_main_stylesheet())
        
        self._init_ui(heading, message, icon)
    
    def _init_ui(self, heading: str, message: str, icon: str):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header with icon and heading
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Icon
        icon_label = QLabel(icon)
        icon_font = QFont()
        icon_font.setPointSize(32)
        icon_label.setFont(icon_font)
        header_layout.addWidget(icon_label)
        
        # Heading
        heading_label = QLabel(heading)
        heading_font = QFont()
        heading_font.setBold(True)
        heading_font.setPointSize(16)
        heading_label.setFont(heading_font)
        heading_label.setStyleSheet(get_panel_title_stylesheet())
        heading_label.setWordWrap(True)
        header_layout.addWidget(heading_label, stretch=1)
        
        layout.addLayout(header_layout)
        
        # Message content
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.RichText)
        message_font = QFont()
        message_font.setPointSize(11)
        message_label.setFont(message_font)
        message_label.setStyleSheet("color: #E8EAED; line-height: 1.6;")
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        # OK button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("✓ OK")
        ok_button.setMinimumWidth(120)
        ok_button.setMinimumHeight(40)
        ok_button.setStyleSheet(get_primary_button_stylesheet())
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)


def show_alert(
    parent,
    title: str,
    heading: str,
    message: str,
    icon: str = "⚠️"
):
    """
    Convenience function to show an alert dialog.
    
    Args:
        parent: Parent widget
        title: Window title
        heading: Bold heading text
        message: Main message text (supports HTML)
        icon: Emoji icon (⚠️, ✅, ❌, ℹ️)
    """
    dialog = AlertDialog(title, heading, message, icon, parent)
    dialog.exec_()


def show_warning(parent, title: str, heading: str, message: str):
    """Show a warning alert (yellow triangle icon)."""
    show_alert(parent, title, heading, message, "⚠️")


def show_error(parent, title: str, heading: str, message: str):
    """Show an error alert (red X icon)."""
    show_alert(parent, title, heading, message, "❌")


def show_info(parent, title: str, heading: str, message: str):
    """Show an info alert (blue i icon)."""
    show_alert(parent, title, heading, message, "ℹ️")


def show_success(parent, title: str, heading: str, message: str):
    """Show a success alert (green checkmark icon)."""
    show_alert(parent, title, heading, message, "✅")
