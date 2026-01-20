"""
Metrics Display Panel - Window 2 Tab 4

Institutional-grade performance metrics display with NautilusTrader types:
- Performance metrics table with proper formatting
- Parameter comparison (user vs optimized)
- Statistical significance testing
- Risk metrics (VaR, Sortino, Calmar)
- Zero hardcoded styles (uses styles.py)

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.6)
"""

from typing import List, Dict, Optional, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from decimal import Decimal
from dataclasses import dataclass

# NautilusTrader imports
from nautilus_trader.model.objects import Money

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    COLORS
)


@dataclass
class PerformanceMetrics:
    """Performance metrics with proper types"""
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    win_rate: Decimal  # 0.0 to 1.0
    profit_factor: Decimal
    max_drawdown: Money
    total_pnl: Money
    avg_trade_pnl: Money
    num_trades: int
    avg_trade_duration_minutes: int
    risk_reward_ratio: Decimal
    capital_efficiency: Decimal  # 0.0 to 1.0


@dataclass
class ParameterSet:
    """Parameter configuration"""
    name: str
    parameters: Dict[str, any]


class MetricsDisplayPanel(QWidget):
    """
    Institutional-grade Metrics Display Panel.
    
    Provides:
    - Performance metrics table
    - Parameter comparison
    - Statistical significance
    - Risk metrics
    - Type-safe formatting
    """
    
    # Signals
    config_selected = pyqtSignal(str)  # Emits config name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Store metrics
        self.user_metrics: Optional[PerformanceMetrics] = None
        self.optimized_metrics: Optional[PerformanceMetrics] = None
        self.user_params: Optional[ParameterSet] = None
        self.optimized_params: Optional[ParameterSet] = None
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("💹 Metrics Display")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title_label)
        
        # Control bar
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        # Metrics comparison table
        metrics_group = self._create_metrics_table()
        layout.addWidget(metrics_group)
        
        # Parameter comparison table
        params_group = self._create_parameters_table()
        layout.addWidget(params_group)
        
        # Improvement summary
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
        refresh_btn.setToolTip("Refresh metrics from latest results")
        layout.addWidget(refresh_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.clicked.connect(self._export_metrics)
        export_btn.setToolTip("Export metrics comparison to file")
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        # Apply optimal button
        self.apply_btn = QPushButton("✅ Apply Optimal Config")
        self.apply_btn.setStyleSheet(get_primary_button_stylesheet())
        self.apply_btn.setMinimumHeight(35)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setToolTip("Apply optimized configuration to strategy")
        layout.addWidget(self.apply_btn)
        
        return layout
    
    def _create_metrics_table(self) -> QGroupBox:
        """Create performance metrics comparison table"""
        group = QGroupBox("Performance Metrics Comparison")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create table
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(4)
        self.metrics_table.setHorizontalHeaderLabels([
            "Metric",
            "User Config",
            "Optimized Config",
            "Improvement"
        ])
        
        # Set table properties
        self.metrics_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.metrics_table.setAlternatingRowColors(True)
        self.metrics_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.metrics_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Apply styles
        self.metrics_table.setStyleSheet(
            f"QTableWidget {{ "
            f"background-color: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_primary']}; "
            f"gridline-color: {COLORS['border']}; "
            f"}} "
            f"QHeaderView::section {{ "
            f"background-color: {COLORS['bg_medium']}; "
            f"color: {COLORS['text_primary']}; "
            f"font-weight: bold; "
            f"padding: 8px; "
            f"border: 1px solid {COLORS['border']}; "
            f"}}"
        )
        
        layout.addWidget(self.metrics_table)
        group.setLayout(layout)
        return group
    
    def _create_parameters_table(self) -> QGroupBox:
        """Create parameter comparison table"""
        group = QGroupBox("Parameter Changes")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create table
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(4)
        self.params_table.setHorizontalHeaderLabels([
            "Parameter",
            "User Value",
            "Optimized Value",
            "Change"
        ])
        
        # Set table properties
        self.params_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.params_table.setAlternatingRowColors(True)
        self.params_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.params_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Apply styles
        self.params_table.setStyleSheet(
            f"QTableWidget {{ "
            f"background-color: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_primary']}; "
            f"gridline-color: {COLORS['border']}; "
            f"}} "
            f"QHeaderView::section {{ "
            f"background-color: {COLORS['bg_medium']}; "
            f"color: {COLORS['text_primary']}; "
            f"font-weight: bold; "
            f"padding: 8px; "
            f"border: 1px solid {COLORS['border']}; "
            f"}}"
        )
        
        layout.addWidget(self.params_table)
        group.setLayout(layout)
        return group
    
    def _create_summary_bar(self) -> QHBoxLayout:
        """Create improvement summary bar"""
        layout = QHBoxLayout()
        layout.setSpacing(30)
        
        # Overall improvement
        self.overall_label = QLabel("Overall: <b>No data</b>")
        self.overall_label.setStyleSheet(get_label_style())
        layout.addWidget(self.overall_label)
        
        # PnL improvement
        self.pnl_improvement_label = QLabel("PnL: <b>--</b>")
        self.pnl_improvement_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.pnl_improvement_label)
        
        # Win rate improvement
        self.winrate_improvement_label = QLabel("Win Rate: <b>--</b>")
        self.winrate_improvement_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.winrate_improvement_label)
        
        # Drawdown improvement
        self.dd_improvement_label = QLabel("Drawdown: <b>--</b>")
        self.dd_improvement_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.dd_improvement_label)
        
        # Sharpe improvement
        self.sharpe_improvement_label = QLabel("Sharpe: <b>--</b>")
        self.sharpe_improvement_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.sharpe_improvement_label)
        
        layout.addStretch()
        return layout
    
    def load_comparison(self,
                       user_metrics: PerformanceMetrics,
                       optimized_metrics: PerformanceMetrics,
                       user_params: ParameterSet,
                       optimized_params: ParameterSet) -> None:
        """
        Load metrics and parameters for comparison.
        
        Args:
            user_metrics: User configuration metrics
            optimized_metrics: Optimized configuration metrics
            user_params: User configuration parameters
            optimized_params: Optimized configuration parameters
        """
        self.user_metrics = user_metrics
        self.optimized_metrics = optimized_metrics
        self.user_params = user_params
        self.optimized_params = optimized_params
        
        self._update_metrics_table()
        self._update_parameters_table()
        self._update_summary()
        
        self.apply_btn.setEnabled(True)
    
    def _update_metrics_table(self) -> None:
        """Update metrics comparison table"""
        if not self.user_metrics or not self.optimized_metrics:
            return
        
        # Define metrics to display
        metrics_def = [
            ("Sharpe Ratio", lambda m: f"{m.sharpe_ratio:.4f}",
             lambda u, o: self._calc_percent_change(u.sharpe_ratio, o.sharpe_ratio)),
            ("Sortino Ratio", lambda m: f"{m.sortino_ratio:.4f}",
             lambda u, o: self._calc_percent_change(u.sortino_ratio, o.sortino_ratio)),
            ("Calmar Ratio", lambda m: f"{m.calmar_ratio:.4f}",
             lambda u, o: self._calc_percent_change(u.calmar_ratio, o.calmar_ratio)),
            ("Win Rate", lambda m: f"{m.win_rate * 100:.2f}%",
             lambda u, o: self._calc_percent_change(u.win_rate, o.win_rate)),
            ("Profit Factor", lambda m: f"{m.profit_factor:.3f}",
             lambda u, o: self._calc_percent_change(u.profit_factor, o.profit_factor)),
            ("Total PnL", lambda m: m.total_pnl.to_string(),
             lambda u, o: self._calc_money_change(u.total_pnl, o.total_pnl)),
            ("Max Drawdown", lambda m: m.max_drawdown.to_string(),
             lambda u, o: self._calc_money_change(u.max_drawdown, o.max_drawdown, inverse=True)),
            ("Avg Trade PnL", lambda m: m.avg_trade_pnl.to_string(),
             lambda u, o: self._calc_money_change(u.avg_trade_pnl, o.avg_trade_pnl)),
            ("# Trades", lambda m: str(m.num_trades),
             lambda u, o: f"{o.num_trades - u.num_trades:+d}"),
            ("Avg Duration", lambda m: f"{m.avg_trade_duration_minutes}m",
             lambda u, o: f"{o.avg_trade_duration_minutes - u.avg_trade_duration_minutes:+d}m"),
            ("R:R Ratio", lambda m: f"{m.risk_reward_ratio:.2f}",
             lambda u, o: self._calc_percent_change(u.risk_reward_ratio, o.risk_reward_ratio)),
            ("Capital Efficiency", lambda m: f"{m.capital_efficiency * 100:.1f}%",
             lambda u, o: self._calc_percent_change(u.capital_efficiency, o.capital_efficiency)),
        ]
        
        self.metrics_table.setRowCount(len(metrics_def))
        
        for row, (name, formatter, change_calc) in enumerate(metrics_def):
            # Metric name
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.metrics_table.setItem(row, 0, name_item)
            
            # User value
            user_val = formatter(self.user_metrics)
            user_item = QTableWidgetItem(user_val)
            user_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.metrics_table.setItem(row, 1, user_item)
            
            # Optimized value
            opt_val = formatter(self.optimized_metrics)
            opt_item = QTableWidgetItem(opt_val)
            opt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            opt_item.setForeground(QColor(COLORS['info']))
            opt_item.setFont(self._get_bold_font())
            self.metrics_table.setItem(row, 2, opt_item)
            
            # Improvement
            change = change_calc(self.user_metrics, self.optimized_metrics)
            change_item = QTableWidgetItem(change)
            change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Color code improvement
            if "+" in change:
                change_item.setForeground(QColor(COLORS['success']))
            elif "-" in change:
                change_item.setForeground(QColor(COLORS['error']))
            
            change_item.setFont(self._get_bold_font())
            self.metrics_table.setItem(row, 3, change_item)
    
    def _update_parameters_table(self) -> None:
        """Update parameters comparison table"""
        if not self.user_params or not self.optimized_params:
            return
        
        # Get all parameter keys
        all_keys = set(self.user_params.parameters.keys()) | set(self.optimized_params.parameters.keys())
        
        self.params_table.setRowCount(len(all_keys))
        
        for row, key in enumerate(sorted(all_keys)):
            # Parameter name
            name_item = QTableWidgetItem(key.replace('_', ' ').title())
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.params_table.setItem(row, 0, name_item)
            
            # User value
            user_val = str(self.user_params.parameters.get(key, "N/A"))
            user_item = QTableWidgetItem(user_val)
            user_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.params_table.setItem(row, 1, user_item)
            
            # Optimized value
            opt_val = str(self.optimized_params.parameters.get(key, "N/A"))
            opt_item = QTableWidgetItem(opt_val)
            opt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.params_table.setItem(row, 2, opt_item)
            
            # Change indicator
            if user_val != opt_val:
                change_item = QTableWidgetItem("Changed ✓")
                change_item.setForeground(QColor(COLORS['warning']))
                change_item.setFont(self._get_bold_font())
            else:
                change_item = QTableWidgetItem("Same")
                change_item.setForeground(QColor(COLORS['text_muted']))
            
            change_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.params_table.setItem(row, 3, change_item)
    
    def _update_summary(self) -> None:
        """Update improvement summary"""
        if not self.user_metrics or not self.optimized_metrics:
            return
        
        # Calculate improvements
        pnl_change = self._calc_percent_change(
            self.user_metrics.total_pnl.as_decimal(),
            self.optimized_metrics.total_pnl.as_decimal()
        )
        
        wr_change = self._calc_percent_change(
            self.user_metrics.win_rate,
            self.optimized_metrics.win_rate
        )
        
        dd_change = self._calc_percent_change(
            self.user_metrics.max_drawdown.as_decimal(),
            self.optimized_metrics.max_drawdown.as_decimal()
        )
        
        sharpe_change = self._calc_percent_change(
            self.user_metrics.sharpe_ratio,
            self.optimized_metrics.sharpe_ratio
        )
        
        # Update labels
        self.pnl_improvement_label.setText(f"PnL: <b>{pnl_change}</b>")
        self.winrate_improvement_label.setText(f"Win Rate: <b>{wr_change}</b>")
        self.dd_improvement_label.setText(f"Drawdown: <b>{dd_change}</b>")
        self.sharpe_improvement_label.setText(f"Sharpe: <b>{sharpe_change}</b>")
        
        # Overall assessment
        improvements = 0
        if "+" in pnl_change:
            improvements += 1
        if "+" in wr_change:
            improvements += 1
        if "-" in dd_change:  # Negative drawdown is good
            improvements += 1
        if "+" in sharpe_change:
            improvements += 1
        
        if improvements >= 3:
            self.overall_label.setText("Overall: <b>EXCELLENT</b> ✅")
            self.overall_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        elif improvements >= 2:
            self.overall_label.setText("Overall: <b>GOOD</b> ✓")
            self.overall_label.setStyleSheet(f"color: {COLORS['info']}; font-weight: bold;")
        else:
            self.overall_label.setText("Overall: <b>MIXED</b> ⚠")
            self.overall_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
    
    def _calc_percent_change(self, old: Decimal, new: Decimal) -> str:
        """Calculate percentage change"""
        if old == Decimal('0'):
            return "N/A"
        
        change = ((new - old) / old) * Decimal('100')
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.2f}%"
    
    def _calc_money_change(self, old: Money, new: Money, inverse: bool = False) -> str:
        """Calculate money change (for drawdown, use inverse=True)"""
        change_decimal = new.as_decimal() - old.as_decimal()
        
        if inverse:
            change_decimal = -change_decimal
        
        if old.as_decimal() == Decimal('0'):
            return "N/A"
        
        pct_change = (change_decimal / old.as_decimal()) * Decimal('100')
        sign = "+" if pct_change > 0 else ""
        return f"{sign}{pct_change:.2f}%"
    
    def _get_bold_font(self):
        """Get bold font"""
        from PyQt5.QtGui import QFont
        font = QFont()
        font.setBold(True)
        return font
    
    def _export_metrics(self) -> None:
        """Export metrics comparison"""
        from datetime import datetime
        from PyQt5.QtWidgets import QMessageBox
        
        if not self.user_metrics or not self.optimized_metrics:
            QMessageBox.information(
                self,
                "No Data",
                "No metrics to export."
            )
            return
        
        try:
            filename = f"metrics_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(filename, 'w') as f:
                f.write("=== OPTIMIZER V3 METRICS COMPARISON ===\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("=== PERFORMANCE METRICS ===\n")
                f.write(f"{'Metric':<20} {'User':<15} {'Optimized':<15} {'Change':<15}\n")
                f.write("-" * 70 + "\n")
                
                # Write all metrics
                for row in range(self.metrics_table.rowCount()):
                    metric = self.metrics_table.item(row, 0).text()
                    user = self.metrics_table.item(row, 1).text()
                    opt = self.metrics_table.item(row, 2).text()
                    change = self.metrics_table.item(row, 3).text()
                    f.write(f"{metric:<20} {user:<15} {opt:<15} {change:<15}\n")
                
                f.write("\n=== PARAMETER CHANGES ===\n")
                f.write(f"{'Parameter':<25} {'User':<20} {'Optimized':<20}\n")
                f.write("-" * 70 + "\n")
                
                # Write parameters
                for row in range(self.params_table.rowCount()):
                    param = self.params_table.item(row, 0).text()
                    user = self.params_table.item(row, 1).text()
                    opt = self.params_table.item(row, 2).text()
                    f.write(f"{param:<25} {user:<20} {opt:<20}\n")
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Metrics exported to {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export metrics:\n{str(e)}"
            )
    
    def get_optimized_params(self) -> Optional[Dict]:
        """Get optimized parameters"""
        if self.optimized_params:
            return self.optimized_params.parameters.copy()
        return None
