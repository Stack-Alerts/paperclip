"""
Tests for Sprint 2.0.1 Task 2.0.1.2 - BacktestDataProvider

Validates institutional-grade data loading for backtesting.

NAUTILUS EXPERT: Ensures proper Bar loading, caching, validation

Author: BTC_Engine_v3 Test Suite
Date: 2026-02-06
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from nautilus_trader.model.data import Bar

from src.optimizer_v3.core.backtest_data_provider import (
    BacktestDataProvider,
    get_backtest_provider
)


@pytest.fixture
def mock_nautilus_loader():
    """Create mock NautilusDataLoader"""
    with patch('src.optimizer_v3.core.backtest_data_provider.NautilusDataLoader') as mock:
        loader = mock.return_value
        # Create mock bars
        mock_bars = []
        for i in range(100):
            bar = Mock(spec=Bar)
            bar.ts_event = i * 1000000000  # Sequential timestamps
            mock_bars.append(bar)
        loader.load_bars.return_value = mock_bars
        yield loader


@pytest.fixture
def mock_unified_manager():
    """Create mock UnifiedDataManager"""
    with patch('src.optimizer_v3.core.backtest_data_provider.UnifiedDataManager') as mock:
        manager = mock.return_value
        manager.get_available_date_range.return_value = {
            'earliest': datetime(2024, 1, 1),
            'latest': datetime(2026, 2, 6)
        }
        yield manager


@pytest.fixture
def provider(mock_nautilus_loader, mock_unified_manager):
    """Create BacktestDataProvider with mocked dependencies"""
    return BacktestDataProvider()


def test_provider_initialization(provider):
    """Test provider initializes correctly"""
    assert provider.unified_manager is not None
    assert provider.nautilus_loader is not None
    assert provider._cache == {}
    assert provider._lock is not None


def test_load_bars_success(provider, mock_nautilus_loader):
    """Test successful bar loading"""
    # Load data
    bars = provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31)
    )
    
    # Verify result
    assert isinstance(bars, list)
    assert len(bars) == 100  # Mock returns 100 bars
    assert all(isinstance(b, Mock) for b in bars)  # Mock bars
    
    # Verify loader was called
    mock_nautilus_loader.load_bars.assert_called_once_with(
        start=datetime(2025, 12, 1),
        end=datetime(2025, 12, 31),
        timeframe='15m'
    )


def test_load_bars_with_progress(provider, mock_nautilus_loader):
    """Test progress callback"""
    progress_calls = []
    
    def progress_callback(current, total, message):
        progress_calls.append((current, total, message))
    
    bars = provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31),
        progress_callback=progress_callback
    )
    
    # Verify progress was called
    assert len(progress_calls) >= 2  # Start + Complete
    assert any("Loading" in msg for _, _, msg in progress_calls)
    assert any("Loaded" in msg or "✅" in msg for _, _, msg in progress_calls)


def test_empty_timeframe_raises_error(provider):
    """Test that empty timeframe raises ValueError"""
    with pytest.raises(ValueError, match="Timeframe cannot be empty"):
        provider.load_bars_for_backtest(
            timeframe='',
            start_date=datetime(2025, 12, 1),
            end_date=datetime(2025, 12, 31)
        )


def test_invalid_date_range_raises_error(provider):
    """Test that start_date >= end_date raises ValueError"""
    with pytest.raises(ValueError, match="must be before"):
        provider.load_bars_for_backtest(
            timeframe='15m',
            start_date=datetime(2025, 12, 31),
            end_date=datetime(2025, 12, 1)
        )


def test_no_data_available_raises_error(provider, mock_nautilus_loader):
    """Test that empty bar list raises RuntimeError (wrapped ValueError)"""
    mock_nautilus_loader.load_bars.return_value = []
    
    with pytest.raises(RuntimeError, match="Failed to load bars"):
        provider.load_bars_for_backtest(
            timeframe='15m',
            start_date=datetime(2025, 12, 1),
            end_date=datetime(2025, 12, 31)
        )


def test_chronological_order_validation(provider, mock_nautilus_loader):
    """Test that non-chronological bars raise RuntimeError"""
    # Create bars with non-chronological timestamps
    bad_bars = []
    for i in range(10):
        bar = Mock(spec=Bar)
        bar.ts_event = (10 - i) * 1000000000  # Descending timestamps
        bad_bars.append(bar)
    
    mock_nautilus_loader.load_bars.return_value = bad_bars
    
    with pytest.raises(RuntimeError, match="not in chronological order"):
        provider.load_bars_for_backtest(
            timeframe='15m',
            start_date=datetime(2025, 12, 1),
            end_date=datetime(2025, 12, 31)
        )


def test_caching(provider, mock_nautilus_loader):
    """Test result caching"""
    # First load
    bars1 = provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31)
    )
    
    # Verify loader was called once
    assert mock_nautilus_loader.load_bars.call_count == 1
    
    # Second load (should be from cache)
    bars2 = provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31)
    )
    
    # Loader should still only have been called once
    assert mock_nautilus_loader.load_bars.call_count == 1
    
    # Should be same instances (from cache)
    assert bars1 is bars2


def test_cache_with_progress_callback(provider, mock_nautilus_loader):
    """Test that cache hit triggers progress callback"""
    # First load (populates cache)
    provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31)
    )
    
    # Second load with progress callback
    progress_calls = []
    def progress_callback(current, total, message):
        progress_calls.append((current, total, message))
    
    bars = provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31),
        progress_callback=progress_callback
    )
    
    # Should have called progress with cache message
    assert len(progress_calls) == 1
    assert "cache" in progress_calls[0][2].lower()


def test_get_available_range(provider, mock_unified_manager):
    """Test get_available_range"""
    range_info = provider.get_available_range('15m')
    
    assert 'earliest' in range_info
    assert 'latest' in range_info
    assert isinstance(range_info['earliest'], datetime)
    assert isinstance(range_info['latest'], datetime)
    
    # Verify manager was called
    mock_unified_manager.get_available_date_range.assert_called_once_with('15m')


def test_validate_date_range_valid(provider, mock_unified_manager):
    """Test date range validation - valid range"""
    valid, msg = provider.validate_date_range(
        '15m',
        datetime(2025, 1, 1),
        datetime(2025, 12, 31)
    )
    
    assert valid is True
    assert "Valid" in msg
    assert "bars expected" in msg


def test_validate_date_range_start_too_early(provider, mock_unified_manager):
    """Test date range validation - start date too early"""
    valid, msg = provider.validate_date_range(
        '15m',
        datetime(2023, 1, 1),  # Before earliest (2024-01-01)
        datetime(2025, 12, 31)
    )
    
    assert valid is False
    assert "before earliest available" in msg


def test_validate_date_range_end_too_late(provider, mock_unified_manager):
    """Test date range validation - end date too late"""
    valid, msg = provider.validate_date_range(
        '15m',
        datetime(2025, 1, 1),
        datetime(2027, 12, 31)  # After latest (2026-02-06)
    )
    
    assert valid is False
    assert "after latest available" in msg


def test_validate_date_range_start_after_end(provider, mock_unified_manager):
    """Test date range validation - start >= end"""
    valid, msg = provider.validate_date_range(
        '15m',
        datetime(2025, 12, 31),
        datetime(2025, 1, 1)
    )
    
    assert valid is False
    assert "must be before" in msg


def test_clear_cache(provider, mock_nautilus_loader):
    """Test cache clearing"""
    # Load data to populate cache
    provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31)
    )
    
    # Verify cache has data
    assert len(provider._cache) == 1
    
    # Clear cache
    cleared = provider.clear_cache()
    
    # Verify cache is empty
    assert cleared == 1
    assert len(provider._cache) == 0


def test_singleton_pattern():
    """Test singleton pattern"""
    provider1 = get_backtest_provider()
    provider2 = get_backtest_provider()
    
    assert provider1 is provider2


def test_loader_exception_handling(provider, mock_nautilus_loader):
    """Test that loader exceptions are properly wrapped"""
    mock_nautilus_loader.load_bars.side_effect = Exception("Test error")
    
    with pytest.raises(RuntimeError, match="Failed to load bars"):
        provider.load_bars_for_backtest(
            timeframe='15m',
            start_date=datetime(2025, 12, 1),
            end_date=datetime(2025, 12, 31)
        )


def test_loader_exception_with_progress_callback(provider, mock_nautilus_loader):
    """Test that loader exceptions trigger error progress callback"""
    mock_nautilus_loader.load_bars.side_effect = Exception("Test error")
    
    progress_calls = []
    def progress_callback(current, total, message):
        progress_calls.append((current, total, message))
    
    with pytest.raises(RuntimeError):
        provider.load_bars_for_backtest(
            timeframe='15m',
            start_date=datetime(2025, 12, 1),
            end_date=datetime(2025, 12, 31),
            progress_callback=progress_callback
        )
    
    # Should have error message in progress
    assert any("ERROR" in msg or "❌" in msg for _, _, msg in progress_calls)


def test_thread_safety_lock(provider):
    """Test that operations use thread lock"""
    assert provider._lock is not None
    
    # Verify lock is acquired during load_bars_for_backtest
    # (This is implicit in the implementation, but we verify the lock exists)
    import threading
    assert isinstance(provider._lock, type(threading.Lock()))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
