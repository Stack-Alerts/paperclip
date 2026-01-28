"""
Exit Condition Dialog - Configure exit conditions for strategy
Sprint 1.8 Phase 7 - Task 1.8.46

Allows users to configure exit conditions with:
- Percentage-based partial exits (0-100%)
- Exit mode selection (ABSOLUTE/FLEXIBLE)
- FLEXIBLE mode parameters (TP proximity, reversal trigger)
- RECHECK validation support

Author: Strategy Builder Team
Date: 2026-01-27
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QRadioButton, QGroupBox, QCheckBox, QButtonGroup, QComboBox
)
from PyQt5.QtCore import Qt

from src.strategy_builder.ui.styles import (
    get_exit_dialog_stylesheet, get_color, get_primary_button_stylesheet,
    get_secondary_button_stylesheet, get_label_style, get_radio_button_style,
    get_checkbox_style, create_font
)


class ExitConditionDialog(QDialog):
    """
    Dialog for configuring exit conditions.
    
    Features:
    - Percentage input (1-100%)
    - Exit mode: ABSOLUTE or FLEXIBLE
    - FLEXIBLE mode parameters
    - RECHECK enable checkbox
    - Tooltips for all fields
    """
    
    def __init__(
        self,
        signal_name: Optional[str] = None,
        existing_percentage: Optional[float] = None,
        existing_exit_mode: str = "ABSOLUTE",
        existing_tp_proximity: float = 2.0,
        existing_reversal: float = 0.5,
        parent=None
    ):
        """
        Initialize exit condition dialog.
        
        Args:
            signal_name: Name of exit signal (None = show signal selector)
            existing_percentage: Existing percentage (0.0-1.0) if editing
            existing_exit_mode: Existing mode ("ABSOLUTE" or "FLEXIBLE")
            existing_tp_proximity: Existing TP proximity threshold
            existing_reversal: Existing reversal trigger
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.signal_name = signal_name  # May be None - signal selector mode
        self.signal_selector_mode = (signal_name is None)
        self.exit_mode = existing_exit_mode
        
        # Convert percentage from 0.0-1.0 to 1-100 for display
        if existing_percentage is not None:
            self.percentage = int(existing_percentage * 100)
        else:
            self.percentage = 50  # Default 50%
        
        self.tp_proximity_threshold = existing_tp_proximity
        self.reversal_trigger = existing_reversal
        self.recheck_enabled = False
        
        # UI components
        self.signal_selector: Optional[QComboBox] = None
        self.percentage_spin: Optional[QSpinBox] = None
        self.absolute_radio: Optional[QRadioButton] = None
        self.flexible_radio: Optional[QRadioButton] = None
        self.tp_proximity_spin: Optional[QSpinBox] = None
        self.reversal_spin: Optional[QSpinBox] = None
        self.recheck_checkbox: Optional[QCheckBox] = None
        
        self._init_ui()
        self._connect_signals()
        self._load_available_signals()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"Configure Exit Condition: {self.signal_name}")
        self.setStyleSheet(get_exit_dialog_stylesheet())
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        if self.signal_selector_mode:
            title_label = QLabel("🔴 Configure Strategy Exit Condition")
        else:
            title_label = QLabel(f"🔴 EXIT: {self.signal_name}")
        title_font = create_font(size=13, bold=True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {get_color('error')};")
        layout.addWidget(title_label)
        
        # Signal selector (only if signal_name not provided)
        if self.signal_selector_mode:
            signal_group = QGroupBox("Select Exit Signal")
            signal_layout = QVBoxLayout()
            
            signal_row = QHBoxLayout()
            signal_label = QLabel("Signal:")
            signal_label.setStyleSheet(get_label_style('default'))
            signal_label.setToolTip("Choose which signal will trigger the exit condition")
            signal_row.addWidget(signal_label)
            
            self.signal_selector = QComboBox()
            self.signal_selector.setMinimumWidth(300)
            self.signal_selector.setToolTip("Select an exit signal from the building blocks registry")
            signal_row.addWidget(self.signal_selector, stretch=1)
            
            signal_layout.addLayout(signal_row)
            signal_group.setLayout(signal_layout)
            layout.addWidget(signal_group)
        
        # Percentage section
        percentage_group = QGroupBox("Exit Percentage")
        percentage_layout = QVBoxLayout()
        
        percentage_row = QHBoxLayout()
        percentage_label = QLabel("Close % of Position:")
        percentage_label.setStyleSheet(get_label_style('default'))
        percentage_label.setToolTip("Percentage of position to close when signal triggers (1-100%)")
        percentage_row.addWidget(percentage_label)
        
        self.percentage_spin = QSpinBox()
        self.percentage_spin.setRange(1, 100)
        self.percentage_spin.setValue(self.percentage)
        self.percentage_spin.setSuffix("%")
        self.percentage_spin.setToolTip("How much of the position to exit (1-100%)")
        percentage_row.addWidget(self.percentage_spin)
        percentage_row.addStretch()
        
        percentage_layout.addLayout(percentage_row)
        percentage_group.setLayout(percentage_layout)
        layout.addWidget(percentage_group)
        
        # Exit mode section
        mode_group = QGroupBox("Exit Mode")
        mode_layout = QVBoxLayout()
        
        # Create button group for radio buttons
        self.mode_button_group = QButtonGroup()
        
        # ABSOLUTE mode
        self.absolute_radio = QRadioButton("ABSOLUTE - Exit Immediately")
        self.absolute_radio.setStyleSheet(get_radio_button_style('default'))
        self.absolute_radio.setToolTip("Exit position immediately when signal triggers (no TP proximity check)")
        self.mode_button_group.addButton(self.absolute_radio)
        mode_layout.addWidget(self.absolute_radio)
        
        absolute_desc = QLabel("    └─ Executes partial exit as soon as signal fires")
        absolute_desc.setStyleSheet(get_label_style('muted'))
        absolute_desc_font = create_font(size=9)
        absolute_desc.setFont(absolute_desc_font)
        mode_layout.addWidget(absolute_desc)
        
        # FLEXIBLE mode
        self.flexible_radio = QRadioButton("FLEXIBLE - TP-Aware Exit")
        self.flexible_radio.setStyleSheet(get_radio_button_style('info'))
        self.flexible_radio.setToolTip("Check TP proximity before exiting; defer if price heading toward TP")
        self.mode_button_group.addButton(self.flexible_radio)
        mode_layout.addWidget(self.flexible_radio)
        
        flexible_desc = QLabel("    └─ Defers exit if price moving toward TP; fires on reversal")
        flexible_desc.setStyleSheet(get_label_style('muted'))
        flexible_desc_font = create_font(size=9)
        flexible_desc.setFont(flexible_desc_font)
        mode_layout.addWidget(flexible_desc)
        
        # Set initial state
        if self.exit_mode == "ABSOLUTE":
            self.absolute_radio.setChecked(True)
        else:
            self.flexible_radio.setChecked(True)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # FLEXIBLE mode parameters
        self.flexible_params_group = QGroupBox("FLEXIBLE Mode Parameters")
        flexible_params_layout = QVBoxLayout()
        
        # TP Proximity Threshold
        proximity_row = QHBoxLayout()
        proximity_label = QLabel("TP Proximity Threshold:")
        proximity_label.setStyleSheet(get_label_style('default'))
        proximity_label.setToolTip("Distance from TP to consider 'close to TP' (percentage)")
        proximity_row.addWidget(proximity_label)
        
        self.tp_proximity_spin = QSpinBox()
        self.tp_proximity_spin.setRange(1, 10)
        self.tp_proximity_spin.setValue(int(self.tp_proximity_threshold))
        self.tp_proximity_spin.setSuffix("%")
        self.tp_proximity_spin.setToolTip("If price is within this % of TP, consider deferring exit")
        proximity_row.addWidget(self.tp_proximity_spin)
        proximity_row.addStretch()
        
        flexible_params_layout.addLayout(proximity_row)
        
        # Reversal Trigger
        reversal_row = QHBoxLayout()
        reversal_label = QLabel("Reversal Trigger:")
        reversal_label.setStyleSheet(get_label_style('default'))
        reversal_label.setToolTip("Pullback % from peak that triggers deferred exit")
        reversal_row.addWidget(reversal_label)
        
        self.reversal_spin = QSpinBox()
        self.reversal_spin.setRange(1, 10)
        self.reversal_spin.setValue(int(self.reversal_trigger * 10))  # Convert 0.5 to 5
        self.reversal_spin.setSuffix("%")
        self.reversal_spin.setToolTip("If price pulls back this % from peak, execute deferred exit")
        reversal_row.addWidget(self.reversal_spin)
        reversal_row.addStretch()
        
        flexible_params_layout.addLayout(reversal_row)
        
        self.flexible_params_group.setLayout(flexible_params_layout)
        layout.addWidget(self.flexible_params_group)
        
        # Enable/disable FLEXIBLE parameters based on mode
        self.flexible_params_group.setEnabled(self.exit_mode == "FLEXIBLE")
        
        # RECHECK section
        recheck_group = QGroupBox("RECHECK Validation")
        recheck_layout = QVBoxLayout()
        
        self.recheck_checkbox = QCheckBox("Enable RECHECK for this exit condition")
        self.recheck_checkbox.setStyleSheet(get_checkbox_style('default'))
        self.recheck_checkbox.setToolTip("Require signal to be true again after delay before executing exit")
        recheck_layout.addWidget(self.recheck_checkbox)
        
        recheck_note = QLabel("    └─ Configure RECHECK settings after adding exit condition")
        recheck_note.setStyleSheet(get_label_style('muted'))
        recheck_note_font = create_font(size=9)
        recheck_note.setFont(recheck_note_font)
        recheck_layout.addWidget(recheck_note)
        
        recheck_group.setLayout(recheck_layout)
        layout.addWidget(recheck_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(get_secondary_button_stylesheet())
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("Add Exit Condition")
        ok_button.setStyleSheet(get_primary_button_stylesheet())
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self.absolute_radio.toggled.connect(self._on_mode_changed)
        self.flexible_radio.toggled.connect(self._on_mode_changed)
    
    def _on_mode_changed(self, checked):
        """Handle exit mode radio button changes."""
        if self.absolute_radio.isChecked():
            self.exit_mode = "ABSOLUTE"
            self.flexible_params_group.setEnabled(False)
        else:
            self.exit_mode = "FLEXIBLE"
            self.flexible_params_group.setEnabled(True)
    
    def _load_available_signals(self):
        """Load available signals from registry (only in selector mode)."""
        if not self.signal_selector_mode or not self.signal_selector:
            return
        
        try:
            # Get parent to access orchestrator
            parent = self.parent()
            if not parent or not hasattr(parent, 'orchestrator'):
                print("Warning: Cannot access orchestrator from dialog parent")
                return
            
            orchestrator = parent.orchestrator
            
            # Get all blocks from registry
            search_results = orchestrator.search_blocks("")  # Empty = all blocks
            
            # Collect all signals
            signals_set = set()
            for result in search_results:
                block_info = orchestrator.registry_interface.get_block(result.block_name)
                if block_info and block_info.signals:
                    for signal in block_info.signals:
                        # Only add if ui_visible is not explicitly False
                        if getattr(signal, 'ui_visible', True) is not False:
                            signals_set.add(signal.name)
            
            # Sort and populate combo box
            for signal_name in sorted(signals_set):
                self.signal_selector.addItem(signal_name)
            
            if self.signal_selector.count() == 0:
                self.signal_selector.addItem("No signals available")
                self.signal_selector.setEnabled(False)
            
        except Exception as e:
            print(f"Error loading signals: {e}")
            self.signal_selector.addItem("Error loading signals")
            self.signal_selector.setEnabled(False)
    
    def get_config(self) -> dict:
        """
        Get exit condition configuration from dialog.
        
        Returns:
            Dictionary with exit condition settings
        """
        # Get signal name from selector if in selector mode
        if self.signal_selector_mode and self.signal_selector:
            selected_signal = self.signal_selector.currentText()
            if selected_signal and selected_signal not in ["No signals available", "Error loading signals"]:
                self.signal_name = selected_signal
        
        return {
            'signal_name': self.signal_name,
            'percentage': self.percentage_spin.value() / 100.0,  # Convert to 0.0-1.0
            'exit_mode': self.exit_mode,
            'tp_proximity_threshold': float(self.tp_proximity_spin.value()),
            'reversal_trigger': self.reversal_spin.value() / 10.0,  # Convert to 0.0-1.0
            'recheck_enabled': self.recheck_checkbox.isChecked()
        }
