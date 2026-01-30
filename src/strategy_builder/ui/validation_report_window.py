"""
Validation Report Window - Institutional-Grade Validation UI
Sprint 1.9 Tasks 1.9.16-1.9.21

Full-screen validation report window with:
- Severity-based issue display (color-coded)
- Strategy direction mismatch UI with auto-fix
- Timing conflict timeline visualization
- One-click fix suggestions
- Export to PDF/CSV
- Window state persistence

Author: BTC_Engine_v3
Date: 2026-01-30
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel,
    QScrollArea, QWidget, QGroupBox, QTextEdit, QMessageBox,
    QFileDialog
)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
import json
import csv

from src.optimizer_v3.validation.institutional_validator import (
    InstitutionalValidator,
    ValidationReport,
    ValidationSeverity
)
from src.strategy_builder.ui.styles import COLORS, create_font

# Define spacing unit for layout consistency
SPACING_UNIT = 8


class ValidationReportWindow(QDialog):
    """
    Full-screen validation report window
    
    Tasks 1.9.16-1.9.21:
    - Window state persistence (QSettings)
    - Severity-based issue display
    - Direction mismatch UI  
    - Timeline visualization
    - One-click fixes
    - Export to PDF/CSV
    """
    
    # Signals for auto-fix actions
    fix_applied = pyqtSignal(str, dict)  # fix_type, fix_data
    
    def __init__(self, report: ValidationReport, config: any, parent: Optional[QWidget] = None):
        """
        Initialize validation report window
        
        Args:
            report: ValidationReport from InstitutionalValidator
            config: Strategy configuration (for auto-fixes)
            parent: Parent widget
        """
        super().__init__(parent)
        self.report = report
        self.config = config
        
        self._init_ui()
        self._restore_geometry()
        self._populate_report()
    
    def _init_ui(self):
        """Initialize UI (Task 1.9.16)"""
        self.setWindowTitle("BTC Engine v3 - Institutional Validation Report")
        
        # Full window with resize capabilities
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        
        # Larger default size for full-screen experience
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING_UNIT * 2, SPACING_UNIT * 2, 
                                  SPACING_UNIT * 2, SPACING_UNIT * 2)
        layout.setSpacing(SPACING_UNIT * 2)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Scroll area for issues
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {COLORS['bg_secondary']}; }}")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(SPACING_UNIT)
        
        # Add severity sections (Task 1.9.17)
        self._add_severity_sections(content_layout)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)
        
        # Footer with action buttons
        footer = self._create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Create header with summary (Task 1.9.16)"""
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setSpacing(SPACING_UNIT)
        
        # Title
        title = QLabel("Strategy Validation Report")
        title.setFont(create_font(24, bold=True))
        title.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(title)
        
        # Summary stats
        summary = QLabel(self._get_summary_text())
        summary.setFont(create_font(12))
        summary.setWordWrap(True)
        layout.addWidget(summary)
        
        # Overall status
        status = self._get_status_label()
        layout.addWidget(status)
        
        return header
    
    def _add_severity_sections(self, layout: QVBoxLayout):
        """Add collapsible severity sections (Task 1.9.17)"""
        # Critical issues
        if self.report.critical_issues:
            section = self._create_severity_section(
                "CRITICAL Issues",
                self.report.critical_issues,
                "#DC3545",  # Red
                "Critical issues must be fixed before live trading"
            )
            layout.addWidget(section)
        
        # Errors
        if self.report.errors:
            section = self._create_severity_section(
                "ERROR Issues", 
                self.report.errors,
                "#FFA500",  # Orange
                "Errors must be fixed before backtesting"
            )
            layout.addWidget(section)
        
        # Warnings
        if self.report.warnings:
            section = self._create_severity_section(
                "WARNING Issues",
                self.report.warnings,
                "#FFD700",  # Yellow/Gold
                "Warnings should be reviewed"
            )
            layout.addWidget(section)
        
        # Notices
        if self.report.notices:
            section = self._create_severity_section(
                "NOTICE Items",
                self.report.notices,
                "#17A2B8",  # Cyan
                "Notices for your review"
            )
            layout.addWidget(section)
        
        # Info
        if self.report.info:
            section = self._create_severity_section(
                "INFO Items",
                self.report.info,
                "#007ACC",  # Blue
                "Informational messages"
            )
            layout.addWidget(section)
    
    def _create_severity_section(
        self,
        title: str,
        issues: list,
        color: str,
        description: str
    ) -> QGroupBox:
        """Create a severity section with issues"""
        group = QGroupBox(f"{title} ({len(issues)})")
        group.setFont(create_font(14, bold=True))
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {color};
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                background: rgba(255, 255, 255, 0.05);
            }}
            QGroupBox::title {{
                color: {color};
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Section description
        desc_label = QLabel(description)
        desc_label.setFont(create_font(11))
        desc_label.setStyleSheet(f"color: {color};")
        layout.addWidget(desc_label)
        
        # Add each issue
        for issue in issues:
            issue_widget = self._create_issue_widget(issue, color)
            layout.addWidget(issue_widget)
        
        group.setLayout(layout)
        return group
    
    def _create_issue_widget(self, issue: any, color: str) -> QWidget:
        """Create widget for single issue (Tasks 1.9.17-1.9.20)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_UNIT, SPACING_UNIT, SPACING_UNIT, SPACING_UNIT)
        layout.setSpacing(SPACING_UNIT // 2)
        
        # Issue header
        header = QLabel(f"• {issue.rule_name} ({issue.rule_id})")
        header.setFont(create_font(12, bold=True))
        header.setStyleSheet(f"color: {color};")
        layout.addWidget(header)
        
        # Location
        if issue.location != "Strategy":
            loc_label = QLabel(f"Location: {issue.location}")
            loc_label.setFont(create_font(10))
            layout.addWidget(loc_label)
        
        # Message
        msg_label = QLabel(issue.message)
        msg_label.setFont(create_font(11))
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        # Suggestion
        if issue.suggestion:
            sugg_label = QLabel(f"💡 Suggestion: {issue.suggestion}")
            sugg_label.setFont(create_font(10))
            sugg_label.setStyleSheet("color: #28A745;")  # Green
            sugg_label.setWordWrap(True)
            layout.addWidget(sugg_label)
        
        # Task 1.9.18: Strategy direction mismatch UI
        if issue.category == "DIRECTION" and issue.auto_fix_available:
            fix_btn = self._create_direction_fix_button(issue)
            layout.addWidget(fix_btn)
        
        # Task 1.9.19: Timing conflict timeline
        if issue.category == "TIMING" and issue.rule_id == "TIMING_004":
            timeline = self._create_timeline_widget(issue)
            layout.addWidget(timeline)
        
        # Task 1.9.20: Generic one-click fixes
        if issue.auto_fix_available and issue.category != "DIRECTION":
            fix_btn = self._create_generic_fix_button(issue)
            layout.addWidget(fix_btn)
        
        widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(255, 255, 255, 0.03);
                border-left: 3px solid {color};
                border-radius: 3px;
            }}
        """)
        
        return widget
    
    def _create_direction_fix_button(self, issue: any) -> QPushButton:
        """Create direction mismatch fix button (Task 1.9.18)"""
        fix_data = issue.auto_fix_data
        suggested = fix_data['suggested_type']
        
        btn = QPushButton(f"🔄 Switch to {suggested}")
        btn.setFont(create_font(11, bold=True))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #28A745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #218838;
            }}
        """)
        btn.clicked.connect(lambda: self._apply_direction_fix(fix_data))
        return btn
    
    def _create_timeline_widget(self, issue: any) -> QWidget:
        """Create timing conflict timeline (Task 1.9.19)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_UNIT, SPACING_UNIT, SPACING_UNIT, SPACING_UNIT)
        
        label = QLabel("📊 Timeline Visualization:")
        label.setFont(create_font(11, bold=True))
        layout.addWidget(label)
        
        # Find timeline data from report
        timeline_data = None
        for conflict in self.report.timing_conflicts:
            if issue.location in conflict.get('signal', ''):
                timeline_data = conflict.get('timeline', [])
                break
        
        if timeline_data:
            timeline_text = QTextEdit()
            timeline_text.setReadOnly(True)
            timeline_text.setMaximumHeight(150)
            timeline_text.setFont(create_font(10))
            
            text = "Bar-by-bar timeline:\n\n"
            for event in timeline_data:
                status_icon = {
                    'OK':' ✅',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'TOO_LATE': '🚫'
                }.get(event['status'], '•')
                
                text += f"Bar {event['bar']:3d}: {status_icon} {event['description']}\n"
            
            timeline_text.setPlainText(text)
            timeline_text.setStyleSheet("background: rgba(0, 0, 0, 0.3);")
            layout.addWidget(timeline_text)
        
        return widget
    
    def _create_generic_fix_button(self, issue: any) -> QPushButton:
        """Create generic fix button (Task 1.9.20)"""
        fix_type = issue.auto_fix_data.get('fix_type', 'fix')
        
        label_map = {
            'reduce_recheck': '🔧 Reduce RECHECK Delay',
            'consolidate_exits': '🔄 Consolidate Exit Conditions',
            'disable_signal': '⚠️ Disable Dead Signal'
        }
        
        btn = QPushButton(label_map.get(fix_type, '🔧 Apply Fix'))
        btn.setFont(create_font(11))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        btn.clicked.connect(lambda: self._apply_generic_fix(issue))
        return btn
    
    def _create_footer(self) -> QWidget:
        """Create footer with action buttons"""
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setSpacing(SPACING_UNIT)
        
        # Export buttons (Task 1.9.21)
        export_csv_btn = QPushButton("📄 Export CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        layout.addWidget(export_csv_btn)
        
        export_pdf_btn = QPushButton("📑 Export PDF")
        export_pdf_btn.clicked.connect(self._export_pdf)
        layout.addWidget(export_pdf_btn)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFont(create_font(12))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        return footer
    
    def _apply_direction_fix(self, fix_data: dict):
        """Apply direction fix (Task 1.9.18)"""
        suggested = fix_data['suggested_type']
        current = fix_data['current_type']
        
        reply = QMessageBox.question(
            self,
            "Apply Direction Fix",
            f"Switch strategy type from '{current}' to '{suggested}'?\n\n"
            f"This will update the strategy_type field to match your signal selections.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Apply fix to config
            setattr(self.config, 'strategy_type', suggested)
            
            # Update side for consistency
            if suggested == "Bullish":
                self.config.side = "LONG"
            elif suggested == "Bearish":
                self.config.side = "SHORT"
            
            self.fix_applied.emit('switch_direction', fix_data)
            
            QMessageBox.information(
                self,
                "Fix Applied",
                f"Strategy type changed to '{suggested}'.\n\n"
                f"Remember to save your strategy to persist this change."
            )
    
    def _apply_generic_fix(self, issue: any):
        """Apply generic fix (Task 1.9.20)"""
        fix_type = issue.auto_fix_data.get('fix_type')
        
        QMessageBox.information(
            self,
            "Fix Implementation",
            f"Fix type '{fix_type}' will be implemented in future update.\n\n"
            f"For now, please manually address: {issue.suggestion}"
        )
    
    def _export_csv(self):
        """Export report to CSV (Task 1.9.21)"""
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
                    writer.writerow(['Severity', 'Category', 'Rule ID', 'Rule Name', 
                                   'Location', 'Message', 'Suggestion'])
                    
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
                
                QMessageBox.information(self, "Export Complete", 
                                      f"Report exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", 
                                   f"Failed to export: {str(e)}")
    
    def _export_pdf(self):
        """Export report to PDF (Task 1.9.21)"""
        QMessageBox.information(
            self,
            "PDF Export",
            "PDF export will be implemented in a future update.\n\n"
            "For now, use CSV export or print this window."
        )
    
    def _get_summary_text(self) -> str:
        """Get summary text for header"""
        strategy_name = self.report.strategy_summary.get('name', 'Unknown')
        timestamp = datetime.fromisoformat(self.report.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        return (
            f"Strategy: {strategy_name}\n"
            f"Validated: {timestamp}\n"
            f"Total Issues: {self.report.total_issues()} "
            f"(Critical: {len(self.report.critical_issues)}, "
            f"Errors: {len(self.report.errors)}, "
            f"Warnings: {len(self.report.warnings)})\n"
            f"Complexity Score: {self.report.complexity_metrics.get('complexity_score', 0)}/100"
        )
    
    def _get_status_label(self) -> QLabel:
        """Get overall status label"""
        if self.report.is_valid:
            text = "✅ VALIDATION PASSED"
            color = "#28A745"  # Green
        else:
            text = f"❌ VALIDATION FAILED ({self.report.blocking_issues()} blocking issues)"
            color = "#DC3545"  # Red
        
        label = QLabel(text)
        label.setFont(create_font(16, bold=True))
        label.setStyleSheet(f"color: {color}; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 5px;")
        return label
    
    def _populate_report(self):
        """Populate report with data"""
        # Data is populated via _add_severity_sections in _init_ui
        pass
    
    def _restore_geometry(self):
        """Restore window geometry (Task 1.9.16)"""
        settings = QSettings("BTC_Engine", "ValidationReport")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """Save window geometry on close (Task 1.9.16)"""
        settings = QSettings("BTC_Engine", "ValidationReport")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
