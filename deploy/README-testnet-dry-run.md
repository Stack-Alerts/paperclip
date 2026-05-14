# Binance Testnet Paper Trading — Deployment Guide

## Overview

Deploys the ITM (Intelligent Trade Manager) as a long-running systemd service
for 72-hour continuous testnet dry runs on Binance Futures Testnet.

## Safety

**`ITM_PAPER_TRADING=true` by default.** The kill-switch is ON — no outbound
Binance API calls are made. To run against real testnet, you must explicitly
set `ITM_PAPER_TRADING=false`.

## Prerequisites

- Python virtual environment (`venv/`) with dependencies installed
- `.env` file configured (see `.env.example`)
- Binance Futures Testnet credentials (only for live testnet mode):
  - Get keys: https://testnet.binancefuture.com
  - Set `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET` in `.env`

## Installation

```bash
# Install systemd service (paper_trading=true)
bash deploy/systemd/install-itm-testnet-dry-run.sh

# Verify it's running
systemctl --user status itm-testnet-dry-run.service
journalctl --user -u itm-testnet-dry-run.service -n 50 -f
```

## Switching to Live Testnet Mode

**Only proceed if testnet credentials are configured in `.env`.**

```bash
# Override the paper_trading env var via systemd drop-in
systemctl --user edit itm-testnet-dry-run.service
```

Add:
```
[Service]
Environment=ITM_PAPER_TRADING=false
Environment=BINANCE_TESTNET_API_KEY=your_key
Environment=BINANCE_TESTNET_API_SECRET=your_secret
```

Then restart:
```bash
systemctl --user restart itm-testnet-dry-run.service
```

## Monitoring

```bash
# Tail logs
journalctl --user -u itm-testnet-dry-run.service -f

# View latest dry run report
cat logs/dry_run/dry_run_report.md

# Check final snapshot
cat logs/dry_run/final_snapshot.json

# View post-trade records
cat logs/dry_run/post_trade.jsonl
```

## Architecture

```
systemd service
    └── run_testnet_dry_run.py  (launcher)
        └── DryRunRunner
            ├── ExecutionEngine  (RiskGate → OrderFactory → BinanceClient)
            ├── PositionVerifier (H.1 reconciliation)
            ├── MultiStrategyOrchestrator  (strategy loading + signalling)
            └── DryRunMonitor    (6 success criteria)
```

## Pre-Trade Risk Enforcement

Every order passes through the RiskGate which enforces:
- Max position size: 1.0 BTC
- Min position size: 0.001 BTC  
- Stop-loss: 2% mandatory on every entry
- Daily loss limit: $500
- Leverage: 1.0 (no margin)
- Account heat: RED/YELLOW/green
- Capital governor: per-trade and total exposure caps

## Files

| File | Purpose |
|------|---------|
| `deploy/systemd/itm-testnet-dry-run.service` | Systemd unit file |
| `deploy/systemd/install-itm-testnet-dry-run.sh` | Installation script |
| `deploy/itm_testnet_config.yaml` | ITM config for testnet env |
| `scripts/run_testnet_dry_run.py` | Entry point launcher |
| `src/itm/dry_run/runner.py` | DryRunRunner orchestration |
| `src/itm/risk/risk_gate.py` | Pre-trade risk enforcement |
| `src/strategies/risk_enforcer.py` | NautilusTrader risk enforcer |

## Recovery

If the service crashes:
- systemd auto-restarts after 30s (`Restart=on-failure`)
- The dry run starts fresh (no state persistence in paper mode)
- Logs are preserved for post-mortem analysis
