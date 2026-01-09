"""
Institutional-Grade Backtest Simulator
Simulates strategy performance with real capital, leverage, fees, and comprehensive metrics.

Features:
- Starting capital tracking
- Leverage support (up to 15x)
- Trading fees (maker/taker)
- Sharpe Ratio calculation
- Complete P&L tracking
- Win/loss statistics
- Detailed trade log
- Final capital calculation
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json


@dataclass
class BacktestConfig:
    """Configuration for backtest simulation"""
    starting_capital: float = 10000.0
    max_leverage: float = 15.0
    maker_fee: float = 0.0002  # 0.02%
    taker_fee: float = 0.0005  # 0.05%
    risk_per_trade_pct: float = 1.0  # 1% of capital per trade
    use_leverage: bool = True
    compound_profits: bool = True


@dataclass
class Trade:
    """Individual trade record"""
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    side: str = 'SHORT'  # 'LONG' or 'SHORT'
    position_size_usd: float = 0.0
    position_size_btc: float = 0.0
    leverage: float = 1.0
    tp1: float = 0.0
    tp2: float = 0.0
    tp3: float = 0.0
    sl: float = 0.0
    
    # Exit details
    exit_reason: str = ''  # 'TP1', 'TP2', 'TP3', 'SL', 'MANUAL'
    
    # P&L
    gross_pnl: float = 0.0
    fees_paid: float = 0.0
    net_pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Metadata
    confluence: float = 0.0
    signals: List[str] = field(default_factory=list)


class BacktestSimulator:
    """
    Simulates strategy trading with institutional-grade metrics
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.capital = config.starting_capital
        self.starting_capital = config.starting_capital
        
        # Trade tracking
        self.trades: List[Trade] = []
        self.open_trade: Optional[Trade] = None
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.breakeven_trades = 0
        
        # P&L tracking
        self.total_gross_pnl = 0.0
        self.total_fees = 0.0
        self.total_net_pnl = 0.0
        self.peak_capital = config.starting_capital
        self.max_drawdown = 0.0
        
        # Daily returns for Sharpe
        self.daily_returns = []
        self.equity_curve = []
        
    def calculate_position_size(self, entry_price: float, sl_price: float) -> Tuple[float, float, float]:
        """
        Calculate position size based on risk management
        
        Returns:
            (position_size_usd, position_size_btc, leverage_used)
        """
        # Risk amount in USD
        risk_amount = self.capital * (self.config.risk_per_trade_pct / 100.0)
        
        # Distance to stop loss (absolute USD)
        sl_distance_usd = abs(entry_price - sl_price)
        
        # Calculate position size to risk exactly risk_amount
        # If we risk $100 and SL is $10 away, position should be such that $10 move = $100 loss
        # For BTC: if entry $50,000 and SL $49,990 ($10 away), and we want $100 risk:
        # Position in BTC = risk_amount / sl_distance_usd
        # Position in USD = (risk_amount / sl_distance_usd) * entry_price
        
        if sl_distance_usd == 0:
            # Avoid division by zero - use minimum position
            position_size_btc = 0.001
            position_size_usd = position_size_btc * entry_price
        else:
            # Calculate how many units (BTC) we need
            # If SL is $10 away and we want to risk $100, we need 10 BTC
            # Because 10 BTC * $10 move = $100 risk
            position_size_btc = risk_amount / sl_distance_usd
            position_size_usd = position_size_btc * entry_price
        
        # Apply capital constraint with leverage
        max_position_with_leverage = self.capital * self.config.max_leverage
        
        if position_size_usd > max_position_with_leverage:
            # Cap position at max leverage allows
            position_size_usd = max_position_with_leverage
            position_size_btc = position_size_usd / entry_price
        
        # Calculate actual leverage used
        leverage_used = min(position_size_usd / self.capital, self.config.max_leverage)
        
        # Ensure we never use more than max leverage
        if leverage_used > self.config.max_leverage:
            leverage_used = self.config.max_leverage
            position_size_usd = self.capital * leverage_used
            position_size_btc = position_size_usd / entry_price
        
        return position_size_usd, position_size_btc, leverage_used
    
    def open_position(self, 
                     entry_time: datetime,
                     entry_price: float,
                     side: str,
                     tp1: float,
                     tp2: float,
                     tp3: float,
                     sl: float,
                     confluence: float,
                     signals: List[str]) -> bool:
        """
        Open a new position
        
        Returns:
            True if position opened successfully, False otherwise
        """
        if self.open_trade is not None:
            return False  # Already have open position
        
        # Calculate position size
        position_usd, position_btc, leverage = self.calculate_position_size(entry_price, sl)
        
        # Entry fee (taker)
        entry_fee = position_usd * self.config.taker_fee
        
        # Check if we have enough capital for collateral + fees
        # Collateral needed = position_usd / leverage
        # But if at max leverage, reduce position to fit fees
        collateral_needed = position_usd / leverage
        total_needed = collateral_needed + entry_fee
        
        if total_needed > self.capital:
            # Reduce position to fit within capital
            available_for_position = self.capital * 0.99  # Leave 1% buffer
            # Work backwards: available = (position / leverage) + (position * fee)
            # available = position * (1/leverage + fee)
            # position = available / (1/leverage + fee)
            position_usd = available_for_position / ((1/leverage) + self.config.taker_fee)
            position_btc = position_usd / entry_price
            entry_fee = position_usd * self.config.taker_fee
        
        # Create trade
        self.open_trade = Trade(
            entry_time=entry_time,
            entry_price=entry_price,
            side=side,
            position_size_usd=position_usd,
            position_size_btc=position_btc,
            leverage=leverage,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            sl=sl,
            confluence=confluence,
            signals=signals.copy()
        )
        
        # Deduct fees immediately
        self.capital -= entry_fee
        self.total_fees += entry_fee
        
        return True
    
    def update_open_position(self, current_bar: pd.Series) -> Optional[str]:
        """
        Check if open position hits TP or SL
        
        Returns:
            Exit reason if position closed, None if still open
        """
        if self.open_trade is None:
            return None
        
        trade = self.open_trade
        current_price = current_bar['close']
        high = current_bar['high']
        low = current_bar['low']
        
        # Check for exits based on side
        if trade.side == 'SHORT':
            # SHORT trade - profit when price goes down
            
            # Check SL (price goes up)
            if high >= trade.sl:
                self.close_position(current_bar['timestamp'], trade.sl, 'SL')
                return 'SL'
            
            # Check TPs (price goes down)
            if low <= trade.tp3:
                self.close_position(current_bar['timestamp'], trade.tp3, 'TP3')
                return 'TP3'
            elif low <= trade.tp2:
                self.close_position(current_bar['timestamp'], trade.tp2, 'TP2')
                return 'TP2'
            elif low <= trade.tp1:
                self.close_position(current_bar['timestamp'], trade.tp1, 'TP1')
                return 'TP1'
                
        else:  # LONG
            # LONG trade - profit when price goes up
            
            # Check SL (price goes down)
            if low <= trade.sl:
                self.close_position(current_bar['timestamp'], trade.sl, 'SL')
                return 'SL'
            
            # Check TPs (price goes up)
            if high >= trade.tp3:
                self.close_position(current_bar['timestamp'], trade.tp3, 'TP3')
                return 'TP3'
            elif high >= trade.tp2:
                self.close_position(current_bar['timestamp'], trade.tp2, 'TP2')
                return 'TP2'
            elif high >= trade.tp1:
                self.close_position(current_bar['timestamp'], trade.tp1, 'TP1')
                return 'TP1'
        
        return None
    
    def close_position(self, exit_time: datetime, exit_price: float, exit_reason: str):
        """Close the open position and calculate P&L"""
        if self.open_trade is None:
            return
        
        trade = self.open_trade
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        
        # Calculate P&L
        if trade.side == 'SHORT':
            # SHORT: profit when price goes down
            price_change_pct = (trade.entry_price - exit_price) / trade.entry_price
        else:  # LONG
            # LONG: profit when price goes up
            price_change_pct = (exit_price - trade.entry_price) / trade.entry_price
        
        # Gross P&L (with leverage)
        trade.gross_pnl = trade.position_size_usd * price_change_pct
        
        # Exit fee
        exit_fee = trade.position_size_usd * self.config.taker_fee
        trade.fees_paid = exit_fee
        
        # Net P&L
        trade.net_pnl = trade.gross_pnl - exit_fee
        trade.pnl_pct = (trade.net_pnl / (trade.position_size_usd / trade.leverage)) * 100
        
        # Update capital
        self.capital += trade.net_pnl
        self.total_fees += exit_fee
        self.total_gross_pnl += trade.gross_pnl
        self.total_net_pnl += trade.net_pnl
        
        # Update statistics
        self.total_trades += 1
        if trade.net_pnl > 0:
            self.winning_trades += 1
        elif trade.net_pnl < 0:
            self.losing_trades += 1
        else:
            self.breakeven_trades += 1
        
        # Track drawdown
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
        else:
            current_drawdown = (self.peak_capital - self.capital) / self.peak_capital
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
        
        # Save trade
        self.trades.append(trade)
        self.open_trade = None
        
        # Track equity
        self.equity_curve.append({
            'timestamp': exit_time,
            'capital': self.capital,
            'trade_pnl': trade.net_pnl
        })
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe Ratio from trade returns"""
        if len(self.trades) < 2:
            return 0.0
        
        # Calculate returns per trade
        returns = [t.pnl_pct for t in self.trades]
        
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe (assuming ~2-4 trades/month = ~30 trades/year)
        sharpe = (mean_return - risk_free_rate) / std_return
        annualized_sharpe = sharpe * np.sqrt(30)  # Approximate annualization
        
        return annualized_sharpe
    
    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics"""
        
        # Win rate
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # Average win/loss
        winning_pnls = [t.net_pnl for t in self.trades if t.net_pnl > 0]
        losing_pnls = [t.net_pnl for t in self.trades if t.net_pnl < 0]
        
        avg_win = np.mean(winning_pnls) if winning_pnls else 0
        avg_loss = np.mean(losing_pnls) if losing_pnls else 0
        
        # Profit factor
        total_wins = sum(winning_pnls) if winning_pnls else 0
        total_losses = abs(sum(losing_pnls)) if losing_pnls else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Returns
        total_return_pct = ((self.capital - self.starting_capital) / self.starting_capital) * 100
        
        # Sharpe
        sharpe = self.calculate_sharpe_ratio()
        
        return {
            'starting_capital': self.starting_capital,
            'final_capital': self.capital,
            'total_return_usd': self.capital - self.starting_capital,
            'total_return_pct': total_return_pct,
            'max_drawdown_pct': self.max_drawdown * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': win_rate,
            'avg_win_usd': avg_win,
            'avg_loss_usd': avg_loss,
            'profit_factor': profit_factor,
            'total_fees_paid': self.total_fees,
            'sharpe_ratio': sharpe,
            'total_gross_pnl': self.total_gross_pnl,
            'total_net_pnl': self.total_net_pnl
        }
    
    def get_trade_log(self) -> List[Dict]:
        """Get detailed trade log"""
        return [{
            'entry_time': t.entry_time.isoformat() if isinstance(t.entry_time, datetime) else str(t.entry_time),
            'exit_time': t.exit_time.isoformat() if isinstance(t.exit_time, datetime) else str(t.exit_time),
            'side': t.side,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'position_size_usd': t.position_size_usd,
            'position_size_btc': t.position_size_btc,
            'leverage': t.leverage,
            'exit_reason': t.exit_reason,
            'gross_pnl': t.gross_pnl,
            'fees_paid': t.fees_paid,
            'net_pnl': t.net_pnl,
            'pnl_pct': t.pnl_pct,
            'confluence': t.confluence,
            'tp1': t.tp1,
            'tp2': t.tp2,
            'tp3': t.tp3,
            'sl': t.sl
        } for t in self.trades]
    
    def print_summary(self):
        """Print comprehensive backtest summary"""
        metrics = self.get_performance_metrics()
        
        print("\n" + "="*80)
        print("BACKTEST RESULTS - INSTITUTIONAL GRADE")
        print("="*80)
        
        print("\n💰 CAPITAL & RETURNS")
        print(f"Starting Capital:     ${metrics['starting_capital']:,.2f}")
        print(f"Final Capital:        ${metrics['final_capital']:,.2f}")
        print(f"Total Return:         ${metrics['total_return_usd']:,.2f} ({metrics['total_return_pct']:.2f}%)")
        print(f"Max Drawdown:         {metrics['max_drawdown_pct']:.2f}%")
        
        print("\n📊 TRADE STATISTICS")
        print(f"Total Trades:         {metrics['total_trades']}")
        print(f"Winning Trades:       {metrics['winning_trades']}")
        print(f"Losing Trades:        {metrics['losing_trades']}")
        print(f"Win Rate:             {metrics['win_rate_pct']:.2f}%")
        
        print("\n💵 PROFIT & LOSS")
        print(f"Gross P&L:            ${metrics['total_gross_pnl']:,.2f}")
        print(f"Total Fees:           ${metrics['total_fees_paid']:,.2f}")
        print(f"Net P&L:              ${metrics['total_net_pnl']:,.2f}")
        print(f"Average Win:          ${metrics['avg_win_usd']:,.2f}")
        print(f"Average Loss:         ${metrics['avg_loss_usd']:,.2f}")
        print(f"Profit Factor:        {metrics['profit_factor']:.2f}")
        
        print("\n📈 RISK METRICS")
        print(f"Sharpe Ratio:         {metrics['sharpe_ratio']:.2f}")
        print(f"Max Leverage Used:    {self.config.max_leverage}x")
        print(f"Risk Per Trade:       {self.config.risk_per_trade_pct}%")
        
        print("\n" + "="*80)