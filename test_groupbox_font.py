#!/usr/bin/env python3
"""
Test script to verify QGroupBox::title font sizing works.

This will show two identical QGroupBox widgets with the 12pt stylesheet
to verify if the CSS is being applied correctly.
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGroupBox, QLabel
from PyQt5.QtCore import Qt

# Import centralized stylesheet
from src.strategy_builder.ui.styles import get_main_stylesheet


def main():
    """Run test window."""
    app = QApplication(sys.argv)
    
    # Create window
    window = QWidget()
    window.setWindowTitle("QGroupBox Font Size Test")
    window.setGeometry(100, 100, 600, 400)
    
    # Apply the SAME stylesheet as main window
    window.setStyleSheet(get_main_stylesheet())
    
    # Create layout
    layout = QVBoxLayout()
    window.setLayout(layout)
    
    # Test 1: GroupBox with emoji (like Strategy Information)
    group1 = QGroupBox("📋 Strategy Information")
    group1_layout = QVBoxLayout()
    group1_layout.addWidget(QLabel("Content inside group box 1"))
    group1.setLayout(group1_layout)
    layout.addWidget(group1)
    
    # Test 2: GroupBox with emoji (like Available Building Blocks)
    group2 = QGroupBox("📦 Available Building Blocks")
    group2_layout = QVBoxLayout()
    group2_layout.addWidget(QLabel("Content inside group box 2"))
    group2.setLayout(group2_layout)
    layout.addWidget(group2)
    
    # Test 3: GroupBox with emoji (like Strategy Building Blocks)
    group3 = QGroupBox("🧩 Strategy Building Blocks")
    group3_layout = QVBoxLayout()
    group3_layout.addWidget(QLabel("Content inside group box 3"))
    group3.setLayout(group3_layout)
    layout.addWidget(group3)
    
    # Add spacing
    layout.addStretch()
    
    # Show window
    window.show()
    
    print("=" * 70)
    print("GROUPBOX FONT SIZE TEST")
    print("=" * 70)
    print("If the stylesheet works, all three QGroupBox titles should be 12pt.")
    print("Compare the title sizes to verify they match the Backtest dialog.")
    print("=" * 70)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
