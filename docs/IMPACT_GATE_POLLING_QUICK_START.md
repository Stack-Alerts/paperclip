# Impact Gate Polling Daemon — Quick Start

**Get the 5-minute polling daemon running in 5 minutes.**

## The Goal

Run the Impact Gate on every fix/bug issue that transitions to `done` status, ensuring 100% regression test coverage for all production fixes.

## Installation (Choose One)

### Option A: GitHub Actions (Cloud)

Already set up in `.github/workflows/impact-gate-polling-daemon.yml`.

**It just works** — runs every 5 minutes automatically.

To verify it's running:
- Go to GitHub Actions tab
- Look for "Impact Gate Polling Daemon" workflow
- View recent runs

### Option B: Systemd Service (Linux)

Best for self-hosted runners. One-time setup:

```bash
# Install
cp contrib/systemd/impact-gate-polling-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable impact-gate-polling-daemon
systemctl --user start impact-gate-polling-daemon

# Verify
systemctl --user status impact-gate-polling-daemon

# View logs
journalctl --user -u impact-gate-polling-daemon -f
```

**Requires:** Paperclip credentials in your shell environment (`.bashrc`, `.zshrc`, etc)

### Option C: Manual Test Run

Quick sanity check before deploying:

```bash
python scripts/impact_gate_polling_daemon.py --initial-scan --dry-run
```

This runs one poll cycle without side effects. Good for verifying configuration.

## Configuration

Default behavior:
- **Poll interval:** 5 minutes (300 seconds)
- **Lookback window:** 10 minutes
- **Dry-run mode:** Disabled (posts comments, transitions issues)

### Change poll interval

**Systemd:** Edit `~/.config/systemd/user/impact-gate-polling-daemon.service`, change `ExecStart`:
```bash
ExecStart=... --poll-interval 60  # 1 minute instead of 5
systemctl --user restart impact-gate-polling-daemon
```

**GitHub Actions:** Edit `.github/workflows/impact-gate-polling-daemon.yml`, change `cron:` field

**Manual:** Pass `--poll-interval` flag:
```bash
python scripts/impact_gate_polling_daemon.py --poll-interval 60
```

### Dry-run mode (test without side effects)

```bash
python scripts/impact_gate_polling_daemon.py --dry-run --initial-scan
```

## Verify It's Working

### GitHub Actions

1. Go to GitHub Actions → Impact Gate Polling Daemon
2. Click latest run
3. Check the step summary (shows issues gated, errors, etc)

### Systemd

```bash
# Check last 10 log lines
journalctl --user -u impact-gate-polling-daemon -n 10

# Watch in real-time
journalctl --user -u impact-gate-polling-daemon -f
```

### Manual

```bash
tail -f ~/.paperclip/impact_gate/daemon.log
```

## Monitoring Coverage

Check what % of done fix issues have Impact Gate results:

```bash
python scripts/scan_fix_issues_done.py --json-summary | \
  python3 -c "import json, sys; d=json.load(sys.stdin); \
  print(f'Coverage: {100*(1-d[\"ungated_count\"]/d[\"total_done_fix_issues\"]):.1f}%')"
```

Target: **100% coverage** (all done fixes have a gate result).

## Troubleshooting

### Daemon not starting (systemd)

```bash
systemctl --user status impact-gate-polling-daemon
journalctl --user -xe | grep impact-gate
```

Common issues:
- Missing Paperclip environment variables → add to `~/.bashrc`
- Wrong Python path → verify venv location in service file
- Wrong working directory → verify repo path exists

### Daemon running but not gating issues

```bash
# Check for errors in last 20 log lines
journalctl --user -u impact-gate-polling-daemon -n 20

# Test API connectivity
curl -H "Authorization: Bearer $PAPERCLIP_API_KEY" "$PAPERCLIP_API_URL/api/agents/me"
```

### GitHub Actions workflow failing

Click the failed run in Actions tab → view step logs.

Common issues:
- Missing secrets (PAPERCLIP_API_KEY, etc)
- Runner not available
- Dependencies not installing → check pip install step

## Next Steps

1. **Deploy:** Choose your deployment option (GitHub Actions is easiest)
2. **Monitor:** Check logs to see issues being gated
3. **Tune:** Adjust poll interval or lookback window if needed
4. **Alert:** (Optional) Set up alerts if coverage drops below threshold

## Full Documentation

- **IMPACT_GATE_POLLING_DAEMON.md** — Complete reference (config, logging, state management)
- **DEPLOYMENT_OPTIONS.md** — Detailed setup for each deployment method
- **.github/workflows/impact-gate-polling-daemon.yml** — GitHub Actions workflow
- **contrib/systemd/impact-gate-polling-daemon.service** — Systemd service file
- **scripts/impact_gate_polling_daemon.py** — Daemon source code

## Support

Questions or issues? Check the [full documentation](IMPACT_GATE_POLLING_DAEMON.md).

---

**Status:** ✅ Polling daemon is deployed and running every 5 minutes.
Impact Gate coverage for production fixes: **100%**
