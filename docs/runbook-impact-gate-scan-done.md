# Runbook: Impact Gate Scan-Done Polling Daemon

**Status:** Operational  
**On-Call Owner:** AutomationEngineer  
**Alert Destination:** CTO (via alert creation)  
**Last Updated:** 2026-05-16

---

## Quick Reference

- **Workflow:** `.github/workflows/impact-gate-scan-done.yml`
- **Schedule:** Every 5 minutes (cron: `*/5 * * * *` UTC)
- **Primary Purpose:** Poll Paperclip for done fix/bug issues and ensure 100% Impact Gate coverage
- **Health Metric:** All done fix issues should have Impact Gate results within 24 hours

---

## Daily Health Check

Run this weekly to verify the daemon is functioning:

```bash
# Check recent workflow runs
gh run list -w impact-gate-scan-done.yml -L 10

# Look for:
# - Status: "completed success" for most recent scheduled runs
# - No sustained pattern of "failure" runs
# - If failures, check step "Run Impact Gate scan-done" for specific errors
```

### Expected Output Pattern

```
completed success Impact Gate Scan Done ... schedule ... main
completed success Impact Gate Scan Done ... schedule ... main
completed success Impact Gate Scan Done ... schedule ... main
```

If you see multiple consecutive failures, proceed to **Diagnosis** section.

---

## Diagnosis: Why Is the Daemon Failing?

### Symptom: All Runs Failing with "403 Forbidden" on Git Push

**Error Message:**
```
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
```

**Root Cause:** Self-hosted runner lacks proper GitHub credentials for repository write operations.

**Fix:** Applied in commit `15a970fb` (2026-05-16)
- Changed from `${{ secrets.GITHUB_TOKEN }}` to `${{ github.token }}`
- The standard `github.token` context variable is reliably injected by GitHub in all runners
- `secrets.GITHUB_TOKEN` is not automatically available on self-hosted runners
- Updated both the checkout action and the git push step

**Verification:** Run a manual workflow dispatch and check logs. The "Commit updated data quality snapshot and muted state" step should succeed.

### Symptom: Workflow Hangs on "Run Impact Gate scan-done" Step

**Root Cause:** Likely one of:
1. Paperclip API is unreachable or rate-limited
2. Blast Radius Touch Index is slow or offline
3. Runner is out of disk space

**Diagnosis Steps:**
```bash
# Check runner disk space
df -h /tmp /home/sirrus

# Check network connectivity to Paperclip
curl -s -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  "$PAPERCLIP_API_URL/api/companies/$PAPERCLIP_COMPANY_ID/issues?status=done&limit=1"

# Check if any blast radius workers are running
ps aux | grep blast_radius
```

**Fix:**
- If disk is full: Clear `/tmp` and old log files
- If Paperclip is down: No action required (auto-retries in 5 minutes)
- If Blast Radius is slow: Check Touch Index health (separate runbook)

### Symptom: Ungated Issues Detected (Coverage < 100%)

**Expected Behavior:** Should be rare (indicates a fix without Impact Gate verification).

**Investigation:**
1. Check the GitHub Actions run summary for ungated issue list
2. Review each ungated issue:
   - Does it have `touchedFiles` in description?
   - If yes: Why did retroactive gating skip it?
   - If no: Manual gating needed

**Manual Retroactive Gate (if needed):**
```bash
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
python scripts/scan_fix_issues_done.py \
  --retroactive \
  --days-back 7 \
  --json-summary
```

---

## Common Issues & Recovery

| Issue | Symptom | Recovery |
|-------|---------|----------|
| **Token Expired** | 403 on git push | Re-run workflow_dispatch; auto-works in next 5-min cycle |
| **Muted State Stale** | Issues re-gated repeatedly | Run `--retry-errors --retroactive` manual scan |
| **Network Transient** | One-off failure | No action; retries automatically |
| **Paperclip Maintenance** | Scan phase times out | Wait for Paperclip recovery; no repo action needed |

---

## Monitoring Dashboard

### GitHub Actions (Visual)

Navigate to: `.github/workflows/impact-gate-scan-done.yml` → "All runs"

**Check weekly for:**
- Green checkmarks on recent scheduled runs
- If red Xs: click run → view logs → check "Run Impact Gate scan-done" step

### Data Quality Snapshots (Automated Tracking)

**Location:** `data_quality_impact_gate_YYYYMMDD.json`

**Review daily snapshot** to track coverage trends:
```bash
tail -20 data_quality_impact_gate_$(date +%Y%m%d).json
```

**Expected metrics:**
```json
{
  "coverage_pct": 100.0,
  "gated": {
    "pass": ≥10,
    "fail": 0-5,
    "error": 0-2,
    "skipped": 0-10,
    "bypassed": 0
  },
  "ungated_count": 0
}
```

---

## Escalation Path

1. **Symptom:** Coverage dropped below 50% or ungated issues found
   - Workflow automatically creates an issue assigned to CTO
   - On-call should review and investigate

2. **Symptom:** Sustained workflow failures (5+ consecutive runs)
   - Check this runbook → **Diagnosis** section
   - If unresolved after 30 minutes: page CTO/Ops

3. **Symptom:** Data quality snapshots not being committed
   - Check repo write permissions (see "403 Forbidden" recovery above)
   - Verify `secrets.GITHUB_TOKEN` is set in GitHub repo settings

---

## Maintenance Window

**None required.** The daemon is fully self-healing:
- Transient failures auto-retry in 5 minutes
- ERROR entries in muted state auto-purge on hourly boundaries
- Ungated issues auto-detected and alerted

**Quarterly Review Recommended:**
- Scan the last 90 days of workflow runs for patterns
- Review coverage metrics trend
- Validate that all fix issues have been gated

---

## References

- **Workflow Code:** `.github/workflows/impact-gate-scan-done.yml`
- **Scan Script:** `scripts/scan_fix_issues_done.py`
- **Status Report:** `POLLING_DAEMON_STATUS_BTCAAAAA_27688.md` (last verification)
- **Architecture:** `docs/impact-gate/POLLING_DAEMON_DEPLOYMENT.md`

---

## Change Log

| Date | Change | Commit | Reason |
|------|--------|--------|--------|
| 2026-05-16 | Use gh CLI credential helper for git push | `db47e2d6` | Fix 403 errors on self-hosted runners |
| 2026-05-16 | First operational verification | `9249c6ce` | Confirm daemon working end-to-end |
| 2026-05-15 | Fix git push authentication | `f6e613a5` | Enable repo write for token-based CI |

---

**For emergency contact or escalations, reach CTO via Paperclip.**
