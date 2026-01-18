"""
Backtest Configuration Dialog - Modal Window

Wrapper dialog for BacktestConfigPanel that displays as a modal window.

Author: Strategy Builder Team
Date: 2026-01-17
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt

from .backtest_config_panel import BacktestConfigPanel
from .styles import get_main_stylesheet


class BacktestConfigDialog(QDialog):
    """
    Modal dialog for backtest configuration.
    
    Displays the backtest configuration panel in a standalone window.
    """
    
    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Backtest Configuration")
        self.setModal(False)  # Non-modal so user can see strategy
        
        # Set window flags to enable maximize/minimize/close buttons
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        
        # Start fullscreen (like old Universal Optimizer)
        self.showMaximized()
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add backtest panel
        self.backtest_panel = BacktestConfigPanel(self.orchestrator, self)
        layout.addWidget(self.backtest_panel)
        
        self.setLayout(layout)
        
        # Apply centralized dark theme
        self.setStyleSheet(get_main_stylesheet())
