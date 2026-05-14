# Runbook: Archive Operations

**Last updated:** 2026-05-14
**Owner:** DocWriter
**Audience:** All engineers, DocWriter

---

## 1. Overview

This runbook covers all archive, retention, and cleanup operations across the BTC Trade Engine. The system has four archive domains:

| Domain | Description | Owner |
|---|---|---|
| **Code/scripts** | `scripts/archived/` — legacy scripts removed from active codebase | DocWriter / Coder |
| **Documentation** | `docs/archive/` — completed session notes, legacy docs, sprint handoffs | DocWriter |
| **GitHub artifacts** | CI workflow artifact retention (7–90 day policies) | RepoSteward |
| **Log rotation** | Local script log auto-rotation at 1 MB | AutomationEngineer |

---

## 2. Code/Script Archiving (`scripts/archived/`)

### 2.1 Purpose

The `scripts/archived/` directory holds legacy scripts that have been removed from the active codebase but preserved for reference. These scripts are **not importable** by production code.

### 2.2 Guard: Lint CI (`archived-paths` job)

The lint workflow ([`.github/workflows/lint.yml`](../.github/workflows/lint.yml):43–77) enforces that archived `src/` paths are never re-introduced:

```bash
# The blocklist in the lint workflow checks these paths:
# - src/utils/Strategy_Builder/
# - src/strategies/strategy_02_reversal_w_pattern.py
# - src/strategy_builder/core/nautilus_code_generator.py
# - src/strategy_builder/examples/complete_workflow_example.py
```

**To add a new archived path to the guard:**
1. Move the file/directory out of `src/` to the appropriate location
2. Add the old path to the `check_path` blocklist in the `archived-paths` job
3. Update `.gitignore` stale-code section if applicable

### 2.3 How to Archive a Script

```bash
# 1. Move the script to scripts/archived/
mv scripts/my_old_script.py scripts/archived/

# 2. Remove any import references in active code
#    (static_dep_graph.py, secrets_audit.py, etc. skip archived/ by path)

# 3. If it was a src/ path, add it to the lint blocklist
#    (see .github/workflows/lint.yml archived-paths job)

# 4. Commit with message: "chore: archive <script-name>"
```

### 2.4 Current Contents

The `scripts/archived/` directory contains ~100 entries including:
- Old strategy builder variants (Tkinter, CLI, Qt)
- Batch optimization and validation scripts (pre-multicore)
- Walkforward test scripts (pre-v2)
- Pattern analysis and training scripts
- Various migration and debug utilities

**Note:** Archived scripts are excluded from static analysis by `scripts/static_dep_graph.py` (skips `archived` in path components) and `scripts/audit/secrets_audit.py` (skips `archive` in path components).

### 2.5 Restoration

If an archived script needs to be restored:

```bash
# Check if a replacement exists in active code first
grep -r "function_name" src/ --include="*.py"

# If no replacement, restore from archived/
cp scripts/archived/my_script.py scripts/my_script.py
```

---

## 3. Document Archiving (`docs/archive/`)

### 3.1 Purpose

The `docs/archive/` directory preserves completed or superseded documentation. See [`docs/README.md`](README.md) for the canonical navigation.

### 3.2 Archive Directory Layout

```
docs/archive/
├── ui-ux/                   # Session notes and gap analyses from UI-UX development
├── integration-results/     # Backtest forensic and wiring analysis reports
├── test-notes/              # Building blocks registry test session notes
├── testing/                 # Old testing documentation
├── v3-legacy/               # Pre-v3 layered architecture docs
├── v3-archived/             # V3 top-level archived files
├── v3-sessions/             # V3 session notes
├── root-archived/           # Root-level archived session and rule files
├── data-reports/            # Old data analysis reports
└── optimizer/sprints/       # Completed optimizer sprint docs
```

### 3.3 How to Archive a Document

```bash
# 1. Determine the correct subdirectory in docs/archive/
#    - UI/UX docs → archive/ui-ux/
#    - Integration reports → archive/integration-results/
#    - Test session notes → archive/test-notes/
#    - Pre-v3 architecture → archive/v3-legacy/
#    - V3 sprint docs → archive/v3-archived/  (sprints live in optimizer/sprints/)
#    - Root-level session/rule files → archive/root-archived/
#    - Anything else → archive/ (choose/create appropriate subdirectory)

# 2. Move the file
mv docs/my-old-doc.md docs/archive/appropriate-subdir/

# 3. If the doc was referenced in docs/README.md, remove or update the link

# 4. Commit with message: "docs: archive <document-name>"
```

### 3.4 Cross-Reference Integrity

Before archiving a document, check for cross-references:

```bash
grep -r "my-old-doc.md" docs/ --include="*.md"
```

Update or remove any cross-references before archiving.

---

## 4. GitHub Actions Artifact Retention

### 4.1 Retention Policies by Workflow

| Workflow | Retention | Reference |
|---|---|---|
| Walkforward validation | 90 days | `.github/workflows/walkforward-validation.yml:136,144` |
| Lock module verify | 30 days | `.github/workflows/lock-module-verify.yml:161` |
| Blast Radius Worker | 30 days | `.github/workflows/blast-radius-worker.yml:117` |
| Impact Gate scan-done | 30 days | `.github/workflows/impact-gate-scan-done.yml:112` |
| Impact Gate scan-health | 14 days | `.github/workflows/impact-gate-scan-health.yml:113` |
| Backup-to-Drive | 14 days | `.github/workflows/backup-to-drive.yml:61,69` |
| All other workflows | 7 days | (default for monitors, watchdogs, QA pipelines) |

### 4.2 Manual Artifact Cleanup

GitHub Actions artifacts accumulate even after retention expiry. To purge manually:

```bash
# List all artifacts for the repo
gh api repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions/artifacts --paginate

# Delete a specific artifact by ID
gh api -X DELETE repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions/artifacts/{artifact_id}

# Delete all expired artifacts
gh api -X DELETE repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions/artifacts?per_page=100 \
  | jq '.artifacts[] | select(.expired == true) | .id' \
  | xargs -I{} gh api -X DELETE repos/Stack-Alerts/BTC-Trade-Engine-PaperClip/actions/artifacts/{}
```

### 4.3 Log Retention

Workflow run logs are retained per GitHub default (default: 90 days for public repos, 400 days for enterprise). Check current setting:

```bash
gh api repos/Stack-Alerts/BTC-Trade-Engine-PaperClip \
  | jq '.archived, .archive_url, .allow_merge_commit'
```

---

## 5. Local Log Rotation

### 5.1 Pattern

Several monitor scripts implement automatic log rotation at 1 MB via a shared `_rotate_log_if_needed()` pattern:

| Script | Log File |
|---|---|
| `scripts/backup_dead_switch.py` | `~/.paperclip/backup_dead_log` |
| `scripts/backup_dead_switch_monitor.py` | `~/.paperclip/backup_dead_switch_monitor.log` |
| `scripts/deadman_switch_monitor.py` | `~/.paperclip/deadman_switch_monitor.log` |
| `scripts/deadman_switch_local_monitor.py` | `~/.paperclip/deadman_switch_local_monitor.log` |
| `scripts/rclone_oauth_health.py` | `~/.paperclip/rclone_oauth_health.log` |
| `scripts/paperclip_recovery_monitor.py` | `~/.paperclip/recovery_monitor.log` |
| `scripts/provider_monitor.py` | Provider-specific log |

### 5.2 How Rotation Works

When a log file exceeds 1 MB:
1. The current log is renamed to `{log_path}.1` (overwriting any existing `.1` file)
2. A fresh log file is created
3. This is a single-backup rotation (only one rotated copy is kept)

### 5.3 Manual Log Cleanup

```bash
# View log sizes
du -sh ~/.paperclip/*.log ~/.paperclip/*.log.1 2>/dev/null

# Truncate a log (losing current content, not recommended)
: > ~/.paperclip/some_monitor.log

# Remove rotated backup
rm ~/.paperclip/some_monitor.log.1
```

### 5.4 Journald Logs (systemd services)

Monitor scripts running as systemd user services also write to journald:

```bash
# View size
journalctl --user --disk-usage

# Vacuum to 50 MB
journalctl --user --vacuum-size=50M

# Vacuum to 7 days
journalctl --user --vacuum-time=7d
```

---

## 6. Database Backup Retention

See [runbook-backup-restore.md](runbook-backup-restore.md) for full details.

| Policy | Value | Config |
|---|---|---|
| Backup retention | 30 days | `POSTGRES_BACKUP_RETENTION_DAYS` in `.env` |
| Cleanup command | `python scripts/manage_backups.py cleanup` | Uses file ctime |
| Offsite (GDrive) retention | Managed by rclone | Manual purge per bucket |

### 6.1 Manual Cleanup

```bash
# Apply retention policy
python scripts/manage_backups.py cleanup

# Custom retention with auto-confirm
python scripts/manage_backups.py cleanup --retention 7 --yes

# Offsite GDrive purge (DESTRUCTIVE)
rclone purge gdrive:Paperclip-Backups/<companyId>/<year>/<month>/<day>/<time>
```

---

## 7. Paperclip Issue Lifecycle (Stale Issue Management)

### 7.1 Issue States

Paperclip issues follow the lifecycle: `backlog` → `todo` → `in_progress` → `in_review` → `done` / `cancelled` / `blocked`.

### 7.2 When to Archive / Close

| Condition | Action |
|---|---|
| Work completed and verified | Move to `done` |
| Scope changed, no longer needed | Move to `cancelled` |
| Dependencies stalled >30 days | Move to `backlog` or `cancelled` with comment |
| Duplicate issue | Move to `cancelled` with reference to canonical issue |
| Research/completed analysis | Move to `done` with summary comment |

### 7.3 Bulk Cleanup (Manual)

Use the Paperclip API to find stale issues:

```bash
# Find issues in todo/backlog untouched for 30+ days
# (Requires PAPERCLIP_API_KEY)
curl -s -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  "$PAPERCLIP_API_URL/api/companies/$PAPERCLIP_COMPANY_ID/issues?status=todo,backlog" \
  | jq '.data[] | select(.updatedAt < (now - 30*86400)) | .id + " " + .identifier'
```

---

## 8. Security Archive Note

Per [SECURITY_INCIDENT_20260513.md](SECURITY_INCIDENT_20260513.md), historically committed credentials required a git history purge. When archiving files that once contained credentials:

1. **Do NOT** restore unredacted versions from `scripts/archived/`
2. **Do NOT** copy credential-containing files into `docs/archive/`
3. Verify redacted state: `python scripts/audit/secrets_audit.py`

See [runbooks/key-rotation.md](runbooks/key-rotation.md) for key rotation procedures.

---

## 9. Related Documents

- [README.md](README.md) — Documentation index with archive structure
- [runbook-backup-restore.md](runbook-backup-restore.md) — Database backup/retention
- [runbook-ci-cd.md](runbook-ci-cd.md) — CI/CD artifact retention
- [runbooks/key-rotation.md](runbooks/key-rotation.md) — Key lifecycle
- [runbook-incident-response.md](runbook-incident-response.md) — Incident escalation
- [SECURITY_INCIDENT_20260513.md](../SECURITY_INCIDENT_20260513.md) — Security incident (history purge)
- [.github/workflows/lint.yml](../.github/workflows/lint.yml) — Archived-paths CI guard
