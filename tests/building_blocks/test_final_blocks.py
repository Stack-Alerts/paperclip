"""
Unit tests for final building blocks (57-66)
Market Structure, Institutional, Supply/Demand, Fibonacci
"""

import pytest
import pandas as pd
from src.detectors.building_blocks.market_structure.swing_points import SwingPoints
from src.detectors.building_blocks.market_structure.premium_discount_zones import PremiumDiscountZones
from src.detectors.building_blocks.market_structure.range_liquidity import RangeLiquidity
from src.detectors.building_blocks.institutional.vwap import VWAP
from src.detectors.building_blocks.institutional.anchored_vwap import AnchoredVWAP
from src.detectors.building_blocks.institutional.ema_crossover import EMACrossover
from src.detectors.building_blocks.institutional.order_flow_imbalance import OrderFlowImbalance
from src.detectors.building_blocks.institutional.market_depth import MarketDepth
from src.detectors.building_blocks.supply_demand.supply_demand_zones import SupplyDemandZones
from src.detectors.building_blocks.fibonacci.fibonacci_retracements import FibonacciRetracements


@pytest.fixture
def data():
    prices = list(range(44000, 45000, 20))
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 100 for p in prices],
        'low': [p - 100 for p in prices],
        'close': prices,
        'volume': [100] * len(prices)
    })


class TestMarketStructure:
    def test_swing_points(self, data):
        b = SwingPoints()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_premium_discount(self, data):
        b = PremiumDiscountZones()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_range_liquidity(self, data):
        b = RangeLiquidity()
        r = b.analyze(data)
        assert 'signal' in r


class TestInstitutional:
    def test_vwap(self, data):
        b = VWAP()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_anchored_vwap(self, data):
        b = AnchoredVWAP()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_ema_crossover(self, data):
        b = EMACrossover()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_order_flow(self, data):
        b = OrderFlowImbalance()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_market_depth(self, data):
        b = MarketDepth()
        r = b.analyze(data)
        assert 'signal' in r


class TestSupplyDemandFibonacci:
    def test_supply_demand(self, data):
        b = SupplyDemandZones()
        r = b.analyze(data)
        assert 'signal' in r
    
    def test_fibonacci(self, data):
        b = FibonacciRetracements()
        r = b.analyze(data)
        assert 'signal' in r


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
