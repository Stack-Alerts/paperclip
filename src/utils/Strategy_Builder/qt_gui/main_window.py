"""
Strategy Builder - PyQt6 Main Window

Professional UI with VSCode dark theme and large fonts.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QTextEdit,
    QToolBar, QStatusBar, QMessageBox, QSplitter, QComboBox, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QAction

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from PyQt6.QtCore import QThread, pyqtSignal
import subprocess

from src.utils.Strategy_Builder import (
    StrategyRegistry,
    StrategyValidator,
    StrategyGenerator
)
from src.utils.Strategy_Builder.qt_gui.block_library import BlockLibraryPanel
from src.utils.Strategy_Builder.qt_gui.code_preview import CodePreviewDialog
from src.utils.Strategy_Builder.qt_gui.strategy_creator import StrategyCreatorDialog
from src.debugger_logger import ConfigDebugger


class BacktestThread(QThread):
    """Background thread for running backtests without freezing UI"""
    
    # Signals for real-time output streaming
    output_signal = pyqtSignal(str)  # Emits each line of output
    finished_signal = pyqtSignal(int, int)  # Emits (strategy_num, return_code)
    
    def __init__(self, cmd, cwd, strategy_num, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.cwd = cwd
        self.strategy_num = strategy_num
        self.return_code = -1
        self.error = None
        self.process = None  # Store subprocess reference
        
    def run(self):
        """Execute subprocess with real-time output streaming"""
        try:
            # Use Popen for real-time output
            self.process = subprocess.Popen(  # Store as instance variable
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                cwd=self.cwd
            )
            
            # Stream output line by line
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.output_signal.emit(line.rstrip())
            
            # Wait for completion
            self.process.wait()
            self.return_code = self.process.returncode
            
            # Emit completion signal
            self.finished_signal.emit(self.strategy_num, self.return_code)
            
        except Exception as e:
            self.error = str(e)
            self.output_signal.emit(f"\n❌ ERROR: {e}\n")
            self.finished_signal.emit(self.strategy_num, -1)
    
    def stop_process(self):
        """Terminate the subprocess"""
        if self.process and self.process.poll() is None:  # Check if still running
            try:
                self.process.terminate()  # Send SIGTERM
                # Wait briefly, then kill if still alive
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()  # Force kill with SIGKILL
                    self.process.wait()
            except Exception as e:
                print(f"Error stopping process: {e}")


class StrategyBuilderMainWindow(QMainWindow):
    """Main window for Strategy Builder PyQt6 UI"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize backend components
        self.registry = StrategyRegistry()
        self.validator = StrategyValidator()
        self.generator = StrategyGenerator()
        
        # Initialize Config Debugger (disabled by default)
        log_file = Path("logs/strategy_builder_debug.log")
        self.config_debugger = ConfigDebugger(
            name="StrategyBuilder",
            log_file=log_file,
            console_output=False  # Don't spam console
        )
        self.debugger_enabled = False
        
        # Setup UI
        self.init_ui()
        self.apply_dark_theme()
        self.restore_window_state()
        self.load_strategies()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("BTC Engine v3 - Strategy Builder")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create central widget
        self.create_central_widget()
        
        # Create status bar
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('📁 File')
        
        new_action = QAction('➕ New Strategy', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_strategy)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('❌ Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('👁️ View')
        
        refresh_action = QAction('🔄 Refresh', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.load_strategies)
        view_menu.addAction(refresh_action)
        
        stats_action = QAction('📊 Statistics', self)
        stats_action.triggered.connect(self.show_statistics)
        view_menu.addAction(stats_action)
        
        view_menu.addSeparator()
        
        clear_cache_action = QAction('🧹 Clear Cache & Restart', self)
        clear_cache_action.setShortcut('Ctrl+Shift+C')
        clear_cache_action.triggered.connect(self.clear_cache_and_restart)
        view_menu.addAction(clear_cache_action)
        
        # Debug menu
        debug_menu = menubar.addMenu('🐛 Debug')
        
        self.show_debug_action = QAction('✓ Show Debug Messages', self, checkable=True)
        self.show_debug_action.setShortcut('Ctrl+D')
        self.show_debug_action.setChecked(False)  # Default: hide debug messages
        self.show_debug_action.triggered.connect(self.toggle_debug_messages)
        debug_menu.addAction(self.show_debug_action)
        
        debug_menu.addSeparator()
        
        # Granular Debugger toggle (renamed from Config Debugger)
        self.enable_debugger_action = QAction('Enable Granular Debugger', self, checkable=True)
        self.enable_debugger_action.setChecked(False)  # Default: disabled
        self.enable_debugger_action.triggered.connect(self.toggle_config_debugger)
        debug_menu.addAction(self.enable_debugger_action)
        
        # View Debug Log
        view_log_action = QAction('📄 View Debug Log', self)
        view_log_action.triggered.connect(self.view_debug_log)
        debug_menu.addAction(view_log_action)
        
        # Help menu
        help_menu = menubar.addMenu('❓ Help')
        
        about_action = QAction('ℹ️ About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create toolbar with large buttons"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(48, 48))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # New button
        new_btn = QAction('➕ New', self)
        new_btn.triggered.connect(self.new_strategy)
        toolbar.addAction(new_btn)
        
        # Edit button
        edit_btn = QAction('✏️ Edit', self)
        edit_btn.triggered.connect(self.edit_strategy)
        toolbar.addAction(edit_btn)
        
        # Delete button
        delete_btn = QAction('🗑 Delete', self)
        delete_btn.triggered.connect(self.delete_strategy)
        toolbar.addAction(delete_btn)
        
        toolbar.addSeparator()
        
        # Validate button
        validate_btn = QAction('✓ Validate', self)
        validate_btn.triggered.connect(self.validate_strategy)
        toolbar.addAction(validate_btn)
        
        toolbar.addSeparator()
        
        # Publish button
        publish_btn = QAction('✅ Publish', self)
        publish_btn.triggered.connect(self.publish_strategy)
        toolbar.addAction(publish_btn)
        
        # Generate button
        generate_btn = QAction('⚙ Generate', self)
        generate_btn.triggered.connect(self.generate_files)
        toolbar.addAction(generate_btn)
        
        # Test button
        test_btn = QAction('🧪 Test', self)
        test_btn.triggered.connect(self.test_strategy)
        toolbar.addAction(test_btn)
        
        # Quick Test button
        quick_test_btn = QAction('⚡ Quick Test', self)
        quick_test_btn.triggered.connect(self.quick_test_strategy)
        toolbar.addAction(quick_test_btn)
        
        # View Results button
        results_btn = QAction('📊 Results', self)
        results_btn.triggered.connect(self.view_test_results)
        toolbar.addAction(results_btn)
        
        # Load Last Test button
        load_test_btn = QAction('📂 Last Test', self)
        load_test_btn.triggered.connect(self.load_last_test)
        toolbar.addAction(load_test_btn)
        
        toolbar.addSeparator()
        
        # Refresh button
        refresh_btn = QAction('🔄 Refresh', self)
        refresh_btn.triggered.connect(self.load_strategies)
        toolbar.addAction(refresh_btn)
        
        toolbar.addSeparator()
        
        # Clear Cache & Restart button
        clear_cache_btn = QAction('🧹 Clear Cache', self)
        clear_cache_btn.triggered.connect(self.clear_cache_and_restart)
        clear_cache_btn.setToolTip("Clear Python bytecode cache and restart GUI")
        toolbar.addAction(clear_cache_btn)
        
    def create_central_widget(self):
        """Create main content area"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panes (3-pane)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left pane: Block Library
        self.block_library = BlockLibraryPanel()
        self.splitter.addWidget(self.block_library)
        
        # Middle pane: Strategy list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("📋 Strategies")
        list_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #ffffff;")
        left_layout.addWidget(list_label)
        
        # Status filter and search
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filter_label = QLabel("Filter:")
        filter_layout.addWidget(filter_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems([
            "All Status",
            "💾 Drafts Only",
            "📝 Ready Only",
            "✅ Published Only"
        ])
        self.status_filter.currentTextChanged.connect(self.load_strategies)
        filter_layout.addWidget(self.status_filter)
        
        # Add search box
        self.strategy_search = QLineEdit()
        self.strategy_search.setPlaceholderText("🔍 Search strategies...")
        self.strategy_search.setMaximumWidth(200)
        self.strategy_search.textChanged.connect(self.load_strategies)
        filter_layout.addWidget(self.strategy_search)
        
        left_layout.addLayout(filter_layout)
        
        self.strategy_list = QListWidget()
        self.strategy_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.strategy_list.customContextMenuRequested.connect(self.show_context_menu)
        self.strategy_list.itemDoubleClicked.connect(self.on_strategy_double_clicked)
        left_layout.addWidget(self.strategy_list)
        
        self.splitter.addWidget(left_widget)
        
        # Right pane: Details/Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        editor_label = QLabel("📝 Strategy Details")
        editor_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(editor_label)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText(
            "Select a strategy from the list to view details...\n\n"
            "Or click '➕ New' to create a new strategy!"
        )
        right_layout.addWidget(self.details_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("✓ Validate")
        validate_btn.clicked.connect(self.validate_strategy)
        button_layout.addWidget(validate_btn)
        
        test_btn = QPushButton("🧪 Test")
        test_btn.clicked.connect(self.test_strategy)
        button_layout.addWidget(test_btn)
        
        generate_btn = QPushButton("⚙ Generate")
        generate_btn.clicked.connect(self.generate_files)
        button_layout.addWidget(generate_btn)
        
        right_layout.addLayout(button_layout)
        
        self.splitter.addWidget(right_widget)
        
        # Set initial sizes (25% library, 30% strategies, 45% details)
        self.splitter.setSizes([250, 300, 450])
        
        layout.addWidget(self.splitter)
        
        # Connect list selection
        self.strategy_list.currentItemChanged.connect(self.on_strategy_selected)
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | 0/150 Strategy Slots")
        
    def apply_dark_theme(self):
        """Apply VSCode dark theme stylesheet"""
        qss_path = Path(__file__).parent / 'dark_theme.qss'
        try:
            with open(qss_path, 'r') as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Warning: Could not load dark theme: {e}")
            
    def load_strategies(self):
        """Load strategies from registry with folder status and filtering"""
        self.strategy_list.clear()
        strategies = self.registry.list_strategies()
        
        # Get filter selection
        filter_text = self.status_filter.currentText() if hasattr(self, 'status_filter') else "All Status"
        
        # Get search text
        search_text = self.strategy_search.text().lower() if hasattr(self, 'strategy_search') else ""
        
        # Count by folder
        drafts_count = 0
        unpublished_count = 0
        published_count = 0
        displayed_count = 0
        
        for strategy in sorted(strategies, key=lambda s: s.number):
            # Determine folder from file path
            file_path = Path(strategy.file_path)
            folder_name = file_path.parent.name
            
            # Set status indicator
            if folder_name == "drafts":
                status = " 💾[DRAFT]"
                status_type = "draft"
                drafts_count += 1
            elif folder_name == "published":
                status = " ✅[PUBLISHED]"
                status_type = "published"
                published_count += 1
            else:  # unpublished
                status = " 📝[READY]"
                status_type = "ready"
                unpublished_count += 1
            
            # Apply status filter
            show_strategy = False
            if filter_text == "All Status":
                show_strategy = True
            elif filter_text == "💾 Drafts Only" and status_type == "draft":
                show_strategy = True
            elif filter_text == "📝 Ready Only" and status_type == "ready":
                show_strategy = True
            elif filter_text == "✅ Published Only" and status_type == "published":
                show_strategy = True
            
            # Apply text search filter
            if show_strategy and search_text:
                # Search in strategy name, number, and category
                strategy_text = f"{strategy.number:03d} {strategy.name} {strategy.category}".lower()
                if search_text not in strategy_text:
                    show_strategy = False
            
            if show_strategy:
                item_text = f"{strategy.number:03d}. {strategy.name} ({strategy.category}){status}"
                self.strategy_list.addItem(item_text)
                displayed_count += 1
        
        total = len(strategies)
        if search_text:
            # Show search results
            self.status_bar.showMessage(
                f"Search: '{search_text}' | Found {displayed_count}/{total} strategies"
            )
        elif filter_text == "All Status":
            self.status_bar.showMessage(
                f"Ready | {total}/150 Slots | "
                f"💾{drafts_count} Drafts | 📝{unpublished_count} Ready | ✅{published_count} Published"
            )
        else:
            self.status_bar.showMessage(
                f"Filter: {filter_text} | Showing {displayed_count}/{total} strategies"
            )
        
    def on_strategy_selected(self, current, previous):
        """Handle strategy selection"""
        if not current:
            return
            
        # Extract strategy number
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Load strategy details
        config = self.registry.load_strategy(strategy_num)
        if config:
            # Log to debugger if enabled
            if self.debugger_enabled:
                # Register the loaded configuration
                config_dict = {
                    'strategy_name': config.strategy_name,
                    'strategy_number': strategy_num,  # Use the parsed strategy_num
                    'tp_mode': getattr(config, 'tp_mode', 'PERCENTAGE'),
                    'min_risk_reward': getattr(config, 'min_risk_reward', 1.2),
                    'min_confluence': getattr(config, 'min_confluence', 70),
                    'blocks_count': len(config.blocks)
                }
                self.config_debugger.register_config_source(
                    config_dict,
                    source=f"strategy_{strategy_num:03d}.json",
                    source_type="strategy_json"
                )
                self.config_debugger.log_action(
                    action=f"Loaded strategy #{strategy_num:03d}",
                    config_keys_used=['strategy_name', 'tp_mode', 'blocks_count'],
                    parameters={'strategy_num': strategy_num}
                )
            
            # Build comprehensive details view
            details = f"""Strategy #{strategy_num:03d}
{'='*60}
Name: {config.strategy_name}
Category: {config.strategy_category}
Trade Direction: {getattr(config, 'side', 'LONG')}

Building Blocks ({len(config.blocks)}):
"""
            # Show blocks with weights and signals
            for i, block in enumerate(config.blocks, 1):
                details += f"\n{i}. {block.block_name} (Weight: {block.weight})"
                if block.signals:
                    for signal in block.signals:
                        details += f"\n   - {signal.signal_name}"
                else:
                    details += f"\n   - (No signals configured)"
            
            # Separator before configuration parameters
            details += f"\n\n{'─'*60}\n"
            
            # Risk/Reward Settings
            tp_mode = getattr(config, 'tp_mode', 'PERCENTAGE')
            details += f"""
💰 RISK/REWARD SETTINGS
{'─'*60}
TP Mode:               {tp_mode} ⭐
Min R:R Ratio:         {getattr(config, 'min_risk_reward', 1.2):.1f}
Risk Per Trade:        {getattr(config, 'risk_per_trade_pct', 1.0):.1f}%
Max Leverage:          {getattr(config, 'max_leverage', 2.0):.1f}x
Min Confluence:        {getattr(config, 'min_confluence', 70)} points
Max Bars Held:         {getattr(config, 'max_bars_held', 1000)} bars
"""
            
            # Walk-Forward Settings
            details += f"""
🔬 WALK-FORWARD SETTINGS
{'─'*60}
Training Window:       {getattr(config, 'training_window_days', 90)} days
Testing Window:        {getattr(config, 'testing_window_days', 30)} days
"""
            
            # Adaptive SL v2.0 Settings
            use_delayed_sl = getattr(config, 'use_delayed_sl', True)
            use_structure_sl = getattr(config, 'use_structure_sl', True)
            
            details += f"""
🛡️ ADAPTIVE STOP LOSS v2.0 SETTINGS
{'─'*60}
Delayed SL:            {'✅ Enabled' if use_delayed_sl else '❌ Disabled'}
Delay Period:          {getattr(config, 'delay_bars', 2)} bars
Emergency SL:          {getattr(config, 'emergency_sl_pct', 2.5):.1f}%
Volatility Lookback:   {getattr(config, 'volatility_lookback', 20)} bars
Volatility Multiplier: {getattr(config, 'volatility_multiplier', 1.2):.1f}x
Min SL %:              {getattr(config, 'absolute_min_sl_pct', 0.7):.1f}%
Max SL %:              {getattr(config, 'absolute_max_sl_pct', 2.0):.1f}%
Structure-Based SL:    {'✅ Enabled' if use_structure_sl else '❌ Disabled'}
"""
            
            # Footer
            details += f"\n{'='*60}\n"
            
            self.details_text.setPlainText(details)
            self.status_bar.showMessage(f"Selected: Strategy #{strategy_num:03d}")
    
    def on_strategy_double_clicked(self, item):
        """Handle double-click on strategy - open edit dialog"""
        # Simply call edit_strategy which already has all the logic
        self.edit_strategy()
            
    def new_strategy(self):
        """Create new strategy"""
        try:
            # Check if slots available
            next_num = self.registry.get_next_strategy_number()
            
            # Launch visual creator (non-blocking)
            # Pass refresh callback so drafts update list immediately
            creator = StrategyCreatorDialog(self, on_draft_saved=self.load_strategies)
            creator.show()  # Non-blocking - allows multiple windows
                
        except ValueError:
            QMessageBox.critical(
                self,
                "Error",
                "All 150 strategy slots are filled!"
            )
    
    def edit_strategy(self):
        """Edit existing strategy or draft"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to edit"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Load strategy config
        config = self.registry.load_strategy(strategy_num)
        if not config:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load strategy #{strategy_num:03d}"
            )
            return
        
        # Launch visual creator with existing config (non-blocking)
        # Pass refresh callback so drafts update list immediately
        creator = StrategyCreatorDialog(
            self, 
            existing_config=config,
            on_draft_saved=self.load_strategies
        )
        creator.show()  # Non-blocking - allows multiple edit windows
            
    def delete_strategy(self):
        """Delete selected strategy"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to delete"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete Strategy #{strategy_num:03d}?\n\n"
            "This will remove the strategy configuration.\n"
            "(Generated files will not be deleted)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.registry.delete_strategy(strategy_num)
                self.load_strategies()
                QMessageBox.information(
                    self,
                    "Success",
                    f"✅ Strategy #{strategy_num:03d} deleted"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete strategy:\n{e}"
                )
            
    def validate_strategy(self):
        """Validate selected strategy"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to validate"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        config = self.registry.load_strategy(strategy_num)
        if config:
            result = self.validator.validate(config)
            if result.is_valid:
                QMessageBox.information(
                    self,
                    "Validation Success",
                    "✅ Strategy is VALID!"
                )
            else:
                errors = '\n'.join(f"• {e}" for e in result.errors)
                QMessageBox.critical(
                    self,
                    "Validation Failed",
                    f"❌ Errors:\n\n{errors}"
                )
                
    def generate_files(self):
        """Generate strategy files with feedback"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to generate files for"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        try:
            # Show progress
            self.status_bar.showMessage(f"Generating files for strategy #{strategy_num:03d}...")
            
            files = self.registry.generate_strategy_files(strategy_num)
            if files:
                # Show success message with file list
                file_list = "\n".join(f"• {Path(p).name}" for p in files.values())
                QMessageBox.information(
                    self,
                    "Files Generated",
                    f"✅ Successfully generated {len(files)} files:\n\n{file_list}\n\n"
                    f"Location: src/strategies/ and tests/"
                )
                self.status_bar.showMessage(f"Generated {len(files)} files for strategy #{strategy_num:03d}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Generation failed:\n{e}"
            )
            self.status_bar.showMessage("Generation failed")
    
    def test_strategy(self):
        """Test strategy with Universal Optimizer v2"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to test"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Confirm test
        reply = QMessageBox.question(
            self,
            "Run Backtest",
            f"Run Universal Optimizer v2 test on Strategy #{strategy_num:03d}?\n\n"
            f"This will:\n"
            f"• Generate strategy files if needed\n"
            f"• Run walk-forward optimization\n"
            f"• Display results in this window\n\n"
            f"This may take several minutes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._run_backtest(strategy_num)
    
    def quick_test_strategy(self):
        """Quick test strategy (skip TP/SL optimization for fast iteration)"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to test"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Confirm test
        reply = QMessageBox.question(
            self,
            "Run Quick Test",
            f"Run QUICK TEST on Strategy #{strategy_num:03d}?\n\n"
            f"⚡ QUICK TEST MODE:\n"
            f"• Skips TP/SL optimization (uses current config)\n"
            f"• Much faster (~2 minutes vs 10+ minutes)\n"
            f"• Perfect for refining block selection\n"
            f"• Use after finding good TP/SL values\n\n"
            f"This is ideal for iterating on building blocks!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._run_backtest(strategy_num, quick_test=True)
    
    def _run_backtest(self, strategy_num: int, quick_test: bool = False):
        """Run backtest with live output streaming"""
        try:
            # Update status
            self.status_bar.showMessage(f"Running backtest for strategy #{strategy_num:03d}...")
            
            # Generate files first
            files = self.registry.generate_strategy_files(strategy_num)
            
            # Get the strategy module name from generated file
            if not files or 'strategy' not in files:
                raise ValueError("Strategy file generation failed")
            
            strategy_file = Path(files['strategy'])
            strategy_module = strategy_file.stem  # e.g., "strategy_001_hod_rejection"
            
            # Build command with non-interactive flag for GUI use
            cmd = [
                "python",
                "scripts/universal_optimizer_v2.py",
                strategy_module,
                "--days", "90",
                "--non-interactive"  # Auto-select best config without prompts
            ]
            
            # Add quick-test flag if requested
            if quick_test:
                cmd.append("--quick-test")
            
            # Add enable-debugger flag if GUI debugger is enabled
            if self.debugger_enabled:
                cmd.append("--enable-debugger")
            
            # Create live output dialog
            self._create_live_output_dialog(strategy_num)
            
            # Run in background thread
            self.backtest_thread = BacktestThread(cmd, Path.cwd(), strategy_num, self)
            self.backtest_thread.output_signal.connect(self._append_output_line)
            self.backtest_thread.finished_signal.connect(self._on_backtest_finished)
            self.backtest_thread.start()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Test execution failed:\n{e}"
            )
            self.status_bar.showMessage("Ready")
    
    def _create_live_output_dialog(self, strategy_num: int):
        """Create live output dialog that shows test progress in real-time"""
        # Create independent window
        self.live_output_dialog = QDialog(self, Qt.WindowType.Window)
        self.live_output_dialog.setWindowTitle(f"🧪 Testing Strategy #{strategy_num:03d} - LIVE OUTPUT")
        self.live_output_dialog.setGeometry(200, 200, 900, 700)
        self.live_output_dialog.setModal(False)
        
        layout = QVBoxLayout(self.live_output_dialog)
        
        # Status label
        self.live_status_label = QLabel("⏳ Running backtest...")
        self.live_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #ffaa00;")
        layout.addWidget(self.live_status_label)
        
        # Output text area
        self.live_output_text = QTextEdit()
        self.live_output_text.setReadOnly(True)
        self.live_output_text.setPlaceholderText("Waiting for output...")
        layout.addWidget(self.live_output_text)
        
        # Buttons - Row 1: Action buttons
        button_row1 = QHBoxLayout()
        
        # Stop/Cancel button
        self.stop_test_btn = QPushButton("🛑 Stop Test")
        self.stop_test_btn.setToolTip("Cancel the running backtest")
        self.stop_test_btn.clicked.connect(self._stop_backtest)
        self.stop_test_btn.setEnabled(True)  # Enabled during run
        button_row1.addWidget(self.stop_test_btn)
        
        # Summary button
        self.summary_btn = QPushButton("📊 Summary Only")
        self.summary_btn.setToolTip("Show only summary results")
        self.summary_btn.clicked.connect(self._show_summary_results)
        self.summary_btn.setEnabled(False)  # Disabled until complete
        button_row1.addWidget(self.summary_btn)
        
        # Show Trades button
        self.trades_btn = QPushButton("📈 Show Trades")
        self.trades_btn.setToolTip("Display trades in new window")
        self.trades_btn.clicked.connect(self._show_trades_window)
        self.trades_btn.setEnabled(False)  # Disabled until complete
        button_row1.addWidget(self.trades_btn)
        
        # Compare button
        self.compare_btn = QPushButton("⚖️ Compare Results")
        self.compare_btn.setToolTip("Compare with previous test results")
        self.compare_btn.clicked.connect(self._compare_results)
        self.compare_btn.setEnabled(False)  # Disabled until complete
        button_row1.addWidget(self.compare_btn)
        
        button_row1.addStretch()
        
        layout.addLayout(button_row1)
        
        # Buttons - Row 2: Copy and close buttons
        button_row2 = QHBoxLayout()
        
        # Copy buttons
        copy_all_btn = QPushButton("📋 Copy All")
        copy_all_btn.setToolTip("Copy all output to clipboard")
        copy_all_btn.clicked.connect(self._copy_output_to_clipboard)
        button_row2.addWidget(copy_all_btn)
        
        copy_paths_btn = QPushButton("📂 Copy Paths")
        copy_paths_btn.setToolTip("Copy trade record paths to clipboard")
        copy_paths_btn.clicked.connect(self._copy_trade_records_to_clipboard)
        button_row2.addWidget(copy_paths_btn)
        
        button_row2.addStretch()
        
        # Progress bar with time estimate
        self.test_progress_bar = QProgressBar()
        self.test_progress_bar.setMinimum(0)
        self.test_progress_bar.setMaximum(100)
        self.test_progress_bar.setValue(0)
        self.test_progress_bar.setTextVisible(True)
        self.test_progress_bar.setFormat("Initializing... 0%")
        self.test_progress_bar.setFixedWidth(300)
        button_row2.addWidget(self.test_progress_bar)
        
        self.live_close_btn = QPushButton("⏸ Running...")
        self.live_close_btn.setEnabled(False)  # Disabled while running
        self.live_close_btn.clicked.connect(self.live_output_dialog.accept)
        button_row2.addWidget(self.live_close_btn)
        
        layout.addLayout(button_row2)
        
        # Initialize progress tracking
        import time
        self.test_start_time = time.time()
        self.test_total_configs = 0
        self.test_current_config = 0
        
        # Show dialog
        self.live_output_dialog.show()
    
    def toggle_debug_messages(self):
        """Toggle visibility of DEBUG messages in output"""
        # Update the checkmark in menu
        is_checked = self.show_debug_action.isChecked()
        
        # Update menu text to show current state
        if is_checked:
            self.show_debug_action.setText('✓ Show Debug Messages')
        else:
            self.show_debug_action.setText('✗ Hide Debug Messages')
        
        # Save preference to settings for persistence
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        settings.setValue("debug/show_messages", is_checked)
        
        # Update status bar
        status = "showing" if is_checked else "hiding"
        self.status_bar.showMessage(f"Debug messages now {status}")
    
    def toggle_config_debugger(self):
        """Toggle Granular Debugger on/off"""
        is_enabled = self.enable_debugger_action.isChecked()
        self.debugger_enabled = is_enabled
        
        # Update menu text
        if is_enabled:
            self.enable_debugger_action.setText('✓ Granular Debugger Enabled')
            self.status_bar.showMessage("Granular Debugger ENABLED - Micro-granular logging of all TP/SL/Confluence calculations")
            QMessageBox.information(
                self,
                "Granular Debugger Enabled",
                "🔍 Granular Debugger is now ACTIVE\n\n"
                "Micro-granular logging will track:\n"
                "• GUI: Strategy loading and saving\n"
                "• Optimizer: TP calculation methods and results\n"
                "• Optimizer: SL calculation decisions and structures\n"
                "• Optimizer: Confluence scoring and block weighting\n"
                "• Optimizer: Config snapshots and parameter usage\n\n"
                f"GUI Log: logs/strategy_builder_debug.log\n"
                f"Optimizer Logs: logs/optimizer_debug_*.log"
            )
        else:
            self.enable_debugger_action.setText('Granular Debugger Disabled')
            self.status_bar.showMessage("Granular Debugger DISABLED")
        
        # Save preference for persistence
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        settings.setValue("debug/config_debugger_enabled", is_enabled)
    
    def view_debug_log(self):
        """Open debug log files in a viewer dialog (GUI + Optimizer logs)"""
        logs_dir = Path("logs")
        
        # Find all available debug logs
        gui_log = logs_dir / "strategy_builder_debug.log"
        optimizer_logs = sorted(logs_dir.glob("optimizer_debug_*.log"), reverse=True)
        
        available_logs = []
        if gui_log.exists():
            available_logs.append(("GUI Log", gui_log))
        for opt_log in optimizer_logs[:5]:  # Show last 5 optimizer logs
            available_logs.append((f"Optimizer: {opt_log.name}", opt_log))
        
        if not available_logs:
            QMessageBox.information(
                self,
                "No Log Files",
                f"No debug log files found.\n\n"
                "Debug logs are created when:\n"
                "1. Granular Debugger is enabled, AND\n"
                "2. Operations are performed (strategy loading or optimization)\n\n"
                "Enable Granular Debugger and run a test to generate logs."
            )
            return
        
        # If only one log, show it directly
        if len(available_logs) == 1:
            log_name, log_file = available_logs[0]
            self._show_single_log(log_name, log_file)
            return
        
        # Multiple logs - show selection dialog
        from PyQt6.QtWidgets import QListWidget, QDialogButtonBox
        
        select_dialog = QDialog(self, Qt.WindowType.Dialog)
        select_dialog.setWindowTitle("📄 Select Debug Log")
        select_dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout(select_dialog)
        
        label = QLabel("Multiple debug logs available. Select one to view:")
        label.setStyleSheet("font-size: 10pt; padding: 5px;")
        layout.addWidget(label)
        
        log_list = QListWidget()
        for log_name, _ in available_logs:
            log_list.addItem(log_name)
        log_list.setCurrentRow(0)
        log_list.itemDoubleClicked.connect(select_dialog.accept)
        layout.addWidget(log_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(select_dialog.accept)
        buttons.rejected.connect(select_dialog.reject)
        layout.addWidget(buttons)
        
        if select_dialog.exec() == QDialog.DialogCode.Accepted:
            selected_idx = log_list.currentRow()
            log_name, log_file = available_logs[selected_idx]
            self._show_single_log(log_name, log_file)
    
    def _show_single_log(self, log_name: str, log_file: Path):
        """Show a single debug log file"""
        try:
            # Read log file
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Create log viewer dialog
            dialog = QDialog(self, Qt.WindowType.Window)
            dialog.setWindowTitle(f"📄 {log_name}")
            dialog.setGeometry(150, 150, 1000, 700)
            
            layout = QVBoxLayout(dialog)
            
            # Info header
            info_label = QLabel(f"Log File: {log_file.absolute()}")
            info_label.setStyleSheet("font-size: 10pt; font-weight: bold; padding: 5px;")
            layout.addWidget(info_label)
            
            # Log content view
            log_text = QTextEdit()
            log_text.setReadOnly(True)
            log_text.setPlainText(log_content)
            log_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
            layout.addWidget(log_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            # Copy button
            copy_btn = QPushButton("📋 Copy to Clipboard")
            copy_btn.clicked.connect(lambda: self._copy_log_to_clipboard(log_content))
            button_layout.addWidget(copy_btn)
            
            # Refresh button
            refresh_btn = QPushButton("🔄 Refresh")
            refresh_btn.clicked.connect(lambda: self._refresh_log_viewer(log_file, log_text))
            button_layout.addWidget(refresh_btn)
            
            # Clear log button
            clear_btn = QPushButton("🗑️ Clear Log")
            clear_btn.clicked.connect(lambda: self._clear_debug_log(log_file, dialog))
            button_layout.addWidget(clear_btn)
            
            button_layout.addStretch()
            
            # Close button
            close_btn = QPushButton("✅ Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open log file:\n{e}"
            )
    
    def _copy_log_to_clipboard(self, log_content: str):
        """Copy log content to clipboard"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(log_content)
        QMessageBox.information(
            self,
            "Copied",
            "📋 Debug log copied to clipboard!"
        )
    
    def _refresh_log_viewer(self, log_file: Path, log_text: QTextEdit):
        """Refresh log viewer with latest content"""
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            log_text.setPlainText(log_content)
            self.status_bar.showMessage("Log refreshed")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to refresh log:\n{e}"
            )
    
    def _clear_debug_log(self, log_file: Path, parent_dialog):
        """Clear the debug log file"""
        reply = QMessageBox.question(
            parent_dialog,
            "Confirm Clear Log",
            "⚠️ Clear Debug Log?\n\n"
            "This will permanently delete all log entries.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Clear log file
                with open(log_file, 'w') as f:
                    f.write("")
                
                QMessageBox.information(
                    parent_dialog,
                    "Log Cleared",
                    "✅ Debug log has been cleared"
                )
                
                # Close the dialog
                parent_dialog.accept()
                
            except Exception as e:
                QMessageBox.critical(
                    parent_dialog,
                    "Error",
                    f"Failed to clear log:\n{e}"
                )
    
    def _append_output_line(self, line: str):
        """Append a line of output to the live output dialog (with optional DEBUG filtering)"""
        if hasattr(self, 'live_output_text'):
            # Check if this is a DEBUG line and if debug messages are hidden
            is_debug_line = 'DEBUG:' in line or line.strip().startswith('DEBUG')
            show_debug = self.show_debug_action.isChecked() if hasattr(self, 'show_debug_action') else False
            
            # Skip DEBUG lines if filtering is enabled
            if is_debug_line and not show_debug:
                return  # Don't append debug lines when hidden
            
            # Append line
            self.live_output_text.append(line)
            
            # Auto-scroll to bottom
            scrollbar = self.live_output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            # Update progress bar based on output
            self._update_progress_from_output(line)
    
    def _update_progress_from_output(self, line: str):
        """Update progress bar by parsing output for actual optimizer stages
        
        Progress allocation (Phase 3 is longest, gets 15%-89%):
        - 5% - Extracting blocks
        - 7% - Loading data
        - 9% - Building configs
        - 11% - Running optimization
        - 13% - Phase 1: Pre-compute
        - 14% - Phase 2: Merge
        - 15%-89% - Phase 3: Testing configs (LONGEST - 74% of progress bar)
        - 90% - Optimization complete
        - 95% - Validation
        - 98% - Exporting
        - 100% - Complete
        """
        import time
        
        if not hasattr(self, 'test_progress_bar'):
            return
        
        # Detect actual output patterns from universal_optimizer_v2.py
        # The optimizer uses "ULTRA HYBRID" mode - no per-config progress
        
        # Stage 1: Extracting blocks (5%)
        if 'Extracting building blocks' in line:
            self.test_progress_bar.setValue(5)
            self.test_progress_bar.setFormat("Extracting blocks... 5%")
            self.phase3_start_time = None  # Reset Phase 3 timer
        
        # Stage 2: Loading data (7%)
        elif 'Loading BTC data' in line:
            self.test_progress_bar.setValue(7)
            self.test_progress_bar.setFormat("Loading data... 7%")
        
        # Stage 3: Building configs (9%)
        elif 'Building optimization configurations' in line:
            self.test_progress_bar.setValue(9)
            self.test_progress_bar.setFormat("Building configs... 9%")
        
        # Stage 4: Running optimization (11%)
        elif 'Running ULTRA HYBRID optimization' in line or 'Running optimization' in line:
            self.test_progress_bar.setValue(11)
            elapsed = time.time() - self.test_start_time
            self.test_progress_bar.setFormat(f"Optimizing... 11% (~{int(elapsed)}s)")
        
        # Stage 5: Phase 1 - Pre-compute (13%)
        elif 'Phase 1:' in line:
            self.test_progress_bar.setValue(13)
            self.test_progress_bar.setFormat("Phase 1: Pre-compute... 13%")
            self.phase3_start_time = None  # Reset Phase 3 timer
        
        # Stage 6: Phase 2 - Merge (14%)
        elif 'Phase 2:' in line:
            self.test_progress_bar.setValue(14)
            self.test_progress_bar.setFormat("Phase 2: Merge... 14%")
            self.phase3_start_time = None  # Reset Phase 3 timer
        
        # Stage 7: Phase 3 - Testing configs (15%-89% - LONGEST PHASE)
        elif 'Phase 3:' in line:
            # Start Phase 3 - this is the longest phase, gets 74% of progress bar
            self.test_progress_bar.setValue(15)
            self.phase3_start_time = time.time()
            self.test_progress_bar.setFormat("Phase 3: Testing configs... 15%")
        
        # Granular updates during Phase 3 (every 5 seconds, increment 1%)
        elif hasattr(self, 'phase3_start_time') and self.phase3_start_time:
            current_value = self.test_progress_bar.value()
            if 15 <= current_value < 89:  # Only during Phase 3
                phase3_elapsed = time.time() - self.phase3_start_time
                # Increment 1% every 5 seconds, max 89%
                new_value = min(15 + int(phase3_elapsed / 5), 89)
                if new_value > current_value:
                    self.test_progress_bar.setValue(new_value)
                    self.test_progress_bar.setFormat(f"Phase 3: Testing configs... {new_value}% ({int(phase3_elapsed)}s)")
        
        # Stage 8: Optimization complete (90%)
        if 'Optimization complete in' in line:
            self.test_progress_bar.setValue(90)
            self.phase3_start_time = None  # Clear Phase 3 timer
            elapsed = time.time() - self.test_start_time
            self.test_progress_bar.setFormat(f"Processing results... 90% ({int(elapsed)}s)")
        
        # Stage 9: Validation (95%)
        elif 'Running institutional-grade result validation' in line:
            self.test_progress_bar.setValue(95)
            self.test_progress_bar.setFormat("Validating... 95%")
        
        # Stage 10: Exporting (98%)
        elif 'Exporting trade records' in line:
            self.test_progress_bar.setValue(98)
            self.test_progress_bar.setFormat("Exporting... 98%")
        
        # Final: Complete (100%)
        elif 'OPTIMIZATION COMPLETE' in line or 'Optimization successful' in line:
            self.test_progress_bar.setValue(100)
            elapsed = time.time() - self.test_start_time
            mins = int(elapsed / 60)
            secs = int(elapsed % 60)
            self.test_progress_bar.setFormat(f"✅ Complete! {mins}m {secs}s")
            self.phase3_start_time = None  # Clear Phase 3 timer
    
    def _on_backtest_finished(self, strategy_num: int, return_code: int):
        """Handle backtest completion with live output"""
        try:
            # Update status
            if return_code == 0:
                self.live_status_label.setText("✅ Backtest completed successfully!")
                self.live_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #4ec9b0;")
            else:
                self.live_status_label.setText(f"⚠️ Backtest completed with return code: {return_code}")
                self.live_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #f48771;")
            
            # Save test output log (keep max 2 per strategy)
            output_text = self.live_output_text.toPlainText()
            self._save_test_log(strategy_num, output_text)
            
            # Enable close button
            self.live_close_btn.setText("✅ Close")
            self.live_close_btn.setEnabled(True)
            
            # Disable stop button, enable action buttons
            self.stop_test_btn.setEnabled(False)
            self.stop_test_btn.setText("⏹ Test Complete")
            self.summary_btn.setEnabled(True)
            self.trades_btn.setEnabled(True)
            
            # Enable Compare only if 2+ logs exist
            logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
            if logs_dir.exists():
                log_files = list(logs_dir.glob("test_*.txt"))
                if len(log_files) >= 2:
                    self.compare_btn.setEnabled(True)
                else:
                    self.compare_btn.setEnabled(False)
                    self.compare_btn.setToolTip("Need 2+ test runs to compare")
            else:
                self.compare_btn.setEnabled(False)
            
            # Update status bar
            self.status_bar.showMessage("Backtest completed")
            
            # Check for errors
            if self.backtest_thread.error:
                self._append_output_line(f"\n❌ ERROR: {self.backtest_thread.error}\n")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error processing backtest results:\n{e}"
            )
        finally:
            self.status_bar.showMessage("Ready")
    
    def _stop_backtest(self):
        """Stop/Cancel the running backtest"""
        if hasattr(self, 'backtest_thread') and self.backtest_thread.isRunning():
            reply = QMessageBox.question(
                self.live_output_dialog,
                "Confirm Cancel",
                "Are you sure you want to cancel the running backtest?\n\n"
                "This will terminate the process.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # First, terminate the subprocess
                self._append_output_line("\n🛑 Stopping subprocess...\n")
                self.backtest_thread.stop_process()
                
                # Then terminate the thread
                self.backtest_thread.terminate()
                self.backtest_thread.wait()
                
                self._append_output_line("🛑 Test cancelled by user\n")
                self.live_status_label.setText("🛑 Test cancelled")
                self.live_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #f48771;")
                self.live_close_btn.setText("✅ Close")
                self.live_close_btn.setEnabled(True)
                self.stop_test_btn.setEnabled(False)
                self.status_bar.showMessage("Test cancelled")
        else:
            QMessageBox.information(
                self.live_output_dialog,
                "Not Running",
                "No backtest is currently running."
            )
    
    def _show_summary_results(self):
        """Extract and show only summary results from output"""
        if not hasattr(self, 'live_output_text'):
            return
        
        full_output = self.live_output_text.toPlainText()
        lines = full_output.split('\n')
        
        # Extract structured summary sections
        summary_lines = []
        capturing = False
        section_started = False
        
        for i, line in enumerate(lines):
            # Start capturing at TEST PARAMETERS
            if 'TEST PARAMETERS:' in line:
                capturing = True
                section_started = True
                summary_lines.append(line)
                continue
            
            # Stop capturing after TRADE RECORD line
            if capturing and 'TRADE RECORD:' in line:
                summary_lines.append(line)
                # Check if there are more configs (#2, #3, etc.)
                # Look ahead to see if there's another config
                found_next_config = False
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].startswith('#') and 'Configuration' in lines[j]:
                        found_next_config = True
                        summary_lines.append('')  # Add blank line before next config
                        break
                
                if not found_next_config:
                    capturing = False
                continue
            
            # Capture lines while in capturing mode
            if capturing:
                summary_lines.append(line)
        
        # If no structured summary found, try alternate extraction
        if not section_started:
            summary_lines = []
            in_results = False
            
            for line in lines:
                # Look for results sections
                if any(marker in line for marker in [
                    '═══', 'RESULTS', 'PERFORMANCE', 'Best Configuration',
                    'TRADING PERFORMANCE', 'FINANCIAL RESULTS', 'RISK METRICS'
                ]):
                    in_results = True
                
                if in_results:
                    # Include lines with content or tree characters
                    if line.strip() or any(char in line for char in ['├', '└', '│', '─', '═']):
                        summary_lines.append(line)
                    # Stop at certain end markers
                    elif 'Saving results' in line or 'Complete!' in line:
                        break
        
        if not summary_lines or len(summary_lines) < 5:
            summary_text = "⚠️ No summary information found in output yet.\n\nPossible reasons:\n• Test is still running\n• Test failed before generating summary\n• Output format has changed\n\nCheck the full output for details."
        else:
            summary_text = '\n'.join(summary_lines)
        
        # Show in dialog
        dialog = QDialog(self.live_output_dialog, Qt.WindowType.Window)
        dialog.setWindowTitle("📊 Summary Results")
        dialog.resize(900, 700)
        
        layout = QVBoxLayout(dialog)
        
        # Add header
        header = QLabel("Summary of Test Results")
        header.setStyleSheet("font-size: 12pt; font-weight: bold; color: #4ec9b0; padding: 5px;")
        layout.addWidget(header)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(summary_text)
        text_edit.setStyleSheet("font-family: monospace; font-size: 10pt;")
        layout.addWidget(text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy Summary")
        copy_btn.setToolTip("Copy summary to clipboard")
        copy_btn.clicked.connect(lambda: self._copy_text_to_clipboard(summary_text, "Summary"))
        button_layout.addWidget(copy_btn)
        
        # Add Compare button (enabled only if previous test exists)
        compare_summary_btn = QPushButton("⚖️ Compare")
        compare_summary_btn.setToolTip("Compare with previous test summary")
        
        # Check if comparison is possible
        if hasattr(self, 'backtest_thread'):
            strategy_num = self.backtest_thread.strategy_num
            logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
            if logs_dir.exists():
                log_files = sorted(logs_dir.glob("test_*.txt"), reverse=True)
                if len(log_files) >= 2:
                    compare_summary_btn.setEnabled(True)
                    compare_summary_btn.clicked.connect(lambda: self._compare_summary_results(dialog))
                else:
                    compare_summary_btn.setEnabled(False)
                    compare_summary_btn.setToolTip("Need 2+ test runs to compare")
            else:
                compare_summary_btn.setEnabled(False)
                compare_summary_btn.setToolTip("No previous tests found")
        else:
            compare_summary_btn.setEnabled(False)
        
        button_layout.addWidget(compare_summary_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("✅ Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.show()
    
    def _compare_summary_results(self, summary_dialog):
        """Compare current summary with previous test summary - highlighting only key financial metrics"""
        if not hasattr(self, 'backtest_thread'):
            return
        
        strategy_num = self.backtest_thread.strategy_num
        logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
        
        if not logs_dir.exists():
            QMessageBox.warning(
                summary_dialog,
                "No Logs",
                "No test logs found to compare."
            )
            return
        
        # Get all log files sorted by timestamp (newest first)
        log_files = sorted(logs_dir.glob("test_*.txt"), reverse=True)
        
        if len(log_files) < 2:
            QMessageBox.warning(
                summary_dialog,
                "Insufficient Data",
                f"Need at least 2 test runs to compare.\nCurrently have: {len(log_files)}"
            )
            return
        
        try:
            # Determine which logs to compare
            is_loaded_test = "LOADED TEST RESULTS" in self.live_output_dialog.windowTitle()
            
            if is_loaded_test:
                # Compare the two most recent logs
                newer_file = log_files[0]
                older_file = log_files[1]
                
                with open(newer_file, 'r') as f:
                    newer_full = f.read()
                with open(older_file, 'r') as f:
                    older_full = f.read()
                    
                newer_label = f"Most Recent: {newer_file.name}"
                older_label = f"Previous: {older_file.name}"
            else:
                # Compare: most recent saved log [0] vs previous log [1]
                # The test just completed was saved to log_files[0]
                newer_file = log_files[0]
                older_file = log_files[1]
                
                # Read both from saved files for consistency
                with open(newer_file, 'r') as f:
                    newer_full = f.read()
                with open(older_file, 'r') as f:
                    older_full = f.read()
                    
                newer_label = f"Current Test: {newer_file.name}"
                older_label = f"Previous Test: {older_file.name}"
            
            # Extract summaries from both
            def extract_summary(text):
                """Extract only summary section from full output"""
                lines = text.split('\n')
                summary_lines = []
                capturing = False
                
                for i, line in enumerate(lines):
                    if 'TEST PARAMETERS:' in line:
                        capturing = True
                        summary_lines.append(line)
                        continue
                    
                    if capturing and 'TRADE RECORD:' in line:
                        summary_lines.append(line)
                        # Check if there are more configs
                        found_next_config = False
                        for j in range(i+1, min(i+10, len(lines))):
                            if lines[j].startswith('#') and 'Configuration' in lines[j]:
                                found_next_config = True
                                summary_lines.append('')
                                break
                        
                        if not found_next_config:
                            capturing = False
                        continue
                    
                    if capturing:
                        summary_lines.append(line)
                
                return '\n'.join(summary_lines) if summary_lines else text
            
            newer_summary = extract_summary(newer_full)
            older_summary = extract_summary(older_full)
            
            # Create comparison dialog
            dialog = QDialog(summary_dialog, Qt.WindowType.Window)
            dialog.setWindowTitle(f"⚖️ Compare Summary - Strategy #{strategy_num:03d}")
            dialog.resize(1400, 800)
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)
            
            # Create splitter for side-by-side views
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Left pane (newer test)
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_layout.setContentsMargins(0, 0, 0, 0)
            
            left_label = QLabel(f"🆕 {newer_label}")
            left_label.setStyleSheet("font-size: 10pt; font-weight: bold; background: #2d2d2d; padding: 5px;")
            left_layout.addWidget(left_label)
            
            newer_text_widget = QTextEdit()
            newer_text_widget.setReadOnly(True)
            newer_text_widget.setStyleSheet("font-family: monospace; font-size: 9pt;")
            left_layout.addWidget(newer_text_widget)
            
            splitter.addWidget(left_widget)
            
            # Right pane (older test)
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)
            
            right_label = QLabel(f"📅 {older_label}")
            right_label.setStyleSheet("font-size: 10pt; font-weight: bold; background: #2d2d2d; padding: 5px;")
            right_layout.addWidget(right_label)
            
            older_text_widget = QTextEdit()
            older_text_widget.setReadOnly(True)
            older_text_widget.setStyleSheet("font-family: monospace; font-size: 9pt;")
            right_layout.addWidget(older_text_widget)
            
            splitter.addWidget(right_widget)
            
            # Set equal sizes
            splitter.setSizes([700, 700])
            
            layout.addWidget(splitter)
            
            # Apply selective highlighting for only key financial metrics
            newer_highlighted, older_highlighted = self._highlight_summary_differences(
                newer_summary, older_summary
            )
            
            newer_text_widget.setHtml(newer_highlighted)
            older_text_widget.setHtml(older_highlighted)
            
            # Synchronize scrollbars
            self._sync_scrollbars(newer_text_widget, older_text_widget)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            copy_btn = QPushButton("📋 Copy Current Summary")
            copy_btn.setToolTip("Copy current summary to clipboard")
            copy_btn.clicked.connect(lambda: self._copy_text_to_clipboard(newer_summary, "Summary"))
            button_layout.addWidget(copy_btn)
            
            button_layout.addStretch()
            
            close_btn = QPushButton("✅ Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(
                summary_dialog,
                "Error",
                f"Failed to compare summaries:\n{e}"
            )
    
    def _highlight_summary_differences(self, newer_text: str, older_text: str):
        """Highlight differences - ONLY for specific financial metrics"""
        import re
        
        # Define metrics that should be highlighted when different
        financial_metrics = [
            'Risk per trade', 'Risk Per Trade',
            'Leverage', 'Max Leverage',
            'Total Trades',
            'Winning Trades',
            'Losing Trades',
            'Avg Win', 'Average Win',
            'Avg Loss', 'Average Loss',
            'Largest Win',
            'Largest Loss',
            'Gross PnL',
            'Total Fees',
            'Net PnL',
            'Net Return',
            'Starting Capital',
            'Final Capital',
            'Profit Factor',
            'Sharpe Ratio',
            'Max Drawdown', 'Maximum Drawdown',
            'Risk-Adjusted Return', 'Risk-Adjusted'
        ]
        
        def extract_metric_value(line: str):
            """Extract metric name and value from a line"""
            match = re.search(r'([A-Za-z\s/-]+):\s*([^\n]+)$', line)
            if match:
                metric_name = match.group(1).strip()
                value = match.group(2).strip()
                return (metric_name, value)
            return None
        
        def is_financial_metric(metric_name: str) -> bool:
            """Check if metric is in our financial metrics list"""
            metric_lower = metric_name.lower()
            for fm in financial_metrics:
                if fm.lower() in metric_lower or metric_lower in fm.lower():
                    return True
            return False
        
        # Build metric dictionaries for both texts
        newer_metrics = {}
        older_metrics = {}
        
        for line in newer_text.split('\n'):
            result = extract_metric_value(line)
            if result:
                newer_metrics[result[0]] = result[1]
        
        for line in older_text.split('\n'):
            result = extract_metric_value(line)
            if result:
                older_metrics[result[0]] = result[1]
        
        # Build HTML with selective highlighting
        newer_html = '<pre style="margin: 0; padding: 5px;">'
        older_html = '<pre style="margin: 0; padding: 5px;">'
        
        newer_lines = newer_text.split('\n')
        older_lines = older_text.split('\n')
        max_lines = max(len(newer_lines), len(older_lines))
        
        for i in range(max_lines):
            newer_line = newer_lines[i] if i < len(newer_lines) else ''
            older_line = older_lines[i] if i < len(older_lines) else ''
            
            # Escape HTML
            newer_escaped = newer_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            older_escaped = older_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Extract metrics from both lines
            newer_metric = extract_metric_value(newer_line)
            older_metric = extract_metric_value(older_line)
            
            # Only highlight if:
            # 1. It's a financial metric
            # 2. Values differ
            should_highlight = False
            if newer_metric and is_financial_metric(newer_metric[0]):
                if older_metric and newer_metric[0] == older_metric[0]:
                    # Same metric name, check if values differ
                    if newer_metric[1] != older_metric[1]:
                        should_highlight = True
                elif newer_metric[0] in older_metrics:
                    # Metric exists elsewhere with different value
                    if older_metrics[newer_metric[0]] != newer_metric[1]:
                        should_highlight = True
            elif older_metric and is_financial_metric(older_metric[0]):
                if older_metric[0] in newer_metrics:
                    # Metric exists elsewhere with different value
                    if newer_metrics[older_metric[0]] != older_metric[1]:
                        should_highlight = True
            
            # Apply highlighting
            if should_highlight:
                newer_html += f'<span style="background-color: #2d5016; color: #a5d6a7;">{newer_escaped}</span>\n'
                older_html += f'<span style="background-color: #5d2929; color: #f48771;">{older_escaped}</span>\n'
            else:
                newer_html += f'{newer_escaped}\n'
                older_html += f'{older_escaped}\n'
        
        newer_html += '</pre>'
        older_html += '</pre>'
        
        return newer_html, older_html
    
    def _copy_text_to_clipboard(self, text: str, label: str = "Text"):
        """Copy provided text to clipboard"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        if hasattr(self, 'live_output_dialog'):
            QMessageBox.information(
                self.live_output_dialog,
                "Copied",
                f"📋 {label} copied to clipboard!"
            )
    
    def _show_trades_window(self):
        """Display trades in Excel-like sortable table"""
        if not hasattr(self, 'backtest_thread'):
            return
        
        strategy_num = self.backtest_thread.strategy_num
        
        # Load strategy config to get name
        config = self.registry.load_strategy(strategy_num)
        if not config:
            QMessageBox.warning(
                self.live_output_dialog,
                "Config Not Found",
                f"Could not load strategy #{strategy_num:03d} configuration"
            )
            return
        
        # Find trades files
        strategy_name = config.strategy_name.lower().replace(' ', '_')
        results_dir = Path(f"data/reports/strategies/universal_optimizer/strategy_{strategy_num:03d}_{strategy_name}")
        
        if not results_dir.exists():
            QMessageBox.warning(
                self.live_output_dialog,
                "Results Not Found",
                f"Results directory not found:\n{results_dir}\n\n"
                "Wait for test to complete."
            )
            return
        
        # Look for config_*_trades.csv files (multiple configs tested)
        trades_files = list(results_dir.glob("config_*_trades.csv"))
        
        if not trades_files:
            QMessageBox.warning(
                self.live_output_dialog,
                "Trades Not Found",
                f"No trades files found in:\n{results_dir}\n\n"
                "Looking for: config_*_trades.csv\n\n"
                "Wait for test to complete or check if results were generated."
            )
            return
        
        try:
            import pandas as pd
            
            # Load and combine all trades from all configs
            all_trades = []
            for trades_file in sorted(trades_files):
                df = pd.read_csv(trades_file)
                # Add config ID from filename
                config_id = trades_file.stem.split('_')[1]  # Extract XXX from config_XXX_trades
                df['config_id'] = config_id
                all_trades.append(df)
            
            # Combine all trades
            df_combined = pd.concat(all_trades, ignore_index=True)
            
            # Rename 'reason' column to 'exit_reason' if it exists
            if 'reason' in df_combined.columns:
                df_combined.rename(columns={'reason': 'exit_reason'}, inplace=True)
            
            # Create trades window
            dialog = QDialog(self.live_output_dialog, Qt.WindowType.Window)
            dialog.setWindowTitle(f"📈 Trades - Strategy #{strategy_num:03d}")
            dialog.resize(1600, 900)  # Larger window to avoid horizontal scrolling
            
            layout = QVBoxLayout(dialog)
            
            # Store full dataframe for filtering
            self.trades_df_full = df_combined
            self.trades_dialog = dialog
            
            # Configuration filter checkboxes
            filter_layout = QHBoxLayout()
            filter_label = QLabel("📊 Filter by Configuration:")
            filter_label.setStyleSheet("font-weight: bold;")
            filter_layout.addWidget(filter_label)
            
            # Get unique config IDs
            unique_configs = sorted(df_combined['config_id'].unique())
            self.config_checkboxes = {}
            
            for idx, config_id in enumerate(unique_configs):
                checkbox = QCheckBox(f"Config {config_id}")
                checkbox.setChecked(idx == 0)  # Only first config checked by default
                checkbox.stateChanged.connect(lambda state, dialog=dialog: self._update_trades_filter(dialog))
                self.config_checkboxes[config_id] = checkbox
                filter_layout.addWidget(checkbox)
            
            filter_layout.addStretch()
            layout.addLayout(filter_layout)
            
            # Stats summary (will be updated by filter)
            self.trades_stats_label = QLabel()
            self.trades_stats_label.setStyleSheet("font-family: monospace; background: #2d2d2d; padding: 8px; font-size: 10pt;")
            layout.addWidget(self.trades_stats_label)
            
            # Create table widget for Excel-like view
            self.trades_table = QTableWidget()
            table = self.trades_table

            table.setSortingEnabled(True)  # Enable column sorting
            table.setAlternatingRowColors(True)
            
            # Set data
            table.setRowCount(len(df_combined))
            table.setColumnCount(len(df_combined.columns))
            table.setHorizontalHeaderLabels(df_combined.columns.tolist())
            
            # Populate table
            for row_idx, row in df_combined.iterrows():
                for col_idx, value in enumerate(row):
                    # Format numeric values
                    if isinstance(value, (int, float)):
                        if 'pnl' in df_combined.columns[col_idx].lower():
                            # Format PnL with color
                            item = QTableWidgetItem(f"${value:.2f}")
                            if value > 0:
                                item.setForeground(Qt.GlobalColor.green)
                            elif value < 0:
                                item.setForeground(Qt.GlobalColor.red)
                        else:
                            item = QTableWidgetItem(f"{value:.4f}" if isinstance(value, float) else str(value))
                    else:
                        item = QTableWidgetItem(str(value))
                    
                    # Make cells read-only
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table.setItem(row_idx, col_idx, item)
            
            # Auto-resize columns to content with spacing
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setDefaultSectionSize(120)  # Minimum width for columns
            table.horizontalHeader().setStretchLastSection(False)
            
            # Add spacing between columns for better readability
            table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #3c3c3c;
                }
                QTableWidget::item {
                    padding: 5px 10px;  /* Vertical and horizontal padding */
                }
            """)
            
            layout.addWidget(table)
            
            # Apply initial filter (show only first config)
            self._update_trades_filter(dialog)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            # Export button
            export_btn = QPushButton("📥 Export CSV")
            export_btn.setToolTip("Export trades to CSV file")
            export_btn.clicked.connect(lambda: self._export_trades(df_combined, strategy_num))
            button_layout.addWidget(export_btn)
            
            # Copy button
            copy_btn = QPushButton("📋 Copy Selected")
            copy_btn.setToolTip("Copy selected rows to clipboard")
            copy_btn.clicked.connect(lambda: self._copy_selected_rows(table))
            button_layout.addWidget(copy_btn)
            
            button_layout.addStretch()
            
            # Close button
            close_btn = QPushButton("✅ Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(
                self.live_output_dialog,
                "Error",
                f"Failed to load trades:\n{e}"
            )
    
    def _export_trades(self, df, strategy_num: int):
        """Export trades DataFrame to CSV"""
        from PyQt6.QtWidgets import QFileDialog
        
        default_filename = f"strategy_{strategy_num:03d}_all_trades.csv"
        filename, _ = QFileDialog.getSaveFileName(
            self.live_output_dialog,
            "Export Trades",
            default_filename,
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                df.to_csv(filename, index=False)
                QMessageBox.information(
                    self.live_output_dialog,
                    "Exported",
                    f"✅ Trades exported successfully to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.live_output_dialog,
                    "Export Failed",
                    f"Failed to export trades:\n{e}"
                )
    
    def _copy_selected_rows(self, table: QTableWidget):
        """Copy selected rows from table to clipboard"""
        from PyQt6.QtWidgets import QApplication
        
        selected_ranges = table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(
                self.live_output_dialog,
                "No Selection",
                "Please select rows to copy."
            )
            return
        
        # Get selected data
        rows = set()
        for selected_range in selected_ranges:
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                rows.add(row)
        
        # Build CSV text
        lines = []
        
        # Header
        headers = []
        for col in range(table.columnCount()):
            headers.append(table.horizontalHeaderItem(col).text())
        lines.append(','.join(headers))
        
        # Data rows
        for row in sorted(rows):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else '')
            lines.append(','.join(row_data))
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(lines))
        
        QMessageBox.information(
            self.live_output_dialog,
            "Copied",
            f"📋 {len(rows)} row(s) copied to clipboard!"
        )
    
    def _update_trades_filter(self, dialog):
        """Update trades table based on selected configuration checkboxes"""
        if not hasattr(self, 'trades_df_full') or not hasattr(self, 'config_checkboxes'):
            return
        
        import pandas as pd
        
        # Get selected config IDs
        selected_configs = []
        for config_id, checkbox in self.config_checkboxes.items():
            if checkbox.isChecked():
                selected_configs.append(config_id)
        
        # Filter dataframe
        if selected_configs:
            df_filtered = self.trades_df_full[self.trades_df_full['config_id'].isin(selected_configs)]
        else:
            # If none selected, show empty table
            df_filtered = pd.DataFrame(columns=self.trades_df_full.columns)
        
        # Update stats
        if len(df_filtered) > 0:
            wins = len(df_filtered[df_filtered['pnl'] > 0])
            losses = len(df_filtered[df_filtered['pnl'] <= 0])
            win_rate = (wins / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
            total_pnl = df_filtered['pnl'].sum()
            avg_trade = df_filtered['pnl'].mean()
            
            stats_text = f"""📊 Trades Summary - {len(selected_configs)} Configuration(s) Selected
Total Trades: {len(df_filtered)} | Wins: {wins} | Losses: {losses}
Win Rate: {win_rate:.1f}% | Total PnL: ${total_pnl:.2f} | Avg Trade: ${avg_trade:.2f}
"""
        else:
            stats_text = "📊 No configurations selected - Select at least one configuration to view trades"
        
        self.trades_stats_label.setText(stats_text)
        
        # Update table
        table = self.trades_table
        table.setSortingEnabled(False)  # Disable while updating
        table.setRowCount(len(df_filtered))
        
        # Clear and repopulate table
        for row_idx, (_, row) in enumerate(df_filtered.iterrows()):
            for col_idx, value in enumerate(row):
                # Format numeric values
                if isinstance(value, (int, float)):
                    if 'pnl' in df_filtered.columns[col_idx].lower():
                        # Format PnL with color
                        item = QTableWidgetItem(f"${value:.2f}")
                        if value > 0:
                            item.setForeground(Qt.GlobalColor.green)
                        elif value < 0:
                            item.setForeground(Qt.GlobalColor.red)
                    else:
                        item = QTableWidgetItem(f"{value:.4f}" if isinstance(value, float) else str(value))
                else:
                    item = QTableWidgetItem(str(value))
                
                # Make cells read-only
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_idx, col_idx, item)
        
        table.setSortingEnabled(True)  # Re-enable sorting
    
    def _compare_results(self):
        """Compare current results with previous test"""
        if not hasattr(self, 'backtest_thread'):
            return
        
        strategy_num = self.backtest_thread.strategy_num
        logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
        
        if not logs_dir.exists():
            QMessageBox.warning(
                self.live_output_dialog,
                "No Logs",
                "No test logs found to compare."
            )
            return
        
        # Get all log files sorted by timestamp (newest first)
        log_files = sorted(logs_dir.glob("test_*.txt"), reverse=True)
        
        if len(log_files) < 2:
            QMessageBox.warning(
                self.live_output_dialog,
                "Insufficient Data",
                f"Need at least 2 test runs to compare.\nCurrently have: {len(log_files)}"
            )
            return
        
        try:
            # Determine which logs to compare
            # If current view is loaded (not running), compare log 0 vs log 1
            # If current view is fresh test, use current output vs log 0
            
            is_loaded_test = "LOADED TEST RESULTS" in self.live_output_dialog.windowTitle()
            
            if is_loaded_test:
                # Compare the two most recent logs
                with open(log_files[0], 'r') as f:
                    newer_content = f.read()
                with open(log_files[1], 'r') as f:
                    older_content = f.read()
                newer_label = f"Most Recent: {log_files[0].name}"
                older_label = f"Previous: {log_files[1].name}"
            else:
                # Compare current output vs SECOND most recent saved log
                # (log_files[0] is the current test that was just saved, so compare to [1])
                newer_content = self.live_output_text.toPlainText()
                
                # Need at least 2 logs to compare (current + previous)
                if len(log_files) < 2:
                    QMessageBox.warning(
                        self.live_output_dialog,
                        "Insufficient Data",
                        "Need at least 2 test runs to compare.\n"
                        "Run another test to enable comparison."
                    )
                    return
                
                with open(log_files[1], 'r') as f:
                    older_content = f.read()
                newer_label = "Current Test (Just Completed)"
                older_label = f"Previous Test: {log_files[1].name}"
            
            # Strip log file headers for clean comparison (both sides same format)
            newer_content = self._strip_log_header(newer_content)
            older_content = self._strip_log_header(older_content)
            
            # Create comparison dialog
            self._create_comparison_dialog(
                newer_content, older_content,
                newer_label, older_label,
                strategy_num
            )
            
        except Exception as e:
            QMessageBox.critical(
                self.live_output_dialog,
                "Error",
                f"Failed to load test logs for comparison:\n{e}"
            )
    
    def _create_comparison_dialog(self, newer_text: str, older_text: str, 
                                   newer_label: str, older_label: str, strategy_num: int):
        """Create side-by-side comparison dialog with scroll sync and highlighting"""
        dialog = QDialog(self.live_output_dialog, Qt.WindowType.Window)
        dialog.setWindowTitle(f"⚖️ Compare Tests - Strategy #{strategy_num:03d}")
        dialog.resize(1400, 800)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        layout.setSpacing(5)  # Reduce spacing between widgets
        
        # Create splitter for side-by-side views (no header - titles are in panes)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left pane (newer test)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_label = QLabel(f"🆕 {newer_label}")
        left_label.setStyleSheet("font-size: 10pt; font-weight: bold; background: #2d2d2d; padding: 5px;")
        left_layout.addWidget(left_label)
        
        self.compare_left_text = QTextEdit()
        self.compare_left_text.setReadOnly(True)
        self.compare_left_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
        left_layout.addWidget(self.compare_left_text)
        
        splitter.addWidget(left_widget)
        
        # Right pane (older test)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_label = QLabel(f"📅 {older_label}")
        right_label.setStyleSheet("font-size: 10pt; font-weight: bold; background: #2d2d2d; padding: 5px;")
        right_layout.addWidget(right_label)
        
        self.compare_right_text = QTextEdit()
        self.compare_right_text.setReadOnly(True)
        self.compare_right_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
        right_layout.addWidget(self.compare_right_text)
        
        splitter.addWidget(right_widget)
        
        # Set equal sizes
        splitter.setSizes([700, 700])
        
        layout.addWidget(splitter)
        
        # Extract and highlight differences
        newer_highlighted, older_highlighted = self._highlight_differences(newer_text, older_text)
        
        self.compare_left_text.setHtml(newer_highlighted)
        self.compare_right_text.setHtml(older_highlighted)
        
        # Synchronize scrollbars
        self._sync_scrollbars(self.compare_left_text, self.compare_right_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        stats_btn = QPushButton("📊 Key Metrics")
        stats_btn.setToolTip("Show key metric comparison")
        stats_btn.clicked.connect(lambda: self._show_metrics_comparison(strategy_num))
        button_layout.addWidget(stats_btn)
        
        config_btn = QPushButton("⚙️ Compare Configurations")
        config_btn.setToolTip("Compare strategy configuration files")
        config_btn.clicked.connect(lambda: self._compare_strategy_configurations(strategy_num))
        button_layout.addWidget(config_btn)
        
        button_layout.addStretch()
        
        restore_btn = QPushButton("⏮️ Restore Previous Config")
        restore_btn.setToolTip("Restore the configuration from the previous test")
        restore_btn.clicked.connect(lambda: self._restore_previous_config(strategy_num, dialog))
        button_layout.addWidget(restore_btn)
        
        close_btn = QPushButton("✅ Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.show()
    
    def _compare_strategy_configurations(self, strategy_num: int):
        """Compare strategy configuration snapshots from test runs"""
        try:
            # Get test logs directory
            logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
            
            if not logs_dir.exists():
                QMessageBox.warning(
                    self,
                    "No Config Snapshots",
                    f"No config snapshots found for Strategy #{strategy_num:03d}\n\n"
                    "Config snapshots are saved automatically when you run tests.\n"
                    "Run at least 2 tests to compare configurations."
                )
                return
            
            # Get all config snapshot files sorted by timestamp (newest first)
            config_files = sorted(logs_dir.glob("config_*.yaml"), reverse=True)
            
            if len(config_files) < 2:
                QMessageBox.warning(
                    self,
                    "Insufficient Snapshots",
                    f"Need at least 2 config snapshots to compare.\n"
                    f"Currently have: {len(config_files)}\n\n"
                    "Config snapshots are saved when you run tests.\n"
                    "Run another test to enable configuration comparison."
                )
                return
            
            # Determine which configs to compare (same logic as result comparison)
            is_loaded_test = "LOADED TEST RESULTS" in self.live_output_dialog.windowTitle()
            
            if is_loaded_test:
                # Compare the two most recent snapshots
                newer_config_file = config_files[0]
                older_config_file = config_files[1]
                newer_label = f"Most Recent: {newer_config_file.name}"
                older_label = f"Previous: {older_config_file.name}"
            else:
                # Compare most recent (just saved) vs second most recent
                newer_config_file = config_files[0]
                older_config_file = config_files[1]
                newer_label = f"Current Test: {newer_config_file.name}"
                older_label = f"Previous Test: {older_config_file.name}"
            
            # Read both config files
            import yaml
            
            with open(newer_config_file, 'r') as f:
                newer_config = yaml.safe_load(f)
            
            with open(older_config_file, 'r') as f:
                older_config = yaml.safe_load(f)
            
            # Convert to formatted YAML text for comparison
            current_config_text = yaml.dump(newer_config, default_flow_style=False, sort_keys=False)
            older_config_text = yaml.dump(older_config, default_flow_style=False, sort_keys=False)
            
            # Create comparison dialog
            dialog = QDialog(self, Qt.WindowType.Window)
            dialog.setWindowTitle(f"⚙️ Compare Strategy Configurations - Strategy #{strategy_num:03d}")
            dialog.resize(1400, 800)
            
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)
            
            # Create splitter for side-by-side views
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Left pane (current config)
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_layout.setContentsMargins(0, 0, 0, 0)
            
            left_label = QLabel(f"🆕 Current Configuration")
            left_label.setStyleSheet("font-size: 10pt; font-weight: bold; background: #2d2d2d; padding: 5px;")
            left_layout.addWidget(left_label)
            
            left_text = QTextEdit()
            left_text.setReadOnly(True)
            left_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
            left_layout.addWidget(left_text)
            
            splitter.addWidget(left_widget)
            
            # Right pane (saved/previous config)
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)
            
            right_label = QLabel(f"📅 Previous Configuration")
            right_label.setStyleSheet("font-size: 10pt; font-weight: bold; background: #2d2d2d; padding: 5px;")
            right_layout.addWidget(right_label)
            
            right_text = QTextEdit()
            right_text.setReadOnly(True)
            right_text.setStyleSheet("font-family: monospace; font-size: 9pt;")
            right_layout.addWidget(right_text)
            
            splitter.addWidget(right_widget)
            
            # Set equal sizes
            splitter.setSizes([700, 700])
            
            layout.addWidget(splitter)
            
            # Highlight differences
            current_highlighted, older_highlighted = self._highlight_config_differences(
                current_config_text, older_config_text
            )
            
            left_text.setHtml(current_highlighted)
            right_text.setHtml(older_highlighted)
            
            # Synchronize scrollbars
            self._sync_scrollbars(left_text, right_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            copy_btn = QPushButton("📋 Copy Current Config")
            copy_btn.setToolTip("Copy current configuration to clipboard")
            copy_btn.clicked.connect(lambda: self._copy_text_to_clipboard(current_config_text, "Configuration"))
            button_layout.addWidget(copy_btn)
            
            button_layout.addStretch()
            
            restore_btn = QPushButton("⏮️ Restore Previous Config")
            restore_btn.setToolTip("Restore the configuration from the previous test")
            restore_btn.clicked.connect(lambda: self._restore_previous_config(strategy_num, dialog))
            button_layout.addWidget(restore_btn)
            
            close_btn = QPushButton("✅ Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to compare configurations:\n{e}"
            )
    
    def _highlight_config_differences(self, current_text: str, older_text: str):
        """Highlight differences between two configuration files"""
        current_lines = current_text.split('\n')
        older_lines = older_text.split('\n')
        
        # Build HTML with highlighting
        current_html = '<pre style="margin: 0; padding: 5px;">'
        older_html = '<pre style="margin: 0; padding: 5px;">'
        
        max_lines = max(len(current_lines), len(older_lines))
        
        for i in range(max_lines):
            current_line = current_lines[i] if i < len(current_lines) else ''
            older_line = older_lines[i] if i < len(older_lines) else ''
            
            # Escape HTML
            current_escaped = current_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            older_escaped = older_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Check for differences
            if current_line != older_line:
                # Highlight changed lines - use orange/yellow for config differences
                current_html += f'<span style="background-color: #4a3c1f; color: #ffcc80;">{current_escaped}</span>\n'
                older_html += f'<span style="background-color: #3a2c2f; color: #f48771;">{older_escaped}</span>\n'
            else:
                current_html += f'{current_escaped}\n'
                older_html += f'{older_escaped}\n'
        
        current_html += '</pre>'
        older_html += '</pre>'
        
        return current_html, older_html
    
    def _highlight_differences(self, newer_text: str, older_text: str):
        """Highlight differences between two test outputs - smart metric comparison"""
        import re
        
        def extract_metric_value(line: str):
            """Extract metric name and value from a line like '├─ Total Trades: 9'"""
            # Match patterns like "Total Trades: 9" or "Net PnL: $+607.99"
            match = re.search(r'([A-Za-z\s]+):\s*([^\n]+)$', line)
            if match:
                metric_name = match.group(1).strip()
                value = match.group(2).strip()
                return (metric_name, value)
            return None
        
        # Build metric dictionaries for both texts
        newer_metrics = {}
        older_metrics = {}
        
        for line in newer_text.split('\n'):
            result = extract_metric_value(line)
            if result:
                newer_metrics[result[0]] = result[1]
        
        for line in older_text.split('\n'):
            result = extract_metric_value(line)
            if result:
                older_metrics[result[0]] = result[1]
        
        # Build HTML with smart highlighting
        newer_html = '<pre style="margin: 0; padding: 5px;">'
        older_html = '<pre style="margin: 0; padding: 5px;">'
        
        newer_lines = newer_text.split('\n')
        older_lines = older_text.split('\n')
        max_lines = max(len(newer_lines), len(older_lines))
        
        for i in range(max_lines):
            newer_line = newer_lines[i] if i < len(newer_lines) else ''
            older_line = older_lines[i] if i < len(older_lines) else ''
            
            # Escape HTML
            newer_escaped = newer_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            older_escaped = older_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Extract metrics from both lines
            newer_metric = extract_metric_value(newer_line)
            older_metric = extract_metric_value(older_line)
            
            # Smart comparison: only highlight if METRIC VALUES differ
            should_highlight = False
            if newer_metric and older_metric:
                # Both lines have metrics - compare values
                if newer_metric[0] == older_metric[0]:  # Same metric name
                    if newer_metric[1] != older_metric[1]:  # Different values
                        should_highlight = True
            elif newer_metric:
                # Check if this metric exists elsewhere in older text with different value
                metric_name = newer_metric[0]
                if metric_name in older_metrics and older_metrics[metric_name] != newer_metric[1]:
                    should_highlight = True
            elif older_metric:
                # Check if this metric exists elsewhere in newer text with different value
                metric_name = older_metric[0]
                if metric_name in newer_metrics and newer_metrics[metric_name] != older_metric[1]:
                    should_highlight = True
            
            # Apply highlighting
            if should_highlight:
                newer_html += f'<span style="background-color: #2d5016; color: #a5d6a7;">{newer_escaped}</span>\n'
                older_html += f'<span style="background-color: #5d2929; color: #f48771;">{older_escaped}</span>\n'
            else:
                newer_html += f'{newer_escaped}\n'
                older_html += f'{older_escaped}\n'
        
        newer_html += '</pre>'
        older_html += '</pre>'
        
        return newer_html, older_html
    
    def _contains_metrics(self, line: str) -> bool:
        """Check if line contains performance metrics"""
        metric_keywords = [
            'Total Trades:', 'Win Rate:', 'Net PnL:', 'Profit Factor:',
            'Sharpe Ratio:', 'Max Drawdown:', 'Avg Win:', 'Avg Loss:',
            'Largest Win:', 'Largest Loss:', 'Net Return:', 'Risk-Adjusted'
        ]
        return any(keyword in line for keyword in metric_keywords)
    
    def _sync_scrollbars(self, left_text: QTextEdit, right_text: QTextEdit):
        """Synchronize scrollbars between two text edits"""
        left_scrollbar = left_text.verticalScrollBar()
        right_scrollbar = right_text.verticalScrollBar()

        # Connect scrollbars
        left_scrollbar.valueChanged.connect(right_scrollbar.setValue)
        right_scrollbar.valueChanged.connect(left_scrollbar.setValue)

    def _strip_log_header(self, content: str) -> str:
        """
        Strip the header box from test log content for clean comparison.
        
        Removes header from:
        ╔════════════════════════════════════════════════════════════════╗
        ║ TEST LOG - Strategy #001                                       ║
        ╚════════════════════════════════════════════════════════════════╝
        
        Test Timestamp: 2026-01-11 07:25:02
        Test Type: Quick Test
        Log File: test_20260111_072502.txt
        
        ────────────────────────────────────────────────────────────────
        
        Returns everything after the separator line (────).
        If no header exists, returns content unchanged.
        """
        if not content or not content.strip():
            return content
        
        # Check if content has header (starts with ╔)
        if not content.lstrip().startswith('╔'):
            return content
        
        # Find the separator line (────)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '────' in line:
                # Return everything after separator line
                # Skip the separator line itself and any empty lines immediately after
                result_lines = lines[i+1:]
                # Remove leading empty lines
                while result_lines and not result_lines[0].strip():
                    result_lines.pop(0)
                return '\n'.join(result_lines)
        
        # If no separator found, return original content
        return content

    def _show_metrics_comparison(self, strategy_num: int):
        """Extract and display key metrics comparison - loads from actual test logs"""
        import re
        
        # Get test logs directory
        logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
        
        if not logs_dir.exists():
            QMessageBox.warning(
                self,
                "No Logs",
                "No test logs found to compare metrics."
            )
            return
        
        # Get all log files sorted by timestamp (newest first)
        log_files = sorted(logs_dir.glob("test_*.txt"), reverse=True)
        
        if len(log_files) < 2:
            QMessageBox.warning(
                self,
                "Insufficient Data",
                f"Need at least 2 test runs to compare metrics.\nCurrently have: {len(log_files)}"
            )
            return
        
        try:
            # Load the two most recent test logs
            with open(log_files[0], 'r') as f:
                newer_text = f.read()
            with open(log_files[1], 'r') as f:
                older_text = f.read()
            
            def extract_metrics(text: str) -> dict:
                """Extract key metrics from test output"""
                metrics = {}
                
                patterns = {
                    'total_trades': r'Total Trades:\s*(\d+)',
                    'win_rate': r'Win.*Rate:\s*([\d.]+)%',
                    'net_pnl': r'Net PnL:\s*\$([+-]?[\d,]+\.?\d*)',
                    'net_return': r'Net Return:\s*([+-]?[\d.]+)%',
                    'profit_factor': r'Profit Factor:\s*([\d.]+)',
                    'sharpe_ratio': r'Sharpe Ratio:\s*([\d.]+)',
                    'max_drawdown': r'Max Drawdown:\s*([\d.]+)%',
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, text)
                    if match:
                        value_str = match.group(1).replace(',', '')
                        try:
                            metrics[key] = float(value_str)
                        except:
                            metrics[key] = value_str
                
                return metrics
            
            newer_metrics = extract_metrics(newer_text)
            older_metrics = extract_metrics(older_text)
            
            # Build comparison table with HTML and color highlighting
            comparison_html = '<pre style="margin: 0; padding: 10px; font-family: monospace; font-size: 10pt;">'
            comparison_html += "📊 KEY METRICS COMPARISON\n"
            comparison_html += "=" * 80 + "\n\n"
            comparison_html += f"{'Metric':<20} {'Newer Test':>15} {'Previous Test':>15} {'Change':>15}\n"
            comparison_html += "-" * 80 + "\n"
            
            metric_labels = {
                'total_trades': 'Total Trades',
                'win_rate': 'Win Rate (%)',
                'net_pnl': 'Net PnL ($)',
                'net_return': 'Net Return (%)',
                'profit_factor': 'Profit Factor',
                'sharpe_ratio': 'Sharpe Ratio',
                'max_drawdown': 'Max Drawdown (%)',
            }
            
            # Metrics where higher = better
            higher_is_better = {'total_trades', 'win_rate', 'net_pnl', 'net_return', 'profit_factor', 'sharpe_ratio'}
            
            for key, label in metric_labels.items():
                if key in newer_metrics and key in older_metrics:
                    newer_val = newer_metrics[key]
                    older_val = older_metrics[key]
                    
                    try:
                        newer_float = float(newer_val)
                        older_float = float(older_val)
                        change = newer_float - older_float
                        change_pct = (change / older_float * 100) if older_float != 0 else 0
                        
                        # Determine if this is an improvement
                        if key in higher_is_better:
                            is_improvement = change > 0
                        else:  # max_drawdown - lower is better
                            is_improvement = change < 0
                        
                        # Format change with color
                        change_str = f"{change:+.2f} ({change_pct:+.1f}%)"
                        
                        # Apply color highlighting
                        if abs(change) < 0.01:  # No significant change
                            color = "#cccccc"  # Gray
                        elif is_improvement:
                            color = "#4ec9b0"  # Green
                        else:
                            color = "#f48771"  # Red
                        
                        line = f"{label:<20} {newer_val:>15.2f} {older_val:>15.2f} "
                        comparison_html += f'{line}<span style="color: {color}; font-weight: bold;">{change_str:>15}</span>\n'
                    except:
                        comparison_html += f"{label:<20} {str(newer_val):>15} {str(older_val):>15} {'N/A':>15}\n"
            
            comparison_html += "\n" + "=" * 80 + "\n"
            comparison_html += '\n<span style="color: #4ec9b0;">■ Green = Improvement</span>\n'
            comparison_html += '<span style="color: #f48771;">■ Red = Degradation</span>\n'
            comparison_html += '<span style="color: #cccccc;">■ Gray = No Change</span>\n'
            comparison_html += '</pre>'
            
            # Show in dialog
            dialog = QDialog(self.live_output_dialog, Qt.WindowType.Window)
            dialog.setWindowTitle("📊 Key Metrics Comparison")
            dialog.resize(700, 500)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setHtml(comparison_html)
            layout.addWidget(text_edit)
            
            close_btn = QPushButton("✅ Close")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.show()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to compare metrics:\n{e}"
            )
    
    def _copy_output_to_clipboard(self):
        """Copy all output text to clipboard"""
        if hasattr(self, 'live_output_text'):
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.live_output_text.toPlainText())
            
            # Show confirmation
            QMessageBox.information(
                self.live_output_dialog,
                "Copied",
                "📋 All output copied to clipboard!"
            )
    
    def _copy_trade_records_to_clipboard(self):
        """Copy only trade record paths from output to clipboard"""
        if hasattr(self, 'live_output_text'):
            import re
            from PyQt6.QtWidgets import QApplication
            
            # Get all text
            text = self.live_output_text.toPlainText()
            
            # Extract paths - look for various patterns
            paths = []
            for line in text.split('\n'):
                # Case-insensitive search for trade record indicators
                line_lower = line.lower()
                
                # Check if line contains trade record keywords
                if any(keyword in line_lower for keyword in [
                    'trade record', 'trade_record', 'trades.csv', 
                    'optimization_results', 'data/reports'
                ]):
                    # Extract all path-like strings ending in .csv
                    matches = re.findall(r'[a-zA-Z0-9_/.-]+\.csv', line)
                    paths.extend(matches)
            
            if paths:
                # Remove duplicates and sort
                unique_paths = sorted(set(paths))
                
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText('\n'.join(unique_paths))
                
                # Show confirmation with count
                QMessageBox.information(
                    self.live_output_dialog,
                    "Copied",
                    f"📂 Copied {len(unique_paths)} trade record path(s) to clipboard!"
                )
            else:
                QMessageBox.warning(
                    self.live_output_dialog,
                    "No Paths Found",
                    "No trade record paths found in output.\n\n"
                    "Test may still be running or no results generated yet."
                )
    
    def _show_test_results(self, strategy_num: int, output: str):
        """Display test results in independent window"""
        # Create results window (not a dialog, so it's independent)
        dialog = QDialog(self, Qt.WindowType.Window)  # Window flag makes it independent
        dialog.setWindowTitle(f"Test Results - Strategy #{strategy_num:03d}")
        dialog.setGeometry(200, 200, 800, 600)
        dialog.setModal(False)  # Non-modal - can move independently
        
        layout = QVBoxLayout(dialog)
        
        # Results text
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        results_text.setPlainText(output)
        layout.addWidget(results_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        edit_btn = QPushButton("✏️ Edit Strategy")
        edit_btn.clicked.connect(lambda: self._edit_from_results(dialog, strategy_num))
        button_layout.addWidget(edit_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("✅ Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.show()  # Non-blocking - can use main window while open
    
    def _edit_from_results(self, results_dialog, strategy_num: int):
        """Edit strategy from test results dialog"""
        results_dialog.close()
        
        # Load and edit (non-blocking)
        config = self.registry.load_strategy(strategy_num)
        if config:
            creator = StrategyCreatorDialog(self, existing_config=config, on_draft_saved=self.load_strategies)
            creator.show()
    
    def view_test_results(self):
        """View last test results for selected strategy"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to view results for"
            )
            return
        
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Load strategy config
        config = self.registry.load_strategy(strategy_num)
        if not config:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load strategy #{strategy_num:03d}"
            )
            return
        
        # Build path to results based on strategy name/number
        strategy_name = config.strategy_name.lower().replace(' ', '_')
        results_dir = Path(f"data/reports/strategies/universal_optimizer/strategy_{strategy_num:03d}_{strategy_name}")
        
        # Check if results directory exists
        if not results_dir.exists():
            QMessageBox.warning(
                self,
                "No Results Found",
                f"No test results found for Strategy #{strategy_num:03d}\n\n"
                f"Expected location:\n{results_dir}\n\n"
                "Run a test first using the '🧪 Test' button."
            )
            return
        
        # Look for common result files
        summary_file = results_dir / "optimization_summary.csv"
        trades_file = results_dir / "all_trades.csv"
        best_config_file = results_dir / "best_configuration.txt"
        
        # Build results display
        results_text = f"""📊 Test Results - Strategy #{strategy_num:03d}
{'='*60}
Strategy: {config.strategy_name}
Results Directory: {results_dir}

"""
        
        # Read summary if exists
        if summary_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(summary_file)
                
                if len(df) > 0:
                    # Get best row (highest Sharpe)
                    best_idx = df['sharpe_ratio'].idxmax()
                    best = df.loc[best_idx]
                    
                    results_text += f"""✅ OPTIMIZATION SUMMARY
{'-'*60}
Best Configuration (by Sharpe Ratio):

Trades: {int(best['total_trades'])}
Win Rate: {best['win_rate']:.1f}%
Net PnL: ${best['net_pnl']:.2f}
Net PnL %: {best['net_pnl_pct']:.2f}%
Profit Factor: {best['profit_factor']:.2f}
Sharpe Ratio: {best['sharpe_ratio']:.2f}
Max Drawdown: {best['max_drawdown_pct']:.2f}%

Avg Win: ${best['avg_win']:.2f}
Avg Loss: ${best['avg_loss']:.2f}
Largest Win: ${best['largest_win']:.2f}
Largest Loss: ${best['largest_loss']:.2f}

Total Configurations Tested: {len(df)}

"""
                else:
                    results_text += "⚠️ No optimization results found in summary file.\n\n"
                    
            except Exception as e:
                results_text += f"⚠️ Error reading summary: {e}\n\n"
        else:
            results_text += "⚠️ No optimization_summary.csv found.\n\n"
        
        # List available files
        results_text += f"""📁 AVAILABLE RESULT FILES
{'-'*60}
"""
        
        csv_files = list(results_dir.glob("*.csv"))
        txt_files = list(results_dir.glob("*.txt"))
        
        if csv_files:
            results_text += "\nCSV Files:\n"
            for f in sorted(csv_files):
                size_kb = f.stat().st_size / 1024
                results_text += f"  • {f.name} ({size_kb:.1f} KB)\n"
        
        if txt_files:
            results_text += "\nText Files:\n"
            for f in sorted(txt_files):
                size_kb = f.stat().st_size / 1024
                results_text += f"  • {f.name} ({size_kb:.1f} KB)\n"
        
        results_text += f"\n{'-'*60}\n"
        results_text += f"Full Path: {results_dir.absolute()}\n"
        
        # Create results dialog
        dialog = QDialog(self, Qt.WindowType.Window)
        dialog.setWindowTitle(f"📊 Test Results - Strategy #{strategy_num:03d}")
        dialog.setGeometry(200, 200, 900, 700)
        dialog.setModal(False)
        
        layout = QVBoxLayout(dialog)
        
        # Results text area
        results_display = QTextEdit()
        results_display.setReadOnly(True)
        results_display.setPlainText(results_text)
        layout.addWidget(results_display)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Open folder button
        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.setToolTip("Open results folder in file manager")
        open_folder_btn.clicked.connect(lambda: self._open_results_folder(results_dir))
        button_layout.addWidget(open_folder_btn)
        
        # Copy path button
        copy_path_btn = QPushButton("📋 Copy Path")
        copy_path_btn.setToolTip("Copy results path to clipboard")
        copy_path_btn.clicked.connect(lambda: self._copy_results_path(results_dir))
        button_layout.addWidget(copy_path_btn)
        
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("✅ Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.show()
    
    def _open_results_folder(self, results_dir: Path):
        """Open results folder in file manager"""
        import platform
        import subprocess
        
        try:
            system = platform.system()
            
            if system == 'Linux':
                subprocess.run(['xdg-open', str(results_dir)])
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', str(results_dir)])
            elif system == 'Windows':
                subprocess.run(['explorer', str(results_dir)])
            else:
                QMessageBox.warning(
                    self,
                    "Unsupported Platform",
                    f"Cannot open folder on {system}\n\nPath: {results_dir}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open folder:\n{e}"
            )
    
    def _copy_results_path(self, results_dir: Path):
        """Copy results path to clipboard"""
        from PyQt6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()
        clipboard.setText(str(results_dir.absolute()))
        
        self.status_bar.showMessage(f"📋 Copied path to clipboard: {results_dir}")
            
    def preview_code(self):
        """Preview code for selected strategy"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to preview"
            )
            return
            
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        try:
            files = self.registry.generate_strategy_files(strategy_num)
            if files:
                preview = CodePreviewDialog(files, self)
                preview.show()  # Non-blocking
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Preview failed:\n{e}"
            )
            
    def show_context_menu(self, position):
        """Show right-click context menu"""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu()
        
        # Only show actions if item selected
        current = self.strategy_list.currentItem()
        if current:
            edit_action = menu.addAction("✏️ Edit")
            edit_action.triggered.connect(self.edit_strategy)
            
            menu.addSeparator()
            
            validate_action = menu.addAction("✓ Validate")
            validate_action.triggered.connect(self.validate_strategy)
            
            publish_action = menu.addAction("✅ Publish")
            publish_action.triggered.connect(self.publish_strategy)
            
            generate_action = menu.addAction("⚙ Generate Files")
            generate_action.triggered.connect(self.generate_files)
            
            preview_action = menu.addAction("👁 Preview Code")
            preview_action.triggered.connect(self.preview_code)
            
            menu.addSeparator()
            
            delete_action = menu.addAction("🗑 Delete")
            delete_action.triggered.connect(self.delete_strategy)
            
            menu.exec(self.strategy_list.mapToGlobal(position))
    
    def show_statistics(self):
        """Show strategy statistics"""
        total = self.registry.get_strategy_count()
        by_category = self.registry.get_category_counts()
        
        stats_text = f"Total Strategies: {total}/150\n"
        stats_text += f"Available Slots: {150 - total}\n\n"
        stats_text += "By Category:\n"
        
        for category, count in sorted(by_category.items()):
            stats_text += f"  {category}: {count}\n"
        
        QMessageBox.information(self, "Statistics", stats_text)
        
    def publish_strategy(self):
        """Publish strategy (move to published folder for ITM)"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to publish"
            )
            return
        
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Check if already published
        if "[PUBLISHED]" in item_text:
            QMessageBox.information(
                self,
                "Already Published",
                f"Strategy #{strategy_num:03d} is already published!"
            )
            return
        
        # Load strategy
        config = self.registry.load_strategy(strategy_num)
        if not config:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load strategy #{strategy_num:03d}"
            )
            return
        
        # Remove [DRAFT] marker if present
        if config.description and "[DRAFT]" in config.description:
            config.description = config.description.replace("[DRAFT] ", "").replace("[DRAFT]", "")
        
        # Validate before publishing
        result = self.validator.validate(config)
        if not result.is_valid:
            errors = '\n'.join(f"• {e}" for e in result.errors)
            reply = QMessageBox.warning(
                self,
                "Validation Failed",
                f"Strategy has validation errors:\n\n{errors}\n\n"
                "Publish anyway? (Not recommended - ITM may reject it)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Confirm publication
        reply = QMessageBox.question(
            self,
            "Confirm Publication",
            f"Publish Strategy #{strategy_num:03d}?\n\n"
            f"Name: {config.strategy_name}\n"
            f"Category: {config.strategy_category}\n"
            f"Blocks: {len(config.blocks)}\n\n"
            "This will make it available to the Intelligent Trade Manager.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Save as published (will move to published folder)
                self.registry.save_strategy(config, validate=False, overwrite=True, is_published=True)
                
                self.load_strategies()
                QMessageBox.information(
                    self,
                    "Success",
                    f"✅ Strategy #{strategy_num:03d} published!\n\n"
                    "It is now available for the Intelligent Trade Manager."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to publish strategy:\n{e}"
                )
    
    def clear_cache_and_restart(self):
        """Clear Python bytecode cache and restart the GUI"""
        reply = QMessageBox.question(
            self,
            "Clear Cache & Restart",
            "🧹 Clear Python Bytecode Cache?\n\n"
            "This will:\n"
            "• Delete all .pyc files (compiled Python)\n"
            "• Remove all __pycache__ directories\n"
            "• Restart the Strategy Builder GUI\n\n"
            "This fixes issues with stale/outdated code.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Show progress message
                self.status_bar.showMessage("🧹 Clearing Python cache...")
                
                # Get project root
                project_root = Path(__file__).parent.parent.parent.parent.parent
                
                # Clear cache
                import subprocess
                
                # Find and delete .pyc files
                result1 = subprocess.run(
                    ['find', str(project_root), '-type', 'f', '-name', '*.pyc', '-delete'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Find and delete __pycache__ directories  
                result2 = subprocess.run(
                    ['find', str(project_root), '-type', 'd', '-name', '__pycache__', '-exec', 'rm', '-rf', '{}', '+'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,  # Suppress "No such file" errors
                    text=True
                )
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    "✅ Python cache cleared successfully!\n\n"
                    "The GUI will now restart..."
                )
                
                # Save window state before restarting
                self.save_window_state()
                
                # Restart the application
                import os
                python = sys.executable
                os.execl(python, python, *sys.argv)
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear cache:\n{e}\n\n"
                    "You can manually clear cache by running:\n"
                    f"find {project_root} -name '*.pyc' -delete\n"
                    f"find {project_root} -name '__pycache__' -exec rm -rf {{}} +"
                )
                self.status_bar.showMessage("Cache clear failed")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Strategy Builder v3.0

Professional PyQt6 Interface

Features:
• VSCode dark theme
• Large, readable fonts
• 83 production-ready building blocks
• Automated code generation
• Institutional validation
• Organized folder structure:
  - drafts/ (WIP strategies)
  - unpublished/ (Complete, not published)
  - published/ (Ready for ITM)

©  2026 BTC Engine Project
"""
        QMessageBox.about(self, "About", about_text)
    
    def restore_window_state(self):
        """Restore window geometry and splitter sizes from settings"""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        
        # Restore window geometry
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore splitter sizes
        splitter_state = settings.value("window/splitter")
        if splitter_state:
            self.splitter.restoreState(splitter_state)
    
    def save_window_state(self):
        """Save window geometry and splitter sizes to settings"""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        
        # Save window geometry
        settings.setValue("window/geometry", self.saveGeometry())
        
        # Save splitter sizes
        settings.setValue("window/splitter", self.splitter.saveState())
    
    def load_last_test(self):
        """Load and display the last test output for selected strategy"""
        current = self.strategy_list.currentItem()
        if not current:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a strategy to load test results for"
            )
            return
        
        item_text = current.text()
        strategy_num = int(item_text.split('.')[0])
        
        # Get test logs directory
        logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
        
        if not logs_dir.exists():
            QMessageBox.information(
                self,
                "No Test Logs",
                f"No test logs found for Strategy #{strategy_num:03d}\n\n"
                "Run a test first using the '🧪 Test' button."
            )
            return
        
        # Find most recent log file
        log_files = sorted(logs_dir.glob("test_*.txt"), reverse=True)
        
        if not log_files:
            QMessageBox.information(
                self,
                "No Test Logs",
                f"No test log files found for Strategy #{strategy_num:03d}\n\n"
                "Run a test first using the '🧪 Test' button."
            )
            return
        
        # Load most recent log
        latest_log = log_files[0]
        
        try:
            with open(latest_log, 'r') as f:
                log_content = f.read()
            
            # Create a mock backtest thread for showing trades
            class MockBacktestThread:
                def __init__(self, strategy_num):
                    self.strategy_num = strategy_num
            
            self.backtest_thread = MockBacktestThread(strategy_num)
            
            # Create live output dialog
            self._create_live_output_dialog(strategy_num)
            
            # Set window title to indicate loaded test
            self.live_output_dialog.setWindowTitle(f"📂 Strategy #{strategy_num:03d} - LOADED TEST RESULTS")
            
            # Load the saved output
            self.live_output_text.setPlainText(log_content)
            
            # Set status as completed (not running)
            self.live_status_label.setText(f"✅ Loaded test from: {latest_log.name}")
            self.live_status_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #4ec9b0;")
            
            # Enable buttons (not running test)
            self.stop_test_btn.setEnabled(False)
            self.stop_test_btn.setText("📂 Loaded")
            self.summary_btn.setEnabled(True)
            self.trades_btn.setEnabled(True)
            
            # Enable Compare if 2+ logs exist
            if len(log_files) >= 2:
                self.compare_btn.setEnabled(True)
            else:
                self.compare_btn.setEnabled(False)
                self.compare_btn.setToolTip("Need 2+ test runs to compare (currently: 1)")
            
            self.live_close_btn.setText("✅ Close")
            self.live_close_btn.setEnabled(True)
            
            self.status_bar.showMessage(f"Loaded test results for strategy #{strategy_num:03d}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load test log:\n{e}"
            )
    
    def _save_test_log(self, strategy_num: int, output: str):
        """Save test output log with metadata (keep max 2 per strategy)"""
        try:
            # Create logs directory
            logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamp filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Detect test type from output or backtest thread command
            test_type = "Unknown"
            if hasattr(self, 'backtest_thread') and hasattr(self.backtest_thread, 'cmd'):
                if '--quick-test' in self.backtest_thread.cmd:
                    test_type = "Quick Test"
                else:
                    test_type = "Full Test"
            elif "QUICK TEST MODE" in output:
                test_type = "Quick Test"
            elif "TP/SL optimization" in output or "Testing TP mode" in output:
                test_type = "Full Test"
            
            # Create header with metadata
            header = f"""╔{'═'*78}╗
║ TEST LOG - Strategy #{strategy_num:03d}                                               ║
╚{'═'*78}╝

Test Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Test Type: {test_type}
Log File: test_{timestamp}.txt

{'─'*80}

"""
            
            # Save output with header
            log_file = logs_dir / f"test_{timestamp}.txt"
            with open(log_file, 'w') as f:
                f.write(header)
                f.write(output)
            
            # Also save config snapshot for comparison
            # Read directly from JSON file to ensure 100% accuracy (no hardcoded defaults)
            try:
                import yaml
                import json
                
                config_snapshot_file = logs_dir / f"config_{timestamp}.yaml"
                
                # Find the actual strategy JSON file by searching all folders
                pattern = f"strategy_{strategy_num:03d}_*.json"
                strategy_json_file = None
                
                for folder in [self.registry.drafts_dir, self.registry.unpublished_dir, self.registry.published_dir]:
                    matching_files = list(folder.glob(pattern))
                    if matching_files:
                        strategy_json_file = matching_files[0]
                        break
                
                if strategy_json_file and strategy_json_file.exists():
                    # Read the actual JSON file directly to preserve all values exactly as configured
                    with open(strategy_json_file, 'r') as f:
                        actual_json_config = json.load(f)
                    
                    # Remove internal metadata from original file
                    actual_json_config.pop('_metadata', None)
                    
                    # Add test metadata to the snapshot
                    snapshot_config = actual_json_config.copy()
                    snapshot_config['_test_metadata'] = {
                        'test_type': test_type,
                        'test_timestamp': timestamp,
                        'test_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'source_file': str(strategy_json_file)
                    }
                    
                    # Save the snapshot as YAML for human readability
                    with open(config_snapshot_file, 'w') as f:
                        yaml.dump(snapshot_config, f, default_flow_style=False, sort_keys=False)
                    
                    print(f"✅ Config snapshot saved from: {strategy_json_file.name}")
                else:
                    # This should NEVER happen - log error
                    print(f"❌ CRITICAL: Strategy #{strategy_num:03d} JSON file not found in any folder!")
                    print(f"   Searched: drafts/, unpublished/, published/")
                    
            except Exception as e:
                print(f"⚠️ Warning: Failed to save config snapshot: {e}")
            
            # Keep only 2 most recent logs (and their configs)
            log_files = sorted(logs_dir.glob("test_*.txt"), reverse=True)
            for old_log in log_files[2:]:  # Delete all except 2 most recent
                old_log.unlink()
                # Also delete corresponding config snapshot
                old_timestamp = old_log.stem.replace('test_', '')
                old_config = logs_dir / f"config_{old_timestamp}.yaml"
                if old_config.exists():
                    old_config.unlink()
            
            print(f"Saved test log: {log_file}")
            print(f"Saved config snapshot: {config_snapshot_file if config_snapshot_file.exists() else 'N/A'}")
            print(f"Total logs for strategy {strategy_num}: {len(list(logs_dir.glob('test_*.txt')))}")
            
        except Exception as e:
            print(f"Warning: Failed to save test log: {e}")
    
    def _restore_previous_config(self, strategy_num: int, parent_dialog):
        """Restore configuration from previous test to the selected strategy"""
        try:
            # Get test logs directory
            logs_dir = Path(f"data/test_logs/strategy_{strategy_num:03d}")
            
            if not logs_dir.exists():
                QMessageBox.warning(
                    parent_dialog,
                    "No Config Snapshots",
                    "No config snapshots found.\n\n"
                    "Config snapshots are saved automatically when you run tests."
                )
                return
            
            # Get all config snapshot files sorted by timestamp (newest first)
            config_files = sorted(logs_dir.glob("config_*.yaml"), reverse=True)
            
            if len(config_files) < 2:
                QMessageBox.warning(
                    parent_dialog,
                    "Insufficient Snapshots",
                    f"Need at least 2 config snapshots to restore previous config.\n"
                    f"Currently have: {len(config_files)}\n\n"
                    "Run another test to create more snapshots."
                )
                return
            
            # Get the second most recent config (the "previous" one)
            previous_config_file = config_files[1]
            
            # Confirm restoration
            reply = QMessageBox.question(
                parent_dialog,
                "Confirm Config Restoration",
                f"⏮️ Restore Previous Configuration?\n\n"
                f"This will restore Strategy #{strategy_num:03d} to the configuration from:\n"
                f"{previous_config_file.name}\n\n"
                f"Current configuration will be overwritten.\n\n"
                f"Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Read the previous config
            import yaml
            with open(previous_config_file, 'r') as f:
                previous_config_data = yaml.safe_load(f)
            
            # Remove test metadata (not part of actual config)
            previous_config_data.pop('_test_metadata', None)
            
            # Load the current strategy to get the file path
            current_config = self.registry.load_strategy(strategy_num)
            if not current_config:
                raise ValueError(f"Failed to load current strategy #{strategy_num:03d}")
            
            # Find the strategy JSON file
            pattern = f"strategy_{strategy_num:03d}_*.json"
            strategy_json_file = None
            
            for folder in [self.registry.drafts_dir, self.registry.unpublished_dir, self.registry.published_dir]:
                matching_files = list(folder.glob(pattern))
                if matching_files:
                    strategy_json_file = matching_files[0]
                    break
            
            if not strategy_json_file or not strategy_json_file.exists():
                raise ValueError(f"Strategy JSON file not found for #{strategy_num:03d}")
            
            # Write the previous config back to the JSON file
            import json
            with open(strategy_json_file, 'w') as f:
                json.dump(previous_config_data, f, indent=2)
            
            # Refresh the strategy list to show updated config
            self.load_strategies()
            
            # Show success message
            QMessageBox.information(
                parent_dialog,
                "Config Restored",
                f"✅ Configuration restored successfully!\n\n"
                f"Strategy #{strategy_num:03d} has been restored to the\n"
                f"configuration from the previous test.\n\n"
                f"Source: {previous_config_file.name}"
            )
            
            # Close the comparison dialog
            parent_dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(
                parent_dialog,
                "Restoration Failed",
                f"Failed to restore previous configuration:\n\n{e}"
            )
    
    def closeEvent(self, event):
        """Handle window close event - save state before closing"""
        self.save_window_state()
        event.accept()


def main():
    """Entry point"""
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = StrategyBuilderMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
