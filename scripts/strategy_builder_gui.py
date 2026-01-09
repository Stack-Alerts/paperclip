#!/usr/bin/env python3
"""
Strategy Builder GUI Launcher

Launch the graphical user interface for strategy creation.

Usage:
    python scripts/strategy_builder_gui.py

Author: Strategy Builder v2.0
Date: 2026-01-09
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.Strategy_Builder.gui.main_window import StrategyBuilderApp


def main():
    """Launch the GUI application"""
    print("🚀 Launching Strategy Builder GUI...")
    print("📍 Location: Strategy Builder v2.0")
    print("📖 Help: Press F1 or Help menu for guide")
    print()
    
    try:
        app = StrategyBuilderApp()
        app.run()
    except Exception as e:
        print(f"\n❌ Error launching GUI: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())