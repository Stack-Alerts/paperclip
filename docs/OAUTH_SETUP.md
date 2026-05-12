# OAUTH_SETUP — rclone Google Drive OAuth (Board One-Pager)

**Audience:** Board members / administrators performing this one-time setup
**Time required:** ~10 minutes
**What you need:** A Google account (corporate Gmail or Google Workspace)

---

## What This Does

This registers Google Drive as the offsite backup target for the BTC Trade Engine's
PostgreSQL database backups. rclone requests **least-privilege Drive access**
(`drive.file` scope) — it can only see and modify files it creates itself.

---

## Step-by-Step

### Step 1: Install rclone (if not already installed)

```bash
sudo apt install rclone
```

### Step 2: Run the bootstrap script

```bash
bash scripts/rclone_bootstrap.sh
```

You will see:

```
========================================
  BTC Trade Engine -- rclone GDrive Bootstrap
========================================

rclone found: rclone v1.68

Step 1: Creating rclone remote 'btc_backup' for Google Drive
  Scope: drive.file
  (Least privilege -- only files created by this app)
```

### Step 3: Authorize in the browser

The script will print a URL like:

```
https://accounts.google.com/o/oauth2/auth?client_id=...
```

1. **Copy the URL** from the terminal
2. **Open it** in any browser (can be a different machine than the server)
3. **Log in** with your Google account
4. The consent screen will show: **"Grant rclone access to your Google Drive"**
   - Permission requested: *See and download files it creates*
   - This is the `drive.file` scope — it cannot see your other Drive files
5. Click **Allow**
6. **Copy the verification code** that appears

### Step 4: Paste the code back

Go back to the terminal where `rclone_bootstrap.sh` is running and paste the
verification code when prompted. The script will then:

- Store the OAuth token in `~/.config/rclone/rclone.conf` (never in git)
- Verify the connection works
- Create the backup directory `btc-trade-engine-backups/` on Google Drive

### Step 5: Verify success

```bash
# Check the remote is configured
rclone listremotes
# Expected output: btc_backup:

# List the backup directory
rclone ls btc_backup:btc-trade-engine-backups/

# Check configuration file exists (contains OAuth token, keep secret)
ls -la ~/.config/rclone/rclone.conf
```

---

## Permission Scope Reference

| Scope | rclone flag | What it allows |
|-------|-------------|----------------|
| `drive.file` | `--drive-scope drive.file` | **Only files created by this app.** Cannot see your personal docs, photos, etc. |
| `drive` (full) | `--drive-scope drive` | Full access to all Drive files (not used — too permissive) |

We use `drive.file` exclusively. The rclone config sets `--drive-auth-owner-only` as
an additional safety constraint.

---

## Security Notes

- The OAuth token is stored in `~/.config/rclone/rclone.conf`
- **Never commit this file to git** — it is not in the repo and must not be added
- If the token is compromised, revoke it at:
  https://myaccount.google.com/permissions
- To re-authorize with a different account:

  ```bash
  rclone config delete btc_backup
  bash scripts/rclone_bootstrap.sh
  ```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `rclone: not found` | Install: `sudo apt install rclone` |
| `No verification code shown` | Make sure you click "Allow" in the browser, not just "Cancel" |
| `Token expired` | Run `bash scripts/rclone_bootstrap.sh` again to re-authorize |
| `Drive quota exceeded` | Free up space in the backup directory on GDrive |
| `Remote 'btc_backup' already configured` | Script will ask if you want to reconfigure. Say `y` to redo OAuth |

---

## What Happens Next

Once OAuth is complete:

1. Backups are created locally via `manage_backups.py` (every 4 hours)
2. `sync_backups_to_gdrive.py` pushes them to `btc_backup:btc-trade-engine-backups/`
3. The dead-man's-switch monitor alerts if backups stop flowing

Manual sync test after setup:

```bash
python scripts/sync_backups_to_gdrive.py --dry-run
python scripts/sync_backups_to_gdrive.py
rclone ls btc_backup:btc-trade-engine-backups/
```
