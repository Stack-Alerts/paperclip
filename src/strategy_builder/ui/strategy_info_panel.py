"""
Strategy Information Panel - UI Component for Strategy Builder

This panel displays and manages basic strategy metadata including:
- Strategy name
- Auto-generated description
- Strategy type (Bullish/Bearish)
- Required signals count (auto-calculated)

Author: Strategy Builder Team
Date: 2026-01-16
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QRadioButton, QButtonGroup,
    QGroupBox, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)


class StrategyInfoPanel(QWidget):
    """
    Panel for displaying and editing strategy information.
    
    Signals:
        strategy_name_changed: Emitted when strategy name is modified
        strategy_type_changed: Emitted when strategy type is changed (str: "Bullish" or "Bearish")
    """
    
    strategy_name_changed = pyqtSignal(str)
    strategy_type_changed = pyqtSignal(str)
    
    def __init__(self, orchestrator: StrategyBuilderOrchestrator, parent: Optional[QWidget] = None):
        """
        Initialize the Strategy Information Panel.
        
        Args:
            orchestrator: StrategyBuilderOrchestrator instance for backend communication
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.orchestrator = orchestrator
        
        # UI Components
        self.name_input: Optional[QLineEdit] = None
        self.description_text: Optional[QTextEdit] = None
        self.bullish_radio: Optional[QRadioButton] = None
        self.bearish_radio: Optional[QRadioButton] = None
        self.type_button_group: Optional[QButtonGroup] = None
        self.required_signals_label: Optional[QLabel] = None
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the user interface components."""
        # Main layout - increased spacing
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Group box for all strategy info
        group_box = QGroupBox("Strategy Information")
        group_box_font = QFont()
        group_box_font.setBold(True)
        group_box_font.setPointSize(10)
        group_box.setFont(group_box_font)
        group_box.setStyleSheet("QGroupBox::title { color: #00A3BF; }")  # Muted Cyan for title (25% darker)
        
        group_layout = QVBoxLayout()
        group_layout.setSpacing(18)  # Increased spacing between fields
        
        # Strategy Name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)
        name_label = QLabel("Strategy Name:")
        name_label.setStyleSheet("color: #A0AEC0;")  # Softer label color
        name_label.setToolTip("Enter a unique name for your strategy")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Example_MA_Crossover")
        self.name_input.setMaxLength(100)
        self.name_input.setMinimumHeight(36)  # Bigger input
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        group_layout.addLayout(name_layout)
        
        # Description (Auto-generated) - Now scrollable with word wrap!
        desc_layout = QVBoxLayout()
        desc_layout.setSpacing(8)
        desc_label = QLabel("Description (Auto-generated from blocks):")
        desc_label.setStyleSheet("color: #A0AEC0;")  # Softer label color
        desc_label.setToolTip("Strategy description is auto-generated based on selected blocks and signals")
        self.description_text = QTextEdit()
        self.description_text.setPlaceholderText(
            "Description will be auto-generated when you add building blocks...\n\n"
            "Example:\n"
            "Moving Average crossover with momentum confirmation. "
            "Entry on golden cross with volume confirmation within 5 candles..."
        )
        self.description_text.setMinimumHeight(120)  # Allow scrolling instead of max
        self.description_text.setMaximumHeight(180)  # Cap the max height
        self.description_text.setWordWrapMode(1)  # Enable word wrap (WordWrap mode)
        self.description_text.setLineWrapMode(1)  # Wrap at widget width
        self.description_text.setReadOnly(True)  # Auto-generated, not editable
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.description_text)
        group_layout.addLayout(desc_layout)
        
        # Strategy Type
        type_layout = QHBoxLayout()
        type_label = QLabel("Strategy Type:")
        type_label.setStyleSheet("color: #A0AEC0;")  # Softer label color
        type_label.setToolTip("Select whether this is a bullish or bearish strategy")
        
        self.bullish_radio = QRadioButton("Bullish")
        self.bullish_radio.setStyleSheet("QRadioButton { color: #10B981; background: transparent; }")  # Success green, no background
        self.bullish_radio.setToolTip("Strategy designed for uptrending markets")
        self.bullish_radio.setChecked(True)  # Default to Bullish
        
        self.bearish_radio = QRadioButton("Bearish")
        self.bearish_radio.setStyleSheet("QRadioButton { color: #EF4444; background: transparent; }")  # Error red, no background
        self.bearish_radio.setToolTip("Strategy designed for downtrending markets")
        
        # Button group to ensure only one can be selected
        self.type_button_group = QButtonGroup()
        self.type_button_group.addButton(self.bullish_radio)
        self.type_button_group.addButton(self.bearish_radio)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.bullish_radio)
        type_layout.addWidget(self.bearish_radio)
        type_layout.addStretch()
        group_layout.addLayout(type_layout)
        
        # Required Signals (Auto-calculated)
        signals_layout = QHBoxLayout()
        signals_label = QLabel("Required Signals:")
        signals_label.setStyleSheet("color: #A0AEC0;")  # Softer label color
        signals_label.setToolTip("Number of signals required for strategy entry (auto-calculated)")
        self.required_signals_label = QLabel("0")
        required_signals_font = QFont()
        required_signals_font.setBold(True)
        required_signals_font.setPointSize(11)
        self.required_signals_label.setFont(required_signals_font)
        self.required_signals_label.setStyleSheet("color: #0066cc;")
        
        signals_layout.addWidget(signals_label)
        signals_layout.addWidget(self.required_signals_label)
        signals_layout.addStretch()
        group_layout.addLayout(signals_layout)
        
        # Add horizontal line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        group_layout.addWidget(line)
        
        # Status indicator (for future validation integration)
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Not configured")
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        group_layout.addLayout(status_layout)
        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        # Name input changes
        self.name_input.textChanged.connect(self._on_name_changed)
        
        # Strategy type radio buttons
        self.bullish_radio.toggled.connect(self._on_type_changed)
        self.bearish_radio.toggled.connect(self._on_type_changed)
    
    def _on_name_changed(self, text: str):
        """
        Handle strategy name change.
        
        Args:
            text: New strategy name
        """
        self.strategy_name_changed.emit(text)
        self._update_status()
    
    def _on_type_changed(self):
        """Handle strategy type change."""
        strategy_type = self.get_strategy_type()
        self.strategy_type_changed.emit(strategy_type)
        self._update_status()
    
    def _update_status(self):
        """Update the status indicator based on current configuration."""
        name = self.name_input.text().strip()
        
        if not name:
            self.status_label.setText("Status: Enter strategy name")
            self.status_label.setStyleSheet("color: #ff6600; font-style: italic;")
        else:
            self.status_label.setText("Status: Ready to add blocks")
            self.status_label.setStyleSheet("color: #00aa00; font-style: italic;")
    
    def get_strategy_name(self) -> str:
        """
        Get the current strategy name.
        
        Returns:
            Strategy name string
        """
        return self.name_input.text().strip()
    
    def set_strategy_name(self, name: str):
        """
        Set the strategy name.
        
        Args:
            name: Strategy name to set
        """
        self.name_input.setText(name)
    
    def get_strategy_type(self) -> str:
        """
        Get the current strategy type.
        
        Returns:
            "Bullish" or "Bearish"
        """
        return "Bullish" if self.bullish_radio.isChecked() else "Bearish"
    
    def set_strategy_type(self, strategy_type: str):
        """
        Set the strategy type.
        
        Args:
            strategy_type: "Bullish" or "Bearish"
        """
        if strategy_type.lower() == "bullish":
            self.bullish_radio.setChecked(True)
        elif strategy_type.lower() == "bearish":
            self.bearish_radio.setChecked(True)
    
    def get_description(self) -> str:
        """
        Get the current description.
        
        Returns:
            Description text
        """
        return self.description_text.toPlainText()
    
    def set_description(self, description: str):
        """
        Set the description text.
        
        Args:
            description: Description to set
        """
        self.description_text.setPlainText(description)
    
    def update_description_from_config(self):
        """
        Update description based on current strategy configuration.
        
        This method retrieves the current config from the orchestrator
        and generates a description from the blocks and signals.
        """
        try:
            config = self.orchestrator.get_current_config()
            
            if not config or not config.blocks:
                self.set_description("No blocks added yet...")
                return
            
            # Use the backend's generate_description() method for intelligent description
            if hasattr(self.orchestrator, 'config_engine') and hasattr(self.orchestrator.config_engine, 'generate_description'):
                generated_desc = self.orchestrator.config_engine.generate_description()
                
                # Enhance with additional information
                required_blocks = [b for b in config.blocks if b.logic == 'AND']
                optional_blocks = [b for b in config.blocks if b.logic == 'OR']
                
                # Count total required signals
                total_required_signals = 0
                for block in required_blocks:
                    total_required_signals += sum(1 for s in block.signals if s.logic == 'AND')
                
                # Build enhanced description
                description_lines = []
                description_lines.append(f"Strategy has {len(config.blocks)} block(s) ({len(required_blocks)} required, {len(optional_blocks)} optional).")
                
                if total_required_signals > 0:
                    description_lines.append(f"Total required signals: {total_required_signals}.")
                
                description_lines.append("\n" + generated_desc)
                
                # Add timing constraint info if any
                has_timing = False
                for block in config.blocks:
                    for signal in block.signals:
                        if signal.timing_constraint:
                            has_timing = True
                            break
                    if has_timing:
                        break
                
                if has_timing:
                    description_lines.append("\nIncludes timing constraints between signals.")
                
                self.set_description("\n".join(description_lines))
            else:
                # Fallback to simple description if backend method not available
                description_parts = []
                for block in config.blocks:
                    block_desc = f"- {block.name}"
                    if hasattr(block, 'signals') and block.signals:
                        signal_names = [s.name for s in block.signals[:3]]  # First 3 signals
                        block_desc += f" ({', '.join(signal_names)})"
                        if len(block.signals) > 3:
                            block_desc += f" +{len(block.signals) - 3} more"
                    description_parts.append(block_desc)
                
                if description_parts:
                    generated = "Strategy with:\n" + "\n".join(description_parts)
                    self.set_description(generated)
        except Exception as e:
            # Gracefully handle any errors
            self.set_description(f"Error generating description: {str(e)}")
    
    def get_required_signals(self) -> int:
        """
        Get the current required signals count.
        
        Returns:
            Number of required signals
        """
        return int(self.required_signals_label.text())
    
    def set_required_signals(self, count: int):
        """
        Set the required signals count.
        
        Args:
            count: Number of required signals
        """
        self.required_signals_label.setText(str(count))
        
        # Color code based on count
        if count == 0:
            self.required_signals_label.setStyleSheet("color: #888888;")
        elif count <= 5:
            self.required_signals_label.setStyleSheet("color: #00aa00;")
        elif count <= 10:
            self.required_signals_label.setStyleSheet("color: #0066cc;")
        else:
            self.required_signals_label.setStyleSheet("color: #ff6600;")
    
    def update_required_signals_from_config(self):
        """
        Update required signals count based on current strategy configuration.
        
        Retrieves the count from the orchestrator's current config.
        """
        try:
            config = self.orchestrator.get_current_config()
            
            if config and hasattr(config, 'required_signals'):
                self.set_required_signals(config.required_signals)
            else:
                # Calculate manually from blocks
                total_required = 0
                if config and hasattr(config, 'blocks'):
                    for block in config.blocks:
                        if hasattr(block, 'logic') and block.logic == "AND":
                            # For AND blocks, count all AND signals
                            if hasattr(block, 'signals'):
                                total_required += sum(
                                    1 for s in block.signals 
                                    if hasattr(s, 'logic') and s.logic == "AND"
                                )
                        elif hasattr(block, 'logic') and block.logic == "OR":
                            # For OR blocks, count at least 1
                            if hasattr(block, 'signals') and block.signals:
                                total_required += 1
                
                self.set_required_signals(total_required)
        except Exception as e:
            # Gracefully handle errors
            self.set_required_signals(0)
    
    def refresh_from_orchestrator(self):
        """
        Refresh all fields from the orchestrator's current configuration.
        
        This is called when the strategy configuration changes elsewhere
        in the application.
        """
        self.update_description_from_config()
        self.update_required_signals_from_config()
        self._update_status()
    
    def create_strategy_in_orchestrator(self) -> bool:
        """
        Create/update the strategy in the orchestrator with current panel values.
        
        Returns:
            True if successful, False otherwise
        """
        name = self.get_strategy_name()
        description = self.get_description()
        
        if not name:
            self.status_label.setText("Status: Name required!")
            self.status_label.setStyleSheet("color: #ff0000; font-style: italic;")
            return False
        
        try:
            result = self.orchestrator.create_strategy(name, description)
            
            if result.success:
                self.status_label.setText("Status: Strategy created")
                self.status_label.setStyleSheet("color: #00aa00; font-style: italic;")
                return True
            else:
                error_msg = result.message if hasattr(result, 'message') else "Unknown error"
                self.status_label.setText(f"Status: Error - {error_msg}")
                self.status_label.setStyleSheet("color: #ff0000; font-style: italic;")
                return False
        except Exception as e:
            self.status_label.setText(f"Status: Exception - {str(e)}")
            self.status_label.setStyleSheet("color: #ff0000; font-style: italic;")
            return False
