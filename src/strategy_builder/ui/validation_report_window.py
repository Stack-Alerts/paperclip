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
        self.setWindowTitle("BTC Engine v3 - Validation Report")
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
        """Create header with title matching main window colors"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)  # More padding between title and info
        layout.setContentsMargins(0, 0, 0, 16)  # Extra padding at bottom before status banner
        
        # Title matching Strategy Browser style (#095983 - teal/blue)
        title = QLabel("💼 Validation Report")
        title.setFont(create_font(18, bold=True))
        title.setStyleSheet("color: #095983; font-size: 16pt; font-weight: bold; background: transparent;")
        layout.addWidget(title)
        
        # Strategy info with version
        strategy_name = self.report.strategy_summary.get('name', 'Unknown')
        version = self.report.strategy_summary.get('version', None)
        timestamp = datetime.fromisoformat(self.report.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        # Add version to strategy name if available
        if version:
            info_text = f"Strategy: {strategy_name} (v{version})  •  Validated: {timestamp}"
        else:
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
            # FAILED - Smaller font, muted icon
            icon = QLabel("❌")
            icon.setFont(create_font(14))  # Reduced from 24 to 14
            icon.setStyleSheet(f"color: {COLORS['text_muted']};")  # Muted icon
            title = QLabel(f"VALIDATION FAILED")
            title.setFont(create_font(12, bold=True))  # Reduced from 14 to 12
            title.setStyleSheet(f"color: {COLORS['error']};")
            
            blocking = self.report.blocking_issues()
            desc = QLabel(
                f"{blocking} blocking issue(s) must be fixed before backtest. "
                "Review the Issues tab below for detailed guidance on resolving each issue."
            )
            desc.setFont(create_font(10))  # Reduced from 11 to 10
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
        
        # Summary tab is ALWAYS default (tab index 0)
        # User requested: Summary tab should be default regardless of validation status
        tabs.setCurrentIndex(0)
        
        return tabs
    
    def _create_summary_tab(self) -> QWidget:
        """Create summary overview tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Horizontal layout for Summary and Composition side by side
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        
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
        top_row.addWidget(summary_group)
        
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
        top_row.addWidget(composition_group)
        
        layout.addLayout(top_row)
        
        # Complexity summary - SINGLE ROW with score and rating side by side
        complexity = self.report.complexity_metrics.get('complexity_score', 0)
        complexity_group = QGroupBox("Strategy Complexity")
        complexity_group.setFont(create_font(12, bold=True))  # Match other group boxes
        complexity_layout = QVBoxLayout()
        
        # Single row with both score and rating
        complexity_row = QWidget()
        complexity_row_layout = QHBoxLayout(complexity_row)
        complexity_row_layout.setContentsMargins(0, 4, 0, 4)
        
        complexity_label = QLabel("Complexity Score:")
        complexity_label.setFont(create_font(11))  # Match other labels
        complexity_label.setMinimumWidth(150)
        complexity_row_layout.addWidget(complexity_label)
        
        complexity_value = QLabel(f"{complexity}/100")
        complexity_value.setFont(create_font(11, bold=True))  # Match other values
        
        if complexity < 30:
            rating = "Simple - Excellent for reliability"
            color = COLORS['success']
        elif complexity < 60:
            rating = "Moderate - Good balance"
            color = COLORS['info']
        else:
            rating = "Complex - Review for optimization opportunities"
            color = COLORS['warning']
        
        complexity_value.setStyleSheet(f"color: {color};")
        complexity_row_layout.addWidget(complexity_value)
        
        # Add separator
        separator = QLabel(" • ")
        separator.setFont(create_font(11))
        separator.setStyleSheet(f"color: {COLORS['text_muted']};")
        complexity_row_layout.addWidget(separator)
        
        # Add rating on same row
        rating_label = QLabel(rating)
        rating_label.setFont(create_font(11))
        rating_label.setStyleSheet(f"color: {color};")
        complexity_row_layout.addWidget(rating_label)
        
        complexity_row_layout.addStretch()
        
        complexity_layout.addWidget(complexity_row)
        complexity_group.setLayout(complexity_layout)
        layout.addWidget(complexity_group)
        
        # NEW: Strategy Flow Visualization - Institutional Grade
        # Uses stretch factor of 1 to expand and fill remaining space
        flow_group = self._create_strategy_flow_panel()
        layout.addWidget(flow_group, 1)  # Stretch factor 1 - fills remaining space
        
        # NO addStretch() here - flow panel should expand to fill space
        
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
        """Create metrics and analysis tab - Matching Summary tab style"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Exit strategy analysis
        exit_group = QGroupBox("Exit Strategy Analysis")
        exit_group.setFont(create_font(12, bold=True))  # Match Summary tab group box font
        exit_layout = QVBoxLayout()
        
        exit_info = self._get_exit_strategy_info()
        exit_text = QTextEdit()
        exit_text.setReadOnly(True)
        exit_text.setMinimumHeight(150)  # Changed from maxHeight to minHeight
        # No maxHeight - let it expand to show all content
        exit_text.setPlainText(exit_info)  
        exit_text.setFont(create_font(11))  # Match Summary tab font (was 10)
        
        exit_layout.addWidget(exit_text, 1)  # Stretch factor 1 - can expand
        exit_group.setLayout(exit_layout)
        layout.addWidget(exit_group)
        
        # Timing analysis
        if self.report.timing_conflicts:
            timing_group = QGroupBox("Timing Conflict Analysis")
            timing_group.setFont(create_font(12, bold=True))  # Match Summary tab
            timing_layout = QVBoxLayout()
            
            timing_text = QTextEdit()
            timing_text.setReadOnly(True)
            timing_text.setMinimumHeight(150)  # Changed from maxHeight to minHeight
            # No maxHeight - let it expand to show all content
            timing_text.setFont(create_font(11))  # Match Summary tab font (was 10)
            
            conflicts_info = self._get_timing_conflicts_info()
            timing_text.setPlainText(conflicts_info)
            
            timing_layout.addWidget(timing_text, 1)  # Stretch factor 1 - can expand
            timing_group.setLayout(timing_layout)
            layout.addWidget(timing_group)
        
        # Direction analysis
        direction_group = QGroupBox("Signal Direction Analysis")
        direction_group.setFont(create_font(12, bold=True))  # Match Summary tab
        direction_layout = QVBoxLayout()
        
        direction_info = self._get_direction_info()
        direction_text = QTextEdit()
        direction_text.setReadOnly(True)
        direction_text.setMinimumHeight(120)  # Changed from maxHeight to minHeight
        # No maxHeight - let it expand to show all content
        direction_text.setPlainText(direction_info)
        direction_text.setFont(create_font(11))  # Match Summary tab font (was 10)
        
        direction_layout.addWidget(direction_text, 1)  # Stretch factor 1 - can expand
        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)
        
        # NO addStretch() - let panels expand to fill space
        
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
        
        Uses EXACT same counting logic as main window (strategy_info_panel.py)
        
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
                        # Count RECHECKs - EXACT logic from main window
                        # Check signal.recheck_config.enabled (not recheck_conditions!)
                        if hasattr(signal, 'recheck_config') and signal.recheck_config and signal.recheck_config.enabled:
                            rechecks_count += 1
                        
                        # Count entry signals (signals that are NOT exits)
                        is_exit = False
                        
                        if hasattr(signal, 'is_exit_signal') and signal.is_exit_signal:
                            is_exit = True
                        
                        if hasattr(signal, 'exit_for') and signal.exit_for and len(signal.exit_for) > 0:
                            is_exit = True
                        
                        # Only count as entry if NOT an exit signal
                        if not is_exit:
                            entry_signals_count += 1
        
        # Count exit conditions at ALL levels - EXACT logic from main window
        # Strategy-level exits
        if hasattr(self.config, 'exit_conditions') and self.config.exit_conditions:
            exits_count += len(self.config.exit_conditions)
        
        # Block-level exits
        if hasattr(self.config, 'blocks'):
            for block in self.config.blocks:
                if hasattr(block, 'exit_conditions') and block.exit_conditions:
                    exits_count += len(block.exit_conditions)
                
                # Signal-level exits
                if hasattr(block, 'signals'):
                    for signal in block.signals:
                        if hasattr(signal, 'exit_conditions') and signal.exit_conditions:
                            exits_count += len(signal.exit_conditions)
        
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
        """Get exit strategy analysis - Extract actual data from config"""
        lines = []
        lines.append("EXIT STRATEGY BREAKDOWN")
        lines.append("=" * 60)
        lines.append("")
        
        exit_count = 0
        
        # Strategy-level exits
        if hasattr(self.config, 'exit_conditions') and self.config.exit_conditions:
            lines.append("📍 STRATEGY-LEVEL EXITS:")
            for idx, exit_cond in enumerate(self.config.exit_conditions, 1):
                signal_name = getattr(exit_cond, 'signal_name', 'Unknown')
                percentage = getattr(exit_cond, 'percentage', 0) * 100
                mode = getattr(exit_cond, 'exit_mode', 'ABSOLUTE')
                lines.append(f"   Exit #{idx}: {signal_name} → Close {percentage:.0f}% ({mode})")
                exit_count += 1
            lines.append("")
        
        # Block-level exits
        if hasattr(self.config, 'blocks'):
            for block_idx, block in enumerate(self.config.blocks, 1):
                if hasattr(block, 'exit_conditions') and block.exit_conditions:
                    lines.append(f"📦 BLOCK {block_idx} ({block.name.upper()}) EXITS:")
                    for idx, exit_cond in enumerate(block.exit_conditions, 1):
                        signal_name = getattr(exit_cond, 'signal_name', 'Unknown')
                        percentage = getattr(exit_cond, 'percentage', 0) * 100
                        mode = getattr(exit_cond, 'exit_mode', 'ABSOLUTE')
                        lines.append(f"   Exit #{idx}: {signal_name} → Close {percentage:.0f}% ({mode})")
                        exit_count += 1
                    lines.append("")
                
                # Signal-level exits
                if hasattr(block, 'signals'):
                    for signal in block.signals:
                        if hasattr(signal, 'exit_conditions') and signal.exit_conditions:
                            lines.append(f"🎯 SIGNAL ({signal.name}) EXITS:")
                            for idx, exit_cond in enumerate(signal.exit_conditions, 1):
                                exit_signal_name = getattr(exit_cond, 'signal_name', 'Unknown')
                                percentage = getattr(exit_cond, 'percentage', 0) * 100
                                mode = getattr(exit_cond, 'exit_mode', 'ABSOLUTE')
                                lines.append(f"   Exit #{idx}: {exit_signal_name} → Close {percentage:.0f}% ({mode})")
                                exit_count += 1
                            lines.append("")
        
        if exit_count == 0:
            return "⚠️ WARNING: No exit conditions configured!\n\nThis strategy has no defined exit points. You must add exit conditions to close positions."
        
        lines.append("=" * 60)
        lines.append(f"TOTAL EXIT CONDITIONS: {exit_count}")
        lines.append("")
        lines.append("✓ Multiple exit levels provide flexibility")
        lines.append("✓ Partial exits allow position scaling")
        lines.append("✓ ABSOLUTE mode: Exit at exact percentage")
        lines.append("✓ FLEXIBLE mode: Exit percentage of remaining position")
        
        return "\n".join(lines)
    
    def _get_timing_conflicts_info(self) -> str:
        """Get timing conflicts detailed info with clear explanation"""
        if not self.report.timing_conflicts:
            return "✅ No timing conflicts detected.\n\nAll RECHECK delays are within their timing windows."
        
        lines = []
        lines.append("⚠️ TIMING CONFLICT DETECTED - CRITICAL ISSUE")
        lines.append("=" * 60)
        lines.append("")
        lines.append("WHAT THIS MEANS:")
        lines.append("Your RECHECK delay is longer than the timing window,")
        lines.append("which means the signal will NEVER successfully trigger.")
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        
        for idx, conflict in enumerate(self.report.timing_conflicts, 1):
            signal = conflict.get('signal', 'Unknown')
            timing_window = conflict.get('timing_window', 'N/A')
            recheck_delay = conflict.get('recheck_delay', 'N/A')
            
            lines.append(f"CONFLICT #{idx}:")
            lines.append(f"Signal: {signal}")
            lines.append("")
            lines.append(f"❌ Problem:")
            lines.append(f"   Timing Window: {timing_window} bars")
            lines.append(f"   RECHECK Delay: {recheck_delay} bars")
            lines.append("")
            lines.append(f"   The RECHECK happens at bar {recheck_delay},")
            lines.append(f"   but the timing window expires at bar {timing_window}.")
            lines.append(f"   This signal will NEVER trigger!")
            lines.append("")
            lines.append(f"✅ Solution:")
            lines.append(f"   1. Reduce RECHECK delay to ≤ {timing_window} bars, OR")
            lines.append(f"   2. Increase timing window to ≥ {recheck_delay} bars")
            lines.append("")
            lines.append("=" * 60)
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_direction_info(self) -> str:
        """Get signal direction breakdown - Extract from config"""
        lines = []
        lines.append("SIGNAL DIRECTION BREAKDOWN")
        lines.append("=" * 60)
        lines.append("")
        
        bullish_signals = []
        bearish_signals = []
        neutral_signals = []
        
        # Extract signals from config and determine direction
        if hasattr(self.config, 'blocks'):
            for block in self.config.blocks:
                if hasattr(block, 'signals'):
                    for signal in block.signals:
                        signal_name = signal.name
                        
                        # Determine direction from signal name (common patterns)
                        signal_lower = signal_name.lower()
                        
                        # Bullish indicators
                        if any(word in signal_lower for word in ['bullish', 'bull', 'long', 'buy', 'support', 'bounce', 'breakout_up', 'cross_up']):
                            bullish_signals.append(signal_name)
                        # Bearish indicators
                        elif any(word in signal_lower for word in ['bearish', 'bear', 'short', 'sell', 'resistance', 'rejection', 'breakout_down', 'cross_down']):
                            bearish_signals.append(signal_name)
                        else:
                            neutral_signals.append(signal_name)
        
        bullish_count = len(bullish_signals)
        bearish_count = len(bearish_signals)
        neutral_count = len(neutral_signals)
        total = bullish_count + bearish_count + neutral_count
        
        if total == 0:
            return "⚠️ No signals detected in strategy.\n\nPlease add building blocks with signals."
        
        # Get strategy type from config
        strategy_type = getattr(self.config, 'strategy_type', 'Unknown')
        if not strategy_type or strategy_type == 'Unknown':
            strategy_type = getattr(self.config, 'type', 'Not Specified')
        
        lines.append(f"Strategy Type: {strategy_type}")
        lines.append("")
        
        lines.append(f"Total Signals: {total}")
        lines.append("")
        
        if bullish_count > 0:
            bullish_pct = (bullish_count / total) * 100
            lines.append(f"📈 BULLISH SIGNALS: {bullish_count} ({bullish_pct:.1f}%)")
            for signal in bullish_signals:
                lines.append(f"   • {signal}")
            lines.append("")
        
        if bearish_count > 0:
            bearish_pct = (bearish_count / total) * 100
            lines.append(f"📉 BEARISH SIGNALS: {bearish_count} ({bearish_pct:.1f}%)")
            for signal in bearish_signals:
                lines.append(f"   • {signal}")
            lines.append("")
        
        if neutral_count > 0:
            neutral_pct = (neutral_count / total) * 100
            lines.append(f"⚖️ NEUTRAL/EXIT SIGNALS: {neutral_count} ({neutral_pct:.1f}%)")
            for signal in neutral_signals:
                lines.append(f"   • {signal}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("ANALYSIS:")
        lines.append("")
        
        # Analysis
        if bullish_count > 0 and bearish_count == 0:
            lines.append("✓ Pure bullish strategy - All signals aligned")
        elif bearish_count > 0 and bullish_count == 0:
            lines.append("✓ Pure bearish strategy - All signals aligned")
        elif bullish_count > 0 and bearish_count > 0:
            lines.append("⚠️ Mixed direction signals detected")
            lines.append("   Consider separating into distinct bullish/bearish strategies")
        elif neutral_count == total:
            lines.append("ℹ️ All signals are neutral (exits/conditions)")
        
        return "\n".join(lines)
    
    def _create_strategy_flow_panel(self) -> QGroupBox:
        """
        Create institutional-grade Strategy Flow visualization panel
        
        Presents the strategy execution flow in simple, user-friendly language
        with visual hierarchy showing signal flow, timing, and RECHECKs
        """
        flow_group = QGroupBox("📋 Strategy Execution Flow")
        flow_group.setFont(create_font(12, bold=True))
        flow_layout = QVBoxLayout()
        
        # Create monospace text area for flow visualization
        flow_text_widget = QTextEdit()
        flow_text_widget.setReadOnly(True)
        flow_text_widget.setMinimumHeight(300)  # Minimum height, but can expand
        # No maxHeight - let it fill available space
        flow_text_widget.setFont(QFont("Courier New", 10))  # Monospace for alignment
        flow_text_widget.setStyleSheet(f"color: {COLORS['text_primary']}; background-color: {COLORS['bg_input']};")
        
        # Generate flow visualization with error handling
        try:
            flow_content = self._generate_strategy_flow()
            # Use HTML to support colored text for validation failures
            flow_text_widget.setHtml(f"<pre style='font-family: Courier New; font-size: 10pt; color: {COLORS['text_primary']};'>{flow_content}</pre>")
        except Exception as e:
            # Graceful fallback if flow generation fails
            error_msg = f"Error generating strategy flow: {str(e)}\n\nPlease check your strategy configuration."
            flow_text_widget.setPlainText(error_msg)
            flow_text_widget.setStyleSheet(f"color: {COLORS['error']}; background-color: {COLORS['bg_input']};")
        
        flow_layout.addWidget(flow_text_widget)
        flow_group.setLayout(flow_layout)
        
        return flow_group
    
    def _generate_strategy_flow(self) -> str:
        """
        Generate institutional-grade strategy flow visualization with HTML coloring
        
        Shows:
        - Entry signal flow with timing windows
        - RECHECK validation chains
        - Exit conditions
        - Failed items highlighted in RED
        """
        if not hasattr(self.config, 'blocks') or not self.config.blocks:
            return "No strategy flow available - strategy has no building blocks."
        
        # Collect failed signal names from validation issues
        failed_signals = set()
        failed_blocks = set()
        timing_failed_signals = set()
        
        for issue in (self.report.critical_issues + self.report.errors):
            # Extract signal/block names from location
            if hasattr(issue, 'location') and issue.location:
                parts = issue.location.split('::')
                for i in range(0, len(parts)-1, 2):
                    if i+1 < len(parts):
                        label = parts[i]
                        value = parts[i+1]
                        if label == "Signal":
                            failed_signals.add(value)
                        elif label == "Block":
                            failed_blocks.add(value.lower())
            
            # Mark timing conflicts
            if hasattr(issue, 'rule_id') and issue.rule_id == "TIMING_004":
                if hasattr(issue, 'location') and 'Signal::' in issue.location:
                    parts = issue.location.split('::')
                    for i in range(len(parts)):
                        if parts[i] == "Signal" and i+1 < len(parts):
                            timing_failed_signals.add(parts[i+1])
        
        lines = []
        lines.append("=" * 80)
        lines.append("STRATEGY EXECUTION FLOW - HOW YOUR STRATEGY WORKS")
        lines.append("=" * 80)
        lines.append("")
        
        # Add validation failure notice if strategy failed
        if not self.report.is_valid:
            blocking = self.report.blocking_issues()
            lines.append('<span style="color: #FFA500;">⚠️  VALIDATION FAILED</span>')
            lines.append(f'<span style="color: #FFA500;">⚠️  {blocking} blocking issue(s) detected - items marked in RED below</span>')
            lines.append('<span style="color: #FFA500;">⚠️  See \'Issues\' tab for detailed fix instructions</span>')
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
        
        # Process each block
        for block_idx, block in enumerate(self.config.blocks, 1):
            block_logic = getattr(block, 'logic', 'AND')
            # Clearer explanation for OR logic
            if block_logic == "AND":
                logic_text = "ALL signals required"
            else:
                logic_text = "OPTIONAL - any 1 signal triggers entry"
            
            lines.append(f"📦 BLOCK {block_idx}: {block.name.upper()} ({logic_text})")
            lines.append("")
            
            if not hasattr(block, 'signals') or not block.signals:
                lines.append("   (No signals configured)")
                lines.append("")
                continue
            
            # Process each signal in block
            for sig_idx, signal in enumerate(block.signals, 1):
                # Check if it's an exit signal
                is_exit = False
                if hasattr(signal, 'is_exit_signal') and signal.is_exit_signal:
                    is_exit = True
                elif hasattr(signal, 'exit_for') and signal.exit_for and len(signal.exit_for) > 0:
                    is_exit = True
                
                # Check if signal failed validation
                signal_failed = signal.name in failed_signals or signal.name in timing_failed_signals
                
                if is_exit:
                    signal_line = f"   🚪 EXIT SIGNAL: {signal.name}"
                else:
                    signal_line = f"   🎯 ENTRY SIGNAL: {signal.name}"
                
                # Apply red color if failed
                if signal_failed:
                    lines.append(f'<span style="color: #FF4444;">{signal_line} ⚠️ FAILED VALIDATION</span>')
                else:
                    lines.append(signal_line)
                
                # Check for timing constraints
                if hasattr(signal, 'timing_constraint') and signal.timing_constraint:
                    timing = signal.timing_constraint
                    ref = getattr(timing, 'reference', 'previous signal')
                    window = getattr(timing, 'max_candles', 0)
                    if window > 0:
                        lines.append(f"      └── ⏱️  Timing: Must trigger within {window} candles of '{ref}'")
                
                # Check for RECHECK configurations
                if hasattr(signal, 'recheck_config') and signal.recheck_config:
                    if hasattr(signal.recheck_config, 'enabled') and signal.recheck_config.enabled:
                        delay = getattr(signal.recheck_config, 'bar_delay', 0)
                        parent = getattr(signal.recheck_config, 'parent_signal', None)
                        # FIX: If parent is None, default to signal's own name
                        if not parent:
                            parent = signal.name
                        
                        lines.append(f"      └── 🔄 RECHECK: Validate '{parent}' after {delay} bars")
                        lines.append(f"          ├── If found: Signal VALID ✓")
                        lines.append(f"          └── If not found: Signal RESET ✗")
                        
                        # Check for nested RECHECK chain
                        if hasattr(signal, 'recheck_chain') and signal.recheck_chain:
                            for recheck_idx, recheck in enumerate(signal.recheck_chain, 1):
                                recheck_delay = getattr(recheck, 'bar_delay', 0)
                                recheck_parent = getattr(recheck, 'parent_signal', None)
                                # FIX: If parent is None, default to signal's own name
                                if not recheck_parent:
                                    recheck_parent = signal.name
                                indent = "             " + ("   " * recheck_idx)
                                lines.append(f"{indent}└── 🔄 RECHECK #{recheck_idx+1}: Validate '{recheck_parent}' after {recheck_delay} bars")
                
                # Check for signal-level exit conditions
                if hasattr(signal, 'exit_conditions') and signal.exit_conditions:
                    for exit_idx, exit_cond in enumerate(signal.exit_conditions, 1):
                        exit_signal_name = getattr(exit_cond, 'signal_name', 'Unknown')
                        exit_percentage = getattr(exit_cond, 'percentage', 0) * 100
                        exit_mode = getattr(exit_cond, 'exit_mode', 'ABSOLUTE')
                        lines.append(f"      └── 🚪 EXIT: {exit_signal_name} → Close {exit_percentage:.0f}% ({exit_mode})")
                
                lines.append("")
            
            # Add block-level exit conditions
            if hasattr(block, 'exit_conditions') and block.exit_conditions:
                lines.append("   📍 BLOCK-LEVEL EXITS:")
                for exit_idx, exit_cond in enumerate(block.exit_conditions, 1):
                    exit_signal_name = getattr(exit_cond, 'signal_name', 'Unknown')
                    exit_percentage = getattr(exit_cond, 'percentage', 0) * 100
                    exit_mode = getattr(exit_cond, 'exit_mode', 'ABSOLUTE')
                    lines.append(f"      🚪 EXIT #{exit_idx}: {exit_signal_name} → Close {exit_percentage:.0f}% ({exit_mode})")
                lines.append("")
        
        # Add exit conditions from strategy level
        if hasattr(self.config, 'exit_conditions') and self.config.exit_conditions:
            lines.append("=" * 80)
            lines.append("EXIT CONDITIONS (Strategy-Level)")
            lines.append("=" * 80)
            lines.append("")
            
            for exit_idx, exit_cond in enumerate(self.config.exit_conditions, 1):
                signal_name = getattr(exit_cond, 'signal_name', 'Unknown')
                percentage = getattr(exit_cond, 'percentage', 0) * 100
                mode = getattr(exit_cond, 'exit_mode', 'ABSOLUTE')
                
                lines.append(f"   🚪 EXIT #{exit_idx}: {signal_name} triggers")
                lines.append(f"      └── Action: Close {percentage:.0f}% of position ({mode} mode)")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("EXECUTION: Signals evaluated bar-by-bar in real-time")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
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
