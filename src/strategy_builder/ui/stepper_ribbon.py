"""
Stepper Ribbon - Workflow Progress Component

Shows the 5-step workflow progression in the toolbar:
1. Design Strategy
2. Validate
3. Generate Code  
4. Test
5. Publish

Author: Strategy Builder Team
Date: 2026-01-17
"""

from typing import Optional, Set
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont


class StepperRibbon(QWidget):
    """
    Stepper ribbon showing workflow progress.
    
    Steps:
    1. Design Strategy
    2. Validate
    3. Generate Code
    4. Test/Backtest
    5. Publish Status
    
    Signals:
        step_clicked(int): Emitted when step is clicked
    """
    
    step_clicked = pyqtSignal(int)
    
    STEPS = [
        {"name": "Design", "icon": "📝", "tooltip": "Design your trading strategy"},
        {"name": "Validate", "icon": "✓", "tooltip": "Validate strategy configuration"},
        {"name": "Generate", "icon": "⚙️", "tooltip": "Generate NautilusTrader code"},
        {"name": "Test", "icon": "🧪", "tooltip": "Run backtest"},
        {"name": "Publish", "icon": "🚀", "tooltip": "Set publish status"}
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the stepper ribbon."""
        super().__init__(parent)
        self.current_step = 0
        self.completed_steps: Set[int] = set()
        self.error_steps: Set[int] = set()
        
        self.step_buttons = []
        self.arrow_labels = []
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # Add stretch before steps (right-align in toolbar)
        layout.addStretch()
        
        # Create step buttons with arrows
        for idx, step in enumerate(self.STEPS):
            # Step button
            btn = QPushButton(f"{step['icon']} {step['name']}")
            btn.setToolTip(step['tooltip'])
            btn.setMinimumWidth(110)
            btn.setMaximumWidth(110)
            btn.setMinimumHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self._on_step_clicked(i))
            
            # Store reference
            self.step_buttons.append(btn)
            layout.addWidget(btn)
            
            # Arrow separator (except after last step)
            if idx < len(self.STEPS) - 1:
                arrow = QLabel("→")
                arrow_font = QFont()
                arrow_font.setPointSize(12)
                arrow_font.setBold(True)
                arrow.setFont(arrow_font)
                arrow.setStyleSheet("color: #4A5568; background: transparent;")
                self.arrow_labels.append(arrow)
                layout.addWidget(arrow)
        
        self.setLayout(layout)
        
        # Initial state
        self._update_display()
    
    def _on_step_clicked(self, step: int):
        """Handle step button click."""
        # Emit signal for parent to handle
        self.step_clicked.emit(step)
    
    def set_current_step(self, step: int):
        """
        Set the current active step.
        
        Args:
            step: Step index (0-4)
        """
        if 0 <= step < len(self.STEPS):
            self.current_step = step
            self._update_display()
    
    def mark_step_complete(self, step: int):
        """
        Mark a step as complete with checkmark.
        
        Args:
            step: Step index (0-4)
        """
        if 0 <= step < len(self.STEPS):
            self.completed_steps.add(step)
            # Remove from errors if it was there
            self.error_steps.discard(step)
            self._update_display()
    
    def mark_step_error(self, step: int):
        """
        Mark a step as having an error.
        
        Args:
            step: Step index (0-4)
        """
        if 0 <= step < len(self.STEPS):
            self.error_steps.add(step)
            # Remove from completed if it was there
            self.completed_steps.discard(step)
            self._update_display()
    
    def clear_step_error(self, step: int):
        """
        Clear error state from a step.
        
        Args:
            step: Step index (0-4)
        """
        if 0 <= step < len(self.STEPS):
            self.error_steps.discard(step)
            self._update_display()
    
    def reset(self):
        """Reset all steps to initial state."""
        self.current_step = 0
        self.completed_steps.clear()
        self.error_steps.clear()
        self._update_display()
    
    def _update_display(self):
        """Update the visual display of all steps."""
        for idx, btn in enumerate(self.step_buttons):
            step = self.STEPS[idx]
            
            # Determine state
            is_current = (idx == self.current_step)
            is_completed = (idx in self.completed_steps)
            is_error = (idx in self.error_steps)
            
            # Build button text
            icon = step['icon']
            if is_completed:
                icon = "✓"
            elif is_error:
                icon = "✗"
            
            btn.setText(f"{icon} {step['name']}")
            
            # Apply styling based on state
            if is_error:
                # Error state - red
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #DC2626;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #991B1B;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 10pt;
                    }
                    QPushButton:hover {
                        background-color: #B91C1C;
                    }
                """)
            elif is_completed:
                # Completed state - green
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #10B981;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #059669;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 10pt;
                    }
                    QPushButton:hover {
                        background-color: #059669;
                    }
                """)
            elif is_current:
                # Active/current state - blue
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2070FF;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #1E40AF;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 10pt;
                    }
                    QPushButton:hover {
                        background-color: #1E40AF;
                    }
                """)
            else:
                # Pending state - gray
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #374151;
                        color: #9CA3AF;
                        font-weight: normal;
                        border: 1px solid #4B5563;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 10pt;
                    }
                    QPushButton:hover {
                        background-color: #4B5563;
                        color: #D1D5DB;
                    }
                """)
