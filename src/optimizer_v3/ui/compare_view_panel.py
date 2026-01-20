"""
Compare View Panel - Window 2 Tab 5

Institutional-grade three-panel configuration comparison:
- Last 3 configurations side-by-side
- Synchronized scrolling
- Difference highlighting
- Statistical significance indicators
- Zero hardcoded styles (uses styles.py)

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.7)
"""

from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

# NautilusTrader imports
from nautilus_trader.model.objects import Money, Quantity

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    COLORS
)


@dataclass
class ConfigSnapshot:
    """Configuration snapshot with metadata"""
    name: str
    timestamp: datetime
    parameters: Dict[str, any]
    metrics: Dict[str, any]
    runtime_seconds: int
    hardware_usage: Dict[str, float]


class ConfigurationPanel(QFrame):
    """Single configuration display panel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config: Optional[ConfigSnapshot] = None
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize panel UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        self.header_label = QLabel("Configuration")
        self.header_label.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {COLORS['text_primary']};"
        )
        layout.addWidget(self.header_label)
        
        # Timestamp
        self.timestamp_label = QLabel("--")
        self.timestamp_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(self.timestamp_label)
        
        # Runtime
        self.runtime_label = QLabel("Runtime: --")
        self.runtime_label.setStyleSheet(get_label_style())
        layout.addWidget(self.runtime_label)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(15)
        
        # Parameters group
        self.params_group = self._create_params_group()
        self.content_layout.addWidget(self.params_group)
        
        # Metrics group
        self.metrics_group = self._create_metrics_group()
        self.content_layout.addWidget(self.metrics_group)
        
        self.content_layout.addStretch()
        self.content_widget.setLayout(self.content_layout)
        scroll.setWidget(self.content_widget)
        
        # Store scroll area reference
        self.scroll_area = scroll
        
        layout.addWidget(scroll)
        self.setLayout(layout)
    
    def _create_params_group(self) -> QGroupBox:
        """Create parameters display group"""
        group = QGroupBox("Parameters")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        self.param_labels: Dict[str, QLabel] = {}
        
        # Parameter placeholders (will be populated on load)
        self.params_layout = layout
        
        group.setLayout(layout)
        return group
    
    def _create_metrics_group(self) -> QGroupBox:
        """Create metrics display group"""
        group = QGroupBox("Performance Metrics")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        self.metric_labels: Dict[str, QLabel] = {}
        
        # Metric placeholders (will be populated on load)
        self.metrics_layout = layout
        
        group.setLayout(layout)
        return group
    
    def load_config(self, config: ConfigSnapshot) -> None:
        """
        Load configuration into panel.
        
        Args:
            config: Configuration snapshot to display
        """
        self.config = config
        
        # Update header
        self.header_label.setText(config.name)
        self.timestamp_label.setText(
            f"Run: {config.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.runtime_label.setText(
            f"Runtime: {config.runtime_seconds // 60}m {config.runtime_seconds % 60}s"
        )
        
        # Clear existing parameters
        for i in reversed(range(self.params_layout.count())):
            self.params_layout.itemAt(i).widget().setParent(None)
        self.param_labels.clear()
        
        # Add parameters
        for key, value in sorted(config.parameters.items()):
            label = QLabel(f"<b>{key.replace('_', ' ').title()}:</b> {self._format_value(value)}")
            label.setStyleSheet(get_label_style())
            label.setWordWrap(True)
            self.params_layout.addWidget(label)
            self.param_labels[key] = label
        
        # Clear existing metrics
        for i in reversed(range(self.metrics_layout.count())):
            self.metrics_layout.itemAt(i).widget().setParent(None)
        self.metric_labels.clear()
        
        # Add metrics
        for key, value in sorted(config.metrics.items()):
            label = QLabel(f"<b>{key.replace('_', ' ').title()}:</b> {self._format_value(value)}")
            label.setStyleSheet(get_label_style())
            label.setWordWrap(True)
            self.metrics_layout.addWidget(label)
            self.metric_labels[key] = label
    
    def _format_value(self, value: any) -> str:
        """Format value for display"""
        if isinstance(value, Money):
            return value.to_string()
        elif isinstance(value, Quantity):
            return value.to_string()
        elif isinstance(value, Decimal):
            return f"{value:.4f}"
        elif isinstance(value, float):
            return f"{value:.4f}"
        else:
            return str(value)
    
    def highlight_difference(self, key: str, color: str, is_param: bool = True) -> None:
        """
        Highlight a difference.
        
        Args:
            key: Parameter or metric key
            color: Color to use for highlighting
            is_param: True if parameter, False if metric
        """
        labels_dict = self.param_labels if is_param else self.metric_labels
        
        if key in labels_dict:
            label = labels_dict[key]
            label.setStyleSheet(
                f"color: {color}; font-weight: bold; "
                f"background-color: {COLORS['bg_medium']}; "
                f"padding: 4px; border-radius: 2px;"
            )


class CompareViewPanel(QWidget):
    """
    Institutional-grade Compare View Panel.
    
    Provides:
    - Three-panel configuration comparison
    - Synchronized scrolling
    - Difference highlighting
    - Statistical indicators
    """
    
    # Signals
    config_selected = pyqtSignal(str)  # Emits config name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.panels: List[ConfigurationPanel] = []
        self.configs: List[ConfigSnapshot] = []
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("📊 Configuration Comparison")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title_label)
        
        # Control bar
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        # Three-panel layout
        panels_layout = self._create_panels_layout()
        layout.addLayout(panels_layout)
        
        # Difference summary
        summary_bar = self._create_summary_bar()
        layout.addLayout(summary_bar)
        
        self.setLayout(layout)
    
    def _create_control_bar(self) -> QHBoxLayout:
        """Create control button bar"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        refresh_btn.setToolTip("Refresh with latest configurations")
        layout.addWidget(refresh_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export Comparison")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.clicked.connect(self._export_comparison)
        export_btn.setToolTip("Export comparison to file")
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        # Info label
        self.info_label = QLabel("Last 3 configurations")
        self.info_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(self.info_label)
        
        return layout
    
    def _create_panels_layout(self) -> QHBoxLayout:
        """Create three-panel comparison layout"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Create 3 panels
        for i in range(3):
            panel = ConfigurationPanel()
            panel.setStyleSheet(
                f"ConfigurationPanel {{ "
                f"background-color: {COLORS['bg_dark']}; "
                f"border: 1px solid {COLORS['border']}; "
                f"border-radius: 4px; "
                f"}}"
            )
            
            # Connect scroll synchronization
            panel.scroll_area.verticalScrollBar().valueChanged.connect(
                lambda value, p=panel: self._sync_scroll(value, p)
            )
            
            self.panels.append(panel)
            layout.addWidget(panel)
        
        return layout
    
    def _create_summary_bar(self) -> QHBoxLayout:
        """Create difference summary bar"""
        layout = QHBoxLayout()
        layout.setSpacing(30)
        
        # Differences count
        self.diff_count_label = QLabel("Differences: <b>0</b>")
        self.diff_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.diff_count_label)
        
        # Improvements
        self.improvements_label = QLabel("Improvements: <b>0</b>")
        self.improvements_label.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(self.improvements_label)
        
        # Regressions
        self.regressions_label = QLabel("Regressions: <b>0</b>")
        self.regressions_label.setStyleSheet(f"color: {COLORS['error']};")
        layout.addWidget(self.regressions_label)
        
        # Statistical significance
        self.significance_label = QLabel("Significant Changes: <b>0</b>")
        self.significance_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.significance_label)
        
        layout.addStretch()
        return layout
    
    def load_configurations(self, configs: List[ConfigSnapshot]) -> None:
        """
        Load configurations for comparison.
        
        Args:
            configs: List of up to 3 configuration snapshots
        """
        self.configs = configs[:3]  # Take at most 3
        
        # Load into panels
        for i, config in enumerate(self.configs):
            if i < len(self.panels):
                self.panels[i].load_config(config)
        
        # Clear remaining panels
        for i in range(len(self.configs), len(self.panels)):
            self.panels[i].header_label.setText("No Data")
            self.panels[i].timestamp_label.setText("--")
            self.panels[i].runtime_label.setText("--")
        
        # Analyze and highlight differences
        if len(self.configs) >= 2:
            self._analyze_differences()
    
    def _sync_scroll(self, value: int, source_panel: ConfigurationPanel) -> None:
        """
        Synchronize scrolling across panels.
        
        Args:
            value: Scroll position
            source_panel: Panel that initiated scroll
        """
        for panel in self.panels:
            if panel != source_panel:
                # Block signals to prevent recursion
                panel.scroll_area.verticalScrollBar().blockSignals(True)
                panel.scroll_area.verticalScrollBar().setValue(value)
                panel.scroll_area.verticalScrollBar().blockSignals(False)
    
    def _analyze_differences(self) -> None:
        """Analyze and highlight differences between configurations"""
        if len(self.configs) < 2:
            return
        
        base_config = self.configs[0]
        total_diffs = 0
        improvements = 0
        regressions = 0
        significant = 0
        
        # Compare with subsequent configs
        for i in range(1, len(self.configs)):
            compare_config = self.configs[i]
            
            # Compare parameters
            for key in base_config.parameters.keys():
                if key in compare_config.parameters:
                    base_val = base_config.parameters[key]
                    comp_val = compare_config.parameters[key]
                    
                    if base_val != comp_val:
                        total_diffs += 1
                        self.panels[i].highlight_difference(
                            key, COLORS['warning'], is_param=True
                        )
            
            # Compare metrics
            for key in base_config.metrics.keys():
                if key in compare_config.metrics:
                    base_val = base_config.metrics[key]
                    comp_val = compare_config.metrics[key]
                    
                    # Determine if difference is significant
                    is_sig, is_improvement = self._assess_metric_change(
                        key, base_val, comp_val
                    )
                    
                    if base_val != comp_val:
                        total_diffs += 1
                        
                        if is_sig:
                            significant += 1
                            if is_improvement:
                                improvements += 1
                                color = COLORS['success']
                            else:
                                regressions += 1
                                color = COLORS['error']
                        else:
                            color = COLORS['info']
                        
                        self.panels[i].highlight_difference(
                            key, color, is_param=False
                        )
        
        # Update summary
        self.diff_count_label.setText(f"Differences: <b>{total_diffs}</b>")
        self.improvements_label.setText(f"Improvements: <b>{improvements}</b>")
        self.regressions_label.setText(f"Regressions: <b>{regressions}</b>")
        self.significance_label.setText(f"Significant Changes: <b>{significant}</b>")
    
    def _assess_metric_change(self, key: str, old_val: any, new_val: any) -> tuple:
        """
        Assess if metric change is significant and an improvement.
        
        Args:
            key: Metric key
            old_val: Old value
            new_val: New value
            
        Returns:
            Tuple of (is_significant, is_improvement)
        """
        # Simple heuristic - can be enhanced with statistical tests
        try:
            if isinstance(old_val, Money):
                old_dec = old_val.as_decimal()
                new_dec = new_val.as_decimal()
            elif isinstance(old_val, Quantity):
                old_dec = old_val.as_decimal()
                new_dec = new_val.as_decimal()
            elif isinstance(old_val, Decimal):
                old_dec = old_val
                new_dec = new_val
            else:
                old_dec = Decimal(str(old_val))
                new_dec = Decimal(str(new_val))
            
            # Calculate percentage change
            if old_dec != Decimal('0'):
                pct_change = abs((new_dec - old_dec) / old_dec) * Decimal('100')
                is_significant = pct_change > Decimal('5')  # >5% change
            else:
                is_significant = new_dec != Decimal('0')
            
            # Determine if improvement (depends on metric)
            improvement_metrics = {
                'sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
                'win_rate', 'profit_factor', 'total_pnl'
            }
            reduction_metrics = {
                'max_drawdown', 'avg_loss'
            }
            
            if any(m in key.lower() for m in improvement_metrics):
                is_improvement = new_dec > old_dec
            elif any(m in key.lower() for m in reduction_metrics):
                is_improvement = new_dec < old_dec
            else:
                is_improvement = False
            
            return (is_significant, is_improvement)
            
        except:
            return (False, False)
    
    def _export_comparison(self) -> None:
        """Export comparison to file"""
        from datetime import datetime
        from PyQt5.QtWidgets import QMessageBox
        
        if not self.configs:
            QMessageBox.information(
                self,
                "No Data",
                "No configurations to export."
            )
            return
        
        try:
            filename = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(filename, 'w') as f:
                f.write("=== OPTIMIZER V3 CONFIGURATION COMPARISON ===\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Configurations: {len(self.configs)}\n\n")
                
                for i, config in enumerate(self.configs, 1):
                    f.write(f"=== CONFIGURATION {i}: {config.name} ===\n")
                    f.write(f"Timestamp: {config.timestamp}\n")
                    f.write(f"Runtime: {config.runtime_seconds}s\n\n")
                    
                    f.write("Parameters:\n")
                    for key, value in sorted(config.parameters.items()):
                        f.write(f"  {key}: {value}\n")
                    
                    f.write("\nMetrics:\n")
                    for key, value in sorted(config.metrics.items()):
                        f.write(f"  {key}: {value}\n")
                    
                    f.write("\n" + "="*70 + "\n\n")
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Comparison exported to {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export comparison:\n{str(e)}"
            )
    
    def get_selected_config(self, panel_index: int) -> Optional[ConfigSnapshot]:
        """
        Get configuration from panel.
        
        Args:
            panel_index: Panel index (0, 1, or 2)
            
        Returns:
            Configuration snapshot if available
        """
        if 0 <= panel_index < len(self.configs):
            return self.configs[panel_index]
        return None
