# Runbook: CI Walkforward Validation Pipeline

**Issue:** BTCAAAAA-25615
**Owner:** AutomationEngineer
**Last updated:** 2026-05-14

## Overview

The walkforward CI pipeline validates every strategy against institutional-grade thresholds before paper trading. It runs real building block detectors on 30m BTC data and gates strategies on win rate, profit factor, drawdown, and trade count.

## Quick start

```bash
# Validate a single strategy locally
python scripts/run_walkforward_ci.py \
  --strategy src/strategies/strategy_01_reversal_m_pattern.py \
  --data data/raw/BTC_USDT_PERP_30m.pkl \
  --days 30

# Validate with custom thresholds and output
python scripts/run_walkforward_ci.py \
  --strategy src/strategies/strategy_02_reversal_w_pattern.py \
  --days 180 \
  --timeout 900 \
  --output /tmp/results.json
```

## Threshold gates

| Metric | Threshold | Exit code |
|---|---|---|
| Win rate | >= 60% | Fail if below |
| Profit factor | >= 1.5 | Fail if below |
| Max drawdown | <= 20% | Fail if above |
| Minimum trades | >= 20 | Fail if below |

Exit codes: `0` = pass, `1` = threshold failure, `2` = runtime error.

## CI workflow

**File:** `.github/workflows/walkforward-validation.yml`

### Triggers
- **Push/PR** to `main`: when strategy files, walkforward engine, or runner script change
- **Schedule:** nightly at 06:00 UTC
- **Manual:** `workflow_dispatch` with optional `--strategy` input

### Jobs
1. `walkforward-unit` — fast unit tests (no data dependency, ~0.3s)
2. `walkforward-gate` — real-data threshold validation on 30m bars

### Artifacts
- `walkforward-results`: per-strategy JSON output (30-day retention)
- `walkforward-registry`: cumulative `walkforward_results_registry.json` (90-day retention)

## Registry

Each run appends to `walkforward_results_registry.json`:

```json
{
  "last_updated": "2026-05-14T...",
  "entries": [
    {
      "strategy": "strategy_01_reversal_m_pattern",
      "file": "src/strategies/strategy_01_reversal_m_pattern.py",
      "timestamp": "2026-05-14T...",
      "passed": false,
      "metrics": {
        "total_trades": 0,
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "sharpe_ratio": 0.0
      }
    }
  ]
}
```

## How it works

1. Runner imports the strategy module dynamically via `importlib`
2. Extracts block weights from strategy source (parses `self.blocks['key'] = {'weight': N, ...}`)
3. Initializes real building block detector instances (16 detectors)
4. Binds `_analyze_blocks`, `_calculate_confluence`, `_calculate_tp_sl` from the strategy class
5. Loads 30m BTC data, trims to `--days` recent bars
6. Walks forward bar-by-bar: builds bars incrementally, analyzes, checks confluence
7. Simulates trades via `backtest_simulator.py` (starting capital $10k, 15x max leverage)
8. Checks metrics against thresholds, writes registry, returns exit code

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `signals_checked=0` | Missing detector import | Check `Detectors initialized: N blocks` — verify >= 12 |
| `FATAL: missing required detectors` | Strategy uses detector not in spec | Add detector to `detector_specs` dict in runner |
| Timeout | Too many bars with too many detectors | Reduce `--days` or increase `--timeout` |
| `FATAL: data load failed` | 30m pickle missing | Ensure `data/raw/BTC_USDT_PERP_30m.pkl` exists |
| `FATAL: failed to import strategy` | Missing NautilusTrader or other dep | Install deps: `pip install nautilus_trader pandas numpy` |

## Dependencies

- `data/raw/BTC_USDT_PERP_30m.pkl` (5.3 MB, 109,949 bars)
- Building block detectors in `src/detectors/building_blocks/`
- `tests/strategies/backtest_simulator.py`
- `src/strategies/universal_optimizer/modules/confluence_calculator.py`
- Python 3.11+ with pandas, numpy, nautilus_trader
