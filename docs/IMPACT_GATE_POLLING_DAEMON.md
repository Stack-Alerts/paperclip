# Impact Gate Polling Daemon

**5-minute polling daemon that ensures 100% regression test coverage for all fixes moving to production.**

The Impact Gate polling daemon continuously scans for fix/bug issues that have transitioned to `done` status and runs the full Impact Gate verification (FR acceptance + regression test suites) on any ungated issues.

## What It Does

1. **Polls every 5 minutes** for fix/bug issues in `done` status
2. **Checks Impact Gate coverage** — identifies which issues have gate results
3. **Runs full Impact Gate** on ungated issues:
   - Reads touched files from issue description
   - Queries Blast Radius Touch Index for FR and regression impacts
   - Executes FR acceptance test suite
   - Executes bug regression test suite
   - Posts detailed result comments
   - On PASS: issue stays in `done`, moves to production
   - On FAIL: reverts issue to `in_progress`, creates blocking sub-issues
4. **Ensures 100% coverage**: Every fix moving to production must have a gate result

## Architecture

The daemon uses the existing Impact Gate infrastructure:

- **Gate runner**: `scripts/impact_gate_worker.py` — runs FR + regression tests
- **Gate scorer**: `impact_gate/worker.py::process_issue()` — orchestrates full gate flow
- **Touch Index**: `touch_index/` — maps file changes to FR and regression impacts
- **Blast Radius**: `blast_radius/` — computes impact sets

The daemon wraps this logic in a long-running poll loop with:
- Persistent state management (prevent re-processing issues)
- Log rotation (prevents disk filling)
- Error recovery (restarts on transient failures)
- Optional dry-run mode (test without side effects)

## Installation

### Option 1: systemd Service (Recommended)

Copy the systemd service file and enable it:

```bash
cp contrib/systemd/impact-gate-polling-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable impact-gate-polling-daemon
systemctl --user start impact-gate-polling-daemon
```

Requires:
- Systemd user session (standard on modern Linux)
- `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `PAPERCLIP_BOARD_API_KEY`, `PAPERCLIP_COMPANY_ID` exported in user environment
- Python venv at `~/.venv` (or adjust `ExecStart` path in service file)
- Working directory: `~/projects/BTC-Trade-Engine-PaperClip`

### Option 2: Manual Background Process

```bash
nohup python scripts/impact_gate_polling_daemon.py \
  --poll-interval 300 \
  --lookback-minutes 10 \
  > ~/.paperclip/impact_gate/daemon.log 2>&1 &
```

**Important:** Set Paperclip API credentials before running:
```bash
export PAPERCLIP_API_URL=<url>
export PAPERCLIP_API_KEY=<key>
export PAPERCLIP_BOARD_API_KEY=<key>
export PAPERCLIP_COMPANY_ID=<id>
```

### Option 3: Docker/Container

TODO: Add Dockerfile if deploying to containerized infrastructure.

## Usage

### Start the daemon (systemd)

```bash
systemctl --user start impact-gate-polling-daemon
systemctl --user status impact-gate-polling-daemon
```

### View logs (systemd)

```bash
journalctl --user -u impact-gate-polling-daemon -f
```

Or check the log file directly:

```bash
tail -f ~/.paperclip/impact_gate/daemon.log
```

### Run a single poll cycle (testing)

```bash
python scripts/impact_gate_polling_daemon.py --initial-scan
python scripts/impact_gate_polling_daemon.py --initial-scan --dry-run  # No side effects
```

### Dry-run mode

Test without posting comments or transitioning issues:

```bash
python scripts/impact_gate_polling_daemon.py --dry-run
```

### Custom poll interval

Default is 300 seconds (5 minutes). To change:

```bash
python scripts/impact_gate_polling_daemon.py --poll-interval 60  # 1 minute
```

Or set environment variable:

```bash
export IMPACT_GATE_POLL_INTERVAL=60
python scripts/impact_gate_polling_daemon.py
```

### Custom lookback window

Default lookback is 10 minutes. To scan issues done in last 30 minutes:

```bash
python scripts/impact_gate_polling_daemon.py --lookback-minutes 30
```

## State and Logs

### Daemon State

Location: `~/.paperclip/impact_gate/daemon_state.json`

Tracks:
- `started_at`: Daemon start time
- `last_poll_utc`: Last poll timestamp
- `total_polls`: Total poll cycles executed
- `total_gated`: Total issues gated (all statuses)
- `total_errors`: Total gate errors encountered

Example:

```json
{
  "started_at": "2026-05-16T14:30:00Z",
  "last_poll_utc": "2026-05-16T14:35:00Z",
  "total_polls": 42,
  "total_gated": 12,
  "total_errors": 2,
  "processed_issues": []
}
```

### Daemon Logs

Location: `~/.paperclip/impact_gate/daemon.log`

Rotates automatically when exceeding 10 MB. Previous log: `daemon.log.1`

Log levels:
- `INFO`: Poll cycles, gate results, errors
- `DEBUG`: Issue dedup, skips (enable with `--verbose` if added)
- `WARNING`: API failures, missing data
- `ERROR`: Gate failures, processing errors

Example log:

```
2026-05-16 14:35:00 [INFO] Starting poll cycle (lookback=10m, dry_run=False)
2026-05-16 14:35:00 [INFO] Fetched 2 recently done fix/bug issue(s)
2026-05-16 14:35:00 [INFO] [gate] Running Impact Gate on BTCAAAAA-12345
2026-05-16 14:35:05 [INFO] [gate] Impact Gate for BTCAAAAA-12345 completed: PASS
2026-05-16 14:35:05 [INFO] [skip] BTCAAAAA-12346 already gated with status PASS
2026-05-16 14:35:05 [INFO] Poll cycle complete — gated=1 skipped=1 errors=0
```

## Troubleshooting

### Daemon not starting

1. Check systemd service status:
   ```bash
   systemctl --user status impact-gate-polling-daemon
   journalctl --user -xe | grep impact-gate
   ```

2. Verify environment variables:
   ```bash
   echo $PAPERCLIP_API_URL
   echo $PAPERCLIP_API_KEY
   ```

3. Check that working directory and venv exist:
   ```bash
   ls -d ~/projects/BTC-Trade-Engine-PaperClip
   ls -d ~/.venv
   ```

### High error rate in logs

1. Check Paperclip API connectivity:
   ```bash
   curl -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
     "$PAPERCLIP_API_URL/api/agents/me"
   ```

2. Check Blast Radius Touch Index availability:
   ```bash
   python scripts/impact_gate_polling_daemon.py --initial-scan --dry-run
   ```

3. Review recent gate results:
   ```bash
   tail -20 ~/.paperclip/impact_gate/daemon.log
   ```

### Disk space filling up

Log rotation is automatic at 10 MB. To manually rotate:

```bash
mv ~/.paperclip/impact_gate/daemon.log ~/.paperclip/impact_gate/daemon.log.1
# Daemon will create a new log on next cycle
```

### Daemon hanging or not polling

1. Check if process is still running:
   ```bash
   systemctl --user status impact-gate-polling-daemon
   ```

2. Restart the daemon:
   ```bash
   systemctl --user restart impact-gate-polling-daemon
   ```

3. Check for stuck processes:
   ```bash
   ps aux | grep impact_gate_polling_daemon
   ```

## Integration with GitHub Actions

The daemon complements (not replaces) the GitHub Actions workflow:

- **Workflow**: `impact-gate-scan-done.yml` — runs every 5 min, posts verification comments
- **Daemon**: Impact Gate polling daemon — runs every 5 min, runs FULL gate tests

Both serve the same goal (100% coverage) but via different paths:
- **Workflow**: Fast feedback loop for already-done issues (posts diagnostic comments)
- **Daemon**: Continuous regression verification (full test execution)

Over time, the daemon should handle all gating, and the workflow can focus on monitoring coverage metrics.

## Monitoring

Check coverage on demand:

```bash
python scripts/scan_fix_issues_done.py --json-summary | \
  python3 -c "import json, sys; d=json.load(sys.stdin); print(f'Coverage: {100*(1-d[\"ungated_count\"]/d[\"total_done_fix_issues\"]):.1f}%')"
```

## API Keys and Security

The daemon requires Paperclip API credentials:

- `PAPERCLIP_API_URL`: Paperclip base URL
- `PAPERCLIP_API_KEY`: Agent API key (short-lived JWT)
- `PAPERCLIP_BOARD_API_KEY`: Board API key (for issue transitions)
- `PAPERCLIP_COMPANY_ID`: Company ID

**Do not hardcode credentials.** Use:
- Systemd service environment (recommended)
- `.env` file in repo root (loaded automatically if not in CI)
- Shell environment variables

## Performance

Expected performance per poll cycle:

- **Scan time**: 2-5 seconds (fetch done issues)
- **Per-issue gate time**: 30-120 seconds (run tests)
- **Total cycle (0 ungated)**: ~5 seconds
- **Total cycle (1 ungated)**: ~60 seconds
- **Total cycle (5 ungated)**: ~5-10 minutes

With `--lookback-minutes 10` and `--poll-interval 300`, issues are gated within 5-10 minutes of transitioning to `done`.

## Future Improvements

- [ ] Metrics export (Prometheus, DataDog)
- [ ] Slack/PagerDuty alerts on gate failures
- [ ] Retry logic for transient CI failures
- [ ] Parallel gate execution for multiple issues
- [ ] Web UI for daemon status and history
- [ ] Rollback automation on repeated failures
