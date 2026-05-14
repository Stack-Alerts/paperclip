"""
Tests for src/strategies/paper_trading_strategy.py — BTCAAAAA-25616
=====================================================================
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.objects import Money, Price, Quantity

from src.strategies.paper_trading_strategy import PaperTradingStrategy


class TestPaperTradingStrategy:
    def test_init_sets_defaults(self):
        strategy = PaperTradingStrategy({"instrument_id": "BTC/USDT.BINANCE"})
        assert strategy._daily_pnl == Money("0.00", USD)
        assert strategy.bar_type is None

    def test_init_with_bar_type_config(self):
        strategy = PaperTradingStrategy({
            "instrument_id": "BTC/USDT.BINANCE",
            "bar_type": "BTC/USDT.BINANCE-15-MINUTE-BID-INTERNAL",
        })
        assert strategy.bar_type is not None
        assert isinstance(strategy.bar_type, BarType)

    def test_on_start_sets_risk_enforcer(self):
        strategy = PaperTradingStrategy({"instrument_id": "BTC/USDT.BINANCE"})
        with patch.object(strategy, "subscribe_bars") as mock_sub:
            strategy.on_start()
        assert strategy.risk_enforcer is not None
        mock_sub.assert_not_called()

    def test_on_start_subscribes_bars_when_configured(self):
        strategy = PaperTradingStrategy({
            "instrument_id": "BTC/USDT.BINANCE",
            "bar_type": "BTC/USDT.BINANCE-15-MINUTE-BID-INTERNAL",
        })
        with patch.object(strategy, "subscribe_bars") as mock_sub:
            strategy.on_start()
        mock_sub.assert_called_once()

    def test_evaluate_entry_signal_returns_none(self):
        strategy = PaperTradingStrategy({"instrument_id": "BTC/USDT.BINANCE"})
        bar = MagicMock()
        result = strategy._evaluate_entry_signal(bar)
        assert result is None

    def test_should_reset_daily_pnl_no_last_reset(self):
        strategy = PaperTradingStrategy({"instrument_id": "BTC/USDT.BINANCE"})
        assert strategy._should_reset_daily_pnl() is True

    def test_on_bar_no_entry_no_error(self):
        strategy = PaperTradingStrategy({"instrument_id": "BTC/USDT.BINANCE"})
        strategy.on_start()
        bar = MagicMock()
        strategy.on_bar(bar)

    def test_on_stop_logs(self):
        strategy = PaperTradingStrategy({"instrument_id": "BTC/USDT.BINANCE"})
        strategy.on_start()
        strategy.on_stop()

    def test_instrument_id_from_config(self):
        strategy = PaperTradingStrategy({"instrument_id": "ETH/USDT.BINANCE"})
        assert strategy.instrument_id == InstrumentId.from_str("ETH/USDT.BINANCE")
