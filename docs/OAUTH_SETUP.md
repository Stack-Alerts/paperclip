# OAUTH_SETUP — rclone Google Drive OAuth for PaperClip Backups (Board One-Pager)

**Audience:** Board members / administrators
**Time required:** ~10 minutes
**What you need:** A Google account (corporate Gmail or Google Workspace)

---

## What This Does

This authorises the PaperClip server to upload backups to a dedicated Google Drive
folder (`Paperclip-Backups/`). It uses `drive` scope to access all files in its
folder, including historical backups created with previous tokens:

> ✅ rclone can see and manage files in its Drive folder (including historical backups)
> ❌ rclone cannot access any Google services other than Drive

---

## Step-by-Step

### Step 1: SSH into the PaperClip server

```bash
ssh <user>@<paperclip-server>
```

### Step 2: Verify rclone is installed

```bash
rclone version
```

If not installed:

```bash
sudo apt update && sudo apt install rclone
```

### Step 3: Run the bootstrap script

```bash
/home/sirrus/.paperclip/scripts/rclone-bootstrap.sh
```

You will see:

```
========================================
  Paperclip -- rclone GDrive Bootstrap
========================================

Step 1: Creating rclone remote 'gdrive' (scope: drive)

A browser URL will be printed. On a headless server:
  1. Copy the URL
  2. Open it in a browser on any machine
  3. Authorize with your Google account
  4. Paste the returned verification code here
```

### Step 4: Authorize in the browser

1. **Copy the URL** from the terminal — it looks like:
   ```
   https://accounts.google.com/o/oauth2/auth?client_id=...
   ```
2. **Open it** in any browser (can be your laptop — not the server)
3. **Log in** with your Google account
4. **Review the consent screen:**
   - **App name:** rclone
   - **Permission requested:** *See, edit, create, and delete all of your Google Drive files*
   - This is the `drive` scope — needed to access historical backups from prior tokens
5. Click **Allow**
6. **Copy the verification code** that appears

### Step 5: Paste the code back

Go back to the terminal session and paste the code when prompted.

### Step 6: Confirm success

The script will show:

```
========================================
  Bootstrap complete!
  Remote:  gdrive:
  Root:    gdrive:Paperclip-Backups/
  Config:  /home/sirrus/.config/rclone/rclone.conf

To run a backup now:
  /home/sirrus/.paperclip/scripts/backup-to-drive.sh
```

---

## Verifying the Setup

```bash
# Check the remote exists
rclone listremotes
# Expected: gdrive:

# Check the backup root directory exists
rclone lsd gdrive:Paperclip-Backups/
# Expected: empty or listing backup subdirectories

# Run a manual backup to test
/home/sirrus/.paperclip/scripts/backup-to-drive.sh
```

---

## Permission Scope Reference

| Scope | What It Allows |
|-------|----------------|
| `drive` | Full Drive file access (used — needed for cross-token backup visibility) |
| `drive.file` | Per-file access only (NOT used — prevents seeing historical backups) |

---

## How to Revoke Access Later

1. Go to https://myaccount.google.com/permissions
2. Look for **"rclone"** in the list of third-party apps
3. Click **Remove Access**

After revocation, re-run `rclone-bootstrap.sh` to set up fresh credentials.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `rclone: not found` | `sudo apt install rclone` |
| No URL printed | Ensure terminal supports interactive prompts or use `ssh -t` |
| `Token expired` | Re-run `rclone-bootstrap.sh` and re-authorize |
| `Remote 'gdrive' already configured` | Say `y` to reconfigure, or run `rclone config delete gdrive` first |
| `Failed to create file system` | Check `~/.config/rclone/rclone.conf` exists and is readable |
| Quota exceeded | Clean up old backups or upgrade Google Drive storage |
| Permission denied | Ensure the Google account has write access to the target Drive |

---

## What Happens After Setup

1. The PaperClip routine calls `backup-to-drive.sh` every 4 hours
2. Each backup uploads to `gdrive:Paperclip-Backups/<companyId>/YYYY/MM/DD/HHMM/`
3. A dead-man's-switch monitors that backups are flowing
4. To restore, use `restore-from-drive.sh` (see `RESTORE.md`)
