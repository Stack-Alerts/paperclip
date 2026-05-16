"""
mock-itm.py — Mock ITM for FastAPI bridge testing
===================================================
Populates Redis with synthetic ITM state and publishes to all 7 pub/sub
channels on a configurable interval.

Run alongside the API server to test BTE-TC-WS-001 through 007.

Usage
-----
    python mock-itm.py [--interval SECONDS] [--redis-host HOST] [--redis-port PORT]

Environment
-----------
  BTE_REDIS_HOST  (default: localhost)
  BTE_REDIS_PORT  (default: 6379)
  BTE_REDIS_DB    (default: 0)
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_snapshot() -> dict:
    pos_id = str(uuid.uuid4())
    strat_id = "mock-strategy-001"
    return {
        "state_id": str(uuid.uuid4()),
        "checkpoint_seq": int(time.monotonic() * 1000) % 1_000_000,
        "created_at": _now(),
        "updated_at": _now(),
        "positions": {
            pos_id: {
                "position_id": pos_id,
                "instrument_symbol": "BTC/USDT",
                "instrument_exchange": "binance",
                "instrument_contract_type": "spot",
                "instrument_tick_size": "0.01",
                "instrument_lot_size": "0.00001",
                "instrument_base_currency": "BTC",
                "instrument_quote_currency": "USDT",
                "direction": "long",
                "entries": [
                    {
                        "order_id": str(uuid.uuid4()),
                        "quantity": "0.01",
                        "price": "65000.00",
                        "timestamp": _now(),
                    }
                ],
                "exits": [],
                "opened_at": _now(),
                "closed_at": None,
            }
        },
        "orders": {},
        "risk": {
            "account_heat": {
                "max_heat": "10.0",
                "current_heat": "2.0",
                "per_strategy_heat": {strat_id: "2.0"},
            },
            "capital_state": {
                "total_capital": "10000.00",
                "allocated": "650.00",
                "locked": "0.00",
            },
            "total_open_positions": 1,
            "total_pending_orders": 0,
            "total_realized_pnl": "125.50",
            "total_daily_pnl": "42.30",
            "max_daily_loss": "500.00",
            "max_drawdown_pct": "0.05",
            "current_drawdown_pct": "0.00",
            "updated_at": _now(),
        },
        "strategies": {
            strat_id: {
                "strategy_id": strat_id,
                "run_state": "active",
                "instrument": {
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "contract_type": "spot",
                    "tick_size": "0.01",
                    "lot_size": "0.00001",
                    "base_currency": "BTC",
                    "quote_currency": "USDT",
                },
                "risk_profile": {
                    "strategy_id": strat_id,
                    "max_drawdown_pct": "0.05",
                    "max_position_qty": "0.1",
                    "heat_limit": "5.0",
                    "max_daily_loss": "100.00",
                    "max_leverage": "1.0",
                },
                "active_position_id": pos_id,
                "open_order_ids": [],
                "daily_pnl": "42.30",
                "heat": "2.0",
                "realized_pnl": "125.50",
                "daily_pnl_date": _now(),
                "cooldown_until": None,
                "error_message": None,
                "updated_at": _now(),
            }
        },
    }


def _build_decision() -> dict:
    return {
        "decision_id": str(uuid.uuid4()),
        "action": "enter_long",
        "confidence": "0.85",
        "risk_gated": False,
        "instrument_symbol": "BTC/USDT",
        "reason": "Confluence: RSI oversold + VWAP reclaim",
        "created_at": _now(),
        "metadata": {"quantity": "0.01", "entry_price": "65000.00"},
    }


def _build_signal() -> dict:
    return {
        "signal_id": str(uuid.uuid4()),
        "direction": "long",
        "strength": "0.78",
        "source_strategy": "mock-strategy-001",
        "instrument_symbol": "BTC/USDT",
        "is_expired": False,
        "created_at": _now(),
        "metadata": {"rsi": "28.4", "vwap_diff": "0.3%"},
    }


def _build_alert() -> dict:
    return {
        "alert_id": str(uuid.uuid4()),
        "level": "warning",
        "category": "risk",
        "message": "Daily PnL approaching 50% of max_daily_loss limit",
        "strategy_id": "mock-strategy-001",
        "created_at": _now(),
        "resolved": False,
    }


def _build_cycle_event() -> dict:
    return {
        "cycle_id": str(uuid.uuid4()),
        "bar_close_utc": _now(),
        "checkpoint_seq": int(time.monotonic() * 1000) % 1_000_000,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock ITM for BTE API testing")
    parser.add_argument("--interval", type=float, default=2.0, help="Publish interval (s)")
    parser.add_argument("--redis-host", default=os.environ.get("BTE_REDIS_HOST", "localhost"))
    parser.add_argument("--redis-port", type=int, default=int(os.environ.get("BTE_REDIS_PORT", "6379")))
    parser.add_argument("--redis-db", type=int, default=int(os.environ.get("BTE_REDIS_DB", "0")))
    args = parser.parse_args()

    import redis
    r = redis.Redis(
        host=args.redis_host,
        port=args.redis_port,
        db=args.redis_db,
        decode_responses=True,
    )

    # Ping test
    try:
        r.ping()
        print(f"[mock-itm] Connected to Redis {args.redis_host}:{args.redis_port}/{args.redis_db}")
    except Exception as exc:
        print(f"[mock-itm] ERROR: Cannot connect to Redis: {exc}")
        raise SystemExit(1)

    print(f"[mock-itm] Publishing every {args.interval}s. Ctrl+C to stop.")
    cycle = 0
    while True:
        try:
            snap = _build_snapshot()
            decision = _build_decision()
            signal = _build_signal()
            alert = _build_alert()
            cycle_ev = _build_cycle_event()

            # Write KV state
            r.set("itm:state:snapshot", json.dumps(snap), ex=90_000)
            r.rpush("itm:decisions:recent", json.dumps(decision))
            r.ltrim("itm:decisions:recent", -500, -1)
            r.rpush("itm:signals:recent", json.dumps(signal))
            r.ltrim("itm:signals:recent", -500, -1)
            r.hset("itm:alerts:active", alert["alert_id"], json.dumps(alert))

            # Publish to all channels
            r.publish("itm:cycle", json.dumps(cycle_ev))
            r.publish("itm:capital", json.dumps(snap["risk"].get("capital_state", {})))
            r.publish("itm:positions", json.dumps(list(snap["positions"].values())))
            r.publish("itm:decisions", json.dumps(decision))
            r.publish("itm:signals", json.dumps(signal))
            r.publish("itm:alerts", json.dumps(alert))
            r.publish("itm:strategies", json.dumps(list(snap["strategies"].values())))

            cycle += 1
            print(f"[mock-itm] cycle={cycle} seq={snap['checkpoint_seq']}", flush=True)
            time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n[mock-itm] Stopped.")
            break
        except Exception as exc:
            print(f"[mock-itm] ERROR: {exc}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
