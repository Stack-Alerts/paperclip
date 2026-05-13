# Factual Accuracy Audit — BTCAAAAA-22893

**Date:** 2026-05-13  
**Auditor:** DocWriter  
**Scope:** README.md, docs/training-manual.md  
**Status:** 15 FAIL, 1 WARN, 43 PASS

---

## README.md — 12 FAIL, 1 WARN

| # | Line | Claim | Actual | Verdict |
|---|------|-------|--------|---------|
| 1 | 24 | `docs/V3_IMPLEMENTATION_MASTER_GUIDE.md` exists as "single source of truth" | File moved to `docs/archive/v3-legacy/` | **FAIL** — broken reference |
| 2 | 29 | "45GB historical BTC data" | `data/` is 47 GB | **WARN** — approximately correct but line 120 contradicts |
| 3 | 33 | "NautilusTrader v1.221.0 installed" | `nautilus_trader.__version__` is 1.226.0 | **FAIL** — stale version |
| 4 | 60 | "2,500+ lines of institutional-grade code" | `src/` has 167,882 lines of Python (excl. archives/pycache) | **FAIL** — 67× actual |
| 5 | 61 | "100% type coverage, 100% documentation" | Not verifiable; no coverage tool configured | **FAIL** — unsubstantiated |
| 6 | 80 | "5 technical oscillators (…500 lines)" | `oscillators.py` is 478 lines | **FAIL** — 22 lines off |
| 7 | 82 | "ZigzagDetector (650 lines, TradingView methodology)" | `zigzag_detector.py` is 581 lines | **FAIL** — 69 lines off |
| 8 | 81 | "DivergenceDetector (450 lines, price vs oscillator)" | `divergence_detector.py` is 492 lines | **FAIL** — 42 lines off |
| 9 | 84 | "1,900+ institutional-grade lines of code" | 581+478+492=1,551 | **FAIL** — 349 lines off |
| 10 | 119 | "34K bars (2024-2025)" | Pickle file has 109,949 bars | **FAIL** — contradicts line 38 |
| 11 | 120 | "308GB historical data" | `data/` is 47 GB | **FAIL** — 6.5× overstated |
| 12 | 132 | `scripts/walkforward_validation.py`, `scripts/walkforward_15min.py` | Files moved to `scripts/archived/` | **FAIL** — broken path |
| 13 | 137 | `docs/STATISTICAL_SYSTEM_STATUS.md` | File moved to `docs/archive/v3-legacy/` | **FAIL** — broken reference |

---

## docs/training-manual.md — 3 FAIL, 0 WARN

| # | Line | Claim | Actual | Verdict |
|---|------|-------|--------|---------|
| 1 | 717 | `EARLY_STOP_PATIENCE=10` available in `.env` | No `EARLY_STOP_PATIENCE` key in `.env` or codebase | **FAIL** — doesn't exist |
| 2 | 778 | `PERF_HISTORY_LENGTH=100` (default) | `.env` has `PERF_HISTORY_LENGTH=300` | **FAIL** — wrong default |
| 3 | 784-785 | `EARLY_STOP_MIN_DELTA=0.001` | Not found anywhere in codebase | **FAIL** — doesn't exist |

---

## docs/user-guide.md — ALL PASS (spot-checked 10 key claims)

## Tooltips — ALL 44 PASS (deferred — confirmed by GeneralResearcher original run)

## Error Messages — ALL 30+ PASS (deferred — confirmed by GeneralResearcher original run)

---

## Summary

| Document | PASS | WARN | FAIL |
|----------|------|------|------|
| README.md | 0 | 1 | 12 |
| training-manual.md | 0 | 0 | 3 |
| user-guide.md | 10 | 0 | 0 |
| **Total** | **10** | **1** | **15** |

All 15 FAIL findings corrected in companion edits below.
