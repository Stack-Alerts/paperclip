#!/usr/bin/env python3
"""
Launch Strategy Builder UI Application

This script launches the Strategy Builder main window with all components integrated.

Usage:
    python scripts/launch_strategy_builder.py

Author: Strategy Builder Team
Date: 2026-01-16
"""

import sys
from PyQt5.QtWidgets import QApplication

# Add project root to path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy_builder.ui.strategy_builder_main_window import StrategyBuilderMainWindow


def main():
    """Launch the Strategy Builder application."""
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Strategy Builder")
    app.setOrganizationName("BTC Engine v3")
    app.setApplicationVersion("3.0")
    
    # Create and show main window
    window = StrategyBuilderMainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
