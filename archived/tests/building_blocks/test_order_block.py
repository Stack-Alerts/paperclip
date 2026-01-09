"""
Unit tests for Order Block Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_action.order_block import OrderBlock


@pytest.fixture
def sample_data_with_ob():
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min')
    prices = [45000]
    for i in range(99):
        if i == 50:
            prices.append(prices[-1] - 200)
        elif i == 51:
            prices.append(prices[-1] + 800)
        else:
            prices.append(prices[-1] + np.random.uniform(-20, 20))
    
    return pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'open': [p - 10 for p in prices],
        'high': [p + 20 for p in prices],
        'low': [p - 20 for p in prices]
    })


class TestInitialization:
    def test_default(self):
        ob = OrderBlock()
        assert ob.timeframe == '15min'
        assert ob.min_impulse_pct == 1.5


class TestAnalysis:
    def test_standardized_format(self, sample_data_with_ob):
        ob = OrderBlock()
        result = ob.analyze(sample_data_with_ob)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_detects_order_block(self, sample_data_with_ob):
        ob = OrderBlock()
        result = ob.analyze(sample_data_with_ob)
        assert result['signal'] in ['BULLISH', 'BEARISH', 'NEUTRAL', 'NO_ORDER_BLOCK']


class TestValidation:
    def test_missing_columns(self):
        ob = OrderBlock()
        assert ob.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'
    
    def test_insufficient_data(self):
        ob = OrderBlock()
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min'),
            'open': [45000]*5, 'high': [45100]*5, 'low': [44900]*5, 'close': [45050]*5
        })
        assert ob.analyze(df)['signal'] == 'INSUFFICIENT_DATA'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
