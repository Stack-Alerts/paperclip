"""
Metrics Display Panel - Comprehensive Performance Analysis

Institutional-grade performance metrics and analysis:
- Performance metrics table (Sharpe, Win Rate, Profit Factor, etc.)
- Risk metrics (VaR, Max Drawdown, Sortino, etc.)
- Parameter comparison (user vs optimized)
- Statistical significance indicators
- Proper NautilusTrader type formatting
- Export capabilities

ZERO HARDCODED STYLES - All from styles.py

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.6)
"""

from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QScrollArea, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_tab_widget_stylesheet,
    get_table_stylesheet,
    get_color
)


class MetricsDisplayPanel(QWidget):
    """
    Comprehensive Metrics Display Panel
    
    Features:
    - Performance metrics with proper type formatting
    - Risk metrics analysis
    - Parameter comparison view
    - Statistical significance testing
    - Export capabilities
    - Dark theme compatible
    """
    
    # Signals
    metrics_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_metrics: Dict = {}
        self.baseline_metrics: Dict = {}
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("📊 Performance Metrics")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title_label)
        
        # Two-column layout: Performance (left) and Risk (right) side-by-side
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(20)
        
        # Left column: Performance Metrics
        perf_group = self._create_performance_group()
        metrics_layout.addWidget(perf_group, 1)  # Equal stretch
        
        # Right column: Risk Metrics
        risk_group = self._create_risk_group()
        metrics_layout.addWidget(risk_group, 1)  # Equal stretch
        
        layout.addLayout(metrics_layout)
        
        # Control buttons at bottom
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        self.setLayout(layout)
    
    def _create_performance_group(self) -> QGroupBox:
        """Create performance metrics group"""
        # Performance metrics table
        perf_group = QGroupBox("📊 Performance Metrics")
        perf_group.setStyleSheet(get_groupbox_header_stylesheet())
        
        perf_layout = QVBoxLayout()
        perf_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create metrics table with Recommendations column
        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(4)
        self.perf_table.setHorizontalHeaderLabels(['Metric', 'Value', 'Rating', 'Recommendation'])
        
        # Table styling
        # Use centralized table stylesheet (ZERO hardcoded styles)
        self.perf_table.setStyleSheet(get_table_stylesheet())
        
        self.perf_table.setAlternatingRowColors(True)
        self.perf_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.perf_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.perf_table.setSortingEnabled(True)  # Excel-like sorting
        self.perf_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.perf_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.perf_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.perf_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.perf_table.setColumnWidth(0, 180)  # Metric name
        self.perf_table.setColumnWidth(1, 120)  # Value column
        self.perf_table.setColumnWidth(2, 100)  # Rating column
        # Column 3 (Recommendation) stretches to fill remaining space
        self.perf_table.verticalHeader().setVisible(False)
        
        # Populate with metric rows with institutional-grade tooltips
        metrics = [
            ('Total P&L', '$0.00', '-', 
             'Total Profit & Loss\n\n'
             'Sum of all realized trade profits and losses.\n\n'
             'Calculation:\n'
             'Total P&L = Σ(Trade PnL)\n\n'
             'Interpretation:\n'
             '• Positive: Strategy is profitable overall\n'
             '• Negative: Strategy is losing money\n'
             '• Zero: Break-even performance\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: Positive and growing\n'
             '⚠ Fair: Small positive or near break-even\n'
             '✗ Poor: Negative'),
            
            ('Total Return %', '0.00%', '-',
             'Total Return Percentage\n\n'
             'Percentage return on starting capital.\n\n'
             'Calculation:\n'
             'Return % = (Total P&L / Starting Capital) × 100\n\n'
             'Example:\n'
             '$10,000 capital → $500 profit = 5% return\n\n'
             'Interpretation:\n'
             '• Higher is better\n'
             '• Compare to buy-and-hold returns\n'
             '• Annualize for multi-period comparison\n\n'
             'Institutional Benchmark (Annual):\n'
             '✓ Good: >15% (outperforms markets)\n'
             '⚠ Fair: 8-15% (matches markets)\n'
             '✗ Poor: <8% (underperforms)'),
            
            ('Sharpe Ratio', '0.0000', '-',
             'Sharpe Ratio (Risk-Adjusted Return)\n\n'
             'Measures return per unit of risk (volatility).\n\n'
             'Calculation:\n'
             'Sharpe = (Avg Return - Risk Free Rate) / Std Dev\n'
             'Simplified: Sharpe = Avg Trade / Std Deviation\n\n'
             'Interpretation:\n'
             '• Higher = Better risk-adjusted returns\n'
             '• Accounts for volatility, not just returns\n'
             '• Industry standard for comparing strategies\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: ≥2.0 (excellent risk-adjusted returns)\n'
             '⚠ Fair: 1.0-2.0 (acceptable)\n'
             '✗ Poor: <1.0 (poor risk management)'),
            
            ('Win Rate', '0.00%', '-',
             'Win Rate (Percentage of Winning Trades)\n\n'
             'Percentage of trades that ended in profit.\n\n'
             'Calculation:\n'
             'Win Rate = (Winning Trades / Total Trades) × 100\n\n'
             'Example:\n'
             '60 wins out of 100 trades = 60% win rate\n\n'
             'Interpretation:\n'
             '• NOT the only important metric\n'
             '• Must consider with Profit Factor\n'
             '• High win rate can still lose money if losses are large\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: ≥60% (highly selective)\n'
             '⚠ Fair: 50-60% (balanced)\n'
             '✗ Poor: <50% (need high R:R to profit)'),
            
            ('Profit Factor', '0.000', '-',
             'Profit Factor (Gross Profit / Gross Loss)\n\n'
             'Ratio of total winning trades to total losing trades.\n\n'
             'Calculation:\n'
             'Profit Factor = Gross Profit / |Gross Loss|\n\n'
             'Example:\n'
             '$10,000 in wins / $5,000 in losses = 2.0\n\n'
             'Interpretation:\n'
             '• >1.0: Profitable strategy\n'
             '• =1.0: Break-even\n'
             '• <1.0: Losing strategy\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: ≥2.0 (wins are 2x losses)\n'
             '⚠ Fair: 1.5-2.0 (acceptable)\n'
             '✗ Poor: <1.5 (marginal profitability)'),
            
            ('Max Drawdown', '$0.00', '-',
             'Maximum Drawdown (Largest Peak-to-Trough Decline)\n\n'
             'Largest drop from equity peak to trough.\n\n'
             'Calculation:\n'
             'Max DD = Peak Equity - Lowest Trough After Peak\n\n'
             'Example:\n'
             'Peak: $12,000 → Trough: $10,000 = $2,000 drawdown\n\n'
             'Interpretation:\n'
             '• Measures worst-case scenario\n'
             '• Critical for position sizing\n'
             '• Expect 2-3x in live trading\n\n'
             'Risk Management:\n'
             '✓ Good: <10% of capital\n'
             '⚠ Monitor: 10-20% of capital\n'
             '✗ High Risk: >20% of capital'),
            
            ('Number of Trades', '0', '-',
             'Total Number of Trades Executed\n\n'
             'Count of all completed trades (entries + exits).\n\n'
             'Statistical Significance:\n'
             '• <30 trades: Not statistically significant\n'
             '• 30-100 trades: Moderate confidence\n'
             '• >100 trades: High statistical confidence\n\n'
             'Interpretation:\n'
             '• More trades = More reliable metrics\n'
             '• Too few trades = Unreliable results\n'
             '• Too many trades = High transaction costs\n\n'
             'Institutional Minimum:\n'
             '• Backtesting: ≥100 trades for confidence\n'
             '• Live validation: ≥30 trades minimum'),
            
            ('Average Trade P&L', '$0.00', '-',
             'Average Profit/Loss Per Trade\n\n'
             'Mean P&L across all trades.\n\n'
             'Calculation:\n'
             'Avg Trade = Total P&L / Number of Trades\n\n'
             'Example:\n'
             '$1,000 profit / 50 trades = $20 per trade\n\n'
             'Interpretation:\n'
             '• Must exceed transaction costs\n'
             '• Higher = More efficient strategy\n'
             '• Consistency matters more than size\n\n'
             'After Costs:\n'
             '• Consider commissions (~$2-5 per trade)\n'
             '• Consider slippage (~0.1-0.5%)\n'
             '• Net avg should be >$10 minimum'),
            
            ('Average Win', '$0.00', '-',
             'Average Winning Trade Size\n\n'
             'Mean profit of all winning trades only.\n\n'
             'Calculation:\n'
             'Avg Win = Gross Profit / Number of Wins\n\n'
             'Use With:\n'
             '• Compare to Average Loss\n'
             '• Calculate realistic R:R ratios\n'
             '• Size positions appropriately\n\n'
             'Interpretation:\n'
             '• Larger wins = Better asymmetry\n'
             '• Should be >2x Average Loss for sustainability\n'
             '• Consistency of win size matters'),
            
            ('Average Loss', '$0.00', '-',
             'Average Losing Trade Size\n\n'
             'Mean loss of all losing trades only.\n\n'
             'Calculation:\n'
             'Avg Loss = |Gross Loss| / Number of Losses\n\n'
             'Risk Management:\n'
             '• Should be consistent (good risk control)\n'
             '• Large variance = Poor stop loss discipline\n'
             '• Should be ≤1% of capital per trade\n\n'
             'Interpretation:\n'
             '• Smaller losses = Better risk management\n'
             '• Consistency indicates discipline\n'
             '• Wide variation = Poor execution'),
            
            ('Largest Win', '$0.00', '-',
             'Largest Single Winning Trade\n\n'
             'The most profitable trade in the series.\n\n'
             'Analysis:\n'
             '• If >>Average Win: Outlier dependency risk\n'
             '• If ≈Average Win: Consistent performance\n\n'
             'Warning Signs:\n'
             '✗ Largest Win > 50% of Total P&L\n'
             '  → Strategy depends on rare events\n'
             '✗ Largest Win > 10x Average Win\n'
             '  → Not repeatable performance\n\n'
             'Healthy Strategy:\n'
             '✓ Largest Win ≤ 3x Average Win\n'
             '✓ Profits distributed across many trades'),
            
            ('Largest Loss', '$0.00', '-',
             'Largest Single Losing Trade\n\n'
             'The worst trade in the series.\n\n'
             'Risk Assessment:\n'
             '• Should be ≤2x Average Loss\n'
             '• If much larger: Stop loss failure\n'
             '• Indicates worst-case scenario\n\n'
             'Warning Signs:\n'
             '✗ Largest Loss > 3x Average Loss\n'
             '  → Stop loss not working properly\n'
             '✗ Largest Loss > 5% of capital\n'
             '  → Excessive single-trade risk\n\n'
             'Institutional Standard:\n'
             '✓ Largest Loss ≤ 1.5x Average Loss\n'
             '✓ Largest Loss < 2% of capital'),
            
            ('Risk/Reward Ratio', '0.00', '-',
             'Risk to Reward Ratio (R:R)\n\n'
             'Ratio of average win to average loss.\n\n'
             'Calculation:\n'
             'R:R = |Average Win| / |Average Loss|\n\n'
             'Example:\n'
             '$150 avg win / $100 avg loss = 1.5:1\n\n'
             'Win Rate Requirements:\n'
             '• 1:1 R:R needs >50% win rate to profit\n'
             '• 2:1 R:R needs >33% win rate to profit\n'
             '• 3:1 R:R needs >25% win rate to profit\n\n'
             'Institutional Target:\n'
             '✓ Good: ≥2:1 (wins are 2x losses)\n'
             '⚠ Fair: 1.5-2:1 (acceptable)\n'
             '✗ Poor: <1.5:1 (need high win rate)'),
            
            ('Recovery Factor', '0.00', '-',
             'Recovery Factor (Profit / Max Drawdown)\n\n'
             'How many times profit covers worst drawdown.\n\n'
             'Calculation:\n'
             'Recovery = Net Profit / Max Drawdown\n\n'
             'Example:\n'
             '$1,000 profit / $200 max DD = 5.0\n\n'
             'Interpretation:\n'
             '• Higher = Better drawdown recovery\n'
             '• Measures resilience\n'
             '• Important for live trading psychology\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: ≥5.0 (strong recovery)\n'
             '⚠ Fair: 2.0-5.0 (acceptable)\n'
             '✗ Poor: <2.0 (weak recovery)'),
        ]
        
        self.perf_table.setRowCount(len(metrics))
        for row, (metric, value, rating, tooltip) in enumerate(metrics):
            item_metric = self._create_item(metric, align_left=True)
            item_metric.setToolTip(tooltip)
            self.perf_table.setItem(row, 0, item_metric)
            self.perf_table.setItem(row, 1, self._create_item(value))
            self.perf_table.setItem(row, 2, self._create_item(rating))
        
        perf_layout.addWidget(self.perf_table)
        perf_group.setLayout(perf_layout)
        
        return perf_group
    
    def _create_risk_group(self) -> QGroupBox:
        """Create risk metrics group"""
        # Risk metrics table
        risk_group = QGroupBox("⚠️ Risk Metrics")
        risk_group.setStyleSheet(get_groupbox_header_stylesheet())
        
        risk_layout = QVBoxLayout()
        risk_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create risk table with Recommendations column
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(4)
        self.risk_table.setHorizontalHeaderLabels(['Metric', 'Value', 'Status', 'Recommendation'])
        
        # Use centralized table stylesheet (ZERO hardcoded styles)
        self.risk_table.setStyleSheet(get_table_stylesheet())
        
        self.risk_table.setAlternatingRowColors(True)
        self.risk_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.risk_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.risk_table.setSortingEnabled(True)  # Excel-like sorting
        self.risk_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.risk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.risk_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.risk_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.risk_table.setColumnWidth(0, 180)  # Metric name
        self.risk_table.setColumnWidth(1, 120)  # Value column
        self.risk_table.setColumnWidth(2, 100)  # Status column
        # Column 3 (Recommendation) stretches to fill remaining space
        self.risk_table.verticalHeader().setVisible(False)
        
        # Populate with risk metrics with institutional-grade tooltips
        risk_metrics = [
            ('Max Drawdown %', '0.00%', '-',
             'Maximum Drawdown Percentage\n\n'
             'Largest peak-to-trough decline as % of capital.\n\n'
             'Calculation:\n'
             'Max DD% = (Max DD$ / Starting Capital) × 100\n\n'
             'Example:\n'
             '$10,000 capital → $2,000 drawdown = 20% DD\n\n'
             'Interpretation:\n'
             '• Measures maximum pain endured\n'
             '• Critical for position sizing\n'
             '• Expect 2-3x worse in live trading\n\n'
             'Institutional Limits:\n'
             '✓ Good: <10% (conservative)\n'
             '⚠ Monitor: 10-20% (standard)\n'
             '✗ High Risk: >20% (aggressive)'),
            
            ('Max Drawdown Duration', '0 days', '-',
             'Maximum Drawdown Duration\n\n'
             'Longest time to recover from a drawdown.\n\n'
             'Measures:\n'
             '• Days from peak to new peak\n'
             '• Psychological endurance required\n'
             '• Strategy resilience\n\n'
             'Interpretation:\n'
             '• Shorter = Faster recovery\n'
             '• Longer = More psychological stress\n'
             '• Critical for trader psychology\n\n'
             'Institutional Tolerance:\n'
             '✓ Good: <30 days (quick recovery)\n'
             '⚠ Monitor: 30-90 days (moderate)\n'
             '✗ Concern: >90 days (prolonged)'),
            
            ('Value at Risk (95%)', '$0.00', '-',
             'Value at Risk - 95th Percentile\n\n'
             'Maximum expected loss in 95% of cases.\n\n'
             'Calculation:\n'
             'VaR(95%) = 5th percentile of P&L distribution\n\n'
             'Example:\n'
             'VaR = -$500 means:\n'
             '• 95% of trades lose <$500\n'
             '• 5% of trades lose >$500\n\n'
             'Interpretation:\n'
             '• Risk management tool\n'
             '• Position sizing input\n'
             '• Regulatory requirement for institutions\n\n'
             'Use For:\n'
             '• Setting position limits\n'
             '• Capital requirements\n'
             '• Risk budgeting'),
            
            ('Expected Shortfall', '$0.00', '-',
             'Expected Shortfall (Conditional VaR)\n\n'
             'Average loss when VaR is exceeded.\n\n'
             'Calculation:\n'
             'ES = Average of losses beyond VaR threshold\n\n'
             'Example:\n'
             '• VaR(95%) = -$500\n'
             '• ES = -$800 (avg of worst 5% losses)\n\n'
             'Interpretation:\n'
             '• Tail risk measurement\n'
             '• "What if VaR is breached?"\n'
             '• More conservative than VaR\n\n'
             'Institutional Use:\n'
             '• Stress testing\n'
             '• Capital allocation\n'
             '• Risk limit setting\n'
             '• Basel III compliance'),
            
            ('Sortino Ratio', '0.0000', '-',
             'Sortino Ratio (Downside Risk-Adjusted Return)\n\n'
             'Like Sharpe, but only penalizes downside volatility.\n\n'
             'Calculation:\n'
             'Sortino = Avg Return / Downside Deviation\n\n'
             'Difference from Sharpe:\n'
             '• Sharpe: Penalizes all volatility (up & down)\n'
             '• Sortino: Only penalizes downside volatility\n'
             '• Better for asymmetric strategies\n\n'
             'Interpretation:\n'
             '• Higher = Better downside-adjusted returns\n'
             '• Preferred by hedge funds\n'
             '• More realistic for active strategies\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: ≥2.0 (excellent)\n'
             '⚠ Monitor: 1.0-2.0 (acceptable)\n'
             '✗ Poor: <1.0 (poor downside protection)'),
            
            ('Calmar Ratio', '0.00', '-',
             'Calmar Ratio (Return / Max Drawdown)\n\n'
             'Annual return divided by max drawdown.\n\n'
             'Calculation:\n'
             'Calmar = Annual Return% / Max Drawdown%\n\n'
             'Example:\n'
             '20% annual return / 10% max DD = 2.0\n\n'
             'Interpretation:\n'
             '• Measures return per unit of drawdown risk\n'
             '• Higher = Better drawdown-adjusted returns\n'
             '• Popular in managed futures industry\n\n'
             'Institutional Benchmark:\n'
             '✓ Good: ≥3.0 (excellent)\n'
             '⚠ Monitor: 1.0-3.0 (acceptable)\n'
             '✗ Poor: <1.0 (poor drawdown management)'),
            
            ('Max Consecutive Losses', '0', '-',
             'Maximum Consecutive Losing Trades\n\n'
             'Longest losing streak experienced.\n\n'
             'Psychological Impact:\n'
             '• Tests trader discipline\n'
             '• Indicates when to reduce size\n'
             '• Stress testing metric\n\n'
             'Interpretation:\n'
             '• Shorter = More consistent\n'
             '• Longer = Higher psychological stress\n'
             '• Prepare for 2x in live trading\n\n'
             'Risk Management:\n'
             '✓ Good: ≤3 (high consistency)\n'
             '⚠ Monitor: 4-5 (normal variance)\n'
             '✗ Concern: >5 (review strategy)'),
            
            ('Max Consecutive Wins', '0', '-',
             'Maximum Consecutive Winning Trades\n\n'
             'Longest winning streak experienced.\n\n'
             'Analysis:\n'
             '• If >>average: Watch for overconfidence\n'
             '• Prepare for regression to mean\n'
             '• Don\'t increase risk after wins\n\n'
             'Interpretation:\n'
             '• Shows best-case scenarios\n'
             '• Balance with max consecutive losses\n'
             '• Don\'t size up during streaks\n\n'
             'Behavioral Warning:\n'
             '⚠ Long win streaks can lead to:\n'
             '• Overconfidence\n'
             '• Increased position sizing\n'
             '• Complacency in risk management'),
            
            ('Average Drawdown', '$0.00', '-',
             'Average Drawdown\n\n'
             'Mean of all drawdown periods.\n\n'
             'Calculation:\n'
             'Avg DD = Sum of all drawdowns / Count\n\n'
             'Interpretation:\n'
             '• Typical drawdown experience\n'
             '• More realistic than max drawdown\n'
             '• Better for regular expectation setting\n\n'
             'Use For:\n'
             '• Position sizing baseline\n'
             '• Psychological preparation\n'
             '• Capital requirements\n\n'
             'Guideline:\n'
             '• Avg DD typically 30-50% of Max DD\n'
             '• Prepare for this regularly\n'
             '• Don\'t panic at average levels'),
            
            ('Standard Deviation', '$0.00', '-',
             'Standard Deviation of Returns\n\n'
             'Volatility of P&L distribution.\n\n'
             'Calculation:\n'
             'σ = √(Σ(Return - Mean)² / N)\n\n'
             'Interpretation:\n'
             '• Higher = More volatile returns\n'
             '• Lower = More consistent returns\n'
             '• Used in Sharpe Ratio denominator\n\n'
             'Normal Distribution:\n'
             '• 68% of trades within ±1σ\n'
             '• 95% of trades within ±2σ\n'
             '• 99.7% of trades within ±3σ\n\n'
             'Risk Management:\n'
             '• Position sizing input\n'
             '• Volatility targeting\n'
             '• Risk parity allocation'),
            
            ('Downside Deviation', '$0.00', '-',
             'Downside Deviation (Semi-Deviation)\n\n'
             'Standard deviation of negative returns only.\n\n'
             'Calculation:\n'
             'DD = √(Σ(Negative Returns)² / N)\n\n'
             'Difference from Std Dev:\n'
             '• Std Dev: Includes all returns (up & down)\n'
             '• Downside Dev: Only negative returns\n'
             '• More relevant for risk measurement\n\n'
             'Interpretation:\n'
             '• Lower = Less downside volatility\n'
             '• Used in Sortino Ratio\n'
             '• Better risk measure for asymmetric returns\n\n'
             'Institutional Preference:\n'
             '• Preferred over std dev for risk\n'
             '• Separates good volatility from bad\n'
             '• More conservative risk measure'),
            
            ('Ulcer Index', '0.00', '-',
             'Ulcer Index (Drawdown Stress Measure)\n\n'
             'Measures depth and duration of drawdowns.\n\n'
             'Calculation:\n'
             'UI = √(Σ(Drawdown%)² / N)\n\n'
             'What It Measures:\n'
             '• Investor stress/discomfort\n'
             '• Combines DD depth + duration\n'
             '• More comprehensive than max DD\n\n'
             'Interpretation:\n'
             '• Lower = Less stressful equity curve\n'
             '• Higher = More painful drawdowns\n'
             '• Alternative to standard deviation\n\n'
             'Behavioral Finance:\n'
             '• Accounts for psychological pain\n'
             '• Better for understanding trader stress\n'
             '• Used to compare strategies\n\n'
             'Target:\n'
             '✓ Good: <5% (smooth equity curve)\n'
             '⚠ Monitor: 5-10% (normal variance)\n'
             '✗ High: >10% (stressful drawdowns)'),
        ]
        
        self.risk_table.setRowCount(len(risk_metrics))
        for row, (metric, value, status, tooltip) in enumerate(risk_metrics):
            item_metric = self._create_item(metric, align_left=True)
            item_metric.setToolTip(tooltip)
            self.risk_table.setItem(row, 0, item_metric)
            self.risk_table.setItem(row, 1, self._create_item(value))
            self.risk_table.setItem(row, 2, self._create_item(status))
        
        risk_layout.addWidget(self.risk_table)
        risk_group.setLayout(risk_layout)
        
        return risk_group
    
    def _create_comparison_tab(self) -> QWidget:
        """Create parameter comparison tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Comparison table
        comp_group = QGroupBox("Configuration Comparison")
        comp_group.setStyleSheet(get_groupbox_header_stylesheet())
        
        comp_layout = QVBoxLayout()
        comp_layout.setContentsMargins(10, 15, 10, 10)
        
        # Status label
        self.comp_status_label = QLabel("No comparison data available. Run optimization to compare configurations.")
        self.comp_status_label.setStyleSheet(get_label_style('muted'))
        self.comp_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        comp_layout.addWidget(self.comp_status_label)
        
        # Create comparison table
        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(4)
        self.comp_table.setHorizontalHeaderLabels(['Parameter', 'Original', 'Optimized', 'Change'])
        
        # Use centralized table stylesheet (ZERO hardcoded styles)
        self.comp_table.setStyleSheet(get_table_stylesheet())
        
        self.comp_table.setAlternatingRowColors(True)
        self.comp_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.comp_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.comp_table.setSortingEnabled(True)  # Excel-like sorting
        self.comp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.comp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.comp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.comp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.comp_table.setColumnWidth(1, 120)
        self.comp_table.setColumnWidth(2, 120)
        self.comp_table.setColumnWidth(3, 100)
        self.comp_table.verticalHeader().setVisible(False)
        self.comp_table.setVisible(False)  # Hidden until data available
        
        comp_layout.addWidget(self.comp_table)
        comp_group.setLayout(comp_layout)
        layout.addWidget(comp_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_control_bar(self) -> QHBoxLayout:
        """Create control buttons at bottom"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Status info
        self.status_label = QLabel("Status: <b>No data</b>")
        self.status_label.setStyleSheet(get_label_style())
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        refresh_btn.setFixedSize(130, 42)
        refresh_btn.clicked.connect(self._refresh_metrics)
        refresh_btn.setToolTip("Refresh metrics display")
        layout.addWidget(refresh_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.setFixedSize(130, 42)
        export_btn.clicked.connect(self._export_metrics)
        export_btn.setToolTip("Export metrics to CSV")
        layout.addWidget(export_btn)
        
        return layout
    
    def _create_item(self, text: str, align_left: bool = False) -> QTableWidgetItem:
        """Create table item with proper alignment"""
        item = QTableWidgetItem(text)
        if align_left:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
    
    def update_metrics(self, metrics: Dict) -> None:
        """
        Update metrics display.
        
        Args:
            metrics: Dictionary with performance metrics
        """
        self.current_metrics = metrics
        self._update_performance_table()
        self._update_risk_table()
        self.status_label.setText("Status: <b>Data loaded</b>")
        self.metrics_updated.emit(metrics)
    
    def _update_performance_table(self) -> None:
        """Update performance metrics table"""
        if not self.current_metrics:
            return
        
        # Update each row with actual data
        metrics_map = {
            0: ('total_pnl', lambda x: f"${float(x):,.2f}"),
            1: ('total_return', lambda x: f"{float(x):.2f}%"),
            2: ('sharpe_ratio', lambda x: f"{float(x):.4f}"),
            3: ('win_rate', lambda x: f"{float(x):.2f}%"),
            4: ('profit_factor', lambda x: f"{float(x):.3f}"),
            5: ('max_drawdown', lambda x: f"${float(x):,.2f}"),
            6: ('total_trades', lambda x: str(int(x))),
            7: ('avg_trade_pnl', lambda x: f"${float(x):,.2f}"),
            8: ('avg_win', lambda x: f"${float(x):,.2f}"),
            9: ('avg_loss', lambda x: f"${float(x):,.2f}"),
            10: ('largest_win', lambda x: f"${float(x):,.2f}"),
            11: ('largest_loss', lambda x: f"${float(x):,.2f}"),
            12: ('risk_reward_ratio', lambda x: f"{float(x):.2f}"),
            13: ('recovery_factor', lambda x: f"{float(x):.2f}"),
        }
        
        for row, (key, formatter) in metrics_map.items():
            if key in self.current_metrics:
                value = self.current_metrics[key]
                formatted = formatter(value)
                item = self._create_item(formatted)
                
                # Color code certain metrics
                if key in ['total_pnl', 'avg_trade_pnl']:
                    if float(value) > 0:
                        item.setForeground(QColor(get_color('success')))
                    elif float(value) < 0:
                        item.setForeground(QColor(get_color('error')))
                
                self.perf_table.setItem(row, 1, item)
                
                # Set rating
                rating = self._get_rating(key, value)
                rating_item = self._create_item(rating)
                if rating == '✓ Good':
                    rating_item.setForeground(QColor(get_color('success')))
                elif rating == '⚠ Fair':
                    rating_item.setForeground(QColor(get_color('warning')))
                elif rating == '✗ Poor':
                    rating_item.setForeground(QColor(get_color('error')))
                self.perf_table.setItem(row, 2, rating_item)
    
    def _update_risk_table(self) -> None:
        """Update risk metrics table"""
        if not self.current_metrics:
            return
        
        # Update each row with actual risk data
        risk_metrics_map = {
            0: ('max_drawdown_pct', lambda x: f"{float(x):.2f}%"),
            1: ('max_drawdown_duration', lambda x: f"{int(x)} days"),
            2: ('var_95', lambda x: f"${float(x):,.2f}"),
            3: ('expected_shortfall', lambda x: f"${float(x):,.2f}"),
            4: ('sortino_ratio', lambda x: f"{float(x):.4f}"),
            5: ('calmar_ratio', lambda x: f"{float(x):.2f}"),
            6: ('max_consecutive_losses', lambda x: str(int(x))),
            7: ('max_consecutive_wins', lambda x: str(int(x))),
            8: ('avg_drawdown', lambda x: f"${float(x):,.2f}"),
            9: ('std_deviation', lambda x: f"${float(x):,.2f}"),
            10: ('downside_deviation', lambda x: f"${float(x):,.2f}"),
            11: ('ulcer_index', lambda x: f"{float(x):.2f}"),
        }
        
        for row, (key, formatter) in risk_metrics_map.items():
            if key in self.current_metrics:
                value = self.current_metrics[key]
                formatted = formatter(value)
                item = self._create_item(formatted)
                
                # Color code certain risk metrics
                if key == 'max_drawdown_pct':
                    if float(value) < 10.0:
                        item.setForeground(QColor(get_color('success')))
                    elif float(value) < 20.0:
                        item.setForeground(QColor(get_color('warning')))
                    else:
                        item.setForeground(QColor(get_color('error')))
                
                self.risk_table.setItem(row, 1, item)
                
                # Set status
                status = self._get_risk_status(key, value)
                status_item = self._create_item(status)
                if status == '✓ Good':
                    status_item.setForeground(QColor(get_color('success')))
                elif status == '⚠ Monitor':
                    status_item.setForeground(QColor(get_color('warning')))
                elif status == '✗ High':
                    status_item.setForeground(QColor(get_color('error')))
                self.risk_table.setItem(row, 2, status_item)
    
    def _get_risk_status(self, metric_key: str, value) -> str:
        """Get status for risk metric value"""
        try:
            val = float(value)
            
            if metric_key == 'max_drawdown_pct':
                if val < 10.0:
                    return '✓ Good'
                elif val < 20.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'max_drawdown_duration':
                val_int = int(val)
                if val_int < 30:
                    return '✓ Good'
                elif val_int < 90:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'var_95':
                # VaR should be reasonable (less loss = better)
                abs_val = abs(val)
                if abs_val < 100.0:
                    return '✓ Good'
                elif abs_val < 200.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'expected_shortfall':
                # ES should be controlled (less loss = better)
                abs_val = abs(val)
                if abs_val < 150.0:
                    return '✓ Good'
                elif abs_val < 300.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'sortino_ratio':
                if val >= 2.0:
                    return '✓ Good'
                elif val >= 1.0:
                    return '⚠ Monitor'
                else:
                    return '✗ Poor'
            elif metric_key == 'calmar_ratio':
                if val >= 3.0:
                    return '✓ Good'
                elif val >= 1.0:
                    return '⚠ Monitor'
                else:
                    return '✗ Poor'
            elif metric_key == 'max_consecutive_losses':
                val_int = int(val)
                if val_int <= 3:
                    return '✓ Good'
                elif val_int <= 5:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'max_consecutive_wins':
                val_int = int(val)
                if val_int >= 3:
                    return '✓ Good'
                elif val_int >= 2:
                    return '⚠ Monitor'
                else:
                    return '✗ Low'
            elif metric_key == 'avg_drawdown':
                # Average DD should be reasonable
                abs_val = abs(val)
                if abs_val < 150.0:
                    return '✓ Good'
                elif abs_val < 300.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'std_deviation':
                # Lower volatility is better
                if val < 50.0:
                    return '✓ Good'
                elif val < 100.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'downside_deviation':
                # Lower downside volatility is better
                if val < 40.0:
                    return '✓ Good'
                elif val < 80.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            elif metric_key == 'ulcer_index':
                # Lower UI = less stress
                if val < 5.0:
                    return '✓ Good'
                elif val < 10.0:
                    return '⚠ Monitor'
                else:
                    return '✗ High'
            else:
                return '-'
        except:
            return '-'
    
    def _get_rating(self, metric_key: str, value) -> str:
        """Get rating for metric value"""
        try:
            val = float(value)
            
            if metric_key == 'total_pnl':
                if val > 0:
                    return '✓ Good'
                elif val == 0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'total_return':
                if val >= 15.0:
                    return '✓ Good'
                elif val >= 8.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'sharpe_ratio':
                if val >= 2.0:
                    return '✓ Good'
                elif val >= 1.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'win_rate':
                if val >= 60.0:
                    return '✓ Good'
                elif val >= 50.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'profit_factor':
                if val >= 2.0:
                    return '✓ Good'
                elif val >= 1.5:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'max_drawdown':
                # For drawdown, lower is better (it's negative impact)
                # This is in dollars, so context matters
                return '-'  # Better to check max_drawdown_pct in risk metrics
            elif metric_key == 'total_trades':
                val_int = int(val)
                if val_int >= 100:
                    return '✓ Good'
                elif val_int >= 30:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'avg_trade_pnl':
                if val > 10.0:
                    return '✓ Good'
                elif val > 0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'avg_win':
                # Larger wins are better
                if val > 50.0:
                    return '✓ Good'
                elif val > 20.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'avg_loss':
                # Smaller losses are better (absolute value)
                abs_val = abs(val)
                if abs_val < 30.0:
                    return '✓ Good'
                elif abs_val < 60.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'largest_win':
                # Should not dominate total P&L
                if val > 0 and val < 200:
                    return '✓ Good'
                elif val >= 200:
                    return '⚠ Fair'  # Might be outlier dependency
                else:
                    return '-'
            elif metric_key == 'largest_loss':
                # Should be controlled
                abs_val = abs(val)
                if abs_val < 80.0:
                    return '✓ Good'
                elif abs_val < 150.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'risk_reward_ratio':
                if val >= 2.0:
                    return '✓ Good'
                elif val >= 1.5:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            elif metric_key == 'recovery_factor':
                if val >= 5.0:
                    return '✓ Good'
                elif val >= 2.0:
                    return '⚠ Fair'
                else:
                    return '✗ Poor'
            else:
                return '-'
        except:
            return '-'
    
    def _refresh_metrics(self) -> None:
        """Refresh metrics display"""
        if self.current_metrics:
            self.update_metrics(self.current_metrics)
    
    def _export_metrics(self) -> None:
        """Export metrics to CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"metrics_export_{timestamp}.csv"
        
        try:
            with open(filename, 'w') as f:
                f.write("Metric,Value,Rating\n")
                
                for row in range(self.perf_table.rowCount()):
                    metric = self.perf_table.item(row, 0).text()
                    value = self.perf_table.item(row, 1).text()
                    rating = self.perf_table.item(row, 2).text()
                    f.write(f"{metric},{value},{rating}\n")
            
            print(f"✅ Metrics exported to {filename}")
            
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return self.current_metrics.copy()
