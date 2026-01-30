"""
Validation Report Window - Institutional-Grade Professional UI
Sprint 1.9 - Complete Redesign to Match Strategy Browser

Professional table-based validation report with:
- Table layout matching Strategy Browser style
- Blue section headers matching system theme
- Institutional-grade content and explanations
- Clear, actionable guidance for users
- One-click fix buttons integrated

Author: BTC_Engine_v3
Date: 2026-01-30 (Redesigned)
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QTabWidget, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import csv

from src.optimizer_v3.validation.institutional_validator import (
    InstitutionalValidator,
    ValidationReport,
    ValidationSeverity
)
from src.strategy_builder.ui.styles import (
    COLORS, create_font, get_main_stylesheet,
    get_table_stylesheet, get_tab_widget_stylesheet
)


class ValidationReportWindow(QDialog):
    """
    Professional validation report window matching Strategy Browser style
    
    Features:
    - Table-based issue display
    - Tab-based organization (Summary, Issues, Metrics)
    - Blue headers matching system theme
    - Institutional-grade explanations
    - Integrated fix buttons
    """
    
    # Signals
    fix_applied = pyqtSignal(str, dict)  # fix_type, fix_data
    
    def __init__(self, report: ValidationReport, config: any, parent: Optional[QWidget] = None):
        """Initialize professional validation window"""
        super().__init__(parent)
        self.report = report
        self.config = config
        
        self._init_ui()
        self._restore_geometry()
        self._populate_data()
    
    def _init_ui(self):
        """Initialize UI with professional styling"""
        self.setWindowTitle("BTC Engine v3 - Institutional Validation Report")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # Make window independent and movable to other screens
        self.setModal(False)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        # Apply main stylesheet
        self.setStyleSheet(get_main_stylesheet())
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header with blue title (matching Strategy Browser)
        header = self._create_header()
        layout.addWidget(header)
        
        # Status banner
        status_banner = self._create_status_banner()
        layout.addWidget(status_banner)
        
        # Tab widget for organized content
        tabs = self._create_tabs()
        layout.addWidget(tabs, 1)
        
        # Footer with actions
        footer = self._create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Create header with blue title matching Strategy Browser"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Blue title matching Strategy Browser style
        title = QLabel("💼 Institutional Validation Report")
        title.setFont(create_font(18, bold=True))
        title.setStyleSheet(f"color: {COLORS['info']}; background: transparent;")
        layout.addWidget(title)
        
        # Strategy info
        strategy_name = self.report.strategy_summary.get('name', 'Unknown')
        timestamp = datetime.fromisoformat(self.report.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        info_text = f"Strategy: {strategy_name}  •  Validated: {timestamp}"
        info_label = QLabel(info_text)
        info_label.setFont(create_font(11))
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
        layout.addWidget(info_label)
        
        return widget
    
    def _create_status_banner(self) -> QWidget:
        """Create status banner showing pass/fail"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        if self.report.is_valid:
            # PASSED
            icon = QLabel("✅")
            icon.setFont(create_font(24))
            title = QLabel("VALIDATION PASSED")
            title.setFont(create_font(14, bold=True))
            title.setStyleSheet(f"color: {COLORS['success']};")
            
            desc = QLabel("Your strategy meets all institutional-grade requirements and is ready for backtesting.")
            desc.setFont(create_font(11))
            desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
            desc.setWordWrap(True)
            
            widget.setStyleSheet(f"""
                QWidget {{
                    background-color: rgba(16, 185, 129, 0.1);
                    border-left: 4px solid {COLORS['success']};
                    border-radius: 4px;
                }}
            """)
        else:
            # FAILED
            icon = QLabel("❌")
            icon.setFont(create_font(24))
            title = QLabel(f"VALIDATION FAILED")
            title.setFont(create_font(14, bold=True))
            title.setStyleSheet(f"color: {COLORS['error']};")
            
            blocking = self.report.blocking_issues()
            desc = QLabel(
                f"{blocking} blocking issue(s) must be fixed before backtest. "
                "Review the Issues tab below for detailed guidance on resolving each issue."
            )
            desc.setFont(create_font(11))
            desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
            desc.setWordWrap(True)
            
            widget.setStyleSheet(f"""
                QWidget {{
                    background-color: rgba(220, 53, 69, 0.1);
                    border-left: 4px solid {COLORS['error']};
                    border-radius: 4px;
                }}
            """)
        
        layout.addWidget(icon)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.addWidget(title)
        text_layout.addWidget(desc)
        layout.addLayout(text_layout, 1)
        
        return widget
    
    def _create_tabs(self) -> QTabWidget:
        """Create tab widget with Summary, Issues, Metrics"""
        tabs = QTabWidget()
        tabs.setStyleSheet(get_tab_widget_stylesheet())
        
        # Tab 1: Summary
        summary_tab = self._create_summary_tab()
        tabs.addTab(summary_tab, "📊 Summary")
        
        # Tab 2: Issues (main tab - most important)
        issues_tab = self._create_issues_tab()
        tabs.addTab(issues_tab, "⚠️ Issues")
        
        # Tab 3: Metrics & Analysis
        metrics_tab = self._create_metrics_tab()
        tabs.addTab(metrics_tab, "📈 Metrics & Analysis")
        
        # Set Issues tab as default  if there are issues
        if not self.report.is_valid:
            tabs.setCurrentIndex(1)
        
        return tabs
    
    def _create_summary_tab(self) -> QWidget:
        """Create summary overview tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Issue count summary
        summary_group = QGroupBox("Validation Summary")
        summary_group.setFont(create_font(12, bold=True))
        summary_layout = QVBoxLayout()
        
        counts = [
            ("Critical Issues", len(self.report.critical_issues), COLORS['error']),
            ("Errors", len(self.report.errors), COLORS['warning']),
            ("Warnings", len(self.report.warnings), "#FFD700"),
            ("Notices", len(self.report.notices), COLORS['info']),
            ("Info", len(self.report.info), COLORS['text_secondary'])
        ]
        
        for label, count, color in counts:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            
            label_widget = QLabel(f"{label}:")
            label_widget.setFont(create_font(11))
            label_widget.setMinimumWidth(150)
            row_layout.addWidget(label_widget)
            
            count_widget = QLabel(str(count))
            count_widget.setFont(create_font(11, bold=True))
            count_widget.setStyleSheet(f"color: {color};")
            row_layout.addWidget(count_widget)
            
            row_layout.addStretch()
            summary_layout.addWidget(row)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Strategy Composition
        composition_group = QGroupBox("Strategy Composition")
        composition_group.setFont(create_font(12, bold=True))
        composition_layout = QVBoxLayout()
        
        # Extract composition data from config
        composition_data = self._get_strategy_composition()
        
        composition_items = [
            ("Building Blocks", composition_data['blocks'], COLORS['info']),
            ("Total Signals", composition_data['signals'], COLORS['info']),
            ("RECHECK Conditions", composition_data['rechecks'], COLORS['text_secondary']),
            ("Exit Conditions", composition_data['exits'], COLORS['success']),
            ("Entry Signals", composition_data['entry_signals'], COLORS['info']),
        ]
        
        for label, count, color in composition_items:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            
            label_widget = QLabel(f"{label}:")
            label_widget.setFont(create_font(11))
            label_widget.setMinimumWidth(150)
            row_layout.addWidget(label_widget)
            
            count_widget = QLabel(str(count))
            count_widget.setFont(create_font(11, bold=True))
            count_widget.setStyleSheet(f"color: {color};")
            row_layout.addWidget(count_widget)
            
            row_layout.addStretch()
            composition_layout.addWidget(row)
        
        composition_group.setLayout(composition_layout)
        layout.addWidget(composition_group)
        
        # Complexity summary
        complexity = self.report.complexity_metrics.get('complexity_score', 0)
        complexity_group = QGroupBox("Strategy Complexity")
        complexity_layout = QVBoxLayout()
        
        complexity_label = QLabel(f"Complexity Score: {complexity}/100")
        complexity_label.setFont(create_font(12, bold=True))
        
        if complexity < 30:
            rating = "Simple - Excellent for reliability"
            color = COLORS['success']
        elif complexity < 60:
            rating = "Moderate - Good balance"
            color = COLORS['info']
        else:
            rating = "Complex - Review for optimization opportunities"
            color = COLORS['warning']
        
        rating_label = QLabel(rating)
        rating_label.setFont(create_font(11))
        rating_label.setStyleSheet(f"color: {color};")
        
        complexity_layout.addWidget(complexity_label)
        complexity_layout.addWidget(rating_label)
        complexity_group.setLayout(complexity_layout)
        layout.addWidget(complexity_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_issues_tab(self) -> QWidget:
        """Create issues table tab (main content)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create table
        table = QTableWidget()
        table.setStyleSheet(get_table_stylesheet())
        
        # Set columns
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Severity", "Category", "Issue", "Location", "Description & Guidance", "Action"
        ])
        
        # Collect all issues
        all_issues = []
        for issue in self.report.critical_issues:
            all_issues.append(('CRITICAL', issue))
        for issue in self.report.errors:
            all_issues.append(('ERROR', issue))
        for issue in self.report.warnings:
            all_issues.append(('WARNING', issue))
        for issue in self.report.notices:
            all_issues.append(('NOTICE', issue))
        for issue in self.report.info:
            all_issues.append(('INFO', issue))
        
        table.setRowCount(len(all_issues))
        
        # Populate rows
        for row, (severity, issue) in enumerate(all_issues):
            # Column 0: Severity
            severity_item = QTableWidgetItem(severity)
            severity_item.setFont(create_font(10, bold=True))
            severity_color = {
                'CRITICAL': COLORS['error'],
                'ERROR': COLORS['warning'],
                'WARNING': '#FFD700',
                'NOTICE': COLORS['info'],
                'INFO': COLORS['text_secondary']
            }[severity]
            severity_item.setForeground(QColor(severity_color))
            table.setItem(row, 0, severity_item)
            
            # Column 1: Category
            category_item = QTableWidgetItem(issue.category)
            category_item.setFont(create_font(10))
            table.setItem(row, 1, category_item)
            
            # Column 2: Issue
            issue_item = QTableWidgetItem(issue.rule_name)
            issue_item.setFont(create_font(10, bold=True))
            table.setItem(row, 2, issue_item)
            
            # Column 3: Location (formatted hierarchically)
            formatted_location = self._format_location(issue.location)
            location_item = QTableWidgetItem(formatted_location)
            location_item.setFont(create_font(10))
            table.setItem(row, 3, location_item)
            
            # Column 4: Description & Guidance (institutional-grade)
            desc_text = self._get_institutional_description(issue)
            # Add 1 line padding at the end
            desc_text += "\n"
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setFont(create_font(10))
            desc_item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            # Enable word wrap for long descriptions
            desc_item.setFlags(desc_item.flags() | Qt.ItemIsEditable)
            table.setItem(row, 4, desc_item)
            
            # Column 5: Action
            action_text = "✓ Passed" if severity == 'INFO' else self._get_action_text(issue)
            action_item = QTableWidgetItem(action_text)
            action_item.setFont(create_font(10))
            if severity in ['CRITICAL', 'ERROR']:
                action_item.setForeground(QColor(COLORS['error']))
            table.setItem(row, 5, action_item)
        
        # Configure table
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        # Enable word wrapping for all cells
        table.setWordWrap(True)
        table.setTextElideMode(Qt.ElideNone)
        
        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Severity
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Issue - fit to text
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Location - fit to text
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Description (takes remaining space)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Action
        
        # CRITICAL FIX: Set vertical header to resize to contents automatically
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(table)
        
        # Store table reference for later use
        self.issues_table = table
        
        return widget
    
    def _create_metrics_tab(self) -> QWidget:
        """Create metrics and analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16,  16, 16, 16)
        
        # Exit strategy analysis
        exit_group = QGroupBox("Exit Strategy Analysis")
        exit_layout = QVBoxLayout()
        
        exit_info = self._get_exit_strategy_info()
        exit_text = QTextEdit()
        exit_text.setReadOnly(True)
        exit_text.setMaximumHeight(150)
        exit_text.setPlainText(exit_info)
        exit_text.setFont(create_font(10))
        
        exit_layout.addWidget(exit_text)
        exit_group.setLayout(exit_layout)
        layout.addWidget(exit_group)
        
        # Timing analysis
        if self.report.timing_conflicts:
            timing_group = QGroupBox("Timing Conflict Analysis")
            timing_layout = QVBoxLayout()
            
            timing_text = QTextEdit()
            timing_text.setReadOnly(True)
            timing_text.setMaximumHeight(200)
            timing_text.setFont(create_font(10))
            
            conflicts_info = self._get_timing_conflicts_info()
            timing_text.setPlainText(conflicts_info)
            
            timing_layout.addWidget(timing_text)
            timing_group.setLayout(timing_layout)
            layout.addWidget(timing_group)
        
        # Direction analysis
        direction_group = QGroupBox("Signal Direction Analysis")
        direction_layout = QVBoxLayout()
        
        direction_info = self._get_direction_info()
        direction_text = QTextEdit()
        direction_text.setReadOnly(True)
        direction_text.setMaximumHeight(120)
        direction_text.setPlainText(direction_info)
        direction_text.setFont(create_font(10))
        
        direction_layout.addWidget(direction_text)
        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_footer(self) -> QWidget:
        """Create footer with action buttons"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Export CSV button
        export_btn = QPushButton("📄 Export Report to CSV")
        export_btn.setFont(create_font(11))
        export_btn.clicked.connect(self._export_csv)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFont(create_font(11))
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        return widget
    
    def _get_institutional_description(self, issue: any) -> str:
        """
        Get institutional-grade description with clear explanation and guidance
        
        This provides professional, institutional-grade content that helps users
        understand the issue and know exactly how to fix it.
        """
        # Base description
        desc = issue.message
        
        # Add suggestion if available
        if issue.suggestion:
            desc += f"\n\n💡 How to Fix: {issue.suggestion}"
        
        # Add institutional context for common issues
        if issue.rule_id == "TIMING_004":
            desc += "\n\n⚠️ Why This Matters: When RECHECK delays exceed timing windows, signals will never trigger because the recheck validation occurs after the window has already closed. This makes the signal functionally dead code."
        elif issue.rule_id == "DIRECTION_001":
            desc += "\n\n⚠️ Why This Matters: Trading in the wrong direction (e.g., bearish signals in a bullish strategy) will cause losses. Institutional traders never mix signal directions."
        elif issue.rule_id == "RECHECK_001":
            desc += "\n\n⚠️ Why This Matters: Circular RECHECK dependencies create infinite loops that prevent strategy execution. This is a critical structural error."
        elif issue.category == "EXIT_STRATEGY":
            desc += "\n\n📊 Note: Exit strategy analysis is informational. Multiple exit opportunities increase probability of profit-taking without blocking validation."
        
        return desc
    
    def _format_location(self, location: str) -> str:
        """
        Format location string hierarchically
        
        Input: "Block::hod::Signal::BELOW_HOD"
        Output: "Block: Hod\n└── Signal: BELOW_HOD"
        
        Capitalizes block names for better readability
        """
        if not location or '::' not in location:
            return location
        
        parts = location.split('::')
        formatted_lines = []
        
        # Process pairs (label::value)
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                label = parts[i]
                value = parts[i + 1]
                
                # Capitalize block names only (not signal names)
                if label == "Block":
                    value = value.capitalize()
                
                # Add tree structure indent for nested items
                if i == 0:
                    formatted_lines.append(f"{label}: {value}")
                else:
                    formatted_lines.append(f"└── {label}: {value}")
        
        return '\n'.join(formatted_lines)
    
    def _get_strategy_composition(self) -> dict:
        """
        Extract strategy composition data from config
        
        Returns counts for:
        - Building blocks
        - Total signals
        - RECHECK conditions
        - Exit conditions
        - Entry signals
        """
        blocks_count = 0
        signals_count = 0
        rechecks_count = 0
        exits_count = 0
        entry_signals_count = 0
        
        if hasattr(self.config, 'blocks') and self.config.blocks:
            blocks_count = len(self.config.blocks)
            
            for block in self.config.blocks:
                if hasattr(block, 'signals') and block.signals:
                    signals_count += len(block.signals)
                    
                    for signal in block.signals:
                        # Count RECHECKs
                        if hasattr(signal, 'recheck_conditions') and signal.recheck_conditions:
                            rechecks_count += len(signal.recheck_conditions)
                        
                        # Count entry signals (signals without exit flag or exit_for empty)
                        is_exit = False
                        if hasattr(signal, 'is_exit_signal'):
                            is_exit = signal.is_exit_signal
                        elif hasattr(signal, 'exit_for') and signal.exit_for:
                            is_exit = True
                        
                        if not is_exit:
                            entry_signals_count += 1
        
        # Count exit conditions
        if hasattr(self.config, 'exit_conditions') and self.config.exit_conditions:
            exits_count = len(self.config.exit_conditions)
        
        return {
            'blocks': blocks_count,
            'signals': signals_count,
            'rechecks': rechecks_count,
            'exits': exits_count,
            'entry_signals': entry_signals_count
        }
    
    def _get_action_text(self, issue: any) -> str:
        """Get action text for issue"""
        if issue.auto_fix_available:
            return "🔧 Fix Available"
        elif issue.severity.name in ['CRITICAL', 'ERROR']:
            return "⚠️ Must Fix"
        elif issue.severity.name == 'WARNING':
            return "⚡ Should Review"
        else:
            return "ℹ️ Review"
    
    def _get_exit_strategy_info(self) -> str:
        """Get exit strategy analysis text"""
        # Find exit analysis in info issues
        for issue in self.report.info:
            if issue.category == "EXIT_STRATEGY":
                return f"{issue.rule_name}\n\n{issue.message}\n\n{issue.suggestion or ''}"
        
        return "No exit strategy analysis available."
    
    def _get_timing_conflicts_info(self) -> str:
        """Get timing conflicts detailed info"""
        if not self.report.timing_conflicts:
            return "No timing conflicts detected."
        
        info = "TIMING CONFLICT DETAILS:\n\n"
        
        for conflict in self.report.timing_conflicts:
            info += f"Signal: {conflict.get('signal', 'Unknown')}\n"
            info += f"Timing Window: {conflict.get('timing_window', 'N/A')} bars\n"
            info += f"RECHECK Delay: {conflict.get('recheck_delay', 'N/A')} bars\n"
            info += f"Status: {conflict.get('status', 'Unknown')}\n"
            info += "\n"
        
        return info
    
    def _get_direction_info(self) -> str:
        """Get signal direction breakdown"""
        summary = self.report.strategy_summary
        
        bullish_count = summary.get('bullish_signal_count', 0)
        bearish_count = summary.get('bearish_signal_count', 0)
        strategy_type = summary.get('strategy_type', 'Unknown')
        
        total = bullish_count + bearish_count
        if total == 0:
            return "No signals detected in strategy."
        
        bullish_pct = (bullish_count / total) * 100
        bearish_pct = (bearish_count / total) * 100
        
        info = f"Strategy Type: {strategy_type}\n\n"
        info += f"Signal Breakdown:\n"
        info += f"  • Bullish Signals: {bullish_count} ({bullish_pct:.1f}%)\n"
        info += f"  • Bearish Signals: {bearish_count} ({bearish_pct:.1f}%)\n\n"
        
        if bullish_pct > 70 and strategy_type != "Bullish":
            info += "⚠️ Mismatch: Strategy has majority bullish signals but is not marked as Bullish.\n"
        elif bearish_pct > 70 and strategy_type != "Bearish":
            info += "⚠️ Mismatch: Strategy has majority bearish signals but is not marked as Bearish.\n"
        else:
            info += "✓ Signal direction matches strategy type."
        
        return info
    
    def _export_csv(self):
        """Export validation report to CSV"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Validation Report",
            f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Header
                    writer.writerow(['BTC Engine v3 - Institutional Validation Report'])
                    writer.writerow([])
                    writer.writerow(['Strategy:', self.report.strategy_summary.get('name', 'Unknown')])
                    writer.writerow(['Validated:', datetime.fromisoformat(self.report.timestamp).strftime('%Y-%m-%d %H:%M:%S')])
                    writer.writerow(['Status:', 'PASSED' if self.report.is_valid else 'FAILED'])
                    writer.writerow([])
                    
                    # Issues table
                    writer.writerow(['Severity', 'Category', 'Rule ID', 'Issue', 'Location', 'Description', 'Suggestion'])
                    
                    all_issues = (
                        self.report.critical_issues +
                        self.report.errors +
                        self.report.warnings +
                        self.report.notices +
                        self.report.info
                    )
                    
                    for issue in all_issues:
                        writer.writerow([
                            issue.severity.name,
                            issue.category,
                            issue.rule_id,
                            issue.rule_name,
                            issue.location,
                            issue.message,
                            issue.suggestion or ''
                        ])
                
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Validation report exported successfully!\n\nFile: {filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Error",
                    f"Failed to export report:\n\n{str(e)}"
                )
    
    def _populate_data(self):
        """Populate window with report data (called after UI init)"""
        # Data populated via _create_tabs and table population
        pass
    
    def _restore_geometry(self):
        """Restore window geometry from settings"""
        settings = QSettings("BTC_Engine", "ValidationReport")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """Save window geometry on close"""
        settings = QSettings("BTC_Engine", "ValidationReport")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
