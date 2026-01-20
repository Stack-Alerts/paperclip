from PyQt6.QtWidgets import QMainWindow, QMenuBar, QMenu, QAction
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    MENU_STYLE,
    create_font
)
from src.strategy_builder.ui.system_config import SystemConfigWindow

class MainWindow(QMainWindow):
    """Main application window with consistent styling"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Strategy Builder")
        self.setStyleSheet(WINDOW_STYLE)
        self.setup_menu()
        
        # Store child windows
        self.system_config_window = None
    
    def setup_menu(self):
        """Setup main menu bar"""
        menubar = QMenuBar()
        menubar.setStyleSheet(MENU_STYLE)
        menubar.setFont(create_font())
        
        # File menu
        file_menu = QMenu("File", self)
        file_menu.setStyleSheet(MENU_STYLE)
        file_menu.setFont(create_font())
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = QMenu("Tools", self)
        tools_menu.setStyleSheet(MENU_STYLE)
        tools_menu.setFont(create_font())
        
        system_config_action = QAction("System Configuration", self)
        system_config_action.triggered.connect(self.show_system_config)
        tools_menu.addAction(system_config_action)
        
        # Add menus to menubar
        menubar.addMenu(file_menu)
        menubar.addMenu(tools_menu)
        
        self.setMenuBar(menubar)
    
    def show_system_config(self):
        """Show system configuration window"""
        if self.system_config_window is None:
            self.system_config_window = SystemConfigWindow()
        self.system_config_window.show()
        self.system_config_window.activateWindow()
