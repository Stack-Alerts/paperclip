# NAUTILUS TRADES PANEL INTEGRATION
**Integration of Institutional-Grade Trades Panel with Optimizer V3**

## 📋 OVERVIEW

This document outlines how the institutional-grade trades panel is integrated with Optimizer V3, providing detailed trade information, signal tracking, capital management, and comprehensive reporting capabilities.

## 🔧 IMPLEMENTATION

### 1. Trade Data Structure

```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId, OrderId, TradeId
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import pandas as pd

@dataclass
class SignalInfo:
    """Signal information for trade"""
    name: str
    block: str
    timestamp: datetime
    triggered: bool
    details: dict

@dataclass
class TradeDetails:
    """Comprehensive trade details"""
    trade_id: TradeId
    order_id: OrderId
    instrument_id: InstrumentId
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str
    quantity: Quantity
    entry_price: Price
    exit_price: Optional[Price]
    stop_loss: Price
    take_profit: Price
    commission: Money
    slippage: Money
    pnl: Money
    risk_reward_ratio: Decimal
    win_loss: str
    duration: timedelta
    signals: List[SignalInfo]
    capital_start: Money
    capital_end: Money
    drawdown: Money
    notes: str

class NautilusTradesPanel:
    """Handle institutional-grade trades panel"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self._trades = []
        self._df = None
        self._current_capital = None
        self._peak_capital = None
        self._max_drawdown = None
    
    def add_trade(self, trade: TradeDetails):
        """Add trade to panel"""
        self._trades.append(trade)
        self._update_dataframe()
        self._update_capital_metrics(trade)
    
    def _update_dataframe(self):
        """Update trades DataFrame"""
        # Convert trades to DataFrame format
        data = []
        for trade in self._trades:
            # Flatten signals information
            triggered_signals = [
                s.name for s in trade.signals if s.triggered
            ]
            untriggered_signals = [
                s.name for s in trade.signals if not s.triggered
            ]
            
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
                'Triggered Signals': ', '.join(triggered_signals),
                'Untriggered Signals': ', '.join(untriggered_signals),
                'Starting Capital': trade.capital_start.to_string(),
                'Ending Capital': trade.capital_end.to_string(),
                'Drawdown': trade.drawdown.to_string(),
                'Notes': trade.notes
            })
        
        self._df = pd.DataFrame(data)
    
    def _update_capital_metrics(self, trade: TradeDetails):
        """Update capital metrics"""
        if self._current_capital is None:
            self._current_capital = trade.capital_start
            self._peak_capital = trade.capital_start
        
        self._current_capital = trade.capital_end
        if self._current_capital > self._peak_capital:
            self._peak_capital = self._current_capital
        
        drawdown = self._peak_capital - self._current_capital
        if self._max_drawdown is None or drawdown > self._max_drawdown:
            self._max_drawdown = drawdown
    
    def get_trades_table(self,
                        filters: Optional[Dict] = None,
                        sort_by: Optional[str] = None,
                        ascending: bool = True) -> pd.DataFrame:
        """Get filtered and sorted trades table"""
        if self._df is None:
            return pd.DataFrame()
            
        df = self._df.copy()
        
        # Apply filters
        if filters:
            for column, value in filters.items():
                if isinstance(value, (list, tuple)):
                    df = df[df[column].isin(value)]
                else:
                    df = df[df[column] == value]
        
        # Apply sorting
        if sort_by:
            df = df.sort_values(by=sort_by, ascending=ascending)
        
        return df
    
    def get_summary_stats(self) -> dict:
        """Get summary statistics"""
        if not self._trades:
            return {}
        
        total_trades = len(self._trades)
        winning_trades = len([t for t in self._trades if t.win_loss == 'WIN'])
        
        total_pnl = sum((t.pnl for t in self._trades), start=Money('0', 'USD'))
        avg_pnl = total_pnl / total_trades if total_trades > 0 else Money('0', 'USD')
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': Decimal(winning_trades) / Decimal(total_trades),
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'starting_capital': self._trades[0].capital_start if self._trades else None,
            'current_capital': self._current_capital,
            'peak_capital': self._peak_capital,
            'max_drawdown': self._max_drawdown,
            'avg_trade_duration': sum(
                (t.duration for t in self._trades),
                start=timedelta()
            ) / total_trades if total_trades > 0 else timedelta(),
            'avg_risk_reward': sum(
                (t.risk_reward_ratio for t in self._trades),
                start=Decimal('0')
            ) / Decimal(total_trades) if total_trades > 0 else Decimal('0')
        }
    
    def export_to_excel(self, filepath: str):
        """Export trades to Excel"""
        if self._df is None:
            raise ValueError("No trades to export")
            
        # Create Excel writer
        writer = pd.ExcelWriter(filepath, engine='xlsxwriter')
        
        # Write trades table
        self._df.to_excel(writer, sheet_name='Trades', index=False)
        
        # Get workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Trades']
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'bg_color': '#D9D9D9',
            'border': 1
        })
        
        win_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'font_color': '#006100'
        })
        
        loss_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006'
        })
        
        # Set column widths
        for idx, col in enumerate(self._df.columns):
            max_length = max(
                self._df[col].astype(str).apply(len).max(),
                len(col)
            )
            worksheet.set_column(idx, idx, max_length + 2)
        
        # Format header
        for col_num, value in enumerate(self._df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Add conditional formatting
        worksheet.conditional_format(
            1, self._df.columns.get_loc('Outcome'),
            len(self._df), self._df.columns.get_loc('Outcome'),
            {'type': 'text',
             'criteria': 'containing',
             'value': 'WIN',
             'format': win_format}
        )
        
        worksheet.conditional_format(
            1, self._df.columns.get_loc('Outcome'),
            len(self._df), self._df.columns.get_loc('Outcome'),
            {'type': 'text',
             'criteria': 'containing',
             'value': 'LOSS',
             'format': loss_format}
        )
        
        # Add summary sheet
        summary_df = pd.DataFrame([self.get_summary_stats()])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Save Excel file
        writer.save()

class NautilusTradesPanelUI:
    """Handle trades panel UI integration"""
    
    def __init__(self,
                 trades_panel: NautilusTradesPanel,
                 logger: OptimizerLogger):
        self.trades_panel = trades_panel
        self.logger = logger
        self._table_widget = None
        self._filters = {}
        self._sort_column = None
        self._sort_ascending = True
    
    def initialize_ui(self, table_widget):
        """Initialize UI components"""
        self._table_widget = table_widget
        self._setup_table()
        self._update_table()
    
    def _setup_table(self):
        """Setup table widget"""
        if not self._table_widget:
            return
            
        # Set column headers
        headers = [
            'Trade ID', 'Entry Time', 'Exit Time', 'Side', 'Quantity',
            'Entry Price', 'Exit Price', 'Stop Loss', 'Take Profit',
            'PnL', 'Risk/Reward', 'Outcome', 'Duration',
            'Triggered Signals', 'Untriggered Signals',
            'Starting Capital', 'Ending Capital', 'Drawdown'
        ]
        
        self._table_widget.setColumnCount(len(headers))
        self._table_widget.setHorizontalHeaderLabels(headers)
        
        # Enable sorting
        self._table_widget.setSortingEnabled(True)
        
        # Set column widths
        self._table_widget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
    
    def _update_table(self):
        """Update table with current data"""
        if not self._table_widget:
            return
            
        # Get filtered and sorted data
        df = self.trades_panel.get_trades_table(
            filters=self._filters,
            sort_by=self._sort_column,
            ascending=self._sort_ascending
        )
        
        # Update table
        self._table_widget.setRowCount(len(df))
        
        for row_idx, row in df.iterrows():
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                
                # Set colors for outcome column
                if df.columns[col_idx] == 'Outcome':
                    if value == 'WIN':
                        item.setBackground(QColor('#C6EFCE'))
                        item.setForeground(QColor('#006100'))
                    elif value == 'LOSS':
                        item.setBackground(QColor('#FFC7CE'))
                        item.setForeground(QColor('#9C0006'))
                
                self._table_widget.setItem(row_idx, col_idx, item)
    
    def set_filter(self, column: str, value: any):
        """Set filter for column"""
        self._filters[column] = value
        self._update_table()
    
    def clear_filter(self, column: str):
        """Clear filter for column"""
        if column in self._filters:
            del self._filters[column]
            self._update_table()
    
    def clear_all_filters(self):
        """Clear all filters"""
        self._filters = {}
        self._update_table()
    
    def set_sorting(self, column: str, ascending: bool = True):
        """Set sorting for table"""
        self._sort_column = column
        self._sort_ascending = ascending
        self._update_table()
```

### 2. Integration with Live Output

```python
class NautilusTradeOutput:
    """Handle trade-related output with panel integration"""
    
    def __init__(self,
                 live_output: NautilusLiveOutput,
                 trades_panel: NautilusTradesPanel):
        self.live_output = live_output
        self.trades_panel = trades_panel
    
    async def trade_initiated(self,
                            trade_id: TradeId,
                            order_id: OrderId,
                            side: str,
                            quantity: Quantity,
                            price: Price,
                            signals: List[SignalInfo],
                            details: dict):
        """Output trade initiation and update panel"""
        # Send live output message
        await self.live_output.send_message(
            level=OutputLevel.ACTION,
            category=OutputCategory.TRADE,
            message=f"Trade initiated: {side}",
            details={
                'trade_id': trade_id.to_string(),
                'order_id': order_id.to_string(),
                'side': side,
                'quantity': quantity.to_string(),
                'price': price.to_string(),
                'signals': [s.name for s in signals if s.triggered],
                **details
            }
        )
        
        # Create trade details
        trade = TradeDetails(
            trade_id=trade_id,
            order_id=order_id,
            instrument_id=details['instrument_id'],
            entry_time=datetime.now(),
            exit_time=None,
            side=side,
            quantity=quantity,
            entry_price=price,
            exit_price=None,
            stop_loss=details['stop_loss'],
            take_profit=details['take_profit'],
            commission=details.get('commission', Money('0', 'USD')),
            slippage=details.get('slippage', Money('0', 'USD')),
            pnl=Money('0', 'USD'),
            risk_reward_ratio=details['risk_reward'],
            win_loss='OPEN',
            duration=timedelta(),
            signals=signals,
            capital_start=details['capital'],
            capital_end=details['capital'],
            drawdown=Money('0', 'USD'),
            notes=details.get('notes', '')
        )
        
        # Add to panel
        self.trades_panel.add_trade(trade)
    
    async def trade_completed(self,
                            trade_id: TradeId,
                            exit_price: Price,
                            pnl: Money,
                            details: dict):
        """Update completed trade in panel"""
        # Find trade in panel
        for trade in self.trades_panel._trades:
            if trade.trade_id == trade_id:
                # Update trade details
                trade.exit_time = datetime.now()
                trade.exit_price = exit_price
                trade.pnl = pnl
                trade.win_loss = 'WIN' if pnl > Money('0', 'USD') else 'LOSS'
                trade.duration = trade.exit_time - trade.entry_time
                trade.capital_end = details['capital']
                trade.drawdown = details['drawdown']
                
                # Update panel
                self.trades_panel._update_dataframe()
                
                # Send live output message
                await self.live_output.send_message(
                    level=OutputLevel.ACTION,
                    category=OutputCategory.TRADE,
                    message=f"Trade completed: {trade.side}",
                    details={
                        'trade_id': trade_id.to_string(),
                        'exit_price': exit_price.to_string(),
                        'pnl': pnl.to_string(),
                        'duration': str(trade.duration),
                        **details
                    }
                )
                break
```

### 3. Integration Tests

```python
async def test_trades_panel():
    """Test trades panel functionality"""
    logger = OptimizerLogger('test')
    trades_panel = NautilusTradesPanel(logger)
    
    # Create test trade
    trade = TradeDetails(
        trade_id=TradeId('1'),
        order_id=OrderId('1'),
        instrument_id=InstrumentId('BTC-USD'),
        entry_time=datetime.now(),
        exit_time=datetime.now() + timedelta(minutes=5),
        side='BUY',
        quantity=Quantity('1.0'),
        entry_price=Price('50000'),
        exit_price=Price('51000'),
        stop_loss=Price('49000'),
        take_profit=Price('52000'),
        commission=Money('10', 'USD'),
        slippage=Money('5', 'USD'),
        pnl=Money('985', 'USD'),
        risk_reward_ratio=Decimal('2'),
        win_loss='WIN',
        duration=timedelta(minutes=5),
        signals=[
            SignalInfo(
                name='RSI_OVERSOLD',
                block='rsi',
                timestamp=datetime.now(),
                triggered=True,
                details={'value': 25}
            ),
            SignalInfo(
                name='TREND_FILTER',
                block='trend',
                timestamp=datetime.now(),
                triggered=False,
                details={'trend': 'neutral'}
            )
        ],
        capital_start=Money('10000', 'USD'),
        capital_end=Money('10985', 'USD'),
        drawdown=Money('0', 'USD'),
        notes='Test trade'
    )
    
    # Add trade to panel
    trades_panel.add_trade(trade)
    
    # Test DataFrame creation
    df = trades_panel.get_trades_table()
    assert len(df) == 1
    assert df.iloc[0]['PnL'] == '985 USD'
    assert df.iloc[0]['Outcome'] == 'WIN'
    
    # Test filtering
    filtered = trades_panel.get_trades_table(
        filters={'Side': 'BUY'}
    )
    assert len(filtered) == 1
    
    filtered = trades_panel.get_trades_table(
        filters={'Side': 'SELL'}
    )
    assert len(filtered) == 0
    
    # Test sorting
    sorted_df = trades_panel.get_trades_table(
        sort_by='PnL',
        ascending=False
    )
    assert len(sorted_df) == 1
    
    # Test summary stats
    stats = trades_panel.get_summary_stats()
    assert stats['total_trades'] == 1
    assert stats['winning_trades'] == 1
    assert stats['win_rate'] == Decimal('1')
    assert stats['total_pnl'] == Money('985', 'USD')
    
    # Test Excel export
    trades_panel.export_to_excel('test_trades.xlsx')
    assert os.path.exists('test_trades.xlsx')
    
    # Clean up
    os.remove('test_trades.xlsx')
```

## 🔍 KEY CONSIDERATIONS

1. **Trade Information**
   - Complete trade details
   - Signal tracking
   - Capital management
   - Risk metrics

2. **Panel Features**
   - Filtering capability
   - Sorting options
   - Excel export
   - Summary statistics

3. **UI Integration**
   - Real-time updates
   - Color coding
   - Column customization
   - Auto-scrolling

4. **Data Management**
   - Type safety
   - Performance optimization
   - Memory management
   - Data persistence

## 📈 IMPLEMENTATION STEPS

1. **Setup**
   - [ ] Implement NautilusTradesPanel
   - [ ] Add UI integration
   - [ ] Create data structures
   - [ ] Add export functionality

2. **Testing**
   - [ ] Data handling tests
   - [ ] UI update tests
   - [ ] Export tests
   - [ ] Performance tests

3. **Validation**
   - [ ] Test all features
   - [ ] Verify calculations
   - [ ] Check formatting
   - [ ] Validate exports

4. **Documentation**
   - [ ] Update user guide
   - [ ] Document features
   - [ ] Add usage examples

## 🎯 EXPECTED OUTCOMES

1. **Trade Management**
   - Complete trade tracking
   - Signal association
   - Capital tracking
   - Risk monitoring

2. **UI Features**
   - Excel-like interface
   - Filtering capability
   - Sorting functionality
   - Export options

3. **Integration**
   - Live updates
   - Type safety
   - Performance optimization
   - Data persistence

## 📝 MONITORING

Monitor these aspects:
- Data accuracy
- UI responsiveness
- Memory usage
- Export performance
