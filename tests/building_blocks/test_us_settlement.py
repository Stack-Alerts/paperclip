"""
Unit tests for US Settlement Price Building Block
"""

import pytest
import pandas as pd
import numpy as np
from src.detectors.building_blocks.price_levels.us_settlement import USSettlement


@pytest.fixture
def sample_data():
    # Create data with 21:00 UTC settlement times
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    np.random.seed(42)
    closes = 45000 + np.random.uniform(-500, 500, 100)
    return pd.DataFrame({
        'timestamp': dates,
        'close': closes,
        'high': closes + 100,
        'low': closes - 100,
        'volume': np.random.uniform(100, 1000, 100)
    })


class TestInitialization:
    def test_default(self):
        settlement = USSettlement()
        assert settlement.settlement_hour_utc == 21


class TestSettlementPriceFinding:
    def test_finds_settlement(self, sample_data):
        settlement = USSettlement()
        price = settlement.find_settlement_price(sample_data)
        assert price is not None


class TestAnalysis:
    def test_standardized_format(self, sample_data):
        settlement = USSettlement()
        result = settlement.analyze(sample_data)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_valid_data(self, sample_data):
        settlement = USSettlement()
        result = settlement.analyze(sample_data)
        # May be NO_SETTLEMENT_DATA depending on data
        assert result['signal'] in ['NEUTRAL', 'NO_SETTLEMENT_DATA', 'BULLISH', 'BEARISH']
    
    def test_metadata_complete(self, sample_data):
        settlement = USSettlement()
        result = settlement.analyze(sample_data)
        if result['signal'] != 'NO_SETTLEMENT_DATA':
            assert 'settlement_price' in result['metadata']


class TestValidation:
    def test_missing_columns(self):
        settlement = USSettlement()
        assert settlement.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
