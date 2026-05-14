# Runbook: CI Walkforward Validation Pipeline

**Issue:** BTCAAAAA-25615
**Owner:** AutomationEngineer
**Last updated:** 2026-05-14

## Overview

The walkforward CI pipeline validates strategies against institutional-grade thresholds before paper trading. The CI runs pytest-based walkforward tests on 15m BTC data. A standalone runner script (`scripts/run_walkforward_ci.py`) is also available for local validation on 30m data.

## Quick start — local validation

```bash
# Validate a single strategy locally (uses 30m data directly)
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
- **Push/PR** to `main`/`master`: when strategy files, walkforward engine, or CI workflow change
- **Schedule:** nightly at 06:00 UTC
- **Manual:** `workflow_dispatch` (no input parameters — uses default test suite)

### Jobs
1. `walkforward-unit` — fast unit tests on `test_walkforward_test_engine.py` (no data dependency, ~0.3s)
2. `walkforward-strategy` — real-data threshold validation via pytest on 15m BTC bars

### Key differences from local runner
The CI does **not** use `scripts/run_walkforward_ci.py`. Instead, it runs:
```bash
python -m pytest tests/strategies/01_test_strategy_Reversal_M_Pattern_Standard.py \
  tests/strategies/02_test_strategy_Reversal_W_Pattern_Standard.py \
  tests/strategies/test_strategy_with_backtest.py \
  tests/strategies/walkforward_test.py \
  -v --tb=short --timeout=900 -p no:cacheprovider
```

These pytest test files implement walkforward logic with integrated building block detectors, loading `data/raw/BTC_USDT_PERP_15m.csv` directly.

### Artifacts
- `walkforward-reports`: test output log + `data/reports/walkforward_tests/` directory (90-day retention)
- `walkforward-registry`: consolidated `walkforward_results_registry.json` with `overwrite: true` (90-day retention, replaced each run)

### Nightly failure alert
When the scheduled run fails, `scripts/nightly_test_alert.py` creates a `critical`-priority issue assigned to the CTO with the CI run URL.

## Registry

The runner script (`scripts/run_walkforward_ci.py`) appends results to `walkforward_results_registry.json`:

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

The registry is written during CI and local runs. In CI, the runner step calls `scripts/run_walkforward_ci.py` which calls `update_registry()`, appending to any previously-downloaded registry artifact. The updated file is uploaded with `overwrite: true` as the `walkforward-registry` artifact, so the next CI run picks it up via `actions/download-artifact`.

## How the local runner works

1. Runner imports the strategy module dynamically via `importlib`
2. Extracts block weights from strategy source (parses `self.blocks['key'] = {'weight': N, ...}`)
3. Initializes real building block detector instances (16 detectors)
4. Binds `_analyze_blocks`, `_calculate_confluence`, `_calculate_tp_sl` from the strategy class
5. Loads 30m BTC data (`.pkl` or `.csv`), trims to `--days` recent bars
6. Walks forward bar-by-bar: builds bars incrementally, analyzes, checks confluence
7. Simulates trades via `backtest_simulator.py` (starting capital $10k, 15x max leverage)
8. Checks metrics against thresholds, writes registry, returns exit code

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `signals_checked=0` | Missing detector import | Check `Detectors initialized: N blocks` — verify >= 12 |
| `FATAL: missing required detectors` | Strategy uses detector not in spec | Add detector to `detector_specs` dict in runner |
| Timeout | Too many bars with too many detectors | Reduce `--days` or increase `--timeout` |
| `FATAL: data load failed` | 30m pickle or 15m CSV missing | Ensure `data/raw/BTC_USDT_PERP_30m.pkl` or `BTC_USDT_PERP_15m.csv` exists |
| `FATAL: failed to import strategy` | Missing NautilusTrader or other dep | Install deps: `pip install nautilus_trader pandas numpy` |
| CI: test timeout / OOM | pytest --timeout fires | Increase `--timeout` in CI workflow step or reduce test scope |

## Dependencies

- `data/raw/BTC_USDT_PERP_30m.pkl` (runner, 5.3 MB, 109,949 bars)
- `data/raw/BTC_USDT_PERP_15m.csv` (CI pytest tests)
- Building block detectors in `src/detectors/building_blocks/`
- `tests/strategies/backtest_simulator.py`
- Python 3.11+ with pandas, numpy
