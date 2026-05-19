# Runbook: PaperClip Recovery Monitor

**Owner:** AutomationEngineer
**Audience:** Platform Engineers, On-call responders, CTO
**Last Updated:** 2026-05-14

## Overview

The PaperClip Recovery Monitor detects and recovers stalled agent workflows by
polling the Paperclip API for `in_progress` issues that match configured
recovery scenarios (exchange API timeout, position mismatch, signal timeout,
orphaned checkouts, paused agents). It executes source-scoped recovery actions:
diagnostic comments, heartbeat invocations, agent resumption, forced release of
orphaned checkouts, and escalation issue creation.

Recovery actions are governed by per-issue cooldowns (120 min default) and a
max-attempt cap (3 attempts default) to prevent over-recovery and API thrashing.

## Architecture

```
Paperclip API          Recovery Monitor              Paperclip API
     |                        |                            |
     |---in_progress issues-->|                            |
     |---live runs----------->|                            |
     |                        |                            |
     |                        +--match scenarios----       |
     |                        +--check cooldowns----       |
     |                        +--execute recovery--->      |
     |                        |                            |
     |                        |<--post comment-------------|
     |                        |<--invoke heartbeat---------|
     |                        |<--resume agent-------------|
     |                        |<--force-release issue------|
     |                        |<--create escalation issue--|
     |                        |                            |
     |                        +--persist state---> ~/.paperclip/recovery_monitor_state.json
     |                        +--write log-------> ~/.paperclip/recovery_monitor.log
```

### State file

Stored at `~/.paperclip/recovery_monitor_state.json`. Shape:

```json
{
  "scenarios": {
    "exchange_api_timeout": {
      "<issue-uuid>": {
        "recovery_attempts": 2,
        "first_detected_at": "2026-05-14T12:00:00+00:00",
        "last_recovery_attempt_at": "2026-05-14T14:30:00+00:00",
        "last_action": "invoke_heartbeat",
        "escalation_issue_id": "<esc-uuid>"
      }
    }
  },
  "last_run_at": "2026-05-14T14:30:00+00:00"
}
```

- Each scenario tracks per-issue recovery attempts, last action, and escalation references.
- Cooldown is enforced per-scenario-scope × issue — an issue may have different
  recovery tracks for different scenarios simultaneously.
- State is persisted to disk after each run and uploaded as a workflow artifact.

### Configuration file

Stored at `scripts/paperclip_recovery_actions.json`. Controls:

| Section | Purpose |
|---|---|
| `defaults` | Global cooldown, max attempts, escalation agent, alert project |
| `agent_scope_map` | Groups agent UUIDs by domain (exchange, data, signal, risk, monitoring) |
| `recovery_scenarios` | Detection rules + ordered recovery action chains |

## CLI Usage

### Run with full recovery actions

```bash
python scripts/paperclip_recovery_monitor.py run [--dry-run] [--json-summary] [--scenario <id>]
```

### Show matches only (no actions taken)

```bash
python scripts/paperclip_recovery_monitor.py matches [--scenario <id>]
```

### Flags

| Flag | Description |
|---|---|
| `run` | Execute the recovery monitor (default subcommand) |
| `matches` | Show scenario matches without executing recovery actions |
| `--dry-run` | Log actions but do not execute API calls |
| `--json-summary` | Output structured JSON to stdout |
| `--scenario <id>` | Target a specific recovery scenario (e.g., `exchange_api_timeout`) |

### Per-scenario targeting

```bash
# Check only for exchange API timeouts
python scripts/paperclip_recovery_monitor.py matches --scenario exchange_api_timeout

# Execute recovery only for orphaned checkouts
python scripts/paperclip_recovery_monitor.py run --scenario orphan_checkout --dry-run
```

## Recovery Scenarios

The monitor ships with five recovery scenarios defined in
`scripts/paperclip_recovery_actions.json`:

| Scenario ID | Domain | Min Age | Detection | Recovery Chain |
|---|---|---|---|---|
| `exchange_api_timeout` | Exchange / Data agents | 2h | Live-run silence check (`suspicious`, `critical`) | Comment → Heartbeat → Escalate (CTO) |
| `position_mismatch` | Risk agents | 1h | Status only | Comment → Escalate (RiskAnalyst) |
| `signal_timeout` | Signal / Data agents | 3h | Live-run silence check (`suspicious`, `critical`) | Comment → Heartbeat → Escalate (NautilusEngineer) |
| `orphan_checkout` | All agents | 6h | Live-run silence (`critical` only) | Force-release → Escalate (CTO) |
| `agent_paused_stalled` | All agents | 2h | Status only | Resume agent |

### Scenario matching algorithm

For each issue × scenario pair, all of these must match:

1. **Enabled**: `scenario.enabled` is `true`
2. **Status**: Issue status matches `detection.status` (default: `in_progress`)
3. **Age window**: `issue_age >= min_age_hours AND issue_age <= max_age_hours`
4. **Agent scope**: If `agent_scopes` is non-empty, the issue's `assigneeAgentId`
   must be in one of the named scopes (resolved via `agent_scope_map`)
5. **Keywords**: If `issue_keywords` is non-empty, at least one keyword must
   appear in the issue title or description (case-insensitive)
6. **Live-run silence** (optional): If `check_live_runs` is `true`, at least one
   live run for the issue must have an `outputSilence.level` in
   `run_silence_levels`. If no live runs exist for the issue, this check passes
   (the issue is presumed orphaned from a run perspective).

### Batch threshold

If `min_issues_for_batch_alert` > 1, the scenario only fires when the number of
matched issues meets or exceeds the threshold. This prevents alert storms from
transient API blips.

## CI/CD Pipeline

Workflow: `.github/workflows/paperclip-recovery-monitor.yml`

### Triggers

| Trigger | Schedule / Event |
|---|---|
| `schedule` | Every 30 minutes (`*/30 * * * *`) |
| `workflow_dispatch` | Manual trigger with `dry_run`, `scenario`, `matches_only` inputs |

### Concurrency

Single implicit run — the scheduled run does `matches`-only (logging matches
without executing recovery). Manual `workflow_dispatch` runs execute full
recovery when `matches_only` is `false` and `dry_run` controls live vs.
simulated execution.

### Step sequence

1. **Checkout** repo
2. **Set up Python** 3.12
3. **Install dependencies** (`requests`, `python-dotenv`)
4. **Run matches** (scheduled) — writes `/tmp/recovery-matches.json`
5. **Run recovery** (manual only) — writes `/tmp/recovery-summary.json`
6. **Write step summary** — renders Markdown table to `$GITHUB_STEP_SUMMARY`
7. **Upload monitor logs** (`~/.paperclip/recovery_monitor.log`, 7-day retention)
8. **Upload recovery state** (`~/.paperclip/recovery_monitor_state.json`, 7-day retention)
9. **Upload summary artifact** (`/tmp/recovery-*.json`, 7-day retention)

### Environment Variables

| Variable | Source | Purpose |
|---|---|---|
| `PAPERCLIP_API_URL` | Secret | Paperclip API base URL |
| `PAPERCLIP_API_KEY` | Secret | API bearer token |
| `PAPERCLIP_COMPANY_ID` | Secret | Company UUID |
| `PAPERCLIP_BOARD_API_KEY` | Secret | Elevated key for `force-release` actions |

## Systemd Integration (Local Execution)

The recovery monitor can run locally as a systemd timer, providing a second
layer of detection independent of GitHub Actions availability.

### Unit files

| File | Location |
|---|---|
| `paperclip-recovery-monitor.service` | `deploy/systemd/` |
| `paperclip-recovery-monitor.timer` | `deploy/systemd/` |
| `install-recovery-monitor.sh` | `deploy/systemd/` |

### Timer schedule

Runs at the 15th and 45th minute of every hour, offsetting from the GitHub
Actions schedule (which runs at 0 and 30). This provides coverage every 15
minutes across the two schedulers.

### Install

```bash
cd deploy/systemd
DRY_RUN=true bash install-recovery-monitor.sh    # Verify
bash install-recovery-monitor.sh                  # Install
```

### Verify

```bash
systemctl --user status paperclip-recovery-monitor.timer
systemctl --user list-timers paperclip-recovery-monitor.timer
journalctl --user -u paperclip-recovery-monitor.service -n 20
```

### Uninstall

```bash
systemctl --user stop paperclip-recovery-monitor.timer
systemctl --user disable paperclip-recovery-monitor.timer
rm ~/.config/systemd/user/paperclip-recovery-monitor.{service,timer}
systemctl --user daemon-reload
```

## Rollback Procedure

If the monitor begins taking harmful recovery actions (e.g., force-releasing
valid issues, spamming comments):

1. **Disable both schedulers:**
   - GitHub Actions: Navigate to Actions → PaperClip Recovery Monitor → ... → Disable workflow
   - Systemd: `systemctl --user stop paperclip-recovery-monitor.timer && systemctl --user disable paperclip-recovery-monitor.timer`

2. **Reset recovery state** to prevent immediate re-trigger on restart:
   ```bash
   rm ~/.paperclip/recovery_monitor_state.json
   ```

3. **Revert config** if a scenario misconfiguration caused the issue:
   ```bash
   git log --oneline scripts/paperclip_recovery_actions.json | head -5
   git revert <bad-commit-hash> --no-edit
   git push origin main
   ```

4. **Validate with dry-run first:**
   ```bash
   python scripts/paperclip_recovery_monitor.py run --dry-run --json-summary
   ```

5. **Re-enable** after fix is validated.

### Manual cleanup of erroneous recovery comments

```
No built-in tooling — delete comments via Paperclip API:
curl -X DELETE "$PAPERCLIP_API_URL/api/issues/$ISSUE_ID/comments/$COMMENT_ID" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY"
```

## Monitoring & Alerting

### Log file

`~/.paperclip/recovery_monitor.log` — auto-rotated at 1 MB with one backup
(`recovery_monitor.log.1`).

### Key log patterns

| Log pattern | Meaning |
|---|---|
| `Recovery monitor starting` | Run began (includes `(dry-run)` suffix when applicable) |
| `Fetched N in_progress issues` | API poll completed |
| `Fetched N live runs` | Live-run data loaded |
| `Scenario X: N matched issues (ISSUE-1, ...)` | Scenario triggered |
| `Posted recovery comment on issue X` | Diagnostic comment posted |
| `Invoked heartbeat for agent X` | Heartbeat triggered |
| `Resumed agent X` | Paused agent resumed |
| `Force-released issue X` | Orphaned checkout released |
| `Created escalation issue X for stalled Y` | Escalation chain started |
| `Issue X scenario Y in cooldown, skipping` | Cooldown suppression active |
| `Recovery monitor complete: N issues scanned, M scenarios, K actions taken` | Run summary |
| `[DRY-RUN] Would ...` | All dry-run actions are prefixed |
| `Recovery action X failed for issue Y: ...` | Action-level error (non-fatal) |
| `Failed to fetch in_progress issues: ...` | Fatal API error, run aborted |
| `Cannot force-release issue X: PAPERCLIP_BOARD_API_KEY not set` | Missing elevation key |

### Recovery state artifact

Each GitHub Actions run uploads `recovery-monitor-state` artifact (7-day
retention). Download for debugging:

```bash
gh run download <run-id> -n recovery-monitor-state
cat recovery_monitor_state.json | python -m json.tool
```

### Escalation flow

Recovery actions follow an ordered chain. Escalation (`create_escalation`) is
typically the last action in a chain:

```
Match → add_comment → invoke_heartbeat → [cooldown resets] → ...
                                                    → [max attempts reached]
                                                    → create_escalation (CTO)
```

Escalation issues are created in the `alert_project_id` project, assigned to
the scenario's `escalation_agent_id`, marked `high` priority, and linked to the
stalled issue via `blockedByIssueIds`.

## Configuration Reference

### Defaults

| Key | Default | Description |
|---|---|---|
| `recovery_cooldown_minutes` | 120 | Minutes before same issue×scenario can be acted on again |
| `max_recovery_attempts` | 3 | Max recovery actions per issue×scenario |
| `escalation_agent_id` | CTO agent UUID | Default escalation target |
| `alert_project_id` | Alert project UUID | Project for auto-created escalation issues |

### Agent scope map

Maps logical agent scopes to agent UUIDs. Update this when agents are
added/removed:

```json
{
  "exchange_agents": ["<uuid>", ...],
  "data_agents": ["<uuid>", ...],
  "signal_agents": ["<uuid>", ...],
  "risk_agents": ["<uuid>", ...],
  "monitoring_agents": ["<uuid>", ...]
}
```

### Recovery scenarios

Each scenario has:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique scenario identifier |
| `name` | string | Human-readable name |
| `enabled` | bool | Toggle on/off without deleting |
| `source_scope.agent_scopes` | [string] | Agent scope names from `agent_scope_map` |
| `source_scope.issue_keywords` | [string] | Case-insensitive keyword filters |
| `detection.status` | string | Issue status to match |
| `detection.min_age_hours` | int | Minimum issue age to match |
| `detection.max_age_hours` | int | Maximum issue age to match |
| `detection.check_live_runs` | bool | Whether to check live-run silence |
| `detection.run_silence_levels` | [string] | Silence levels that trigger |
| `detection.min_issues_for_batch_alert` | int | Minimum matches to fire |
| `recovery_actions` | [action] | Ordered recovery actions |

### Recovery actions

| `action` | Description | Requires |
|---|---|---|
| `add_comment` | Post diagnostic comment on issue | — |
| `invoke_heartbeat` | Trigger assigned agent's heartbeat | — |
| `resume_agent` | Resume a paused agent | Agent must have `status: paused` |
| `force_release` | Force-release issue checkout | `PAPERCLIP_BOARD_API_KEY` |
| `create_escalation` | Create escalation issue for CTO/domain owner | — |

### Adding a new recovery scenario

1. Add the scenario to `scripts/paperclip_recovery_actions.json`:
   ```json
   {
     "id": "my_new_scenario",
     "name": "My New Scenario",
     "enabled": true,
     "source_scope": {
       "agent_scopes": ["signal_agents"],
       "issue_keywords": ["new", "pattern"]
     },
     "detection": {
       "status": "in_progress",
       "min_age_hours": 4,
       "max_age_hours": 48,
       "check_live_runs": true,
       "run_silence_levels": ["suspicious", "critical"],
       "min_issues_for_batch_alert": 1
     },
     "recovery_actions": [
       {"order": 1, "action": "add_comment", "description": "Diagnostic check"},
       {"order": 2, "action": "invoke_heartbeat", "description": "Trigger heartbeat"},
       {"order": 3, "action": "create_escalation", "description": "Escalate to CTO",
        "escalation_agent_id": "<cto-uuid>",
        "escalation_title_prefix": "[RECOVERY] My scenario — "}
     ]
   }
   ```

2. Validate with dry-run:
   ```bash
   python scripts/paperclip_recovery_monitor.py run --dry-run --scenario my_new_scenario --json-summary
   ```

3. Commit and push:
   ```bash
   git add scripts/paperclip_recovery_actions.json
   git commit -m "feat(recovery): add my_new_scenario to recovery monitor"
   git push origin main
   ```

### Disabling a scenario

Set `"enabled": false` in the scenario config. No code changes needed.

```bash
python -c "
import json
cfg = json.load(open('scripts/paperclip_recovery_actions.json'))
for s in cfg['recovery_scenarios']:
    if s['id'] == 'exchange_api_timeout':
        s['enabled'] = False
json.dump(cfg, open('scripts/paperclip_recovery_actions.json','w'), indent=2)
"
git commit -am 'chore(recovery): disable exchange_api_timeout scenario'
```

## Troubleshooting

| Symptom | Likely Cause | Action |
|---|---|---|
| No matches on schedule | No stalled issues meeting criteria | Normal — check matches output in step summary |
| | Scenario age window too narrow | Adjust `min_age_hours` / `max_age_hours` |
| | API key expired or invalid | Verify `PAPERCLIP_API_*` secrets |
| Recovery actions not executing | Dry-run mode enabled | Check `dry_run` flag; GH Actions scheduled runs are matches-only |
| | Issue in cooldown | Check state file for recent attempt timestamps |
| | Batch threshold not met | Increase issue volume or lower `min_issues_for_batch_alert` |
| Force-release fails | `PAPERCLIP_BOARD_API_KEY` not set or expired | Verify the elevated key secret |
| | Issue not found (404) | Issue was already released or deleted |
| Heartbeat invoke has no effect | Agent is not running / systemd down | Check agent systemd status separately |
| | Agent is paused with stalled work | Use `agent_paused_stalled` scenario for `resume_agent` action |
| Escalation issues not created | Escalation agent UUID invalid | Verify agent UUIDs in config match current org chart |
| | Alert project UUID invalid | Verify `alert_project_id` in `defaults` |
| State file corruption | JSON malformed from concurrent writes | Delete `~/.paperclip/recovery_monitor_state.json` — auto-recreated |
| Log file too large | High-frequency runs with verbose matches | Log auto-rotates at 1 MB; reduce scenario breadth if flooding |

## Local Development

### Setup

```bash
cd /path/to/repo
python -m venv venv
source venv/bin/activate
pip install requests python-dotenv
```

### Run tests

```bash
# All recovery monitor tests (47 tests)
python -m pytest tests/test_scripts/test_paperclip_recovery_monitor.py -v

# Without coverage noise
python -m pytest tests/test_scripts/test_paperclip_recovery_monitor.py -p no:coverage -o "addopts=" -v
```

### Dry-run test

```bash
python scripts/paperclip_recovery_monitor.py run --dry-run --json-summary
```

### Check matches without acting

```bash
python scripts/paperclip_recovery_monitor.py matches
```

## Health Check and Stalled Workflow Reporting (BTCAAAAA-28995)

The Hourly Health Check verifies that the recovery monitor is functioning correctly
and provides visibility into any workflows currently undergoing recovery.

### Health Check Script

Located at `scripts/paperclip_recovery_health_check.py`. Validates:

| Check | What It Verifies |
|-------|------------------|
| Monitor Execution | Last run timestamp (should be < 45 min old) |
| Configuration | Valid scenarios, agent scopes, defaults |
| State Health | Recovery metrics, active escalations, recovery loops |
| Log Health | Error rate, fatal issues, recent exceptions |
| Systemd Timer | Timer is running (if systemd-based execution) |

#### Usage

```bash
# Run health check with JSON output
python scripts/paperclip_recovery_health_check.py --json-report

# Run health check and fail if unhealthy
python scripts/paperclip_recovery_health_check.py --alert-on-unhealthy
```

#### Health Status Values

- **healthy**: All checks pass, recovery monitor operational
- **degraded**: One or more warnings (non-fatal issues, elevated error rate, etc.)
- **unhealthy**: One or more check failures (monitor stalled, config invalid, etc.)

#### Key Metrics

- **Monitor execution age**: Time since last recovery monitor run (should be ~0–1 min for recent runs, < 45 min always)
- **Configuration validity**: All scenarios enabled, agent scopes defined, defaults set
- **State file health**: No corruption, recent recovery metrics tracked
- **Log error rate**: Elevated errors (> 5 in last 500 lines) trigger warning
- **Recovery loops**: Issues with repeated recovery attempts in < 15 min

### Stalled Workflow Reporter

Located at `scripts/paperclip_stalled_workflow_reporter.py`. Analyzes recovery state to report:

- Issues currently undergoing recovery by scenario
- Recovery attempt count and age
- Escalated issues requiring manual intervention
- Issues stuck in recovery loops (rapid repeated attempts)

#### Usage

```bash
# Generate human-readable report
python scripts/paperclip_stalled_workflow_reporter.py

# Generate JSON report
python scripts/paperclip_stalled_workflow_reporter.py --json-report

# Filter to specific scenario
python scripts/paperclip_stalled_workflow_reporter.py --scenario exchange_api_timeout
```

### GitHub Actions Hourly Workflow

Workflow: `.github/workflows/paperclip-recovery-health-check.yml`

**Schedule:** Every hour (`:00` minute mark)

**Steps:**
1. Run health check with JSON output
2. Generate stalled workflow report
3. Write combined summary to GitHub step summary
4. Upload artifacts: health report, stalled workflows JSON, logs (30-day retention)

**Manual Trigger:**
```bash
gh workflow run paperclip-recovery-health-check.yml \
  -f alert_on_unhealthy=true
```

### Interpreting Health Check Results

#### Healthy Status

```json
{
  "overall_status": "healthy",
  "checks": {
    "monitor_execution": {"status": "pass", "details": {"age_minutes": 1.5}},
    "configuration": {"status": "pass", "details": {"scenarios_enabled": 5}},
    "state_health": {"status": "pass", "details": {"total_issues_recovered": 0}},
    "log_health": {"status": "pass", "details": {"recent_errors": 0}},
    "systemd_timer": {"status": "pass", "details": {"systemd_timer_running": true}}
  },
  "alerts": [],
  "warnings": []
}
```

**Action:** None — system is operating normally.

#### Degraded Status (Warnings)

Example: Monitor has not run in 35–45 minutes.

```json
{
  "overall_status": "degraded",
  "warnings": [
    "monitor_execution: Monitor last ran 38 minutes ago (expected ~30 min)"
  ]
}
```

**Action:** Monitor might have missed a cycle. Check GitHub Actions workflow runs:
```bash
gh run list --workflow=paperclip-recovery-monitor.yml --limit=5
gh run view <run-id> --log
```

#### Unhealthy Status (Alerts)

Example: Recovery state file missing or corrupted.

```json
{
  "overall_status": "unhealthy",
  "alerts": [
    "monitor_execution: Recovery state file not found — monitor may have never run",
    "log_health: Recent fatal errors (1) or high error rate (12 errors, 8 exceptions)"
  ]
}
```

**Action:**
1. **State file missing/corrupt:** Run recovery monitor manually:
   ```bash
   python scripts/paperclip_recovery_monitor.py run --dry-run --json-summary
   ```
2. **API errors in logs:** Check environment variables (`PAPERCLIP_API_KEY`, `PAPERCLIP_API_URL`)
3. **Configuration error:** Validate config file:
   ```bash
   python -m json.tool scripts/paperclip_recovery_actions.json | head -20
   ```

### Stalled Workflow Report Examples

#### No Stalled Workflows

```markdown
# PaperClip Stalled Workflow Report

**Generated:** 2026-05-19T06:16 UTC

✅ **No stalled workflows currently in recovery.**
```

#### With Active Recoveries

```markdown
# PaperClip Stalled Workflow Report

**Generated:** 2026-05-19T06:16 UTC

## Summary

- **Scenarios tracking issues:** 2
- **Total issues in recovery:** 3
- **Issues escalated:** 1
- **Issues stuck in loop:** 0

## By Scenario

### Exchange API Timeout Recovery (2 issue(s))

- **BTCA1234**: in_recovery, 2 attempt(s), age 4.5h
- **BTCA5678**: escalated, 3 attempt(s), age 8.2h ⚠️ Escalation required

### Position Mismatch Detection (1 issue(s))

- **BTCA9999**: in_recovery, 1 attempt(s), age 1.3h
```

### Alerting and Thresholds

The health check is designed for integration with monitoring systems. Suggested alerting:

| Condition | Severity | Action |
|-----------|----------|--------|
| `overall_status != "healthy"` for > 2 check runs | Warning | Review logs, check API key |
| `issues_stuck_in_loop > 0` | Warning | Check configuration for over-aggressive recovery |
| `log_health.recent_errors > 10` in recent run | Error | Investigate API/config issues |
| Monitor age > 45 minutes | Error | Check GitHub Actions; review systemd logs |

### Local Testing

```bash
# Full health check
python scripts/paperclip_recovery_health_check.py --json-report | python -m json.tool

# Monitor execution check only (no API calls required)
python scripts/paperclip_recovery_health_check.py

# Stalled workflow report (no API calls)
python scripts/paperclip_stalled_workflow_reporter.py
```

## Related Documents

- `scripts/paperclip_recovery_monitor.py` — Monitor implementation
- `scripts/paperclip_recovery_health_check.py` — Hourly health check script (BTCAAAAA-28995)
- `scripts/paperclip_stalled_workflow_reporter.py` — Stalled workflow analyzer (BTCAAAAA-28995)
- `scripts/paperclip_recovery_actions.json` — Scenario and agent config
- `.github/workflows/paperclip-recovery-monitor.yml` — CI/CD workflow for recovery actions
- `.github/workflows/paperclip-recovery-health-check.yml` — Hourly health check workflow (BTCAAAAA-28995)
- `tests/test_scripts/test_paperclip_recovery_monitor.py` — Test suite (47 tests)
- `deploy/systemd/paperclip-recovery-monitor.service` — Systemd service unit
- `deploy/systemd/paperclip-recovery-monitor.timer` — Systemd timer unit
- `deploy/systemd/install-recovery-monitor.sh` — Systemd install script
- `src/touch_index/paperclip_client.py` — Underlying API client (`_base`, `_company`)
- `docs/runbook-incident-response.md` — Incident severity classification and response flow

## P5.1 Design Notes (BTCAAAAA-26508)

The recovery monitor is part of the P5.1 production hardening initiative.
Key design decisions:

- **Source-scoped recovery**: Recovery actions are scoped to the agent domain
  that is most likely affected, avoiding cross-domain noise.
- **Cooldown-first**: Every recovery action is gated by a per-issue×scenario
  cooldown (120 min default) to prevent over-recovery from tight polling loops.
- **Escalation as last resort**: Escalation issues are only created after all
  preceding actions in the chain have been attempted and the cooldown has reset
  at each step.
- **Dual scheduler**: GitHub Actions (every 30 min, matches-only on schedule)
  and systemd timer (every 30 min, offset by 15 min) provide overlapping
  coverage without double-execution of recovery actions.
