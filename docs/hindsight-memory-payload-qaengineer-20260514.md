# QAEngineer Hindsight Memory Payload — 2026-05-14

Populated per BTCAAAAA-26761. Structured facts for Hindsight memory bank ingestion.

---

## QA Process Architecture

### Atomic Verdict Rule (BTCAAAAA-1476)
- Comment + status PATCH + GET-readback are a single atomic operation
- Status declared inside comment via `## QA: PASS` / `## QA: FAIL` headings
- POST comment first, then PATCH status, then GET to verify persistence
- If any step fails, roll back all completed steps

### Post-PATCH Verification (BTCAAAAA-26631)
- Every status PATCH MUST be followed by GET readback
- HTTP 200 on PATCH is NOT sufficient proof
- If PATCH does not persist: retry once, then re-verify
- If retry also fails: escalate with blocked issue to CTO

### Definition of Done — Hard Gate
1. Verify local commits: `git log --oneline -5`
2. Check remote sync: `git fetch origin && git status` (must not be behind)
3. Push to remote: `git push origin main`
4. Confirm: `git log -1 origin/main` matches local HEAD

### Bug Reporting Rules
- Any bug found during QA MUST be reported, even if unrelated to current PR
- UI bugs (src/ui/, tests/ui_qt/) → UIEngineer (9113b321-771b-481d-8ae7-33765ed9b1f5)
- Other bugs → Bug Tracker project (53c5b306-abee-41f8-939d-730736aabd3a) → TestManager (d53906e4-5660-4a47-bef4-148a69979b20)
- Unrelated bugs do NOT block current QA sign-off

### Pre-Deployment Validation Checklist
- Unit tests pass, strategy handlers tested, edge cases covered
- UI tests: `QT_QPA_PLATFORM=offscreen pytest tests/ui_qt -v --tb=short`
- Anti-mock-pollution: `grep -r "import.*mock\|MagicMock\|patch" tests/ui_qt/` returns empty
- NautilusTrader type compliance: no bare float for Price/Quantity/Money, no string enum literals
- OHLCV data validation: no NaN, no zero volume, high>=low, open<=high, close<=high
- Risk params: MAX_POSITION_SIZE <= 1.0 BTC, stop loss 2%, daily loss limit $500, no leverage
- Backtest validation: reasonable trade count, no future-date fills, no look-ahead bias
- Code quality: no debug prints, no hardcoded keys, comprehensive logging, type hints
- StrategyResearcher EXPERT_MODE GO recommendation required
- Fact-check verification: `python scripts/qa_fact_check_pipeline.py scan`
- Paper-trading validation: ran successfully for minimum period

### Locked Module Exception (BTCAAAAA-1479)
- Changes to locked modules require documented CTO authorization
- Exception template: module name, lock reason, change description, CTO authorization link, scope, additional QA, rollback plan, review expiry (<=30 days)

---

## Test Framework Standards

### UI Tests (PyQt5)
- Always use `QT_QPA_PLATFORM=offscreen` — never run without it
- Tests under `tests/ui_qt/` with `qt_real` marker
- Standalone conftest at `tests/ui_qt/conftest.py` — no mock imports
- pytest-qt required: `pip install pytest-qt`
- Signal verification: `qtbot.waitSignal`, `qtbot.assertNotEmitted`
- State verification: `qtbot.waitUntil` for async updates (never `time.sleep`)

### Regression Tests
- Dedicated test files under `tests/bug_regression/` for each fixed bug
- Naming convention: `test_btcaaaaa_{issue_number}_regression.py`
- Each regression test verifies the fix via source inspection, AST parsing, or invariant testing

### Walkforward CI Thresholds
- Win rate >= 60%
- Profit factor >= 1.5
- Max drawdown <= 20%
- Minimum 20 trades
- Pipeline: `scripts/run_walkforward_ci.py` + `.github/workflows/walkforward-validation.yml`

---

## Common Bug Patterns Discovered

### Sliding Data Window
- **Root cause**: `datetime.now(timezone.utc)` in backtest config not floored to midnight UTC
- **Fix**: `.replace(hour=0, minute=0, second=0, microsecond=0)` on all end_date computations
- **Affected file**: `src/strategy_builder/ui/strategy_builder_main_window.py:1454`
- **Regression test**: `tests/bug_regression/test_btcaaaaa_26132_regression.py`

### QThread Destruction on Exit
- **Symptoms**: SIGABRT, "QThread: Destroyed while thread is still running" warnings
- **Fix**: Use QThreadPool with QRunnable for background loading instead of manual QThread
- **Caps**: MAX_LINES_PER_FILE=5000, MAX_FILES_ALL_LOGS=100

### Registry State Bleed
- **Problem**: Backtest engine state persists between runs causing cross-run contamination
- **Fix**: `registry.clear()` called between backtest runs in `multicore_backtest_engine.py:816`

### is_new_event Gate
- **Problem**: Duplicate event processing in session strategies
- **Fix**: `is_new_event` gate applied in `asia_session_50_percent.py:501`

### NautilusTrader Type Violations
- **Pattern**: bare `float` used for Price, Quantity, or Money
- **Pattern**: string literals used instead of `OrderSide.BUY`, `OrderType.MARKET`, `TimeInForce.GTC`
- **Fix**: Use `Price('x.xx')`, `Quantity(x)`, `Money('x.xx', CURRENCY)` and proper enum values

### AI Recommendations Tab Blank
- **Root cause**: `_allow_dialog_close()` never calls `_finalize_recommendations()`
- **Fix**: Ensure dialog close triggers recommendation finalization

### Per-Timeframe Scan Anchor + UTC Timezone
- **Root cause**: `_fetch_binance_range` not using UTC timezone consistently
- **Fix**: RC4c + RC6 fixes for per-timeframe scan anchor and UTC timezone

---

## ITM Architecture Phases Verified

| Phase | Description | Status |
|-------|-------------|--------|
| A | Core Domain Model | Verified |
| B | Data Management & Synchronization | Verified |
| C | State Management & Recovery Framework | Verified |
| D | Multi-Strategy Framework & Orchestrator | Verified |
| F | Risk, Capital & Account Heat Management | Verified |
| G | Execution Engine & Order Lifecycle | Verified |
| H | Exchange Verification + Testnet Dry Run | Verified |

### EXPERT_MODE Validations
- Backtest engine core: multicore engine, data provider, signal evaluator
- Full backtest engine: every signal, strategy, configuration
- Signal-accuracy differential audit
- Differential PnL audit (before/after check_required_signals gate)

---

## Recent QA Issues (May 8-14, 2026)

| Issue | Description | Date |
|-------|-------------|------|
| BTCAAAAA-26446 | Log Viewer Freeze Fix — QThreadPool, streaming, caps | May 14 |
| BTCAAAAA-26278/26279 | CI Walkforward Validation Pipeline | May 14 |
| BTCAAAAA-26132 | Sliding Data Window — midnight UTC floor fix | May 14 |
| BTCAAAAA-25896 | Dead-man's-switch monitor alert | May 13 |
| BTCAAAAA-25827 | Trade trace + engine correctness Phase 1+2a | May 13 |
| BTCAAAAA-25589 | Signal-accuracy differential audit | May 13 |
| BTCAAAAA-25474 | Differential PnL audit (check_required_signals gate) | May 13 |
| BTCAAAAA-24971 | ITM Section H — Exchange Verification + Testnet | May 13 |
| BTCAAAAA-22898 | EXPERT_MODE backtest engine core validation | May 13 |
| BTCAAAAA-22902 | Runtime update visibility + data panel fix | May 13 |
| BTCAAAAA-1478 | Live X11 UI-path verification (Mode 1 + Mode 2) | May 13 |
| BTCAAAAA-20258/20266 | Full backtest engine validation | May 12 |
| BTCAAAAA-4887 | Green-red flip forensics (72h) | May 12 |
| BTCAAAAA-7333 | bars-loaded pipeline fix | May 12 |
| BTCAAAAA-7289 | SECURITY P0: AWS key exposure | May 12 |
| BTCAAAAA-6869 | State Management & Recovery Framework | May 12 |
| BTCAAAAA-1663 | BacktestWorker regression test | May 12 |
| BTCAAAAA-1216 | Live UI: H1 vs H2 discrimination | May 11 |
| BTCAAAAA-1094 | Calibration cache fix live-UI verification | May 10 |
| BTCAAAAA-978 | asia_session_50_percent state reset fix | May 10 |
| BTCAAAAA-867 | _download_with_retry tz-aware fix regression | May 9 |
| BTCAAAAA-726 | ITM Live Trading kill-switch | May 9 |
| BTCAAAAA-563 | ITM Section G: Execution Engine | May 8 |
| BTCAAAAA-434 | ITM Section F: Risk/Capital | May 8 |
| BTCAAAAA-431 | ITM Section D: Multi-Strategy Framework | May 8 |
| BTCAAAAA-416/419/405 | ITM Sections B/C: Data + State Management | May 8 |
| BTCAAAAA-382 | AI Recommendations tab blank fix | May 8 |
| BTCAAAAA-377 | UDM Remediation Phase 1 | May 8 |
| BTCAAAAA-368 | RC4c+RC6 per-timeframe scan + UTC fix | May 7 |
| BTCAAAAA-358 | AI Recommendations tab regression | May 6 |

---

## Escalation Routing

| Blocker Type | Route To |
|---|---|
| GitHub admin / repo permissions | RepoSteward |
| X11 / display / GUI environment | LinuxSpecialist |
| Routines / cron / scheduled tasks | AutomationEngineer |
| Database schema / migrations | DatabaseAdministrator |
| UI verification / visual QA | QAEngineer (self) |
| Documentation / runbooks | DocWriter |
| Locked module / architecture decision | CTO (BTCAAAAA-1479 escape hatch) |

---

## Memory Gaps

1. No automated runbook freshness check for QA documentation
2. No centralized QA changelog tracking test suite evolution
3. No flaky test tracking database — flaky tests are handled ad-hoc
4. No coverage threshold enforcement in CI (coverage targets defined but not gated)
5. No smoke test marker carved out yet — full qt_real suite used for smoke tests
6. No automated regression test generation from bug reports