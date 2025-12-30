"""
Pattern Statistics - TradingView Statistical Pattern Matching

Implements the revolutionary 64x3 matrix approach from TradingView:
- Encodes pattern combinations (trend/price/osc) to 0-63 indices
- Tracks historical outcomes (HH/LH for highs, LL/HL for lows)
- Stores Fibonacci ratios and bar counts
- Predicts next pivot based on probabilities

Based on: TradingView_Scripts/next_pivot_projection.pine
Author: BTC Scalp Bot V10 Framework
Version: 1.0.0
Date: December 30, 2025
"""

import pandas as pd
import numpy as np
import pickle
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path

from .zigzag_detector import Pivot, PivotType
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PatternProjection:
    """
    Projected next pivot based on historical patterns
    
    Attributes:
        hh_probability: Probability of Higher High (for pivot highs)
        lh_probability: Probability of Lower High (for pivot highs)
        ll_probability: Probability of Lower Low (for pivot lows)
        hl_probability: Probability of Higher Low (for pivot lows)
        dominant_outcome: The most likely outcome ('HH', 'LH', 'LL', 'HL')
        avg_fib_ratio: Average Fibonacci ratio for dominant outcome
        expected_bars: Expected bars to next pivot
        historical_samples: Number of historical samples for this pattern
        confidence: Confidence in prediction (0-1) based on sample size
    """
    hh_probability: float = 0.0
    lh_probability: float = 0.0
    ll_probability: float = 0.0
    hl_probability: float = 0.0
    dominant_outcome: str = ""
    avg_fib_ratio: float = 1.0
    expected_bars: int = 10
    historical_samples: int = 0
    confidence: float = 0.0
    
    def __str__(self) -> str:
        return (f"Projection({self.dominant_outcome}: "
                f"{self.hh_probability or self.ll_probability:.1%}, "
                f"ratio={self.avg_fib_ratio:.3f}, "
                f"bars={self.expected_bars}, "
                f"samples={self.historical_samples})")


class PatternStatistics:
    """
    Statistical pattern matcher using 64x3 matrix approach
    
    The genius of TradingView's approach:
    - Each pattern combination gets an index 0-63
    - Pattern = Trend direction (U/D) + Price pattern (HH/LH) + Osc pattern (HH/LH)
    - For each pattern, track what happened historically
    - Use probabilities to predict next pivot
    
    Matrix Structure:
    - Rows: 64 possible pattern combinations
    - Columns: [outcome1_count, outcome2_count, total_count]
      * For pivot highs: [HH_count, LH_count, total]
      * For pivot lows: [LL_count, HL_count, total]
    
    Additional Matrices:
    - Ratios: [avg_ratio_outcome1, avg_ratio_outcome2, avg_ratio_total]
    - Bars: [avg_bars_outcome1, avg_bars_outcome2, avg_bars_total]
    
    Pattern Index Encoding (0-63):
    - Bit 0: Oscillator pattern (0=Lower, 1=Higher)
    - Bit 1: Price pattern (0=Lower, 1=Higher)
    - Bit 2: Trend direction (0=Up, 1=Down)
    - Index = trend*4 + price*2 + osc
    
    Example: U-HH/HH = 0*4 + 1*2 + 1 = 3
    Example: D-LH/LH = 1*4 + 0*2 + 0 = 4
    """
    
    def __init__(self, min_samples: int = 10):
        """
        Initialize PatternStatistics
        
        Args:
            min_samples: Minimum historical samples before trusting prediction
        """
        self.min_samples = min_samples
        
        # 64x3 matrices for pivot highs
        self.pivot_high_stats = np.zeros((64, 3), dtype=np.int32)
        self.pivot_high_ratios = np.zeros((64, 3), dtype=np.float64)
        self.pivot_high_bars = np.zeros((64, 3), dtype=np.float64)
        
        # 64x3 matrices for pivot lows
        self.pivot_low_stats = np.zeros((64, 3), dtype=np.int32)
        self.pivot_low_ratios = np.zeros((64, 3), dtype=np.float64)
        self.pivot_low_bars = np.zeros((64, 3), dtype=np.float64)
        
        logger.info(f"PatternStatistics initialized (min_samples={min_samples})")
    
    def encode_pattern(
        self,
        price_dir: int,
        osc_dir: int,
        trend_dir: int
    ) -> int:
        """
        Encode pattern to 0-63 index
        
        Args:
            price_dir: Price direction (-1=Lower, +1=Higher, 0=equal)
            osc_dir: Oscillator direction (-1=Lower, +1=Higher, 0=equal)
            trend_dir: Trend direction (-1=Down, +1=Up, 0=neutral)
            
        Returns:
            Pattern index 0-63
        """
        trend_bit = 0 if trend_dir > 0 else 1
        price_bit = 1 if abs(price_dir) > 0 and price_dir > 0 else 0
        osc_bit = 1 if abs(osc_dir) > 0 and osc_dir > 0 else 0
        
        index = trend_bit * 4 + price_bit * 2 + osc_bit
        
        return int(index)
    
    def get_pattern_index_from_sequence(
        self,
        last_pattern: str,
        llast_pattern: str,
        trend: int
    ) -> int:
        """
        Get pattern index from pattern sequence
        
        Args:
            last_pattern: Last pattern ('HH', 'LH', 'LL', 'HL')
            llast_pattern: Pattern before last
            trend: Current trend direction
            
        Returns:
            Combined pattern index for statistics lookup
        """
        # Encode last pattern (current)
        if last_pattern in ['HH']:
            price_dir = 1
        elif last_pattern in ['LH']:
            price_dir = -1
        elif last_pattern in ['LL']:
            price_dir = -1
        elif last_pattern in ['HL']:
            price_dir = 1
        else:
            price_dir = 0
        
        # For simplicity, assume osc follows price (will be overridden with real data)
        osc_dir = price_dir
        
        # Encode
        last_idx = self.encode_pattern(price_dir, osc_dir, trend)
        
        # Encode previous pattern
        if llast_pattern in ['HH']:
            pprice_dir = 1
        elif llast_pattern in ['LH']:
            pprice_dir = -1
        elif llast_pattern in ['LL']:
            pprice_dir = -1
        elif llast_pattern in ['HL']:
            pprice_dir = 1
        else:
            pprice_dir = 0
        
        posc_dir = pprice_dir
        llast_idx = self.encode_pattern(pprice_dir, posc_dir, trend)
        
        # Combine: last*8 + llast (creates wider index space like TradingView)
        combined_idx = last_idx * 8 + llast_idx
        # Map back to 0-63 (simplified - in real impl we'd use larger matrix)
        return combined_idx % 64
    
    def update_outcome(
        self,
        pattern_idx: int,
        pivot_type: PivotType,
        outcome_type: str,
        fib_ratio: float,
        bars: int
    ) -> None:
        """
        Update statistics with historical outcome
        
        Args:
            pattern_idx: Pattern index (0-63)
            pivot_type: HIGH or LOW
            outcome_type: 'HH', 'LH', 'LL', or 'HL'
            fib_ratio: Fibonacci ratio (price change / previous move)
            bars: Number of bars to this pivot
        """
        if pivot_type == PivotType.HIGH:
            col = 0 if outcome_type == 'HH' else 1
            
            # Update counts
            self.pivot_high_stats[pattern_idx, col] += 1
            self.pivot_high_stats[pattern_idx, 2] += 1
            
            # Update ratios (running sum, will average later)
            self.pivot_high_ratios[pattern_idx, col] += fib_ratio
            self.pivot_high_ratios[pattern_idx, 2] += fib_ratio
            
            # Update bars
            self.pivot_high_bars[pattern_idx, col] += bars
            self.pivot_high_bars[pattern_idx, 2] += bars
        
        else:  # PivotType.LOW
            col = 0 if outcome_type == 'LL' else 1
            
            # Update counts
            self.pivot_low_stats[pattern_idx, col] += 1
            self.pivot_low_stats[pattern_idx, 2] += 1
            
            # Update ratios
            self.pivot_low_ratios[pattern_idx, col] += fib_ratio
            self.pivot_low_ratios[pattern_idx, 2] += fib_ratio
            
            # Update bars
            self.pivot_low_bars[pattern_idx, col] += bars
            self.pivot_low_bars[pattern_idx, 2] += bars
    
    def predict_next_pivot(
        self,
        pattern_idx: int,
        pivot_type: PivotType
    ) -> PatternProjection:
        """
        Predict next pivot based on historical statistics
        
        Args:
            pattern_idx: Current pattern index (0-63)
            pivot_type: Whether we're predicting next HIGH or LOW
            
        Returns:
            PatternProjection with probabilities and expectations
        """
        if pivot_type == PivotType.HIGH:
            stats = self.pivot_high_stats[pattern_idx]
            ratios = self.pivot_high_ratios[pattern_idx]
            bars = self.pivot_high_bars[pattern_idx]
            
            hh_count = stats[0]
            lh_count = stats[1]
            total = stats[2]
            
            if total == 0:
                return self._default_projection(pivot_type)
            
            # Calculate probabilities
            hh_prob = hh_count / total
            lh_prob = lh_count / total
            
            # Get average ratios and bars
            if hh_count > 0:
                hh_ratio = ratios[0] / hh_count
                hh_bars = bars[0] / hh_count
            else:
                hh_ratio = 1.0
                hh_bars = 10
            
            if lh_count > 0:
                lh_ratio = ratios[1] / lh_count
                lh_bars = bars[1] / lh_count
            else:
                lh_ratio = 1.0
                lh_bars = 10
            
            # Determine dominant outcome
            if hh_prob > lh_prob:
                dominant = 'HH'
                dominant_ratio = hh_ratio
                dominant_bars = hh_bars
                dominant_prob = hh_prob
            else:
                dominant = 'LH'
                dominant_ratio = lh_ratio
                dominant_bars = lh_bars
                dominant_prob = lh_prob
            
            # Calculate confidence based on sample size
            confidence = min(total / (self.min_samples * 2), 1.0)
            
            return PatternProjection(
                hh_probability=hh_prob,
                lh_probability=lh_prob,
                dominant_outcome=dominant,
                avg_fib_ratio=dominant_ratio,
                expected_bars=int(dominant_bars),
                historical_samples=int(total),
                confidence=confidence
            )
        
        else:  # PivotType.LOW
            stats = self.pivot_low_stats[pattern_idx]
            ratios = self.pivot_low_ratios[pattern_idx]
            bars = self.pivot_low_bars[pattern_idx]
            
            ll_count = stats[0]
            hl_count = stats[1]
            total = stats[2]
            
            if total == 0:
                return self._default_projection(pivot_type)
            
            # Calculate probabilities
            ll_prob = ll_count / total
            hl_prob = hl_count / total
            
            # Get average ratios and bars
            if ll_count > 0:
                ll_ratio = ratios[0] / ll_count
                ll_bars = bars[0] / ll_count
            else:
                ll_ratio = 1.0
                ll_bars = 10
            
            if hl_count > 0:
                hl_ratio = ratios[1] / hl_count
                hl_bars = bars[1] / hl_count
            else:
                hl_ratio = 1.0
                hl_bars = 10
            
            # Determine dominant outcome
            if ll_prob > hl_prob:
                dominant = 'LL'
                dominant_ratio = ll_ratio
                dominant_bars = ll_bars
                dominant_prob = ll_prob
            else:
                dominant = 'HL'
                dominant_ratio = hl_ratio
                dominant_bars = hl_bars
                dominant_prob = hl_prob
            
            # Calculate confidence
            confidence = min(total / (self.min_samples * 2), 1.0)
            
            return PatternProjection(
                ll_probability=ll_prob,
                hl_probability=hl_prob,
                dominant_outcome=dominant,
                avg_fib_ratio=dominant_ratio,
                expected_bars=int(dominant_bars),
                historical_samples=int(total),
                confidence=confidence
            )
    
    def _default_projection(self, pivot_type: PivotType) -> PatternProjection:
        """Return default projection when no historical data"""
        return PatternProjection(
            hh_probability=0.50 if pivot_type == PivotType.HIGH else 0.0,
            lh_probability=0.50 if pivot_type == PivotType.HIGH else 0.0,
            ll_probability=0.50 if pivot_type == PivotType.LOW else 0.0,
            hl_probability=0.50 if pivot_type == PivotType.LOW else 0.0,
            dominant_outcome='HH' if pivot_type == PivotType.HIGH else 'LL',
            avg_fib_ratio=1.0,
            expected_bars=10,
            historical_samples=0,
            confidence=0.0
        )
    
    def train_on_historical_data(
        self,
        data: pd.DataFrame,
        zigzag_detector,
        divergence_detector
    ) -> None:
        """
        Train statistics on historical data
        
        Args:
            data: Historical OHLCV data
            zigzag_detector: ZigzagDetector instance
            divergence_detector: DivergenceDetector instance
        """
        logger.info(f"Training pattern statistics on {len(data)} bars of historical data...")
        
        # Find all pivots
        pivots = zigzag_detector.find_pivots(data)
        
        logger.info(f"Found {len(pivots)} zigzag pivots")
        
        if len(pivots) < 4:
            logger.warning(f"Insufficient pivots for training: {len(pivots)} < 4")
            return
        
        # Calculate oscillator
        osc_data = divergence_detector.calculate_oscillator(data)
        
        # Estimate trend (simple: compare to SMA)
        sma_50 = data['close'].rolling(50).mean()
        
        # Process pivot sequences
        # Zigzag alternates H-L-H-L, so we need to look at every other pivot of same type
        # For each pivot, find the previous and next pivot of the SAME type
        
        for i in range(len(pivots)):
            curr_pivot = pivots[i]
            
            # Find previous pivot of same type
            prev_same = None
            for j in range(i - 1, -1, -1):
                if pivots[j].pivot_type == curr_pivot.pivot_type:
                    prev_same = pivots[j]
                    break
            
            # Find next pivot of same type  
            next_same = None
            for j in range(i + 1, len(pivots)):
                if pivots[j].pivot_type == curr_pivot.pivot_type:
                    next_same = pivots[j]
                    break
            
            # Need all three: prev_same -> curr -> next_same
            if prev_same is None or next_same is None:
                continue
            
            # Now analyze the pattern: prev_same -> curr_pivot -> next_same (all same type)
            
            if curr_pivot.pivot_type == PivotType.HIGH:
                # Price direction from prev_same to curr_pivot
                price_dir = 1 if curr_pivot.price > prev_same.price else -1
                
                # Oscillator direction
                try:
                    osc_curr = osc_data.iloc[curr_pivot.index]
                    osc_prev = osc_data.iloc[prev_same.index]
                    osc_dir = 1 if osc_curr > osc_prev else -1
                except:
                    osc_dir = price_dir
                
                # Trend at curr_pivot
                try:
                    trend_dir = 1 if data['close'].iloc[curr_pivot.index] > sma_50.iloc[curr_pivot.index] else -1
                except:
                    trend_dir = 1
                
                pattern_idx = self.encode_pattern(price_dir, osc_dir, trend_dir)
                
                # Outcome: comparing next_same to curr_pivot
                outcome = 'HH' if next_same.price > curr_pivot.price else 'LH'
                
                # Fib ratio: (next_same - curr_pivot) / (curr_pivot - prev_same)
                price_move = abs(next_same.price - curr_pivot.price)
                prev_move = abs(curr_pivot.price - prev_same.price)
                fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
                
                bars_to_pivot = next_same.index - curr_pivot.index
                
                self.update_outcome(pattern_idx, PivotType.HIGH, outcome, fib_ratio, bars_to_pivot)
            
            else:  # PivotType.LOW
                # Price direction from prev_same to curr_pivot
                price_dir = 1 if curr_pivot.price > prev_same.price else -1
                
                # Oscillator direction
                try:
                    osc_curr = osc_data.iloc[curr_pivot.index]
                    osc_prev = osc_data.iloc[prev_same.index]
                    osc_dir = 1 if osc_curr > osc_prev else -1
                except:
                    osc_dir = price_dir
                
                # Trend at curr_pivot
                try:
                    trend_dir = 1 if data['close'].iloc[curr_pivot.index] > sma_50.iloc[curr_pivot.index] else -1
                except:
                    trend_dir = 1
                
                pattern_idx = self.encode_pattern(price_dir, osc_dir, trend_dir)
                
                # Outcome: comparing next_same to curr_pivot
                outcome = 'LL' if next_same.price < curr_pivot.price else 'HL'
                
                # Fib ratio: (next_same - curr_pivot) / (curr_pivot - prev_same)
                price_move = abs(next_same.price - curr_pivot.price)
                prev_move = abs(curr_pivot.price - prev_same.price)
                fib_ratio = price_move / prev_move if prev_move > 0 else 1.0
                
                bars_to_pivot = next_same.index - curr_pivot.index
                
                self.update_outcome(pattern_idx, PivotType.LOW, outcome, fib_ratio, bars_to_pivot)
        
        # Log statistics
        total_high_samples = int(self.pivot_high_stats[:, 2].sum())
        total_low_samples = int(self.pivot_low_stats[:, 2].sum())
        
        logger.info(f"Training complete: {total_high_samples} high patterns, "
                   f"{total_low_samples} low patterns")
    
    def save(self, filepath: str) -> None:
        """Save statistics to file"""
        data = {
            'pivot_high_stats': self.pivot_high_stats,
            'pivot_high_ratios': self.pivot_high_ratios,
            'pivot_high_bars': self.pivot_high_bars,
            'pivot_low_stats': self.pivot_low_stats,
            'pivot_low_ratios': self.pivot_low_ratios,
            'pivot_low_bars': self.pivot_low_bars,
            'min_samples': self.min_samples
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Pattern statistics saved to {filepath}")
    
    def load(self, filepath: str) -> bool:
        """
        Load statistics from file
        
        Returns:
            True if loaded successfully
        """
        if not Path(filepath).exists():
            logger.warning(f"Statistics file not found: {filepath}")
            return False
        
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.pivot_high_stats = data['pivot_high_stats']
            self.pivot_high_ratios = data['pivot_high_ratios']
            self.pivot_high_bars = data['pivot_high_bars']
            self.pivot_low_stats = data['pivot_low_stats']
            self.pivot_low_ratios = data['pivot_low_ratios']
            self.pivot_low_bars = data['pivot_low_bars']
            self.min_samples = data.get('min_samples', 10)
            
            total_samples = int(self.pivot_high_stats[:, 2].sum() + self.pivot_low_stats[:, 2].sum())
            logger.info(f"Pattern statistics loaded from {filepath} ({total_samples} total samples)")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to load statistics: {e}")
            return False
