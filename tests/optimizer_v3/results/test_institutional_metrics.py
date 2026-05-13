"""
Unit Tests for Institutional Metrics Calculator
Task 1.3.9: Comprehensive unit tests with 100% coverage
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from nautilus_trader.model.objects import Money, Quantity, Price
from nautilus_trader.model.currencies import USD

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.optimizer_v3.core.results.institutional_metrics import InstitutionalMetrics


@pytest.fixture
def metrics_calculator():
    """Create metrics calculator instance"""
    return InstitutionalMetrics()


@pytest.fixture
def sample_trades():
    """Create sample trades for testing"""
    trades = []
    base_time = datetime(2024, 1, 1, 9, 0)
    capital = Money('10000', USD)
    
    # Create 50 trades with varying outcomes
    for i in range(50):
        # Alternate between wins and losses with some randomness
        is_winner = i % 3 != 2  # 66% win rate
        pnl_amount = str(100 if is_winner else -50)
        
        trade = {
            'trade_id': f'TRADE_{i}',
            'entry_time': base_time + timedelta(hours=i),
            'exit_time': base_time + timedelta(hours=i, minutes=30),
            'pnl': Money(pnl_amount, USD),
            'capital_start': capital,
            'capital_end': Money(str(capital.as_decimal() + Decimal(pnl_amount)), USD),
            'quantity': Quantity.from_str('0.1'),
            'entry_price': Price.from_str('50000'),
            'exit_price': Price('50100' if is_winner else '49950'),
            'side': 'BUY',
            'commission': Money('2.5', USD),
            'slippage': Money('0.5', USD)
        }
        
        trades.append(trade)
        capital = trade['capital_end']
    
    return trades


@pytest.fixture
def minimal_trades():
    """Create minimal set of trades (below threshold)"""
    return [
        {
            'pnl': Money('100', USD),
            'capital_start': Money('10000', USD),
            'entry_time': datetime.now(),
            'exit_time': datetime.now() + timedelta(hours=1)
        }
    ]


class TestInstitutionalMetrics:
    """Test suite for InstitutionalMetrics calculator"""
    
    # ==================== Core Metrics Tests ====================
    
    def test_calculate_all_metrics(self, metrics_calculator, sample_trades):
        """Test comprehensive metrics calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        
        # Verify all metric categories present
        assert 'sharpe_ratio' in result
        assert 'sortino_ratio' in result
        assert 'calmar_ratio' in result
        assert 'win_rate' in result
        assert 'profit_factor' in result
        assert 'total_trades' in result
        assert result['trade_sample_sufficient'] is True
    
    def test_empty_trades(self, metrics_calculator):
        """Test handling of empty trades list"""
        result = metrics_calculator.calculate_all_metrics([])
        
        assert result['total_trades'] == 0
        assert result['trade_sample_sufficient'] is False
        assert 'error' in result
    
    def test_insufficient_trades(self, metrics_calculator, minimal_trades):
        """Test handling of insufficient trade sample"""
        result = metrics_calculator.calculate_all_metrics(minimal_trades)
        
        assert result['total_trades'] == 1
        assert result['trade_sample_sufficient'] is False
        assert 'error' in result
    
    def test_sharpe_ratio_calculation(self, metrics_calculator, sample_trades):
        """Test Sharpe ratio calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        sharpe = result['sharpe_ratio']
        
        assert isinstance(sharpe, Decimal)
        assert sharpe >= Decimal('0')
        # With 66% win rate and positive returns, should have positive Sharpe
        assert sharpe > Decimal('0')
    
    def test_sortino_ratio_calculation(self, metrics_calculator, sample_trades):
        """Test Sortino ratio calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        sortino = result['sortino_ratio']
        
        assert isinstance(sortino, Decimal)
        assert sortino >= Decimal('0')
        # Sortino should be >= Sharpe for positive returns
        assert sortino >= result['sharpe_ratio']
    
    def test_calmar_ratio_calculation(self, metrics_calculator, sample_trades):
        """Test Calmar ratio calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        calmar = result['calmar_ratio']
        
        assert isinstance(calmar, Decimal)
        assert calmar >= Decimal('0')
    
    def test_win_rate_calculation(self, metrics_calculator, sample_trades):
        """Test win rate calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        win_rate = result['win_rate']
        
        assert isinstance(win_rate, Decimal)
        assert Decimal('0') <= win_rate <= Decimal('1')
        # Based on our sample data, should be around 0.66
        assert Decimal('0.6') <= win_rate <= Decimal('0.7')
    
    def test_profit_factor_calculation(self, metrics_calculator, sample_trades):
        """Test profit factor calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        profit_factor = result['profit_factor']
        
        assert isinstance(profit_factor, Decimal)
        assert profit_factor > Decimal('1')  # Should be profitable
    
    def test_recovery_factor_calculation(self, metrics_calculator, sample_trades):
        """Test recovery factor calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        recovery_factor = result['recovery_factor']
        
        assert isinstance(recovery_factor, Decimal)
        assert recovery_factor >= Decimal('0')
    
    def test_max_drawdown_calculation(self, metrics_calculator, sample_trades):
        """Test maximum drawdown calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        
        assert 'max_drawdown' in result
        max_dd = result['max_drawdown']
        assert isinstance(max_dd, Money)
    
    def test_volatility_calculation(self, metrics_calculator, sample_trades):
        """Test volatility calculation"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        volatility = result['volatility']
        
        assert isinstance(volatility, Decimal)
        assert volatility >= Decimal('0')
    
    # ==================== Edge Case Tests ====================
    
    def test_all_winning_trades(self, metrics_calculator):
        """Test with all winning trades"""
        trades = [
            {
                'pnl': Money('100', USD),
                'capital_start': Money('10000', USD),
                'capital_end': Money('10100', USD),
                'entry_time': datetime.now() + timedelta(hours=i),
                'exit_time': datetime.now() + timedelta(hours=i, minutes=30),
                'quantity': Quantity.from_str('0.1'),
                'entry_price': Price.from_str('50000'),
                'exit_price': Price.from_str('50100')
            }
            for i in range(50)
        ]
        
        result = metrics_calculator.calculate_all_metrics(trades)
        
        assert result['win_rate'] == Decimal('1')
        assert result['profit_factor'] == Decimal('999.99')  # No losses
    
    def test_all_losing_trades(self, metrics_calculator):
        """Test with all losing trades"""
        trades = [
            {
                'pnl': Money('-50', USD),
                'capital_start': Money('10000', USD),
                'capital_end': Money('9950', USD),
                'entry_time': datetime.now() + timedelta(hours=i),
                'exit_time': datetime.now() + timedelta(hours=i, minutes=30),
                'quantity': Quantity.from_str('0.1'),
                'entry_price': Price.from_str('50000'),
                'exit_price': Price.from_str('49950')
            }
            for i in range(50)
        ]
        
        result = metrics_calculator.calculate_all_metrics(trades)
        
        assert result['win_rate'] == Decimal('0')
        assert result['profit_factor'] == Decimal('0')
    
    def test_single_trade_above_threshold(self, metrics_calculator):
        """Test with exactly minimum trades"""
        trades = [
            {
                'pnl': Money('100', USD),
                'capital_start': Money('10000', USD),
                'capital_end': Money('10100', USD),
                'entry_time': datetime.now() + timedelta(hours=i),
                'exit_time': datetime.now() + timedelta(hours=i, minutes=30),
                'quantity': Quantity.from_str('0.1'),
                'entry_price': Price.from_str('50000'),
                'exit_price': Price.from_str('50100')
            }
            for i in range(30)  # Minimum threshold
        ]
        
        result = metrics_calculator.calculate_all_metrics(trades)
        
        assert result['trade_sample_sufficient'] is True
        assert result['total_trades'] == 30
    
    def test_zero_capital_handling(self, metrics_calculator):
        """Test handling of zero capital"""
        trades = [
            {
                'pnl': Money('0', USD),
                'capital_start': Money('0', USD),
                'capital_end': Money('0', USD),
                'entry_time': datetime.now(),
                'exit_time': datetime.now() + timedelta(hours=1),
                'quantity': Quantity.from_str('0'),
                'entry_price': Price.from_str('50000'),
                'exit_price': Price.from_str('50000')
            }
        ]
        
        # Should not crash with zero capital
        result = metrics_calculator.calculate_all_metrics(trades)
        assert 'error' in result or result['total_trades'] == 1
    
    # ==================== Type Safety Tests ====================
    
    def test_nautilus_type_handling(self, metrics_calculator, sample_trades):
        """Test proper handling of NautilusTrader types"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        
        # Verify Money types returned where appropriate
        assert isinstance(result['average_trade_pnl'], Money)
        assert isinstance(result['largest_winner'], Money)
        assert isinstance(result['largest_loser'], Money)
        assert isinstance(result['max_drawdown'], Money)
    
    def test_decimal_precision(self, metrics_calculator, sample_trades):
        """Test decimal precision in calculations"""
        result = metrics_calculator.calculate_all_metrics(sample_trades)
        
        # Verify Decimal types for ratios
        assert isinstance(result['sharpe_ratio'], Decimal)
        assert isinstance(result['win_rate'], Decimal)
        
        # Check reasonable precision (not extreme values)
        assert abs(result['sharpe_ratio']) < Decimal('100')
        assert Decimal('0') <= result['win_rate'] <= Decimal('1')
    
    # ==================== Helper Method Tests ====================
    
    def test_money_to_decimal_conversion(self, metrics_calculator):
        """Test Money to Decimal conversion"""
        money = Money('123.456', USD)
        result = metrics_calculator._money_to_decimal(money)
        
        assert isinstance(result, Decimal)
        assert result == Decimal('123.456')
    
    def test_is_winning_trade(self, metrics_calculator):
        """Test winning trade identification"""
        winning_trade = {
            'pnl': Money('100', USD)
        }
        losing_trade = {
            'pnl': Money('-50', USD)
        }
        
        assert metrics_calculator._is_winning_trade(winning_trade) is True
        assert metrics_calculator._is_winning_trade(losing_trade) is False
    
    # ==================== Performance Tests ====================
    
    def test_large_dataset_performance(self, metrics_calculator):
        """Test performance with large dataset"""
        import time
        
        # Create 1000 trades
        trades = [
            {
                'pnl': Money('100', USD) if i % 2 == 0 else Money('-50', USD),
                'capital_start': Money('10000', USD),
                'capital_end': Money('10050', USD),
                'entry_time': datetime.now() + timedelta(hours=i),
                'exit_time': datetime.now() + timedelta(hours=i, minutes=30),
                'quantity': Quantity.from_str('0.1'),
                'entry_price': Price.from_str('50000'),
                'exit_price': Price.from_str('50100')
            }
            for i in range(1000)
        ]
        
        start = time.time()
        result = metrics_calculator.calculate_all_metrics(trades)
        duration = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0
        assert result['total_trades'] == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src.optimizer_v3.core.results.institutional_metrics', '--cov-report=term-missing'])
