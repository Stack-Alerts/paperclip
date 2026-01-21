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
    QAction, QToolBar, QStatusBar, QFileDialog, QMessageBox
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
from src.strategy_builder.ui.validation_dialog import ValidationDialog
from src.strategy_builder.ui.backtest_config_dialog import BacktestConfigDialog
from src.strategy_builder.ui.data_update_modal import DataUpdateModal
from src.strategy_builder.ui.alert_dialog import show_warning, ask_question
from src.strategy_builder.ui.stepper_ribbon import StepperRibbon
from src.strategy_builder.ui.styles import get_main_stylesheet

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
        
        # Track current file
        self.current_file: Optional[str] = None
        self.is_modified = False
        
        # Track workflow state (step completion flags)
        self.validation_passed = False
        self.test_completed = False
        
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
        
        generate_action = QAction(style.standardIcon(QStyle.SP_FileDialogDetailedView), "&Generate Code", self)
        generate_action.setStatusTip("Generate NautilusTrader code from strategy")
        generate_action.triggered.connect(self._on_generate_code)
        tools_menu.addAction(generate_action)
        
        tools_menu.addSeparator()
        
        update_data_action = QAction(style.standardIcon(QStyle.SP_BrowserReload), "&Update Data...", self)
        update_data_action.setStatusTip("Check for data gaps and update from Binance")
        update_data_action.triggered.connect(self._on_update_data)
        tools_menu.addAction(update_data_action)
        
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
    
    def _on_block_selected(self, block_name: str):
        """Handle block selection from search panel."""
        # NOTE: Blocks are now added via orchestrator.add_block_with_signals()
        # which is called from the search panel. We just need to refresh the display.
        
        # Refresh blocks panel to show newly added block
        self.blocks_panel.refresh_from_orchestrator()
        
        # Refresh info panel to update description and required signals
        self.info_panel.refresh_from_orchestrator()
        
        # Mark as added in search panel
        self.search_panel.mark_block_as_added(block_name)
        
        # Update status
        block_count = self.blocks_panel.get_block_count()
        self._update_status(f"Added block: {block_name} ({block_count} blocks total)")
        self.is_modified = True
        self._update_window_title()
    
    def _on_blocks_changed(self):
        """Handle blocks changed event."""
        # Refresh info panel to update description and required signals
        self.info_panel.refresh_from_orchestrator()
        
        # Mark as modified
        self.is_modified = True
        self._update_window_title()
        
        # Update status
        block_count = self.blocks_panel.get_block_count()
        self._update_status(f"Strategy updated - {block_count} block(s) configured")
    
    def _on_strategy_name_changed(self, name: str):
        """Handle strategy name change."""
        self.is_modified = True
        self._update_window_title()
    
    def _on_new_strategy(self):
        """Create a new strategy."""
        # Check if current strategy should be saved
        if self.is_modified:
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
        
        # Reset strategy name in UI
        self.info_panel.set_strategy_name("")
        
        # CRITICAL: Create new empty strategy in orchestrator (clears all blocks)
        self.orchestrator.create_strategy("New_Strategy")
        
        # Clear current file tracking
        self.current_file = None
        self.is_modified = False
        
        # Clear visual markers in search panel
        self.search_panel.clear_added_blocks()
        
        # Refresh all panels to show empty state
        self.blocks_panel.refresh_from_orchestrator()
        self.info_panel.refresh_from_orchestrator()
        
        # Update UI
        self._update_window_title()
        self._update_status("New strategy created - ready to configure")
    
    def _on_open_strategy(self):
        """Open an existing strategy."""
        # Get last used directory
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        last_dir = settings.value("lastDirectory", "")
        
        # Create custom dialog with larger size and persistence
        # Pass None as parent so dialog is independent and can be moved freely
        dialog = QFileDialog(None, "Open Strategy", last_dir, "Strategy Files (*.json);;All Files (*)")
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        
        # CRITICAL: Use Qt's dialog instead of native dialog (native doesn't respect sizing)
        dialog.setOptions(QFileDialog.DontUseNativeDialog)
        
        # Apply dark theme stylesheet (since parent is None, it doesn't inherit)
        dialog.setStyleSheet(self.styleSheet())
        
        # Set larger default size (1600x1200 - 100% bigger per user request)
        dialog.resize(1600, 1200)
        
        # Restore saved size if available
        dialog_geometry = settings.value("openDialog/geometry")
        if dialog_geometry:
            dialog.restoreGeometry(dialog_geometry)
        
        # Execute dialog
        if dialog.exec_() != QFileDialog.Accepted:
            return
        
        # Save dialog geometry for next time
        settings.setValue("openDialog/geometry", dialog.saveGeometry())
        
        files = dialog.selectedFiles()
        if not files:
            return
        
        filename = files[0]
        
        if filename:
            try:
                # Load strategy (orchestrator handles this)
                result = self.orchestrator.load_strategy(filename)
                
                if result.success:
                    self.current_file = filename
                    self.is_modified = False
                    
                    # Save directory for next time
                    import os
                    settings.setValue("lastDirectory", os.path.dirname(filename))
                    
                    # RESET WORKFLOW STATE FIRST (clear previous strategy state)
                    self.validation_passed = False
                    self.test_completed = False
                    self.stepper.reset_all_steps()  # Clear all step states
                    
                    # Refresh all panels
                    self.info_panel.refresh_from_orchestrator()
                    self.blocks_panel.refresh_from_orchestrator()
                    
                    # Mark blocks as added in search panel
                    for block_name in self.blocks_panel.get_block_names():
                        self.search_panel.mark_block_as_added(block_name)
                    
                    # RESTORE WORKFLOW STATE from loaded strategy JSON
                    config = self.orchestrator.get_current_config()
                    if config:
                        # Check validation status from JSON
                        validation_status = getattr(config, 'validation_status', None)
                        if validation_status == 'passed':
                            self.validation_passed = True
                            self.stepper.mark_step_complete(1)
                    
                    self._update_window_title()
                    self._update_status(f"Loaded strategy from:{filename}")
                else:
                    QMessageBox.warning(self, "Load Failed", f"Failed to load strategy: {result.message}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading strategy: {str(e)}")
    
    def _on_save_strategy(self) -> bool:
        """Save the current strategy."""
        if self.current_file:
            return self._save_to_file(self.current_file)
        else:
            return self._on_save_strategy_as()
    
    def _on_save_strategy_with_feedback(self) -> bool:
        """Save the current strategy with success dialog (for validation dialog)."""
        if self.current_file:
            return self._save_to_file(self.current_file, show_success=True)
        else:
            # Save As always shows its own dialog, so no need for extra feedback
            return self._on_save_strategy_as()
    
    def _on_save_strategy_as(self) -> bool:
        """Save the strategy with a new filename."""
        # Get last used directory
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        last_dir = settings.value("lastDirectory", "")
        
        # Create custom dialog with larger size and persistence
        # Pass None as parent so dialog is independent and can be moved freely
        dialog = QFileDialog(None, "Save Strategy As", last_dir, "Strategy Files (*.json);;All Files (*)")
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setDefaultSuffix("json")
        
        # CRITICAL: Use Qt's dialog instead of native dialog (native doesn't respect sizing)
        dialog.setOptions(QFileDialog.DontUseNativeDialog)
        
        # Apply dark theme stylesheet (since parent is None, it doesn't inherit)
        dialog.setStyleSheet(self.styleSheet())
        
        # Auto-generate filename from strategy name
        strategy_name = self.info_panel.get_strategy_name()
        if strategy_name:
            # Convert to valid filename: lowercase, spaces to underscores
            filename_base = strategy_name.lower().replace(' ', '_')
            # Remove any invalid characters
            import re
            filename_base = re.sub(r'[^\w\-_]', '', filename_base)
            suggested_filename = f"{filename_base}.json"
            # Set as default filename
            dialog.selectFile(suggested_filename)
        
        # Set larger default size (1600x1200 - 100% bigger per user request)
        dialog.resize(1600, 1200)
        
        # Restore saved size if available
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        dialog_geometry = settings.value("saveDialog/geometry")
        if dialog_geometry:
            dialog.restoreGeometry(dialog_geometry)
        
        # Execute dialog
        if dialog.exec_() != QFileDialog.Accepted:
            return False
        
        # Save dialog geometry for next time
        settings.setValue("saveDialog/geometry", dialog.saveGeometry())
        
        files = dialog.selectedFiles()
        if not files:
            return False
        
        filename = files[0]
        if not filename.endswith('.json'):
            filename += '.json'
        
        return self._save_to_file(filename)
    
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
    
    def _on_generate_code(self):
        """Generate NautilusTrader code from strategy."""
        try:
            result = self.orchestrator.generate_code()
            
            if result.success:
                # Show success message
                QMessageBox.information(
                    self,
                    "Code Generated",
                    f"Code generated successfully!\n\nSaved to: {result.data.get('file_path', 'Unknown')}"
                )
                self._update_status("Code generated successfully")
            else:
                QMessageBox.warning(
                    self,
                    "Generation Failed",
                    f"Code generation failed:\n\n{result.message}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating code: {str(e)}")
    
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
            
            # Create and show validation dialog
            dialog = ValidationDialog(self.orchestrator, self)
            
            # Connect dialog signals to main window actions (with visual feedback)
            dialog.validation_panel.save_requested.connect(lambda: self._on_save_strategy_with_feedback())
            dialog.validation_panel.generate_requested.connect(self._on_generate_code)
            dialog.validation_panel.run_test_requested.connect(self._on_run_backtest)
            
            # Show modal dialog
            dialog.exec_()
            
            # Update stepper state based on validation result
            result = self.orchestrator.validate_strategy()
            if result.success:
                self.validation_passed = True  # Track completion
                # IMMEDIATELY set status on config so it persists on save
                self.orchestrator.config_engine.config.validation_status = 'passed'
                self.stepper.mark_step_complete(1)
                self._update_status("Strategy validated successfully")
                
                # AUTO-SAVE after validation (if file exists)
                if self.current_file:
                    self._save_to_file(self.current_file)
            else:
                self.validation_passed = False
                # Clear validation status on error
                if hasattr(self.orchestrator.config_engine.config, 'validation_status'):
                    delattr(self.orchestrator.config_engine.config, 'validation_status')
                self.stepper.mark_step_error(1)
                self._update_status("Strategy validation has errors")
        
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
    
    def _on_update_data(self):
        """Open the data update modal."""
        try:
            modal = DataUpdateModal(self)
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
        """Show the data update modal on startup."""
        try:
            modal = DataUpdateModal(self)
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
        """Delete old log files."""
        import os
        from pathlib import Path
        
        # Ask for confirmation
        reply = ask_question(
            self,
            "Clear Old Logs",
            "Delete Old Log Files",
            "This will delete all log files older than today.\n\n"
            "Are you sure you want to continue?"
        )
        
        if reply != 'yes':
            return
        
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
            
            # Get today's date
            today = datetime.now().date()
            
            # Count files
            deleted_count = 0
            total_size = 0
            
            # Recursively find and delete old log files
            for log_file in logs_dir.rglob('*.log'):
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    file_date = file_mtime.date()
                    
                    # Delete if older than today
                    if file_date < today:
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
                f"Successfully deleted {deleted_count} old log files.\n\n"
                f"Space freed: {size_mb:.2f} MB"
            )
            self._update_status(f"Deleted {deleted_count} old log files ({size_mb:.1f} MB)")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error clearing old logs:\n\n{str(e)}"
            )
    
    def _on_view_current_log(self):
        """Open the most recent log file."""
        import os
        import subprocess
        from pathlib import Path
        
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
            
            # Open with default text editor
            # Use xdg-open on Linux, open on macOS, start on Windows
            try:
                if os.name == 'posix':
                    # Linux/Mac - use xdg-open with detached process
                    subprocess.Popen(
                        ['xdg-open', str(newest_log)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                elif os.name == 'nt':
                    # Windows
                    os.startfile(str(newest_log))
                else:
                    # Unknown OS - just show path
                    raise OSError("Unknown operating system")
                
                self._update_status(f"Opened log file: {newest_log.name}")
                
            except Exception as open_error:
                # Fallback: Show path and copy to clipboard
                from PyQt5.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                clipboard.setText(str(newest_log.absolute()))
                
                QMessageBox.information(
                    self,
                    "Log File Location",
                    f"Most recent log file:\n\n{newest_log.absolute()}\n\n"
                    f"(Path copied to clipboard)"
                )
                self._update_status(f"Log file path copied to clipboard: {newest_log.name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error finding log file:\n\n{str(e)}"
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
        self._save_debug_settings()
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_modified:
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
