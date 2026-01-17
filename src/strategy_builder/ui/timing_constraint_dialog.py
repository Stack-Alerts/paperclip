"""
Timing Constraint Configuration Dialog

Dialog for configuring timing constraints on signals:
- Within X candles from reference signal
- Reference signal selector
- Dependency configuration

Author: Strategy Builder Team
Date: 2026-01-16
"""

from typing import Optional, List, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class TimingConstraintDialog(QDialog):
    """
    Dialog for configuring timing constraints on signals.
    
    Allows users to specify:
    - Whether a timing constraint is enabled
    - Number of candles for the constraint
    - Reference signal for the constraint
    """
    
    def __init__(self, block_name: str, signal_name: str, 
                 available_references: List[Tuple[str, str]], 
                 current_constraint: Optional[dict] = None,
                 parent=None):
        """
        Initialize the timing constraint dialog.
        
        Args:
            block_name: Name of the current block
            signal_name: Name of the current signal
            available_references: List of (display_name, reference_id) tuples
            current_constraint: Existing constraint dict or None
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Make dialog TRULY movable - use Tool window instead of Dialog
        # This prevents modal locking to parent window
        self.setWindowFlags(
            Qt.Window | 
            Qt.WindowTitleHint | 
            Qt.WindowCloseButtonHint |
            Qt.WindowStaysOnTopHint
        )
        # Still modal for keyboard focus, but not locked visually
        self.setModal(True)
        
        self.block_name = block_name
        self.signal_name = signal_name
        self.available_references = available_references
        self.current_constraint = current_constraint or {}
        
        self.constraint_enabled: Optional[QCheckBox] = None
        self.candles_spinner: Optional[QSpinBox] = None
        self.reference_combo: Optional[QComboBox] = None
        
        self._init_ui()
        self._load_current_values()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"Configure Timing Constraint - {self.signal_name}")
        # Increased size to prevent text compression
        self.setMinimumWidth(700)
        self.setMinimumHeight(450)
        # Set initial size for better appearance
        self.resize(750, 500)
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1E2128;
                color: #E8EAED;
            }
            QLabel {
                color: #E8EAED;
                background: transparent;
            }
            QGroupBox {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                color: #E8EAED;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QSpinBox {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 4px;
                padding: 6px;
                color: #E8EAED;
                min-width: 100px;
            }
            QSpinBox:focus {
                border-color: #2070FF;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3C4149;
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4A5058;
            }
            QComboBox {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 4px;
                padding: 6px;
                color: #E8EAED;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #2070FF;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                selection-background-color: #2070FF;
                color: #E8EAED;
            }
            QCheckBox {
                color: #E8EAED;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #3C4149;
                border-radius: 4px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #4ADE80;
                border-color: #4ADE80;
            }
            QCheckBox::indicator:hover {
                border-color: #4ADE80;
            }
            QPushButton {
                background-color: #2070FF;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
                border: none;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1860EF;
            }
            QPushButton:pressed {
                background-color: #1550DF;
            }
            QPushButton#cancelButton {
                background-color: #555555;
            }
            QPushButton#cancelButton:hover {
                background-color: #666666;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel(f"Configure timing constraint for signal:\n{self.block_name} → {self.signal_name}")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(10)
        header.setFont(header_font)
        header.setStyleSheet("color: #00A3BF; padding: 10px;")
        layout.addWidget(header)
        
        # Constraint configuration group
        config_group = QGroupBox("Timing Constraint Settings")
        config_layout = QFormLayout()
        config_layout.setSpacing(15)
        config_layout.setContentsMargins(15, 20, 15, 15)
        
        # Enable checkbox
        self.constraint_enabled = QCheckBox("Enable timing constraint")
        self.constraint_enabled.setStyleSheet("font-weight: bold; font-size: 10pt;")
        self.constraint_enabled.stateChanged.connect(self._on_enabled_changed)
        config_layout.addRow("", self.constraint_enabled)
        
        # Number of candles
        candles_layout = QHBoxLayout()
        self.candles_spinner = QSpinBox()
        self.candles_spinner.setMinimum(1)
        self.candles_spinner.setMaximum(1000)
        self.candles_spinner.setValue(5)
        self.candles_spinner.setSuffix(" candles")
        candles_layout.addWidget(self.candles_spinner)
        candles_layout.addStretch()
        
        candles_label = QLabel("Maximum candles:")
        candles_label.setToolTip("Maximum number of candles between this signal and the reference signal")
        config_layout.addRow(candles_label, candles_layout)
        
        # Reference signal
        reference_layout = QHBoxLayout()
        self.reference_combo = QComboBox()
        self.reference_combo.setToolTip("Select which signal to measure the timing from")
        
        # Add reference options
        if self.available_references:
            for display_name, reference_id in self.available_references:
                self.reference_combo.addItem(display_name, reference_id)
        else:
            # No references available yet
            self.reference_combo.addItem("(No previous signals)", None)
            self.reference_combo.setEnabled(False)
        
        reference_layout.addWidget(self.reference_combo)
        reference_layout.addStretch()
        
        reference_label = QLabel("Reference signal:")
        reference_label.setToolTip("The signal to measure timing from")
        config_layout.addRow(reference_label, reference_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Example text
        example_group = QGroupBox("Example")
        example_layout = QVBoxLayout()
        example_layout.setContentsMargins(15, 20, 15, 15)
        
        self.example_label = QLabel()
        self.example_label.setWordWrap(True)
        self.example_label.setStyleSheet("color: #9AA0A6; font-style: italic; padding: 5px;")
        self._update_example_text()
        example_layout.addWidget(self.example_label)
        
        example_group.setLayout(example_layout)
        layout.addWidget(example_group)
        
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        buttons_layout.addWidget(ok_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Connect signals for real-time example update
        self.candles_spinner.valueChanged.connect(self._update_example_text)
        self.reference_combo.currentIndexChanged.connect(self._update_example_text)
    
    def _load_current_values(self):
        """Load current constraint values if they exist."""
        if self.current_constraint:
            # Enable checkbox
            self.constraint_enabled.setChecked(True)
            
            # Set candles
            candles = self.current_constraint.get('candles', 5)
            self.candles_spinner.setValue(candles)
            
            # Set reference
            reference_id = self.current_constraint.get('reference', None)
            if reference_id:
                # Find the index of this reference
                for i in range(self.reference_combo.count()):
                    if self.reference_combo.itemData(i) == reference_id:
                        self.reference_combo.setCurrentIndex(i)
                        break
        else:
            # Disable by default
            self.constraint_enabled.setChecked(False)
            self._on_enabled_changed(Qt.Unchecked)
    
    def _on_enabled_changed(self, state):
        """Handle enable/disable of timing constraint."""
        enabled = state == Qt.Checked
        self.candles_spinner.setEnabled(enabled)
        self.reference_combo.setEnabled(enabled and self.reference_combo.count() > 0)
        self._update_example_text()
    
    def _update_example_text(self):
        """Update the example text based on current settings."""
        if not self.constraint_enabled.isChecked():
            self.example_label.setText(
                "No timing constraint. This signal can trigger at any time."
            )
            return
        
        candles = self.candles_spinner.value()
        reference_name = self.reference_combo.currentText()
        
        if reference_name == "(No previous signals)":
            self.example_label.setText(
                "Cannot configure timing constraint without a reference signal."
            )
            return
        
        self.example_label.setText(
            f"This signal must trigger within {candles} candle(s) of '{reference_name}'. "
            f"If more than {candles} candle(s) pass without this signal triggering, "
            f"the entire strategy will reset and start counting from scratch."
        )
    
    def get_constraint(self) -> Optional[dict]:
        """
        Get the configured constraint.
        
        Returns:
            Constraint dict or None if disabled
        """
        if not self.constraint_enabled.isChecked():
            return None
        
        reference_id = self.reference_combo.currentData()
        if reference_id is None:
            return None
        
        return {
            'candles': self.candles_spinner.value(),
            'reference': reference_id,
            'reference_name': self.reference_combo.currentText()
        }
