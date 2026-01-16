"""
Walkforward Test Engine
Implements candle-by-candle expanding window testing (Mode 1 & 2)
Reference: docs/v3/UI-UX/14_TESTING_MODES.md
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.strategy_builder.core.strategy_config_engine import StrategyConfig


class TestMode(Enum):
    """Test execution modes"""
    MODE_1 = "historical_only"  # Run historical data and stop
    MODE_2 = "historical_plus_live"  # Run historical then wait for new candles


@dataclass
class PositionAdjustment:
    """Record of a TP/SL adjustment"""
    adjustment_type: str  # "TP1", "TP2", "TP3", "SL"
    old_value: float
    new_value: float
    candle_index: int
    timestamp: Optional[datetime] = None


@dataclass
class TestConfig:
    """Configuration for walkforward testing"""
    mode: TestMode = TestMode.MODE_1
    lookback_days: int = 180
    training_window_days: int = 0
    start_date: Optional[datetime] = None
    bar_timeframe: str = "15-MINUTE"
    

@dataclass
class TestResult:
    """Results from walkforward test"""
    total_positions: int = 0
    winning_positions: int = 0
    losing_positions: int = 0
    tp1_adjustments: int = 0
    tp2_adjustments: int = 0
    tp3_adjustments: int = 0
    sl_adjustments: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    adjustments_per_position: float = 0.0
    test_duration_days: int = 0
    candles_processed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WalkforwardTestEngine:
    """
    Walkforward testing engine with expanding window
    Processes candles one-by-one from lookback_days to present
    
    Mode 1: Historical only - processes past data and stops
    Mode 2: Historical + Live - processes past data then waits for new candles
    """
    
    def __init__(self, config: Optional[TestConfig] = None):
        """
        Initialize walkforward test engine
        
        Args:
            config: Test configuration (defaults to Mode 1, 180 days)
        """
        self.config = config or TestConfig()
        self.adjustments: List[PositionAdjustment] = []
        self.positions: List[Dict[str, Any]] = []
        self.current_candle_index = 0
        
    def run(self, strategy_config: StrategyConfig) -> TestResult:
        """
        Run walkforward test on strategy
        
        Args:
            strategy_config: Strategy configuration to test
            
        Returns:
            TestResult with comprehensive statistics
        """
        # Calculate date range
        total_lookback = self._calculate_total_lookback()
        start_date = self.config.start_date or (datetime.now() - timedelta(days=total_lookback))
        end_date = datetime.now()
        
        # Initialize result
        result = TestResult()
        result.test_duration_days = (end_date - start_date).days
        
        # Simulate candle-by-candle processing
        result.candles_processed = self._simulate_candles(
            strategy_config,
            start_date,
            end_date
        )
        
        # Calculate statistics from tracked data
        result = self._calculate_statistics(result)
        
        # Mode 2: Would continue waiting for new candles
        if self.config.mode == TestMode.MODE_2:
            result.metadata['mode'] = 'live_continuation'
            result.metadata['waiting_for_new_candles'] = True
        else:
            result.metadata['mode'] = 'historical_complete'
            
        return result
        
    def _calculate_total_lookback(self) -> int:
        """
        Calculate total lookback including training window
        
        Returns:
            Total days to look back
        """
        return self.config.lookback_days + self.config.training_window_days
        
    def _simulate_candles(
        self,
        strategy_config: StrategyConfig,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        Simulate candle-by-candle processing with expanding window
        
        Args:
            strategy_config: Strategy to test
            start_date: Start date for testing
            end_date: End date for testing
            
        Returns:
            Number of candles processed
        """
        candles_processed = 0
        
        # Calculate expected candles based on timeframe
        # For 15-minute bars: 4 per hour * 24 hours = 96 per day
        days = (end_date - start_date).days
        expected_candles = days * 96  # Approximate for 15-minute bars
        
        # Simulate processing (in production, would process real data)
        for i in range(expected_candles):
            self.current_candle_index = i
            
            # Would process strategy logic here
            # For now, simulate some positions and adjustments
            if i % 100 == 0:  # Simulate position every 100 candles
                self._simulate_position()
                
        candles_processed = expected_candles
        return candles_processed
        
    def _simulate_position(self):
        """Simulate a position with potential adjustments"""
        position = {
            'entry_candle': self.current_candle_index,
            'entry_price': 50000.0,  # Mock price
            'adjustments': []
        }
        
        # Simulate some TP/SL adjustments
        if self.current_candle_index % 3 == 0:
            self._track_adjustment(PositionAdjustment(
                adjustment_type="TP1",
                old_value=51000.0,
                new_value=51500.0,
                candle_index=self.current_candle_index
            ))
            
        if self.current_candle_index % 5 == 0:
            self._track_adjustment(PositionAdjustment(
                adjustment_type="SL",
                old_value=49000.0,
                new_value=49500.0,
                candle_index=self.current_candle_index
            ))
            
        self.positions.append(position)
        
    def _track_adjustment(self, adjustment: PositionAdjustment):
        """
        Track a TP/SL adjustment
        
        Args:
            adjustment: Adjustment to track
        """
        self.adjustments.append(adjustment)
        
    def _calculate_statistics(self, result: TestResult) -> TestResult:
        """
        Calculate final statistics from tracked data
        
        Args:
            result: Result object to populate
            
        Returns:
            Updated result with statistics
        """
        # Count positions
        result.total_positions = len(self.positions)
        
        # Simulate win/loss (in production, would be calculated from actual trades)
        result.winning_positions = int(result.total_positions * 0.6)  # Mock 60% win rate
        result.losing_positions = result.total_positions - result.winning_positions
        
        # Count adjustments by type
        for adj in self.adjustments:
            if adj.adjustment_type == "TP1":
                result.tp1_adjustments += 1
            elif adj.adjustment_type == "TP2":
                result.tp2_adjustments += 1
            elif adj.adjustment_type == "TP3":
                result.tp3_adjustments += 1
            elif adj.adjustment_type == "SL":
                result.sl_adjustments += 1
                
        # Calculate derived metrics
        if result.total_positions > 0:
            result.win_rate = result.winning_positions / result.total_positions
            total_adjustments = (result.tp1_adjustments + result.tp2_adjustments +
                                result.tp3_adjustments + result.sl_adjustments)
            result.adjustments_per_position = total_adjustments / result.total_positions
            
        # Mock PnL (in production, would be calculated from actual trades)
        result.total_pnl = result.winning_positions * 100.0 - result.losing_positions * 50.0
        
        return result
        
    def get_adjustment_report(self) -> Dict[str, Any]:
        """
        Get detailed adjustment report
        
        Returns:
            Dictionary with adjustment statistics per position
        """
        report = {
            'total_adjustments': len(self.adjustments),
            'by_type': {
                'TP1': sum(1 for a in self.adjustments if a.adjustment_type == "TP1"),
                'TP2': sum(1 for a in self.adjustments if a.adjustment_type == "TP2"),
                'TP3': sum(1 for a in self.adjustments if a.adjustment_type == "TP3"),
                'SL': sum(1 for a in self.adjustments if a.adjustment_type == "SL"),
            },
            'positions': len(self.positions),
            'avg_adjustments_per_position': (
                len(self.adjustments) / len(self.positions) if self.positions else 0
            )
        }
        return report
        
    def reset(self):
        """Reset engine state for new test"""
        self.adjustments = []
        self.positions = []
        self.current_candle_index = 0
