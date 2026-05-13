"""
Strategy Builder - Code Preview Dialog

Displays generated code with syntax highlighting.

Author: Strategy Builder v3.0
Date: 2026-01-10
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtCore import Qt, QRegularExpression
import re


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code"""
    
    def __init__(self, document):
        super().__init__(document)
        
        # Define formats
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#569cd6"))  # Blue
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#ce9178"))  # Orange
        
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6a9955"))  # Green
        
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("#dcdcaa"))  # Yellow
        
        self.class_format = QTextCharFormat()
        self.class_format.setForeground(QColor("#4ec9b0"))  # Cyan
        
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#b5cea8"))  # Light green
        
        # Define patterns
        self.highlighting_rules = []
        
        # Keywords
        keywords = [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'try', 'while', 'with', 'yield', 'self'
        ]
        
        for word in keywords:
            pattern = QRegularExpression(f"\\b{word}\\b")
            self.highlighting_rules.append((pattern, self.keyword_format))
        
        # Functions
        pattern = QRegularExpression(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\()')
        self.highlighting_rules.append((pattern, self.function_format))
        
        # Classes
        pattern = QRegularExpression(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)')
        self.highlighting_rules.append((pattern, self.class_format))
        
        # Numbers
        pattern = QRegularExpression(r'\b[0-9]+\.?[0-9]*\b')
        self.highlighting_rules.append((pattern, self.number_format))
        
        # Strings
        pattern = QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"')
        self.highlighting_rules.append((pattern, self.string_format))
        
        pattern = QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'")
        self.highlighting_rules.append((pattern, self.string_format))
        
        # Comments
        self.comment_pattern = QRegularExpression(r'#[^\n]*')
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text"""
        # Apply all rules
        for pattern, format in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)
        
        # Comments (last so they override)
        iterator = self.comment_pattern.globalMatch(text)
        while iterator.hasNext():
            match = iterator.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), self.comment_format)


class CodePreviewDialog(QDialog):
    """Dialog to preview generated strategy code"""
    
    def __init__(self, files_dict, parent=None):
        """
        Initialize code preview dialog
        
        Args:
            files_dict: Dict with keys 'strategy', 'test', 'optimizer'
            parent: Parent widget
        """
        # Make window independent for multi-monitor support
        super().__init__(parent, Qt.WindowType.Window)
        self.setModal(False)
        
        self.files_dict = files_dict
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Code Preview")
        self.setGeometry(200, 200, 1200, 800)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📄 Generated Code Preview")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)
        
        # Tab widget for different files
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Add tabs for each file
        self.create_code_tab("Strategy", self.files_dict.get('strategy', ''), 'python')
        self.create_code_tab("Test", self.files_dict.get('test', ''), 'python')
        self.create_code_tab("Optimizer Config", self.files_dict.get('optimizer', ''), 'yaml')
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy Current Tab")
        copy_btn.clicked.connect(self.copy_current_tab)
        button_layout.addWidget(copy_btn)
        
        copy_all_btn = QPushButton("📋 Copy All")
        copy_all_btn.clicked.connect(self.copy_all)
        button_layout.addWidget(copy_all_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("✖ Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Info label
        info_label = QLabel(
            f"Strategy: {self.files_dict.get('strategy', 'N/A')}\n"
            f"Test: {self.files_dict.get('test', 'N/A')}\n"
            f"Config: {self.files_dict.get('optimizer', 'N/A')}"
        )
        info_label.setStyleSheet("font-size: 9pt; color: #888;")
        layout.addWidget(info_label)
        
    def create_code_tab(self, title, file_path, language='python'):
        """
        Create a tab with code editor
        
        Args:
            title: Tab title
            file_path: Path to file (or empty if not generated)
            language: Language for syntax highlighting
        """
        if not file_path:
            editor = QTextEdit()
            editor.setPlainText("(Not generated)")
            editor.setReadOnly(True)
            self.tabs.addTab(editor, title)
            return
        
        try:
            # Read file content
            from pathlib import Path
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            code = f"Error reading file: {e}"
        
        # Create editor
        editor = QTextEdit()
        editor.setPlainText(code)
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", 10))
        
        # Apply syntax highlighting for Python
        if language == 'python':
            highlighter = PythonHighlighter(editor.document())
        
        self.tabs.addTab(editor, title)
    
    def copy_current_tab(self):
        """Copy current tab content to clipboard"""
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, QTextEdit):
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(current_widget.toPlainText())
            QMessageBox.information(self, "Copied", "Code copied to clipboard!")
    
    def copy_all(self):
        """Copy all tabs content to clipboard"""
        from PyQt6.QtWidgets import QApplication
        
        all_code = []
        for i in range(self.tabs.count()):
            tab_name = self.tabs.tabText(i)
            widget = self.tabs.widget(i)
            if isinstance(widget, QTextEdit):
                code = widget.toPlainText()
                all_code.append(f"# ===== {tab_name} =====\n{code}\n")
        
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(all_code))
        QMessageBox.information(self, "Copied", "All code copied to clipboard!")
