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
    QToolBar, QStatusBar, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.Strategy_Builder import (
    StrategyRegistry,
    StrategyValidator,
    StrategyGenerator
)
from src.utils.Strategy_Builder.qt_gui.block_library import BlockLibraryPanel
from src.utils.Strategy_Builder.qt_gui.code_preview import CodePreviewDialog
from src.utils.Strategy_Builder.qt_gui.strategy_creator import StrategyCreatorDialog


class StrategyBuilderMainWindow(QMainWindow):
    """Main window for Strategy Builder PyQt6 UI"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize backend components
        self.registry = StrategyRegistry()
        self.validator = StrategyValidator()
        self.generator = StrategyGenerator()
        
        # Setup UI
        self.init_ui()
        self.apply_dark_theme()
        self.load_strategies()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Strategy Builder v3.0 - Professional")
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
        
        toolbar.addSeparator()
        
        # Refresh button
        refresh_btn = QAction('🔄 Refresh', self)
        refresh_btn.triggered.connect(self.load_strategies)
        toolbar.addAction(refresh_btn)
        
    def create_central_widget(self):
        """Create main content area"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panes (3-pane)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left pane: Block Library
        self.block_library = BlockLibraryPanel()
        splitter.addWidget(self.block_library)
        
        # Middle pane: Strategy list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("📋 Strategies")
        list_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #ffffff;")
        left_layout.addWidget(list_label)
        
        # Status filter
        filter_layout = QHBoxLayout()
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
        left_layout.addLayout(filter_layout)
        
        self.strategy_list = QListWidget()
        self.strategy_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.strategy_list.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.strategy_list)
        
        splitter.addWidget(left_widget)
        
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
        
        validate_btn = QPushButton("✓ Validate Selected")
        validate_btn.clicked.connect(self.validate_strategy)
        button_layout.addWidget(validate_btn)
        
        generate_btn = QPushButton("⚙ Generate Files")
        generate_btn.clicked.connect(self.generate_files)
        button_layout.addWidget(generate_btn)
        
        preview_btn = QPushButton("👁 Preview Code")
        preview_btn.clicked.connect(self.preview_code)
        button_layout.addWidget(preview_btn)
        
        right_layout.addLayout(button_layout)
        
        splitter.addWidget(right_widget)
        
        # Set initial sizes (25% library, 30% strategies, 45% details)
        splitter.setSizes([250, 300, 450])
        
        layout.addWidget(splitter)
        
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
            
            # Apply filter
            show_strategy = False
            if filter_text == "All Status":
                show_strategy = True
            elif filter_text == "💾 Drafts Only" and status_type == "draft":
                show_strategy = True
            elif filter_text == "📝 Ready Only" and status_type == "ready":
                show_strategy = True
            elif filter_text == "✅ Published Only" and status_type == "published":
                show_strategy = True
            
            if show_strategy:
                item_text = f"{strategy.number:03d}. {strategy.name} ({strategy.category}){status}"
                self.strategy_list.addItem(item_text)
                displayed_count += 1
        
        total = len(strategies)
        if filter_text == "All Status":
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
            details = f"""Strategy #{strategy_num:03d}
------------------
Name: {config.strategy_name}
Category: {config.strategy_category}

Building Blocks ({len(config.blocks)}):
"""
            for i, block in enumerate(config.blocks, 1):
                details += f"\n{i}. {block.block_name} (Weight: {block.weight})"
                for signal in block.signals:
                    details += f"\n   - {signal.signal_name}"
            
            self.details_text.setPlainText(details)
            self.status_bar.showMessage(f"Selected: Strategy #{strategy_num:03d}")
            
    def new_strategy(self):
        """Create new strategy"""
        try:
            # Check if slots available
            next_num = self.registry.get_next_strategy_number()
            
            # Launch visual creator
            creator = StrategyCreatorDialog(self)
            if creator.exec():
                # Refresh list after successful creation
                self.load_strategies()
                
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
        
        # Launch visual creator with existing config
        creator = StrategyCreatorDialog(self, existing_config=config)
        if creator.exec():
            # Refresh list after successful edit
            self.load_strategies()
            
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
        """Generate strategy files"""
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
            files = self.registry.generate_strategy_files(strategy_num)
            if files:
                # Show preview dialog
                preview = CodePreviewDialog(files, self)
                preview.exec()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Generation failed:\n{e}"
            )
            
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
                preview.exec()
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

© 2026 BTC Engine Project
"""
        QMessageBox.about(self, "About", about_text)


def main():
    """Entry point"""
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = StrategyBuilderMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
