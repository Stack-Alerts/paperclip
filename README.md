# BTC Trade Engine

**Institutional-Grade BTC Automated Trading Platform**  
**Framework:** NautilusTrader (Rust-powered)  
**Strategy:** Composable Multi-Signal Building Block Architecture

## Quick Start

```bash
# Setup
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify
python -c "import nautilus_trader as nt; print(f'✅ v{nt.__version__}')"
```

## Documentation

**START HERE:** `docs/archive/v3-legacy/V3_IMPLEMENTATION_MASTER_GUIDE.md`

Legacy 14-day implementation plan (archived).

## Project Status

- [x] Framework selected: NautilusTrader ✅
- [x] Data ready: 47GB historical BTC data ✅
- [x] Pattern detectors: Copied & ready ✅
- [x] **Day 1 COMPLETE:** Environment setup ✅
  - [x] Virtual environment created
  - [x] NautilusTrader v1.226.0 installed
  - [x] Installation verified
  - [x] Data catalog configured
- [x] **Day 2 COMPLETE:** Data validation ✅
  - [x] Data catalog setup script created
  - [x] 109,949 bars loaded and validated
  - [x] NautilusTrader Bar conversion working
  - [x] Simple backtest test passed
- [x] **Day 3 COMPLETE:** Pattern integration ✅
  - [x] Pattern adapter created (framework-agnostic)
  - [x] M-pattern detection working (5 patterns found in 1K bars)
  - [x] W-pattern detection working (3 patterns found in 1K bars)
  - [x] Signal generation verified with proper SL/TP
- [x] **Day 4 COMPLETE:** M-Pattern Strategy ✅
  - [x] MPatternStrategy class created
  - [x] Strategy initialization working
  - [x] Pattern detection integrated
  - [x] Risk management implemented
  - [x] Order submission logic ready
- [x] **Day 5 COMPLETE:** W-Pattern Strategy ✅
  - [x] WPatternStrategy class created
  - [x] Strategy initialization working (LONG positions)
  - [x] Pattern detection integrated
  - [x] Risk management mirrored from M-pattern
  - [x] Both patterns ready for backtesting
- [x] **PHASE 1 COMPLETE:** Strategy Implementation (Days 1-5) ✅
  - [x] All core infrastructure operational
  - [x] Core strategy infrastructure operational (M/W pattern system)
  - [x] Ready for backtest execution
- [x] **Day 6 COMPLETE:** Backtest Framework ✅
  - [x] BacktestEngine fully configured
  - [x] All 11 API issues resolved
  - [x] Data loading updated (2024-2025)
  - [x] Strategies execute end-to-end
  - [x] Pattern detection operational (9 patterns/100 bars)
  - [x] Order submission working (100% entry rate)
  - [x] Framework 100% complete
- [x] **Day 7 COMPLETE:** Exit Logic & Path B Planning ✅
  - [x] Stop loss orders implemented
  - [x] Take profit orders implemented
  - [x] Positions close properly (4 closed in 100 bars)
  - [x] P&L calculation accurate (-$6.29 validates system works)
  - [x] Full baseline trading system operational
  - [x] Path B implementation plan created (sophisticated V2)
- [x] **Day 8 COMPLETE:** Zigzag Foundation + Divergence Detection ✅
  - [x] ZigzagDetector implemented (581 lines, TradingView methodology)
  - [x] 5 technical oscillators (RSI, CCI, CMO, MFI, ROC - 478 lines)
  - [x] DivergenceDetector (492 lines, price vs oscillator)
  - [x] EXPERT VERIFIED: 100% accuracy (14/14 divergences matched)
  - [x] 1,551 institutional-grade lines of code
  - [x] Documentation complete, committed to git (b5c3106)
- [x] **Day 9-10 COMPLETE:** M/W System Validation + Statistical Investigation ✅
  - [x] M/W bug fixes (3 critical bugs found via EXPERT MODE)
  - [x] Walk-forward validation (30min: 68.6%, 15min: 67.7%)
  - [x] Multi-timeframe testing (timeframe-robust)
  - [x] Statistical system investigation (shelved - lookahead bias)
  - [x] **M/W System: DEPLOYMENT-READY** ✅
  - [x] **Statistical System: SHELVED** (see docs/archive/v3-legacy/STATISTICAL_SYSTEM_STATUS.md)
- [ ] **Days 11-13:** Building Blocks & Advanced Strategies 🎯 ← **NEXT**
  - [ ] Additional pattern building blocks
  - [ ] Confluence strategies
  - [ ] Advanced entry/exit logic
  - [ ] Performance optimization
- [ ] **Day 14:** Final Validation & Deployment
  - [ ] Full validation on live-like conditions
  - [ ] Paper trading setup
  - [ ] Production readiness check

## Key Files

**Implementation Guides:**
- `docs/archive/v3-legacy/V3_IMPLEMENTATION_MASTER_GUIDE.md` - Legacy 14-day implementation plan (archived)
- `docs/archive/v3-legacy/DAY8_PATH_B_PLAN.md` - Sophisticated V2 implementation plan (Days 8-13)

**Specifications:**
- `docs/building-blocks/patterns-research/SOPHISTICATED_M_PATTERN_DETECTOR_SPEC.md` - V2 detector architecture
- `docs/archive/v3-legacy/NAUTILUS_TRADER_ANALYSIS.md` - Framework analysis

**Code:**
- `src/strategies/strategy_01_reversal_m_pattern.py` - M-pattern strategy (baseline)
- `src/indicators/pattern_adapter.py` - Pattern detection adapter
- `scripts/run_backtest_matrix.py` - Backtest execution script

**Data:**
- `data/raw/BTC_USDT_PERP_30m.pkl` - 109,949 bars (2024-2025)
- `data/` - 47GB historical data

**Current Status:** Day 9-10 complete (71%), M/W System validated (68.6%/67.7%) and deployment-ready

**Next Steps:** Building block patterns and confluence strategies (Days 11-13)



## Strategy Factory (BTCAAAAA-25614)

Template-based generator for production-grade NautilusTrader strategies.

### Usage

```bash
# Generate a single strategy from a JSON config
python scripts/generate_strategy.py --config strategy_definitions/my_strategy.json

# Batch generate from a directory of configs
python scripts/generate_strategy.py --config-dir strategy_definitions/ --start 1 --end 10

# List available building blocks
python scripts/generate_strategy.py --list-blocks
```

### Config Format

Strategy definitions are JSON files in `strategy_definitions/`.
See `strategy_definitions/m_pattern_reversal.json` for a full example.

### Generated Strategy Features

- Complete NautilusTrader `Strategy` subclass with all required methods
- RiskEnforcer pre-trade checks (position size, daily loss limit, stop loss)
- Centralized ConfluenceCalculator integration
- ATR-based dynamic TP/SL calculation
- Daily PnL tracking with UTC midnight reset

### Known Block Registry

The factory currently supports 19 building blocks across patterns, indicators,
and market structure categories. Use `--list-blocks` to see all available blocks.


## Validated Systems

### ✅ M/W Pattern System (DEPLOYMENT-READY)
- **30min Walk-Forward:** 68.6% win rate (1,266 trades)
- **15min Walk-Forward:** 67.7% win rate (1,316 trades)
- **Status:** Timeframe-robust, no lookahead bias
- **Scripts:** `scripts/archived/walkforward_validation.py`, `scripts/archived/walkforward_15min.py`
- **Docs:** `docs/archive/v3-legacy/EXPERT_MODE_MW_FIX_COMPLETE.md`

### ⚠️ Statistical System (SHELVED)
- **Status:** Lookahead bias identified, not viable for walk-forward
- **Details:** See `docs/archive/v3-legacy/STATISTICAL_SYSTEM_STATUS.md`
- **Future:** Can revisit with different approach

## Contact

Questions? See Emergency Contacts in master guide.

**Let's build! 🚀**
