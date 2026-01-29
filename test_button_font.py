"""Test button font rendering to identify root cause"""
import sys
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton, QVBoxLayout
from PyQt5.QtGui import QFont

app = QApplication(sys.argv)
dialog = QDialog()
layout = QVBoxLayout()

# Test 1: Button with NO stylesheet
btn1 = QPushButton("10% (No Style)")
font1 = QFont()
font1.setPointSize(14)
btn1.setFont(font1)
layout.addWidget(btn1)

# Test 2: Button with stylesheet THEN font
btn2 = QPushButton("10% (Style Then Font)")
btn2.setStyleSheet("""
    QPushButton {
        background-color: #244647;
        color: #999999;
        border: none;
        border-radius: 6px;
    }
""")
font2 = QFont()
font2.setPointSize(14)
btn2.setFont(font2)
layout.addWidget(btn2)

# Test 3: Button with stylesheet INCLUDING font
btn3 = QPushButton("10% (Font in Style)")
btn3.setStyleSheet("""
    QPushButton {
        background-color: #244647;
        color: #999999;
        border: none;
        border-radius: 6px;
        font-size: 14pt;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
""")
layout.addWidget(btn3)

# Test 4: Current approach from our code
from src.strategy_builder.ui.styles import create_font
btn4 = QPushButton("10% (Our Approach)")
btn4.setStyleSheet("""
    QPushButton {
        background-color: #244647;
        color: #999999;
        border: none;
        border-radius: 6px;
    }
""")
btn_font = create_font(size=14)
btn4.setFont(btn_font)
layout.addWidget(btn4)

dialog.setLayout(layout)
dialog.setWindowTitle("Font Test - Which Works?")
dialog.show()

sys.exit(app.exec_())
