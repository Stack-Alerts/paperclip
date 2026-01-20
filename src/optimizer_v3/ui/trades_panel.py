"""
Trades Panel - Window 2 Tab 3

Institutional-grade trade tracking with full NautilusTrader type integration:
- Real-time trade display with proper types
- Signal tracking per trade
- PnL calculations with Money types
- Excel export functionality
- Zero hardcoded styles (uses styles.py)

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.5)
"""

from typing import List, Dict, Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, field

# NautilusTrader imports
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId, OrderId, TradeId

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_color,
    COLORS
)


@dataclass
class SignalInfo:
    """Signal information for trade - institutional grade"""
    name: str
    block: str
    timestamp: datetime
    triggered: bool
    details: Dict = field(default_factory=dict)


@dataclass
class TradeDetails:
    """Comprehensive trade details with NautilusTrader types"""
    trade_id: TradeId
    order_id: OrderId
    instrument_id: InstrumentId
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str  # 'BUY' or 'SELL'
    quantity: Quantity
    entry_price: Price
    exit_price: Optional[Price]
    stop_loss: Price
    take_profit: Price
    commission: Money
    slippage: Money
    pnl: Money
    risk_reward_ratio: Decimal
    win_loss: str  # 'WIN', 'LOSS', 'OPEN'
    duration: timedelta
    signals: List[SignalInfo]
    capital_start: Money
    capital_end: Money
    drawdown: Money
    notes: str = ""


class TradesPanel(QWidget):
    """
    Institutional-grade Trades Panel for trade tracking.
    
    Provides:
    - Real-time trade display
    - NautilusTrader type safety
    - Signal tracking
    - PnL monitoring
    - Excel export
    - Filtering and sorting
    """
    
    # Signals
    trade_selected = pyqtSignal(TradeDetails)  # Emits selected trade
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trades: List[TradeDetails] = []
        self.filtered_trades: List[TradeDetails] = []
        self.current_filter = {}
        self.current_sort_column = None
        self.current_sort_ascending = True
        
        # Capital tracking
        self.starting_capital: Optional[Money] = None
        self.current_capital: Optional[Money] = None
        self.peak_capital: Optional[Money] = None
        self.max_drawdown: Optional[Money] = None
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("💰 Trades Panel")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title_label)
        
        # Control bar
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        # Summary panel
        summary_panel = self._create_summary_panel()
        layout.addWidget(summary_panel)
        
        # Trades table
        table_group = self._create_trades_table()
        layout.addWidget(table_group)
        
        # Stats bar
        stats_bar = self._create_stats_bar()
        layout.addLayout(stats_bar)
        
        self.setLayout(layout)
    
    def _create_control_bar(self) -> QHBoxLayout:
        """Create control button bar"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Filter combo
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Trades",
            "Winning Trades",
            "Losing Trades",
            "Open Trades",
            "Buy Trades",
            "Sell Trades"
        ])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_combo)
        
        # Search box
        search_label = QLabel("Search:")
        search_label.setStyleSheet(get_label_style('muted'))
        layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search trades...")
        self.search_box.textChanged.connect(self._apply_search)
        layout.addWidget(self.search_box)
        
        layout.addStretch()
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_btn.clicked.connect(self._clear_trades)
        clear_btn.setToolTip("Clear all trades")
        layout.addWidget(clear_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export Excel")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.clicked.connect(self._export_to_excel)
        export_btn.setToolTip("Export trades to Excel file")
        layout.addWidget(export_btn)
        
        return layout
    
    def _create_summary_panel(self) -> QGroupBox:
        """Create summary statistics panel"""
        group = QGroupBox("Summary Statistics")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(120)
        
        layout = QHBoxLayout()
        layout.setSpacing(30)
        
        # Total trades
        self.total_trades_label = QLabel("Total Trades: <b>0</b>")
        self.total_trades_label.setStyleSheet(get_label_style())
        layout.addWidget(self.total_trades_label)
        
        # Win rate
        self.win_rate_label = QLabel("Win Rate: <b>0.00%</b>")
        self.win_rate_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.win_rate_label)
        
        # Total PnL
        self.total_pnl_label = QLabel("Total PnL: <b>$0.00</b>")
        self.total_pnl_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(self.total_pnl_label)
        
        # Avg PnL
        self.avg_pnl_label = QLabel("Avg PnL: <b>$0.00</b>")
        self.avg_pnl_label.setStyleSheet(get_label_style())
        layout.addWidget(self.avg_pnl_label)
        
        # Current capital
        self.current_capital_label = QLabel("Current Capital: <b>$0.00</b>")
        self.current_capital_label.setStyleSheet(get_label_style())
        layout.addWidget(self.current_capital_label)
        
        # Max drawdown
        self.max_drawdown_label = QLabel("Max Drawdown: <b>$0.00</b>")
        self.max_drawdown_label.setStyleSheet(f"color: {COLORS['error']};")
        layout.addWidget(self.max_drawdown_label)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_trades_table(self) -> QGroupBox:
        """Create trades table"""
        group = QGroupBox("Trade History")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create table
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(15)
        self.trades_table.setHorizontalHeaderLabels([
            "Trade ID",
            "Entry Time",
            "Exit Time",
            "Side",
            "Quantity",
            "Entry Price",
            "Exit Price",
            "PnL",
            "Outcome",
            "Duration",
            "R:R",
            "Signals",
            "Capital",
            "Drawdown",
            "Notes"
        ])
        
        # Set table properties
        self.trades_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.trades_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.trades_table.setAlternatingRowColors(True)
        self.trades_table.setSortingEnabled(True)
        self.trades_table.horizontalHeader().setStretchLastSection(True)
        self.trades_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.trades_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Set colors from styles
        self.trades_table.setStyleSheet(
            f"QTableWidget {{ "
            f"background-color: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_primary']}; "
            f"gridline-color: {COLORS['border']}; "
            f"selection-background-color: {COLORS['info']}; "
            f"}} "
            f"QHeaderView::section {{ "
            f"background-color: {COLORS['bg_medium']}; "
            f"color: {COLORS['text_primary']}; "
            f"font-weight: bold; "
            f"padding: 8px; "
            f"border: 1px solid {COLORS['border']}; "
            f"}}"
        )
        
        # Connect selection signal
        self.trades_table.itemSelectionChanged.connect(self._on_trade_selected)
        
        layout.addWidget(self.trades_table)
        group.setLayout(layout)
        return group
    
    def _create_stats_bar(self) -> QHBoxLayout:
        """Create statistics bar"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Winning trades
        self.winning_count_label = QLabel("✅ Wins: <b>0</b>")
        self.winning_count_label.setStyleSheet(f"color: {COLORS['success']};")
        layout.addWidget(self.winning_count_label)
        
        # Losing trades
        self.losing_count_label = QLabel("❌ Losses: <b>0</b>")
        self.losing_count_label.setStyleSheet(f"color: {COLORS['error']};")
        layout.addWidget(self.losing_count_label)
        
        # Open trades
        self.open_count_label = QLabel("🔵 Open: <b>0</b>")
        self.open_count_label.setStyleSheet(f"color: {COLORS['info']};")
        layout.addWidget(self.open_count_label)
        
        # Avg duration
        self.avg_duration_label = QLabel("⏱️ Avg Duration: <b>0m</b>")
        self.avg_duration_label.setStyleSheet(get_label_style())
        layout.addWidget(self.avg_duration_label)
        
        # Avg R:R
        self.avg_rr_label = QLabel("📊 Avg R:R: <b>0.00</b>")
        self.avg_rr_label.setStyleSheet(get_label_style())
        layout.addWidget(self.avg_rr_label)
        
        layout.addStretch()
        return layout
    
    def add_trade(self, trade: TradeDetails) -> None:
        """
        Add trade to panel with full type safety.
        
        Args:
            trade: TradeDetails with NautilusTrader types
        """
        self.trades.append(trade)
        self._update_capital_tracking(trade)
        self._apply_current_filter()
        self._update_summary()
        self._update_stats()
    
    def update_trade(self, trade_id: TradeId, updates: Dict) -> None:
        """
        Update existing trade.
        
        Args:
            trade_id: Trade identifier
            updates: Dictionary of fields to update
        """
        for trade in self.trades:
            if trade.trade_id == trade_id:
                for key, value in updates.items():
                    if hasattr(trade, key):
                        setattr(trade, key, value)
                
                self._apply_current_filter()
                self._update_summary()
                self._update_stats()
                break
    
    def _update_capital_tracking(self, trade: TradeDetails) -> None:
        """Update capital tracking metrics"""
        if self.starting_capital is None:
            self.starting_capital = trade.capital_start
            self.peak_capital = trade.capital_start
        
        self.current_capital = trade.capital_end
        
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        drawdown = self.peak_capital - self.current_capital
        if self.max_drawdown is None or drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def _apply_filter(self, filter_text: str) -> None:
        """Apply filter to trades"""
        self.filtered_trades = []
        
        for trade in self.trades:
            if filter_text == "All Trades":
                self.filtered_trades.append(trade)
            elif filter_text == "Winning Trades" and trade.win_loss == "WIN":
                self.filtered_trades.append(trade)
            elif filter_text == "Losing Trades" and trade.win_loss == "LOSS":
                self.filtered_trades.append(trade)
            elif filter_text == "Open Trades" and trade.win_loss == "OPEN":
                self.filtered_trades.append(trade)
            elif filter_text == "Buy Trades" and trade.side == "BUY":
                self.filtered_trades.append(trade)
            elif filter_text == "Sell Trades" and trade.side == "SELL":
                self.filtered_trades.append(trade)
        
        self._update_table_display()
    
    def _apply_search(self, search_text: str) -> None:
        """Apply search filter"""
        if not search_text:
            self._apply_current_filter()
            return
        
        search_lower = search_text.lower()
        self.filtered_trades = [
            trade for trade in self.filtered_trades
            if (search_lower in trade.trade_id.to_string().lower() or
                search_lower in trade.notes.lower() or
                any(search_lower in sig.name.lower() for sig in trade.signals))
        ]
        
        self._update_table_display()
    
    def _apply_current_filter(self) -> None:
        """Reapply current filter"""
        current_filter = self.filter_combo.currentText()
        self._apply_filter(current_filter)
    
    def _update_table_display(self) -> None:
        """Update table with filtered trades"""
        self.trades_table.setRowCount(0)
        self.trades_table.setRowCount(len(self.filtered_trades))
        
        for row, trade in enumerate(self.filtered_trades):
            # Format data with proper types
            items = [
                trade.trade_id.to_string(),
                trade.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else "Open",
                trade.side,
                trade.quantity.to_string(),
                trade.entry_price.to_string(),
                trade.exit_price.to_string() if trade.exit_price else "-",
                trade.pnl.to_string(),
                trade.win_loss,
                str(trade.duration),
                str(trade.risk_reward_ratio),
                f"{len([s for s in trade.signals if s.triggered])}/{len(trade.signals)}",
                trade.capital_end.to_string(),
                trade.drawdown.to_string(),
                trade.notes
            ]
            
            for col, item_text in enumerate(items):
                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Color code outcome column
                if col == 8:  # Outcome column
                    if trade.win_loss == "WIN":
                        item.setForeground(QColor(COLORS['success']))
                    elif trade.win_loss == "LOSS":
                        item.setForeground(QColor(COLORS['error']))
                    else:  # OPEN
                        item.setForeground(QColor(COLORS['info']))
                
                # Color code PnL column
                elif col == 7:  # PnL column
                    if trade.pnl > Money('0', trade.pnl.currency):
                        item.setForeground(QColor(COLORS['success']))
                    elif trade.pnl < Money('0', trade.pnl.currency):
                        item.setForeground(QColor(COLORS['error']))
                
                self.trades_table.setItem(row, col, item)
    
    def _update_summary(self) -> None:
        """Update summary statistics"""
        if not self.trades:
            return
        
        total = len(self.trades)
        wins = len([t for t in self.trades if t.win_loss == "WIN"])
        win_rate = (Decimal(wins) / Decimal(total)) * Decimal('100') if total > 0 else Decimal('0')
        
        total_pnl = sum(
            (t.pnl for t in self.trades),
            Money('0', self.trades[0].pnl.currency)
        )
        avg_pnl = total_pnl / total if total > 0 else Money('0', self.trades[0].pnl.currency)
        
        # Update labels
        self.total_trades_label.setText(f"Total Trades: <b>{total}</b>")
        self.win_rate_label.setText(f"Win Rate: <b>{win_rate:.2f}%</b>")
        
        # Color code PnL
        pnl_color = COLORS['success'] if total_pnl > Money('0', total_pnl.currency) else COLORS['error']
        self.total_pnl_label.setText(f"Total PnL: <b>{total_pnl.to_string()}</b>")
        self.total_pnl_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold;")
        
        self.avg_pnl_label.setText(f"Avg PnL: <b>{avg_pnl.to_string()}</b>")
        
        if self.current_capital:
            self.current_capital_label.setText(
                f"Current Capital: <b>{self.current_capital.to_string()}</b>"
            )
        
        if self.max_drawdown:
            self.max_drawdown_label.setText(
                f"Max Drawdown: <b>{self.max_drawdown.to_string()}</b>"
            )
    
    def _update_stats(self) -> None:
        """Update statistics bar"""
        wins = len([t for t in self.trades if t.win_loss == "WIN"])
        losses = len([t for t in self.trades if t.win_loss == "LOSS"])
        open_trades = len([t for t in self.trades if t.win_loss == "OPEN"])
        
        self.winning_count_label.setText(f"✅ Wins: <b>{wins}</b>")
        self.losing_count_label.setText(f"❌ Losses: <b>{losses}</b>")
        self.open_count_label.setText(f"🔵 Open: <b>{open_trades}</b>")
        
        if self.trades:
            # Average duration
            total_duration = sum(
                (t.duration for t in self.trades if t.exit_time),
                timedelta()
            )
            closed_trades = len([t for t in self.trades if t.exit_time])
            avg_duration = total_duration / closed_trades if closed_trades > 0 else timedelta()
            avg_minutes = int(avg_duration.total_seconds() / 60)
            self.avg_duration_label.setText(f"⏱️ Avg Duration: <b>{avg_minutes}m</b>")
            
            # Average R:R
            total_rr = sum(t.risk_reward_ratio for t in self.trades)
            avg_rr = total_rr / len(self.trades)
            self.avg_rr_label.setText(f"📊 Avg R:R: <b>{avg_rr:.2f}</b>")
    
    def _on_trade_selected(self) -> None:
        """Handle trade selection"""
        selected_rows = self.trades_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            if 0 <= row < len(self.filtered_trades):
                trade = self.filtered_trades[row]
                self.trade_selected.emit(trade)
    
    def _clear_trades(self) -> None:
        """Clear all trades"""
        reply = QMessageBox.question(
            self,
            "Clear Trades",
            "Are you sure you want to clear all trades?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.trades.clear()
            self.filtered_trades.clear()
            self.starting_capital = None
            self.current_capital = None
            self.peak_capital = None
            self.max_drawdown = None
            self._update_table_display()
            self._update_summary()
            self._update_stats()
    
    def _export_to_excel(self) -> None:
        """Export trades to Excel file"""
        if not self.trades:
            QMessageBox.information(
                self,
                "No Trades",
                "No trades to export."
            )
            return
        
        try:
            import pandas as pd
            from datetime import datetime
            
            filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Convert trades to DataFrame
            data = []
            for trade in self.trades:
                triggered_signals = [s.name for s in trade.signals if s.triggered]
                
                data.append({
                    'Trade ID': trade.trade_id.to_string(),
                    'Order ID': trade.order_id.to_string(),
                    'Instrument': trade.instrument_id.to_string(),
                    'Entry Time': trade.entry_time,
                    'Exit Time': trade.exit_time,
                    'Side': trade.side,
                    'Quantity': trade.quantity.to_string(),
                    'Entry Price': trade.entry_price.to_string(),
                    'Exit Price': trade.exit_price.to_string() if trade.exit_price else None,
                    'Stop Loss': trade.stop_loss.to_string(),
                    'Take Profit': trade.take_profit.to_string(),
                    'Commission': trade.commission.to_string(),
                    'Slippage': trade.slippage.to_string(),
                    'PnL': trade.pnl.to_string(),
                    'Risk/Reward': str(trade.risk_reward_ratio),
                    'Outcome': trade.win_loss,
                    'Duration': str(trade.duration),
                    'Signals': ', '.join(triggered_signals),
                    'Starting Capital': trade.capital_start.to_string(),
                    'Ending Capital': trade.capital_end.to_string(),
                    'Drawdown': trade.drawdown.to_string(),
                    'Notes': trade.notes
                })
            
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, sheet_name='Trades')
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Trades exported to {filename}"
            )
            
        except ImportError:
            QMessageBox.warning(
                self,
                "Export Error",
                "pandas and openpyxl required for Excel export.\n"
                "Install with: pip install pandas openpyxl"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export trades:\n{str(e)}"
            )
    
    def get_trades(self) -> List[TradeDetails]:
        """
        Get all trades.
        
        Returns:
            List of TradeDetails
        """
        return self.trades.copy()
    
    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics.
        
        Returns:
            Dictionary of statistics
        """
        if not self.trades:
            return {}
        
        total = len(self.trades)
        wins = len([t for t in self.trades if t.win_loss == "WIN"])
        
        return {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': len([t for t in self.trades if t.win_loss == "LOSS"]),
            'open_trades': len([t for t in self.trades if t.win_loss == "OPEN"]),
            'win_rate': Decimal(wins) / Decimal(total) if total > 0 else Decimal('0'),
            'total_pnl': sum(
                (t.pnl for t in self.trades),
                Money('0', self.trades[0].pnl.currency)
            ),
            'starting_capital': self.starting_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'max_drawdown': self.max_drawdown
        }
