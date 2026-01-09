"""
Strategy Builder - Visual Strategy Creator Dialog

Visual interface for creating strategies by selecting and configuring blocks.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QListWidget, QPushButton,
    QSpinBox, QGroupBox, QMessageBox, QListWidgetItem
)
from PyQt6.QtCore import Qt

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.Strategy_Builder import (
    StrategyRegistry, RegistryBridge, StrategyValidator,
    StrategyConfiguration, BlockSelection, SignalConfiguration
)


class StrategyCreatorDialog(QDialog):
    """Dialog for creating new strategies visually"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.registry = StrategyRegistry()
        self.bridge = RegistryBridge()
        self.validator = StrategyValidator()
        
        # Strategy data
        self.selected_blocks = []  # List of BlockConfiguration
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Create New Strategy")
        self.setGeometry(150, 150, 1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🎨 Visual Strategy Creator")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)
        
        # Strategy info section
        info_group = QGroupBox("Strategy Information")
        info_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., M_Pattern_Reversal")
        info_layout.addRow("Strategy Name:", self.name_edit)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "REVERSAL", "CONTINUATION", "BREAKOUT", "MOMENTUM", 
            "MEAN_REVERSION", "TREND_FOLLOWING", "SCALPING", "SWING"
        ])
        info_layout.addRow("Category:", self.category_combo)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Main content: Two columns
        content_layout = QHBoxLayout()
        
        # Left: Available blocks
        left_group = QGroupBox("📚 Available Blocks")
        left_layout = QVBoxLayout()
        
        # Category filter
        self.block_category_filter = QComboBox()
        self.block_category_filter.addItem("All Categories")
        blocks_by_cat = self.bridge.get_blocks_by_category()
        for category in sorted(blocks_by_cat.keys()):
            self.block_category_filter.addItem(category)
        self.block_category_filter.currentTextChanged.connect(self.load_available_blocks)
        left_layout.addWidget(self.block_category_filter)
        
        self.available_blocks_list = QListWidget()
        self.available_blocks_list.itemDoubleClicked.connect(self.add_block)
        left_layout.addWidget(self.available_blocks_list)
        
        add_btn = QPushButton("➕ Add Selected Block")
        add_btn.clicked.connect(self.add_block)
        left_layout.addWidget(add_btn)
        
        left_group.setLayout(left_layout)
        content_layout.addWidget(left_group)
        
        # Right: Selected blocks
        right_group = QGroupBox("🎯 Strategy Blocks (in order)")
        right_layout = QVBoxLayout()
        
        self.selected_blocks_list = QListWidget()
        self.selected_blocks_list.currentItemChanged.connect(self.on_block_selected)
        right_layout.addWidget(self.selected_blocks_list)
        
        # Block controls
        controls_layout = QHBoxLayout()
        
        remove_btn = QPushButton("🗑 Remove")
        remove_btn.clicked.connect(self.remove_block)
        controls_layout.addWidget(remove_btn)
        
        move_up_btn = QPushButton("⬆ Move Up")
        move_up_btn.clicked.connect(self.move_block_up)
        controls_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("⬇ Move Down")
        move_down_btn.clicked.connect(self.move_block_down)
        controls_layout.addWidget(move_down_btn)
        
        right_layout.addLayout(controls_layout)
        
        # Block configuration
        config_group = QGroupBox("⚙ Block Configuration")
        config_layout = QFormLayout()
        
        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(5, 100)
        self.weight_spin.setValue(20)
        self.weight_spin.valueChanged.connect(self.update_block_weight)
        config_layout.addRow("Weight:", self.weight_spin)
        
        self.signals_list = QListWidget()
        self.signals_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.signals_list.itemSelectionChanged.connect(self.update_block_signals)
        config_layout.addRow("Signals:", self.signals_list)
        
        config_group.setLayout(config_layout)
        right_layout.addWidget(config_group)
        
        # Confluence display
        self.confluence_label = QLabel("Total Confluence: 0 points")
        self.confluence_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #007acc;")
        right_layout.addWidget(self.confluence_label)
        
        right_group.setLayout(right_layout)
        content_layout.addWidget(right_group)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("✓ Validate")
        validate_btn.clicked.connect(self.validate_strategy)
        button_layout.addWidget(validate_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("✅ Create Strategy")
        create_btn.clicked.connect(self.create_strategy)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # Load initial data
        self.load_available_blocks()
        
    def load_available_blocks(self):
        """Load available blocks based on category filter"""
        self.available_blocks_list.clear()
        
        category_filter = self.block_category_filter.currentText()
        blocks_by_cat = self.bridge.get_blocks_by_category()
        
        if category_filter == "All Categories":
            # Show all blocks
            for category, blocks in sorted(blocks_by_cat.items()):
                for block in sorted(blocks, key=lambda b: b.display_name):
                    item = QListWidgetItem(f"{block.display_name} ({category})")
                    item.setData(Qt.ItemDataRole.UserRole, block)
                    self.available_blocks_list.addItem(item)
        else:
            # Show category blocks
            blocks = blocks_by_cat.get(category_filter, [])
            for block in sorted(blocks, key=lambda b: b.display_name):
                item = QListWidgetItem(block.display_name)
                item.setData(Qt.ItemDataRole.UserRole, block)
                self.available_blocks_list.addItem(item)
                
    def add_block(self):
        """Add selected block to strategy"""
        current = self.available_blocks_list.currentItem()
        if not current:
            return
            
        block_info = current.data(Qt.ItemDataRole.UserRole)
        
        # Create block configuration
        block_config = BlockSelection(
            block_name=block_info.name,
            block_display_name=block_info.display_name,
            block_category=block_info.category,
            block_type=block_info.block_type,
            weight=block_info.default_weight,
            weight_range=block_info.weight_range,
            signals=[]
        )
        
        self.selected_blocks.append(block_config)
        
        # Update display to show it has no signals selected yet
        item = QListWidgetItem(f"{block_info.display_name} (Weight: {block_info.default_weight}) [No signals]")
        item.setData(Qt.ItemDataRole.UserRole, (block_config, block_info))
        self.selected_blocks_list.addItem(item)
        
        self.update_confluence()
        
    def remove_block(self):
        """Remove selected block from strategy"""
        current_row = self.selected_blocks_list.currentRow()
        if current_row >= 0:
            self.selected_blocks.pop(current_row)
            self.selected_blocks_list.takeItem(current_row)
            self.update_confluence()
            
    def move_block_up(self):
        """Move block up in list"""
        current_row = self.selected_blocks_list.currentRow()
        if current_row > 0:
            # Swap in data
            self.selected_blocks[current_row], self.selected_blocks[current_row - 1] = \
                self.selected_blocks[current_row - 1], self.selected_blocks[current_row]
            
            # Update display
            item = self.selected_blocks_list.takeItem(current_row)
            self.selected_blocks_list.insertItem(current_row - 1, item)
            self.selected_blocks_list.setCurrentRow(current_row - 1)
            
    def move_block_down(self):
        """Move block down in list"""
        current_row = self.selected_blocks_list.currentRow()
        if current_row >= 0 and current_row < len(self.selected_blocks) - 1:
            # Swap in data
            self.selected_blocks[current_row], self.selected_blocks[current_row + 1] = \
                self.selected_blocks[current_row + 1], self.selected_blocks[current_row]
            
            # Update display
            item = self.selected_blocks_list.takeItem(current_row)
            self.selected_blocks_list.insertItem(current_row + 1, item)
            self.selected_blocks_list.setCurrentRow(current_row + 1)
            
    def on_block_selected(self, current, previous):
        """Handle block selection in strategy list"""
        if not current:
            return
            
        block_config, block_info = current.data(Qt.ItemDataRole.UserRole)
        
        # Update weight
        self.weight_spin.setValue(block_config.weight)
        
        # Load signals
        self.signals_list.clear()
        available_signals = self.bridge.get_signal_options(block_info.name)
        
        for signal in available_signals:
            item = QListWidgetItem(signal.display_name)
            item.setData(Qt.ItemDataRole.UserRole, signal)
            self.signals_list.addItem(item)
            
            # Select if in block config
            if any(s.signal_name == signal.name for s in block_config.signals):
                item.setSelected(True)
                
    def update_block_weight(self, value):
        """Update weight of current block"""
        current_row = self.selected_blocks_list.currentRow()
        if current_row >= 0:
            self.selected_blocks[current_row].weight = value
            
            # Update display
            item = self.selected_blocks_list.currentItem()
            block_config, block_info = item.data(Qt.ItemDataRole.UserRole)
            
            # Update text to show weight and selected signals
            signal_names = [s.signal_name for s in block_config.signals]
            if signal_names:
                signals_str = f" [{', '.join(signal_names[:2])}{'...' if len(signal_names) > 2 else ''}]"
            else:
                signals_str = " [No signals]"
            
            item.setText(f"{block_info.display_name} (Weight: {value}){signals_str}")
            
            self.update_confluence()
            
    def update_block_signals(self):
        """Update signals for currently selected block"""
        current_row = self.selected_blocks_list.currentRow()
        if current_row < 0:
            return
            
        # Get selected signals from list
        selected_signals = []
        for i in range(self.signals_list.count()):
            item = self.signals_list.item(i)
            if item.isSelected():
                signal_info = item.data(Qt.ItemDataRole.UserRole)
                # Create SignalConfiguration
                signal_config = SignalConfiguration(
                    signal_name=signal_info.name,
                    signal_display_name=signal_info.display_name,
                    role='SIGNAL',  # Default role
                    required=True
                )
                selected_signals.append(signal_config)
        
        # Update block configuration
        self.selected_blocks[current_row].signals = selected_signals
        
        # Update display to show selected signals
        item = self.selected_blocks_list.currentItem()
        block_config, block_info = item.data(Qt.ItemDataRole.UserRole)
        
        signal_names = [s.signal_name for s in selected_signals]
        if signal_names:
            signals_str = f" [{', '.join(signal_names[:2])}{'...' if len(signal_names) > 2 else ''}]"
        else:
            signals_str = " [No signals]"
        
        item.setText(f"{block_info.display_name} (Weight: {block_config.weight}){signals_str}")
            
    def update_confluence(self):
        """Calculate and display total confluence"""
        total = sum(block.weight for block in self.selected_blocks)
        self.confluence_label.setText(f"Total Confluence: {total} points")
        
        # Color code
        if total < 60:
            color = "#ce9178"  # Orange - too low
        elif total > 100:
            color = "#f48771"  # Red - too high
        else:
            color = "#4ec9b0"  # Cyan - good
            
        self.confluence_label.setStyleSheet(
            f"font-size: 11pt; font-weight: bold; color: {color};"
        )
        
    def validate_strategy(self):
        """Validate current strategy configuration"""
        # Create temp config
        try:
            config = self._build_config()
            result = self.validator.validate(config)
            
            if result.is_valid:
                QMessageBox.information(
                    self,
                    "Validation Success",
                    "✅ Strategy is VALID!\n\n"
                    f"Blocks: {len(self.selected_blocks)}\n"
                    f"Confluence: {sum(b.weight for b in self.selected_blocks)} points"
                )
            else:
                errors = '\n'.join(f"• {e}" for e in result.errors)
                QMessageBox.warning(
                    self,
                    "Validation Issues",
                    f"⚠️ Issues found:\n\n{errors}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Validation failed:\n{e}")
            
    def _build_config(self):
        """Build StrategyConfiguration from current state"""
        strategy_name = self.name_edit.text().strip()
        if not strategy_name:
            raise ValueError("Strategy name is required")
        
        if not self.selected_blocks:
            raise ValueError("At least one block is required")
        
        # Get next strategy number
        next_num = self.registry.get_next_strategy_number()
        
        # Use first block as main signal
        main_signal = self.selected_blocks[0].block_name
        
        return StrategyConfiguration(
            strategy_name=strategy_name,
            strategy_number=next_num,
            strategy_category=self.category_combo.currentText(),
            main_signal_block=main_signal,
            blocks=self.selected_blocks.copy()
        )
        
    def create_strategy(self):
        """Create and save the strategy"""
        try:
            # Build configuration
            config = self._build_config()
            
            # Validate
            result = self.validator.validate(config)
            if not result.is_valid:
                errors = '\n'.join(f"• {e}" for e in result.errors)
                QMessageBox.critical(
                    self,
                    "Validation Failed",
                    f"Cannot create strategy:\n\n{errors}"
                )
                return
                
            # Save
            strategy_num = self.registry.save_strategy(config)
            
            QMessageBox.information(
                self,
                "Success",
                f"✅ Strategy created!\n\n"
                f"Number: {strategy_num:03d}\n"
                f"Name: {config.strategy_name}\n"
                f"Blocks: {len(config.blocks)}\n"
                f"Confluence: {sum(b.weight for b in config.blocks)} points\n\n"
                "You can now generate files for this strategy."
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create strategy:\n{e}")
