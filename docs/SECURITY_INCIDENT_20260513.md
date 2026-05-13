# Security Incident Report — AWS Credential Exposure

**Issue:** BTCAAAAA-15103  
**Severity:** P0 (Critical)  
**Date:** 2026-05-13  
**Analyst:** SecurityAnalyst  
**Status:** RESOLVED — Git history purged, IAM rotation pending

---

## Executive Summary

AWS Crypto Lake (S3) credentials were committed to the git repository as hardcoded string literals. Both the Access Key ID and Secret Access Key were present in git history across multiple commits. The git history has been purged. AWS IAM key rotation is the outstanding action.

---

## Incident Timeline

| Time | Event |
|------|-------|
| Unknown | AWS credentials hardcoded in `scripts/LakeAPI/test_lakeapi_data.py` |
| 2026-05-11 | Credentials committed to git (commit `847d9119` and descendants) |
| 2026-05-12 | Security audit (BTCAAAAA-1348) discovers hardcoded keys; creds removed from tracked source |
| 2026-05-12 | Purge scripts created but not executed; secret redacted in replacements template |
| 2026-05-13 03:39 | Git history purge executed with `git filter-repo --replace-text` (regex patterns) |
| 2026-05-13 03:45 | Purged history force-pushed to remote |

---

## Exposure Scope

### Credential 1: AWS Access Key ID
- **Value:** Redacted in history as `AKIA************DBUD`
- **Type:** IAM access key ID (identifying, not secret by itself)
- **Commits in history:** 3+ before purge, 0 after

### Credential 2: AWS Secret Access Key
- **Value:** Full secret access key string (40 chars, base64)
- **Type:** IAM secret access key (P0 — grants S3 read access to Crypto Lake)
- **Commits in history:** 3+ before purge, 0 after

### Scope of Access
- **Service:** AWS S3 (Crypto Lake market data)
- **Region:** eu-west-1
- **Permissions:** S3 read (`lakeapi.load_data()` calls)
- **Risk if unrotated:** Anyone with cloned repo can read Crypto Lake S3 data

### .env File Assessment
- `.env` is properly gitignored (`.gitignore` line 56)
- `.env` is NOT tracked by git
- No `.env` content found in git history
- **Verdict:** No exposure via `.env`

---

## Remediation Actions

### COMPLETED
- [x] Removed hardcoded AWS credentials from all tracked source files (2026-05-12)
- [x] Rewrote `test_lakeapi_data.py` to load creds from env vars
- [x] Rewrote all archived LakeAPI scripts to use `os.environ.get()`
- [x] Purged AWS key ID and secret from entire git history
- [x] Force-pushed cleaned history to remote (all branches)
- [x] Local working repository refreshed with cleaned history
- [x] Verified: 0 occurrences of key ID or secret in any commit/ref/tag

### PENDING — REQUIRES HUMAN ACTION
- [ ] **Rotate AWS credentials in IAM** — contact AWS admin to deactivate key and create new keys
- [ ] Notify all team members to discard local clones and re-clone from origin
- [ ] Update `.env` with new credentials after rotation
- [ ] Delete backup bundle at `/tmp/btc-engine-before-purge-*.bundle`

---

## Purge Technical Details

**Tool:** `git filter-repo` v2.47.0  
**Method:** Regex-based text replacement (`--replace-text` only)  
**Commits rewritten:** 3,737  
**Branches rewritten:** main, feature/BTCAAAAA-700-qt-ui-tests-ci-job, fix/btcaaaaa-2182-lock-gate-exception, fix/BTCAAAAA-929-weight-backfill-repair-harden-preview-threshold  
**Corruption check:** No artifacts in any source file  
**Secrets audit:** `python scripts/audit/secrets_audit.py` exits 0 ("No secrets found.")

---

## Prevention Measures

1. **CI Gate (ACTIVE):** `scripts/audit/secrets_audit.py` runs on every push/PR
2. **`.gitignore`:** Credential files properly excluded
3. **Key Rotation Runbook:** `docs/runbooks/key-rotation.md`
4. **Recommended:** Add pre-commit hook for local secrets audit

---

## Security Review Sign-Off

```
## Security Review: PASS (post-remediation)

- No hardcoded credentials: [x]
- API keys from env/vault only: [x]
- HMAC signing correct:     [x] (N/A — AWS SDK handles auth)
- No secrets in logs:       [x]
- Replay protection present: [x] (AWS SigV4)
- .gitignore covers .env and key files: [x]

Security verdict: REMEDIATION COMPLETE — IAM key rotation is final outstanding action
```

---

## Escalation

Per CEO directive (2026-05-12), critical findings require immediate escalation. Git history has been purged. Remaining blocker: IAM key rotation requires AWS console access.

- **Blocker:** No AWS IAM console access to deactivate/rotate keys
- **Unblocker:** AWS account administrator / CTO
- **Action:** Escalating to CTO for IAM key rotation
