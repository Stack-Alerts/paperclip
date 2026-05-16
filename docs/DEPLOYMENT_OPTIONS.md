# Impact Gate Polling Daemon — Deployment Options

**Quick choice guide for deploying the 5-minute polling daemon.**

## 1. GitHub Actions (Recommended for CI/CD)

**Best for:** Cloud-based continuous verification, integrated with GitHub workflow ecosystem.

**Pros:**
- No infrastructure to manage (GitHub-hosted or self-hosted runners)
- Integrated with GitHub Actions dashboard
- Automatic retries, logging, artifacts
- Easy to manually trigger for testing

**Cons:**
- Slight latency (~10 min/cycle vs immediate daemon)
- Each run incurs CI time

**Setup:**

The workflow is already defined in `.github/workflows/impact-gate-polling-daemon.yml`.

It runs:
- **Every 5 minutes** automatically (via cron)
- Can be manually triggered: Actions tab → Impact Gate Polling Daemon → Run workflow

**Status:**

```bash
# View recent runs
gh run list --workflow impact-gate-polling-daemon.yml

# View logs for a specific run
gh run view <run-id> --log
```

**Customize:**

Edit `.github/workflows/impact-gate-polling-daemon.yml` to change:
- `cron: '*/5 * * * *'` — poll interval
- `runs-on: self-hosted` — runner selection
- `FLAGS` in the run step

---

## 2. Systemd Service (Recommended for Self-Hosted Runners)

**Best for:** Long-running daemons on Linux servers, integrated with system supervision.

**Pros:**
- True daemon (runs in background indefinitely)
- Automatic restarts on failure
- System-integrated logging (journalctl)
- Lower latency (immediate polling, no CI overhead)
- Resource-efficient (always running)

**Cons:**
- Requires systemd (standard on modern Linux)
- More complex troubleshooting than GitHub Actions

**Setup:**

```bash
# Install service file
cp contrib/systemd/impact-gate-polling-daemon.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable and start
systemctl --user enable impact-gate-polling-daemon
systemctl --user start impact-gate-polling-daemon

# Verify running
systemctl --user status impact-gate-polling-daemon
```

**Important:** Ensure Paperclip credentials are in your user environment:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PAPERCLIP_API_URL=...
export PAPERCLIP_API_KEY=...
export PAPERCLIP_BOARD_API_KEY=...
export PAPERCLIP_COMPANY_ID=...
```

**Logs:**

```bash
# View real-time logs
journalctl --user -u impact-gate-polling-daemon -f

# View recent logs
journalctl --user -u impact-gate-polling-daemon -n 50

# Or check the log file
tail -f ~/.paperclip/impact_gate/daemon.log
```

**Troubleshooting:**

```bash
# Check service status
systemctl --user status impact-gate-polling-daemon

# Restart daemon
systemctl --user restart impact-gate-polling-daemon

# Stop daemon
systemctl --user stop impact-gate-polling-daemon

# View errors
journalctl --user -u impact-gate-polling-daemon -n 100 --no-pager
```

---

## 3. Docker Container

**Best for:** Containerized infrastructure, cloud deployments (ECS, Kubernetes, etc).

**Pros:**
- Environment isolation
- Easy scaling/orchestration
- Portable across infrastructure
- Version-pinned dependencies

**Cons:**
- Requires Docker infrastructure
- More setup initially

**Dockerfile:**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-xkb1 xvfb libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir requests python-dotenv SQLAlchemy psycopg2-binary

# Copy codebase
COPY . .

# Set environment for headless testing
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONPATH=src
ENV PYTHONUNBUFFERED=1

# Run daemon
CMD ["python", "scripts/impact_gate_polling_daemon.py"]
```

**Build and run:**

```bash
docker build -t impact-gate-daemon:latest .

docker run -d \
  --name impact-gate-daemon \
  -e PAPERCLIP_API_URL=$PAPERCLIP_API_URL \
  -e PAPERCLIP_API_KEY=$PAPERCLIP_API_KEY \
  -e PAPERCLIP_BOARD_API_KEY=$PAPERCLIP_BOARD_API_KEY \
  -e PAPERCLIP_COMPANY_ID=$PAPERCLIP_COMPANY_ID \
  --restart always \
  impact-gate-daemon:latest
```

**View logs:**

```bash
docker logs -f impact-gate-daemon
```

---

## 4. Manual Background Process

**Best for:** Quick testing, development, ad-hoc runs.

**Pros:**
- Simplest setup (no systemd, no Docker)
- Easy to start/stop
- Good for testing

**Cons:**
- Not production-ready (no auto-restart)
- Manual lifecycle management
- Logging to file only

**Run:**

```bash
# Terminal 1: Start daemon
export PAPERCLIP_API_URL=...
export PAPERCLIP_API_KEY=...
export PAPERCLIP_BOARD_API_KEY=...
export PAPERCLIP_COMPANY_ID=...

python scripts/impact_gate_polling_daemon.py
```

Or in background:

```bash
nohup python scripts/impact_gate_polling_daemon.py \
  > ~/.paperclip/impact_gate/daemon.log 2>&1 &

# Verify running
ps aux | grep impact_gate_polling_daemon

# View logs
tail -f ~/.paperclip/impact_gate/daemon.log
```

---

## 5. Kubernetes / Helm

**Best for:** Cloud-native, scalable deployments.

Not yet implemented, but can follow the Docker Compose pattern.

---

## Comparison Matrix

| Aspect | GitHub Actions | Systemd | Docker | Manual |
|--------|---|---|---|---|
| **Setup complexity** | Easy | Medium | Medium | Very easy |
| **Operational overhead** | Low | Low | Medium | High |
| **Latency** | 10 min/cycle | Immediate | Immediate | Immediate |
| **Auto-restart** | Yes | Yes | Yes (Docker restart) | No |
| **Logging integration** | GitHub Artifacts | journalctl | docker logs | File only |
| **Resource cost** | CI time | Always running | Always running | Always running |
| **Best for** | Cloud/CI | Self-hosted | Cloud native | Dev/testing |
| **Scalability** | N/A | Single machine | Multi-container | N/A |

---

## Recommendation

### For Production (choose one):

1. **Cloud deployments (AWS, GCP, Azure, etc):**
   - Use **GitHub Actions** (simplest) or **Docker** on managed container services

2. **Self-hosted Linux servers:**
   - Use **Systemd service** (native integration, zero overhead)

3. **Kubernetes:**
   - Use **Docker container** in a Kubernetes CronJob (runs every 5 min)

### For Development / Testing:

- Use **GitHub Actions `workflow_dispatch`** for quick manual testing
- Use **--initial-scan flag** for one-shot verification

---

## Monitoring the Daemon

All deployments should track:

1. **Coverage percentage** (manual check):
   ```bash
   python scripts/scan_fix_issues_done.py --json-summary | \
     python3 -c "import json, sys; d=json.load(sys.stdin); print(f'Coverage: {100*(1-d[\"ungated_count\"]/d[\"total_done_fix_issues\"]):.1f}%')"
   ```

2. **Daemon state** (systemd):
   ```bash
   cat ~/.paperclip/impact_gate/daemon_state.json
   ```

3. **Recent logs** (systemd):
   ```bash
   journalctl --user -u impact-gate-polling-daemon -n 20 --no-pager
   ```

4. **Recent runs** (GitHub Actions):
   - View in Actions tab
   - Artifacts include poll output JSON

---

## Transitioning Between Deployments

### From GitHub Actions → Systemd

1. Verify systemd service is running and healthy (1+ cycles completed)
2. Keep GitHub Actions workflow as backup monitoring
3. Disable scheduled run in workflow if duplicate polling causes issues
4. Monitor logs for 24-48 hours before fully removing GitHub Actions trigger

### From Manual → Systemd

1. Start systemd service
2. Verify in logs: "Starting Impact Gate polling daemon"
3. Let it run for 2-3 cycles to validate
4. Remove manual background process

### From Docker → Systemd (or vice versa)

1. Start new deployment
2. Verify it's gating issues correctly
3. Stop old deployment
4. Monitor for regressions

---

## Troubleshooting Deployment Issues

### Daemon not running after restart

- **Systemd:** `systemctl --user status impact-gate-polling-daemon` → check ExecStart path
- **Docker:** `docker logs impact-gate-daemon` → check environment variables
- **GitHub Actions:** Check Actions tab for workflow errors

### High error rate

1. Verify Paperclip API connectivity:
   ```bash
   curl -H "Authorization: Bearer $PAPERCLIP_API_KEY" "$PAPERCLIP_API_URL/api/agents/me"
   ```

2. Check that Blast Radius Touch Index is available
3. Review logs for specific error messages
4. Try `--initial-scan --dry-run` to test without side effects

### Disk filling up (logs)

- Systemd: logs are rotated automatically (max 10 MB per file)
- Docker: mount volume for persistence, implement log rotation
- Manual: check `~/.paperclip/impact_gate/` directory

---

## Next Steps

Choose your deployment method from the options above and follow the setup instructions. For questions or issues, check the main documentation in `docs/IMPACT_GATE_POLLING_DAEMON.md`.
