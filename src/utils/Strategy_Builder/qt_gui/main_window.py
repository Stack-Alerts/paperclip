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
        
        toolbar.addSeparator()
        
        # Validate button
        validate_btn = QAction('✓ Validate', self)
        validate_btn.triggered.connect(self.validate_strategy)
        toolbar.addAction(validate_btn)
        
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
        
        self.strategy_list = QListWidget()
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
        """Load strategies from registry"""
        self.strategy_list.clear()
        strategies = self.registry.list_strategies()
        
        for strategy in sorted(strategies, key=lambda s: s.number):
            item_text = f"{strategy.number:03d}. {strategy.name} ({strategy.category})"
            self.strategy_list.addItem(item_text)
        
        total = len(strategies)
        self.status_bar.showMessage(f"Ready | {total}/150 Strategy Slots")
        
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
            next_num = self.registry.get_next_strategy_number()
            QMessageBox.information(
                self,
                "New Strategy",
                f"Creating strategy #{next_num:03d}\n\n"
                "Full editor coming soon!\n"
                "For now, use CLI or programmatic API."
            )
        except ValueError:
            QMessageBox.critical(
                self,
                "Error",
                "All 150 strategy slots are filled!"
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
                QMessageBox.information(
                    self,
                    "Success",
                    f"✅ Files generated!\n\n"
                    f"Strategy: {files['strategy']}\n"
                    f"Test: {files['test']}\n"
                    f"Config: {files['optimizer']}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Generation failed:\n{e}"
            )
            
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
        
    def show_about(self):
        """Show about dialog"""
        about_text = """Strategy Builder v3.0

Professional PyQt6 Interface

Features:
• VSCode dark theme
• Large, readable fonts
• 80 production-ready building blocks
• Automated code generation
• Institutional validation

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