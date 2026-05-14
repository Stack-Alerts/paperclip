"""
Stepper Ribbon - Workflow Progress Component

Shows the 4-step workflow progression in the toolbar:
1. Design Strategy
2. Validate
3. Test / Optimize
4. Publish

Author: Strategy Builder Team
Date: 2026-01-17
"""

from typing import Optional, Set
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont

# Import centralized styles
from src.strategy_builder.ui.styles import get_color


class StepperRibbon(QWidget):
    """
    Stepper ribbon showing workflow progress.
    
    Steps:
    1. Design Strategy
    2. Validate
    3. Test / Optimize
    4. Publish Status
    
    Signals:
        step_clicked(int): Emitted when step is clicked
    """
    
    step_clicked = pyqtSignal(int)
    
    STEPS = [
        {"name": "Design", "icon": "📝", "tooltip": "Design your trading strategy"},
        {"name": "Validate", "icon": "✓", "tooltip": "Validate strategy configuration"},
        {"name": "Test / Optimize", "icon": "🧪", "tooltip": "Run backtest and optimize parameters with Optimizer v3"},
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
        layout.setContentsMargins(0, 0, 0, 0)  # No fixed margin - will be calculated dynamically
        layout.setSpacing(5)
        
        # Create step buttons with arrows
        for idx, step in enumerate(self.STEPS):
            # Step button
            btn = QPushButton(f"{step['icon']} {step['name']}")
            btn.setToolTip(step['tooltip'])
            btn.setMinimumWidth(140)
            btn.setMinimumHeight(36)
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
                from src.strategy_builder.ui.styles import get_color
                arrow.setStyleSheet(f"color: {get_color('text_muted')}; background: transparent;")
                self.arrow_labels.append(arrow)
                layout.addWidget(arrow)
        
        # Add stretch at the END to absorb remaining space (prevents gaps between buttons)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Initial state
        self._update_display()
    
    def showEvent(self, event):
        """Called when widget is shown - recalculate centering."""
        super().showEvent(event)
        # Delay calculation slightly to ensure all widgets are sized
        QTimer.singleShot(100, self._recalculate_centering)
    
    def resizeEvent(self, event):
        """Called when widget or window is resized - recalculate centering."""
        super().resizeEvent(event)
        self._recalculate_centering()
    
    def _recalculate_centering(self):
        """Dynamically calculate left margin to center stepper in window."""
        # Get parent (toolbar) and main window
        toolbar = self.parent()
        if not toolbar:
            return
            
        main_window = toolbar.parent()
        if not main_window:
            return
        
        # Get widths
        window_width = main_window.width()
        
        # Calculate natural stepper width (sum of buttons + arrows + spacing)
        # Don't use sizeHint() as it returns expanded width if widget is expanding
        stepper_width = 0
        for btn in self.step_buttons:
            stepper_width += btn.minimumWidth()  # 140px each
        for arrow in self.arrow_labels:
            stepper_width += arrow.sizeHint().width()  # Arrow width
        # Add spacing between widgets (5px × number of gaps)
        num_widgets = len(self.step_buttons) + len(self.arrow_labels)
        stepper_width += 5 * (num_widgets - 1)  # spacing
        # Add layout margins
        stepper_width += 10  # Small buffer for margins/padding
        
        # Calculate actual toolbar button width (before stepper)
        # Toolbar has New/Open/Save actions + separator before stepper
        toolbar_buttons_width = 0
        for action in toolbar.actions():
            widget = toolbar.widgetForAction(action)
            if widget == self:
                break  # Stop when we reach the stepper
            if widget:
                toolbar_buttons_width += widget.width()
            else:
                # Action button (not widget)
                toolbar_buttons_width += 80  # Approximate action button width
        
        # Calculate left margin to center stepper relative to full window
        # Window center: window_width / 2
        # Stepper center should also be at: window_width / 2
        # Stepper left edge in window = toolbar_buttons_width + left_margin
        # We want: toolbar_buttons_width + left_margin + (stepper_width / 2) = window_width / 2
        # So: left_margin = (window_width / 2) - (stepper_width / 2) - toolbar_buttons_width
        center_pos = (window_width - stepper_width) // 2
        # Adjust toolbar button width for accurate centering (empirically determined)
        adjusted_toolbar_width = int(toolbar_buttons_width * 1.3)
        left_margin = max(0, center_pos - adjusted_toolbar_width)
        
        # Update margin
        layout = self.layout()
        if layout:
            layout.setContentsMargins(left_margin, 0, 0, 0)
    
    def _on_step_clicked(self, step: int):
        """Handle step button click."""
        # Emit signal for parent to handle
        self.step_clicked.emit(step)
    
    def set_current_step(self, step: int):
        """
        Set the current active step.
        
        Args:
            step: Step index (0-3)
        """
        if 0 <= step < len(self.STEPS):
            self.current_step = step
            self._update_display()
    
    def mark_step_complete(self, step: int):
        """
        Mark a step as complete with checkmark.
        
        Args:
            step: Step index (0-3)
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
            step: Step index (0-3)
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
            step: Step index (0-3)
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
    
    def reset_all_steps(self):
        """
        Reset all steps to initial state (alias for reset()).
        
        Clears all completion and error states.
        """
        self.reset()
    
    def _update_display(self):
        """Update the visual display of all steps."""
        try:
            from PyQt5 import sip
        except ImportError:
            sip = None

        for idx, btn in enumerate(self.step_buttons):
            if sip is not None and sip.isdeleted(btn):
                continue

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
                        background-color: #C35252;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #A63F3F;
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-size: 10pt;
                    }
                    QPushButton:hover {
                        background-color: #A63F3F;
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
                        background-color: #204486;
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
