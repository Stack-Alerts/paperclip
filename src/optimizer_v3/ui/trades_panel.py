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
        
        # Long Trades
        self.long_trades_label = QLabel("Long Trades: <b>0</b>")
        self.long_trades_label.setStyleSheet(get_label_style())
        layout.addWidget(self.long_trades_label)
        
        # Short Trades
        self.short_trades_label = QLabel("Short Trades: <b>0</b>")
        self.short_trades_label.setStyleSheet(get_label_style())
        layout.addWidget(self.short_trades_label)
        
        # Winning Trades
        self.winning_trades_label = QLabel("Winning Trades: <b>0</b>")
        self.winning_trades_label.setStyleSheet(get_label_style())
        layout.addWidget(self.winning_trades_label)
        
        # Losing Trades
        self.losing_trades_label = QLabel("Losing Trades: <b>0</b>")
        self.losing_trades_label.setStyleSheet(get_label_style())
        layout.addWidget(self.losing_trades_label)
        
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
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # Allow multi-selection
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setVisible(False)
        
        # Set column widths - ID fixed, Notes fixed, all others stretch equally
        # ID=115px (fixed +35px total from original 80px), Notes=500px (fixed), 10 standard columns stretch to fill window
        # ID, Time, Symbol, Side, Size, Entry, Exit, Duration, P&L, P&L %, Status, Notes
        column_widths = [115, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 500]
        for i, width in enumerate(column_widths):
            self.table.setColumnWidth(i, width)
        
        # Set stretch on all standard columns (1-10) to fill window equally
        # ID (0) and Notes (11) stay fixed
        for i in range(1, 11):  # Columns 1-10 (Time through Status)
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        # Set default sort on ID column (ascending 1,2,3,4...)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.current_sort_column = 0
        self.current_sort_order = Qt.SortOrder.AscendingOrder
        
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
        
        # Copy Selection button (for selected rows)
        copy_selection_btn = QPushButton("📋 Copy Selection")
        copy_selection_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_selection_btn.setFixedSize(245, 42)
        copy_selection_btn.clicked.connect(self._copy_selection)
        copy_selection_btn.setToolTip("Copy selected trades to clipboard (Ctrl+Click for multi-select)")
        layout.addWidget(copy_selection_btn)
        
        # Copy All button
        copy_btn = QPushButton("📋 Copy All")
        copy_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        copy_btn.setFixedSize(135, 42)
        copy_btn.clicked.connect(self._copy_trades)
        copy_btn.setToolTip("Copy all trades to clipboard")
        layout.addWidget(copy_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        export_btn.setFixedSize(130, 42)
        export_btn.clicked.connect(self._export_trades)
        export_btn.setToolTip("Export all trades to CSV file")
        layout.addWidget(export_btn)
        
        return layout
    
    def clear_trades(self) -> None:
        """Clear all trades from panel (call at start of new backtest)"""
        self.trades.clear()
        self.filtered_trades.clear()
        self._update_table()
        self._update_metrics()
        print("🧹 Trades panel cleared for new backtest")
    
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
    
    def update_trade(self, trade_id, trade_data: Dict) -> None:
        """
        Update existing trade in real-time (called when trade closes during execution).
        
        Args:
            trade_id: ID of trade to update (string or int)
            trade_data: Updated trade information (exit_price, pnl, status, etc.)
        """
        # Convert to string for comparison (IDs stored as strings)
        trade_id_str = str(trade_id)
        
        # Find trade by ID and update it
        for i, trade in enumerate(self.trades):
            if str(trade.get('id')) == trade_id_str:
                # Update trade with new data
                self.trades[i].update(trade_data)
                self.filtered_trades = self.trades.copy()
                # Immediately refresh UI to show closed trade
                self._update_table()
                self._update_metrics()
                print(f"✅ Trade #{trade_id} updated in real-time")
                return
        
        print(f"⚠️ Trade #{trade_id} not found for update - adding as new trade")
        # If not found, add as new trade (shouldn't happen, but safety fallback)
        self.add_trade(trade_data)
    
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
            
            # Side (LONG/SHORT for futures trading)
            side = trade.get('side', 'LONG')
            side_item = self._create_item(side)
            if side == 'LONG':
                side_item.setForeground(QColor(get_color('success')))  # Green for LONG
            else:  # SHORT
                side_item.setForeground(QColor(get_color('error')))  # Red for SHORT
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
        
        # Update labels with color coding - consistent font size with other labels
        pnl_text = f"Total P&L: <b>${total_pnl:,.2f}</b>"
        if total_pnl > 0:
            self.pnl_label.setStyleSheet(f"color: {get_color('success')};")
        elif total_pnl < 0:
            self.pnl_label.setStyleSheet(f"color: {get_color('error')};")
        else:
            self.pnl_label.setStyleSheet(get_label_style())
        self.pnl_label.setText(pnl_text)
        
        # Count LONG and SHORT trades
        long_trades = len([t for t in self.trades if t.get('side') == 'LONG'])
        short_trades = len([t for t in self.trades if t.get('side') == 'SHORT'])
        
        # Update individual labels
        self.winrate_label.setText(f"Win Rate: <b>{win_rate:.2f}%</b>")
        self.long_trades_label.setText(f"Long Trades: <b>{long_trades}</b>")
        self.short_trades_label.setText(f"Short Trades: <b>{short_trades}</b>")
        self.winning_trades_label.setText(f"Winning Trades: <b>{wins}</b>")
        self.losing_trades_label.setText(f"Losing Trades: <b>{losses}</b>")
        
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
    
    def _copy_selection(self) -> None:
        """Copy selected trades to clipboard in CSV format"""
        from PyQt5.QtWidgets import QApplication
        
        # Get selected row indices
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            print("⚠️ No trades selected - select rows with Ctrl+Click or Shift+Click")
            return
        
        try:
            # Get selected trade indices
            selected_indices = sorted([row.row() for row in selected_rows])
            selected_trades = [self.filtered_trades[i] for i in selected_indices]
            
            # Build CSV content
            lines = []
            # Header
            lines.append("ID\tTime\tSymbol\tSide\tSize\tEntry\tExit\tDuration\tP&L\tP&L %\tStatus\tNotes")
            
            # Data rows (only selected)
            for trade in selected_trades:
                timestamp = trade.get('timestamp', datetime.now())
                time_str = timestamp.strftime('%H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)
                
                lines.append(
                    f"{trade.get('id', '')}\t"
                    f"{time_str}\t"
                    f"{trade.get('symbol', '')}\t"
                    f"{trade.get('side', '')}\t"
                    f"{trade.get('size', '')}\t"
                    f"${float(trade.get('entry_price', 0)):,.2f}\t"
                    f"${float(trade.get('exit_price', 0)):,.2f}\t"
                    f"{trade.get('duration', '')}\t"
                    f"${float(trade.get('pnl', 0)):,.2f}\t"
                    f"{float(trade.get('pnl_pct', 0)):.2f}%\t"
                    f"{trade.get('status', '')}\t"
                    f"{trade.get('notes', '')}"
                )
            
            # Copy to clipboard
            csv_content = '\n'.join(lines)
            clipboard = QApplication.clipboard()
            clipboard.setText(csv_content)
            
            print(f"✅ {len(selected_trades)} selected trades copied to clipboard")
            
        except Exception as e:
            print(f"❌ Copy selection failed: {str(e)}")
    
    def _copy_trades(self) -> None:
        """Copy all trades to clipboard in CSV format"""
        from PyQt5.QtWidgets import QApplication
        
        if not self.trades:
            print("⚠️ No trades to copy")
            return
        
        try:
            # Build CSV content
            lines = []
            # Header
            lines.append("ID\tTime\tSymbol\tSide\tSize\tEntry\tExit\tDuration\tP&L\tP&L %\tStatus\tNotes")
            
            # Data rows
            for trade in self.trades:
                timestamp = trade.get('timestamp', datetime.now())
                time_str = timestamp.strftime('%H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)
                
                lines.append(
                    f"{trade.get('id', '')}\t"
                    f"{time_str}\t"
                    f"{trade.get('symbol', '')}\t"
                    f"{trade.get('side', '')}\t"
                    f"{trade.get('size', '')}\t"
                    f"${float(trade.get('entry_price', 0)):,.2f}\t"
                    f"${float(trade.get('exit_price', 0)):,.2f}\t"
                    f"{trade.get('duration', '')}\t"
                    f"${float(trade.get('pnl', 0)):,.2f}\t"
                    f"{float(trade.get('pnl_pct', 0)):.2f}%\t"
                    f"{trade.get('status', '')}\t"
                    f"{trade.get('notes', '')}"
                )
            
            # Copy to clipboard
            csv_content = '\n'.join(lines)
            clipboard = QApplication.clipboard()
            clipboard.setText(csv_content)
            
            print(f"✅ {len(self.trades)} trades copied to clipboard")
            
        except Exception as e:
            print(f"❌ Copy failed: {str(e)}")
    
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
