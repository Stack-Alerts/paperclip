#!/usr/bin/env python3
"""
Strategy Builder - PyQt6 Professional UI Launcher

Launch the professional PyQt6 interface.

Usage:
    python scripts/strategy_builder_qt.py

Features:
- VSCode dark theme
- Large, readable fonts (28-40pt)
- Professional UI
- Real-time validation
- Code generation

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from src.utils.Strategy_Builder.qt_gui.main_window import StrategyBuilderMainWindow


def main():
    """Launch the PyQt6 GUI application"""
    print("🚀 Launching Strategy Builder v3.0 (PyQt6)...")
    print("📍 Professional Interface with VSCode Dark Theme")
    print("📖 Help: Menu Bar → Help → About")
    print()
    
    try:
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Strategy Builder")
        app.setOrganizationName("BTC Engine v3")
        
        # Create and show main window
        window = StrategyBuilderMainWindow()
        window.show()
        
        # Run event loop
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"\n❌ Error launching PyQt6 GUI: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())