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
from functools import partial
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea, QFrame, QDialog, QScroller
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.ui.timing_constraint_dialog import TimingConstraintDialog
from src.strategy_builder.ui.exit_condition_dialog import ExitConditionDialog
# Import centralized styles
from src.strategy_builder.ui.styles import (
    get_label_style, get_logic_badge_style, get_primary_button_stylesheet,
    get_danger_button_stylesheet, get_icon_button_style, get_block_label_style,
    get_recheck_button_stylesheet, get_recheck_gear_button_stylesheet,
    get_recheck_duplicate_button_stylesheet, get_recheck_remove_button_stylesheet,
    get_spinbox_button_stylesheet, get_success_button_stylesheet, get_color,
    get_dialog_stylesheet, get_radio_container_stylesheet, get_signal_radio_stylesheet,
    get_recheck_radio_stylesheet, get_exit_tree_item_style, get_exit_button_stylesheet
)


class BlockConfigItem(QWidget):
    """
    Custom widget for displaying a configured block with controls.
    """
    
    move_up_clicked = pyqtSignal(str)  # block_name
    move_down_clicked = pyqtSignal(str)  # block_name
    remove_clicked = pyqtSignal(str)  # block_name
    configure_timing_clicked = pyqtSignal(str, str)  # block_name, signal_name
    
    def __init__(
        self,
        block_name: str,
        block_info: dict,
        position: int,
        total: int,
        orchestrator: Optional[StrategyBuilderOrchestrator] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.block_name = block_name
        self.block_info = block_info
        self.position = position
        self.total = total
        self.orchestrator = orchestrator
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI for this block item."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Main header layout
        header_layout = QHBoxLayout()
        
        # Position indicator - Use centralized color from styles.py
        from src.strategy_builder.ui.styles import get_color
        position_label = QLabel(f"#{self.position}")
        position_font = QFont()
        position_font.setBold(True)
        position_font.setPointSize(12)
        position_label.setFont(position_font)
        position_label.setStyleSheet(f"color: {get_color('button_primary')}; font-weight: bold; min-width: 40px;")
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
        name_label.setStyleSheet(get_label_style('default'))
        name_layout.addWidget(name_label)
        
        # NEW: AND/OR Badge - prominent display with centralized styling
        logic_type = self.block_info.get('logic', 'AND')
        if logic_type == 'AND':
            badge_text = "REQUIRED"
            badge_type_style = 'required'
            badge_tooltip = "This block is REQUIRED - all signals must trigger"
        else:
            badge_text = "OPTIONAL"
            badge_type_style = 'optional'
            badge_tooltip = "This block is OPTIONAL - boosts strategy when triggered"
        
        logic_badge = QLabel(badge_text)
        logic_badge.setStyleSheet(get_logic_badge_style(badge_type_style))
        logic_badge.setToolTip(badge_tooltip)
        # Set size policy to prevent expansion
        from PyQt5.QtWidgets import QSizePolicy
        logic_badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        name_layout.addWidget(logic_badge)
        name_layout.addStretch()
        
        info_layout.addLayout(name_layout)
        
        # Signals count
        signals_count = len(self.block_info.get('signals', []))
        signals_label = QLabel(f"Signals: {signals_count}")
        signals_label.setStyleSheet(get_label_style('muted') + " font-size: 9pt;")
        info_layout.addWidget(signals_label)
        
        header_layout.addLayout(info_layout, stretch=1)
        
        # Control buttons layout
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(5)

        # Move buttons - aligned to the right
        move_layout = QHBoxLayout()
        move_layout.addStretch()  # Push buttons to the right

        self.up_button = QPushButton("▴")  # Sharp small triangle up
        self.up_button.setMaximumWidth(40)
        self.up_button.setStyleSheet("font-size: 18px; font-weight: bold;")  # Bigger triangle
        self.up_button.setToolTip("Move block up")
        self.up_button.clicked.connect(lambda: self.move_up_clicked.emit(self.block_name))
        self.up_button.setEnabled(self.position > 1)  # Disable if first
        move_layout.addWidget(self.up_button)

        self.down_button = QPushButton("▾")  # Sharp small triangle down
        self.down_button.setMaximumWidth(40)
        self.down_button.setStyleSheet("font-size: 18px; font-weight: bold;")  # Bigger triangle
        self.down_button.setToolTip("Move block down")
        self.down_button.clicked.connect(lambda: self.move_down_clicked.emit(self.block_name))
        self.down_button.setEnabled(self.position < self.total)  # Disable if last
        move_layout.addWidget(self.down_button)

        controls_layout.addLayout(move_layout)
        
        # Configure button for blocks #2+ (need reference to previous block)
        if self.position > 1:
            self.configure_block_button = QPushButton("⚙️ Config")
            self.configure_block_button.setMinimumWidth(100)
            self.configure_block_button.setStyleSheet(get_primary_button_stylesheet())
            self.configure_block_button.setToolTip("Configure timing constraint for this block")
            # Emit with empty string as signal_name to indicate block-level config
            self.configure_block_button.clicked.connect(lambda: self.configure_timing_clicked.emit(self.block_name, ""))
            controls_layout.addWidget(self.configure_block_button)
        
        # Remove button
        self.remove_button = QPushButton("✕ Remove")
        self.remove_button.setMinimumWidth(100)  # Changed from setMaximumWidth(90)
        self.remove_button.setStyleSheet(get_danger_button_stylesheet())
        self.remove_button.clicked.connect(lambda: self.remove_clicked.emit(self.block_name))
        controls_layout.addWidget(self.remove_button)
        
        header_layout.addLayout(controls_layout)
        
        layout.addLayout(header_layout)
        
        # Signals section - dark theme with timing constraints and dependencies
        if self.block_info.get('signals'):
            signals_widget = QFrame()
            signals_widget.setFrameShape(QFrame.StyledPanel)
            from src.strategy_builder.ui.styles import get_color
            signals_widget.setStyleSheet(f"background-color: {get_color('bg_light')}; border: 1px solid {get_color('border')}; border-radius: 6px; padding: 5px;")
            
            signals_layout = QVBoxLayout()
            signals_layout.setContentsMargins(10, 5, 10, 5)
            
            signals_header = QLabel("Signals:")
            signals_header.setStyleSheet(get_label_style('info') + " font-weight: bold;")
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
                
                # Add "Recheck On Delayed Candles" button - hide if recheck already configured
                if not signal.get('recheck_config') or not signal['recheck_config'].get('enabled'):
                    recheck_btn = QPushButton("Recheck On Delayed Candles")
                    recheck_btn.setMinimumWidth(180)
                    recheck_btn.setMinimumHeight(28)
                    recheck_btn.setStyleSheet(get_recheck_button_stylesheet())
                    recheck_btn.setToolTip("Require this signal to reoccur within specified bars for validation")
                    recheck_btn.clicked.connect(
                        lambda checked, sname=signal_name: self._on_recheck_clicked(sname)
                    )
                    signal_row_layout.addWidget(recheck_btn)
                
                # Add configure button for signals after the first (need reference signal)
                if idx > 1:
                    configure_btn = QPushButton("⚙️ Config")
                    configure_btn.setMinimumWidth(90)
                    configure_btn.setMinimumHeight(28)
                    configure_btn.setStyleSheet(get_primary_button_stylesheet())
                    configure_btn.setToolTip("Configure timing constraint for this signal")
                    configure_btn.clicked.connect(
                        lambda checked, sname=signal_name: self.configure_timing_clicked.emit(self.block_name, sname)
                    )
                    signal_row_layout.addWidget(configure_btn)
                
                signals_layout.addLayout(signal_row_layout)
                
                # Hierarchical display of timing constraints and RECHECKs
                # Level 1: Timing Constraint (if exists)
                if timing_constraint:
                    ref_signal = timing_constraint.get('reference_signal', 'previous signal')
                    max_candles = timing_constraint.get('max_candles', 'N/A')
                    
                    timing_text = f"     └── TIME CONSTRAINT"
                    timing_detail = f"          └── Within {max_candles} candles of {ref_signal}"
                    timing_label = QLabel(timing_text)
                    timing_detail_label = QLabel(timing_detail)
                    timing_label.setStyleSheet(get_label_style('warning') + " font-size: 9pt; font-weight: bold;")
                    timing_detail_label.setStyleSheet(get_label_style('warning') + " font-size: 9pt;")
                    timing_label.setToolTip(f"This signal must occur within {max_candles} candles after {ref_signal}")
                    signals_layout.addWidget(timing_label)
                    signals_layout.addWidget(timing_detail_label)
                
                # Level 2: RECHECK configuration (if exists)
                if signal.get('recheck_config'):
                    recheck_cfg = signal['recheck_config']
                    if recheck_cfg.get('enabled'):
                        bar_delay = recheck_cfg.get('bar_delay', 0)
                        
                        # Determine indentation based on whether timing constraint exists
                        indent = "          " if timing_constraint else "     "
                        
                        # Create recheck row with input and buttons
                        recheck_row_layout = QHBoxLayout()
                        recheck_row_layout.setSpacing(8)
                        
                        recheck_text = f"{indent}└── RECHECK ({bar_delay} bars)"
                        recheck_label = QLabel(recheck_text)
                        recheck_label.setStyleSheet(get_label_style('success') + " font-size: 9pt; font-weight: bold;")
                        recheck_label.setToolTip(f"This signal must reoccur within {bar_delay} bars for validation")
                        recheck_row_layout.addWidget(recheck_label, stretch=1)
                        
                        # Gear icon button for RECHECK configuration
                        gear_btn = QPushButton("⚙")
                        gear_btn.setStyleSheet(get_recheck_gear_button_stylesheet())
                        gear_btn.setToolTip("Configure RECHECK validation")
                        gear_btn.clicked.connect(
                            lambda checked, sname=signal_name: self._on_recheck_config_clicked(sname)
                        )
                        recheck_row_layout.addWidget(gear_btn)
                        
                        # Duplicate button for nested RECHECK
                        duplicate_btn = QPushButton("⎘")
                        duplicate_btn.setStyleSheet(get_recheck_duplicate_button_stylesheet())
                        duplicate_btn.setToolTip("Add nested RECHECK validation")
                        duplicate_btn.clicked.connect(
                            lambda checked, sname=signal_name: self._on_recheck_duplicate_clicked(sname)
                        )
                        recheck_row_layout.addWidget(duplicate_btn)
                        
                        # Remove recheck button
                        remove_recheck_btn = QPushButton("✕")
                        remove_recheck_btn.setStyleSheet(get_recheck_remove_button_stylesheet())
                        remove_recheck_btn.setToolTip("Remove recheck validation")
                        remove_recheck_btn.clicked.connect(
                            lambda checked, sname=signal_name: self._on_remove_recheck(sname)
                        )
                        recheck_row_layout.addWidget(remove_recheck_btn)
                        
                        signals_layout.addLayout(recheck_row_layout)
                        
                        # Level 3: Nested RECHECKs (if exist)
                        if signal.get('recheck_chain'):
                            for chain_idx, nested_recheck in enumerate(signal['recheck_chain'], 1):
                                if nested_recheck.get('enabled'):
                                    nested_delay = nested_recheck.get('bar_delay', 0)
                                    validation_mode = nested_recheck.get('validation_mode', 'SIGNAL')
                                    
                                    # Create nested recheck row
                                    nested_row_layout = QHBoxLayout()
                                    nested_row_layout.setSpacing(8)
                                    
                                    # Determine validation target description and indentation
                                    if validation_mode == "SIGNAL":
                                        # RECHECKs of Signal are at the same level as the first RECHECK (siblings)
                                        nested_indent = "          " if timing_constraint else "     "
                                        target_desc = "of Signal"
                                    else:
                                        # RECHECKs of RECHECK are nested deeper (children of previous RECHECK)
                                        nested_indent = "               " if timing_constraint else "          "
                                        target_desc = "of RECHECK"
                                    
                                    nested_text = f"{nested_indent}└── RECHECK {target_desc} ({nested_delay} bars)"
                                    nested_label = QLabel(nested_text)
                                    nested_label.setStyleSheet(get_label_style('info') + " font-size: 9pt;")
                                    nested_label.setToolTip(
                                        f"Nested RECHECK validation\n"
                                        f"Validates against: {'Original Signal' if validation_mode == 'SIGNAL' else 'Previous RECHECK'}\n"
                                        f"Bar delay: {nested_delay}"
                                    )
                                    nested_row_layout.addWidget(nested_label, stretch=1)
                                    
                                    signals_layout.addLayout(nested_row_layout)
                
                # Level 4: Exit Conditions (Sprint 1.8 Task 1.8.48) - after RECHECK chains
                if signal.get('exit_conditions'):
                    for exit_cond in signal['exit_conditions']:
                        current_exit_signal_name = exit_cond.get('signal_name', 'Unknown')
                        exit_percentage = exit_cond.get('percentage', 0.5)
                        exit_mode = exit_cond.get('exit_mode', 'ABSOLUTE')
                        
                        # Determine indentation based on whether timing constraint and recheck exist
                        if signal.get('recheck_config') and signal['recheck_config'].get('enabled'):
                            # Has RECHECK - indent further
                            if timing_constraint:
                                exit_indent = "               "
                            else:
                                exit_indent = "          "
                        elif timing_constraint:
                            # Has timing constraint but no RECHECK
                            exit_indent = "          "
                        else:
                            # No timing constraint or RECHECK
                            exit_indent = "     "
                        
                        # Format percentage for display (0.5 -> 50%)
                        pct_display = int(exit_percentage * 100)
                        
                        # Create exit condition row
                        exit_row_layout = QHBoxLayout()
                        exit_row_layout.setSpacing(8)
                        
                        exit_text = f"{exit_indent}└── 🔴 EXIT: {current_exit_signal_name} ({pct_display}%)"
                        exit_label = QLabel(exit_text)
                        exit_label.setStyleSheet(get_exit_tree_item_style() + " font-size: 9pt;")
                        exit_label.setToolTip(
                            f"Signal-Level Exit Condition\n"
                            f"Signal: {current_exit_signal_name}\n"
                            f"Percentage: {pct_display}%\n"
                            f"Mode: {exit_mode}\n"
                            f"Binding: SIGNAL"
                        )
                        exit_row_layout.addWidget(exit_label, stretch=1)
                        
                        # Config button - same style as other exits
                        exit_config_btn = QPushButton("⚙")
                        exit_config_btn.setStyleSheet(get_recheck_gear_button_stylesheet())
                        exit_config_btn.setToolTip("Configure signal exit condition")
                        exit_config_btn.clicked.connect(
                            lambda checked, bname=self.block_name, sname=signal_name, esig=current_exit_signal_name:
                                self._on_signal_exit_config_clicked(bname, sname, esig)
                        )
                        exit_row_layout.addWidget(exit_config_btn)
                        
                        # Duplicate button - add another exit to this signal
                        exit_duplicate_btn = QPushButton("⎘")
                        exit_duplicate_btn.setStyleSheet(get_recheck_duplicate_button_stylesheet())
                        exit_duplicate_btn.setToolTip("Add another exit condition to this signal")
                        exit_duplicate_btn.clicked.connect(
                            lambda checked, bname=self.block_name, sname=signal_name:
                                self._on_signal_exit_duplicate_clicked(bname, sname)
                        )
                        exit_row_layout.addWidget(exit_duplicate_btn)
                        
                        # Remove button - remove this exit
                        exit_remove_btn = QPushButton("✕")
                        exit_remove_btn.setStyleSheet(get_recheck_remove_button_stylesheet())
                        exit_remove_btn.setToolTip("Remove this signal exit condition")
                        exit_remove_btn.clicked.connect(
                            lambda checked, bname=self.block_name, sname=signal_name, esig=current_exit_signal_name:
                                self._on_signal_exit_remove_clicked(bname, sname, esig)
                        )
                        exit_row_layout.addWidget(exit_remove_btn)
                        
                        signals_layout.addLayout(exit_row_layout)
            
            signals_widget.setLayout(signals_layout)
            layout.addWidget(signals_widget)
        
        # Block-level exit conditions (Sprint 1.8 - display exits bound to this block)
        if hasattr(self.block_info, 'exit_conditions') or (isinstance(self.block_info, dict) and 'exit_conditions' in self.block_info):
            # Get exit conditions for this block
            exit_conditions = self.block_info.get('exit_conditions', []) if isinstance(self.block_info, dict) else getattr(self.block_info, 'exit_conditions', [])
            
            if exit_conditions:
                # Create frame for block-level exits
                block_exits_widget = QFrame()
                block_exits_widget.setFrameShape(QFrame.StyledPanel)
                from src.strategy_builder.ui.styles import get_color
                block_exits_widget.setStyleSheet(
                    f"background-color: {get_color('bg_light')}; "
                    f"border: 1px solid {get_color('border')}; "
                    f"border-radius: 6px; padding: 5px;"
                )
                
                block_exits_layout = QVBoxLayout()
                block_exits_layout.setContentsMargins(10, 5, 10, 5)
                
                # Header
                exits_header = QLabel("Block-Level Exit Conditions:")
                exits_header.setStyleSheet(get_label_style('error') + " font-weight: bold;")
                block_exits_layout.addWidget(exits_header)
                
                # Display each exit
                for exit_cond in exit_conditions:
                    current_exit_signal_name = exit_cond.get('signal_name', 'Unknown')
                    exit_percentage = exit_cond.get('percentage', 0.5)
                    exit_mode = exit_cond.get('exit_mode', 'ABSOLUTE')
                    
                    pct_display = int(exit_percentage * 100)
                    
                    # Create exit row
                    exit_row_layout = QHBoxLayout()
                    exit_row_layout.setSpacing(8)
                    
                    exit_text = f"🔴  {current_exit_signal_name} ({pct_display}%) - {exit_mode} mode"
                    exit_label = QLabel(exit_text)
                    exit_label.setStyleSheet(get_exit_tree_item_style() + " font-size: 9pt;")  # Removed bold
                    exit_label.setToolTip(
                        f"Block-Level Exit Condition\n"
                        f"Signal: {current_exit_signal_name}\n"
                        f"Percentage: {pct_display}%\n"
                        f"Mode: {exit_mode}\n"
                        f"Binding: BLOCK"
                    )
                    exit_row_layout.addWidget(exit_label, stretch=1)
                    
                    # Config/Edit button - same style as strategy exit buttons
                    config_btn = QPushButton("⚙")
                    config_btn.setStyleSheet(get_recheck_gear_button_stylesheet())
                    config_btn.setToolTip("Configure block exit condition")
                    # Use lambda to call panel method with captured variables
                    config_btn.clicked.connect(
                        lambda checked, bname=self.block_name, sname=current_exit_signal_name: 
                            self._on_block_exit_config_clicked(bname, sname)
                    )
                    exit_row_layout.addWidget(config_btn)
                    
                    # Duplicate button - add another exit to this block
                    duplicate_btn = QPushButton("⎘")
                    duplicate_btn.setStyleSheet(get_recheck_duplicate_button_stylesheet())
                    duplicate_btn.setToolTip("Add another exit condition to this block")
                    duplicate_btn.clicked.connect(
                        lambda checked, bname=self.block_name:
                            self._on_duplicate_block_exit_clicked(bname)
                    )
                    exit_row_layout.addWidget(duplicate_btn)
                    
                    # Remove button - same style as strategy exit buttons
                    remove_btn = QPushButton("✕")
                    remove_btn.setStyleSheet(get_recheck_remove_button_stylesheet())
                    remove_btn.setToolTip("Remove this block exit condition")
                    # Use lambda to call panel method with captured variables
                    remove_btn.clicked.connect(
                        lambda checked, bname=self.block_name, sname=current_exit_signal_name:
                            self._on_block_exit_remove_clicked(bname, sname)
                    )
                    exit_row_layout.addWidget(remove_btn)
                    
                    block_exits_layout.addLayout(exit_row_layout)
                
                block_exits_widget.setLayout(block_exits_layout)
                layout.addWidget(block_exits_widget)
        
        # Styling - dark theme
        from src.strategy_builder.ui.styles import get_color
        self.setStyleSheet(f"""
            BlockConfigItem {{
                border: 2px solid {get_color('button_primary')};
                border-radius: 8px;
                background-color: {get_color('bg_medium')};
            }}
        """)
        
        self.setLayout(layout)
    
    def _on_recheck_clicked(self, signal_name: str):
        """Handle recheck button click - show dialog to configure bar delay."""
        from PyQt5.QtWidgets import QInputDialog
        
        # Show input dialog for bar delay
        bar_delay, ok = QInputDialog.getInt(
            self,
            "Configure Recheck Validation",
            f"Signal: {signal_name}\n\nEnter number of bars within which signal must reoccur for validation:",
            value=25,  # Default value
            min=1,
            max=500,
            step=1
        )
        
        if ok and bar_delay > 0:
            # Find the StrategyBlocksPanel (traverse up the widget tree)
            panel = self._find_strategy_blocks_panel()
            if panel and hasattr(panel, '_on_signal_recheck_configured'):
                panel._on_signal_recheck_configured(self.block_name, signal_name, bar_delay)
    
    def _on_recheck_config_clicked(self, signal_name: str):
        """Handle recheck gear icon click - show configuration dialog."""
        from PyQt5.QtWidgets import QInputDialog
        
        # Get current config
        config = self.orchestrator.get_current_config()
        if not config:
            return
            
        # Find current recheck config
        current_delay = 25  # Default value
        for block in config.blocks:
            if block.name == self.block_name:
                for signal in block.signals:
                    if signal.name == signal_name and signal.recheck_config:
                        current_delay = signal.recheck_config.bar_delay
                        break
                break
        
        # Show input dialog for bar delay
        bar_delay, ok = QInputDialog.getInt(
            self,
            "Configure RECHECK Validation",
            f"Signal: {signal_name}\n\nEnter number of bars within which signal must reoccur for validation:",
            value=current_delay,
            min=1,
            max=500,
            step=1
        )
        
        if ok and bar_delay > 0:
            # Find the StrategyBlocksPanel
            panel = self._find_strategy_blocks_panel()
            if panel and hasattr(panel, '_on_signal_recheck_configured'):
                panel._on_signal_recheck_configured(self.block_name, signal_name, bar_delay)
    
    def _on_recheck_duplicate_clicked(self, signal_name: str):
        """Handle recheck duplicate button click - show nested recheck dialog."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QSpinBox, QPushButton, QLabel, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Nested RECHECK")
        dialog.setStyleSheet(get_dialog_stylesheet())
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add description with styling
        desc = QLabel(
            f"Configure nested RECHECK validation for {signal_name}.\n"
            "Choose what to validate against and specify the bar delay."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(get_label_style('info'))
        desc.setMinimumHeight(50)
        layout.addWidget(desc)
        
        # Add spacing
        layout.addSpacing(10)
        
        # Add validation target selection
        target_label = QLabel("Validate Against:")
        target_label.setStyleSheet(get_label_style('info') + " font-weight: bold;")
        layout.addWidget(target_label)
        
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QFrame
        
        # Create radio button container with background
        radio_container = QFrame()
        radio_container.setStyleSheet(get_radio_container_stylesheet())
        radio_layout = QVBoxLayout()
        radio_layout.setSpacing(10)
        
        # Create button group for mutual exclusion
        target_group = QButtonGroup(dialog)
        
        # Signal radio with green accent
        signal_radio = QRadioButton("Original Signal")
        signal_radio.setStyleSheet(get_signal_radio_stylesheet())
        signal_radio.setChecked(True)
        target_group.addButton(signal_radio)
        radio_layout.addWidget(signal_radio)
        
        # RECHECK radio with blue accent
        recheck_radio = QRadioButton("Previous RECHECK")
        recheck_radio.setStyleSheet(get_recheck_radio_stylesheet())
        target_group.addButton(recheck_radio)
        radio_layout.addWidget(recheck_radio)
        
        radio_container.setLayout(radio_layout)
        layout.addWidget(radio_container)
        
        # Add spacing
        layout.addSpacing(10)
        
        # Add bar delay input with styling
        delay_label = QLabel("Bar Delay:")
        delay_label.setStyleSheet(get_label_style('info') + " font-weight: bold;")
        layout.addWidget(delay_label)
        
        delay_input = QSpinBox()
        delay_input.setRange(1, 500)
        delay_input.setValue(25)
        delay_input.setStyleSheet(get_spinbox_button_stylesheet())
        layout.addWidget(delay_input)
        
        # Add spacing
        layout.addSpacing(15)
        
        # Add dialog buttons with custom styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(get_danger_button_stylesheet())
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(get_success_button_stylesheet())
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Process the nested recheck configuration
            validate_against = "SIGNAL" if signal_radio.isChecked() else "RECHECK"
            bar_delay = delay_input.value()
            
            # Find the StrategyBlocksPanel
            panel = self._find_strategy_blocks_panel()
            if panel and hasattr(panel, '_on_nested_recheck_configured'):
                panel._on_nested_recheck_configured(
                    self.block_name,
                    signal_name,
                    validate_against,
                    bar_delay
                )
    
    def _on_remove_recheck(self, signal_name: str):
        """Handle remove recheck button click."""
        # Find the StrategyBlocksPanel (traverse up the widget tree)
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_signal_recheck_removed'):
            panel._on_signal_recheck_removed(self.block_name, signal_name)
    
    def _on_block_exit_config_clicked(self, block_name: str, signal_name: str):
        """Handle config button for block-level exit - forward to panel."""
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_edit_block_exit'):
            panel._on_edit_block_exit(block_name, signal_name)
    
    def _on_block_exit_remove_clicked(self, block_name: str, signal_name: str):
        """Handle remove button for block-level exit - forward to panel."""
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_remove_block_exit'):
            panel._on_remove_block_exit(block_name, signal_name)
    
    def _on_duplicate_block_exit_clicked(self, block_name: str):
        """Handle duplicate button for block-level exit - forward to panel."""
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_duplicate_block_exit'):
            panel._on_duplicate_block_exit(block_name)
    
    def _on_signal_exit_config_clicked(self, block_name: str, signal_name: str, exit_signal_name: str):
        """Handle config button for signal-level exit - forward to panel."""
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_signal_exit_config_clicked'):
            panel._on_signal_exit_config_clicked(block_name, signal_name, exit_signal_name)
    
    def _on_signal_exit_duplicate_clicked(self, block_name: str, signal_name: str):
        """Handle duplicate button for signal-level exit - forward to panel."""
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_signal_exit_duplicate_clicked'):
            panel._on_signal_exit_duplicate_clicked(block_name, signal_name)
    
    def _on_signal_exit_remove_clicked(self, block_name: str, signal_name: str, exit_signal_name: str):
        """Handle remove button for signal-level exit - forward to panel."""
        panel = self._find_strategy_blocks_panel()
        if panel and hasattr(panel, '_on_signal_exit_remove_clicked'):
            panel._on_signal_exit_remove_clicked(block_name, signal_name, exit_signal_name)
    
    def _find_strategy_blocks_panel(self):
        """Find the StrategyBlocksPanel by traversing up the widget tree."""
        widget = self.parent()
        while widget is not None:
            if isinstance(widget, StrategyBlocksPanel):
                return widget
            widget = widget.parent()
        return None
    
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
        
        # Set title font programmatically (CSS doesn't work for QGroupBox::title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        group_box.setFont(title_font)
        
        group_layout = QVBoxLayout()
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(15, 20, 15, 15)  # Match backtest panel padding
        
        # Reset font for content (only title should be 12pt)
        content_font = QFont()
        content_font.setPointSize(10)
        
        # Info header
        info_layout = QHBoxLayout()
        info_label = QLabel("ℹ️ Blocks are executed in order from top to bottom")
        info_label.setFont(content_font)
        info_label.setStyleSheet(get_label_style('info') + " font-size: 9pt; font-style: italic; padding: 5px;")
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
            get_label_style('muted') + " font-size: 12pt; padding: 50px; "
            "background-color: #1E2128; border: 1px solid #3C4149; border-radius: 8px;"
        )
        self.blocks_layout.addWidget(self.empty_label)
        
        self.blocks_layout.addStretch()
        self.blocks_container.setLayout(self.blocks_layout)
        
        self.blocks_scroll_area.setWidget(self.blocks_container)
        group_layout.addWidget(self.blocks_scroll_area)
        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        
        # Sprint 1.8 Task 1.8.49: Strategy-level Exit Conditions Section
        self.strategy_exit_section = QGroupBox("🔴 Strategy Exit Conditions")
        exit_section_font = QFont()
        exit_section_font.setPointSize(12)
        exit_section_font.setBold(True)
        self.strategy_exit_section.setFont(exit_section_font)
        self.strategy_exit_section.setCheckable(True)
        self.strategy_exit_section.setChecked(True)  # EXPANDED by default - so buttons are visible!
        
        exit_section_layout = QVBoxLayout()
        exit_section_layout.setSpacing(10)
        exit_section_layout.setContentsMargins(15, 20, 15, 15)
        
        # Info text
        exit_info = QLabel("Strategy level exit conditions apply to the entire strategy and can trigger over any other signal or block specific exit condition.")
        exit_info.setStyleSheet(get_label_style('muted') + " font-size: 9pt; font-style: italic;")
        exit_section_layout.addWidget(exit_info)
        
        # Container for exit conditions list (no add button - use red button in search panel)
        self.strategy_exits_container = QWidget()
        self.strategy_exits_layout = QVBoxLayout()
        self.strategy_exits_layout.setSpacing(5)
        self.strategy_exits_layout.setContentsMargins(0, 10, 0, 0)
        self.strategy_exits_container.setLayout(self.strategy_exits_layout)
        exit_section_layout.addWidget(self.strategy_exits_container)
        
        self.strategy_exit_section.setLayout(exit_section_layout)
        layout.addWidget(self.strategy_exit_section)
        
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
                'signals': [],
                'exit_conditions': []  # Initialize block-level exits list
            }
            
            # Add block-level exit conditions if present
            if hasattr(block_config, 'exit_conditions') and block_config.exit_conditions:
                for exit_cond in block_config.exit_conditions:
                    block_info['exit_conditions'].append({
                        'signal_name': exit_cond.signal_name,
                        'percentage': exit_cond.percentage,
                        'exit_mode': exit_cond.exit_mode,
                        'binding_level': exit_cond.binding_level
                    })
                print(f"DEBUG: Block '{block_config.name}' has {len(block_info['exit_conditions'])} block-level exits")
            
            # Add signal info with timing constraints and recheck config
            for signal_config in block_config.signals:
                signal_dict = {
                    'name': signal_config.name,
                    'logic': signal_config.logic,
                    'timing_constraint': None,
                    'recheck_config': None
                }
                
                # Add timing constraint data if present
                if signal_config.timing_constraint:
                    signal_dict['timing_constraint'] = {
                        'reference_signal': signal_config.timing_constraint.reference,
                        'max_candles': signal_config.timing_constraint.max_candles
                    }
                
                # Add recheck config data if present
                if signal_config.recheck_config:
                    signal_dict['recheck_config'] = {
                        'enabled': signal_config.recheck_config.enabled,
                        'bar_delay': signal_config.recheck_config.bar_delay
                    }
                
                # Add recheck chain data if present
                if hasattr(signal_config, 'recheck_chain') and signal_config.recheck_chain:
                    signal_dict['recheck_chain'] = []
                    for nested in signal_config.recheck_chain:
                        signal_dict['recheck_chain'].append({
                            'enabled': nested.enabled,
                            'bar_delay': nested.bar_delay,
                            'validation_mode': nested.validation_mode
                        })
                
                # Sprint 1.8 Task 1.8.48: Add exit conditions data if present
                if hasattr(signal_config, 'exit_conditions') and signal_config.exit_conditions:
                    signal_dict['exit_conditions'] = []
                    for exit_cond in signal_config.exit_conditions:
                        signal_dict['exit_conditions'].append({
                            'signal_name': exit_cond.signal_name,
                            'percentage': exit_cond.percentage,
                            'exit_mode': exit_cond.exit_mode,
                            'binding_level': exit_cond.binding_level
                        })
                
                block_info['signals'].append(signal_dict)
            
            # Create block item widget with parent set to this panel
            block_item = BlockConfigItem(
                block_config.name,
                block_info,
                idx,
                total_blocks,
                orchestrator=self.orchestrator,
                parent=self.blocks_container  # Set parent to ensure proper signal routing
            )
            
            # Connect signals
            block_item.move_up_clicked.connect(self._on_move_up)
            block_item.move_down_clicked.connect(self._on_move_down)
            block_item.remove_clicked.connect(self._on_remove)
            block_item.configure_timing_clicked.connect(self._on_configure_timing)
            
            # Add to layout (insert before stretch)
            self.blocks_layout.insertWidget(self.blocks_layout.count() - 1, block_item)
            self.block_items.append(block_item)
        
        # Sprint 1.8 Task 1.8.49: Refresh strategy-level exits
        self._refresh_strategy_exits()
    
    def _clear_blocks(self):
        """Clear all block items from the display."""
        # Remove all block items
        for block_item in self.block_items:
            self.blocks_layout.removeWidget(block_item)
            block_item.deleteLater()
        
        self.block_items.clear()
    
    def _clear_layout(self, layout):
        """
        Recursively clear a layout by removing all widgets and sub-layouts.
        
        Args:
            layout: QLayout to clear
        """
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self._clear_layout(sub_layout)
    
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
    
    def _on_signal_recheck_configured(self, block_name: str, signal_name: str, bar_delay: int):
        """
        Handle recheck configuration for a signal.
        
        Args:
            block_name: Block name
            signal_name: Signal name
            bar_delay: Number of bars for recheck validation
        """
        try:
            # Get current config
            config = self.orchestrator.get_current_config()
            if not config:
                print("No configuration available")
                return
            
            # Find and update signal
            from src.strategy_builder.core.strategy_config_engine import RecheckConfig
            
            for block in config.blocks:
                if block.name == block_name:
                    for signal in block.signals:
                        if signal.name == signal_name:
                            # Set recheck config
                            signal.recheck_config = RecheckConfig(enabled=True, bar_delay=bar_delay)
                            print(f"Recheck configured for {block_name}::{signal_name} - {bar_delay} bars")
                            
                            # Refresh display
                            self._refresh_blocks()
                            # Emit changed signal
                            self.blocks_changed.emit()
                            return
            
            print(f"Signal {block_name}::{signal_name} not found")
        except Exception as e:
            print(f"Error configuring recheck: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_nested_recheck_configured(
        self,
        block_name: str,
        signal_name: str,
        validate_against: str,
        bar_delay: int
    ):
        """
        Handle configuration of a nested RECHECK validation.
        
        Args:
            block_name: Block name
            signal_name: Signal name
            validate_against: "SIGNAL" or "RECHECK"
            bar_delay: Number of bars for validation
        """
        try:
            # Get current config
            config = self.orchestrator.get_current_config()
            if not config:
                print("No configuration available")
                return
            
            # Find and update signal
            from src.strategy_builder.core.strategy_config_engine import RecheckConfig
            
            for block in config.blocks:
                if block.name == block_name:
                    for signal in block.signals:
                        if signal.name == signal_name:
                            if not signal.recheck_config:
                                print(f"No base RECHECK found for {block_name}::{signal_name}")
                                return
                                
                            # Create nested recheck config
                            nested_recheck = RecheckConfig(
                                enabled=True,
                                bar_delay=bar_delay,
                                validation_mode=validate_against
                            )
                            
                            # Add to recheck chain
                            if not hasattr(signal, 'recheck_chain'):
                                signal.recheck_chain = []
                            signal.recheck_chain.append(nested_recheck)
                            
                            print(
                                f"Nested RECHECK configured for {block_name}::{signal_name} "
                                f"- {bar_delay} bars, validating against {validate_against}"
                            )
                            
                            # Refresh display
                            self._refresh_blocks()
                            # Emit changed signal
                            self.blocks_changed.emit()
                            return
            
            print(f"Signal {block_name}::{signal_name} not found")
        except Exception as e:
            print(f"Error configuring nested recheck: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_signal_recheck_removed(self, block_name: str, signal_name: str):
        """
        Handle removal of recheck configuration for a signal.
        
        Args:
            block_name: Block name
            signal_name: Signal name
        """
        try:
            # Get current config
            config = self.orchestrator.get_current_config()
            if not config:
                print("No configuration available")
                return
            
            # Find and update signal
            for block in config.blocks:
                if block.name == block_name:
                    for signal in block.signals:
                        if signal.name == signal_name:
                            # Remove recheck config and chain
                            signal.recheck_config = None
                            if hasattr(signal, 'recheck_chain'):
                                signal.recheck_chain = []
                            print(f"Recheck removed for {block_name}::{signal_name}")
                            
                            # Refresh display
                            self._refresh_blocks()
                            # Emit changed signal
                            self.blocks_changed.emit()
                            return
            
            print(f"Signal {block_name}::{signal_name} not found")
        except Exception as e:
            print(f"Error removing recheck: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    def _on_add_strategy_exit(self):
        """Handle Add Strategy Exit Condition button click - Sprint 1.8 Task 1.8.49"""
        try:
            # Show exit condition dialog
            dialog = ExitConditionDialog(parent=self)
            
            if dialog.exec_() == QDialog.Accepted:
                # Get configuration from dialog
                config = dialog.get_config()
                
                # Validate that a signal was selected
                if not config or not config.get('signal_name'):
                    print("No signal selected for exit condition")
                    return
                
                # Add to orchestrator at STRATEGY binding level
                result = self.orchestrator.add_exit_condition(
                    signal_name=config['signal_name'],
                    percentage=config.get('percentage', 50) / 100.0,  # Convert from % to 0.0-1.0
                    binding_level='STRATEGY',
                    exit_mode=config.get('exit_mode', 'ABSOLUTE'),
                    tp_proximity_threshold=config.get('tp_proximity_threshold', 2.0),
                    reversal_trigger=config.get('reversal_trigger', 0.5)
                )
                
                if result.success:
                    print(f"Strategy exit condition added: {config['signal_name']}")
                    # Refresh display
                    self._refresh_strategy_exits()
                    self.blocks_changed.emit()
                else:
                    print(f"Failed to add exit condition: {result.message}")
        
        except Exception as e:
            print(f"Error adding strategy exit condition: {e}")
            import traceback
            traceback.print_exc()
    
    def _refresh_strategy_exits(self):
        """Refresh the strategy-level exit conditions display - Sprint 1.8 Task 1.8.49"""
        try:
            # Clear existing exit items - handle both widgets AND layouts
            while self.strategy_exits_layout.count():
                item = self.strategy_exits_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    # Clear layouts recursively
                    self._clear_layout(item.layout())
            
            # Get current config
            config = self.orchestrator.get_current_config()
            if not config or not hasattr(config, 'exit_conditions') or not config.exit_conditions:
                # No strategy-level exits
                no_exits_label = QLabel("No strategy-level exit conditions configured")
                no_exits_label.setStyleSheet(get_label_style('muted') + " font-size: 9pt; font-style: italic;")
                no_exits_label.setAlignment(Qt.AlignCenter)
                self.strategy_exits_layout.addWidget(no_exits_label)
                return
            
            # Display each exit condition - COPY RECHECK PATTERN EXACTLY
            for exit_cond in config.exit_conditions:
                # Capture signal_name at loop iteration to avoid closure issues
                current_signal_name = exit_cond.signal_name
                
                # Create exit row layout - NO QWidget wrapper, just like RECHECK
                exit_row_layout = QHBoxLayout()
                exit_row_layout.setSpacing(8)
                
                # Exit info label
                pct_display = int(exit_cond.percentage * 100)
                exit_text = f"🔴 {current_signal_name} ({pct_display}%) - {exit_cond.exit_mode} mode"
                exit_label = QLabel(exit_text)
                exit_label.setStyleSheet(get_exit_tree_item_style() + " font-size: 9pt; font-weight: bold;")
                exit_label.setToolTip(
                    f"Signal: {current_signal_name}\n"
                    f"Percentage: {pct_display}%\n"
                    f"Mode: {exit_cond.exit_mode}\n"
                    f"Binding: {exit_cond.binding_level}"
                )
                exit_row_layout.addWidget(exit_label, stretch=1)
                
                # Config/Edit button - same style as recheck gear button
                config_btn = QPushButton("⚙")
                config_btn.setStyleSheet(get_recheck_gear_button_stylesheet())
                config_btn.setToolTip("Configure exit condition")
                # Use functools.partial - proper PyQt5 pattern
                print(f"DEBUG: Connecting config button for signal: {current_signal_name}")
                config_btn.clicked.connect(partial(self._on_edit_strategy_exit, current_signal_name))
                exit_row_layout.addWidget(config_btn)
                
                # Remove button - same style and size as recheck remove button
                remove_btn = QPushButton("✕")
                remove_btn.setStyleSheet(get_recheck_remove_button_stylesheet())
                remove_btn.setToolTip("Remove this exit condition")
                # Use functools.partial - proper PyQt5 pattern
                print(f"DEBUG: Connecting remove button for signal: {current_signal_name}")
                remove_btn.clicked.connect(partial(self._on_remove_strategy_exit, current_signal_name))
                exit_row_layout.addWidget(remove_btn)
                
                # Add layout directly to parent - NO QWidget wrapper
                self.strategy_exits_layout.addLayout(exit_row_layout)
        
        except Exception as e:
            print(f"Error refreshing strategy exits: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_remove_strategy_exit(self, signal_name: str, checked: bool = False):
        """Handle removal of strategy-level exit condition - Sprint 1.8 Task 1.8.49"""
        print(f"\n{'='*80}")
        print(f"DEBUG: _on_remove_strategy_exit CALLED")
        print(f"  signal_name: {signal_name}")
        print(f"  checked: {checked}")
        print(f"{'='*80}\n")
        try:
            result = self.orchestrator.remove_exit_condition(
                signal_name=signal_name,
                binding_level='STRATEGY'
            )
            
            if result.success:
                print(f"Strategy exit condition removed: {signal_name}")
                self._refresh_strategy_exits()
                self.blocks_changed.emit()
            else:
                print(f"Failed to remove exit condition: {result.message}")
        
        except Exception as e:
            print(f"Error removing strategy exit: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_edit_strategy_exit(self, signal_name: str, checked: bool = False):
        """Handle double-click on exit condition to edit - Sprint 1.8 Task 1.8.50"""
        print(f"\n{'='*80}")
        print(f"DEBUG: _on_edit_strategy_exit CALLED")
        print(f"  signal_name: {signal_name}")
        print(f"  checked: {checked}")
        print(f"{'='*80}\n")
        try:
            # Get current config
            config = self.orchestrator.get_current_config()
            if not config or not hasattr(config, 'exit_conditions') or not config.exit_conditions:
                return
            
            # Find the exit condition
            current_exit = None
            for exit_cond in config.exit_conditions:
                if exit_cond.signal_name == signal_name:
                    current_exit = exit_cond
                    break
            
            if not current_exit:
                print(f"Exit condition {signal_name} not found")
                return
            
            # Show exit condition dialog pre-populated with current values (BUG FIX)
            dialog = ExitConditionDialog(
                signal_name=signal_name,
                existing_percentage=current_exit.percentage,
                existing_exit_mode=current_exit.exit_mode,
                existing_tp_proximity=current_exit.tp_proximity_threshold,
                existing_reversal=current_exit.reversal_trigger,
                parent=self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Get new configuration from dialog
                new_config = dialog.get_config()
                
                if not new_config or not new_config.get('signal_name'):
                    print("No signal selected for exit condition")
                    return
                
                # Remove old exit condition first
                remove_result = self.orchestrator.remove_exit_condition(
                    signal_name=signal_name,
                    binding_level='STRATEGY'
                )
                
                if not remove_result.success:
                    print(f"Failed to remove old exit condition: {remove_result.message}")
                    return
                
                # Add updated exit condition
                add_result = self.orchestrator.add_exit_condition(
                    signal_name=new_config['signal_name'],
                    percentage=new_config.get('percentage', 50) / 100.0,
                    binding_level='STRATEGY',
                    exit_mode=new_config.get('exit_mode', 'ABSOLUTE'),
                    tp_proximity_threshold=new_config.get('tp_proximity_threshold', 2.0),
                    reversal_trigger=new_config.get('reversal_trigger', 0.5)
                )
                
                if add_result.success:
                    print(f"Strategy exit condition updated: {new_config['signal_name']}")
                    # Refresh display
                    self._refresh_strategy_exits()
                    self.blocks_changed.emit()
                else:
                    print(f"Failed to update exit condition: {add_result.message}")
        
        except Exception as e:
            print(f"Error editing strategy exit: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_edit_block_exit(self, block_name: str, signal_name: str):
        """Handle config button for block-level exit condition - show exit dialog."""
        print(f"DEBUG: _on_edit_block_exit called for block '{block_name}', signal '{signal_name}'")
        try:
            # Get current config to find the exit
            config = self.orchestrator.get_current_config()
            if not config:
                return
            
            # Find the block and its exit condition
            current_exit = None
            for block in config.blocks:
                if block.name == block_name:
                    if hasattr(block, 'exit_conditions') and block.exit_conditions:
                        for exit_cond in block.exit_conditions:
                            if exit_cond.signal_name == signal_name:
                                current_exit = exit_cond
                                break
                    break
            
            if not current_exit:
                print(f"Block exit condition {signal_name} not found in block {block_name}")
                return
            
            # Show exit condition dialog pre-populated with current values
            dialog = ExitConditionDialog(
                signal_name=signal_name,
                existing_percentage=current_exit.percentage,
                existing_exit_mode=current_exit.exit_mode,
                existing_tp_proximity=current_exit.tp_proximity_threshold,
                existing_reversal=current_exit.reversal_trigger,
                parent=self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Get new configuration
                new_config = dialog.get_config()
                
                if not new_config or not new_config.get('signal_name'):
                    print("No signal selected for exit condition")
                    return
                
                # Remove old exit condition first
                remove_result = self.orchestrator.remove_exit_condition(
                    signal_name=signal_name,
                    binding_level='BLOCK',
                    block_name=block_name
                )
                
                if not remove_result.success:
                    print(f"Failed to remove old block exit condition: {remove_result.message}")
                    return
                
                # Add updated exit condition
                add_result = self.orchestrator.add_exit_condition(
                    signal_name=new_config['signal_name'],
                    percentage=new_config.get('percentage', 50) / 100.0,
                    binding_level='BLOCK',
                    block_name=block_name,
                    exit_mode=new_config.get('exit_mode', 'ABSOLUTE'),
                    tp_proximity_threshold=new_config.get('tp_proximity_threshold', 2.0),
                    reversal_trigger=new_config.get('reversal_trigger', 0.5)
                )
                
                if add_result.success:
                    print(f"Block exit condition updated: {block_name} -> {new_config['signal_name']}")
                    self._refresh_blocks()
                    self.blocks_changed.emit()
                else:
                    print(f"Failed to update block exit condition: {add_result.message}")
        
        except Exception as e:
            print(f"Error editing block exit: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_duplicate_block_exit(self, block_name: str):
        """Handle duplicate button - add another exit to this block."""
        print(f"DEBUG: _on_duplicate_block_exit called for block '{block_name}'")
        try:
            # Show exit condition dialog to add a new exit to this block (no pre-population - user selects signal)
            dialog = ExitConditionDialog(parent=self)
            
            if dialog.exec_() == QDialog.Accepted:
                # Get configuration from dialog
                config = dialog.get_config()
                
                # Validate that a signal was selected
                if not config or not config.get('signal_name'):
                    print("No signal selected for exit condition")
                    return
                
                # Add to orchestrator at BLOCK binding level
                result = self.orchestrator.add_exit_condition(
                    signal_name=config['signal_name'],
                    percentage=config.get('percentage', 50) / 100.0,
                    binding_level='BLOCK',
                    block_name=block_name,
                    exit_mode=config.get('exit_mode', 'ABSOLUTE'),
                    tp_proximity_threshold=config.get('tp_proximity_threshold', 2.0),
                    reversal_trigger=config.get('reversal_trigger', 0.5)
                )
                
                if result.success:
                    print(f"Block exit condition added: {block_name} -> {config['signal_name']}")
                    self._refresh_blocks()
                    self.blocks_changed.emit()
                else:
                    print(f"Failed to add block exit condition: {result.message}")
        
        except Exception as e:
            print(f"Error adding block exit condition: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_remove_block_exit(self, block_name: str, signal_name: str):
        """Handle remove button for block-level exit condition."""
        print(f"DEBUG: _on_remove_block_exit called for block '{block_name}', signal '{signal_name}'")
        try:
            result = self.orchestrator.remove_exit_condition(
                signal_name=signal_name,
                binding_level='BLOCK',
                block_name=block_name
            )
            
            if result.success:
                print(f"Block exit condition removed: {block_name} -> {signal_name}")
                self._refresh_blocks()
                self.blocks_changed.emit()
            else:
                print(f"Failed to remove block exit condition: {result.message}")
        
        except Exception as e:
            print(f"Error removing block exit: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_signal_exit_config_clicked(self, block_name: str, signal_name: str, exit_signal_name: str):
        """Handle config button for signal-level exit condition."""
        print(f"DEBUG: _on_signal_exit_config_clicked called for block '{block_name}', signal '{signal_name}', exit '{exit_signal_name}'")
        try:
            # Get current config to find the exit
            config = self.orchestrator.get_current_config()
            if not config:
                return
            
            # Find the signal and its exit condition
            current_exit = None
            for block in config.blocks:
                if block.name == block_name:
                    for signal in block.signals:
                        if signal.name == signal_name:
                            if hasattr(signal, 'exit_conditions') and signal.exit_conditions:
                                for exit_cond in signal.exit_conditions:
                                    if exit_cond.signal_name == exit_signal_name:
                                        current_exit = exit_cond
                                        break
                            break
                    break
            
            if not current_exit:
                print(f"Signal exit condition {exit_signal_name} not found in signal {block_name}::{signal_name}")
                return
            
            # Show exit condition dialog pre-populated
            dialog = ExitConditionDialog(
                signal_name=exit_signal_name,
                existing_percentage=current_exit.percentage,
                existing_exit_mode=current_exit.exit_mode,
                existing_tp_proximity=current_exit.tp_proximity_threshold,
                existing_reversal=current_exit.reversal_trigger,
                parent=self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                new_config = dialog.get_config()
                
                if not new_config or not new_config.get('signal_name'):
                    print("No signal selected for exit condition")
                    return
                
                # Remove old
                remove_result = self.orchestrator.remove_exit_condition(
                    signal_name=exit_signal_name,
                    binding_level='SIGNAL',
                    block_name=block_name,
                    parent_signal_name=signal_name
                )
                
                if not remove_result.success:
                    print(f"Failed to remove old signal exit: {remove_result.message}")
                    return
                
                # Add updated
                add_result = self.orchestrator.add_exit_condition(
                    signal_name=new_config['signal_name'],
                    percentage=new_config.get('percentage', 50) / 100.0,
                    binding_level='SIGNAL',
                    block_name=block_name,
                    parent_signal_name=signal_name,
                    exit_mode=new_config.get('exit_mode', 'ABSOLUTE'),
                    tp_proximity_threshold=new_config.get('tp_proximity_threshold', 2.0),
                    reversal_trigger=new_config.get('reversal_trigger', 0.5)
                )
                
                if add_result.success:
                    print(f"Signal exit updated: {block_name}::{signal_name} -> {new_config['signal_name']}")
                    self._refresh_blocks()
                    self.blocks_changed.emit()
                else:
                    print(f"Failed to update signal exit: {add_result.message}")
        
        except Exception as e:
            print(f"Error editing signal exit: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_signal_exit_duplicate_clicked(self, block_name: str, signal_name: str):
        """Handle duplicate button for signal-level exit - add another exit to this signal."""
        print(f"DEBUG: _on_signal_exit_duplicate_clicked called for block '{block_name}', signal '{signal_name}'")
        try:
            dialog = ExitConditionDialog(parent=self)
            
            if dialog.exec_() == QDialog.Accepted:
                config = dialog.get_config()
                
                if not config or not config.get('signal_name'):
                    print("No signal selected for exit condition")
                    return
                
                # Add to orchestrator at SIGNAL binding level
                result = self.orchestrator.add_exit_condition(
                    signal_name=config['signal_name'],
                    percentage=config.get('percentage', 50) / 100.0,
                    binding_level='SIGNAL',
                    block_name=block_name,
                    parent_signal_name=signal_name,
                    exit_mode=config.get('exit_mode', 'ABSOLUTE'),
                    tp_proximity_threshold=config.get('tp_proximity_threshold', 2.0),
                    reversal_trigger=config.get('reversal_trigger', 0.5)
                )
                
                if result.success:
                    print(f"Signal exit added: {block_name}::{signal_name} -> {config['signal_name']}")
                    self._refresh_blocks()
                    self.blocks_changed.emit()
                else:
                    print(f"Failed to add signal exit: {result.message}")
        
        except Exception as e:
            print(f"Error adding signal exit: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_signal_exit_remove_clicked(self, block_name: str, signal_name: str, exit_signal_name: str):
        """Handle remove button for signal-level exit condition."""
        print(f"DEBUG: _on_signal_exit_remove_clicked called for block '{block_name}', signal '{signal_name}', exit '{exit_signal_name}'")
        try:
            result = self.orchestrator.remove_exit_condition(
                signal_name=exit_signal_name,
                binding_level='SIGNAL',
                block_name=block_name,
                parent_signal_name=signal_name
            )
            
            if result.success:
                print(f"Signal exit removed: {block_name}::{signal_name} -> {exit_signal_name}")
                self._refresh_blocks()
                self.blocks_changed.emit()
            else:
                print(f"Failed to remove signal exit: {result.message}")
        
        except Exception as e:
            print(f"Error removing signal exit: {e}")
            import traceback
            traceback.print_exc()
