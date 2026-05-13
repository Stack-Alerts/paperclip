"""
Strategy Builder - Visual Strategy Creator Dialog

Visual interface for creating strategies by selecting and configuring blocks.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QListWidget, QPushButton,
    QSpinBox, QGroupBox, QMessageBox, QListWidgetItem, QWidget,
    QCheckBox, QDoubleSpinBox, QScrollArea
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
        # Make window independent for multi-monitor support with maximize capability
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMaximizeButtonHint)
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
        # Start with reasonable default size - maximize button will work on any screen
        self.resize(1200, 800)
        
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
        
        # CRITICAL: Trade direction selector
        self.side_combo = QComboBox()
        self.side_combo.addItems(["SHORT", "LONG"])
        self.side_combo.setToolTip(
            "Trade Direction\n\n"
            "SHORT: Profit when price falls (bearish setups)\n"
            "LONG: Profit when price rises (bullish setups)\n\n"
            "Choose based on your signal blocks:\n"
            "- Double Top, HOD Rejection, Bearish = SHORT\n"
            "- Double Bottom, LOD Support, Bullish = LONG"
        )
        info_layout.addRow("Trade Direction:", self.side_combo)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Adaptive SL v2.0 Configuration Section
        sl_group = QGroupBox("🛡️ Adaptive Stop Loss v2.0 Configuration")
        sl_group.setCheckable(True)
        sl_group.setChecked(True)
        sl_group.setToolTip("Configure adaptive stop loss parameters\nUncheck to use default values")
        sl_layout = QVBoxLayout()
        sl_layout.setContentsMargins(10, 8, 10, 8)  # Comfortable margins
        sl_layout.setSpacing(8)  # Comfortable spacing
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)  # Comfortable spacing between buttons
        preset_layout.setContentsMargins(0, 0, 0, 8)  # Bottom margin for separation
        preset_label = QLabel("Presets:")
        preset_layout.addWidget(preset_label)
        
        conservative_btn = QPushButton("🐢 Conservative")
        conservative_btn.setToolTip("Wider SLs, higher win rate, fewer trades")
        conservative_btn.clicked.connect(self.apply_conservative_sl)
        preset_layout.addWidget(conservative_btn)
        
        balanced_btn = QPushButton("⚖️ Balanced")
        balanced_btn.setToolTip("Default settings - balanced approach")
        balanced_btn.clicked.connect(self.apply_balanced_sl)
        preset_layout.addWidget(balanced_btn)
        
        aggressive_btn = QPushButton("🚀 Aggressive")
        aggressive_btn.setToolTip("Tighter SLs, more trades, lower win rate")
        aggressive_btn.clicked.connect(self.apply_aggressive_sl)
        preset_layout.addWidget(aggressive_btn)
        
        preset_layout.addStretch()
        
        # Starting Capital field (aligned to right)
        capital_label = QLabel("Starting Capital:")
        capital_label.setStyleSheet("font-weight: bold;")
        preset_layout.addWidget(capital_label)
        
        self.starting_capital_spin = QDoubleSpinBox()
        self.starting_capital_spin.setRange(100.0, 1000000.0)
        self.starting_capital_spin.setValue(10000.0)
        self.starting_capital_spin.setSingleStep(1000.0)
        self.starting_capital_spin.setPrefix("$")
        self.starting_capital_spin.setDecimals(0)
        self.starting_capital_spin.setToolTip(
            "Starting Account Balance\n\n"
            "Total capital available for trading.\n\n"
            "Default: $10,000\n"
            "Small Account: $1,000 - $5,000\n"
            "Medium Account: $10,000 - $50,000\n"
            "Large Account: $100,000+\n\n"
            "This affects position sizing calculations."
        )
        preset_layout.addWidget(self.starting_capital_spin)
        
        sl_layout.addLayout(preset_layout)
        
        # Create horizontal split: Left = SL params, Right = Risk/Reward settings
        params_split_layout = QHBoxLayout()
        params_split_layout.setSpacing(15)  # Comfortable horizontal spacing between columns
        params_split_layout.setContentsMargins(0, 0, 0, 0)  # No extra margins needed
        
        # LEFT SIDE: Stop Loss Parameters
        sl_params_widget = QWidget()
        sl_params_layout = QFormLayout()
        sl_params_layout.setVerticalSpacing(8)  # Comfortable vertical spacing
        sl_params_layout.setContentsMargins(0, 0, 5, 0)  # Right margin for separation
        
        # Delayed SL Checkbox
        self.delayed_sl_check = QCheckBox("Enable Delayed SL Activation")
        self.delayed_sl_check.setChecked(True)
        self.delayed_sl_check.setToolTip(
            "Delayed SL Activation (CRITICAL FEATURE)\n\n"
            "Uses wide emergency SL for first few bars,\n"
            "then switches to optimized working SL.\n\n"
            "Prevents 83% of instant stops!\n\n"
            "Emergency SL: 2.5% (bars 0-2)\n"
            "Working SL: 0.9% (bar 3+)"
        )
        sl_params_layout.addRow("", self.delayed_sl_check)
        
        # Delay Bars
        delay_label = QLabel("Delay Period: ℹ️")
        delay_label.setToolTip(
            "Delay Period (bars)\n\n"
            "How long to use emergency SL before switching to working SL.\n"
            "Default: 2 bars\n"
            "Conservative: 3 bars\n"
            "Aggressive: 1 bar"
        )
        self.delay_bars_spin = QSpinBox()
        self.delay_bars_spin.setRange(0, 5)
        self.delay_bars_spin.setValue(2)
        self.delay_bars_spin.setSuffix(" bars")
        self.delay_bars_spin.setToolTip(delay_label.toolTip())
        sl_params_layout.addRow(delay_label, self.delay_bars_spin)
        
        # Emergency SL
        self.emergency_sl_spin = QDoubleSpinBox()
        self.emergency_sl_spin.setRange(1.0, 5.0)
        self.emergency_sl_spin.setValue(2.5)
        self.emergency_sl_spin.setSingleStep(0.1)
        self.emergency_sl_spin.setSuffix(" %")
        self.emergency_sl_spin.setToolTip(
            "Emergency SL Width\n\n"
            "Wide SL used during delay period.\n"
            "Protects against immediate stop-outs.\n\n"
            "Default: 2.5%\n"
            "Conservative: 3.0%\n"
            "Aggressive: 2.0%"
        )
        sl_params_layout.addRow("Emergency SL:", self.emergency_sl_spin)
        
        # Volatility Lookback
        self.volatility_lookback_spin = QSpinBox()
        self.volatility_lookback_spin.setRange(5, 100)
        self.volatility_lookback_spin.setValue(20)
        self.volatility_lookback_spin.setSuffix(" bars")
        self.volatility_lookback_spin.setToolTip(
            "Volatility Calculation Window\n\n"
            "How many bars to analyze for average range.\n"
            "Used to set minimum SL based on market volatility.\n\n"
            "Default: 20 bars"
        )
        sl_params_layout.addRow("Volatility Lookback:", self.volatility_lookback_spin)
        
        # Volatility Multiplier
        self.volatility_mult_spin = QDoubleSpinBox()
        self.volatility_mult_spin.setRange(0.5, 3.0)
        self.volatility_mult_spin.setValue(1.2)
        self.volatility_mult_spin.setSingleStep(0.1)
        self.volatility_mult_spin.setToolTip(
            "Volatility Multiplier\n\n"
            "Minimum SL = Average Range × This Multiplier\n\n"
            "Default: 1.2x\n"
            "Conservative: 1.5x\n"
            "Aggressive: 1.0x"
        )
        sl_params_layout.addRow("Volatility Multiplier:", self.volatility_mult_spin)
        
        # Min SL Percentage
        self.min_sl_pct_spin = QDoubleSpinBox()
        self.min_sl_pct_spin.setRange(0.3, 2.0)
        self.min_sl_pct_spin.setValue(0.7)
        self.min_sl_pct_spin.setSingleStep(0.1)
        self.min_sl_pct_spin.setSuffix(" %")
        self.min_sl_pct_spin.setToolTip(
            "Absolute Minimum SL\n\n"
            "Never tighter than this, even in low volatility.\n\n"
            "Default: 0.7%\n"
            "Conservative: 1.0%\n"
            "Aggressive: 0.6%"
        )
        sl_params_layout.addRow("Min SL %:", self.min_sl_pct_spin)
        
        # Max SL Percentage
        self.max_sl_pct_spin = QDoubleSpinBox()
        self.max_sl_pct_spin.setRange(1.0, 5.0)
        self.max_sl_pct_spin.setValue(2.0)
        self.max_sl_pct_spin.setSingleStep(0.1)
        self.max_sl_pct_spin.setSuffix(" %")
        self.max_sl_pct_spin.setToolTip(
            "Absolute Maximum SL\n\n"
            "Never wider than this, even in high volatility.\n\n"
            "Default: 2.0%\n"
            "Conservative: 2.5%\n"
            "Aggressive: 1.5%"
        )
        sl_params_layout.addRow("Max SL %:", self.max_sl_pct_spin)
        
        # Structure-Based SL
        self.structure_sl_check = QCheckBox("Use Structure for SL Placement")
        self.structure_sl_check.setChecked(True)
        self.structure_sl_check.setToolTip(
            "Structure-Based SL Placement\n\n"
            "When available, place SL at market structure levels\n"
            "(swing points, supply/demand zones, fibonacci levels)\n"
            "within volatility bounds.\n\n"
            "Improves SL quality when structure is clear."
        )
        sl_params_layout.addRow("", self.structure_sl_check)
        
        sl_params_widget.setLayout(sl_params_layout)
        params_split_layout.addWidget(sl_params_widget)
        
        # RIGHT SIDE: Risk/Reward Settings
        rr_params_widget = QWidget()
        rr_params_layout = QFormLayout()
        rr_params_layout.setVerticalSpacing(8)  # Comfortable vertical spacing
        rr_params_layout.setContentsMargins(5, 0, 0, 0)  # Left margin for separation
        
        # Section label
        rr_label = QLabel("💰 Risk/Reward Settings")
        rr_label.setStyleSheet("font-weight: bold; color: #4ec9b0; font-size: 9pt;")
        rr_params_layout.addRow("", rr_label)
        
        # TP Mode Selection (CRITICAL: Choose TP calculation method)
        tp_mode_label = QLabel("TP Mode: ℹ️")
        tp_mode_label.setToolTip(
            "Take Profit Calculation Method\n\n"
            "PERCENTAGE: Fixed distances (1%, 2%, 3.5%)\n"
            "  - Consistent, predictable\n"
            "  - Win Rate: 60-75%\n"
            "  - Best for: Stable markets\n\n"
            "FIBONACCI: Dynamic Fibonacci projections\n"
            "  - Market structure based\n"
            "  - Win Rate: 55-70%\n"
            "  - Best for: Trending markets\n\n"
            "HYBRID: Best of all building blocks\n"
            "  - Adaptive to conditions\n"
            "  - Win Rate: 65-80%\n"
            "  - Best for: All market conditions"
        )
        self.tp_mode_combo = QComboBox()
        self.tp_mode_combo.addItems(["PERCENTAGE", "FIBONACCI", "HYBRID"])
        self.tp_mode_combo.setCurrentText("PERCENTAGE")  # Default
        self.tp_mode_combo.setToolTip(tp_mode_label.toolTip())
        rr_params_layout.addRow(tp_mode_label, self.tp_mode_combo)
        
        # Minimum R:R for trade filtering
        self.min_rr_spin = QDoubleSpinBox()
        self.min_rr_spin.setRange(0.5, 10.0)
        self.min_rr_spin.setValue(1.2)
        self.min_rr_spin.setSingleStep(0.1)
        self.min_rr_spin.setToolTip(
            "Minimum Risk/Reward Ratio\n\n"
            "Only take trades where potential reward\n"
            "is at least this multiple of risk.\n\n"
            "Default: 1.2 (reward must be 1.2x risk)\n"
            "Conservative: 1.5 (better quality trades)\n"
            "Aggressive: 1.0 (more trades, lower quality)"
        )
        rr_params_layout.addRow("Min R:R Ratio:", self.min_rr_spin)
        
        # Risk per trade
        self.risk_per_trade_spin = QDoubleSpinBox()
        self.risk_per_trade_spin.setRange(0.1, 25.0)
        self.risk_per_trade_spin.setValue(1.0)
        self.risk_per_trade_spin.setSingleStep(0.1)
        self.risk_per_trade_spin.setSuffix(" %")
        self.risk_per_trade_spin.setToolTip(
            "Risk Per Trade\n\n"
            "Percentage of account to risk on each trade.\n\n"
            "Default: 1.0% (conservative)\n"
            "Moderate: 1.5-2.0%\n"
            "Aggressive: 2.5-5.0%\n"
            "Very Aggressive: 10-25%\n\n"
            "⚠️ Higher risk = higher potential reward but also higher losses!"
        )
        rr_params_layout.addRow("Risk Per Trade:", self.risk_per_trade_spin)
        
        # Max leverage
        self.max_leverage_spin = QDoubleSpinBox()
        self.max_leverage_spin.setRange(1.0, 25.0)
        self.max_leverage_spin.setValue(2.0)
        self.max_leverage_spin.setSingleStep(0.5)
        self.max_leverage_spin.setSuffix("x")
        self.max_leverage_spin.setToolTip(
            "Maximum Leverage\n\n"
            "Maximum position size multiplier.\n\n"
            "Default: 2.0x (moderate)\n"
            "Conservative: 1.0x (no leverage)\n"
            "Moderate: 3.0-5.0x\n"
            "Aggressive: 10.0-25.0x\n\n"
            "⚠️ Higher leverage = MUCH higher risk! Use with extreme caution!"
        )
        rr_params_layout.addRow("Max Leverage:", self.max_leverage_spin)
        
        # Min confluence
        self.min_confluence_spin = QSpinBox()
        self.min_confluence_spin.setRange(20, 200)
        self.min_confluence_spin.setValue(70)
        self.min_confluence_spin.setSuffix(" points")
        self.min_confluence_spin.setToolTip(
            "Minimum Confluence for Entry\n\n"
            "Total signal points required to trigger trade.\n\n"
            "Default: 70 points\n"
            "Conservative: 80-100 points (fewer, better trades)\n"
            "Aggressive: 50-60 points (more trades)"
        )
        rr_params_layout.addRow("Min Confluence:", self.min_confluence_spin)
        
        # Max bars held
        self.max_bars_held_spin = QSpinBox()
        self.max_bars_held_spin.setRange(10, 5000)  # Allow from 10 to 5000 bars
        self.max_bars_held_spin.setValue(1000)
        self.max_bars_held_spin.setSingleStep(10)  # Step by 10 bars for finer control
        self.max_bars_held_spin.setSuffix(" bars")
        self.max_bars_held_spin.setToolTip(
            "Maximum Trade Duration\n\n"
            "Force exit after this many bars.\n"
            "Prevents holding losing positions forever.\n\n"
            "Examples:\n"
            "- 50 bars = ~12.5 hours (15min chart)\n"
            "- 100 bars = ~1 day\n"
            "- 1000 bars = ~10 days (default)\n"
            "- 2000+ bars = swing trading"
        )
        rr_params_layout.addRow("Max Bars Held:", self.max_bars_held_spin)
        
        # Walk-Forward Optimization Settings
        wf_label = QLabel("🔬 Walk-Forward Settings")
        wf_label.setStyleSheet("font-weight: bold; color: #ce9178; font-size: 9pt; margin-top: 5px;")
        rr_params_layout.addRow("", wf_label)
        
        # Training Window
        self.training_window_spin = QSpinBox()
        self.training_window_spin.setRange(30, 365)
        self.training_window_spin.setValue(90)
        self.training_window_spin.setSingleStep(10)
        self.training_window_spin.setSuffix(" days")
        self.training_window_spin.setToolTip(
            "Training Window (days)\n\n"
            "How many days of data to use for training/optimization.\n\n"
            "Default: 90 days (3 months)\n"
            "Conservative: 120-180 days (more data)\n"
            "Aggressive: 60 days (faster adaptation)"
        )
        rr_params_layout.addRow("Training Window:", self.training_window_spin)
        
        # Testing Window
        self.testing_window_spin = QSpinBox()
        self.testing_window_spin.setRange(7, 180)
        self.testing_window_spin.setValue(30)
        self.testing_window_spin.setSingleStep(5)
        self.testing_window_spin.setSuffix(" days")
        self.testing_window_spin.setToolTip(
            "Testing Window (days)\n\n"
            "How many days to test optimized parameters.\n\n"
            "Default: 30 days (1 month)\n"
            "Conservative: 45-60 days (longer validation)\n"
            "Aggressive: 14-21 days (faster iteration)"
        )
        rr_params_layout.addRow("Testing Window:", self.testing_window_spin)
        
        rr_params_widget.setLayout(rr_params_layout)
        params_split_layout.addWidget(rr_params_widget)
        
        # Add split layout to main SL layout
        sl_layout.addLayout(params_split_layout)
        
        sl_group.setLayout(sl_layout)
        layout.addWidget(sl_group)
        
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
        
        # NEW: Accumulation window setting (for sequential signal accumulation)
        self.accumulation_window_spin = QSpinBox()
        self.accumulation_window_spin.setRange(5, 100)
        self.accumulation_window_spin.setValue(20)
        self.accumulation_window_spin.setSuffix(" bars")
        self.accumulation_window_spin.setToolTip(
            "Signal Accumulation Window\n\n"
            "How many bars to keep signals active.\n"
            "Example: 20 bars = signals from last 20 bars count toward confluence.\n\n"
            "Lower = faster entries, more sensitive\n"
            "Higher = slower entries, more confirmation needed"
        )
        config_layout.addRow("Signal Window:", self.accumulation_window_spin)
        
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
        
        # Status label (for save feedback)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 9pt; color: #4ec9b0;")
        right_layout.addWidget(self.status_label)
        
        content_layout.addWidget(right_widget)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("✓ Validate")
        validate_btn.clicked.connect(self.validate_strategy)
        button_layout.addWidget(validate_btn)
        
        button_layout.addStretch()
        
        save_draft_btn = QPushButton("💾 Save Draft")
        save_draft_btn.setToolTip("Save work-in-progress - keeps editor open")
        save_draft_btn.clicked.connect(self.save_draft)
        button_layout.addWidget(save_draft_btn)
        
        save_and_close_btn = QPushButton("💾 Save Draft & Close")
        save_and_close_btn.setToolTip("Save work-in-progress and close editor")
        save_and_close_btn.clicked.connect(self.save_draft_and_close)
        button_layout.addWidget(save_and_close_btn)
        
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
        
        # Set side (with fallback to LONG if not present)
        side = getattr(self.existing_config, 'side', 'LONG')
        self.side_combo.setCurrentText(side)
        
        # Load Adaptive SL v2.0 parameters
        self.delayed_sl_check.setChecked(getattr(self.existing_config, 'use_delayed_sl', True))
        self.delay_bars_spin.setValue(getattr(self.existing_config, 'delay_bars', 2))
        self.emergency_sl_spin.setValue(getattr(self.existing_config, 'emergency_sl_pct', 2.5))
        self.volatility_lookback_spin.setValue(getattr(self.existing_config, 'volatility_lookback', 20))
        self.volatility_mult_spin.setValue(getattr(self.existing_config, 'volatility_multiplier', 1.2))
        self.min_sl_pct_spin.setValue(getattr(self.existing_config, 'absolute_min_sl_pct', 0.7))
        self.max_sl_pct_spin.setValue(getattr(self.existing_config, 'absolute_max_sl_pct', 2.0))
        self.structure_sl_check.setChecked(getattr(self.existing_config, 'use_structure_sl', True))
        
        # Load Risk/Reward parameters
        self.starting_capital_spin.setValue(getattr(self.existing_config, 'starting_capital', 10000.0))
        self.tp_mode_combo.setCurrentText(getattr(self.existing_config, 'tp_mode', 'PERCENTAGE'))  # Load TP mode
        self.min_rr_spin.setValue(getattr(self.existing_config, 'min_risk_reward', 1.2))
        self.risk_per_trade_spin.setValue(getattr(self.existing_config, 'risk_per_trade_pct', 1.0))
        self.max_leverage_spin.setValue(getattr(self.existing_config, 'max_leverage', 2.0))
        self.min_confluence_spin.setValue(getattr(self.existing_config, 'min_confluence', 70))
        self.max_bars_held_spin.setValue(getattr(self.existing_config, 'max_bars_held', 1000))
        
        # Load Walk-Forward parameters
        self.training_window_spin.setValue(getattr(self.existing_config, 'training_window_days', 90))
        self.testing_window_spin.setValue(getattr(self.existing_config, 'testing_window_days', 30))
        
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
            # Filter out defensive signals (ERROR, INSUFFICIENT_DATA)
            if signal.name in ['ERROR', 'INSUFFICIENT_DATA']:
                continue
                
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
        if current_row < 0 or current_row >= len(self.selected_blocks):
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
        """Calculate and display total confluence with validation feedback"""
        total = sum(block.weight for block in self.selected_blocks)
        num_blocks = len(self.selected_blocks)
        
        # Build display text with requirements
        text = f"Total Confluence: {total} points"
        
        # Add minimum requirement (40 is standard minimum)
        min_required = 40
        if total < min_required:
            text += f" (⚠️ {min_required} required)"
        elif total >= min_required:
            text += f" (✓ {min_required} met)"
        
        # Add block count requirement
        min_blocks = 2
        if num_blocks < min_blocks:
            text += f" | {num_blocks} of {min_blocks} blocks min"
        else:
            text += f" | {num_blocks} blocks ✓"
        
        self.confluence_label.setText(text)
        
        # Color code based on validation
        if total < min_required or num_blocks < min_blocks:
            color = "#f48771"  # Red - validation failed
        elif total < 60:
            color = "#ce9178"  # Orange - low but valid
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
            
    def apply_conservative_sl(self):
        """Apply conservative SL preset (wider SLs, higher win rate, fewer trades)"""
        self.delayed_sl_check.setChecked(True)
        self.delay_bars_spin.setValue(3)
        self.emergency_sl_spin.setValue(3.0)
        self.volatility_lookback_spin.setValue(20)
        self.volatility_mult_spin.setValue(1.5)
        self.min_sl_pct_spin.setValue(1.0)
        self.max_sl_pct_spin.setValue(2.5)
        self.structure_sl_check.setChecked(True)
        
        self.status_label.setText("🐢 Conservative preset applied")
        self.status_label.setStyleSheet("font-size: 9pt; color: #4ec9b0;")
    
    def apply_balanced_sl(self):
        """Apply balanced SL preset (default settings)"""
        self.delayed_sl_check.setChecked(True)
        self.delay_bars_spin.setValue(2)
        self.emergency_sl_spin.setValue(2.5)
        self.volatility_lookback_spin.setValue(20)
        self.volatility_mult_spin.setValue(1.2)
        self.min_sl_pct_spin.setValue(0.7)
        self.max_sl_pct_spin.setValue(2.0)
        self.structure_sl_check.setChecked(True)
        
        self.status_label.setText("⚖️ Balanced preset applied")
        self.status_label.setStyleSheet("font-size: 9pt; color: #4ec9b0;")
    
    def apply_aggressive_sl(self):
        """Apply aggressive SL preset (tighter SLs, more trades, lower win rate)"""
        self.delayed_sl_check.setChecked(True)
        self.delay_bars_spin.setValue(1)
        self.emergency_sl_spin.setValue(2.0)
        self.volatility_lookback_spin.setValue(20)
        self.volatility_mult_spin.setValue(1.0)
        self.min_sl_pct_spin.setValue(0.6)
        self.max_sl_pct_spin.setValue(1.5)
        self.structure_sl_check.setChecked(True)
        
        self.status_label.setText("🚀 Aggressive preset applied")
        self.status_label.setStyleSheet("font-size: 9pt; color: #4ec9b0;")
    
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
        
        # Build configuration with Adaptive SL and Risk/Reward parameters
        config = StrategyConfiguration(
            strategy_name=strategy_name,
            strategy_number=next_num,
            strategy_category=self.category_combo.currentText(),
            side=self.side_combo.currentText(),
            main_signal_block=main_signal,
            blocks=self.selected_blocks.copy(),
            # Adaptive SL v2.0 parameters
            volatility_lookback=self.volatility_lookback_spin.value(),
            volatility_multiplier=self.volatility_mult_spin.value(),
            absolute_min_sl_pct=self.min_sl_pct_spin.value(),
            absolute_max_sl_pct=self.max_sl_pct_spin.value(),
            use_delayed_sl=self.delayed_sl_check.isChecked(),
            delay_bars=self.delay_bars_spin.value(),
            emergency_sl_pct=self.emergency_sl_spin.value(),
            use_structure_sl=self.structure_sl_check.isChecked(),
            structure_sources=['swing_points', 'supply_demand', 'fibonacci'],
            # Risk/Reward parameters
            starting_capital=self.starting_capital_spin.value(),  # CRITICAL: Save starting capital
            tp_mode=self.tp_mode_combo.currentText(),  # CRITICAL: Save TP mode (PERCENTAGE/FIBONACCI/HYBRID)
            min_risk_reward=self.min_rr_spin.value(),
            risk_per_trade_pct=self.risk_per_trade_spin.value(),
            max_leverage=self.max_leverage_spin.value(),
            min_confluence=self.min_confluence_spin.value(),
            max_bars_held=self.max_bars_held_spin.value(),
            # Walk-Forward Optimization parameters
            training_window_days=self.training_window_spin.value(),
            testing_window_days=self.testing_window_spin.value()
        )
        
        return config
    
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
            
            # Update status label instead of popup
            self.status_label.setText(
                f"💾 Draft {action}! | #{strategy_num:03d} | {user_input_name} | {len(config.blocks)} blocks"
            )
            self.status_label.setStyleSheet("font-size: 9pt; color: #4ec9b0;")
            
            # Don't close dialog - user can continue editing
            
        except Exception as e:
            # Show error in status label
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("font-size: 9pt; color: #f48771;")
    
    def save_draft_and_close(self):
        """Save strategy as a draft and close the editor"""
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
            
            action = "updated" if self.editing_mode and strategy_num == config.strategy_number else "saved"
            
            # Call callback to refresh parent window
            if self.on_draft_saved:
                self.on_draft_saved()
            
            # Close dialog (no annoying popup!)
            self.accept()
            
        except Exception as e:
            # Show error in status label
            self.status_label.setText(f"❌ Error: {e}")
            self.status_label.setStyleSheet("font-size: 9pt; color: #f48771;")
        
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
