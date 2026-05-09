"""
Strategy Builder GUI - Graphical User Interface

Tkinter-based GUI for visual strategy creation without coding.

Author: Strategy Builder v2.0
Date: 2026-01-09
"""

from pathlib import Path

__version__ = "2.0.0"
__all__ = ['StrategyBuilderApp']

# Import main application
try:
    from src.utils.Strategy_Builder.gui.main_window import StrategyBuilderApp
except ImportError:
    # Allow importing even if main_window not created yet
    StrategyBuilderApp = None