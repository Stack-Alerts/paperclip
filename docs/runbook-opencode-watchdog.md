# Runbook: OpenCode Watchdog

**Last updated:** 2026-05-12
**Owner:** AutomationEngineer

---

## 1. Overview

The OpenCode Watchdog monitors and kills hanging opencode processes that have been silent beyond the configured threshold. This prevents resource exhaustion from orphaned agent sessions.

**Workflow:** `opencode-watchdog.yml`
**Script:** `scripts/opencode_watchdog.py`
**System files:** `scripts/opencode-watchdog.service`, `scripts/opencode-watchdog.timer`, `scripts/README-opencode-watchdog.md`

---

## 2. Cadence

| Trigger | Cadence | Description |
|---|---|---|
| Scheduled | Every 15 minutes | Standard monitoring cycle |
| Manual | `workflow_dispatch` | On-demand with `dry_run` and `threshold` inputs |

---

## 3. Manual Trigger

```bash
# Dry run (log only, do not kill)
gh workflow run opencode-watchdog.yml -f dry_run=true

# Force kill with custom threshold (default: 1800s = 30min)
gh workflow run opencode-watchdog.yml -f dry_run=false -f threshold=3600
```

---

## 4. Logs

Watchdog logs are uploaded as artifacts on every run:

- **Retention:** 7 days
- **Location:** `~/.paperclip/opencode_watchdog*.log`
- **Access:** GitHub Actions → Workflow run → Artifacts → `watchdog-logs`

---

## 5. Systemd Integration

The watchdog can also run as a systemd service on the local machine:

### Service File

`scripts/opencode-watchdog.service` — runs `scripts/opencode_watchdog.py` as a daemon.

### Timer

`scripts/opencode-watchdog.timer` — triggers the service on a schedule.

### Setup

```bash
# See setup script for details
bash scripts/setup_opencode_watchdog.sh
```

See `scripts/README-opencode-watchdog.md` for full setup instructions.

---

## 6. Thresholds

| Parameter | Default | Description |
|---|---|---|
| `threshold` | 1800 seconds (30 min) | Process silence threshold before kill |
| `dry_run` | `true` (manual) / `false` (scheduled) | Log-only mode |

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Watchdog not killing processes | `dry_run=true` | Check workflow input, re-run with `dry_run=false` |
| False positives (processes killed prematurely) | Threshold too low | Increase threshold to 3600s or higher |
| Logs not available | Artifact retention expired (7 days) | Check earlier runs or local logs |
| Systemd service not running | Timer not enabled | Run `sudo systemctl enable --now opencode-watchdog.timer` |

---

## 8. Related Documents

- [runbook-ci-cd.md](runbook-ci-cd.md) — workflow scheduling reference
- [scripts/README-opencode-watchdog.md](../../scripts/README-opencode-watchdog.md) — systemd setup
- [scripts/opencode_watchdog.py](../../scripts/opencode_watchdog.py)
