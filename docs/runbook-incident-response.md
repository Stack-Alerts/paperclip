# Runbook: Incident Response

**Last updated:** 2026-05-12
**Owner:** CTO / DocWriter
**Severity levels:** Sev1 (critical) → Sev3 (minor)

---

## 1. Incident Classification

| Severity | Definition | Examples | Response Time |
|---|---|---|---|
| **Sev1** | Trading system down, data loss, security breach | Backtest engine crash, DB corruption, leaked credentials | Immediate (<15 min) |
| **Sev2** | Component degraded, partial outage, non-critical data issue | Worker pipeline stuck, stale data, test flakiness | <1 hour |
| **Sev3** | Minor bug, cosmetic issue, documentation error | Wrong label in UI, typo in runbook, slow query | <1 business day |

---

## 2. Response Flow

```
DETECT
  │
  ▼
TRIAGE ──→ Sev1 ──→ DECLARE (Paperclip issue + Slack)
  │                  │
  │                  ▼
  │              CONTAIN
  │                  │
  │                  ▼
  │              RESOLVE
  │                  │
  │                  ▼
  └──→ Sev2/3 ──→ FIX (normal sprint flow)
                       │
                       ▼
                 VERIFY
                       │
                       ▼
                 POSTMORTEM
```

---

## 3. Detection

Incidents are detected through:

| Source | Mechanism | Action |
|---|---|---|
| GitHub Actions | Worker failure notification | Check run logs |
| Paperclip | Alert issues created (e.g. nightly test failure, impact gate alert) | Triage alert issue |
| OpenCode Watchdog | Hanging process killed | Check watchdog logs artifact |
| Lock Gate | Gate blocks on push | Route to CTO for sign-off |
| Monitoring | Manual observation | File bug issue |

---

## 4. Triage (First 15 Minutes)

### 4.1 Determine Severity

```bash
# Check recent CI failures
gh run list --workflow "Test and Coverage" --limit 5 --json conclusion,databaseId

# Check worker health
gh run list --workflow "Blast Radius Worker" --limit 3
gh run list --workflow "Impact Gate Worker" --limit 3

# Check for hanging processes (if you have access to the runner)
# Review latest watchdog artifact
```

### 4.2 For Sev1: Declare Incident

1. Create Paperclip issue with `severity: sev1` label
2. Ping CTO if not already engaged
3. Post in company comms channel

---

## 5. Containment

### 5.1 Git / Branch Issues

```bash
# Revert a bad merge
git revert HEAD
git push origin main

# Or hard reset (only if branch not shared)
git reset --hard HEAD~1
git push --force-with-lease
```

### 5.2 Worker Pipeline Issues

```bash
# Check concurrency group — workers may be queued
# Check secrets are valid:
#   PAPERCLIP_API_KEY, PAPERCLIP_API_URL, PAPERCLIP_COMPANY_ID
#   POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

# Manual trigger with dry-run to test
gh workflow run "Blast Radius Worker" -f dry_run=true
```

### 5.3 Database Issues

```bash
# Check connectivity
python -c "
from src.optimizer_v3.database.config import get_db_url
print(get_db_url())
"

# Check migration state
alembic current

# Restore from backup (DESTRUCTIVE — last resort)
python scripts/manage_backups.py restore latest_backup.sql.gz --drop --yes
```

### 5.4 Lock Gate Blocked

See [lock-gate.md](../lock-gate.md) and [runbook-module-lock.md](runbook-module-lock.md).

---

## 6. Resolution

### 6.1 Quick Fixes

| Symptom | Likely Fix |
|---|---|
| CI lint fails | Fix print() statements / datetime usage |
| Test failure | Check code regression, fix and push |
| Worker timeout | Bump timeout, split work, reduce batch size |
| DB connection refused | Restart PostgreSQL, check .env config |
| Stale run | Will be auto-closed within 60 min by backfill worker |

### 6.2 Standard Fix Path

```
1. Create fix branch from main
2. Implement fix
3. Push + create PR
4. Get review approval (branch protection requires 1 approval)
5. Merge to main
6. Verify CI passes on main
```

---

## 7. Verification

After resolution:

- [ ] CI passes across all relevant workflows
- [ ] Workers cycle without errors (wait 1-2 poll cycles)
- [ ] Lock gate passes (if module changes involved)
- [ ] Touch index catches up (FR + Bug workers)
- [ ] Data quality validation passes
- [ ] Blast radius reports are generated (if fix→in_review issues exist)
- [ ] Impact Gate validates the fix

```bash
# Quick health check
gh run list --limit 10 --json name,conclusion,status
```

---

## 8. Postmortem

For Sev1 incidents and recurring Sev2 issues:

1. **Timeline** — document detection→triage→contain→resolve timestamps
2. **Root cause** — what broke and why
3. **Detection gap** — how did we find out? Could it be faster?
4. **Fix** — what was changed to resolve
5. **Prevention** — what automation/rules prevent recurrence
6. **Action items** — track as child issues on the postmortem issue

Postmortem template: Create a new issue with label `postmortem`.

---

## 9. Escalation Matrix

| Issue | Route To | Method |
|---|---|---|
| GitHub admin / repo permissions | RepoSteward | GitHub issue / Paperclip |
| X11 / display / GUI | LinuxSpecialist | Paperclip |
| DB schema / migrations | DatabaseAdministrator | Paperclip |
| Locked module changes | CTO (escape hatch) | BTCAAAAA-1479 |
| Routine / cron failures | AutomationEngineer | Paperclip |
| UI bugs on X11 | QAEngineer | Paperclip |
| Runbook / doc gaps | DocWriter | Paperclip |
| Worker pipeline design | Architect | Paperclip |

---

## 10. Related Documents

- [runbook-ci-cd.md](runbook-ci-cd.md) — CI/CD pipeline documentation
- [runbook-database-migration.md](runbook-database-migration.md) — DB migration procedures
- [runbook-backup-restore.md](runbook-backup-restore.md) — backup/restore
- [runbook-module-lock.md](runbook-module-lock.md) — lock gate procedures
- [lock-gate.md](../lock-gate.md) — lock gate architecture
- [runbook-blast-radius-worker.md](runbook-blast-radius-worker.md) — Blast Radius worker
- [runbook-touch-index-bug-worker.md](runbook-touch-index-bug-worker.md) — Touch Index Bug worker
- [runbook-touch-index-fr-worker.md](runbook-touch-index-fr-worker.md) — Touch Index FR worker
- [SECURITY_AUDIT_20260512.md](../SECURITY_AUDIT_20260512.md) — security audit findings
