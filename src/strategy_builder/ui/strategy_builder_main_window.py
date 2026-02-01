"""
Strategy Builder Main Window - Complete UI Application

This is the main window that integrates all Strategy Builder UI components:
- Strategy Information Panel
- Block Search and Selection Panel
- Strategy Blocks Configuration Panel

Features:
- Resizable panels with splitters
- Menu bar (File, Edit, Tools, Help)
- Toolbar with quick actions
- Status bar
- Inter-component communication
- Save/Load functionality

Author: Strategy Builder Team
Date: 2026-01-16
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QAction, QToolBar, QStatusBar, QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt, QSize, QSettings, QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QFont
from PyQt5.QtWidgets import QApplication, QStyle
from datetime import datetime, timedelta
import pandas as pd

from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.ui.strategy_info_panel import StrategyInfoPanel
from src.strategy_builder.ui.block_search_panel import BlockSearchPanel
from src.strategy_builder.ui.strategy_blocks_panel import StrategyBlocksPanel
from src.strategy_builder.ui.validation_report_window import ValidationReportWindow
from src.strategy_builder.ui.backtest_config_dialog import BacktestConfigDialog
from src.optimizer_v3.validation.institutional_validator import InstitutionalValidator
from src.strategy_builder.ui.data_update_modal import DataUpdateModal
from src.strategy_builder.ui.alert_dialog import show_warning, ask_question
from src.strategy_builder.ui.stepper_ribbon import StepperRibbon
from src.strategy_builder.ui.styles import get_main_stylesheet, apply_hand_cursor_to_buttons
from src.strategy_builder.ui.new_strategy_dialog import NewStrategyDialog
from src.strategy_builder.ui.strategy_browser_dialog import StrategyBrowserDialog
from src.optimizer_v3.database import get_database_manager

# Import real block registry adapter
try:
    from src.strategy_builder.core.block_registry_adapter import BlockRegistryAdapter
    BLOCK_REGISTRY_ADAPTER_AVAILABLE = True
except ImportError:
    BLOCK_REGISTRY_ADAPTER_AVAILABLE = False


class StrategyBuilderMainWindow(QMainWindow):
    """
    Main application window for Strategy Builder.
    
    Integrates all UI components and provides menu bar, toolbar, and status bar.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Create orchestrator with real registry adapter if available
        if BLOCK_REGISTRY_ADAPTER_AVAILABLE:
            try:
                adapter = BlockRegistryAdapter()
                self.orchestrator = StrategyBuilderOrchestrator(registry=adapter)
            except Exception as e:
                print(f"Warning: Failed to initialize BlockRegistryAdapter: {e}")
                # Fallback to mock registry
                self.orchestrator = StrategyBuilderOrchestrator()
        else:
            # Fallback to mock registry
            self.orchestrator = StrategyBuilderOrchestrator()
        
        # UI Components
        self.info_panel: Optional[StrategyInfoPanel] = None
        self.search_panel: Optional[BlockSearchPanel] = None
        self.blocks_panel: Optional[StrategyBlocksPanel] = None
        
        # Track current file (legacy - keep for now)
        self.current_file: Optional[str] = None
        self.is_modified = False
        
        # Track current strategy in database
        self.current_strategy_id: Optional[str] = None
        self.current_version_id: Optional[str] = None
        
        # Track workflow state (step completion flags)
        self.validation_passed = False
        self.test_completed = False
        
        # Flag to prevent validation reset during strategy load
        self.loading_strategy = False
        
        # Auto-update timers
        self.candle_check_timer: Optional[QTimer] = None
        self.retry_timer: Optional[QTimer] = None
        self.last_update_time: Optional[datetime] = None
        self.retry_count = 0
        self.next_check_time: Optional[datetime] = None
        
        # Countdown timer for status bar
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._update_countdown_status)
        self.countdown_timer.start(1000)  # Update every second
        
        # Setup UI
        self._init_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self._connect_signals()
        
        # Set initial state
        self._update_window_title()
        self._update_status("Ready to create a new strategy")
        
        # Auto-create initial strategy so users can immediately add blocks
        self.orchestrator.create_strategy("New_Strategy")
        
        # Restore window geometry and debug settings
        self._restore_settings()
        self._restore_debug_settings()
        
        # Show data update modal on startup (after window is shown)
        QTimer.singleShot(500, self._show_data_update_modal)
        
        # Start automatic data update system (after modal shown)
        QTimer.singleShot(1500, self._start_auto_update_system)
    
    def _init_ui(self):
        """Initialize the user interface layout."""
        # Window properties
        self.setWindowTitle("BTC Engine v3 - Strategy Builder")
        self.setGeometry(100, 100, 1400, 900)
        
        # Use OS title bar (change via GNOME theme - see TITLE_BAR_COLOR_FIX.md)
        
        # Apply centralized dark theme stylesheet
        self.setStyleSheet(get_main_stylesheet())
        
        # Central widget container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)
        
        # Create main splitter (horizontal split)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Info panel (top) + Blocks panel (bottom)
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(10)
        
        # Create panels
        self.info_panel = StrategyInfoPanel(self.orchestrator)
        self.blocks_panel = StrategyBlocksPanel(self.orchestrator)
        
        # Add to left layout (validation panel removed - now shown as modal)
        left_layout.addWidget(self.info_panel)
        left_layout.addWidget(self.blocks_panel, stretch=1)
        left_widget.setLayout(left_layout)
        
        # Right side: Search panel
        self.search_panel = BlockSearchPanel(self.orchestrator)
        
        # Add to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.search_panel)
        
        # Set initial splitter sizes (40% left, 60% right)
        main_splitter.setSizes([560, 840])
        
        # CRITICAL: Prevent panels from being collapsed/disappearing
        # Index 0 = left (info + blocks), Index 1 = right (search panel)
        main_splitter.setCollapsible(0, False)  # Left cannot collapse
        main_splitter.setCollapsible(1, False)  # Right cannot collapse
        
        # Add visual drag indicator to splitter handle (match Strategy Browser)
        main_splitter.setHandleWidth(8)  # Wider handle for better visibility
        main_splitter.setStyleSheet("""
            QSplitter::handle:horizontal {
                background-color: #3C4149;
                width: 8px;
                margin: 0px;
                padding: 0px;
                image: url(none);
            }
            QSplitter::handle:horizontal:hover {
                background-color: #095983;
            }
        """)
        
        # Add drag indicator icon to handle  
        handle = main_splitter.handle(1)
        if handle:
            from PyQt5.QtGui import QFont
            from .styles import create_font
            
            handle_layout = QVBoxLayout(handle)
            handle_layout.setContentsMargins(0, 0, 0, 0)
            handle_layout.setSpacing(0)
            
            # Add centered drag icon (⋮⋮⋮) - muted color
            drag_icon = QLabel("⋮\n⋮\n⋮")
            drag_icon.setFont(create_font(10, bold=True))
            drag_icon.setStyleSheet("color: #4A4F58; background: transparent;")  # Muted gray
            drag_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            handle_layout.addWidget(drag_icon)
        
        # Store splitter for settings save/restore
        self.main_splitter = main_splitter
        
        # Add splitter to main layout
        main_layout.addWidget(main_splitter)
    
    def _create_menu_bar(self):
        """Create the menu bar with professional icons."""
        menu_bar = self.menuBar()
        style = self.style()
        
        # File Menu
        file_menu = menu_bar.addMenu("&File")
        
        new_action = QAction(style.standardIcon(QStyle.SP_FileIcon), "&New Strategy", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.setStatusTip("Create a new strategy")
        new_action.triggered.connect(self._on_new_strategy)
        file_menu.addAction(new_action)
        
        open_action = QAction(style.standardIcon(QStyle.SP_DirOpenIcon), "&Open Strategy...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip("Open an existing strategy")
        open_action.triggered.connect(self._on_open_strategy)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction(style.standardIcon(QStyle.SP_DialogSaveButton), "&Save Strategy", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setStatusTip("Save the current strategy")
        save_action.triggered.connect(self._on_save_strategy)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(style.standardIcon(QStyle.SP_DialogSaveButton), "Save Strategy &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.setStatusTip("Save the strategy with a new name")
        save_as_action.triggered.connect(self._on_save_strategy_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(style.standardIcon(QStyle.SP_DialogCloseButton), "E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        
        clear_action = QAction(style.standardIcon(QStyle.SP_TrashIcon), "&Clear All Blocks", self)
        clear_action.setStatusTip("Remove all blocks from strategy")
        clear_action.triggered.connect(self._on_clear_blocks)
        edit_menu.addAction(clear_action)
        
        # Tools Menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        validate_action = QAction(style.standardIcon(QStyle.SP_DialogApplyButton), "&Validate Strategy", self)
        validate_action.setStatusTip("Validate the current strategy configuration")
        validate_action.triggered.connect(self._on_validate)
        tools_menu.addAction(validate_action)
        
        tools_menu.addSeparator()
        
        update_data_action = QAction(style.standardIcon(QStyle.SP_BrowserReload), "&Update Data...", self)
        update_data_action.setStatusTip("Check for data gaps and update from Binance")
        update_data_action.triggered.connect(self._on_update_data)
        tools_menu.addAction(update_data_action)
        
        tools_menu.addSeparator()
        
        import_json_action = QAction(style.standardIcon(QStyle.SP_DialogOpenButton), "&Import Strategy from JSON...", self)
        import_json_action.setStatusTip("Import strategy from JSON file and save to database")
        import_json_action.triggered.connect(self._on_import_from_json)
        tools_menu.addAction(import_json_action)
        
        tools_menu.addSeparator()
        
        # Debug Logger submenu
        debug_menu = tools_menu.addMenu(style.standardIcon(QStyle.SP_FileDialogInfoView), "&Debug Logger")
        
        self.enable_console_action = QAction("Enable Debugger in Console", self)
        self.enable_console_action.setCheckable(True)
        self.enable_console_action.setChecked(True)  # Default: enabled
        self.enable_console_action.setStatusTip("Toggle debug output to console")
        self.enable_console_action.triggered.connect(self._on_toggle_console_debug)
        debug_menu.addAction(self.enable_console_action)
        
        self.enable_logfile_action = QAction("Enable Debugger in Log File", self)
        self.enable_logfile_action.setCheckable(True)
        self.enable_logfile_action.setChecked(True)  # Default: enabled
        self.enable_logfile_action.setStatusTip("Toggle debug output to log files")
        self.enable_logfile_action.triggered.connect(self._on_toggle_logfile_debug)
        debug_menu.addAction(self.enable_logfile_action)
        
        debug_menu.addSeparator()
        
        clear_logs_action = QAction(style.standardIcon(QStyle.SP_TrashIcon), "Clear Old Logs", self)
        clear_logs_action.setStatusTip("Delete old log files")
        clear_logs_action.triggered.connect(self._on_clear_old_logs)
        debug_menu.addAction(clear_logs_action)
        
        view_log_action = QAction(style.standardIcon(QStyle.SP_FileDialogDetailedView), "View Current Log File", self)
        view_log_action.setStatusTip("Open the current log file")
        view_log_action.triggered.connect(self._on_view_current_log)
        debug_menu.addAction(view_log_action)
        
        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        
        about_action = QAction(style.standardIcon(QStyle.SP_MessageBoxInformation), "&About Strategy Builder", self)
        about_action.setStatusTip("About Strategy Builder")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Create the toolbar with professional icons and text."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")  # Fix Qt warning on close
        toolbar.setIconSize(QSize(32, 32))  # Bigger icons
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # Show text with icons
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        style = self.style()
        
        # New Strategy
        new_action = QAction(style.standardIcon(QStyle.SP_FileIcon), "New", self)
        new_action.setStatusTip("Create a new strategy")
        new_action.triggered.connect(self._on_new_strategy)
        toolbar.addAction(new_action)
        
        # Open Strategy
        open_action = QAction(style.standardIcon(QStyle.SP_DirOpenIcon), "Open", self)
        open_action.setStatusTip("Open strategy")
        open_action.triggered.connect(self._on_open_strategy)
        toolbar.addAction(open_action)
        
        # Save Strategy
        save_action = QAction(style.standardIcon(QStyle.SP_DialogSaveButton), "Save", self)
        save_action.setStatusTip("Save strategy")
        save_action.triggered.connect(self._on_save_strategy)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Add stepper - make it expand to fill toolbar so internal margin works
        self.stepper = StepperRibbon(self)
        self.stepper.step_clicked.connect(self._on_step_clicked)
        self.stepper.setSizePolicy(QWidget().sizePolicy().Expanding, QWidget().sizePolicy().Preferred)
        toolbar.addWidget(self.stepper)
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.statusBar().showMessage("Ready")
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Block selection: Add to blocks panel
        self.search_panel.block_selected.connect(self._on_block_selected)
        
        # Blocks changed: Refresh other panels
        self.blocks_panel.blocks_changed.connect(self._on_blocks_changed)
        
        # Strategy name changed: Update window title
        self.info_panel.strategy_name_changed.connect(self._on_strategy_name_changed)
        
        # Strategy type changed: Reset validation (requires re-validation)
        self.info_panel.strategy_type_changed.connect(self._on_strategy_type_changed)
    
    def _on_block_selected(self, block_name: str):
        """Handle block selection from search panel."""
        # NOTE: Blocks are now added via orchestrator.add_block_with_signals()
        # which is called from the search panel. We just need to refresh the display.
        
        # Save current name if it's blank (user hasn't named strategy yet)
        current_name = self.info_panel.get_strategy_name()
        preserve_blank = (current_name == "" or current_name.strip() == "")
        
        # Refresh blocks panel to show newly added block
        self.blocks_panel.refresh_from_orchestrator()
        
        # Refresh info panel to update description and required signals
        self.info_panel.refresh_from_orchestrator()
        
        # CRITICAL: Restore blank name if user hasn't named strategy yet
        # (refresh pulls "New_Strategy" from config, which should stay hidden from user)
        if preserve_blank:
            self.info_panel.set_strategy_name("")
        
        # Mark as added in search panel
        self.search_panel.mark_block_as_added(block_name)
        
        # Update status
        block_count = self.blocks_panel.get_block_count()
        self._update_status(f"Added block: {block_name} ({block_count} blocks total)")
        self.is_modified = True
        self._update_window_title()
    
    def reset_validation(self):
        """
        CENTRAL METHOD: Reset validation state when ANY configuration changes.
        
        Called by:
        - Block changes (add/remove/reorder)
        - Signal timing/recheck configuration
        - Exit condition configuration
        - Strategy name/type changes
        - Any other strategy mutation
        
        Forces user to re-validate after ANY modification.
        """
        # FIX: Always reset if step 1 has ANY status (completed or error)
        # Must clear completed_steps AND force visual button reset FOR STEP 1 ONLY
        if 1 in self.stepper.completed_steps or 1 in self.stepper.error_steps:
            self.validation_passed = False
            # Clear step 1 from sets
            self.stepper.completed_steps.discard(1)
            self.stepper.error_steps.discard(1)
            # Force visual refresh by calling _update_display() which rebuilds button styles
            self.stepper._update_display()
    
    def _on_blocks_changed(self):
        """Handle blocks changed event."""
        # Save current name if it's blank (user hasn't named strategy yet)
        current_name = self.info_panel.get_strategy_name()
        preserve_blank = (current_name == "" or current_name.strip() == "")
        
        # Refresh info panel to update description and required signals
        self.info_panel.refresh_from_orchestrator()
        
        # CRITICAL: Restore blank name if user hasn't named strategy yet
        # (refresh pulls "New_Strategy" from config, which should stay hidden from user)
        if preserve_blank:
            self.info_panel.set_strategy_name("")
        
        # Sync search panel button states with actual strategy blocks
        self.search_panel.sync_with_strategy()
        
        # Mark as modified
        self.is_modified = True
        self._update_window_title()
        
        # RESET VALIDATION when blocks change (BUT NOT during strategy load)
        if not self.loading_strategy:
            self.reset_validation()
        
        # Update status
        block_count = self.blocks_panel.get_block_count()
        self._update_status(f"Strategy updated - {block_count} block(s) configured")
    
    def _on_strategy_name_changed(self, name: str):
        """Handle strategy name change."""
        self.is_modified = True
        self._update_window_title()
        # RESET VALIDATION when strategy name changes (BUT NOT during load)
        if not self.loading_strategy:
            self.reset_validation()
    
    def _on_strategy_type_changed(self, strategy_type: str):
        """Handle strategy type change (Bullish/Bearish)."""
        self.is_modified = True
        # RESET VALIDATION when strategy type changes (BUT NOT during load)
        if not self.loading_strategy:
            self.reset_validation()
    
    def _is_strategy_empty(self) -> bool:
        """
        Check if strategy is truly empty (nothing worth saving).
        
        Returns:
            True if strategy has no name and no blocks, False otherwise
        """
        strategy_name = self.info_panel.get_strategy_name()
        block_count = self.blocks_panel.get_block_count()
        
        # Empty if no name AND no blocks
        return (not strategy_name or strategy_name.strip() == "") and block_count == 0
    
    def _on_new_strategy(self):
        """Create a new strategy - reset to clean state."""
        # Check if current strategy should be saved (skip if empty)
        if self.is_modified and not self._is_strategy_empty():
            reply = ask_question(
                self,
                "Unsaved Changes",
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before creating a new strategy?"
            )
            
            if reply == 'yes':
                if not self._on_save_strategy():
                    return  # Save was cancelled
            elif reply == 'cancel':
                return
        
        # Reset strategy in orchestrator with placeholder (allows adding blocks immediately)
        self.orchestrator.create_strategy("New_Strategy")
        
        # Update UI with blank name field (user enters their own name)
        # The placeholder "New_Strategy" is used internally but hidden from user
        self.info_panel.set_strategy_name("")
        self.info_panel.set_description("")
        
        # Clear database IDs (new strategy, not saved yet)
        self.current_strategy_id = None
        self.current_version_id = None
        
        # Clear file tracking
        self.current_file = None
        self.is_modified = False  # Clean state, nothing to save yet
        
        # Clear visual markers
        self.search_panel.clear_added_blocks()
        
        # Refresh blocks panel to show empty state
        self.blocks_panel.refresh_from_orchestrator()
        # NOTE: Don't refresh info_panel - it would pull "New_Strategy" from config
        # and overwrite the blank name we just set. We already set name/description above.
        
        # Reset validation and test states
        self.validation_passed = False
        self.test_completed = False
        self.stepper.reset_all_steps()
        
        # Update UI
        self._update_window_title()
        self._update_status("New strategy created - Ready to add blocks")
    
    def _on_open_strategy(self):
        """Open strategy from database using StrategyBrowserDialog."""
        # Check if current strategy should be saved (skip if empty)
        if self.is_modified and not self._is_strategy_empty():
            reply = ask_question(
                self,
                "Unsaved Changes",
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before opening another strategy?"
            )
            
            if reply == 'yes':
                if not self._on_save_strategy():
                    return  # Save was cancelled
            elif reply == 'cancel':
                return
        
        # Create and show strategy browser window
        browser = StrategyBrowserDialog(mode='open', parent=self)
        
        # Connect signal for when strategy is selected
        browser.strategy_selected.connect(self._load_strategy_from_browser)
        
        # Show as non-modal window
        browser.show()
    
    def _load_strategy_from_browser(self, strategy_id: str, version_id: str):
        """Load strategy after selection from browser"""
        if not strategy_id or not version_id:
            QMessageBox.warning(self, "Open Failed", "No strategy selected")
            return
        
        try:
            # Load strategy from database
            db = get_database_manager()
            version = db.strategy.get_strategy_version(version_id)
            
            if not version:
                QMessageBox.warning(self, "Load Failed", "Strategy version not found in database")
                return
            
            # Load validation status from database and restore stepper state
            validation_status = version.get('validation_status', 'Un-Validated')
            
            if validation_status == 'Pass':
                self.validation_passed = True
                self.test_completed = False
                self.stepper.reset_all_steps()
                self.stepper.mark_step_complete(1)  # Green check mark
            elif validation_status == 'Fail':
                self.validation_passed = False
                self.test_completed = False
                self.stepper.reset_all_steps()
                self.stepper.mark_step_error(1)  # Red X mark
            else:  # Un-Validated
                self.validation_passed = False
                self.test_completed = False
                self.stepper.reset_all_steps()  # Default state
            
            # Load blocks from database using persistence (SAME AS FILE LOAD)
            blocks_data = version.get('blocks', [])
            exit_conditions_data = version.get('exit_conditions', [])  # Sprint 1.8: Load exit conditions
            
            # Build config dict in EXACT same format as file load
            config_dict = {
                'name': version['name'],
                'description': version.get('description', ''),
                'blocks': blocks_data,
                'exit_conditions': exit_conditions_data  # Sprint 1.8: Include exit conditions
            }
            
            # SUPPRESS validation reset during load AND all refresh operations
            self.loading_strategy = True
            
            try:
                # Use persistence._dict_to_config() - EXACT same as file load
                restored_config = self.orchestrator.persistence._dict_to_config(config_dict)
                
                # Assign to config engine (SAME PATTERN as orchestrator.load_strategy)
                self.orchestrator.config_engine.config = restored_config
                
                print(f"Successfully restored {len(restored_config.blocks)} blocks with full config")
                
            except Exception as e:
                print(f"Error loading config from database: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to empty config
                self.orchestrator.create_strategy(version['name'])
            
            # Update UI panels with loaded data (STILL loading)
            self.info_panel.set_strategy_name(version['name'])
            if version.get('description'):
                self.info_panel.set_description(version['description'])
            
            # Track database IDs
            self.current_strategy_id = strategy_id
            self.current_version_id = version_id
            
            # Clear file tracking
            self.current_file = None
            self.is_modified = False
            
            # Clear and refresh panels (refresh can trigger blocks_changed!)
            self.search_panel.clear_added_blocks()
            self.blocks_panel.refresh_from_orchestrator()
            self.info_panel.refresh_from_orchestrator()
            
            # CRITICAL FIX: Sync search panel with loaded strategy to update button states
            self.search_panel.sync_with_strategy()
            
            # NOW re-enable validation reset (AFTER all refresh operations)
            self.loading_strategy = False
            
            # Update UI
            self._update_window_title()
            self._update_status(f"Loaded strategy: {version['name']} (v{version['version_number']}) from database")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading strategy from database:\n\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def _on_save_strategy(self) -> bool:
        """Save the current strategy to database with proper rollback on failure."""
        db = None
        created_strategy = False
        
        try:
            # Get strategy data from UI
            strategy_name = self.info_panel.get_strategy_name()
            description = self.info_panel.get_description()
            
            if not strategy_name or strategy_name.strip() == "":
                QMessageBox.warning(self, "Save Failed", "Strategy must have a name before saving.")
                return False
            
            # Get database manager
            db = get_database_manager()
            
            # CRITICAL: Rollback any previous failed state
            db.strategy.session.rollback()
            
            # If this is a new strategy (no strategy_id yet), create it
            if not self.current_strategy_id:
                self.current_strategy_id = db.strategy.create_strategy(strategy_name)
                created_strategy = True
            
            # Build version data from current config using persistence (SAME AS FILE SAVE)
            config = self.orchestrator.get_current_config()
            
            # Use persistence._config_to_dict() - EXACT same as file save
            config_dict = self.orchestrator.persistence._config_to_dict(config) if config else {}
            
            version_data = {
                'strategy_id': self.current_strategy_id,
                'name': strategy_name,
                'description': description or '',
                'blocks': config_dict.get('blocks', []),  # Full config with timings/rechecks
                'signals': {},  # Reserved
                'parameters': {},  # Reserved
                'entry_conditions': {},  # Reserved
                'exit_conditions': config_dict.get('exit_conditions', []),  # Sprint 1.8: Get from config
                'risk_management': {},  # Reserved
                'backtest_config': {},  # Reserved
                'tags': []  # Reserved
            }
            
            # Create new version
            try:
                self.current_version_id = db.strategy.create_strategy_version(version_data)
                
            except Exception as version_error:
                # VERSION CREATION FAILED
                print(f"\n❌ VERSION CREATION FAILED!")
                print(f"   Error: {version_error}")
                print(f"   Error type: {type(version_error)}")
                import traceback
                traceback.print_exc()
                
                # Note: create_strategy_version already rolled back
                
                # If we created the strategy in this save, delete the orphan
                # Use a FRESH transaction (previous one was rolled back)
                if created_strategy:
                    try:
                        from sqlalchemy import text
                        print(f"   Cleaning up orphaned strategy: {self.current_strategy_id}")
                        # Execute delete in fresh transaction (no intermediate rollback needed)
                        db.strategy.session.execute(
                            text("DELETE FROM strategies WHERE strategy_id = :sid"),
                            {'sid': self.current_strategy_id}
                        )
                        db.strategy.session.commit()
                        print(f"   ✅ Orphan deleted")
                    except Exception as cleanup_error:
                        # Cleanup failed - log but don't block error reporting
                        db.strategy.session.rollback()
                        print(f"   ❌ Failed to cleanup orphaned strategy: {cleanup_error}")
                    
                    self.current_strategy_id = None
                
                # Re-raise the original error
                raise version_error
            
            # Mark as not modified
            self.is_modified = False
            self._update_window_title()
            self._update_status(f"Strategy saved to database: {strategy_name}")
            
            return True
            
        except Exception as e:
            # Rollback on any error
            if db:
                db.strategy.session.rollback()
            
            QMessageBox.critical(self, "Error", f"Error saving strategy to database:\n\n{str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _on_save_strategy_with_feedback(self) -> bool:
        """Save the current strategy with success dialog (for validation dialog)."""
        if self.current_file:
            return self._save_to_file(self.current_file, show_success=True)
        else:
            # Save As always shows its own dialog, so no need for extra feedback
            return self._on_save_strategy_as()
    
    def _on_save_strategy_as(self) -> bool:
        """Save as new strategy (creates new strategy_id in database)."""
        try:
            # Show new strategy dialog to get name for new copy
            dialog = NewStrategyDialog(self)
            if dialog.exec_() != NewStrategyDialog.Accepted:
                return False  # User cancelled
            
            # Get new strategy data
            data = dialog.get_strategy_data()
            
            # Create NEW strategy (different strategy_id)
            db = get_database_manager()
            new_strategy_id = db.strategy.create_strategy(data['name'])
            
            # Build version data from current config (SAME AS FILE SAVE)
            config = self.orchestrator.get_current_config()
            
            # Use persistence._config_to_dict() - EXACT same as file save
            config_dict = self.orchestrator.persistence._config_to_dict(config) if config else {}
            
            version_data = {
                'strategy_id': new_strategy_id,  # NEW strategy ID
                'name': data['name'],
                'description': data.get('description', ''),
                'blocks': config_dict.get('blocks', []),  # Full config with timings/rechecks
                'signals': {},
                'parameters': {},
                'entry_conditions': {},
                'exit_conditions': {},
                'risk_management': {},
                'backtest_config': {},
                'tags': []
            }
            
            # Create version for new strategy
            new_version_id = db.strategy.create_strategy_version(version_data)
            
            # Update tracking to new strategy
            self.current_strategy_id = new_strategy_id
            self.current_version_id = new_version_id
            
            # Update UI with new name
            self.info_panel.set_strategy_name(data['name'])
            if data.get('description'):
                self.info_panel.set_description(data['description'])
            
            # Mark as not modified
            self.is_modified = False
            self._update_window_title()
            self._update_status(f"Strategy saved as: {data['name']} (new strategy in database)")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving strategy as:\n\n{str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _save_to_file(self, filename: str, show_success: bool = False) -> bool:
        """
        Save strategy to file.
        
        Args:
            filename: Path to save file
            show_success: Whether to show success message dialog
        """
        try:
            # Check for strategy type mismatch before saving
            if not self._check_strategy_type_match():
                return False  # User cancelled save
            
            # Update config from UI before saving
            strategy_name = self.info_panel.get_strategy_name()
            if strategy_name:
                self.orchestrator.config_engine.config.name = strategy_name
            
            # Also update strategy type from UI
            strategy_type = self.info_panel.get_strategy_type()
            if strategy_type:
                # Ensure config has strategy_type attribute
                if hasattr(self.orchestrator.config_engine.config, 'strategy_type'):
                    self.orchestrator.config_engine.config.strategy_type = strategy_type
                else:
                    # Add attribute if it doesn't exist
                    setattr(self.orchestrator.config_engine.config, 'strategy_type', strategy_type)
            
            # CRITICAL RECHECK: Verify config matches UI before saving
            ui_type = self.info_panel.get_strategy_type()
            config_type = getattr(self.orchestrator.config_engine.config, 'strategy_type', None)
            if config_type != ui_type:
                print(f"WARNING: Config mismatch before save! UI={ui_type}, Config={config_type}")
                print(f"Forcing config to match UI: {ui_type}")
                # Force config to match UI
                if hasattr(self.orchestrator.config_engine.config, 'strategy_type'):
                    self.orchestrator.config_engine.config.strategy_type = ui_type
                else:
                    setattr(self.orchestrator.config_engine.config, 'strategy_type', ui_type)
                print(f"Config now: {self.orchestrator.config_engine.config.strategy_type}")
            
            # PERSIST WORKFLOW STATE: Save validation status
            if self.validation_passed:
                if not hasattr(self.orchestrator.config_engine.config, 'validation_status'):
                    setattr(self.orchestrator.config_engine.config, 'validation_status', 'passed')
                else:
                    self.orchestrator.config_engine.config.validation_status = 'passed'
            
            # Save using orchestrator
            result = self.orchestrator.save_strategy(filename)
            
            if result.success:
                self.current_file = filename
                self.is_modified = False
                
                # Save directory for next time
                import os
                settings = QSettings("BTC_Engine", "StrategyBuilder")
                settings.setValue("lastDirectory", os.path.dirname(filename))
                
                self._update_window_title()
                self._update_status(f"Saved strategy to: {filename}")
                
                # Show success message if requested (e.g., when called from validation dialog)
                if show_success:
                    QMessageBox.information(
                        self,
                        "Strategy Saved",
                        f"Strategy saved successfully!\n\nFile: {filename}"
                    )
                
                return True
            else:
                QMessageBox.warning(self, "Save Failed", f"Failed to save strategy: {result.message}")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving strategy: {str(e)}")
            return False
    
    def _on_clear_blocks(self):
        """Clear all blocks from strategy."""
        reply = ask_question(
            self,
            "Clear Blocks",
            "Clear All Blocks",
            "Are you sure you want to remove all blocks from the strategy?"
        )
        
        if reply == 'yes':
            # Clear blocks
            self.search_panel.clear_added_blocks()
            # Refresh will happen via blocks_changed signal
            self._update_status("All blocks cleared")
    
    def _on_validate(self):
        """Validate the current strategy."""
        try:
            result = self.orchestrator.validate_strategy()
            
            if result.success:
                QMessageBox.information(
                    self,
                    "Validation Success",
                    "Strategy configuration is valid!"
                )
                self._update_status("Strategy validated successfully")
            else:
                QMessageBox.warning(
                    self,
                    "Validation Failed",
                    f"Strategy validation failed:\n\n{result.message}"
                )
                self._update_status("Strategy validation failed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error validating strategy: {str(e)}")
    
    def _on_run_backtest(self):
        """Run backtest for the current strategy."""
        try:
            dialog = BacktestConfigDialog(self.orchestrator, self)
            dialog.show()  # Non-modal so user can see strategy
            self._update_status("Backtest configuration opened")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening backtest dialog: {str(e)}")
            self._update_status("Backtest configuration failed to open")
    
    def _on_step_clicked(self, step: int):
        """
        Handle stepper ribbon step click with workflow enforcement.
        
        Step 0: Design - Always active
        Step 1: Validate - Requires strategy name + blocks
        Step 2: Generate - Requires successful validation
        Step 3: Test - Requires code generated
        Step 4: Publish - Requires test completed
        """
        if step == 0:
            # Design step - just highlight it
            self.stepper.set_current_step(0)
            self._update_status("Design your strategy by adding blocks")
        
        elif step == 1:
            # Validate step - CHECK PREREQUISITES
            if not self._check_validation_prerequisites():
                return  # Prerequisites not met, error shown
            
            self.stepper.set_current_step(1)
            
            # Run institutional validation
            try:
                config = self.orchestrator.get_current_config()
                validator = InstitutionalValidator()
                report = validator.validate(config)
                
                # Create and show validation report window
                window = ValidationReportWindow(report, config, self)
                window.show()  # QMainWindow uses .show(), not .exec_()
                
                # Update stepper state based on validation result
                if report.is_valid:
                    self.validation_passed = True  # Track completion
                    # IMMEDIATELY set status on config so it persists on save
                    self.orchestrator.config_engine.config.validation_status = 'passed'
                    self.stepper.mark_step_complete(1)
                    self._update_status("Strategy validated successfully")
                    
                    # PERSIST VALIDATION STATUS TO DATABASE (Sprint 1.9 ORM)
                    # Update existing version's status (don't create new version)
                    self._save_validation_status_to_db('Pass')
                else:
                    self.validation_passed = False
                    # Clear validation status on error
                    if hasattr(self.orchestrator.config_engine.config, 'validation_status'):
                        delattr(self.orchestrator.config_engine.config, 'validation_status')
                    self.stepper.mark_step_error(1)
                    self._update_status(f"Strategy validation failed - {report.blocking_issues()} blocking issues")
                    
                    # PERSIST FAILURE STATUS TO DATABASE (Sprint 1.9 ORM)
                    # Update existing version's status (don't create new version)
                    self._save_validation_status_to_db('Fail')
                    
            except Exception as e:
                self.validation_passed = False
                self.stepper.mark_step_error(1)
                QMessageBox.critical(
                    self,
                    "Validation Error",
                    f"Error running validation:\n\n{str(e)}"
                )
                self._update_status("Validation error occurred")
        
        elif step == 2:
            # Test / Optimize step - CHECK PREREQUISITES  
            if not self._check_test_prerequisites():
                return  # Prerequisites not met, error shown
            
            self.stepper.set_current_step(2)
            self._on_run_backtest()
            # Mark complete when backtest dialog opens successfully
            self.test_completed = True
        
        elif step == 3:
            # Publish step - CHECK PREREQUISITES
            if not self._check_publish_prerequisites():
                return  # Prerequisites not met, error shown
            
            self.stepper.set_current_step(3)
            QMessageBox.information(
                self,
                "Publish Status",
                "Publish status management coming soon!\n\n"
                "Options: Draft, Unpublished, Published"
            )
            self._update_status("Publish status management coming soon")
    
    def _on_import_from_json(self):
        """Import strategy from JSON file and load into builder."""
        try:
            # Get last directory
            settings = QSettings("BTC_Engine", "StrategyBuilder")
            last_dir = settings.value("lastDirectory", "")
            
            # Show file dialog
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Import Strategy from JSON",
                last_dir,
                "Strategy Files (*.json);;All Files (*)"
            )
            
            if not filename:
                return  # User cancelled
            
            # Load strategy from JSON file
            result = self.orchestrator.load_strategy(filename)
            
            if not result.success:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    f"Failed to import strategy from JSON:\n\n{result.message}"
                )
                return
            
            # Update UI from loaded config
            config = self.orchestrator.get_current_config()
            
            # Set strategy name
            if config.name:
                self.info_panel.set_strategy_name(config.name)
            
            # Set description if available
            if hasattr(config, 'description') and config.description:
                self.info_panel.set_description(config.description)
            
            # Clear tracking (new strategy for database)
            self.current_strategy_id = None
            self.current_version_id = None
            self.current_file = None
            
            # Mark as modified so user can save to database
            self.is_modified = True
            
            # Refresh all panels
            self.search_panel.clear_added_blocks()
            self.blocks_panel.refresh_from_orchestrator()
            self.info_panel.refresh_from_orchestrator()
            
            # Update UI
            self._update_window_title()
            
            # Show success with save reminder
            QMessageBox.information(
                self,
                "Import Successful",
                f"Strategy imported from JSON file!\n\n"
                f"File: {filename}\n\n"
                f"The strategy has been loaded into the builder.\n"
                f"Press Ctrl+S or click Save to save it to the database."
            )
            
            self._update_status(f"Imported strategy from JSON - Ready to save to database")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Error importing strategy from JSON:\n\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _on_update_data(self):
        """
        Open the data update modal (manual mode - no auto-close).
        
        Called from Tools menu - user-initiated action.
        """
        try:
            # Manual mode: no auto-update, no auto-close
            modal = DataUpdateModal(self, auto_mode=False)
            modal.exec_()  # Show modal (blocks until closed)
            self._update_status("Data update check complete")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening data update dialog: {str(e)}")
            self._update_status("Data update check failed")
    
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Strategy Builder",
            "<h2>Strategy Builder</h2>"
            "<p>Version 3.0</p>"
            "<p>Professional trading strategy builder for NautilusTrader</p>"
            "<p>© 2026 BTC Engine v3</p>"
        )
    
    def _update_window_title(self):
        """Update the window title with strategy name and modified status."""
        title = "BTC Engine v3 - Strategy Builder"

        # Show strategy name only (from orchestrator config)
        strategy_name = None
        if self.orchestrator and self.orchestrator.config_engine.config.name:
            strategy_name = self.orchestrator.config_engine.config.name
        elif self.info_panel:
            strategy_name = self.info_panel.get_strategy_name()
        
        if strategy_name and strategy_name != "New_Strategy":
            title += f" - {strategy_name}"
        elif strategy_name == "New_Strategy":
            title += " - Untitled"

        if self.is_modified:
            title += " *"
        
        self.setWindowTitle(title)
    
    def _update_status(self, message: str):
        """Update the status bar message."""
        self.statusBar().showMessage(message)
    
    def _restore_settings(self):
        """Restore window geometry and state from settings."""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        
        # Restore geometry
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
        
        # Restore splitter sizes (user's preferred panel ratio)
        splitter_sizes = settings.value("mainSplitterSizes")
        if splitter_sizes:
            self.main_splitter.restoreState(splitter_sizes)
    
    def _check_strategy_type_match(self) -> bool:
        """
        Check if strategy type matches signal direction.
        
        Returns:
            True if user wants to proceed with save, False if cancelled
        """
        try:
            config = self.orchestrator.get_current_config()
            if not config or not config.blocks:
                return True  # No blocks, nothing to check
            
            # Count bullish vs bearish signals (comprehensive keyword detection)
            bullish_count = 0
            bearish_count = 0
            
            # Define directional keywords
            bullish_keywords = [
                'BULLISH', 'LONG', 'BUY', 'ABOVE', 'OVER', 'UP', 'HIGHER',
                'BREAKOUT', 'SUPPORT', 'BOUNCE', 'REVERSAL_UP', 'UPTREND',
                'ACCUMULATION', 'REACCUMULATION', 'SPRING', 'SOS', 'LPS'
            ]
            
            bearish_keywords = [
                'BEARISH', 'SHORT', 'SELL', 'BELOW', 'UNDER', 'DOWN', 'LOWER',
                'BREAKDOWN', 'RESISTANCE', 'REJECTION', 'REVERSAL_DOWN', 'DOWNTREND',
                'DISTRIBUTION', 'REDISTRIBUTION', 'UPTHRUST', 'SOW', 'LPSY'
            ]
            
            for block in config.blocks:
                for signal in block.signals:
                    signal_name_upper = signal.name.upper()
                    
                    # Check for bullish keywords
                    is_bullish = any(keyword in signal_name_upper for keyword in bullish_keywords)
                    # Check for bearish keywords
                    is_bearish = any(keyword in signal_name_upper for keyword in bearish_keywords)
                    
                    if is_bullish:
                        bullish_count += 1
                    if is_bearish:
                        bearish_count += 1
                    
                    # Note: A signal can have both (e.g., "BULLISH_REJECTION") - count both
            
            # Get current strategy type from UI
            current_type = self.info_panel.get_strategy_type()
            
            # Check for mismatch
            mismatch = False
            suggested_type = None
            
            if current_type == "Bullish" and bearish_count > bullish_count:
                mismatch = True
                suggested_type = "Bearish"
            elif current_type == "Bearish" and bullish_count > bearish_count:
                mismatch = True
                suggested_type = "Bullish"
            
            if not mismatch:
                return True  # All good, proceed with save
            
            # Show warning dialog with fix option
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Strategy Type Mismatch")
            msg.setText(
                f"<b>Strategy Type Mismatch Detected</b><br><br>"
                f"Current Strategy Type: <b>{current_type}</b><br>"
                f"Signal Direction: <b>{suggested_type}</b> "
                f"({bullish_count} bullish, {bearish_count} bearish)<br><br>"
                f"Your strategy contains mostly {suggested_type.lower()} signals, "
                f"but is configured as {current_type}."
            )
            msg.setInformativeText("Would you like to change the strategy type before saving?")
            
            # Add custom buttons
            change_btn = msg.addButton(f"Change to {suggested_type}", QMessageBox.AcceptRole)
            proceed_btn = msg.addButton("Save Anyway", QMessageBox.DestructiveRole)
            cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
            
            msg.setDefaultButton(change_btn)
            msg.exec_()
            
            clicked = msg.clickedButton()
            
            if clicked == change_btn:
                # User wants to change strategy type
                # Update BOTH UI and config immediately to ensure sync
                self.info_panel.set_strategy_type(suggested_type)
                
                # CRITICAL: Force Qt to process the radio button change NOW
                QApplication.processEvents()
                QApplication.processEvents()  # Process twice to ensure state propagates
                
                # Verify the UI actually changed
                actual_type = self.info_panel.get_strategy_type()
                if actual_type != suggested_type:
                    print(f"WARNING: UI didn't update! Expected {suggested_type}, got {actual_type}")
                
                # Also update config directly right now (don't wait for later)
                if hasattr(self.orchestrator.config_engine.config, 'strategy_type'):
                    self.orchestrator.config_engine.config.strategy_type = suggested_type
                else:
                    setattr(self.orchestrator.config_engine.config, 'strategy_type', suggested_type)
                
                self._update_status(f"Strategy type changed to {suggested_type}")
                return True  # Proceed with save
            elif clicked == proceed_btn:
                # User wants to save anyway
                return True  # Proceed with save
            else:
                # User cancelled
                return False  # Don't save
            
        except Exception as e:
            # Don't block save on error, just log and proceed
            print(f"Error checking strategy type match: {e}")
            return True
    
    def _show_data_update_modal(self):
        """
        Show the data update modal on startup (auto mode - auto-close).
        
        Called automatically on startup - auto-updates and auto-closes.
        """
        try:
            # Auto mode (default): auto-update gaps, auto-close after countdown
            modal = DataUpdateModal(self, auto_mode=True)
            modal.exec_()  # Show modal (blocks until closed)
        except Exception as e:
            # Don't block app startup if modal fails
            print(f"Warning: Data update modal failed: {e}")
            self._update_status("Data update check skipped (error occurred)")
    
    def _start_auto_update_system(self):
        """
        Start automatic data update system.
        
        Updates every 15 minutes:
        - Checks 0.2s after candle close
        - Retries every 2s until data is fresh
        """
        try:
            # Calculate time until next candle close (15-min candles)
            now = datetime.now()
            
            # Next 15-min boundary
            minutes_to_next = 15 - (now.minute % 15)
            seconds_to_next = (minutes_to_next * 60) - now.second
            
            # Add 0.2s delay after candle close
            ms_until_check = (seconds_to_next * 1000) + 200
            
            # Schedule first check
            QTimer.singleShot(ms_until_check, self._check_and_update_data)
            
            self._update_status(f"Auto-update system started - Next check in {seconds_to_next}s")
            
        except Exception as e:
            print(f"Error starting auto-update system: {e}")
    
    def _check_and_update_data(self):
        """
        Check if data needs updating and update if necessary.
        
        Called 0.2s after each 15-min candle close.
        Retries every 2s until data is fresh.
        """
        try:
            self._update_status("Checking for data updates...")
            
            # Import unified manager and Binance client
            from src.data_manager.unified_manager import UnifiedDataManager
            from src.data_manager.binance.rest_client import BinanceRestClient
            
            # Check data status
            manager = UnifiedDataManager()
            status = manager.get_all_data_types_status()
            
            # Check for gaps in trades (15min data)
            trades_status = status.get('trades', {})
            gap_minutes = trades_status.get('gap_minutes', 999)
            
            # If gap > 20 minutes (more than 1 candle + buffer), download
            if gap_minutes > 20:
                # Data needs updating
                self._update_status(f"Downloading fresh data (gap: {gap_minutes} min)...")
                
                try:
                    # Use Binance client to download and save
                    client = BinanceRestClient()
                    bars = client.get_klines('15m', limit=100, futures=True)
                    
                    if len(bars) > 0:
                        # Save to Binance directory
                        now = datetime.now()
                        month_dir = manager.binance_dir / f"{now.year}-{now.month:02d}"
                        month_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save with month-level filename
                        output_file = month_dir / f"BTCUSDT_PERP_15m_{now.year}-{now.month:02d}.parquet"
                        
                        # If file exists, merge with existing data
                        if output_file.exists():
                            existing = pd.read_parquet(output_file)
                            bars = pd.concat([existing, bars], ignore_index=True)
                            bars = bars.drop_duplicates(subset=['timestamp'], keep='last')
                            bars = bars.sort_values('timestamp')
                        
                        # Save merged data
                        bars.to_parquet(output_file, index=False)
                        
                        self.last_update_time = datetime.now()
                        self._update_status(f"Data updated at {self.last_update_time.strftime('%H:%M:%S')}")
                    else:
                        self._update_status("No data received from Binance")
                        
                except Exception as e:
                    print(f"Error downloading data: {e}")
                    self._update_status(f"Download error: {str(e)}")
                
                # Schedule next check (in 15 minutes)
                QTimer.singleShot(15 * 60 * 1000, self._schedule_next_check)
                
            else:
                # Data is fresh, schedule next check
                self._update_status(f"Data is fresh (gap: {gap_minutes} min)")
                QTimer.singleShot(15 * 60 * 1000, self._schedule_next_check)
            
        except Exception as e:
            print(f"Error checking/updating data: {e}")
            import traceback
            traceback.print_exc()
            self._update_status(f"Data update error: {str(e)}")
            # Schedule next check anyway
            QTimer.singleShot(15 * 60 * 1000, self._schedule_next_check)
    
    def _schedule_next_check(self):
        """Schedule the next data check at 0.2s after next candle close."""
        try:
            # Calculate time until next 15-min candle close
            now = datetime.now()
            minutes_to_next = 15 - (now.minute % 15)
            seconds_to_next = (minutes_to_next * 60) - now.second
            
            # Add 0.2s delay after candle close
            ms_until_check = (seconds_to_next * 1000) + 200
            
            # Schedule check
            QTimer.singleShot(ms_until_check, self._check_and_update_data)
            
            # Save next check time for countdown
            self.next_check_time = now + timedelta(seconds=seconds_to_next)
            
        except Exception as e:
            print(f"Error scheduling next check: {e}")
    
    def _update_countdown_status(self):
        """Update status bar with live countdown to next data check."""
        try:
            # Only show countdown when nothing else is being displayed
            current_status = self.statusBar().currentMessage()
            
            # Check if we should show countdown (not during active operations)
            if current_status and any(keyword in current_status for keyword in [
                'Added block', 'Strategy updated', 'Saved', 'Loaded', 'Checking',
                'Updating', 'Validat', 'Generated', 'cleared', 'created'
            ]):
                # Don't override active status messages
                return
            
            # Show countdown if next check is scheduled
            if self.next_check_time:
                now = datetime.now()
                seconds_until = (self.next_check_time - now).total_seconds()
                
                if seconds_until > 0:
                    minutes = int(seconds_until // 60)
                    seconds = int(seconds_until % 60)
                    
                    if minutes > 0:
                        self._update_status(f"Next data check in {minutes}m {seconds}s")
                    else:
                        self._update_status(f"Next data check in {seconds}s")
                else:
                    self._update_status("Checking for data updates...")
            else:
                # No check scheduled yet
                self._update_status("Ready")
                
        except Exception as e:
            # Silently fail to avoid disrupting UI
            pass
    
    def _save_validation_status_to_db(self, status: str):
        """
        Persist validation status to database (Sprint 1.9 ORM persistence).
        
        Updates the strategy_versions table with validation_status and validation_timestamp.
        
        Args:
            status: 'Pass' or 'Fail'
        """
        if not self.current_version_id:
            return  # No version to update yet (strategy not saved)
        
        try:
            from datetime import datetime
            from src.optimizer_v3.database.models import StrategyVersion
            
            db = get_database_manager()
            
            # Get the strategy version using ORM
            version = db.strategy.session.query(StrategyVersion).filter(
                StrategyVersion.version_id == self.current_version_id
            ).first()
            
            if version:
                # Update using ORM
                version.validation_status = status
                version.validation_timestamp = datetime.utcnow()
                db.strategy.session.commit()
            
        except Exception as e:
            # Rollback on error
            try:
                db.strategy.session.rollback()
            except:
                pass
            # Don't fail the UI if database save fails - log silently
            import traceback
            traceback.print_exc()
    
    def _check_validation_prerequisites(self) -> bool:
        """Check if validation prerequisites are met (strategy name + blocks)."""
        strategy_name = self.info_panel.get_strategy_name()
        block_count = self.blocks_panel.get_block_count()
        
        errors = []
        if not strategy_name or strategy_name.strip() == "":
            errors.append("• Strategy must have a name")
        if block_count == 0:
            errors.append("• Strategy must have at least one building block")
        
        if errors:
            show_warning(
                self,
                "Cannot Validate Strategy",
                "Validation Prerequisites Not Met",
                "Please complete the following before validating:\n\n" +
                "\n".join(errors)
            )
            return False
        return True
    
    def _check_generation_prerequisites(self) -> bool:
        """Check if code generation prerequisites are met (valid strategy)."""
        if not self.validation_passed:
            show_warning(
                self,
                "Cannot Generate Code",
                "Validation Required",
                "You must successfully validate your strategy before generating code.\n\n"
                "Steps:\n"
                "1. Click the Validate step\n"
                "2. Fix any validation errors\n"
                "3. Return here to generate code"
            )
            return False
        return True
    
    def _check_test_prerequisites(self) -> bool:
        """Check if testing prerequisites are met (validated strategy)."""
        if not self.validation_passed:
            # Check if validation step is in error state (RED) - means validation FAILED
            # StepperRibbon uses error_steps set to track failed steps
            if 1 in self.stepper.error_steps:  # Index 1 is Validate step
                # Validation was run but FAILED
                show_warning(
                    self,
                    "Cannot Run Test / Optimize",
                    "Strategy Validation FAILED",
                    "Your strategy failed validation and cannot be tested until all errors are resolved.\n\n"
                    "Required Actions:\n"
                    "1. Click the Validate button\n"
                    "2. Review the validation report\n"
                    "3. Fix all blocking issues (marked in RED)\n"
                    "4. Click Validate again to re-check\n"
                    "5. Return here once validation passes"
                )
            else:
                # Validation hasn't been run yet
                show_warning(
                    self,
                    "Cannot Run Test / Optimize",
                    "Validation Required",
                    "You must validate your strategy before running tests.\n\n"
                    "Steps:\n"
                    "1. Click the Validate step\n"
                    "2. Fix any validation errors\n"
                    "3. Return here to run tests and optimize"
                )
            return False
        return True
    
    def _check_publish_prerequisites(self) -> bool:
        """Check if publish prerequisites are met (tests completed)."""
        if not self.test_completed:
            show_warning(
                self,
                "Cannot Publish Strategy",
                "Testing Required",
                "You must complete testing before publishing.\n\n"
                "Steps:\n"
                "1. Complete validation\n"
                "2. Click the Test / Optimize step to run backtests\n"
                "3. Review results\n"
                "4. Return here to publish"
            )
            return False
        return True
    
    def _on_toggle_console_debug(self, checked: bool):
        """Toggle debug output to console."""
        from src.debugger_logger.config_debugger import ConfigDebugger
        
        # Update global console logging state
        ConfigDebugger.CONSOLE_ENABLED = checked
        
        # Update menu text  
        self._update_console_menu_text(checked)
        
        # Save setting
        self._save_debug_settings()
        
        status = "enabled" if checked else "disabled"
        self._update_status(f"Console debugging {status}")
    
    def _on_toggle_logfile_debug(self, checked: bool):
        """Toggle debug output to log files."""
        from src.debugger_logger.config_debugger import ConfigDebugger
        
        # Update global file logging state
        ConfigDebugger.LOGFILE_ENABLED = checked
        
        # Update menu text
        self._update_logfile_menu_text(checked)
        
        # Save setting
        self._save_debug_settings()
        
        status = "enabled" if checked else "disabled"
        self._update_status(f"Log file debugging {status}")
    
    def _on_clear_old_logs(self):
        """Delete ALL log files."""
        import os
        from pathlib import Path
        
        # Use ABSOLUTE path to logs directory
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        logs_dir = project_root / 'logs'
        
        # Ask for confirmation
        reply = ask_question(
            self,
            "Clear Old Logs",
            "Delete Old Log Files",
            f"This will delete ALL log files from:\n{logs_dir}\n\nAre you sure you want to continue?"
        )
        
        if reply != 'yes':
            return
        
        try:
            if not logs_dir.exists():
                QMessageBox.information(
                    self,
                    "No Logs Found",
                    f"No logs directory found at:\n{logs_dir}"
                )
                return
            
            # Count files
            deleted_count = 0
            total_size = 0
            
            # Recursively find and delete ALL log files
            for log_file in logs_dir.rglob('*.log'):
                try:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    total_size += file_size
                except Exception as e:
                    print(f"Error deleting {log_file}: {e}")
            
            # Show result
            size_mb = total_size / (1024 * 1024)
            QMessageBox.information(
                self,
                "Logs Cleared",
                f"Successfully deleted {deleted_count} log files.\n\n"
                f"Space freed: {size_mb:.2f} MB"
            )
            self._update_status(f"Deleted {deleted_count} log files ({size_mb:.1f} MB)")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error clearing logs:\n\n{str(e)}"
            )
    
    def _on_view_current_log(self):
        """Open the most recent log file in professional log viewer."""
        from pathlib import Path
        from src.strategy_builder.ui.log_viewer_window import LogViewerWindow
        
        try:
            # Get logs directory
            logs_dir = Path('logs')
            if not logs_dir.exists():
                QMessageBox.information(
                    self,
                    "No Logs Found",
                    "No logs directory found."
                )
                return
            
            # Find all log files
            log_files = list(logs_dir.rglob('*.log'))
            
            if not log_files:
                QMessageBox.information(
                    self,
                    "No Logs Found",
                    "No log files found in logs directory."
                )
                return
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Get the newest log file
            newest_log = log_files[0]
            
            # Open in professional log viewer window
            viewer = LogViewerWindow(newest_log, self)
            viewer.show()
            
            self._update_status(f"Opened log viewer: {newest_log.name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error opening log viewer:\n\n{str(e)}"
            )
    
    def _restore_debug_settings(self):
        """Restore debug logger settings."""
        from src.debugger_logger.config_debugger import ConfigDebugger
        
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        
        # Restore console debug setting (default: False - disabled)
        console_enabled = settings.value("debug/consoleEnabled", False, type=bool)
        ConfigDebugger.CONSOLE_ENABLED = console_enabled
        self.enable_console_action.setChecked(console_enabled)
        self._update_console_menu_text(console_enabled)
        
        # Restore logfile debug setting (default: False - disabled)
        logfile_enabled = settings.value("debug/logfileEnabled", False, type=bool)
        ConfigDebugger.LOGFILE_ENABLED = logfile_enabled
        self.enable_logfile_action.setChecked(logfile_enabled)
        self._update_logfile_menu_text(logfile_enabled)
    
    def _save_debug_settings(self):
        """Save debug logger settings."""
        from src.debugger_logger.config_debugger import ConfigDebugger
        
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        settings.setValue("debug/consoleEnabled", ConfigDebugger.CONSOLE_ENABLED)
        settings.setValue("debug/logfileEnabled", ConfigDebugger.LOGFILE_ENABLED)
    
    def _update_console_menu_text(self, enabled: bool):
        """Update console debug menu text based on state."""
        if enabled:
            self.enable_console_action.setText("Disable Debugger in Console")
        else:
            self.enable_console_action.setText("Enable Debugger in Console")
    
    def _update_logfile_menu_text(self, enabled: bool):
        """Update logfile debug menu text based on state."""
        if enabled:
            self.enable_logfile_action.setText("Disable Debugger in Log File")
        else:
            self.enable_logfile_action.setText("Enable Debugger in Log File")
    
    def _save_settings(self):
        """Save window geometry, state, and debug settings."""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        # Save splitter sizes (user's preferred panel ratio)
        settings.setValue("mainSplitterSizes", self.main_splitter.saveState())
        self._save_debug_settings()
    
    def showEvent(self, event):
        """Called when window is shown - apply hand cursors to all widgets"""
        super().showEvent(event)
        # Apply hand cursor AFTER Qt finishes all stylesheet processing
        # Qt may reapply stylesheets after showEvent, so delay cursor setting
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Check if current strategy should be saved (skip if empty)
        if self.is_modified and not self._is_strategy_empty():
            reply = ask_question(
                self,
                "Unsaved Changes",
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?"
            )
            
            if reply == 'yes':
                if self._on_save_strategy():
                    self._save_settings()
                    event.accept()
                else:
                    event.ignore()
            elif reply == 'no':
                self._save_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self._save_settings()
            event.accept()
