"""
Data Classes for Universal Optimizer

Contains all data structures used throughout the optimizer.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class OptimizationConfig:
    """Configuration for a single optimization test (ENHANCED with Dynamic TPs + Parameter Testing)"""
    config_id: int
    min_confluence: int
    min_risk_reward: float
    blocks: Dict[str, Dict]  # {block_name: {name, weight, enabled}}
    strategy_id: str
    strategy_name: str
    side: str
    tp_mode: str = 'PERCENTAGE'  # TP calculation method: 'PERCENTAGE', 'FIBONACCI', 'HYBRID'
    sl_mode: str = 'ADAPTIVE'  # SL calculation method: 'ADAPTIVE' (v2.0), 'HYBRID' (v1.0 - deprecated)
    trailing_pct: float = 0.6  # Trailing stop distance after TP2 (0.5%, 0.6%, 0.8%)
    use_trailing: bool = True  # Enable trailing stops
    breakeven_after_tp1: bool = True  # Move SL to breakeven after TP1
    tp_fallback_pcts: Dict[str, float] = None  # {'tp1': 1.0, 'tp2': 2.0, 'tp3': 3.5} - TP distances
    partial_exit_pcts: Dict[str, int] = None  # {'tp1': 50, 'tp2': 30, 'tp3': 20} - Exit splits
    
    # ⭐ ADAPTIVE SL v2.0 PARAMETERS (NEW)
    # Volatility Settings
    volatility_lookback: int = 20  # Bars for volatility calculation
    volatility_multiplier: float = 1.2  # Min SL = avg_range * this
    
    # Bounds
    absolute_min_sl_pct: float = 0.7  # Never tighter than 0.7%
    absolute_max_sl_pct: float = 2.0  # Never wider than 2.0%
    
    # Two-Stage SL
    initial_sl_multiplier: float = 1.5  # Initial SL = volatility * 1.5
    working_sl_multiplier: float = 1.0  # Working SL = volatility * 1.0
    
    # Delayed SL Activation (Your Enhancement!)
    use_delayed_sl: bool = True  # Enable delayed SL activation
    delay_bars: int = 2  # Wait N bars before tight SL (2-3 recommended for BTC 15min)
    emergency_sl_pct: float = 2.5  # Wide emergency SL during delay period
    
    # Structure-Based SL
    use_structure_sl: bool = True  # Use market structure when available
    structure_sources: List[str] = None  # ['swing_points', 'supply_demand', 'fibonacci']
    
    # ⭐ RISK MANAGEMENT PARAMETERS (CRITICAL - READ FROM YAML CONFIG)
    starting_capital: float = 10000.0  # Starting account balance
    max_leverage: float = 10.0  # Maximum leverage allowed
    risk_per_trade_pct: float = 1.0  # Risk per trade as percentage of capital
    
    def __post_init__(self):
        """Set default values for dict fields and lists"""
        if self.tp_fallback_pcts is None:
            self.tp_fallback_pcts = {'tp1': 1.0, 'tp2': 2.0, 'tp3': 3.5}
        if self.partial_exit_pcts is None:
            self.partial_exit_pcts = {'tp1': 50, 'tp2': 30, 'tp3': 20}
        if self.structure_sources is None:
            self.structure_sources = ['swing_points', 'supply_demand', 'fibonacci']
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TradeResult:
    """Result of a single trade"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    side: str
    pnl: float
    pnl_pct: float
    fees: float
    net_pnl: float
    confluence: int
    reason: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary with datetime serialization"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat() if self.entry_time else None
        data['exit_time'] = self.exit_time.isoformat() if self.exit_time else None
        return data


@dataclass
class ConfigPerformance:
    """Performance metrics for a configuration"""
    config_id: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    total_fees: float
    net_pnl: float
    net_return_pct: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    trades: List[TradeResult] = field(default_factory=list)
    
    def to_dict(self, include_trades: bool = True) -> dict:
        """Convert to dictionary"""
        data = {
            'config_id': self.config_id,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': self.win_rate_pct,
            'total_pnl': self.total_pnl,
            'total_fees': self.total_fees,
            'net_pnl': self.net_pnl,
            'net_return_pct': self.net_return_pct,
            'profit_factor': self.profit_factor,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown_pct': self.max_drawdown_pct,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
        }
        
        if include_trades:
            data['trades'] = [t.to_dict() for t in self.trades]
        
        return data
    
    def get_sortable_score(self) -> float:
        """
        Calculate sortable score for ranking configurations
        
        Prioritizes:
        1. Profit Factor (40%)
        2. Net PnL (30%)
        3. Sharpe Ratio (20%)
        4. Win Rate (10%)
        """
        pf_score = min(self.profit_factor / 3.0, 1.0) * 40
        pnl_score = min(self.net_return_pct / 100.0, 1.0) * 30
        sharpe_score = min(self.sharpe_ratio / 2.0, 1.0) * 20
        wr_score = (self.win_rate_pct / 100.0) * 10
        
        return pf_score + pnl_score + sharpe_score + wr_score


@dataclass
class BlockPerformance:
    """Performance metrics for a single building block"""
    block_name: str
    total_uses: int = 0
    successful_uses: int = 0
    avg_contribution: float = 0.0
    avg_weight: float = 0.0
    success_rate: float = 0.0
    confidence_avg: float = 0.0
    
    def update(self, contribution: float, weight: int, confidence: float, successful: bool):
        """Update performance metrics"""
        self.total_uses += 1
        if successful:
            self.successful_uses += 1
        
        # Running average
        self.avg_contribution = (
            (self.avg_contribution * (self.total_uses - 1) + contribution) /
            self.total_uses
        )
        self.avg_weight = (
            (self.avg_weight * (self.total_uses - 1) + weight) /
            self.total_uses
        )
        self.confidence_avg = (
            (self.confidence_avg * (self.total_uses - 1) + confidence) /
            self.total_uses
        )
        self.success_rate = self.successful_uses / self.total_uses * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class StrategyIteration:
    """Track optimization iterations for a strategy"""
    strategy_id: str
    iteration_count: int = 0
    best_config: Optional[Dict] = None
    best_performance: Optional[Dict] = None
    iteration_history: List[Dict] = field(default_factory=list)
    block_performance: Dict[str, BlockPerformance] = field(default_factory=dict)
    
    def add_iteration(self, config: Dict, performance: ConfigPerformance):
        """Add new iteration"""
        self.iteration_count += 1
        self.iteration_history.append({
            'iteration': self.iteration_count,
            'timestamp': datetime.now().isoformat(),
            'config': config,
            'performance': performance.to_dict(include_trades=False)
        })
        
        # Update best if better
        if (self.best_performance is None or 
            performance.get_sortable_score() > self.best_performance.get('score', 0)):
            self.best_config = config
            self.best_performance = {
                'score': performance.get_sortable_score(),
                **performance.to_dict(include_trades=False)
            }
    
    def get_weakest_block(self) -> Optional[str]:
        """
        Identify weakest performing block
        
        Returns:
            Block name or None
        """
        if not self.block_performance:
            return None
        
        # Sort by success rate
        sorted_blocks = sorted(
            self.block_performance.items(),
            key=lambda x: x[1].success_rate
        )
        
        if sorted_blocks:
            return sorted_blocks[0][0]
        
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'strategy_id': self.strategy_id,
            'iteration_count': self.iteration_count,
            'best_config': self.best_config,
            'best_performance': self.best_performance,
            'iteration_history': self.iteration_history,
            'block_performance': {
                k: v.to_dict() for k, v in self.block_performance.items()
            }
        }
