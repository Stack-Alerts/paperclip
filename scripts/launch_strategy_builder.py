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
import logging
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Root logger: honour LOG_LEVEL env var; default INFO.
_root_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(force=True, 
    level=_root_level,
    format='%(message)s',
    stream=sys.stdout,
)

# WindowGeometry logger: always writes to a dedicated file at DEBUG level so
# multi-monitor restore events are captured regardless of LOG_LEVEL.
_wg_log_dir = Path.home() / ".btc-trade-engine"
_wg_log_dir.mkdir(parents=True, exist_ok=True)
_wg_log_path = _wg_log_dir / "window-geometry.log"
_wg_file_handler = logging.FileHandler(_wg_log_path, encoding="utf-8")
_wg_file_handler.setLevel(logging.DEBUG)
_wg_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s"
))
_wg_logger = logging.getLogger("WindowGeometry")
_wg_logger.setLevel(logging.DEBUG)
_wg_logger.addHandler(_wg_file_handler)
_wg_logger.propagate = True  # still appears on stdout when LOG_LEVEL=DEBUG

from src.strategy_builder.ui.strategy_builder_main_window import StrategyBuilderMainWindow


def main():
    """Launch the Strategy Builder application."""
    # Create Qt application
    app = QApplication(sys.argv)

    # Apply Fusion style + dark QPalette before any window is created.
    # Fusion provides consistent cross-platform rendering independent of the
    # system GTK/Breeze theme — without this, Qt uses the native platform
    # theme (light on most Linux distros) and the dark stylesheet applied to
    # individual windows cannot fully override the application-level palette,
    # causing a full light-mode render on cold start after a server restart.
    app.setStyle('Fusion')
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window,          QColor('#0A0E15'))
    dark_palette.setColor(QPalette.WindowText,      QColor('#E8EAED'))
    dark_palette.setColor(QPalette.Base,            QColor('#151C26'))
    dark_palette.setColor(QPalette.AlternateBase,   QColor('#12171F'))
    dark_palette.setColor(QPalette.ToolTipBase,     QColor('#253241'))
    dark_palette.setColor(QPalette.ToolTipText,     QColor('#E8EAED'))
    dark_palette.setColor(QPalette.Text,            QColor('#E8EAED'))
    dark_palette.setColor(QPalette.Button,          QColor('#2A3139'))
    dark_palette.setColor(QPalette.ButtonText,      QColor('#E8EAED'))
    dark_palette.setColor(QPalette.BrightText,      QColor('#FFFFFF'))
    dark_palette.setColor(QPalette.Link,            QColor('#2070FF'))
    dark_palette.setColor(QPalette.Highlight,       QColor('#2070FF'))
    dark_palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))
    dark_palette.setColor(QPalette.Disabled, QPalette.Text,       QColor('#6B7280'))
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#6B7280'))
    app.setPalette(dark_palette)

    # Set application metadata
    app.setApplicationName("Strategy Builder")
    app.setOrganizationName("BTC Trade Engine")
    app.setApplicationVersion("1.0")

    # Create and show main window
    window = StrategyBuilderMainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
