# Key Rotation Runbook

## When to Use

Rotate credentials immediately when:
- A secret or key has been committed to a git repository (even if removed later)
- A credential has been exposed in logs, CI output, or error messages
- A team member with access leaves the company
- A credential is past its rotation window (AWS: 90 days, exchange API: 90 days)

## Severity Assessment

| Exposure | Severity | Response |
|----------|----------|----------|
| Key in public GitHub history | P0 | Immediate rotation + history purge |
| Key committed to private repo | P1 | Rotate within 1 business day |
| Key leaked in CI log | P1 | Rotate within 1 business day |
| Suspected unauthorized access | P0 | Rotate immediately + audit logs |
| Expired rotation window | P2 | Rotate within 1 week |

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
2. Store securely, never in source code or git-tracked files
3. Use environment variables or a secrets manager (.env already in .gitignore)

```
# .env (gitignored - never commit)
LAKEAPI_KEY=your_new_access_key
LAKEAPI_SECRET=your_new_secret_key
LAKEAPI_REGION=eu-west-1
```

### Step 4: Audit Logs

For AWS IAM keys:
1. Open CloudTrail -> Event History
2. Filter by Access Key ID -> check for unexpected IPs, regions, or services
3. Check IAM -> Access Advisor for service usage patterns
4. Document findings in incident report

### Step 5: Update Deployments

1. Update CI/CD environment variables (GitHub Secrets, Jenkins, etc.)
2. Update .env files on production/demo machines
3. Restart any services that cache the credential
4. Verify connectivity with the new key

### Step 6: Purge Git History

Only AFTER rotation is confirmed:

```bash
bash scripts/security/purge_leaked_keys.sh
```

The script:
- Creates a backup tag before rewriting
- Uses git filter-repo --replace-text to purge key strings
- Requires human confirmation before executing

### Step 7: Verify

1. Confirm git log --all -S "OLD_KEY" returns nothing
2. Run python3 scripts/audit/secrets_audit.py, must pass
3. Confirm CI secrets-audit job passes on next push
4. Verify the old key is inactive in provider console

---

## AWS IAM Key Rotation (Standard)

For non-incident rotations (every 90 days):

```bash
# 1. Generate new key in IAM console or CLI
aws iam create-access-key --user-name <user>

# 2. Update .env with new credentials
# 3. Wait 24h for propagation
# 4. Deactivate old key
aws iam update-access-key --access-key-id OLD_KEY_ID --status Inactive --user-name <user>

# 5. Verify services work with new key only
# 6. Delete old key after 7-day grace period
aws iam delete-access-key --access-key-id OLD_KEY_ID --user-name <user>
```

---

## Exchange API Key Rotation

1. Generate new API key in exchange portal (Binance, Bybit, etc.)
2. Restrict permissions: trading only, no withdrawal, IP whitelist if available
3. Update .env:
   ```
   BINANCE_API_KEY=new_key
   BINANCE_SECRET_KEY=new_secret
   ```
4. Test with a read-only endpoint before enabling trading
5. Delete old key from exchange portal

---

## Working Tree Verification Checklist

After any credential rotation:

- [ ] secrets_audit.py passes (python3 scripts/audit/secrets_audit.py)
- [ ] No hardcoded keys in source files
- [ ] .env is in .gitignore
- [ ] New keys stored in .env only (never committed)
- [ ] CI secrets-audit job passes
- [ ] Old keys deactivated in provider console

---

## References

- BTCAAAAA-7256: P0 key rotation incident (2026-05-12)
- scripts/security/purge_leaked_keys.sh: Git history purge tool
- scripts/audit/secrets_audit.py: Automated credential scanner
- .github/workflows/lint.yml: CI pipeline with secrets-audit gate
