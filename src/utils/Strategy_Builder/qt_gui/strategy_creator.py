"""
Strategy Builder - Visual Strategy Creator Dialog

Visual interface for creating strategies by selecting and configuring blocks.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QListWidget, QPushButton,
    QSpinBox, QGroupBox, QMessageBox, QListWidgetItem, QWidget
)
from PyQt6.QtCore import Qt

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.Strategy_Builder import (
    StrategyRegistry, RegistryBridge, StrategyValidator,
    StrategyConfiguration, BlockSelection, SignalConfiguration
)
from src.utils.Strategy_Builder.qt_gui.block_library import BlockLibraryPanel


class StrategyCreatorDialog(QDialog):
    """Dialog for creating new strategies visually"""
    
    def __init__(self, parent=None, existing_config=None, on_draft_saved=None):
        # Make window independent for multi-monitor support
        super().__init__(parent, Qt.WindowType.Window)
        self.setModal(False)
        
        self.registry = StrategyRegistry()
        self.bridge = RegistryBridge()
        self.validator = StrategyValidator()
        
        # Callback for when draft is saved
        self.on_draft_saved = on_draft_saved
        
        # Strategy data
        self.selected_blocks = []  # List of BlockConfiguration
        self.existing_config = existing_config  # For editing existing strategies
        self.editing_mode = existing_config is not None
        
        self.init_ui()
        
        # Load existing config if editing
        if self.existing_config:
            self.load_existing_config()
        
    def init_ui(self):
        """Initialize the user interface"""
        title = "Edit Strategy" if self.editing_mode else "Create New Strategy"
        self.setWindowTitle(title)
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
        
        # Left: Available blocks (absolutely zero wasted space!)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Use block library with vertical orientation (side-by-side per user mockup)
        self.block_library = BlockLibraryPanel(orientation='vertical')
        
        # Connect double-click to add block
        self.block_library.tree.itemDoubleClicked.connect(self.add_block_from_tree)
        
        # Add button for explicit addition (more compact)
        add_btn = QPushButton("➕ Add to Strategy")
        add_btn.clicked.connect(self.add_block_from_tree)
        
        left_layout.addWidget(self.block_library, 1)  # stretch=1 to fill space!
        left_layout.addWidget(add_btn, 0)  # stretch=0 for button
        
        content_layout.addWidget(left_widget)
        
        # Right: Selected blocks (absolutely zero wasted space!)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Compact label
        strategy_label = QLabel("🎯 Strategy Blocks")
        strategy_label.setStyleSheet("font-size: 9pt; font-weight: bold; color: #4ec9b0;")
        right_layout.addWidget(strategy_label)
        
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
        
        content_layout.addWidget(right_widget)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("✓ Validate")
        validate_btn.clicked.connect(self.validate_strategy)
        button_layout.addWidget(validate_btn)
        
        button_layout.addStretch()
        
        save_draft_btn = QPushButton("💾 Save Draft")
        save_draft_btn.setToolTip("Save work-in-progress strategy to continue later")
        save_draft_btn.clicked.connect(self.save_draft)
        button_layout.addWidget(save_draft_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("✅ Create Strategy")
        create_btn.clicked.connect(self.create_strategy)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # Don't need to load blocks - BlockLibraryPanel does it automatically
    
    def load_existing_config(self):
        """Load existing configuration into UI"""
        if not self.existing_config:
            return
        
        # Set strategy info
        self.name_edit.setText(self.existing_config.strategy_name)
        self.category_combo.setCurrentText(self.existing_config.strategy_category)
        
        # Load blocks
        self.selected_blocks = self.existing_config.blocks.copy()
        
        # Populate UI
        for block_config in self.selected_blocks:
            # Get block info from registry
            block_metadata = self.bridge.registry.get_block(block_config.block_name)
            if not block_metadata:
                continue
            
            # Create BlockInfo-like object
            from src.utils.Strategy_Builder.models import BlockInfo, BlockType
            block_info = BlockInfo(
                name=block_config.block_name,
                display_name=block_config.block_display_name,
                category=block_config.block_category,
                block_type=block_config.block_type,
                weight_range=block_config.weight_range,
                default_weight=block_config.weight,
                signals=[s.signal_name for s in block_config.signals],
                description=block_metadata.description
            )
            
            # Add to display
            signal_names = [s.signal_name for s in block_config.signals]
            if signal_names:
                signals_str = f" [{', '.join(signal_names[:2])}{'...' if len(signal_names) > 2 else ''}]"
            else:
                signals_str = " [No signals]"
            
            item = QListWidgetItem(f"{block_info.display_name} (Weight: {block_config.weight}){signals_str}")
            item.setData(Qt.ItemDataRole.UserRole, (block_config, block_info))
            self.selected_blocks_list.addItem(item)
        
        self.update_confluence()
        
    def add_block_from_tree(self, item=None):
        """Add selected block from tree view to strategy"""
        # Get selected item from tree
        if not item:
            selected_items = self.block_library.tree.selectedItems()
            if not selected_items:
                return
            item = selected_items[0]
        
        # Skip category items
        if item.parent() is None:
            return
        
        # Get block data
        block_info = item.data(0, Qt.ItemDataRole.UserRole)
        if not block_info:
            return
        
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
        if current_row >= 0 and current_row < len(self.selected_blocks):
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
            
    def _build_config(self, is_draft=False):
        """Build StrategyConfiguration from current state"""
        strategy_name = self.name_edit.text().strip()
        if not strategy_name:
            raise ValueError("Strategy name is required")
        
        # For drafts, allow empty blocks
        if not is_draft and not self.selected_blocks:
            raise ValueError("At least one block is required")
        
        # Use existing number if editing, otherwise get next
        if self.editing_mode and self.existing_config:
            next_num = self.existing_config.strategy_number
        else:
            next_num = self.registry.get_next_strategy_number()
        
        # Use first block as main signal (or placeholder for drafts)
        main_signal = self.selected_blocks[0].block_name if self.selected_blocks else "placeholder"
        
        return StrategyConfiguration(
            strategy_name=strategy_name,
            strategy_number=next_num,
            strategy_category=self.category_combo.currentText(),
            main_signal_block=main_signal,
            blocks=self.selected_blocks.copy()
        )
    
    def save_draft(self):
        """Save strategy as a draft for later editing"""
        try:
            # Build configuration (allow incomplete)
            config = self._build_config(is_draft=True)
            
            # Capture user's input name before registry modifies it
            user_input_name = self.name_edit.text().strip()
            
            # Save with is_draft marker in description
            if not config.description:
                config.description = "[DRAFT] Work in progress"
            elif "[DRAFT]" not in config.description:
                config.description = f"[DRAFT] {config.description}"
            
            # Save without strict validation (overwrite if editing)
            strategy_num = self.registry.save_strategy(
                config, 
                validate=False,
                overwrite=self.editing_mode
            )
            
            # CRITICAL: After save, update existing_config to reflect changes
            # Reload the saved config to get the current state
            self.existing_config = self.registry.load_strategy(strategy_num)
            
            # Switch to edit mode if not already
            if not self.editing_mode:
                self.editing_mode = True
                self.setWindowTitle("Edit Strategy (Draft)")
            
            action = "updated" if strategy_num == config.strategy_number else "saved"
            
            # Call callback to refresh parent window
            if self.on_draft_saved:
                self.on_draft_saved()
            
            QMessageBox.information(
                self,
                f"Draft {action.title()}",
                f"💾 Draft {action}!\n\n"
                f"Number: {strategy_num:03d}\n"
                f"Name: {user_input_name}\n"
                f"Blocks: {len(config.blocks)}\n\n"
                "You can continue editing this draft.\n"
                "Subsequent saves will update this same strategy."
            )
            
            # Don't close dialog - user can continue editing
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save draft:\n{e}")
        
    def create_strategy(self):
        """Create and save the strategy"""
        try:
            # Build configuration
            config = self._build_config()
            
            # Remove [DRAFT] marker if present
            if config.description and "[DRAFT]" in config.description:
                config.description = config.description.replace("[DRAFT] ", "")
            
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
                
            # Save (overwrite if editing)
            strategy_num = self.registry.save_strategy(
                config,
                overwrite=self.editing_mode
            )
            
            action = "updated" if self.editing_mode else "created"
            QMessageBox.information(
                self,
                "Success",
                f"✅ Strategy {action}!\n\n"
                f"Number: {strategy_num:03d}\n"
                f"Name: {config.strategy_name}\n"
                f"Blocks: {len(config.blocks)}\n"
                f"Confluence: {sum(b.weight for b in config.blocks)} points\n\n"
                "You can now generate files for this strategy."
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to {action} strategy:\n{e}")
