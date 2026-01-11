"""
Data Classes for Universal Optimizer

Contains all data structures used throughout the optimizer.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class OptimizationConfig:
    """
    Configuration for a single optimization test - INSTITUTIONAL GRADE
    
    ⚠️ CRITICAL: NO DEFAULTS! All values MUST come from strategy YAML config.
    This ensures 100% parameter integrity with zero cross-contamination.
    """
    # Required core parameters
    config_id: int
    min_confluence: int
    min_risk_reward: float
    blocks: Dict[str, Dict]
    strategy_id: str
    strategy_name: str
    side: str
    
    # TP/SL modes (MUST be from YAML)
    tp_mode: str
    sl_mode: str
    
    # Trailing & breakeven (MUST be from YAML)
    trailing_pct: float
    use_trailing: bool
    breakeven_after_tp1: bool
    
    # TP/Exit settings (MUST be from YAML)
    tp_fallback_pcts: Dict[str, float]
    partial_exit_pcts: Dict[str, int]
    
    # Adaptive SL v2.0 - Volatility (MUST be from YAML)
    volatility_lookback: int
    volatility_multiplier: float
    
    # Adaptive SL v2.0 - Bounds (MUST be from YAML)
    absolute_min_sl_pct: float
    absolute_max_sl_pct: float
    
    # Adaptive SL v2.0 - Two-Stage SL (MUST be from YAML)
    initial_sl_multiplier: float
    working_sl_multiplier: float
    
    # Adaptive SL v2.0 - Delayed Activation (MUST be from YAML)
    use_delayed_sl: bool
    delay_bars: int
    emergency_sl_pct: float
    
    # Adaptive SL v2.0 - Structure-Based (MUST be from YAML)
    use_structure_sl: bool
    structure_sources: List[str]
    
    # Risk Management (MUST be from YAML - CRITICAL!)
    starting_capital: float
    max_leverage: float
    risk_per_trade_pct: float
    
    def __post_init__(self):
        """
        Validate that all required parameters are present.
        NO DEFAULTS - all values must come from YAML config!
        """
        # Validate critical parameters are not None
        required_params = [
            'config_id', 'min_confluence', 'min_risk_reward', 'blocks',
            'strategy_id', 'strategy_name', 'side', 'tp_mode', 'sl_mode',
            'trailing_pct', 'use_trailing', 'breakeven_after_tp1',
            'tp_fallback_pcts', 'partial_exit_pcts',
            'volatility_lookback', 'volatility_multiplier',
            'absolute_min_sl_pct', 'absolute_max_sl_pct',
            'initial_sl_multiplier', 'working_sl_multiplier',
            'use_delayed_sl', 'delay_bars', 'emergency_sl_pct',
            'use_structure_sl', 'structure_sources',
            'starting_capital', 'max_leverage', 'risk_per_trade_pct'
        ]
        
        for param in required_params:
            value = getattr(self, param, None)
            if value is None:
                raise ValueError(
                    f"❌ CRITICAL: Parameter '{param}' is None! "
                    f"All parameters must be explicitly provided from YAML config. "
                    f"Strategy: {self.strategy_name} (ID: {self.strategy_id})"
                )
    
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
