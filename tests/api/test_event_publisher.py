"""
BTE-TC-API-002 — EventPublisher tests (mock Redis).

Validates:
- publish() serialises events to JSON and delegates to redis.publish().
- Each of the 7 typed callbacks routes to the correct channel.
- Redis errors are swallowed (ITM callback chain is never interrupted).
- Decimal, datetime, and Enum values are coerced to str in JSON output.
- Frozen and mutable dataclasses are serialised correctly.
- Additive pattern: existing callbacks continue to fire alongside publisher.

RTM: BTE-API-WS-002
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from unittest.mock import MagicMock

import pytest

from src.api.event_publisher import (
    CH_ALERTS,
    CH_CAPITAL,
    CH_CYCLE,
    CH_DECISIONS,
    CH_POSITIONS,
    CH_SIGNALS,
    CH_STRATEGIES,
    CHANNELS,
    EventPublisher,
    _to_dict,
)

# ---------------------------------------------------------------------------
# Stub types (avoids importing heavy ITM entities)
# ---------------------------------------------------------------------------


class _Color(str, Enum):
    RED = "red"
    GREEN = "green"


@dataclasses.dataclass(frozen=True)
class _FrozenEvent:
    event_type: str = "test"
    amount: Decimal = Decimal("0")
    occurred_at: datetime = dataclasses.field(
        default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    color: _Color = _Color.RED


@dataclasses.dataclass
class _MutableEntry:
    name: str = "strat-a"
    state: str = "ACTIVE"


@dataclasses.dataclass(frozen=True)
class _Inner:
    value: Decimal = Decimal("1.0")


@dataclasses.dataclass(frozen=True)
class _Outer:
    label: str = "outer"
    inner: _Inner = dataclasses.field(default_factory=_Inner)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    return MagicMock()


@pytest.fixture
def publisher(mock_redis):
    return EventPublisher(mock_redis)


def _channel(mock_redis: MagicMock) -> str:
    return mock_redis.publish.call_args[0][0]


def _payload(mock_redis: MagicMock) -> dict:
    return json.loads(mock_redis.publish.call_args[0][1])


# ---------------------------------------------------------------------------
# _to_dict helper
# ---------------------------------------------------------------------------


class TestToDict:
    def test_dict_passthrough(self):
        d = {"a": 1}
        assert _to_dict(d) is d

    def test_frozen_dataclass(self):
        ev = _FrozenEvent(event_type="capital_changed", amount=Decimal("100"))
        r = _to_dict(ev)
        assert r["event_type"] == "capital_changed"
        assert r["amount"] == Decimal("100")

    def test_mutable_dataclass(self):
        entry = _MutableEntry(name="s1", state="PAUSED")
        r = _to_dict(entry)
        assert r["name"] == "s1"
        assert r["state"] == "PAUSED"

    def test_nested_dataclass_recursed(self):
        outer = _Outer(label="x", inner=_Inner(value=Decimal("5.0")))
        r = _to_dict(outer)
        assert r["label"] == "x"
        assert r["inner"]["value"] == Decimal("5.0")

    def test_plain_object_via_vars(self):
        class _Obj:
            def __init__(self) -> None:
                self.x = 1
                self.y = "hello"

        r = _to_dict(_Obj())
        assert r == {"x": 1, "y": "hello"}

    def test_scalar_fallback(self):
        r = _to_dict(42)
        assert r == {"value": "42"}


# ---------------------------------------------------------------------------
# EventPublisher.publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_delegates_to_redis(self, publisher, mock_redis):
        publisher.publish("itm:cycle", {"symbol": "BTCUSDT"})
        mock_redis.publish.assert_called_once()
        assert _channel(mock_redis) == "itm:cycle"
        assert _payload(mock_redis) == {"symbol": "BTCUSDT"}

    def test_decimal_coerced_to_str(self, publisher, mock_redis):
        publisher.publish("itm:capital", {"amount": Decimal("123.456")})
        assert _payload(mock_redis)["amount"] == "123.456"

    def test_datetime_coerced_to_str(self, publisher, mock_redis):
        dt = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        publisher.publish("itm:cycle", {"ts": dt})
        assert "2026" in _payload(mock_redis)["ts"]

    def test_str_enum_serialised_as_value(self, publisher, mock_redis):
        publisher.publish("itm:decisions", {"color": _Color.RED})
        assert _payload(mock_redis)["color"] == "red"

    def test_redis_error_is_swallowed(self, publisher, mock_redis):
        mock_redis.publish.side_effect = ConnectionError("down")
        publisher.publish("itm:cycle", {"x": 1})  # must not raise

    def test_publish_does_not_raise_on_logging_mock(self, publisher, mock_redis):
        publisher.publish("itm:cycle", {"normal": "data"})
        assert mock_redis.publish.call_count == 1


# ---------------------------------------------------------------------------
# Channel catalogue
# ---------------------------------------------------------------------------


class TestChannelCatalogue:
    def test_seven_channels_defined(self):
        assert len(CHANNELS) == 7

    def test_all_expected_channels_present(self):
        assert set(CHANNELS) == {
            "itm:cycle",
            "itm:capital",
            "itm:positions",
            "itm:decisions",
            "itm:signals",
            "itm:alerts",
            "itm:strategies",
        }


# ---------------------------------------------------------------------------
# BTE-TC-API-002: typed callbacks → correct channel routing
# ---------------------------------------------------------------------------


class TestCallbackRouting:
    """Each typed callback must publish to exactly the right channel."""

    def test_on_bar_closed(self, publisher, mock_redis):
        publisher.on_bar_closed({"symbol": "BTCUSDT", "close": "50000"})
        assert _channel(mock_redis) == CH_CYCLE

    def test_on_capital_changed(self, publisher, mock_redis):
        publisher.on_capital_changed({"change_type": "allocate", "amount": "100"})
        assert _channel(mock_redis) == CH_CAPITAL

    def test_on_position_updated(self, publisher, mock_redis):
        publisher.on_position_updated({"position_id": "p1", "change_type": "entry"})
        assert _channel(mock_redis) == CH_POSITIONS

    def test_on_decision_made(self, publisher, mock_redis):
        publisher.on_decision_made({"decision_id": "d1", "action": "BUY"})
        assert _channel(mock_redis) == CH_DECISIONS

    def test_on_signal_received(self, publisher, mock_redis):
        publisher.on_signal_received({"signal_id": "s1", "strength": "0.8"})
        assert _channel(mock_redis) == CH_SIGNALS

    def test_on_alert_raised(self, publisher, mock_redis):
        publisher.on_alert_raised({"alert_type": "risk_limit", "message": "breach"})
        assert _channel(mock_redis) == CH_ALERTS

    def test_on_strategy_changed(self, publisher, mock_redis):
        publisher.on_strategy_changed({"strategy_id": "s1", "state": "ACTIVE"})
        assert _channel(mock_redis) == CH_STRATEGIES


# ---------------------------------------------------------------------------
# Dataclass serialisation (simulating real ITM domain objects)
# ---------------------------------------------------------------------------


class TestDataclassSerialisation:
    def test_frozen_event_decimal_serialised(self, publisher, mock_redis):
        ev = _FrozenEvent(event_type="capital_changed", amount=Decimal("42.5"))
        publisher.on_capital_changed(ev)
        data = _payload(mock_redis)
        assert data["event_type"] == "capital_changed"
        assert data["amount"] == "42.5"

    def test_mutable_entry_serialised(self, publisher, mock_redis):
        entry = _MutableEntry(name="strat-a", state="PAUSED")
        publisher.on_strategy_changed(entry)
        data = _payload(mock_redis)
        assert data["name"] == "strat-a"
        assert data["state"] == "PAUSED"

    def test_nested_dataclass_serialised(self, publisher, mock_redis):
        outer = _Outer(label="cycle-1", inner=_Inner(value=Decimal("2.5")))
        publisher.on_bar_closed(outer)
        data = _payload(mock_redis)
        assert data["label"] == "cycle-1"
        assert data["inner"]["value"] == "2.5"


# ---------------------------------------------------------------------------
# Additive pattern: existing callbacks remain unmodified
# ---------------------------------------------------------------------------


class TestAdditivePattern:
    """Publishing must not interfere with the existing ITM callback chain."""

    def test_existing_callback_fires_alongside_publisher(self, mock_redis):
        calls: list = []

        def existing_handler(decision: dict) -> None:
            calls.append(decision)

        pub = EventPublisher(mock_redis)
        decision = {"decision_id": "d1", "action": "SELL"}

        def combined_on_decision(d: dict) -> None:
            existing_handler(d)        # existing logic (unchanged)
            pub.on_decision_made(d)    # additive

        combined_on_decision(decision)

        assert calls == [decision], "existing callback must still fire"
        assert mock_redis.publish.call_count == 1
        assert _channel(mock_redis) == CH_DECISIONS

    def test_publisher_error_does_not_prevent_existing_callback(self, mock_redis):
        mock_redis.publish.side_effect = ConnectionError("redis down")
        calls: list = []

        def existing_handler(d: dict) -> None:
            calls.append(d)

        pub = EventPublisher(mock_redis)

        def combined_on_decision(d: dict) -> None:
            existing_handler(d)        # fires first
            pub.on_decision_made(d)    # swallows Redis error

        combined_on_decision({"action": "BUY"})
        assert len(calls) == 1, "existing callback must fire even when Redis is down"
