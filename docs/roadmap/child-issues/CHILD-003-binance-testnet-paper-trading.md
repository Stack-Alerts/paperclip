# CHILD-003: Binance Testnet Paper Trading Deployment

**Parent:** BTCAAAAA-25426  
**Priority:** P1  
**Owner:** Dev  
**Estimate:** 2 days  
**Dependencies:** CHILD-001 (needs at least 1 generated strategy to deploy)

---

## User Story

As the **CEO**, I want to see **1 production-grade strategy running on Binance testnet** so that I can verify the full pipeline from strategy generation → exchange connectivity → order execution before we commit capital.

## Acceptance Criteria

### AC-1: Binance testnet credentials and connectivity
- Binance testnet API key/secret configured (stored in `.env`, never committed)
- `src/data_manager/binance/` extended or wired to support testnet REST + WebSocket endpoints
- Connection health check endpoint returning: connected, latency ms, last heartbeat

### AC-2: Live data feed
- Real-time 1-minute bars from Binance testnet WebSocket
- Bar aggregation to 15-minute for strategy timeframe
- Data freshness < 60s per requirement (from `docs/strategies/strategy_development_guide.md`)
- Graceful reconnection on WebSocket drop (exponential backoff, max 5 retries)

### AC-3: Strategy execution on live data
- One strategy deployed (start with Strategy 01: M Pattern Reversal)
- Strategy receives live bars via `on_bar()`
- Signals generated but trades go to testnet only (paper balance)
- Order status tracked (filled, rejected, expired)

### AC-4: Paper trading dashboard
- A simple CLI or minimal UI showing:
  - Current positions
  - P&L (realized + unrealized)
  - Open orders
  - Strategy status (running/paused/error)
  - Last signal time and direction
- Updates every 30 seconds

### AC-5: Safety rails
- Hard-coded max position size (0.01 BTC)
- Daily loss limit ($100 on testnet)
- Kill switch: env var `PAPER_TRADING_DISABLE=1` stops all orders
- All orders log to `logs/paper_trading/` with full detail

## Definition of Done
- [ ] `python scripts/run_paper_trading.py --strategy 01` starts paper trading
- [ ] Live bars flowing from Binance testnet within 30s
- [ ] Strategy analyzing bars and generating signals
- [ ] Orders appearing on Binance testnet web UI
- [ ] P&L tracking positive/negative correctly
- [ ] Safety rails tested (kill switch, max position, daily limit)
- [ ] Documentation: `docs/runbook-paper-trading.md`

## References
- Strategy development guide: `docs/strategies/strategy_development_guide.md` (see Section 1.2 for execution flow)
- Data manager: `src/data_manager/binance/`
- NautilusTrader live trading: https://nautilustrader.io/docs/latest/user_guide/live/
- Existing strategy: `src/strategies/strategy_01_reversal_m_pattern.py`
