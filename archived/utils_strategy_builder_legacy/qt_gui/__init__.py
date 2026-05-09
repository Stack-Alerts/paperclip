"""
Strategy Builder - PyQt6 Professional UI

Professional-grade graphical interface using PyQt6.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

__version__ = "3.0.0"
__all__ = ['StrategyBuilderMainWindow']

# Import main window
try:
    from src.utils.Strategy_Builder.qt_gui.main_window import StrategyBuilderMainWindow
except ImportError:
    # Allow importing even if main_window not created yet
    StrategyBuilderMainWindow = None