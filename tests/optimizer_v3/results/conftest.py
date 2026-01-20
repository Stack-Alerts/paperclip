"""
Shared Test Fixtures for Results Tests
Sprint 1.3 - Common test data and utilities
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from nautilus_trader.model.objects import Money, Quantity, Price


@pytest.fixture
def sample_trades_50():
    """Create 50 sample trades for testing (66% win rate)"""
    trades = []
    base_time = datetime(2024, 1, 1, 9, 0)
    capital = Money('10000', 'USD')
    
    for i in range(50):
        is_winner = i % 3 != 2  # 66% win rate
        pnl_amount = str(100 if is_winner else -50)
        
        trade = {
            'trade_id': f'TRADE_{i}',
            'entry_time': base_time + timedelta(hours=i),
            'exit_time': base_time + timedelta(hours=i, minutes=30),
            'pnl': Money(pnl_amount, 'USD'),
            'capital_start': capital,
            'capital_end': Money(str(capital.as_decimal() + Decimal(pnl_amount)), 'USD'),
            'quantity': Quantity('0.1'),
            'entry_price': Price('50000'),
            'exit_price': Price('50100' if is_winner else '49950'),
            'side': 'BUY',
            'commission': Money('2.5', 'USD'),
            'slippage': Money('0.5', 'USD'),
            'risk_reward_ratio': Decimal('2.0')
        }
        
        trades.append(trade)
        capital = trade['capital_end']
    
    return trades


@pytest.fixture
def winning_trades():
    """Create trades with 100% win rate"""
    return [
        {
            'pnl': Money('100', 'USD'),
            'capital_start': Money('10000', 'USD'),
            'capital_end': Money('10100', 'USD'),
            'entry_time': datetime.now() + timedelta(hours=i),
            'exit_time': datetime.now() + timedelta(hours=i, minutes=30),
            'quantity': Quantity('0.1'),
            'entry_price': Price('50000'),
            'exit_price': Price('50100')
        }
        for i in range(30)
    ]


@pytest.fixture
def losing_trades():
    """Create trades with 0% win rate"""
    return [
        {
            'pnl': Money('-50', 'USD'),
            'capital_start': Money('10000', 'USD'),
            'capital_end': Money('9950', 'USD'),
            'entry_time': datetime.now() + timedelta(hours=i),
            'exit_time': datetime.now() + timedelta(hours=i, minutes=30),
            'quantity': Quantity('0.1'),
            'entry_price': Price('50000'),
            'exit_price': Price('49950')
        }
        for i in range(30)
    ]


@pytest.fixture
def mixed_results():
    """Create optimization results with mixed performance"""
    return [
        {
            'config_id': 'config_1',
            'trades': [],  # Will be populated by test
            'sharpe_ratio': Decimal('2.0'),
            'win_rate': Decimal('0.65'),
            'max_drawdown': Money('-500', 'USD')
        },
        {
            'config_id': 'config_2',
            'trades': [],
            'sharpe_ratio': Decimal('1.5'),
            'win_rate': Decimal('0.70'),
            'max_drawdown': Money('-800', 'USD')
        }
    ]


@pytest.fixture
def sample_config():
    """Create sample optimization configuration"""
    return {
        'strategy_name': 'test_strategy',
        'parameters': {
            'rsi_period': 14,
            'threshold': Decimal('70'),
            'stop_loss': Money('100', 'USD')
        },
        'risk_management': {
            'max_position_size': Quantity('1.0'),
            'max_drawdown': Money('1000', 'USD')
        },
        'session_id': 'test_session_001',
        'timestamp': datetime(2024, 1, 1, 12, 0, 0)
    }
