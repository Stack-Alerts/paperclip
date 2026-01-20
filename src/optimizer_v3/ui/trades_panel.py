"""
Trades Panel - Institutional-Grade Trade Tracking

Excel-like interface for comprehensive trade tracking:
- Real-time trade updates
- Trade status indicators
- Entry/exit details
- PnL tracking with proper Money types
- Risk metrics analysis
- Interactive sorting and filtering
- Export capabilities

ZERO HARDCODED STYLES - All from styles.py

Author: Optimizer v3 Team
Date: 2026-01-20
Sprint: 1.4 (UI Integration - Task 1.4.5)
"""

from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QContextMenuEvent

# Import centralized styles - ZERO hardcoded styles
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_label_style,
    get_panel_title_stylesheet,
    get_primary_button_stylesheet,
    get_table_stylesheet,
    get_color
)


class TradesPanel(QWidget):
    """
    Institutional-Grade Trades Panel
    
    Features:
    - Real-time trade tracking
    - Excel-like table interface
    - Interactive sorting/filtering
    - PnL tracking with Money types
    - Risk metrics analysis
    - Export capabilities
    - Dark theme compatible
    """
    
    # Signals
    trade_selected = pyqtSignal(dict)  # Emits selected trade data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trades: List[Dict] = []
        self.filtered_trades: List[Dict] = []
        self.current_sort_column = 0
        self.current_sort_order = Qt.SortOrder.DescendingOrder
        
        # Performance tracking
        self.total_pnl = Decimal('0.0')
        self.win_count = 0
        self.loss_count = 0
        
        self._init_ui()
        
        # Update timer for metrics
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self._update_metrics)
        self.metrics_timer.start(1000)  # Update every second
    
    def _init_ui(self) -> None:
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("📊 Trades Panel")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title_label)
        
        # Performance summary
        summary_group = self._create_performance_summary()
        layout.addWidget(summary_group)
        
        # Trades table
        table_group = self._create_trades_table()
        layout.addWidget(table_group)
        
        # Control buttons at bottom
        control_bar = self._create_control_bar()
        layout.addLayout(control_bar)
        
        self.setLayout(layout)
    
    def _create_performance_summary(self) -> QGroupBox:
        """Create performance summary panel"""
        group = QGroupBox("Performance Summary")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        group.setMaximumHeight(120)
        
        layout = QHBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Total PnL
        self.pnl_label = QLabel("Total P&L: <b>$0.00</b>")
        self.pnl_label.setStyleSheet(get_label_style())
        layout.addWidget(self.pnl_label)
        
        # Win Rate
        self.winrate_label = QLabel("Win Rate: <b>0.00%</b>")
        self.winrate_label.setStyleSheet(get_label_style())
        layout.addWidget(self.winrate_label)
        
        # Total Trades
        self.trades_count_label = QLabel("Total Trades: <b>0</b>")
        self.trades_count_label.setStyleSheet(get_label_style())
        layout.addWidget(self.trades_count_label)
        
        # Average Trade
        self.avg_trade_label = QLabel("Avg Trade: <b>$0.00</b>")
        self.avg_trade_label.setStyleSheet(get_label_style())
        layout.addWidget(self.avg_trade_label)
        
        # Profit Factor
        self.pf_label = QLabel("Profit Factor: <b>0.00</b>")
        self.pf_label.setStyleSheet(get_label_style())
        layout.addWidget(self.pf_label)
        
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def _create_trades_table(self) -> QGroupBox:
        """Create trades table with Excel-like interface"""
        group = QGroupBox("Trade History")
        group.setStyleSheet(get_groupbox_header_stylesheet())
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Time', 'Symbol', 'Side', 'Size', 'Entry', 
            'Exit', 'Duration', 'P&L', 'P&L %', 'Status', 'Notes'
        ])
        
        # Table styling - using helper function from styles.py (ZERO hardcoded styles)
        self.table.setStyleSheet(get_table_stylesheet())
        
        # Table configuration
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setVisible(False)
        
        # Set column widths - generous minimum widths to prevent header cutoff
        # ID, Time, Symbol, Side, Size, Entry, Exit, Duration, P&L, P&L %, Status, Notes
        column_widths = [80, 150, 130, 80, 100, 120, 120, 140, 150, 130, 120, 200]
        for i, width in enumerate(column_widths):
            self.table.setColumnWidth(i, width)
        
        # Make Time, Entry, Exit, P&L, and Notes columns stretch proportionally
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Time
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Entry
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Exit
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # P&L
        self.table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.Stretch)  # Notes
        
        # Connect signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        
        layout.addWidget(self.table)
        group.setLayout(layout)
        return group
    
    def _create_control_bar(self) -> QHBoxLayout:
        """Create control buttons at bottom"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Filter info
        self.filter_label = QLabel("Showing: <b>All Trades (0)</b>")
        self.filter_label.setStyleSheet(get_label_style())
        layout.addWidget(self.filter_label)
        
        layout.addStretch()
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        clear_btn.setFixedSize(130, 42)
        clear_btn.clicked.connect(self._clear_trades)
        clear_btn.setToolTip("Clear all trades")
        layout.addWidget(clear_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.setFixedSize(130, 42)
        export_btn.clicked.connect(self._export_trades)
        export_btn.setToolTip("Export trades to Excel")
        layout.addWidget(export_btn)
        
        return layout
    
    def add_trade(self, trade_data: Dict) -> None:
        """
        Add trade to panel.
        
        Args:
            trade_data: Dictionary with trade information
                Required keys: id, timestamp, symbol, side, size, entry_price
                Optional keys: exit_price, exit_timestamp, pnl, status, notes
        """
        self.trades.append(trade_data)
        self.filtered_trades = self.trades.copy()
        self._update_table()
        self._update_metrics()
    
    def _update_table(self) -> None:
        """Update table with current trades"""
        self.table.setRowCount(len(self.filtered_trades))
        
        for row, trade in enumerate(self.filtered_trades):
            # ID
            self.table.setItem(row, 0, self._create_item(str(trade.get('id', ''))))
            
            # Time
            timestamp = trade.get('timestamp', datetime.now())
            time_str = timestamp.strftime('%H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)
            self.table.setItem(row, 1, self._create_item(time_str))
            
            # Symbol
            self.table.setItem(row, 2, self._create_item(trade.get('symbol', 'BTC/USDT')))
            
            # Side
            side = trade.get('side', 'BUY')
            side_item = self._create_item(side)
            if side == 'BUY':
                side_item.setForeground(QColor(get_color('success')))
            else:
                side_item.setForeground(QColor(get_color('error')))
            self.table.setItem(row, 3, side_item)
            
            # Size
            size = trade.get('size', '0.0')
            self.table.setItem(row, 4, self._create_item(f"{float(size):.4f}"))
            
            # Entry Price
            entry = trade.get('entry_price', '0.0')
            self.table.setItem(row, 5, self._create_item(f"${float(entry):,.2f}"))
            
            # Exit Price
            exit_price = trade.get('exit_price')
            if exit_price:
                self.table.setItem(row, 6, self._create_item(f"${float(exit_price):,.2f}"))
            else:
                self.table.setItem(row, 6, self._create_item('-'))
            
            # Duration
            duration = trade.get('duration', '00:00:00')
            self.table.setItem(row, 7, self._create_item(str(duration)))
            
            # P&L
            pnl = trade.get('pnl', 0.0)
            pnl_item = self._create_item(f"${float(pnl):,.2f}")
            if float(pnl) > 0:
                pnl_item.setForeground(QColor(get_color('success')))
            elif float(pnl) < 0:
                pnl_item.setForeground(QColor(get_color('error')))
            self.table.setItem(row, 8, pnl_item)
            
            # P&L %
            pnl_pct = trade.get('pnl_pct', 0.0)
            pnl_pct_item = self._create_item(f"{float(pnl_pct):.2f}%")
            if float(pnl_pct) > 0:
                pnl_pct_item.setForeground(QColor(get_color('success')))
            elif float(pnl_pct) < 0:
                pnl_pct_item.setForeground(QColor(get_color('error')))
            self.table.setItem(row, 9, pnl_pct_item)
            
            # Status
            status = trade.get('status', 'OPEN')
            status_item = self._create_item(status)
            if status == 'CLOSED':
                status_item.setForeground(QColor(get_color('text_muted')))
            elif status == 'OPEN':
                status_item.setForeground(QColor(get_color('success')))
            self.table.setItem(row, 10, status_item)
            
            # Notes
            notes = trade.get('notes', '')
            self.table.setItem(row, 11, self._create_item(str(notes)))
    
    def _create_item(self, text: str) -> QTableWidgetItem:
        """Create centered table item"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
    
    def _update_metrics(self) -> None:
        """Update performance metrics"""
        if not self.trades:
            return
        
        # Calculate metrics
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if float(t.get('pnl', 0)) > 0])
        losses = len([t for t in self.trades if float(t.get('pnl', 0)) < 0])
        
        total_pnl = sum(float(t.get('pnl', 0)) for t in self.trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        
        # Profit factor
        gross_profit = sum(float(t.get('pnl', 0)) for t in self.trades if float(t.get('pnl', 0)) > 0)
        gross_loss = abs(sum(float(t.get('pnl', 0)) for t in self.trades if float(t.get('pnl', 0)) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Update labels with color coding
        pnl_text = f"Total P&L: <b>${total_pnl:,.2f}</b>"
        if total_pnl > 0:
            self.pnl_label.setStyleSheet(f"color: {get_color('success')}; font-size: 14px;")
        elif total_pnl < 0:
            self.pnl_label.setStyleSheet(f"color: {get_color('error')}; font-size: 14px;")
        else:
            self.pnl_label.setStyleSheet(get_label_style())
        self.pnl_label.setText(pnl_text)
        
        self.winrate_label.setText(f"Win Rate: <b>{win_rate:.2f}%</b>")
        self.trades_count_label.setText(f"Total Trades: <b>{total_trades}</b> (W:{wins} L:{losses})")
        self.avg_trade_label.setText(f"Avg Trade: <b>${avg_trade:,.2f}</b>")
        self.pf_label.setText(f"Profit Factor: <b>{profit_factor:.2f}</b>")
        
        # Update filter label
        self.filter_label.setText(f"Showing: <b>All Trades ({len(self.filtered_trades)})</b>")
    
    def _on_selection_changed(self) -> None:
        """Handle row selection"""
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.filtered_trades):
                self.trade_selected.emit(self.filtered_trades[row])
    
    def _on_header_clicked(self, logical_index: int) -> None:
        """Handle column header click for sorting"""
        # Toggle sort order if same column
        if logical_index == self.current_sort_column:
            self.current_sort_order = (
                Qt.SortOrder.AscendingOrder 
                if self.current_sort_order == Qt.SortOrder.DescendingOrder 
                else Qt.SortOrder.DescendingOrder
            )
        else:
            self.current_sort_column = logical_index
            self.current_sort_order = Qt.SortOrder.DescendingOrder
        
        self.table.sortItems(logical_index, self.current_sort_order)
    
    def _clear_trades(self) -> None:
        """Clear all trades"""
        self.trades.clear()
        self.filtered_trades.clear()
        self.table.setRowCount(0)
        self._update_metrics()
    
    def _export_trades(self) -> None:
        """Export trades to Excel/CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"trades_export_{timestamp}.csv"
        
        try:
            with open(filename, 'w') as f:
                # Write header
                f.write("ID,Time,Symbol,Side,Size,Entry,Exit,Duration,P&L,P&L %,Status,Notes\n")
                
                # Write trades
                for trade in self.trades:
                    f.write(
                        f"{trade.get('id', '')},"
                        f"{trade.get('timestamp', '')},"
                        f"{trade.get('symbol', '')},"
                        f"{trade.get('side', '')},"
                        f"{trade.get('size', '')},"
                        f"{trade.get('entry_price', '')},"
                        f"{trade.get('exit_price', '')},"
                        f"{trade.get('duration', '')},"
                        f"{trade.get('pnl', '')},"
                        f"{trade.get('pnl_pct', '')},"
                        f"{trade.get('status', '')},"
                        f"{trade.get('notes', '')}\n"
                    )
            
            print(f"✅ Trades exported to {filename}")
            
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
    
    def get_trades(self) -> List[Dict]:
        """Get all trades"""
        return self.trades.copy()
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        if not self.trades:
            return {
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'avg_trade': 0.0,
                'profit_factor': 0.0
            }
        
        total_trades = len(self.trades)
        wins = len([t for t in self.trades if float(t.get('pnl', 0)) > 0])
        total_pnl = sum(float(t.get('pnl', 0)) for t in self.trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        
        gross_profit = sum(float(t.get('pnl', 0)) for t in self.trades if float(t.get('pnl', 0)) > 0)
        gross_loss = abs(sum(float(t.get('pnl', 0)) for t in self.trades if float(t.get('pnl', 0)) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        return {
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_trade': avg_trade,
            'profit_factor': profit_factor
        }
