"""
Oscillators for Divergence Detection

Implements multiple oscillators used in TradingView methodology:
- RSI (Relative Strength Index)
- CCI (Commodity Channel Index)
- CMO (Chande Momentum Oscillator)
- MFI (Money Flow Index)
- ROC (Rate of Change)

Based on: TradingView_Scripts/next_pivot_projection.pine oscillator options
Author: BTC Scalp Bot V10 Framework
Version: 1.0.0
Date: December 30, 2025
"""

import pandas as pd
import numpy as np
from typing import Literal

from src.utils.logger import get_logger

logger = get_logger(__name__)

OscillatorType = Literal['rsi', 'cci', 'cmo', 'mfi', 'roc']


class Oscillators:
    """
    Collection of oscillators for divergence detection
    
    All oscillators are normalized to similar ranges for comparison
    """
    
    @staticmethod
    def calculate(
        data: pd.DataFrame,
        osc_type: OscillatorType = 'rsi',
        length: int = 14
    ) -> pd.Series:
        """
        Calculate specified oscillator
        
        Args:
            data: OHLCV DataFrame
            osc_type: Type of oscillator
            length: Oscillator period/length
            
        Returns:
            Pandas Series with oscillator values
        """
        if osc_type == 'rsi':
            return Oscillators.rsi(data['close'], length)
        elif osc_type == 'cci':
            return Oscillators.cci(data, length)
        elif osc_type == 'cmo':
            return Oscillators.cmo(data['close'], length)
        elif osc_type == 'mfi':
            return Oscillators.mfi(data, length)
        elif osc_type == 'roc':
            return Oscillators.roc(data['close'], length)
        else:
            raise ValueError(f"Unknown oscillator type: {osc_type}")
    
    @staticmethod
    def rsi(close: pd.Series, length: int = 14) -> pd.Series:
        """
        Relative Strength Index (RSI)
        
        Range: 0-100
        Overbought: >70
        Oversold: <30
        
        Args:
            close: Close prices
            length: RSI period
            
        Returns:
            RSI values
        """
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(window=length, min_periods=length).mean()
        avg_loss = loss.rolling(window=length, min_periods=length).mean()
        
        # Wilder's smoothing for subsequent values
        for i in range(length, len(close)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (length - 1) + gain.iloc[i]) / length
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (length - 1) + loss.iloc[i]) / length
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def cci(data: pd.DataFrame, length: int = 20) -> pd.Series:
        """
        Commodity Channel Index (CCI)
        
        Range: Unbounded (typically -200 to +200)
        Overbought: >100
        Oversold: <-100
        
        Args:
            data: OHLCV DataFrame
            length: CCI period
            
        Returns:
            CCI values
        """
        tp = (data['high'] + data['low'] + data['close']) / 3  # Typical Price
        
        sma_tp = tp.rolling(window=length).mean()
        mean_deviation = tp.rolling(window=length).apply(
            lambda x: np.abs(x - x.mean()).mean(),
            raw=True
        )
        
        cci = (tp - sma_tp) / (0.015 * mean_deviation)
        
        return cci
    
    @staticmethod
    def cmo(close: pd.Series, length: int = 14) -> pd.Series:
        """
        Chande Momentum Oscillator (CMO)
        
        Range: -100 to +100
        Overbought: >50
        Oversold: <-50
        
        Args:
            close: Close prices
            length: CMO period
            
        Returns:
            CMO values
        """
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        sum_gain = gain.rolling(window=length).sum()
        sum_loss = loss.rolling(window=length).sum()
        
        cmo = 100 * (sum_gain - sum_loss) / (sum_gain + sum_loss)
        
        return cmo
    
    @staticmethod
    def mfi(data: pd.DataFrame, length: int = 14) -> pd.Series:
        """
        Money Flow Index (MFI)
        
        Range: 0-100
        Overbought: >80
        Oversold: <20
        
        Args:
            data: OHLCV DataFrame
            length: MFI period
            
        Returns:
            MFI values
        """
        tp = (data['high'] + data['low'] + data['close']) / 3  # Typical Price
        raw_mf = tp * data['volume']  # Raw Money Flow
        
        # Positive and negative money flow
        delta_tp = tp.diff()
        pos_mf = raw_mf.where(delta_tp > 0, 0.0)
        neg_mf = raw_mf.where(delta_tp < 0, 0.0)
        
        pos_mf_sum = pos_mf.rolling(window=length).sum()
        neg_mf_sum = neg_mf.rolling(window=length).sum()
        
        mfr = pos_mf_sum / neg_mf_sum  # Money Flow Ratio
        mfi = 100 - (100 / (1 + mfr))
        
        return mfi
    
    @staticmethod
    def roc(close: pd.Series, length: int = 12) -> pd.Series:
        """
        Rate of Change (ROC)
        
        Range: Unbounded (percentage)
        Measures momentum as percentage change
        
        Args:
            close: Close prices
            length: ROC period
            
        Returns:
            ROC values
        """
        roc = ((close - close.shift(length)) / close.shift(length)) * 100
        
        return roc
    
    @staticmethod
    def get_pivot_values(
        osc_data: pd.Series,
        pivot_indices: list
    ) -> list:
        """
        Extract oscillator values at pivot points
        
        Args:
            osc_data: Oscillator series
            pivot_indices: List of pivot indices
            
        Returns:
            List of oscillator values at pivots
        """
        return [osc_data.iloc[idx] if idx < len(osc_data) else np.nan 
                for idx in pivot_indices]
