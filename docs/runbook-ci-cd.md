# Runbook: CI/CD Pipeline

**Last updated:** 2026-05-12
**Owner:** RepoSteward / DocWriter
**Monitoring:** `.github/workflows/*.yml` (15 workflows)

---

## 1. Overview

The CI/CD pipeline consists of 15 GitHub Actions workflows that handle linting, testing, security gating, documentation indexing, impact analysis, and scheduled maintenance tasks.

### Workflow Summary

| # | Workflow | Trigger | Cadence | Run Time |
|---|---|---|---|---|
| 1 | Lint | push/PR → main | Per commit | <1m |
| 2 | Test & Coverage | push/PR → main, nightly 04:00 UTC | Per commit + daily | ~5m |
| 3 | Lock Gate | push/PR → main | Per commit | <1m |
| 4 | Apply Branch Protection | push → main | Per commit to main | <30s |
| 5 | Freeze-Lift Evidence | push/PR → main, nightly 05:00 UTC | Per commit + daily | ~2m |
| 6 | Blast Radius Worker | Every 5 min + webhook | 5 min cycle | ~1m |
| 7 | Impact Gate Worker | Every 5 min + webhook | 5 min cycle | ~1m |
| 8 | Impact Gate Scan Done | Every 5 min | 5 min cycle | ~1m |
| 9 | Touch Index Bug Worker | Every 15 min + webhook | 15 min cycle | ~2m |
| 10 | Touch Index FR Worker | Every 15 min + webhook | 15 min cycle | ~2m |
| 11 | Backfill — Close Stale Runs | Hourly | 60 min cycle | ~30s |
| 12 | Dep Graph Refresh | Nightly 02:00 UTC | Daily | ~1m |
| 13 | Lock Gate Nightly Alert | Nightly 03:00 UTC | Daily | ~30s |
| 14 | Lock Exception Sign-Off | repository_dispatch | On demand | ~30s |
| 15 | OpenCode Watchdog | Every 15 min | 15 min cycle | ~30s |

---

## 2. Quality Gates (Push/PR to main)

These workflows run on every push or PR to `main`. All must pass for merge.

### 2.1 Lint (`lint.yml`)

**Purpose:** Enforce code quality rules.

- **Ruff lint:** Checks `src/` for `T201` (no print()) and `DTZ003` (timezone-aware datetimes)
- **Secrets audit:** Runs `scripts/audit/secrets_audit.py` to detect hardcoded credentials

**Failure remediation:**
```
ruff check src/ --select T201,DTZ003
# Fix violations, re-push
```

### 2.2 Test & Coverage (`test.yml`)

**Purpose:** Run unit tests, integration tests, and enforce coverage minimum.

- **pytest + coverage gate:** Runs tests under `tests/test_blast_radius/`, `tests/test_impact_gate/`, `tests/test_touch_index/`, `tests/strategy_builder/`, `tests/optimizer_v3/test_error_recovery.py`, `tests/itm/state/`. Coverage threshold: **20%** (fail-under).
- **Real-data regression:** `tests/integration/test_btcaaaaa_745_multicore_real_data_regression.py`
- **Canary smoke:** `tests/bug_regression/test_canary_trade_execution.py`
- Requires PostgreSQL 17 service container.
- Nightly failures post alert to Paperclip via `scripts/nightly_test_alert.py`.

**Failure remediation:**
```bash
# Reproduce locally
source venv/bin/activate
python -m pytest <test_path> -v --tb=long
```

### 2.3 Lock Gate (`lock-gate.yml`)

**Purpose:** Prevent unauthorized changes to locked modules. See [lock-gate.md](lock-gate.md) for full documentation.

- Runs `scripts/lock_gate.py` with JSON summary
- If blocked, creates CTO sign-off issue via `scripts/lock_gate_create_signoff.py`

**Failure remediation:** Follow lock exception process in [lock-gate.md](lock-gate.md).

### 2.4 Apply Branch Protection (`apply-branch-protection.yml`)

**Purpose:** Ensure `main` branch has required settings (1 approval review, enforce admins, conversation resolution).

- Runs on every push to main
- Idempotent — skips if protection already applied

**Failure remediation:** Check `GH_TOKEN` permissions. Manual: `gh api repos/{owner}/{repo}/branches/main/protection`.

### 2.5 Freeze-Lift Evidence (`freeze-lift-evidence.yml`)

**Purpose:** Verify lock-gate integrity through evidence tests.

- **Canary on main:** Lock gate passes on clean branches
- **Broken-branch block:** Locked module changes blocked without exception
- **Escape hatch:** Board and emergency exceptions unblock correctly
- **Locked-itself:** Gate infrastructure files are locked
- **Schema contracts:** Exceptions/registry schema integrity

**Failure remediation:** Investigate `tests/freeze_lift/` output. Usually indicates lock-gate config drift.

---

## 3. Worker Pipelines (Polling/Webhook)

### 3.1 Blast Radius Worker (`blast-radius-worker.yml`)

**Every 5 min + webhook.** Detects fix→in_review issue transitions and posts Blast Radius Reports.

- Scheduled: polls for transitions every 5 min
- `repository_dispatch` — immediate trigger on status change
- `workflow_dispatch` — manual: pass `issue_id`, `old_status`, `dry_run`, `loop_seconds`, `force_reprocess`

See [architecture/BLAST_RADIUS_WORKER.md](../architecture/BLAST_RADIUS_WORKER.md) and [runbook-blast-radius-worker.md](runbook-blast-radius-worker.md).

### 3.2 Impact Gate Worker (`impact-gate-worker.yml`)

**Every 5 min + webhook.** Runs Impact Gate on in_review fix issues.

- Scheduled: polls every 5 min
- `repository_dispatch` — immediate trigger
- `workflow_dispatch` — manual: `issue_id`, `old_status`, `dry_run`

### 3.3 Impact Gate Scan Done (`impact-gate-scan-done.yml`)

**Every 5 min.** Retroactively gates recently-completed fix/bug issues.

- Runs `scripts/scan_fix_issues_done.py` with retroactive mode
- Default lookback: 7 days (scheduled) or `days_back` input (manual)
- Alerts on ungated issues via `scripts/scan_done_alert.py`

### 3.4 Touch Index Bug Worker (`touch-index-bug-worker.yml`)

**Every 15 min + webhook.** Ingests file references from closed bug issues into the touch index.

- Runs `scripts/run_touch_index_bug_worker.py`
- Validates data quality via `scripts/validate_touch_index_bug.py --stale-days 30`
- See [architecture/TOUCH_INDEX_BUG_WORKER.md](../architecture/TOUCH_INDEX_BUG_WORKER.md)

### 3.5 Touch Index FR Worker (`touch-index-fr-worker.yml`)

**Every 15 min + webhook.** Ingests file references from updated FDR (Feature/Defect Request) issues.

- Runs `scripts/run_touch_index_fr_worker.py`
- Validates data quality via `scripts/validate_touch_index_fr.py --stale-hours 168`
- See [architecture/TOUCH_INDEX_FR_WORKER.md](../architecture/TOUCH_INDEX_FR_WORKER.md)

---

## 4. Scheduled Maintenance

### 4.1 Backfill — Close Stale Runs (`backfill-close-stale-runs.yml`)

**Hourly.** Closes Paperclip issues stuck `in_progress` past the staleness threshold (default: 60 min).

- Runs `scripts/backfill_close_stale_runs.py`
- Dry-run by default on manual trigger

### 4.2 Dependency Graph Refresh (`dep-graph-refresh.yml`)

**Nightly 02:00 UTC.** Regenerates `dep_graph.json` for lock gate reverse lookups.

- Runs `scripts/regenerate_dep_graph.py`
- Auto-commits changes to `dep_graph.json` with `[skip ci]`

### 4.3 Lock Gate Nightly Alert (`lock-gate-nightly-alert.yml`)

**Nightly 03:00 UTC.** Posts a summary of lock gate status.

- Runs `scripts/lock_gate_nightly_alert.py`
- Runs after dep-graph-refresh (02:00) so `dep_graph.json` is fresh

---

## 5. Event-Driven Workflows

### 5.1 Lock Exception Sign-Off (`lock-exception-signoff.yml`)

**Trigger:** `repository_dispatch` with `lock_exception_signed_off` type.

Processes approved lock exceptions — adds entry to `lock_gate_exceptions.json` and pushes.

Parameters: `issue_id`, `module`, `scope`, `approved_by`, `approval_id`, `expires_iso`, `dry_run`

---

## 6. Runbook Workflows

### 6.1 OpenCode Watchdog (`opencode-watchdog.yml`)

**Every 15 min.** Kills hanging opencode processes (silent >30 min).

- Runs `scripts/opencode_watchdog.py`
- Dry-run by default on manual trigger
- Uploads watchdog logs as artifact

---

## 7. Alerting

| Workflow | Alert Method |
|---|---|
| Nightly test failure | `scripts/nightly_test_alert.py` → Paperclip issue |
| Lock gate block | `scripts/lock_gate_create_signoff.py` → CTO sign-off issue |
| Impact Gate ungated issues | `scripts/scan_done_alert.py` → alert issue |
| Stale in_progress runs | Hourly auto-close (Paperclip API) |
| OpenCode hang | Auto-kill + logs artifact |

---

## 8. Failure Quick Reference

| Symptom | Likely Cause | Action |
|---|---|---|
| Lint fails | Print statement / naive datetime | Fix violation, re-push |
| Tests fail | Code regression / DB unavail | Check test output, reproduce locally |
| Lock gate blocks | Locked module changed | Get CTO sign-off |
| Worker not running | Rate limit / API key expired | Check secrets, check concurrency |
| stale runner stuck | Stale >60 min | Will be auto-closed on next hourly run |
| Branch protection missing | First push on new repo | Push again, workflow auto-applies |
