"""
Additional unit tests for ITM ↔ NautilusTrader type mapping (function-based API).
Complements test_nt_mapping.py which covers the NTTypeMapper class.
Covers: itm_instrument_to_nt_id, nt_id_to_itm_kwargs, signal_to_sb_dict.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from src.itm.domain.entities import (
    ContractType,
    Instrument,
    Signal,
    SignalDirection,
)
from src.itm.domain.nt_mapping import (
    itm_instrument_to_nt_id,
    nt_id_to_itm_kwargs,
    signal_to_sb_dict,
    NTTypeMapper,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def btc_spot() -> Instrument:
    return Instrument.btc_usdt_spot("binance")


@pytest.fixture
def btc_perp() -> Instrument:
    return Instrument.btc_usdt_perp("bybit")


# ---------------------------------------------------------------------------
# Instrument → NT InstrumentId (function helpers)
# ---------------------------------------------------------------------------


class TestInstrumentIdHelpers:
    def test_spot_symbol_no_slash(self, btc_spot: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_spot)
        assert str(nt_id.symbol) == "BTCUSDT"

    def test_venue_uppercase(self, btc_spot: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_spot)
        assert str(nt_id.venue) == "BINANCE"

    def test_perp_venue(self, btc_perp: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_perp)
        assert str(nt_id.venue) == "BYBIT"

    def test_nt_id_to_itm_kwargs_base_quote(self, btc_spot: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_spot)
        kwargs = nt_id_to_itm_kwargs(nt_id)
        assert kwargs["symbol"] == "BTC/USDT"
        assert kwargs["exchange"] == "binance"
        assert kwargs["base_currency"] == "BTC"
        assert kwargs["quote_currency"] == "USDT"

    def test_nt_id_to_itm_kwargs_exchange_lowercase(self, btc_perp: Instrument) -> None:
        nt_id = itm_instrument_to_nt_id(btc_perp)
        kwargs = nt_id_to_itm_kwargs(nt_id)
        assert kwargs["exchange"] == "bybit"

    def test_nttype_mapper_instrument_to_nt_id(self, btc_spot: Instrument) -> None:
        nt_id = NTTypeMapper.instrument_to_nt_id(btc_spot)
        assert str(nt_id.symbol) == "BTCUSDT"

    def test_nttype_mapper_nt_id_to_itm(self, btc_spot: Instrument) -> None:
        nt_id = NTTypeMapper.instrument_to_nt_id(btc_spot)
        kwargs = NTTypeMapper.nt_instrument_id_to_itm(nt_id)
        assert kwargs["symbol"] == "BTC/USDT"

    def test_nttype_mapper_exchange_override(self, btc_spot: Instrument) -> None:
        nt_id = NTTypeMapper.instrument_to_nt_id(btc_spot)
        kwargs = NTTypeMapper.nt_instrument_id_to_itm(nt_id, exchange="okx")
        assert kwargs["exchange"] == "okx"


# ---------------------------------------------------------------------------
# signal_to_sb_dict tests
# ---------------------------------------------------------------------------


class TestSignalToSbDict:
    def test_round_trip_via_sb_dict(self, btc_spot: Instrument) -> None:
        sig = Signal(
            direction=SignalDirection.SHORT,
            strength=Decimal("0.65"),
            source_strategy="ema_cross_v2",
            instrument=btc_spot,
            metadata={"timeframe": "1h"},
        )
        d = signal_to_sb_dict(sig)
        assert d["strategy_id"] == "ema_cross_v2"
        assert d["direction"] == "short"
        assert d["strength"] == "0.65"
        assert d["metadata"]["timeframe"] == "1h"
        assert d["instrument_symbol"] == "BTC/USDT"
        assert d["instrument_exchange"] == "binance"
        assert "signal_id" in d
        assert "created_at" in d

    def test_created_at_is_isoformat(self, btc_spot: Instrument) -> None:
        sig = Signal(
            direction=SignalDirection.LONG,
            strength=Decimal("0.5"),
            source_strategy="s",
            instrument=btc_spot,
        )
        d = signal_to_sb_dict(sig)
        dt = datetime.fromisoformat(d["created_at"])
        assert dt.tzinfo is not None

    def test_empty_metadata_serializes_empty_dict(self, btc_spot: Instrument) -> None:
        sig = Signal(
            direction=SignalDirection.NEUTRAL,
            strength=Decimal("0"),
            source_strategy="s",
            instrument=btc_spot,
        )
        d = signal_to_sb_dict(sig)
        assert d["metadata"] == {}
