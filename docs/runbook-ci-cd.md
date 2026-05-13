# Runbook: CI/CD Pipeline Reference

**Last updated:** 2026-05-13
**Owner:** RepoSteward / DocWriter
**Audience:** All developers, agents, and on-call responders

---

## 1. Pipeline Overview

The system runs **17 GitHub Actions workflows** organized into three tiers:

| Tier | Trigger | Workflows |
|------|---------|-----------|
| **Gate** | Every PR/push to main | `lint.yml`, `test.yml`, `lock-gate.yml`, `freeze-lift-evidence.yml` |
| **Worker** | Scheduled + webhook | `blast-radius-worker.yml`, `touch-index-bug-worker.yml`, `touch-index-fr-worker.yml`, `impact-gate-worker.yml`, `impact-gate-scan-done.yml` |
| **Infrastructure** | Scheduled | `dep-graph-refresh.yml`, `lock-gate-nightly-alert.yml`, `backfill-close-stale-runs.yml`, `opencode-watchdog.yml`, `apply-branch-protection.yml`, `lock-exception-signoff.yml` |

---

## 2. Gate Workflows (PR/Push)

### 2.1 Lint (`lint.yml`)

- **Trigger:** Push/PR to `main` or `master`
- **Jobs:**
  - `ruff` — ruff check on `src/` for `T201` (no print statements) and `DTZ003` (no naive datetimes)
  - `secrets-audit` — runs `scripts/audit/secrets_audit.py`
- **Failure action:** Block PR merge. Fix and push.

### 2.2 Test and Coverage (`test.yml`)

- **Trigger:** Push/PR to `main`/`master` + nightly at 04:00 UTC
- **Services:** PostgreSQL 17 (ephemeral CI container)
- **Jobs:**
  - `test` — pytest with coverage gate (≥20%). Runs strategy builder, optimizer, ITM state, and gate tests.
  - `integration-real-data` — multicore real-data regression (BTCAAAAA-745)
  - `canary-smoke` — canary trade execution smoke test (BTCAAAAA-1476)
- **Failure action (nightly):** Auto-creates `critical` Paperclip issue via `scripts/nightly_test_alert.py`

### 2.3 Lock Gate (`lock-gate.yml`)

- **Trigger:** Push/PR to `main`/`master`
- **Script:** `scripts/lock_gate.py --json-summary`
- **On block:** Auto-creates CTO sign-off Paperclip issue via `scripts/lock_gate_create_signoff.py`
- **Reference:** [runbook-module-lock.md](runbook-module-lock.md)

### 2.4 Freeze-Lift Evidence (`freeze-lift-evidence.yml`)

- **Trigger:** Push/PR to `main`/`master` + nightly at 05:00 UTC
- **Tests:** `tests/freeze_lift/` — validates lock gate behavior:
  - Canary on main (clean branches pass)
  - Broken-branch block (locked module changes blocked without exception)
  - Escape hatch Path A+B (board/emergency exceptions unblock)
  - Locked-itself (gate infrastructure files are locked)
  - Schema contracts (exceptions/registry schema integrity)

---

## 3. Worker Workflows (Scheduled + Webhook)

### 3.1 Blast Radius Worker (`blast-radius-worker.yml`)

- **Schedule:** Every 5 minutes
- **Trigger:** `repository_dispatch` (issue status changed)
- **Purpose:** Detect `fix → in_review` transitions, post Blast Radius report comments
- **Script:** `scripts/run_blast_radius_worker.py`
- **State caching:** Uses GitHub Actions cache for `data/blast_radius_worker_state.json`

### 3.2 Touch Index Bug Worker (`touch-index-bug-worker.yml`)

- **Schedule:** Every 15 minutes
- **Trigger:** `repository_dispatch` (issue created/updated/status changed)
- **Purpose:** Ingest file references from newly-closed bug issues into touch index
- **Validation:** `scripts/validate_touch_index_bug.py --stale-days 30`

### 3.3 Touch Index FR Worker (`touch-index-fr-worker.yml`)

- **Schedule:** Every 15 minutes
- **Trigger:** `repository_dispatch` (issue created/updated/status changed)
- **Purpose:** Ingest file references from updated FDR (Feature/Defect Report) issues
- **Validation:** `scripts/validate_touch_index_fr.py --stale-hours 168`

### 3.4 Impact Gate Worker (`impact-gate-worker.yml`)

- **Schedule:** Every 5 minutes
- **Trigger:** `repository_dispatch` (issue status changed)
- **Purpose:** Run Impact Gate validation on `in_review` fix issues
- **Scripts:** `scripts/impact_gate_worker.py` / `scripts/run_impact_gate_worker.py`
- **Dependencies:** Qt headless system packages for UI smoke tests

### 3.5 Impact Gate Scan-Done (`impact-gate-scan-done.yml`)

- **Schedule:** Every 5 minutes
- **Purpose:** Retroactively gate recently-done fix/bug issues
- **Script:** `scripts/scan_fix_issues_done.py`
- **Output:** Writes `data_quality_impact_gate_{date}.json` snapshot
- **Alerting:** Creates alert Paperclip issue for ungated issues via `scripts/scan_done_alert.py`

---

## 4. Infrastructure Workflows (Scheduled)

### 4.1 Dependency Graph Refresh (`dep-graph-refresh.yml`)

- **Schedule:** Nightly at 02:00 UTC
- **Purpose:** Regenerate `dep_graph.json` for lock gate reverse-dependency lookups
- **Script:** `scripts/regenerate_dep_graph.py`
- **Output:** Auto-commits updated `dep_graph.json` with `[skip ci]`

### 4.2 Lock Gate Nightly Alert (`lock-gate-nightly-alert.yml`)

- **Schedule:** Nightly at 03:00 UTC (after dep-graph refresh)
- **Purpose:** Generate nightly lock gate alert report
- **Script:** `scripts/lock_gate_nightly_alert.py`

### 4.3 Backfill — Close Stale Runs (`backfill-close-stale-runs.yml`)

- **Schedule:** Hourly
- **Purpose:** Auto-close stale `in_progress` Paperclip issues
- **Script:** `scripts/backfill_close_stale_runs.py`
- **Config:** `--stale-minutes 60`, dry-run mode supported via `workflow_dispatch`

### 4.4 OpenCode Watchdog (`opencode-watchdog.yml`)

- **Schedule:** Every 15 minutes
- **Purpose:** Kill hanging opencode processes on the runner
- **Script:** `scripts/opencode_watchdog.py --verbose`
- **Artifacts:** Uploads watchdog logs (7-day retention)

### 4.5 Apply Branch Protection (`apply-branch-protection.yml`)

- **Trigger:** Push to `main`
- **Purpose:** Ensures branch protection is applied to `main`:
  - 1 required approving review
  - Dismiss stale reviews
  - Require conversation resolution
  - Enforce for admins
  - No force pushes, no deletions

### 4.6 Lock Exception Sign-Off (`lock-exception-signoff.yml`)

- **Trigger:** `repository_dispatch` (type: `lock_exception_signed_off`)
- **Purpose:** Process lock exception sign-off and add entry to `lock_gate_exceptions.json`
- **Script:** `scripts/lock_exception_signoff.py`

---

## 5. Secrets Reference

Workflows use these GitHub secrets:

| Secret | Used By |
|--------|---------|
| `PAPERCLIP_API_URL` | All workers, lock gate, test alert |
| `PAPERCLIP_API_KEY` | All workers, lock gate, test alert |
| `PAPERCLIP_COMPANY_ID` | All workers, lock gate, test alert |
| `PAPERCLIP_BOARD_API_KEY` | Backfill close stale runs |
| `POSTGRES_HOST` | Workers (DB-connected) |
| `POSTGRES_PORT` | Workers (DB-connected) |
| `POSTGRES_DB` | Workers (DB-connected) |
| `POSTGRES_USER` | Workers (DB-connected) |
| `POSTGRES_PASSWORD` | Workers (DB-connected) |

---

## 6. Common Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Lint fails | `print()` statement or `datetime.utcnow()` | Use `structlog` and `datetime.now(timezone.utc)` |
| Test coverage < 20% | Missing or low-coverage tests | Add tests for uncovered code |
| Lock gate blocks PR | Locked module changed without exception | Request exception via CTO sign-off (see [runbook-module-lock.md](runbook-module-lock.md)) |
| Worker timeout | Large batch, slow DB, or resource contention | Bump timeout or reduce batch size in workflow config |
| Secrets missing | `.env` not configured or secrets not set in repo | Check GitHub repo settings → Secrets and variables |
| DB connection refused | PostgreSQL service not started or credentials wrong | Verify `POSTGRES_*` secrets and service configuration |
| Nightly test alert fired | Scheduled test suite failed | Check CI run logs, fix regression, verify next nightly pass |

---

## 7. Manual Intervention

### 7.1 Rerun a Failed Workflow

```bash
gh run list --limit 5 --json databaseId,conclusion,status,name
gh run rerun <run-id>
```

### 7.2 Trigger a Workflow Manually

```bash
gh workflow run "Blast Radius Worker" -f dry_run=true -f issue_id="<uuid>"
```

### 7.3 Check All Workflow Status

```bash
gh run list --limit 20 --json name,conclusion,status,displayTitle
```

---

## 8. Related Documents

- [runbook-deployment.md](runbook-deployment.md) — deployment procedures
- [runbook-incident-response.md](runbook-incident-response.md) — incident handling
- [runbook-module-lock.md](runbook-module-lock.md) — lock gate procedures
- [runbook-database-migration.md](runbook-database-migration.md) — DB migration procedures
- [architecture/GIT_WORKFLOW.md](architecture/GIT_WORKFLOW.md) — git workflow guide
