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
from PyQt5.QtWidgets import QApplication

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

# Import recommendation engine for intelligent recommendations
from src.optimizer_v3.core.recommendation_engine import RecommendationEngine, Recommendation
from src.detectors.building_blocks.registry import BlockRegistry


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
        
        # Intelligent recommendation engine (initialized lazily)
        self.rec_engine: Optional[RecommendationEngine] = None
        self.recommendation_cache: Dict[str, Optional[Recommendation]] = {}  # Cache recommendation objects
        
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
        
        # STACKED LAYOUT (Design v2): Performance on top, Risk below - FULL WIDTH TABLES
        
        # Performance Metrics (top, full width)
        perf_group = self._create_performance_group()
        layout.addWidget(perf_group)
        
        # Risk Metrics (bottom, full width)
        risk_group = self._create_risk_group()
        layout.addWidget(risk_group)
        
        # Control buttons at bottom
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        self.setLayout(layout)
    
    def _create_performance_group(self) -> QGroupBox:
        """Create performance metrics group - Design v2 with checkboxes"""
        # Performance metrics table
        perf_group = QGroupBox("📊 Performance Metrics")
        perf_group.setStyleSheet(get_groupbox_header_stylesheet())
        
        perf_layout = QVBoxLayout()
        perf_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create metrics table with Recommendations + CHECKBOX column (Design v2)
        # Checkbox is ON THE RIGHT (after recommendation)
        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(5)  # Added checkbox column at END
        self.perf_table.setHorizontalHeaderLabels(['Metric', 'Value', 'Rating', 'Recommendation', '☐'])
        
        # Table styling
        # Use centralized table stylesheet (ZERO hardcoded styles)
        self.perf_table.setStyleSheet(get_table_stylesheet())
        
        self.perf_table.setAlternatingRowColors(True)
        self.perf_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # FIXED: Multi-row selection (Ctrl+Click, Shift+Click)
        self.perf_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.perf_table.setSortingEnabled(False)  # Disable sorting (checkboxes break it)
        
        # Column widths: Metric | Value | Rating | Recommendation | Checkbox
        # READABLE widths - we have FULL WIDTH now (stacked layout)
        self.perf_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Metric
        self.perf_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Value
        self.perf_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Rating
        self.perf_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Recommendation (takes remaining space)
        self.perf_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Checkbox
        
        self.perf_table.setColumnWidth(0, 350)  # Metric name (VERY WIDE per user request)
        self.perf_table.setColumnWidth(1, 350)  # Value column (VERY WIDE per user request)
        self.perf_table.setColumnWidth(2, 350)  # Rating column (VERY WIDE per user request)
        # Column 3 (Recommendation) stretches to fill remaining width
        self.perf_table.setColumnWidth(4, 50)   # Checkbox column
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
            # Column 0: Metric name
            item_metric = self._create_item(metric, align_left=True)
            item_metric.setToolTip(tooltip)
            self.perf_table.setItem(row, 0, item_metric)
            
            # Column 1: Value
            self.perf_table.setItem(row, 1, self._create_item(value))
            
            # Column 2: Rating
            self.perf_table.setItem(row, 2, self._create_item(rating))
            
            # Column 3: Recommendation (populated later by _update_performance_table)
            
            # Column 4: Checkbox (AT THE END, on the right)
            # Add empty string to make checkbox render properly
            checkbox_item = QTableWidgetItem("")
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            checkbox_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.perf_table.setItem(row, 4, checkbox_item)
        
        # Connect checkbox state changes to update button
        self.perf_table.itemChanged.connect(self._on_checkbox_changed)
        
        perf_layout.addWidget(self.perf_table)
        perf_group.setLayout(perf_layout)
        
        return perf_group
    
    def _create_risk_group(self) -> QGroupBox:
        """Create risk metrics group - Design v2 with checkboxes"""
        # Risk metrics table
        risk_group = QGroupBox("⚠️ Risk Metrics")
        risk_group.setStyleSheet(get_groupbox_header_stylesheet())
        
        risk_layout = QVBoxLayout()
        risk_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create risk table with Recommendations + CHECKBOX column (Design v2)
        # Checkbox is ON THE RIGHT (after recommendation)
        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(5)  # Added checkbox column at END
        self.risk_table.setHorizontalHeaderLabels(['Metric', 'Value', 'Status', 'Recommendation', '☐'])
        
        # Use centralized table stylesheet (ZERO hardcoded styles)
        self.risk_table.setStyleSheet(get_table_stylesheet())
        
        self.risk_table.setAlternatingRowColors(True)
        self.risk_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # FIXED: Multi-row selection (Ctrl+Click, Shift+Click)
        self.risk_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.risk_table.setSortingEnabled(False)  # Disable sorting (checkboxes break it)
        
        # Column widths: Metric | Value | Status | Recommendation | Checkbox
        # READABLE widths - we have FULL WIDTH now (stacked layout)
        self.risk_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Metric
        self.risk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Value
        self.risk_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Status
        self.risk_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Recommendation (takes remaining space)
        self.risk_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Checkbox
        
        self.risk_table.setColumnWidth(0, 350)  # Metric name (VERY WIDE per user request)
        self.risk_table.setColumnWidth(1, 350)  # Value column (VERY WIDE per user request)
        self.risk_table.setColumnWidth(2, 350)  # Status column (VERY WIDE per user request)
        # Column 3 (Recommendation) stretches to fill remaining width
        self.risk_table.setColumnWidth(4, 50)   # Checkbox column
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
            # Column 0: Metric name
            item_metric = self._create_item(metric, align_left=True)
            item_metric.setToolTip(tooltip)
            self.risk_table.setItem(row, 0, item_metric)
            
            # Column 1: Value
            self.risk_table.setItem(row, 1, self._create_item(value))
            
            # Column 2: Status
            self.risk_table.setItem(row, 2, self._create_item(status))
            
            # Column 3: Recommendation (populated later by _update_risk_table)
            
            # Column 4: Checkbox (AT THE END, on the right)
            # Add empty string to make checkbox render properly
            checkbox_item = QTableWidgetItem("")
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            checkbox_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.risk_table.setItem(row, 4, checkbox_item)
        
        # Connect checkbox state changes to update button
        self.risk_table.itemChanged.connect(self._on_checkbox_changed)
        
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
        """Create control buttons at bottom - Design v2 with selection controls"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # Status info
        self.status_label = QLabel("Status: <b>No data</b>")
        self.status_label.setStyleSheet(get_label_style())
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Copy All button (matches Trades tab naming)
        copy_btn = QPushButton("📋 Copy All")
        copy_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_btn.setFixedSize(170, 52)
        copy_btn.clicked.connect(self._copy_all_metrics)
        copy_btn.setToolTip("Copy all metrics to clipboard")
        layout.addWidget(copy_btn)
        
        # Copy Selection button (matches Trades tab naming)
        copy_sel_btn = QPushButton("📋 Copy Selection")
        copy_sel_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_sel_btn.setFixedSize(260, 52)
        copy_sel_btn.clicked.connect(self._copy_selected_metrics)
        copy_sel_btn.setToolTip("Copy selected rows to clipboard")
        layout.addWidget(copy_sel_btn)
        
        # Select All button
        select_all_btn = QPushButton("☑ Select All")
        select_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        select_all_btn.setFixedSize(170, 52)
        select_all_btn.clicked.connect(self._select_all_recommendations)
        select_all_btn.setToolTip("Select all recommendations for application")
        layout.addWidget(select_all_btn)
        
        # Clear All button
        clear_all_btn = QPushButton("☐ Clear All")
        clear_all_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_all_btn.setFixedSize(170, 52)
        clear_all_btn.clicked.connect(self._clear_all_recommendations)
        clear_all_btn.setToolTip("Deselect all recommendations")
        layout.addWidget(clear_all_btn)
        
        # Apply Recommendation(s) button (Design v2 - PRIMARY ACTION)
        self.apply_btn = QPushButton("💡 Apply Recommendation(s)")
        self.apply_btn.setStyleSheet(get_primary_button_stylesheet(compact=False))  # Prominent
        self.apply_btn.setFixedSize(380, 52)
        self.apply_btn.clicked.connect(self._apply_selected_recommendations)
        self.apply_btn.setEnabled(False)  # Disabled until selections made
        self.apply_btn.setToolTip("Apply selected recommendations to strategy configuration")
        layout.addWidget(self.apply_btn)
        
        # Auto-Retest checkbox
        self.auto_retest_check = QPushButton("🔄 Auto-Retest")
        self.auto_retest_check.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self.auto_retest_check.setCheckable(True)
        self.auto_retest_check.setChecked(False)
        self.auto_retest_check.setFixedSize(200, 52)
        self.auto_retest_check.setToolTip(
            "Auto-Retest After Applying Recommendations\n\n"
            "When enabled:\n"
            "• Recommendations are applied to config\n"
            "• Backtest runs automatically\n"
            "• Results compared with original\n\n"
            "When disabled:\n"
            "• Recommendations applied only\n"
            "• Manual retest required"
        )
        layout.addWidget(self.auto_retest_check)
        
        # Export button (moved to end)
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.setFixedSize(140, 52)  # FIXED: Wider for consistency
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
        
        # Initialize recommendation engine on first use
        if self.rec_engine is None:
            self._initialize_recommendation_engine()
        
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
                
                self.perf_table.setItem(row, 1, item)  # Column 1: Value
                
                # Set rating
                rating = self._get_rating(key, value)
                rating_item = self._create_item(rating)
                if rating == '✓ Good':
                    rating_item.setForeground(QColor(get_color('success')))
                elif rating == '⚠ Fair':
                    rating_item.setForeground(QColor(get_color('warning')))
                elif rating == '✗ Poor':
                    rating_item.setForeground(QColor(get_color('error')))
                self.perf_table.setItem(row, 2, rating_item)  # Column 2: Rating
                
                # Generate intelligent recommendation
                rec_obj = None
                rec_text = ""
                
                if self.rec_engine and rating in ['⚠ Fair', '✗ Poor']:
                    rec_obj = self.rec_engine.generate_recommendation(key, float(value), rating)
                    if rec_obj:
                        rec_text = self.rec_engine.format_recommendation_text(rec_obj)
                        # Cache the recommendation object
                        self.recommendation_cache[f"perf_{row}"] = rec_obj
                    else:
                        # No intelligent recommendation available - use generic
                        rec_text = self._get_generic_recommendation(key, value, rating)
                        self.recommendation_cache[f"perf_{row}"] = None
                else:
                    self.recommendation_cache[f"perf_{row}"] = None
                
                rec_item = self._create_item(rec_text, align_left=True)
                self.perf_table.setItem(row, 3, rec_item)  # Column 3: Recommendation
                
                # Enable/disable checkbox - ONLY for intelligent recommendations
                checkbox_item = self.perf_table.item(row, 4)
                if checkbox_item:
                    # Only enable if we have an intelligent recommendation
                    is_actionable = rec_obj is not None and self._is_intelligent_recommendation(rec_text)
                    if is_actionable:
                        checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    else:
                        # Disable checkbox for non-actionable items
                        checkbox_item.setFlags(Qt.ItemFlag.NoItemFlags)
                        checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
    def _update_risk_table(self) -> None:
        """Update risk metrics table"""
        if not self.current_metrics:
            return
        
        # Initialize recommendation engine on first use
        if self.rec_engine is None:
            self._initialize_recommendation_engine()
        
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
                
                self.risk_table.setItem(row, 1, item)  # Column 1: Value
                
                # Set status
                status = self._get_risk_status(key, value)
                status_item = self._create_item(status)
                if status == '✓ Good':
                    status_item.setForeground(QColor(get_color('success')))
                elif status == '⚠ Monitor':
                    status_item.setForeground(QColor(get_color('warning')))
                elif status == '✗ High' or status == '✗ Poor':
                    status_item.setForeground(QColor(get_color('error')))  # RED for Poor/High
                self.risk_table.setItem(row, 2, status_item)  # Column 2: Status
                
                # Generate intelligent recommendation for risk metrics
                rec_obj = None
                rec_text = ""
                
                if self.rec_engine and status in ['⚠ Monitor', '✗ High', '✗ Poor']:
                    rec_obj = self.rec_engine.generate_recommendation(key, float(value), status)
                    if rec_obj:
                        rec_text = self.rec_engine.format_recommendation_text(rec_obj)
                        # Cache the recommendation object
                        self.recommendation_cache[f"risk_{row}"] = rec_obj
                    else:
                        # No intelligent recommendation available - use generic
                        rec_text = self._get_risk_recommendation_generic(key, value, status)
                        self.recommendation_cache[f"risk_{row}"] = None
                else:
                    self.recommendation_cache[f"risk_{row}"] = None
                
                rec_item = self._create_item(rec_text, align_left=True)
                self.risk_table.setItem(row, 3, rec_item)  # Column 3: Recommendation
                
                # Enable/disable checkbox - ONLY for intelligent recommendations
                checkbox_item = self.risk_table.item(row, 4)
                if checkbox_item:
                    # Only enable if we have an intelligent recommendation
                    is_actionable = rec_obj is not None and self._is_intelligent_recommendation(rec_text)
                    if is_actionable:
                        checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    else:
                        # Disable checkbox for non-actionable items
                        checkbox_item.setFlags(Qt.ItemFlag.NoItemFlags)
                        checkbox_item.setCheckState(Qt.CheckState.Unchecked)
    
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
    
    def _initialize_recommendation_engine(self) -> None:
        """Initialize intelligent recommendation engine"""
        try:
            # Get current strategy configuration
            strategy_config = self._get_current_strategy_config()
            self.rec_engine = RecommendationEngine(strategy_config, BlockRegistry)
            print("✅ Intelligent recommendation engine initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize recommendation engine: {str(e)}")
            self.rec_engine = None
    
    def _get_current_strategy_config(self):
        """Get current strategy config from orchestrator"""
        try:
            # Access main window orchestrator
            main_window = self.window()
            if hasattr(main_window, 'orchestrator'):
                return main_window.orchestrator.get_current_config()
        except Exception as e:
            print(f"⚠️ Could not access strategy config: {str(e)}")
        return None
    
    def _is_intelligent_recommendation(self, rec_text: str) -> bool:
        """Check if recommendation is intelligent (from engine) vs generic"""
        # Intelligent recommendations start with "Add '"
        return rec_text.startswith("Add '")
    
    def _get_generic_recommendation(self, metric_key: str, value, rating: str) -> str:
        """Generate actionable recommendation text for performance metrics"""
        try:
            val = float(value)
            
            if rating == '✓ Good':
                return ""  # No recommendation needed - performance is good
            elif rating == '⚠ Fair':
                if metric_key == 'total_pnl':
                    return "Positive but could be improved - optimize entry/exit rules"
                elif metric_key == 'total_return':
                    return "Matches market - consider improving R:R ratio"
                elif metric_key == 'sharpe_ratio':
                    return "Acceptable - reduce volatility or improve consistency"
                elif metric_key == 'win_rate':
                    return "Average - balance with higher R:R ratio"
                elif metric_key == 'profit_factor':
                    return "Profitable but marginal - tighten entry criteria"
                elif metric_key == 'avg_trade_pnl':
                    return "Positive - increase position size cautiously"
                else:
                    return "Monitor performance - room for improvement"
            elif rating == '✗ Poor':
                if metric_key == 'total_pnl':
                    return "Strategy losing money - review all parameters urgently"
                elif metric_key == 'total_return':
                    return "Underperforming - consider alternative strategies"
                elif metric_key == 'sharpe_ratio':
                    return "Poor risk-adjusted returns - improve or abandon strategy"
                elif metric_key == 'win_rate':
                    if val < 50.0:
                        return "Low win rate - need R:R ≥2.0 to be profitable"
                    else:
                        return "Review entry/exit criteria"
                elif metric_key == 'profit_factor':
                    return "Unprofitable - stop trading this strategy"
                elif metric_key == 'total_trades':
                    return "Insufficient sample size - collect more data before concluding"
                elif metric_key == 'avg_trade_pnl':
                    return "Losing per trade - stop and review strategy completely"
                else:
                    return "Needs immediate attention - review parameters"
            else:
                return "Awaiting more data..."
        except:
            return "Awaiting more data..."
    
    def _get_risk_recommendation_generic(self, metric_key: str, value, status: str) -> str:
        """Generate actionable recommendation text for risk metrics"""
        try:
            val = float(value)
            
            if status == '✓ Good':
                return ""  # No recommendation needed - risk is well-managed
            elif status == '⚠ Monitor':
                if metric_key == 'max_drawdown_pct':
                    return "Drawdown elevated - consider reducing position size"
                elif metric_key == 'max_drawdown_duration':
                    return "Recovery taking time - review strategy resilience"
                elif metric_key == 'var_95':
                    return "Tail risk increasing - tighten stop losses"
                elif metric_key == 'expected_shortfall':
                  return "Worst-case losses growing - review risk limits"
                elif metric_key == 'sortino_ratio':
                    return "Downside volatility high - improve stop loss strategy"
                elif metric_key == 'calmar_ratio':
                    return "Returns not justifying drawdowns - optimize exits"
                elif metric_key == 'max_consecutive_losses':
                    return "Losing streaks lengthening - review entry criteria"
                elif metric_key == 'std_deviation':
                    return "Volatility rising - consider position sizing adjustment"
                elif metric_key == 'ulcer_index':
                    return "Drawdown stress increasing - improve risk management"
                else:
                    return "Monitor closely - risk increasing"
            elif status == '✗ High' or status == '✗ Poor':
                if metric_key == 'max_drawdown_pct':
                    return "CRITICAL: Reduce position size immediately - risk of ruin"
                elif metric_key == 'max_drawdown_duration':
                    return "CONCERN: Recovery too slow - consider strategy change"
                elif metric_key == 'var_95':
                    return "HIGH RISK: Tail losses excessive - tighten all stops"
                elif metric_key == 'expected_shortfall':
                    return "DANGER: Catastrophic loss potential - reduce exposure"
                elif metric_key == 'sortino_ratio':
                    return "POOR: Downside risk not managed - overhaul strategy"
                elif metric_key == 'calmar_ratio':
                    return "POOR: Drawdowns too large for returns - abandon strategy"
                elif metric_key == 'max_consecutive_losses':
                    return "WARNING: Losing streaks too long - halt trading and review"
                elif metric_key == 'std_deviation':
                    return "HIGH: Excessive volatility - reduce positions significantly"
                elif metric_key == 'ulcer_index':
                    return "SEVERE: Unacceptable drawdown stress - stop trading"
                else:
                    return "HIGH RISK: Take immediate corrective action"
            else:
                return "Awaiting more data..."
        except:
            return "Awaiting more data..."
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return self.current_metrics.copy()
    
    def _copy_all_metrics(self) -> None:
        """Copy all metrics to clipboard in tab-delimited format"""
        try:
            # Build tab-delimited text
            lines = []
            
            # Performance Metrics
            lines.append("PERFORMANCE METRICS")
            lines.append("Metric\tValue\tRating\tRecommendation")
            for row in range(self.perf_table.rowCount()):
                metric = self.perf_table.item(row, 0).text() if self.perf_table.item(row, 0) else ""
                value = self.perf_table.item(row, 1).text() if self.perf_table.item(row, 1) else ""
                rating = self.perf_table.item(row, 2).text() if self.perf_table.item(row, 2) else ""
                rec = self.perf_table.item(row, 3).text() if self.perf_table.item(row, 3) else ""
                lines.append(f"{metric}\t{value}\t{rating}\t{rec}")
            
            lines.append("")  # Blank line
            
            # Risk Metrics
            lines.append("RISK METRICS")
            lines.append("Metric\tValue\tStatus\tRecommendation")
            for row in range(self.risk_table.rowCount()):
                metric = self.risk_table.item(row, 0).text() if self.risk_table.item(row, 0) else ""
                value = self.risk_table.item(row, 1).text() if self.risk_table.item(row, 1) else ""
                status = self.risk_table.item(row, 2).text() if self.risk_table.item(row, 2) else ""
                rec = self.risk_table.item(row, 3).text() if self.risk_table.item(row, 3) else ""
                lines.append(f"{metric}\t{value}\t{status}\t{rec}")
            
            # Copy to clipboard
            clipboard_text = "\n".join(lines)
            QApplication.clipboard().setText(clipboard_text)
            
            print(f"✅ Copied all metrics ({len(lines)} lines) to clipboard")
            self.status_label.setText("Status: <b>All metrics copied to clipboard</b>")
            
        except Exception as e:
            print(f"❌ Copy failed: {str(e)}")
            self.status_label.setText(f"Status: <b>Copy failed: {str(e)}</b>")
    
    def _copy_selected_metrics(self) -> None:
        """Copy selected rows to clipboard in tab-delimited format"""
        try:
            lines = []
            
            # Get selected rows from performance table
            perf_selected_rows = set()
            for index in self.perf_table.selectedIndexes():
                perf_selected_rows.add(index.row())
            
            if perf_selected_rows:
                lines.append("PERFORMANCE METRICS")
                lines.append("Metric\tValue\tRating\tRecommendation")
                for row in sorted(perf_selected_rows):
                    metric = self.perf_table.item(row, 0).text() if self.perf_table.item(row, 0) else ""
                    value = self.perf_table.item(row, 1).text() if self.perf_table.item(row, 1) else ""
                    rating = self.perf_table.item(row, 2).text() if self.perf_table.item(row, 2) else ""
                    rec = self.perf_table.item(row, 3).text() if self.perf_table.item(row, 3) else ""
                    lines.append(f"{metric}\t{value}\t{rating}\t{rec}")
                lines.append("")  # Blank line
            
            # Get selected rows from risk table
            risk_selected_rows = set()
            for index in self.risk_table.selectedIndexes():
                risk_selected_rows.add(index.row())
            
            if risk_selected_rows:
                lines.append("RISK METRICS")
                lines.append("Metric\tValue\tStatus\tRecommendation")
                for row in sorted(risk_selected_rows):
                    metric = self.risk_table.item(row, 0).text() if self.risk_table.item(row, 0) else ""
                    value = self.risk_table.item(row, 1).text() if self.risk_table.item(row, 1) else ""
                    status = self.risk_table.item(row, 2).text() if self.risk_table.item(row, 2) else ""
                    rec = self.risk_table.item(row, 3).text() if self.risk_table.item(row, 3) else ""
                    lines.append(f"{metric}\t{value}\t{status}\t{rec}")
            
            if not lines:
                print("⚠️ No rows selected")
                self.status_label.setText("Status: <b>No rows selected</b>")
                return
            
            # Copy to clipboard
            clipboard_text = "\n".join(lines)
            QApplication.clipboard().setText(clipboard_text)
            
            total_selected = len(perf_selected_rows) + len(risk_selected_rows)
            print(f"✅ Copied {total_selected} selected rows to clipboard")
            self.status_label.setText(f"Status: <b>{total_selected} selected rows copied to clipboard</b>")
            
        except Exception as e:
            print(f"❌ Copy failed: {str(e)}")
            self.status_label.setText(f"Status: <b>Copy failed: {str(e)}</b>")
    
    def _select_all_recommendations(self) -> None:
        """Select all recommendation checkboxes"""
        # Select all performance metrics (checkbox is column 4)
        for row in range(self.perf_table.rowCount()):
            item = self.perf_table.item(row, 4)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        
        # Select all risk metrics (checkbox is column 4)
        for row in range(self.risk_table.rowCount()):
            item = self.risk_table.item(row, 4)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        
        # Update apply button
        self._update_apply_button()
    
    def _clear_all_recommendations(self) -> None:
        """Clear all recommendation checkboxes"""
        # Clear all performance metrics (checkbox is column 4)
        for row in range(self.perf_table.rowCount()):
            item = self.perf_table.item(row, 4)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        
        # Clear all risk metrics (checkbox is column 4)
        for row in range(self.risk_table.rowCount()):
            item = self.risk_table.item(row, 4)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        
        # Update apply button
        self._update_apply_button()
    
    def _on_checkbox_changed(self, item: QTableWidgetItem) -> None:
        """Handle checkbox state change"""
        # Only update if it's a checkbox column (column 4)
        if item and item.column() == 4:
            self._update_apply_button()
    
    def _update_apply_button(self) -> None:
        """Update apply button text and enabled state based on selections"""
        # Count selected checkboxes (checkbox is column 4)
        selected_count = 0
        
        # Count performance metrics
        for row in range(self.perf_table.rowCount()):
            item = self.perf_table.item(row, 4)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_count += 1
        
        # Count risk metrics
        for row in range(self.risk_table.rowCount()):
            item = self.risk_table.item(row, 4)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_count += 1
        
        # Update button (show count when >0)
        if selected_count > 0:
            self.apply_btn.setText(f"💡 Apply Recommendation(s) ({selected_count})")
        else:
            self.apply_btn.setText("💡 Apply Recommendation(s)")
        self.apply_btn.setEnabled(selected_count > 0)
    
    def _apply_selected_recommendations(self) -> None:
        """Apply selected recommendations to strategy configuration"""
        # Collect selected recommendations with cached objects
        selected_recs = []
        
        # Collect from performance metrics (checkbox is column 4)
        for row in range(self.perf_table.rowCount()):
            checkbox_item = self.perf_table.item(row, 4)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                rec = self.recommendation_cache.get(f"perf_{row}")
                if rec:
                    selected_recs.append(rec)
        
        # Collect from risk metrics (checkbox is column 4)
        for row in range(self.risk_table.rowCount()):
            checkbox_item = self.risk_table.item(row, 4)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                rec = self.recommendation_cache.get(f"risk_{row}")
                if rec:
                    selected_recs.append(rec)
        
        if not selected_recs:
            return
        
        # Apply each recommendation
        applied_count = 0
        for rec in selected_recs:
            if self._apply_single_recommendation(rec):
                applied_count += 1
        
        # Update status
        self.status_label.setText(
            f"Status: <b>{applied_count}/{len(selected_recs)} recommendations applied</b>"
        )
        
        # Auto-retest if enabled
        if applied_count > 0 and self.auto_retest_check.isChecked():
            self._trigger_retest()
    
    def _apply_single_recommendation(self, rec: Recommendation) -> bool:
        """
        Apply a single recommendation
        
        Args:
            rec: Recommendation object
        
        Returns:
            True if successfully applied, False otherwise
        """
        try:
            if rec.action_type == 'ADD_BLOCK':
                # Add building block to strategy
                success = self._add_building_block(rec.block_name)
                if success:
                    print(f"✅ Added building block: {rec.block_name}")
                return success
                
            elif rec.action_type == 'ADJUST_PARAMETER':
                # Modify parameter (SL, TP, position size, etc.)
                success = self._adjust_parameter(rec.parameter_name, rec.new_value)
                if success:
                    print(f"✅ Adjusted {rec.parameter_name}: {rec.new_value}")
                return success
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to apply recommendation: {str(e)}")
            return False
    
    def _add_building_block(self, block_name: str) -> bool:
        """
        Add building block to current strategy
        
        Args:
            block_name: Registry name of block to add
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Access orchestrator
            orchestrator = self._get_orchestrator()
            if not orchestrator:
                print("⚠️ Orchestrator not available")
                return False
            
            # Add block via orchestrator
            if hasattr(orchestrator, 'add_building_block'):
                return orchestrator.add_building_block(block_name)
            else:
                print("⚠️ Orchestrator does not support add_building_block method")
                return False
                
        except Exception as e:
            print(f"❌ Failed to add block {block_name}: {str(e)}")
            return False
    
    def _adjust_parameter(self, param_name: str, new_value) -> bool:
        """
        Adjust strategy parameter
        
        Args:
            param_name: Parameter to adjust
            new_value: New parameter value
        
        Returns:
            True if successful, False otherwise
        """
        try:
            orchestrator = self._get_orchestrator()
            if not orchestrator:
                return False
            
            # Adjust parameter via orchestrator
            if hasattr(orchestrator, 'update_parameter'):
                return orchestrator.update_parameter(param_name, new_value)
            else:
                print("⚠️ Orchestrator does not support update_parameter method")
                return False
                
        except Exception as e:
            print(f"❌ Failed to adjust {param_name}: {str(e)}")
            return False
    
    def _get_orchestrator(self):
        """Get orchestrator from main window"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'orchestrator'):
                return main_window.orchestrator
        except:
            pass
        return None
    
    def _trigger_retest(self) -> None:
        """Trigger automatic backtest retest after applying recommendations"""
        try:
            # Access backtest config panel
            main_window = self.window()
            if hasattr(main_window, 'backtest_config_panel'):
                config_panel = main_window.backtest_config_panel
                
                # Trigger backtest run
                if hasattr(config_panel, '_on_run_clicked'):
                    config_panel._on_run_clicked()
                    print("🔄 Auto-retest triggered - backtest started")
                else:
                    print("⚠️ Backtest panel does not support _on_run_clicked method")
            else:
                print("⚠️ Backtest panel not accessible for auto-retest")
                
        except Exception as e:
            print(f"❌ Auto-retest failed: {str(e)}")
