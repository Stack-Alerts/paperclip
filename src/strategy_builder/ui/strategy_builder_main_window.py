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
from PyQt5.QtCore import Qt, QSize, QSettings
from PyQt5.QtGui import QIcon, QKeySequence, QFont
from PyQt5.QtWidgets import QApplication, QStyle

from src.strategy_builder.integration.strategy_builder_orchestrator import (
    StrategyBuilderOrchestrator
)
from src.strategy_builder.ui.strategy_info_panel import StrategyInfoPanel
from src.strategy_builder.ui.block_search_panel import BlockSearchPanel
from src.strategy_builder.ui.strategy_blocks_panel import StrategyBlocksPanel
from src.strategy_builder.ui.validation_dialog import ValidationDialog
from src.strategy_builder.ui.stepper_ribbon import StepperRibbon

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
        
        # Restore window geometry from settings
        self._restore_settings()
    
    def _init_ui(self):
        """Initialize the user interface layout."""
        # Window properties
        self.setWindowTitle("Strategy Builder")
        self.setGeometry(100, 100, 1400, 900)
        
        # Use OS title bar (change via GNOME theme - see TITLE_BAR_COLOR_FIX.md)
        
        # Apply dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #15191E;
            }
            QWidget {
                background-color: #15191E;
                color: #E8EAED;
            }
            QGroupBox {
                background-color: #1E2128;
                border: 1px solid #3C4149;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: #E8EAED;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
                color: #E8EAED;
            }
            QLineEdit {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 6px;
                padding: 8px;
                color: #E8EAED;
            }
            QLineEdit:focus {
                border-color: #2070FF;
            }
            QComboBox {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 6px;
                padding: 6px 10px;
                color: #E8EAED;
            }
            QComboBox:hover {
                border-color: #2070FF;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                selection-background-color: #2070FF;
                color: #E8EAED;
            }
            QTextEdit {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 6px;
                padding: 8px;
                color: #BDC1C6;
            }
            QLabel {
                color: #E8EAED;
                background: transparent;
            }
            QScrollArea {
                background-color: #15191E;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1E2128;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #3C4149;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4A5058;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QSplitter::handle {
                background-color: #3C4149;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
            QSplitter::handle:vertical {
                height: 2px;
            }
            QMenuBar {
                background-color: #1E2128;
                color: #E8EAED;
                border-bottom: 1px solid #3C4149;
            }
            QMenuBar::item:selected {
                background-color: #2A2F3A;
            }
            QMenu {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                color: #E8EAED;
            }
            QMenu::item:selected {
                background-color: #2070FF;
            }
            QToolBar {
                background-color: #1E2128;
                border-bottom: 1px solid #3C4149;
                border-top: 1px solid #3C4149;
                spacing: 8px;
                padding: 8px 4px;
                margin-top: 4px;
            }
            QToolButton {
                background: transparent;
                border: none;
                color: #A0AEC0;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #2A2F3A;
                border-radius: 4px;
            }
            QToolButton:pressed {
                background-color: #374151;
            }
            QStatusBar {
                background-color: #1E2128;
                color: #9AA0A6;
                border-top: 1px solid #3C4149;
            }
        """)
        
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
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                " You have unsaved changes. Do you want to save before creating a new strategy?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                if not self._on_save_strategy():
                    return  # Save was cancelled
            elif reply == QMessageBox.Cancel:
                return
        
        # Create new strategy
        self.info_panel.set_strategy_name("")
        self.current_file = None
        self.is_modified = False
        
        # Clear blocks panel
        self.search_panel.clear_added_blocks()
        
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
        
        # Set larger default size (800x600)
        dialog.resize(800, 600)
        
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
                    
                    # Refresh all panels
                    self.info_panel.refresh_from_orchestrator()
                    self.blocks_panel.refresh_from_orchestrator()
                    
                    # Mark blocks as added in search panel
                    for block_name in self.blocks_panel.get_block_names():
                        self.search_panel.mark_block_as_added(block_name)
                    
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
        
        # Set larger default size (800x600)
        dialog.resize(800, 600)
        
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
        reply = QMessageBox.question(
            self,
            "Clear Blocks",
            "Are you sure you want to remove all blocks from the strategy?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
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
        QMessageBox.information(
            self,
            "Backtest",
            "Backtest functionality will be available in the Backtest Configuration Panel.\n\n"
            "Coming soon in Phase 2!"
        )
        self._update_status("Backtest panel coming soon")
    
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
        Handle stepper ribbon step click.
        
        Step 0: Design - Always active
        Step 1: Validate - Opens validation dialog
        Step 2: Generate - Generates code
        Step 3: Test - Opens backtest
        Step 4: Publish - Sets status
        """
        if step == 0:
            # Design step - just highlight it
            self.stepper.set_current_step(0)
            self._update_status("Design your strategy by adding blocks")
        
        elif step == 1:
            # Validate step - show validation dialog
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
                self.stepper.mark_step_complete(1)
                self._update_status("Strategy validated successfully")
            else:
                self.stepper.mark_step_error(1)
                self._update_status("Strategy validation has errors")
        
        elif step == 2:
            # Generate step - generate code
            self.stepper.set_current_step(2)
            self._on_generate_code()
            # Mark as complete after generation
            result = self.orchestrator.generate_code()
            if result.success:
                self.stepper.mark_step_complete(2)
            else:
                self.stepper.mark_step_error(2)
        
        elif step == 3:
            # Test step - run backtest
            self.stepper.set_current_step(3)
            self._on_run_backtest()
            # TODO: Mark complete when backtest runs successfully
        
        elif step == 4:
            # Publish step - set status
            self.stepper.set_current_step(4)
            QMessageBox.information(
                self,
                "Publish Status",
                "Publish status management coming soon!\n\n"
                "Options: Draft, Unpublished, Published"
            )
            self._update_status("Publish status management coming soon")
    
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
        """Update the window title with current file and modified status."""
        title = "BTC Engine v3 - Strategy Builder"
        
        if self.current_file:
            title += f" - {self.current_file}"
        elif self.info_panel and self.info_panel.get_strategy_name():
            title += f" - {self.info_panel.get_strategy_name()}"
        
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
    
    def _save_settings(self):
        """Save window geometry and state to settings."""
        settings = QSettings("BTC_Engine", "StrategyBuilder")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                if self._on_save_strategy():
                    self._save_settings()
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.No:
                self._save_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self._save_settings()
            event.accept()
