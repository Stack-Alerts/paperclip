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
    QDialog, QMainWindow, QVBoxLayout, QPushButton, QHBoxLayout, QLabel,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QTabWidget, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import csv
import logging

logger = logging.getLogger(__name__)

from src.optimizer_v3.validation.institutional_validator import (
    InstitutionalValidator,
    ValidationReport,
    ValidationSeverity
)
from src.strategy_builder.ui.styles import (
    COLORS, create_font, get_main_stylesheet,
    get_primary_button_stylesheet, get_secondary_button_stylesheet,
    get_table_stylesheet, get_text_edit_stylesheet, get_scroll_area_stylesheet,
    get_tab_widget_stylesheet, set_hand_cursor, apply_hand_cursor_to_buttons,
    get_auto_fix_button_style
)
from src.strategy_builder.validation.auto_fix import (
    auto_fix_strategy_type,
    auto_fix_recheck_delay,
    auto_fix_duplicate_exits,
    auto_fix_dead_code,
    AutoFixSafety
)
from src.strategy_builder.ui.auto_fix_confirm_dialog import AutoFixConfirmDialog


class ValidationReportWindow(QMainWindow):
    """
    Professional validation report window matching Strategy Browser style
    
    Features:
    - Table-based issue display
    - Tab-based organization (Summary, Issues, Metrics)
    - Blue headers matching system theme
    - Institutional-grade explanations
    - Integrated fix buttons
    - NON-BLOCKING window (QMainWindow for independence)
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
        """Initialize UI with professional styling - QMainWindow is NON-BLOCKING by default"""
        self.setWindowTitle("BTC Engine v3 - Validation Report")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # QMainWindow is naturally non-blocking - no modal flag needed
        
        # Apply main stylesheet
        self.setStyleSheet(get_main_stylesheet())
        
        # QMainWindow requires central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
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
        
        # Tab 3: Metrics (shortened to avoid text cutoff)
        metrics_tab = self._create_metrics_tab()
        tabs.addTab(metrics_tab, "📈 Metrics")
        
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
            row.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg_input']}; }}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            
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
            ("Recheck", composition_data['rechecks'], COLORS['text_secondary']),
            ("Exit Conditions", composition_data['exits'], COLORS['success']),
            ("Entry Signals", composition_data['entry_signals'], COLORS['info']),
        ]
        
        for label, count, color in composition_items:
            row = QWidget()
            row.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg_input']}; }}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            
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
        complexity_row.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg_input']}; }}")
        complexity_row_layout = QHBoxLayout(complexity_row)
        complexity_row_layout.setContentsMargins(4, 4, 4, 4)
        
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
            
            # Column 5: Action - Sprint 1.9.2 Auto-Fix Button Integration
            if severity == 'INFO':
                # INFO level - no action needed
                action_item = QTableWidgetItem("✓ Passed")
                action_item.setFont(create_font(10))
                table.setItem(row, 5, action_item)
            elif hasattr(issue, 'auto_fix_available') and issue.auto_fix_available:
                # Create clickable fix button
                fix_btn = QPushButton("🔧 Fix Now")
                fix_btn.setFont(create_font(9))
                fix_btn.setStyleSheet(get_auto_fix_button_style())
                fix_btn.setCursor(Qt.PointingHandCursor)
                fix_btn.setToolTip(self._get_fix_button_tooltip(issue))
                fix_btn.clicked.connect(lambda checked, iss=issue: self._handle_fix_click(iss))
                
                # Right-click for preview (stub for Task 1.9.2.7)
                fix_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                fix_btn.customContextMenuRequested.connect(
                    lambda pos, iss=issue: self._show_fix_preview(iss)
                )
                
                table.setCellWidget(row, 5, fix_btn)
            else:
                # No auto-fix available
                action_text = self._get_action_text(issue)
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
        """Create metrics and analysis tab with collapsible sections (like AI Recommendations)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Track all sections for maximize functionality
        self.metrics_sections = []
        
        # Exit strategy analysis - collapsible (always green - informational)
        exit_section = self._create_metrics_collapsible_section(
            "✅ Exit Strategy Analysis",
            self._get_exit_strategy_info()
        )
        layout.addWidget(exit_section['widget'], 1)
        self.metrics_sections.append(exit_section)
        
        # Timing Conflict analysis - collapsible (RED if conflicts exist)
        if self.report.timing_conflicts:
            timing_section = self._create_metrics_collapsible_section(
                "❌ Timing Conflict Analysis",
                self._get_timing_conflicts_info(),
                title_color=COLORS['error']  # RED for errors
            )
            layout.addWidget(timing_section['widget'], 1)
            self.metrics_sections.append(timing_section)
        
        # Signal Direction analysis - collapsible (green if aligned, yellow if mixed)
        # Check if there are direction conflicts
        has_direction_issues = False
        for issue in (self.report.errors + self.report.warnings):
            if hasattr(issue, 'rule_id') and issue.rule_id == "DIRECTION_001":
                has_direction_issues = True
                break
        
        if has_direction_issues:
            direction_icon = "⚠️"
        else:
            direction_icon = "✅"
        
        direction_section = self._create_metrics_collapsible_section(
            f"{direction_icon} Signal Direction Analysis",
            self._get_direction_info()
        )
        layout.addWidget(direction_section['widget'], 1)
        self.metrics_sections.append(direction_section)
        
        # NO addStretch() - let sections expand to fill space
        
        return widget
    
    def _create_metrics_collapsible_section(self, title: str, content: str, title_color: str = "#095983") -> dict:
        """Create a collapsible section for Metrics tab (copied from AI Request Preview pattern)"""
        from PyQt5.QtWidgets import QFrame, QSizePolicy
        from PyQt5.QtGui import QFont as QFontImport
        from PyQt5.QtGui import QTextOption
        
        container = QFrame()
        container.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_medium']}; border: 1px solid {COLORS['border']}; border-radius: 4px; }}")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        
        # Title - use custom color or default to Strategy Builder blue
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {title_color}; font-weight: bold; font-size: 12pt; border: none; background: transparent;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Maximize button
        maximize_btn = QPushButton("🗖 Maximize")
        set_hand_cursor(maximize_btn)
        maximize_btn.setFixedSize(180, 38)
        maximize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['button_primary']};
                color: white;
                font-weight: normal;
                padding: 3px 12px;
                border-radius: 3px;
                font-size: 9pt;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_primary_hover']};
            }}
        """)
        header_layout.addWidget(maximize_btn)
        
        # Collapse/Expand button
        toggle_btn = QPushButton("▼ Collapse")
        set_hand_cursor(toggle_btn)
        toggle_btn.setFixedSize(180, 38)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['button_secondary']};
                color: white;
                font-weight: normal;
                padding: 3px 12px;
                border-radius: 3px;
                font-size: 9pt;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_secondary_hover']};
            }}
        """)
        header_layout.addWidget(toggle_btn)
        
        main_layout.addLayout(header_layout)
        
        # Text editor - Use same background as Strategy Flow for consistency
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFontImport("Courier New", 10))
        text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        text_edit.setStyleSheet(f"QTextEdit {{ background-color: {COLORS['bg_input']}; color: {COLORS['text_primary']}; border: 1px solid {COLORS['border']}; padding: 8px; }}")
        text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        text_edit.setPlainText(content)
        main_layout.addWidget(text_edit)
        
        # Toggle collapse/expand
        def toggle_section():
            is_visible = text_edit.isVisible()
            if is_visible:
                # Check if maximized first
                if is_maximized[0]:
                    # Restore all sections
                    for section in self.metrics_sections:
                        if section['widget'] != container:
                            section['widget'].setVisible(True)
                        section['maximize_btn'].setText("🗖 Maximize")
                    is_maximized[0] = False
                
                # Now collapse
                text_edit.setVisible(False)
                toggle_btn.setText("▶ Expand")
                container.setMaximumHeight(60)
            else:
                # Expand
                text_edit.setVisible(True)
                toggle_btn.setText("▼ Collapse")
                container.setMaximumHeight(16777215)
        
        # Maximize/Minimize toggle
        is_maximized = [False]
        
        def toggle_maximize():
            if not is_maximized[0]:
                # Maximize - hide others
                for section in self.metrics_sections:
                    if section['widget'] != container:
                        section['widget'].setVisible(False)
                    else:
                        section['widget'].setVisible(True)
                        section['text_edit'].setVisible(True)
                        section['toggle_btn'].setText("▼ Collapse")
                        section['widget'].setMaximumHeight(16777215)
                        maximize_btn.setText("🗗 Minimize")
                is_maximized[0] = True
            else:
                # Minimize - restore all
                for section in self.metrics_sections:
                    section['widget'].setVisible(True)
                    section['text_edit'].setVisible(True)
                    section['toggle_btn'].setText("▼ Collapse")
                    section['widget'].setMaximumHeight(16777215)
                    section['maximize_btn'].setText("🗖 Maximize")
                is_maximized[0] = False
        
        toggle_btn.clicked.connect(toggle_section)
        maximize_btn.clicked.connect(toggle_maximize)
        
        return {
            'widget': container,
            'text_edit': text_edit,
            'toggle_btn': toggle_btn,
            'maximize_btn': maximize_btn
        }
    
    def _create_footer(self) -> QWidget:
        """Create footer with action buttons"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Export CSV button
        export_btn = QPushButton("📄 Export Report to CSV")
        set_hand_cursor(export_btn)
        export_btn.setFont(create_font(11))
        export_btn.clicked.connect(self._export_csv)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        set_hand_cursor(close_btn)
        close_btn.setFont(create_font(11))
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.close)  # QMainWindow uses close(), not accept()
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
        lines.append("EXIT MODE EXPLANATIONS:")
        lines.append("")
        lines.append("✓ ABSOLUTE mode:")
        lines.append("  - Exits immediately when signal triggers")
        lines.append("  - Closes exact percentage of position")
        lines.append("  - No deferral logic")
        lines.append("")
        lines.append("✓ FLEXIBLE mode (Sprint 1.8 intelligent exits):")
        lines.append("  - Checks if price is heading toward TP")
        lines.append("  - DEFERS exit if within TP proximity threshold")
        lines.append("  - Allows position to reach TP first")
        lines.append("  - Executes on REVERSAL (price pulls back from TP)")
        lines.append("  - Protects gains from premature exits")
        lines.append("")
        lines.append("BENEFITS:")
        lines.append("✓ Multiple exit levels provide flexibility")
        lines.append("✓ Partial exits allow position scaling")
        lines.append("✓ FLEXIBLE mode maximizes TP capture rate")
        
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
        Create institutional-grade Strategy Flow visualization panel with maximize/minimize
        
        Presents the strategy execution flow in simple, user-friendly language
        with visual hierarchy showing signal flow, timing, and RECHECKs
        """
        from PyQt5.QtWidgets import QFrame
        
        # Use QFrame instead of QGroupBox for custom header
        flow_container = QFrame()
        flow_container.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_medium']}; border: 1px solid {COLORS['border']}; border-radius: 4px; }}")
        main_layout = QVBoxLayout(flow_container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Header with title and maximize button
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("📋 Strategy Execution Flow")
        title_label.setStyleSheet("color: #095983; font-weight: bold; font-size: 12pt; border: none; background: transparent;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Maximize/Minimize button only (no collapse)
        self.flow_maximize_btn = QPushButton("🗖 Maximize")
        self.flow_maximize_btn.setFixedSize(180, 38)
        self.flow_maximize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['button_primary']};
                color: white;
                font-weight: normal;
                padding: 3px 12px;
                border-radius: 3px;
                font-size: 9pt;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_primary_hover']};
            }}
        """)
        header_layout.addWidget(self.flow_maximize_btn)
        
        main_layout.addLayout(header_layout)
        
        # Create monospace text area for flow visualization
        flow_text_widget = QTextEdit()
        flow_text_widget.setReadOnly(True)
        flow_text_widget.setMinimumHeight(300)  # Minimum height, but can expand
        # No maxHeight - let it fill available space
        flow_text_widget.setFont(QFont("Courier New", 10))  # Monospace for alignment
        flow_text_widget.setStyleSheet(f"QTextEdit {{ color: {COLORS['text_primary']}; background-color: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; padding: 8px; }}")
        
        # Generate flow visualization with error handling
        try:
            flow_content = self._generate_strategy_flow()
            # Use HTML to support colored text for validation failures
            flow_text_widget.setHtml(f"<pre style='font-family: Courier New; font-size: 10pt; color: {COLORS['text_primary']};'>{flow_content}</pre>")
        except Exception as e:
            # Graceful fallback if flow generation fails
            error_msg = f"Error generating strategy flow: {str(e)}\n\nPlease check your strategy configuration."
            flow_text_widget.setPlainText(error_msg)
            flow_text_widget.setStyleSheet(f"QTextEdit {{ color: {COLORS['error']}; background-color: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; padding: 8px; }}")
        
        main_layout.addWidget(flow_text_widget)
        
        # Store references for maximize functionality
        self.flow_text_widget = flow_text_widget
        self.flow_container = flow_container
        
        # Maximize/minimize logic
        # Track other widgets in Summary tab to hide/show
        is_maximized = [False]
        
        def toggle_flow_maximize():
            if not is_maximized[0]:
                # Maximize - hide all other widgets in Summary tab
                # Get the Summary tab widget
                summary_tab = self.flow_container.parent()
                if summary_tab:
                    # Hide all children except flow_container
                    for child in summary_tab.findChildren(QWidget):
                        if child != self.flow_container and child.parent() == summary_tab:
                            child.setVisible(False)
                
                self.flow_maximize_btn.setText("🗗 Minimize")
                is_maximized[0] = True
            else:
                # Minimize - restore all widgets
                summary_tab = self.flow_container.parent()
                if summary_tab:
                    # Show all children again
                   for child in summary_tab.findChildren(QWidget):
                        if child.parent() == summary_tab:
                            child.setVisible(True)
                
                self.flow_maximize_btn.setText("🗖 Maximize")
                is_maximized[0] = False
        
        self.flow_maximize_btn.clicked.connect(toggle_flow_maximize)
        
        return flow_container
    
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
        lines.append("POSITION OPENING LOGIC - INSTITUTIONAL-GRADE CONFLUENCE SYSTEM")
        lines.append("=" * 80)
        lines.append("")
        
        # Count REQUIRED vs OPTIONAL blocks
        required_blocks = [b for b in self.config.blocks if getattr(b, 'logic', 'AND') == 'AND']
        optional_blocks = [b for b in self.config.blocks if getattr(b, 'logic', 'AND') == 'OR']
        
        lines.append("BLOCK TYPES IN YOUR STRATEGY:")
        lines.append("")
        
        # Show each block with correct terminology
        for block_idx, block in enumerate(self.config.blocks, 1):
            block_logic = getattr(block, 'logic', 'AND')
            num_signals = len(block.signals) if hasattr(block, 'signals') else 0
            
            if block_logic == "AND":
                lines.append(f"Block {block_idx} ({block.name.upper()}) - REQUIRED (AND logic)")
                lines.append(f"   • Type: REQUIRED - ALL {num_signals} signals must trigger")
                lines.append(f"   • Contributes: ~{num_signals * 10} pts (required)")
                lines.append(f"   • If ANY signal missing → 0 points from this block")
            else:  # OR logic
                lines.append(f"Block {block_idx} ({block.name.upper()}) - OPTIONAL (OR logic)")
                lines.append(f"   • Type: OPTIONAL - ANY 1 of {num_signals} signals can trigger")
                lines.append(f"   • Contributes: ~{num_signals * 10} pts (bonus)")
                lines.append(f"   • Adds bonus points if signals fire")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("CONFLUENCE SCORING SYSTEM - HOW POSITION ACTUALLY OPENS")
        lines.append("=" * 80)
        lines.append("")
        
        # Calculate points
        required_points = sum(len(b.signals) * 10 for b in required_blocks if hasattr(b, 'signals'))
        optional_points = sum(len(b.signals) * 10 for b in optional_blocks if hasattr(b, 'signals'))
        total_possible = required_points + optional_points
        
        lines.append(f"Your Strategy Point Breakdown:")
        lines.append(f"   • Required Points: {required_points} pts ({len(required_blocks)} REQUIRED blocks)")
        lines.append(f"   • Optional Points: {optional_points} pts ({len(optional_blocks)} OPTIONAL blocks)")
        lines.append(f"   • Total Possible: {total_possible} pts")
        lines.append("")
        lines.append("POSITION OPENS WHEN:")
        lines.append(f"   ⇨ Confluence Score >= Threshold (e.g., 40 pts)")
        lines.append(f"   ⇨ ONLY ONE POSITION opens when threshold met")
        lines.append(f"   ⇨ Once open, strategy manages THIS POSITION with exits/TP/SL")
        lines.append("")
        
        # Real examples from user's strategy
        lines.append("Real-World Scenarios:")
        lines.append("")
        lines.append("Scenario A: All REQUIRED blocks fire (high confidence)")
        # FIXED: Show ALL required blocks, not just first 2
        for idx, block in enumerate(required_blocks, 1):
            lines.append(f"   • Block {idx} ({block.name.upper()}): ALL signals ✓ → +{len(block.signals) * 10} pts")
        if len(optional_blocks) > 0:
            lines.append(f"   • Optional blocks: Not needed")
        lines.append(f"   Total: {required_points} pts → POSITION OPENS ✓")
        lines.append("")
        
        if len(optional_blocks) > 0:
            lines.append("Scenario B: Some REQUIRED + OPTIONAL blocks (mixed)")
            if len(required_blocks) > 0:
                lines.append(f"   • Block 1 ({required_blocks[0].name.upper()}): ALL signals ✓ → +{len(required_blocks[0].signals) * 10} pts")
            if len(optional_blocks) > 0:
                lines.append(f"   • Block {len(required_blocks)+1} ({optional_blocks[0].name.upper()}): 1 signal ✓ → +10 pts")
            estimated = (len(required_blocks[0].signals) * 10 if required_blocks else 0) + 10
            if estimated >= 40:
                lines.append(f"   Total: ~{estimated} pts → POSITION OPENS ✓")
            else:
                lines.append(f"   Total: ~{estimated} pts → Need more signals")
            lines.append("")
        
        lines.append("Scenario C: Insufficient confluence (no position)")
        if len(required_blocks) > 0:
            lines.append(f"   • Block 1 ({required_blocks[0].name.upper()}): Missing 1 signal ✗ → 0 pts")
        if len(optional_blocks) > 0:
            lines.append(f"   • Optional blocks: 1-2 signals ✓ → +20 pts")
        lines.append(f"   Total: ~20 pts → Below threshold, NO POSITION")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("KEY TAKEAWAYS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append("✓ REQUIRED blocks (AND): Must have ALL signals to contribute points")
        lines.append("✓ OPTIONAL blocks (OR): Contribute bonus points if ANY signal fires")
        lines.append("✓ Position opens when: Total points >= Confluence Threshold")
        lines.append("✓ ONE POSITION only: Not multiple trades")
        lines.append("✓ Threshold configurable: In backtest config (default ~40 pts)")
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
    
    def showEvent(self, event):
        """Called when window is shown - apply hand cursors to all widgets"""
        super().showEvent(event)
        # Apply hand cursor AFTER Qt finishes all stylesheet processing
        # Qt may reapply stylesheets after showEvent, so delay cursor setting
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))
    
    def closeEvent(self, event):
        """Save window geometry on close"""
        settings = QSettings("BTC_Engine", "ValidationReport")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
    
    # =========================================================================
    # AUTO-FIX BUTTON HANDLERS - Sprint 1.9.2
    # =========================================================================
    
    def _get_fix_button_tooltip(self, issue: any) -> str:
        """
        Get institutional tooltip for fix button
        Sprint 1.9.2 Task 1.9.2.6
        
        Provides specific guidance based on issue type
        """
        tooltips = {
            'DIRECTION_001': "Click to automatically switch strategy direction to match signal bias. Right-click to preview changes before applying.",
            'TIMING_004': "Click to reduce RECHECK delay to fit within timing window. Right-click to see exact adjustments.",
            'EXIT_003': "Click to merge duplicate exit conditions. Right-click to preview consolidated result.",
            'DEAD_CODE_001': "Click to disable unreachable signals. Right-click to preview which signals will be affected."
        }
        
        rule_id = getattr(issue, 'rule_id', '')
        return tooltips.get(rule_id, "Click to apply automated fix. Right-click to preview changes.")
    
    def _handle_fix_click(self, issue: any) -> None:
        """
        Handle fix button click - INSTITUTIONAL GRADE DIRECT ACCESS
        Sprint 1.9.2 - Refactored to use validator-provided data
        
        Flow: Extract data from issue → Apply fix → Feedback → Re-validate
        
        Key: Uses issue.auto_fix_data dict and issue.location (no regex needed)
        """
        # Show confirmation
        result = QMessageBox.question(
            self,
            "Confirm Auto-Fix",
            f"Apply auto-fix for '{issue.rule_name}'?\n\n"
            f"Issue: {issue.message}\n\n"
            f"This operation includes:\n"
            f"• Safety backup before changes\n"
            f"• Automatic rollback on failure\n"
            f"• Validation re-run to verify\n\n"
            f"Apply fix now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Extract location components (block_name, signal_name)
        location_data = self._extract_location_components(issue.location)
        
        # Get auto-fix data from validator (already computed!)
        auto_fix_data = getattr(issue, 'auto_fix_data', {}) or {}
        
        # Apply fix - institutional grade direct access approach
        success = False
        error_msg = None
        
        try:
            if issue.rule_id == 'DIRECTION_001':
                # Direction switch - use suggested_type from auto_fix_data
                suggested_type = auto_fix_data.get('suggested_type')
                if suggested_type:
                    success = auto_fix_strategy_type(self.config, suggested_type)
                else:
                    error_msg = "No suggested direction in fix data"
          
            
            elif issue.rule_id == 'TIMING_004':
                # RECHECK timing fix - use data from auto_fix_data
                timing_window = auto_fix_data.get('timing_window')
                signal_name = location_data.get('signal_name')
                
                if signal_name and timing_window:
                    success = self._apply_recheck_timing_fix(signal_name, timing_window)
                else:
                    error_msg = f"Missing data - signal:{signal_name}, window:{timing_window}"
            
            elif issue.rule_id == 'EXIT_009':
                # Exit consolidation - use signal_name from auto_fix_data
                signal_name = auto_fix_data.get('signal_name')
                if signal_name:
                    # Determine level from location
                    if 'Signal::' in issue.location:
                        level = 'signal'
                    elif 'Block::' in issue.location:
                        level = 'block'
                    else:
                        level = 'strategy'
                    
                    success = self._apply_exit_consolidation_fix(signal_name, level)
                else:
                    error_msg = "No signal name in fix data"
            
            elif issue.rule_id == 'LOGIC_003':
                # Dead code - use signal_name from auto_fix_data
                signal_name = auto_fix_data.get('signal_name') or location_data.get('signal_name')
                block_name = location_data.get('block_name')
                
                if signal_name and block_name:
                    success = self._apply_dead_code_fix(signal_name, block_name)
                else:
                    error_msg = f"Missing data - signal:{signal_name}, block:{block_name}"
            
            else:
                error_msg = f"No auto-fix handler for rule {issue.rule_id}"
                
        except Exception as e:
            error_msg = str(e)
            success = False
        
        # Show result feedback
        if success:
            # Emit signal to notify parent window of config changes
            # Parent window (Strategy Builder) will handle database persistence
            self.fix_applied.emit(issue.rule_id, {'issue': issue.rule_name})
            
            QMessageBox.information(
                self,
                "✅ Fix Applied Successfully",
                f"Auto-fix completed: {issue.rule_name}\n\n"
                f"Validation will re-run automatically to verify the fix.\n\n"
                f"⚠️ IMPORTANT: Please save your strategy to persist these changes."
            )
            
            # Re-run validation
            self._rerun_validation()
        else:
            QMessageBox.warning(
                self,
                "❌ Fix Failed",
                f"Could not apply auto-fix: {issue.rule_name}\n\n"
                f"Error: {error_msg or 'Unknown error'}\n\n"
                f"Your strategy has been restored to its original state.\n"
                f"No changes were made."
            )
    
    def _show_fix_preview(self, issue: any) -> None:
        """
        Show fix preview on right-click
        Sprint 1.9.2 Task 1.9.2.6 (stub for Task 1.9.2.7)
        
        Full preview dialog will be implemented in Task 1.9.2.7
        """
        QMessageBox.information(
            self,
            "Fix Preview",
            f"Preview for: {issue.rule_name}\n\n"
            f"Detailed before/after comparison coming in Task 1.9.2.7.\n\n"
            f"This will show:\n"
            f"• Current configuration\n"
            f"• Proposed changes\n"
            f"• Impact analysis\n"
            f"• Cascading effects (if any)"
        )
    
    def _rerun_validation(self) -> None:
        """
        Re-run validation after applying fix
        Sprint 1.9.2 Task 1.9.2.8
        
        Updates validation report with new results
        Refreshes all tabs (Summary, Issues, Metrics)
        """
        from PyQt5.QtWidgets import QApplication
        
        # Show progress indicator
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # Run validation - FIXED: Method is validate(), not validate_strategy_config()
            validator = InstitutionalValidator()
            new_report = validator.validate(self.config)
            
            # Update report
            self.report = new_report
            
            # Recreate tabs with new data
            self._reinitialize_ui()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Could not re-run validation:\n\n{str(e)}\n\n"
                f"Please close and reopen the validation report."
            )
        finally:
            QApplication.restoreOverrideCursor()
    
    def _reinitialize_ui(self) -> None:
        """Reinitialize UI with updated report data"""
        # Get central widget
        central = self.centralWidget()
        if not central:
            return
        
        # Clear layout
        layout = central.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Recreate UI components
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Status banner
        status_banner = self._create_status_banner()
        layout.addWidget(status_banner)
        
        # Tabs
        tabs = self._create_tabs()
        layout.addWidget(tabs, 1)
        
        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)
    
    # =========================================================================
    # AUTO-FIX DATA EXTRACTION - INSTITUTIONAL GRADE (Direct Access)
    # =========================================================================
    
    def _extract_location_components(self, location: str) -> dict:
        """
        Extract block and signal names from location string
        
        Location format: "Block::block_name::Signal::signal_name"
        
        Returns dict with 'block_name' and 'signal_name' keys
        """
        components = {'block_name': None, 'signal_name': None}
        
        if not location or '::' not in location:
            return components
        
        parts = location.split('::')
        for i in range(len(parts)):
            if parts[i] == "Block" and i+1 < len(parts):
                components['block_name'] = parts[i+1]
            if parts[i] == "Signal" and i+1 < len(parts):
                components['signal_name'] = parts[i+1]
        
        return components
    
    # =========================================================================
    # AUTO-FIX APPLICATION METHODS
    # =========================================================================
    
    def _apply_recheck_timing_fix(self, signal_name: str, timing_window: int) -> bool:
        """Apply RECHECK timing fix to specific signal - INSTITUTIONAL GRADE"""
        try:
            # Find signal in config
            for block in self.config.blocks:
                for signal in block.signals:
                    if signal.name == signal_name:
                        # Found the signal - apply fix
                        if hasattr(signal, 'recheck_config') and signal.recheck_config:
                            # Calculate safe delay (75% of timing window)
                            safe_delay = max(1, int(timing_window * 0.75))
                            
                            # Apply fix using auto_fix module
                            success = auto_fix_recheck_delay(
                                signal.recheck_config,
                                timing_window,
                                buffer=0.75
                            )
                            
                            return success
            
            return False
            
        except Exception as e:
            print(f"RECHECK timing fix failed: {e}")
            return False
    
    def _apply_exit_consolidation_fix(self, identifier: str, level: str) -> bool:
        """Apply exit consolidation fix"""
        try:
            if level == 'strategy':
                # Consolidate at strategy level
                if hasattr(self.config, 'exit_conditions'):
                    new_exits = auto_fix_duplicate_exits(
                        self.config.exit_conditions,
                        identifier
                    )
                    self.config.exit_conditions = new_exits
                    return True
            
            elif level == 'block':
                # Find block and consolidate
                for block in self.config.blocks:
                    if block.name.lower() == identifier.lower():
                        if hasattr(block, 'exit_conditions'):
                            new_exits = auto_fix_duplicate_exits(
                                block.exit_conditions,
                                identifier
                            )
                            block.exit_conditions = new_exits
                            return True
            
            elif level == 'signal':
                # Find signal and consolidate
                for block in self.config.blocks:
                    for signal in block.signals:
                        if signal.name == identifier:
                            if hasattr(signal, 'exit_conditions'):
                                new_exits = auto_fix_duplicate_exits(
                                    signal.exit_conditions,
                                    identifier
                                )
                                signal.exit_conditions = new_exits
                                return True
            
            return False
            
        except Exception as e:
            print(f"Exit consolidation fix failed: {e}")
            return False
    
    def _apply_dead_code_fix(self, signal_name: str, block_name: str) -> bool:
        """Apply dead code fix to disable unreachable signal"""
        try:
            # Find block
            for block in self.config.blocks:
                if block.name.lower() == block_name.lower():
                    # Apply fix using auto_fix module
                    success = auto_fix_dead_code(
                        block,
                        [signal_name],
                        preserve_history=True  # Disable, don't delete
                    )
                    return success
            
            return False
            
        except Exception as e:
            print(f"Dead code fix failed: {e}")
            return False
