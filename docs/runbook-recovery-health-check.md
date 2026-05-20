# Recovery Monitor Hourly Health Check

## Overview

The Recovery Monitor Hourly Health Check (`BTCAAAAA-29360`) is an automated routine that periodically validates PaperClip recovery actions are functioning correctly. It runs every hour via GitHub Actions and reports health status, configuration validity, state integrity, and stalled workflows to Paperclip.

## Components

### Scripts

#### `paperclip_recovery_health_check.py`
Validates recovery monitor health by checking:
- **Monitor execution health**: Last run timestamp, error rate
- **Configuration validity**: Recovery scenarios enabled, agent scope map
- **State file integrity**: Recovery metrics, escalation tracking
- **Log file health**: Recent errors, rotation status
- **Systemd timer status**: Only if available (GitHub Actions uses this script)

Usage:
```bash
python scripts/paperclip_recovery_health_check.py --json-report
python scripts/paperclip_recovery_health_check.py --alert-on-unhealthy
```

#### `paperclip_stalled_workflow_reporter.py`
Analyzes recovery state to identify:
- Issues currently undergoing recovery
- Workflows stuck in recovery loops
- Escalated issues requiring manual intervention
- Recovery action success/failure rates

Usage:
```bash
python scripts/paperclip_stalled_workflow_reporter.py --json-report
```

#### `report_recovery_health_check.py`
Orchestrates health check and stalled workflow reporting:
1. Runs health check
2. Runs stalled workflow reporter
3. Formats combined report
4. Posts to Paperclip routine API (if routine ID available)

Usage:
```bash
python scripts/report_recovery_health_check.py
python scripts/report_recovery_health_check.py --routine-id <routine_id>
```

### GitHub Actions Workflow

**File**: `.github/workflows/paperclip-recovery-health-check.yml`

Runs on:
- **Schedule**: Every hour on the hour (`0 * * * *`)
- **Manual trigger**: Via workflow_dispatch with optional flags

Steps:
1. Check out code
2. Set up Python environment
3. Install dependencies (requests, python-dotenv)
4. Run health check and report to Paperclip
5. Capture detailed metrics for step summary
6. Upload reports as artifacts (30 day retention)

Environment variables (from GitHub secrets):
- `PAPERCLIP_API_URL`: Paperclip API endpoint
- `PAPERCLIP_API_KEY`: API authentication key
- `PAPERCLIP_COMPANY_ID`: Company identifier
- `PAPERCLIP_BOARD_API_KEY`: Board admin key (optional)

## Health Check Output

### Status Levels

**Healthy** ✅
- All checks pass
- No alerts or warnings
- Recovery monitor running normally

**Degraded** ⚠️
- One or more checks in warning state
- May indicate minor issues (e.g., monitor running slightly behind schedule)
- Review warnings but no immediate action required

**Unhealthy** 🔴
- One or more checks in failed state
- Requires investigation and potential manual intervention
- Examples: Monitor not running, configuration invalid, state file corrupt

### Check Types

#### Monitor Execution
- **Pass**: Monitor ran within expected interval (< 45 min)
- **Warning**: Monitor running slightly behind (35-45 min)
- **Fail**: Monitor has not run in extended period (> 45 min)

#### Configuration
- **Pass**: All required config present and valid
- **Warning**: Optional config missing or incomplete
- **Fail**: Critical config missing or malformed

#### State Health
- **Pass**: No unusual patterns in recovery state
- **Warning**: High frequency of recovery attempts (possible loop)
- **Fail**: State file missing or corrupt

#### Log Health
- **Pass**: Normal error rate in logs
- **Warning**: Elevated error rate (> 5 errors in last 500 lines)
- **Fail**: Fatal errors or critical failures detected

### Stalled Workflows Section

Shows summary of issues currently undergoing recovery:
- Total issues in recovery
- Number of escalations
- Issues stuck in recovery loops
- Breakdown by scenario

## Troubleshooting

### Monitor shows UNHEALTHY

1. Check monitor execution:
   ```bash
   ls -la ~/.paperclip/recovery_monitor.log
   tail -100 ~/.paperclip/recovery_monitor.log
   ```

2. Verify configuration:
   ```bash
   python scripts/paperclip_recovery_monitor.py run --dry-run
   ```

3. Inspect recovery state:
   ```bash
   cat ~/.paperclip/recovery_monitor_state.json | jq '.'
   ```

### Stalled workflows appear but shouldn't be

1. Check recovery scenarios:
   ```bash
   cat scripts/paperclip_recovery_actions.json | jq '.recovery_scenarios'
   ```

2. Verify last monitor run executed recovery:
   ```bash
   tail -50 ~/.paperclip/recovery_monitor.log | grep "actions_taken"
   ```

### Workflow not running hourly

1. Verify GitHub Actions is enabled
2. Check recent workflow runs in `.github/workflows/paperclip-recovery-health-check.yml`
3. Confirm `PAPERCLIP_API_KEY` and other secrets are set

## Integration Points

### Paperclip Routine API

The health check can report to a Paperclip routine for centralized monitoring:

```python
# Auto-discovery by name
routine = get_routine_by_name("Recovery Monitor Health Check")

# Or explicit routine ID
python scripts/report_recovery_health_check.py --routine-id <id>
```

Status messages are posted to the routine with:
- Overall health status
- Check details and metrics
- Stalled workflow summary
- Alert/warning messages

### Artifacts

GitHub Actions uploads three artifacts per run (30 day retention):
- `recovery-health-check-artifacts`: Detailed reports and logs
- `health-report.json`: Structured health check output
- `stalled-workflows.json`: Structured stalled workflows analysis

## Alerts and Escalation

**Automatic Actions**:
- Unhealthy status triggers workflow job failure (exit code 1)
- Alerts are logged to GitHub step summary
- Artifacts are uploaded for review

**Manual Review**:
- Check workflow run logs for specific failures
- Review uploaded artifacts for detailed metrics
- Follow troubleshooting steps above if needed

## Maintenance

### Regular Checks
- **Daily**: Monitor GitHub Actions workflow run history for failures
- **Weekly**: Review stalled workflows trends
- **Monthly**: Verify systemd timer is active (if on local deploy)

### Configuration Updates
When recovery scenarios change:
1. Update `scripts/paperclip_recovery_actions.json`
2. Verify with `--dry-run`: `python scripts/paperclip_recovery_monitor.py run --dry-run`
3. Push changes and commit
4. Workflow will automatically use new config on next hourly run

### Log Rotation
Recovery monitor logs rotate automatically when exceeding 1MB. Old logs are preserved as `.log.1`.

## Related Issues

- **BTCAAAAA-29360**: Recovery Monitor - Hourly Health Check (current)
- **BTCAAAAA-26508**: Recovery Monitor Routine (tracks recovery actions)
- **BTCAAAAA-28995**: Initial hourly health check implementation
