"""
Strategy Blocks Configuration Panel - UI Component for Strategy Builder

This panel displays the added building blocks and allows configuration:
- Display blocks in order with signals
- Reorder blocks (up/down)
- Remove blocks
- Show AND/OR logic
- Configure timing constraints
- Visual feedback
- Integration with orchestrator

Author: Strategy Builder Team
Date: 2026-01-16
"""

from typing import Optional, List, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea, QFrame, QDialog
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.ui.timing_constraint_dialog import TimingConstraintDialog
# Import centralized styles
from src.strategy_builder.ui.styles import (
    get_label_style, get_logic_badge_style, get_primary_button_stylesheet,
    get_danger_button_stylesheet, get_icon_button_style, get_block_label_style
)


class BlockConfigItem(QWidget):
    """
    Custom widget for displaying a configured block with controls.
    """
    
    move_up_clicked = pyqtSignal(str)  # block_name
    move_down_clicked = pyqtSignal(str)  # block_name
    remove_clicked = pyqtSignal(str)  # block_name
    configure_timing_clicked = pyqtSignal(str, str)  # block_name, signal_name
    
    def __init__(self, block_name: str, block_info: dict, position: int, total: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.block_name = block_name
        self.block_info = block_info
        self.position = position
        self.total = total
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI for this block item."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Main header layout
        header_layout = QHBoxLayout()
        
        # Position indicator
        position_label = QLabel(f"#{self.position}")
        position_font = QFont()
        position_font.setBold(True)
        position_font.setPointSize(12)
        position_label.setFont(position_font)
        position_label.setStyleSheet(get_label_style('info') + " min-width: 40px;")
        header_layout.addWidget(position_label)
        
        # Block info layout
        info_layout = QVBoxLayout()
        
        # Block name with AND/OR badge
        name_layout = QHBoxLayout()
        name_layout.setSpacing(10)
        
        name_label = QLabel(f"📊 {self.block_name}")
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(10)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: #E8EAED;")
        name_layout.addWidget(name_label)
        
        # NEW: AND/OR Badge - prominent display
        logic_type = self.block_info.get('logic', 'AND')
        if logic_type == 'AND':
            badge_text = "REQUIRED"
            badge_bg = "#204486"  # Blue for required
            badge_tooltip = "This block is REQUIRED - all signals must trigger"
        else:
            badge_text = "OPTIONAL"
            badge_bg = "#28A745"  # Green for optional
            badge_tooltip = "This block is OPTIONAL - boosts strategy when triggered"
        
        logic_badge = QLabel(badge_text)
        logic_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: white;
                font-weight: bold;
                font-size: 9pt;
                padding: 4px 12px;
                border-radius: 4px;
            }}
        """)
        logic_badge.setToolTip(badge_tooltip)
        logic_badge.setMaximumHeight(24)
        name_layout.addWidget(logic_badge)
        name_layout.addStretch()
        
        info_layout.addLayout(name_layout)
        
        # Signals count
        signals_count = len(self.block_info.get('signals', []))
        signals_label = QLabel(f"Signals: {signals_count}")
        signals_label.setStyleSheet("color: #9AA0A6; font-size: 9pt;")
        info_layout.addWidget(signals_label)
        
        header_layout.addLayout(info_layout, stretch=1)
        
        # Control buttons layout
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(5)
        
        # Move buttons
        move_layout = QHBoxLayout()
        
        self.up_button = QPushButton("▲")
        self.up_button.setMaximumWidth(40)
        self.up_button.setToolTip("Move block up")
        self.up_button.clicked.connect(lambda: self.move_up_clicked.emit(self.block_name))
        self.up_button.setEnabled(self.position > 1)  # Disable if first
        move_layout.addWidget(self.up_button)
        
        self.down_button = QPushButton("▼")
        self.down_button.setMaximumWidth(40)
        self.down_button.setToolTip("Move block down")
        self.down_button.clicked.connect(lambda: self.move_down_clicked.emit(self.block_name))
        self.down_button.setEnabled(self.position < self.total)  # Disable if last
        move_layout.addWidget(self.down_button)
        
        controls_layout.addLayout(move_layout)
        
        # Configure button for blocks #2+ (need reference to previous block)
        if self.position > 1:
            self.configure_block_button = QPushButton("⚙️ Config")
            self.configure_block_button.setMinimumWidth(100)
            self.configure_block_button.setStyleSheet(
                "QPushButton { background-color: #204486; color: white; font-weight: bold; padding: 5px; }"
                "QPushButton:hover { background-color: #1A3A70; }"
            )
            self.configure_block_button.setToolTip("Configure timing constraint for this block")
            # Emit with empty string as signal_name to indicate block-level config
            self.configure_block_button.clicked.connect(lambda: self.configure_timing_clicked.emit(self.block_name, ""))
            controls_layout.addWidget(self.configure_block_button)
        
        # Remove button
        self.remove_button = QPushButton("✕ Remove")
        self.remove_button.setMinimumWidth(100)  # Changed from setMaximumWidth(90)
        self.remove_button.setStyleSheet(
            "QPushButton { background-color: #ff4444; color: white; font-weight: bold; padding: 5px; }"
            "QPushButton:hover { background-color: #cc0000; }"
        )
        self.remove_button.clicked.connect(lambda: self.remove_clicked.emit(self.block_name))
        controls_layout.addWidget(self.remove_button)
        
        header_layout.addLayout(controls_layout)
        
        layout.addLayout(header_layout)
        
        # Signals section - dark theme with timing constraints and dependencies
        if self.block_info.get('signals'):
            signals_widget = QFrame()
            signals_widget.setFrameShape(QFrame.StyledPanel)
            signals_widget.setStyleSheet("background-color: #2A2F3A; border: 1px solid #3C4149; border-radius: 6px; padding: 5px;")
            
            signals_layout = QVBoxLayout()
            signals_layout.setContentsMargins(10, 5, 10, 5)
            
            signals_header = QLabel("Signals:")
            signals_header.setStyleSheet("font-weight: bold; color: #204486;")
            signals_layout.addWidget(signals_header)
            
            for idx, signal in enumerate(self.block_info['signals'], 1):
                signal_name = signal.get('name', 'Unknown')
                signal_logic = signal.get('logic', 'AND')
                timing_constraint = signal.get('timing_constraint')
                
                # Create horizontal layout for signal and configure button
                signal_row_layout = QHBoxLayout()
                signal_row_layout.setSpacing(8)
                
                # Logic indicator color - brighter for dark theme
                logic_color = "#4ADE80" if signal_logic == "AND" else "#60A5FA"
                
                # Check if this signal has dependencies (references previous signals)
                has_dependency = timing_constraint is not None
                
                # Build signal text with dependency arrow if needed
                if has_dependency and idx > 1:
                    # Show dependency arrow for non-first signals
                    signal_text = f"  {idx}. {signal_name} [{signal_logic}] ← depends on previous"
                else:
                    signal_text = f"  {idx}. {signal_name} [{signal_logic}]"
                
                signal_label = QLabel(signal_text)
                signal_label.setStyleSheet(f"color: {logic_color}; font-size: 9pt;")
                
                # Add tooltip with full signal info
                tooltip_parts = [f"Signal: {signal_name}", f"Logic: {signal_logic}"]
                if timing_constraint:
                    ref_signal = timing_constraint.get('reference_signal', 'previous signal')
                    max_candles = timing_constraint.get('max_candles', 'N/A')
                    tooltip_parts.append(f"Timing: Within {max_candles} candles of {ref_signal}")
                signal_label.setToolTip("\n".join(tooltip_parts))
                
                signal_row_layout.addWidget(signal_label, stretch=1)
                
                # Add configure button for signals after the first (need reference signal)
                if idx > 1:
                    configure_btn = QPushButton("⚙️ Configure")
                    configure_btn.setMaximumWidth(90)
                    configure_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #204486;
                            color: white;
                            font-weight: bold;
                            font-size: 8pt;
                            padding: 4px 8px;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #1A3A70;
                        }
                        QPushButton:pressed {
                            background-color: #1550DF;
                        }
                    """)
                    configure_btn.setToolTip("Configure timing constraint for this signal")
                    configure_btn.clicked.connect(
                        lambda checked, sname=signal_name: self.configure_timing_clicked.emit(self.block_name, sname)
                    )
                    signal_row_layout.addWidget(configure_btn)
                
                signals_layout.addLayout(signal_row_layout)
                
                # Display timing constraint as indented sub-item
                if timing_constraint:
                    ref_signal = timing_constraint.get('reference_signal', 'previous signal')
                    max_candles = timing_constraint.get('max_candles', 'N/A')
                    
                    timing_text = f"     └─ within {max_candles} candles of {ref_signal}"
                    timing_label = QLabel(timing_text)
                    timing_label.setStyleSheet("color: #FFA500; font-size: 8pt; font-style: italic;")  # Orange for timing
                    timing_label.setToolTip(f"This signal must occur within {max_candles} candles after {ref_signal}")
                    signals_layout.addWidget(timing_label)
            
            signals_widget.setLayout(signals_layout)
            layout.addWidget(signals_widget)
        
        # Styling - dark theme
        self.setStyleSheet("""
            BlockConfigItem {
                border: 2px solid #204486;
                border-radius: 8px;
                background-color: #1E2128;
            }
        """)
        
        self.setLayout(layout)
    
    def update_position(self, position: int, total: int):
        """Update the position indicators and button states."""
        self.position = position
        self.total = total
        
        # Update button states
        self.up_button.setEnabled(position > 1)
        self.down_button.setEnabled(position < total)


class StrategyBlocksPanel(QWidget):
    """
    Panel for configuring strategy building blocks.
    
    Displays added blocks with reordering and removal capabilities.
    
    Signals:
        blocks_changed: Emitted when blocks are reordered or removed
    """
    
    blocks_changed = pyqtSignal()
    
    def __init__(self, orchestrator: StrategyBuilderOrchestrator, parent: Optional[QWidget] = None):
        """
        Initialize the Strategy Blocks Panel.
        
        Args:
            orchestrator: StrategyBuilderOrchestrator instance
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.orchestrator = orchestrator
        
        # UI Components
        self.blocks_scroll_area: Optional[QScrollArea] = None
        self.blocks_container: Optional[QWidget] = None
        self.blocks_layout: Optional[QVBoxLayout] = None
        self.empty_label: Optional[QLabel] = None
        
        # Block items cache
        self.block_items: List[BlockConfigItem] = []
        
        self._init_ui()
        self._refresh_blocks()
    
    def _init_ui(self):
        """Initialize the user interface components."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Group box
        group_box = QGroupBox("🧩 Strategy Building Blocks")
        
        group_layout = QVBoxLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(15, 20, 15, 15)  # Match backtest panel padding
        
        # Info header
        info_layout = QHBoxLayout()
        info_label = QLabel("ℹ️ Blocks are executed in order from top to bottom")
        info_label.setStyleSheet("color: #0066cc; font-size: 9pt; font-style: italic; padding: 5px;")
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        group_layout.addLayout(info_layout)
        
        # Scroll area for blocks
        self.blocks_scroll_area = QScrollArea()
        self.blocks_scroll_area.setWidgetResizable(True)
        self.blocks_scroll_area.setMinimumHeight(300)
        
        # Container widget for blocks
        self.blocks_container = QWidget()
        self.blocks_layout = QVBoxLayout()
        self.blocks_layout.setSpacing(10)
        self.blocks_layout.setContentsMargins(5, 5, 5, 5)
        
        # Empty state label - dark theme
        self.empty_label = QLabel("No blocks added yet.\n\nSearch and add blocks from the panel above.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #9AA0A6; font-size: 12pt; padding: 50px; "
            "background-color: #1E2128; border: 1px solid #3C4149; border-radius: 8px;"
        )
        self.blocks_layout.addWidget(self.empty_label)
        
        self.blocks_layout.addStretch()
        self.blocks_container.setLayout(self.blocks_layout)
        
        self.blocks_scroll_area.setWidget(self.blocks_container)
        group_layout.addWidget(self.blocks_scroll_area)
        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        
        self.setLayout(layout)
    
    def _refresh_blocks(self):
        """Refresh the display from orchestrator's current configuration."""
        # Clear existing items
        self._clear_blocks()
        
        # Get current config
        config = self.orchestrator.get_current_config()
        
        if not config or not config.blocks:
            # Show empty state
            self.empty_label.setVisible(True)
            return
        
        # Hide empty state
        self.empty_label.setVisible(False)
        
        # Create block items
        total_blocks = len(config.blocks)
        for idx, block_config in enumerate(config.blocks, 1):
            block_info = {
                'name': block_config.name,
                'logic': block_config.logic,
                'signals': []
            }
            
            # Add signal info with timing constraints
            for signal_config in block_config.signals:
                signal_dict = {
                    'name': signal_config.name,
                    'logic': signal_config.logic,
                    'timing_constraint': None
                }
                
                # Add timing constraint data if present
                if signal_config.timing_constraint:
                    signal_dict['timing_constraint'] = {
                        'reference_signal': signal_config.timing_constraint.reference,
                        'max_candles': signal_config.timing_constraint.max_candles
                    }
                
                block_info['signals'].append(signal_dict)
            
            # Create block item widget
            block_item = BlockConfigItem(
                block_config.name,
                block_info,
                idx,
                total_blocks
            )
            
            # Connect signals
            block_item.move_up_clicked.connect(self._on_move_up)
            block_item.move_down_clicked.connect(self._on_move_down)
            block_item.remove_clicked.connect(self._on_remove)
            block_item.configure_timing_clicked.connect(self._on_configure_timing)
            
            # Add to layout (insert before stretch)
            self.blocks_layout.insertWidget(self.blocks_layout.count() - 1, block_item)
            self.block_items.append(block_item)
    
    def _clear_blocks(self):
        """Clear all block items from the display."""
        # Remove all block items
        for block_item in self.block_items:
            self.blocks_layout.removeWidget(block_item)
            block_item.deleteLater()
        
        self.block_items.clear()
    
    def _get_block_level_references(self, block_name: str) -> List[Tuple[str, str]]:
        """
        Get list of available reference signals for block-level timing constraints
.
        
        Args:
            block_name: Current block name
            
        Returns:
            List of (display_name, reference_id) tuples from all previous blocks
        """
        references = []
        config = self.orchestrator.get_current_config()
        
        if not config:
            return references
        
        # Find current block index
        current_block_idx = None
        for block_idx, block in enumerate(config.blocks):
            if block.name == block_name:
                current_block_idx = block_idx
                break
        
        if current_block_idx is None:
            return references
        
        # Add all signals from all previous blocks
        for block_idx in range(current_block_idx):
            block = config.blocks[block_idx]
            for signal in block.signals:
                display_name = f"{block.name} → {signal.name}"
                reference_id = f"{block.name}::{signal.name}"
                references.append((display_name, reference_id))
        
        return references
    
    def _get_available_references(self, block_name: str, signal_name: str) -> List[Tuple[str, str]]:
        """
        Get list of available reference signals for timing constraints.
        
        Args:
            block_name: Current block name
            signal_name: Current signal name
            
        Returns:
            List of (display_name, reference_id) tuples
        """
        references = []
        config = self.orchestrator.get_current_config()
        
        if not config:
            return references
        
        # Find current block and signal
        current_block_idx = None
        current_signal_idx = None
        
        for block_idx, block in enumerate(config.blocks):
            if block.name == block_name:
                current_block_idx = block_idx
                for signal_idx, signal in enumerate(block.signals):
                    if signal.name == signal_name:
                        current_signal_idx = signal_idx
                        break
                break
        
        if current_block_idx is None or current_signal_idx is None:
            return references
        
        # Add all signals from previous blocks
        for block_idx in range(current_block_idx):
            block = config.blocks[block_idx]
            for signal in block.signals:
                display_name = f"{block.name} → {signal.name}"
                reference_id = f"{block.name}::{signal.name}"
                references.append((display_name, reference_id))
        
        # Add previous signals from current block
        current_block = config.blocks[current_block_idx]
        for signal_idx in range(current_signal_idx):
            signal = current_block.signals[signal_idx]
            display_name = f"{block_name} → {signal.name}"
            reference_id = f"{block_name}::{signal.name}"
            references.append((display_name, reference_id))
        
        return references
    
    def _get_current_constraint(self, block_name: str, signal_name: str) -> Optional[dict]:
        """
        Get current timing constraint for a signal.
        
        Args:
            block_name: Block name
            signal_name: Signal name
            
        Returns:
            Constraint dict or None
        """
        config = self.orchestrator.get_current_config()
        
        if not config:
            return None
        
        # Find signal
        for block in config.blocks:
            if block.name == block_name:
                for signal in block.signals:
                    if signal.name == signal_name:
                        if signal.timing_constraint:
                            return {
                                'candles': signal.timing_constraint.max_candles,
                                'reference': signal.timing_constraint.reference,
                                'reference_name': signal.timing_constraint.reference  # TODO: Get display name
                            }
                        return None
        
        return None
    
    def _on_configure_timing(self, block_name: str, signal_name: str):
        """
        Handle configure timing button click.
        
        Args:
            block_name: Block name
            signal_name: Signal name (empty string for block-level timing)
        """
        try:
            # Determine if this is block-level or signal-level timing
            is_block_level = (signal_name == "")
            
            if is_block_level:
                # Block-level timing constraint
                display_name = f"Block: {block_name}"
                # Get references: all signals from all previous blocks
                available_references = self._get_block_level_references(block_name)
            else:
                # Signal-level timing constraint
                display_name = f"Signal: {block_name} → {signal_name}"
                # Get references: previous signals
                available_references = self._get_available_references(block_name, signal_name)
            
            if not available_references:
                print(f"No reference signals available for {display_name}")
                return
            
            # Get current constraint
            current_constraint = self._get_current_constraint(block_name, signal_name)
            
            # Use appropriate display name for dialog
            title_name = "Block Timing" if is_block_level else signal_name
            
            # Create and show dialog
            dialog = TimingConstraintDialog(
                block_name=block_name,
                signal_name=title_name,
                available_references=available_references,
                current_constraint=current_constraint,
                parent=self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Get constraint from dialog
                constraint = dialog.get_constraint()
                
                # For block-level timing, apply constraint to first signal in block
                target_signal_name = signal_name
                if is_block_level:
                    # Get first signal in this block
                    config = self.orchestrator.get_current_config()
                    if config:
                        for block in config.blocks:
                            if block.name == block_name:
                                if block.signals:
                                    target_signal_name = block.signals[0].name
                                    print(f"Block-level timing: Applying to first signal '{target_signal_name}'")
                                break
                
                # Save to orchestrator
                if constraint:
                    result = self.orchestrator.set_signal_timing_constraint(
                        block_name=block_name,
                        signal_name=target_signal_name,
                        constraint=constraint
                    )
                    
                    if result.success:
                        # Refresh display
                        self._refresh_blocks()
                        # Emit changed signal
                        self.blocks_changed.emit()
                        print(f"Timing constraint configured for {block_name}::{signal_name}")
                    else:
                        print(f"Failed to set timing constraint: {result.message}")
                else:
                    # Remove constraint
                    result = self.orchestrator.remove_signal_timing_constraint(
                        block_name=block_name,
                        signal_name=signal_name
                    )
                    
                    if result.success:
                        # Refresh display
                        self._refresh_blocks()
                        # Emit changed signal
                        self.blocks_changed.emit()
                        print(f"Timing constraint removed for {block_name}::{signal_name}")
                    else:
                        print(f"Failed to remove timing constraint: {result.message}")
        
        except Exception as e:
            print(f"Error configuring timing constraint: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_move_up(self, block_name: str):
        """Handle move up button click."""
        try:
            # Call orchestrator to move block up
            result = self.orchestrator.reorder_block(block_name, "up")
            
            if result.success:
                # Refresh display
                self._refresh_blocks()
                # Emit changed signal
                self.blocks_changed.emit()
            else:
                print(f"Failed to move block up: {result.message}")
        except Exception as e:
            print(f"Error moving block up: {e}")
    
    def _on_move_down(self, block_name: str):
        """Handle move down button click."""
        try:
            # Call orchestrator to move block down
            result = self.orchestrator.reorder_block(block_name, "down")
            
            if result.success:
                # Refresh display
                self._refresh_blocks()
                # Emit changed signal
                self.blocks_changed.emit()
            else:
                print(f"Failed to move block down: {result.message}")
        except Exception as e:
            print(f"Error moving block down: {e}")
    
    def _on_remove(self, block_name: str):
        """Handle remove button click."""
        try:
            # Call orchestrator to remove block
            result = self.orchestrator.remove_block(block_name)
            
            if result.success:
                # Refresh display
                self._refresh_blocks()
                # Emit changed signal
                self.blocks_changed.emit()
            else:
                print(f"Failed to remove block: {result.message}")
        except Exception as e:
            print(f"Error removing block: {e}")
    
    def refresh_from_orchestrator(self):
        """Public method to refresh display from orchestrator."""
        self._refresh_blocks()
    
    def add_block(self, block_name: str):
        """
        Add a block to the strategy.
        
        Args:
            block_name: Name of the block to add
            
        Returns:
            bool: True if successful
        """
        try:
            result = self.orchestrator.add_block(block_name)
            
            if result.success:
                self._refresh_blocks()
                self.blocks_changed.emit()
                return True
            else:
                print(f"Failed to add block: {result.message}")
                return False
        except Exception as e:
            print(f"Error adding block: {e}")
            return False
    
    def get_block_count(self) -> int:
        """Get the number of blocks currently configured."""
        return len(self.block_items)
    
    def get_block_names(self) -> List[str]:
        """Get list of configured block names in order."""
        return [item.block_name for item in self.block_items]
