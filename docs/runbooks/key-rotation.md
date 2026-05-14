# Key Rotation Runbook

**Issue:** BTCAAAAA-7296
**Owner:** SecurityAnalyst
**Last Review:** 2026-05-12

## When to Use

Rotate credentials immediately when:
- A secret or key has been committed to a git repository (even if removed later)
- A credential has been exposed in logs, CI output, or error messages
- A team member with access leaves the company
- A credential is past its rotation window (see [Rotation Schedule](#rotation-schedule))

## Severity Assessment

| Exposure | Severity | Response |
|----------|----------|----------|
| Key in public GitHub history | P0 | Immediate rotation + history purge |
| Key committed to private repo | P1 | Rotate within 1 business day |
| Key leaked in CI log | P1 | Rotate within 1 business day |
| Suspected unauthorized access | P0 | Rotate immediately + audit logs |
| Expired rotation window | P2 | Rotate within 1 week |

---

## Credential Inventory

| Credential | Env Var(s) / File | Provider | Scope | Rotation Window |
|------------|-------------------|----------|-------|-----------------|
| LakeAPI S3 (Crypto Lake) | `LAKEAPI_KEY`, `LAKEAPI_SECRET` | AWS IAM | S3 read for market data | 90 days |
| Binance Testnet | `BINANCE_TESTNET_API_KEY`, `BINANCE_TESTNET_API_SECRET` | Binance | Futures testnet paper trading | 180 days |
| Binance Mainnet | `BINANCE_MAINNET_API_KEY`, `BINANCE_MAINNET_API_SECRET` | Binance | Futures mainnet (CTO-gated) | 90 days |
| PostgreSQL | `POSTGRES_PASSWORD`, `AI_READONLY_PASSWORD` | Local DB | Optimizer v3 database, AI read-only queries | 90 days |
| Paperclip API | `PAPERCLIP_API_KEY` | Paperclip | Issue/board API automation | 90 days |
| OpenRouter AI | `OPENROUTER_API_KEY` | OpenRouter | AI-enhanced recommendations | 90 days |
| rclone GDrive OAuth | `~/.config/rclone/rclone.conf` | Google OAuth | Drive backup upload (`drive` scope) | 180 days (re-auth) |

**Storage:** All credentials reside in `.env` at the project root (or `~/.config/rclone/rclone.conf` for rclone OAuth). `.env` is in `.gitignore`. Both files MUST have permissions `600` (`-rw-------`).

**Source code check:** No hardcoded credentials. All keys loaded via `os.environ.get()` or `os.getenv()`. Verified by `scripts/audit/secrets_audit.py`.

**Binance mainnet keys** require CTO approval before configuration. They must remain **commented out** in `.env` until approved — see `.env.example:525-526`.

---

## Rotation Schedule

| Calendar Event | Credential | Action |
|---------------|-----------|--------|
| Every 90 days | LakeAPI, Binance Mainnet, PostgreSQL, Paperclip, OpenRouter | Standard rotation |
| Every 180 days | Binance Testnet, rclone GDrive OAuth | Standard rotation (re-run bootstrap) |
| Team member departure | All credentials that member had access to | Immediate rotation |
| Post-incident | Compromised credential only | Immediate rotation |

---

## Pre-Rotation Checklist

Before any scheduled rotation:

- [ ] Notify CTO 48h in advance via issue comment on rotation tracking issue
- [ ] Schedule during low-activity window (weekend or UTC 00:00-04:00)
- [ ] Verify backup of `.env`: `cp .env .env.bak.$(date +%Y%m%d)`
- [ ] Ensure access to all provider consoles (AWS IAM, Binance, Paperclip, OpenRouter)
- [ ] Identify all services that consume the credential (see [Credential Consumers](#credential-consumers))
- [ ] Prepare rollback plan (keep old credential active until new one verified)

### Credential Consumers

| Credential | Consumed By |
|-----------|------------|
| `LAKEAPI_KEY/SECRET` | `src/data_manager/download/lake_api_client.py`, `scripts/LakeAPI/*.py` |
| `BINANCE_TESTNET_*` | `src/itm/dry_run/runner.py`, `src/itm/engine/binance_client.py`, `scripts/run_testnet_dry_run.py` |
| `POSTGRES_PASSWORD` | `src/optimizer_v3/database/*.py`, `src/touch_index/db.py`, `src/ai_consultant/audit_writer.py`, `scripts/manage_migrations.py` |
| `AI_READONLY_PASSWORD` | `src/ai_consultant/` (read-only role for AI queries) |
| `PAPERCLIP_API_KEY` | `src/touch_index/paperclip_client.py`, `scripts/run_touch_index_*_worker.py`, `scripts/lock_gate*.py` |
| `OPENROUTER_API_KEY` | `src/optimizer_v3/core/ai_recommendation_enhancer.py`, `src/optimizer_v3/ui/ai_recommendations_panel.py` |
| `~/.config/rclone/rclone.conf` | `~/.paperclip/scripts/backup-to-drive.sh`, `~/.paperclip/scripts/rclone-headless-auth.sh` |

---

## P0 Incident Response: Key in Public Git History

### Step 1: Verify Exposure Scope

```bash
git log --all -S "KEY_PREFIX" --oneline
grep -r "KEY_PREFIX" --include="*.py" --include="*.md" --exclude-dir=.git
```

Document all affected commits and files.

### Step 2: Stop the Bleed

1. Deactivate the key immediately in the provider console (AWS IAM, exchange API portal, etc.)
2. Revoke if the provider supports it (AWS IAM: Status -> Inactive)
3. Delete only after confirming all services have been migrated to the new key

### Step 3: Generate Replacement

1. Create a new key pair in the provider console
2. Store in `.env` (gitignored, never committed)
3. Verify `.env` permissions are 600

### Step 4: Audit Logs

For AWS IAM keys:
1. Open CloudTrail -> Event History
2. Filter by Access Key ID -> check for unexpected IPs, regions, or services
3. Check IAM -> Access Advisor for service usage patterns
4. Document findings in incident report

For Binance keys:
1. Log in to Binance -> API Management
2. Check API key usage history (last-used timestamps, IP addresses)
3. Review trade history for unauthorized activity
4. Document findings in incident report

### Step 5: Update Deployments

1. Update CI/CD environment variables (GitHub Secrets, Jenkins, etc.)
2. Update `.env` files on all machines (production, demo, development)
3. Restart any services that cache the credential
4. Verify connectivity with the new key

### Step 6: Purge Git History

Only AFTER rotation is confirmed and verified:

```bash
bash scripts/security/purge_leaked_keys.sh
```

The script:
- Creates a backup bundle before rewriting
- Uses git filter-repo --replace-text to purge key strings
- Verifies keys are no longer present in history
- Requires human confirmation before executing

### Step 7: Post-Incident Verification

1. Confirm `git log --all -S "OLD_KEY"` returns nothing
2. Run `python3 scripts/audit/secrets_audit.py`, must pass
3. Confirm CI secrets-audit job passes on next push
4. Verify the old key is inactive/deleted in provider console
5. Create incident post-mortem issue documenting timeline and root cause

---

## LakeAPI / AWS IAM Key Rotation

LakeAPI credentials are AWS IAM access keys used for S3 read access to Crypto Lake market data.
The codebase loads them as both `LAKEAPI_KEY`/`LAKEAPI_SECRET` and `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.

### Standard Rotation (90-day cycle)

```bash
# 1. Generate new key in IAM console or CLI
aws iam create-access-key --user-name <lakeapi-user>

# 2. Update .env with new credentials
#    LAKEAPI_KEY=<new_access_key_id>
#    LAKEAPI_SECRET=<new_secret_access_key>

# 3. Verify data access works
python3 -c "
import os
os.environ.setdefault('LAKEAPI_KEY', '<new_key>')
os.environ.setdefault('LAKEAPI_SECRET', '<new_secret>')
os.environ.setdefault('LAKEAPI_REGION', 'eu-west-1')
from src.data_manager.download.lake_api_client import LakeApiClient
client = LakeApiClient()
print(client.list_available_dates()[:3])
"

# 4. Wait 24h for propagation across all consuming services

# 5. Deactivate old key
aws iam update-access-key --access-key-id OLD_KEY_ID --status Inactive --user-name <lakeapi-user>

# 6. Verify services still work with new key only

# 7. Delete old key after 7-day grace period
aws iam delete-access-key --access-key-id OLD_KEY_ID --user-name <lakeapi-user>
```

### LakeAPI-Specific Verification

```bash
# Quick smoke test — downloads the most recent date's 1h candles
python3 scripts/LakeAPI/scan_lakeapi_s3_availability.py

# Full data access test
python3 scripts/LakeAPI/test_lakeapi_data.py
```

---

## Binance Exchange API Key Rotation

### Testnet Key Rotation (180-day cycle)

1. Go to https://testnet.binancefuture.com -> API Management
2. Create a new API key with:
   - **Restrict to testnet only** (default for testnet portal)
   - Enable Futures trading permissions
   - **Do NOT** enable withdrawal permissions
   - Set IP whitelist if available
3. Update `.env`:
   ```
   BINANCE_TESTNET_API_KEY=<new_api_key>
   BINANCE_TESTNET_API_SECRET=<new_api_secret>
   ```
4. Verify connectivity:
   ```bash
   python3 scripts/run_testnet_dry_run.py --min-hours 0
   # Confirm "Binance testnet connectivity: OK" in output
   ```
5. Delete old key from testnet portal

### Mainnet Key Rotation (90-day cycle — CTO-gated)

**Pre-condition:** CTO must approve before mainnet key rotation.

1. Log in to Binance.com -> API Management
2. Create a new API key with restricted IP whitelist
3. Permissions: **Enable Futures** only. Disable: Spot, Margin, Withdrawal.
4. Update `.env` (uncomment if previously commented):
   ```
   BINANCE_MAINNET_API_KEY=<new_api_key>
   BINANCE_MAINNET_API_SECRET=<new_api_secret>
   ```
5. Test with a read-only endpoint first:
   ```bash
   python3 -c "
   import os
   os.environ['BINANCE_MAINNET_API_KEY'] = '<key>'
   os.environ['BINANCE_MAINNET_API_SECRET'] = '<secret>'
   from src.itm.engine.binance_client import BinanceClient
   c = BinanceClient(use_testnet=False)
   print(c.get_account_info())
   "
   ```
6. Delete old key from Binance portal

### Binance Security Baseline

- [ ] IP whitelist active on all API keys
- [ ] Withdrawal permission disabled on all API keys
- [ ] Testnet keys are only in testnet portal (never mainnet)
- [ ] Mainnet keys commented out in `.env.example`

---

## PostgreSQL Password Rotation

Database credentials are stored in `.env` and consumed by the optimizer v3, touch index workers, and AI consultant modules.
Two roles exist: `optimizer_admin` (owner) and `ai_readonly` (read-only for AI queries).

### Pre-Rotation

```bash
# Backup current .env
cp .env .env.bak.$(date +%Y%m%d)

# Confirm current passwords work
python3 -c "
import os
os.environ['POSTGRES_PASSWORD'] = '$(grep POSTGRES_PASSWORD .env | cut -d= -f2)'
from src.optimizer_v3.database.database_manager import DatabaseManager
mgr = DatabaseManager()
print('Connected:', mgr.test_connection())
"
```

### Rotate POSTGRES_PASSWORD (optimizer_admin)

```bash
# 1. Generate a strong random password (32+ chars)
NEW_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "New optimizer_admin password: $NEW_PASSWORD"

# 2. Change password in PostgreSQL
sudo -u postgres psql -c "ALTER USER optimizer_admin WITH PASSWORD '$NEW_PASSWORD';"

# 3. Update .env
#    POSTGRES_PASSWORD=<new_password>

# 4. Restart consuming services
#    (strategy builder GUI, touch index workers, any running backtests)

# 5. Verify connection with new password
python3 -c "
import os
os.environ['POSTGRES_PASSWORD'] = '$NEW_PASSWORD'
from src.optimizer_v3.database.database_manager import DatabaseManager
mgr = DatabaseManager()
print('OK' if mgr.test_connection() else 'FAIL')
"

# 6. Update pgpass if used
#    ~/.pgpass: localhost:5432:optimizer_v3:optimizer_admin:<new_password>
```

### Rotate AI_READONLY_PASSWORD

```bash
# 1. Generate a strong random password
NEW_AI_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
echo "New ai_readonly password: $NEW_AI_PASSWORD"

# 2. Change password in PostgreSQL
sudo -u postgres psql -c "ALTER USER ai_readonly WITH PASSWORD '$NEW_AI_PASSWORD';"

# 3. Update .env
#    AI_READONLY_PASSWORD=<new_password>
```

---

## Paperclip API Key Rotation

The Paperclip API key grants access to the issue/board API automation. It is consumed by touch index workers, lock gate scripts, and any module importing `src/touch_index/paperclip_client.py`.

### Rotation Procedure

1. Generate new key in Paperclip -> Settings -> API Keys
2. Update `.env`:
   ```
   PAPERCLIP_API_KEY=<new_key>
   ```
3. Verify the new key works:
   ```bash
   python3 -c "
   import os
   os.environ['PAPERCLIP_API_URL'] = '$(grep PAPERCLIP_API_URL .env | cut -d= -f2)'
   os.environ['PAPERCLIP_API_KEY'] = '<new_key>'
   os.environ['PAPERCLIP_COMPANY_ID'] = '$(grep PAPERCLIP_COMPANY_ID .env | cut -d= -f2)'
   from src.touch_index.paperclip_client import PaperclipClient
   c = PaperclipClient()
   print('Authenticated:', c.whoami().get('name', 'OK'))
   "
   ```
4. Revoke old key in Paperclip -> Settings -> API Keys
5. Restart touch index workers:
   ```bash
   # Bug worker
   pkill -f run_touch_index_bug_worker.py
   python3 scripts/run_touch_index_bug_worker.py &

   # FR worker
   pkill -f run_touch_index_fr_worker.py
   python3 scripts/run_touch_index_fr_worker.py &
   ```

---

## OpenRouter AI Key Rotation

The OpenRouter API key enables AI-enhanced strategy recommendations. If the key is missing, the system falls back to local recommendations only (graceful degradation).

### Rotation Procedure

1. Log in to https://openrouter.ai/keys
2. Create a new key (or regenerate existing)
3. Update `.env`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-<new_key>
   ```
4. Verify with a lightweight AI request:
   ```bash
   python3 -c "
   import os
   os.environ['OPENROUTER_API_KEY'] = '<new_key>'
   from src.optimizer_v3.core.ai_recommendation_enhancer import AIRecommendationEnhancer
   enhancer = AIRecommendationEnhancer()
   print('AI enabled:', enhancer.is_enabled())
   "
   ```
5. Delete old key in OpenRouter dashboard

**Note:** The system degrades gracefully without this key — AI features are disabled but all local functionality continues. This credential is not mission-critical for trading operations.

---


---

## rclone Google Drive OAuth Rotation

The rclone OAuth token is used for uploading backups to Google Drive. The token is stored in `~/.config/rclone/rclone.conf` (NOT in `.env`).

**Token lifecycle:**
- Access token expires ~1 hour after issuance, but is auto-refreshed via the refresh token
- The refresh token does not expire unless manually revoked at https://myaccount.google.com/permissions
- Rotation is required when: the refresh token is revoked, a team member with Google Drive access leaves, or as a scheduled precaution

### Scheduled Re-auth (180-day cycle)

```bash
# 1. Check current auth status
~/.paperclip/scripts/rclone-headless-auth.sh --check

# 2. If the token is missing or expired, re-run the bootstrap script
/home/sirrus/.paperclip/scripts/rclone-bootstrap.sh

# The bootstrap script will prompt for browser-based OAuth authorization.
# On a headless server, copy the URL, open in a browser, authorize,
# and paste the verification code back.

# 3. Verify the remote is functional
rclone listremotes
# Expected: gdrive:

rclone lsd gdrive:Paperclip-Backups/
# Expected: empty or listing backup subdirectories

# 4. Run a manual backup to confirm
/home/sirrus/.paperclip/scripts/backup-to-drive.sh
```

### Incident Response: Compromised Token

1. Revoke the rclone app access at https://myaccount.google.com/permissions
2. Clear the existing token:
   ```bash
   rclone config delete gdrive
   ```
3. Re-run bootstrap:
   ```bash
   /home/sirrus/.paperclip/scripts/rclone-bootstrap.sh
   ```
4. Verify as above

### File Protection

```bash
# rclone.conf contains OAuth tokens — protect it
chmod 600 ~/.config/rclone/rclone.conf

# Verify ownership
ls -la ~/.config/rclone/rclone.conf
# Expected: -rw------- 1 <user> <group> ...
```

### OAuth Credential Inventory

| Item | Location | Notes |
|------|----------|-------|
| OAuth token (access + refresh) | `~/.config/rclone/rclone.conf` | Auto-refreshed; only manual action needed if revoked |
| Bootstrap script | `~/.paperclip/scripts/rclone-bootstrap.sh` | Interactive — requires browser for OAuth |
| Headless auth script | `~/.paperclip/scripts/rclone-headless-auth.sh` | For headless token check/apply |
| Google Account permissions | https://myaccount.google.com/permissions | Revoke "rclone" app access here |


## Post-Rotation Verification (All Credentials)

### Automated Audit

```bash
python3 scripts/audit/secrets_audit.py
# Must output: "No secrets found."
```

### Manual Checklist

After any credential rotation:

- [ ] `secrets_audit.py` passes (must output "No secrets found.")
- [ ] No hardcoded credentials in source files
- [ ] `.env` is in `.gitignore`
- [ ] `.env` file permissions are `600` (`ls -la .env`)
- [ ] New keys stored in `.env` only (never committed)
- [ ] `.env.example` does not contain real keys
- [ ] Old keys deactivated or deleted in provider console
- [ ] All consuming services restarted and verified
- [ ] CI secrets-audit job passes (if wired)

### Service Smoke Tests

| Credential | Smoke Test |
|-----------|-----------|
| LakeAPI | `python3 scripts/LakeAPI/scan_lakeapi_s3_availability.py` |
| Binance Testnet | `python3 scripts/run_testnet_dry_run.py --min-hours 0` |
| PostgreSQL | `python3 -c "from src.optimizer_v3.database.database_manager import DatabaseManager; print(DatabaseManager().test_connection())"` |
| Paperclip | Touch index worker heartbeat check (verify it posts a comment) |
| OpenRouter | Strategy Builder -> check AI recommendations panel loads without error |
| rclone GDrive | `rclone lsd gdrive:Paperclip-Backups/` (lists backup directories) |

---

## Rollback Procedure

If verification fails after rotation:

### Step 1: Restore Old Credential

```bash
# Restore from backup
cp .env.bak.YYYYMMDD .env

# Or manually reactivate the old key in the provider console
```

### Step 2: Revert in Provider Console

- **AWS IAM:** `aws iam update-access-key --access-key-id NEW_KEY_ID --status Inactive --user-name <user>`
- **Binance:** Delete the new key from API Management
- **PostgreSQL:** `ALTER USER optimizer_admin WITH PASSWORD '<old_password>';`
- **Paperclip:** Revoke new key, keep old key active
- **OpenRouter:** Delete new key, keep old key active
- **rclone GDrive:** `rclone config delete gdrive` then re-run `rclone-bootstrap.sh` with old token

### Step 3: Verify Rollback

Run the relevant smoke test from the [Service Smoke Tests](#service-smoke-tests) table.

### Step 4: Report

Create an issue documenting the failed rotation with root cause and new plan.

---

## Working Tree Verification Checklist

After any credential rotation:

- [ ] `secrets_audit.py` passes (`python3 scripts/audit/secrets_audit.py`)
- [ ] No hardcoded keys in source files
- [ ] `.env` is in `.gitignore`
- [ ] New keys stored in `.env` only (never committed)
- [ ] CI secrets-audit job passes
- [ ] Old keys deactivated in provider console

---

## References

- BTCAAAAA-7296: Key rotation runbook (this document)
- BTCAAAAA-7256: P0 key rotation incident (2026-05-12)
- [SECURITY_AUDIT_20260512.md](../SECURITY_AUDIT_20260512.md): Latest security audit findings
- `scripts/security/purge_leaked_keys.sh`: Git history purge tool
- `scripts/audit/secrets_audit.py`: Automated credential scanner
- `.github/workflows/lint.yml`: CI pipeline with secrets-audit gate
- `.env.example`: Environment variable template (no real keys)
- `docs/OAUTH_SETUP.md`: rclone Google Drive OAuth setup guide (board one-pager)
- `docs/runbook-backup-restore.md`: Backup/restore runbook with rclone operations
- `~/.paperclip/scripts/rclone-bootstrap.sh`: Interactive OAuth bootstrap script
- `~/.paperclip/scripts/rclone-headless-auth.sh`: Headless token check/apply script
