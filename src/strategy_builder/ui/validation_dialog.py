"""
Strategy Validation Dialog - Modal Dialog Wrapper

This dialog wraps the ValidationPanel in a modal window to save screen space.
Opens when user clicks "Validate" from the stepper ribbon.

Author: Strategy Builder Team
Date: 2026-01-17
"""

from typing import Optional
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from src.strategy_builder.ui.validation_panel import ValidationPanel
from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)


class ValidationDialog(QDialog):
    """
    Modal dialog containing the validation panel.
    
    Shows validation results in a separate window to save main UI space.
    """
    
    def __init__(self, orchestrator: StrategyBuilderOrchestrator, parent: Optional['QWidget'] = None):
        """
        Initialize the validation dialog.
        
        Args:
            orchestrator: StrategyBuilderOrchestrator instance
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.validation_panel: Optional[ValidationPanel] = None
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Strategy Validation")
        
        # Make dialog independent and draggable
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        
        # Larger size to fit all content without scrolling
        self.setMinimumSize(1100, 850)
        self.resize(1200, 950)
        
        # Apply dark theme stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #15191E;
            }
            QWidget {
                background-color: #15191E;
                color: #E8EAED;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Add validation panel
        self.validation_panel = ValidationPanel(self.orchestrator)
        layout.addWidget(self.validation_panel)
        
        # Bottom button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                font-weight: bold;
                padding: 10px 24px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect signals from validation panel to dialog."""
        # When save/generate/test buttons clicked, keep dialog open but signal parent
        self.validation_panel.save_requested.connect(self._on_save_requested)
        self.validation_panel.generate_requested.connect(self._on_generate_requested)
        self.validation_panel.run_test_requested.connect(self._on_run_test_requested)
    
    def _on_save_requested(self):
        """Handle save request - close dialog and let parent handle it."""
        # Don't close dialog - user might want to see validation results
        pass
    
    def _on_generate_requested(self):
        """Handle generate request - close dialog and let parent handle it."""
        # Don't close dialog - user might want to see validation results
        pass
    
    def _on_run_test_requested(self):
        """Handle test request - close dialog and let parent handle it."""
        # Don't close dialog - user might want to see validation results
        pass
    
    def showEvent(self, event):
        """
        Called when dialog is shown.
        
        Auto-validate the current strategy when opening.
        """
        super().showEvent(event)
        # Auto-validate when dialog opens
        self.validation_panel.validate_strategy()
