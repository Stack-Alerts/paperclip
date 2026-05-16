# Hindsight Memory Payload — Security Posture 2026-05-14

Populated per BTCAAAAA-26731. Structured facts for Hindsight memory bank ingestion by SecurityAnalyst.

---

## Security Architecture

### Exchange Authentication

- **Mechanism**: HMAC-SHA256 signing via `src/itm/engine/binance_client.py:420-432`
- **Key loading**: `os.environ.get("BINANCE_TESTNET_API_KEY/SECRET")` — env vars only, no config files
- **API key sent as**: `X-MBX-APIKEY` HTTP header
- **Signature computed over**: URL-encoded query string (timestamp + recvWindow + params)
- **Replay protection**: `timestamp` (ms epoch) + `recvWindow=5000ms` (Binance server-side enforcement)
- **Default mode**: Testnet (`use_testnet=True`). Mainnet keys require CTO approval per `.env.example:547-549`
- **Paper trading fallback**: `PaperBinanceClient` — no-op drop-in, no credentials needed
- **Dry-run guard**: `_assert_testnet_env()` rejects placeholder values; `paper_trading=True` by default

### Secrets Management

- **Local**: `.env` file (gitignored, NOT tracked in git per `.gitignore:56,88`)
- **Template**: `.env.example` (tracked, placeholder-only values)
- **CI Gate**: `scripts/audit/secrets_audit.py` scans for AWS keys, API keys, secrets, Binance literals on every push/PR
- **No pre-commit hook**: Local secrets check only in CI, not pre-commit
- **Key rotation**: Runbook exists (`docs/runbooks/key-rotation.md`) but no automation

### Infrastructure Security

- **Module lock gate**: `scripts/lock_gate.py` + CI workflow prevents unauthorized changes to sensitive modules. Exceptions via `lock_gate_exceptions.json` with board approval. QA 4-item sign-off checklist required for unlocks.
- **Data quality gate**: Impact Gate validates fix→done issues for data quality compliance (100% coverage on 2026-05-14 scan)
- **Backup pipeline**: rclone (Google Drive) with encrypted config, OAuth deadman diagnostics, 4-hour GH Actions workflow
- **Database access**: PostgreSQL (optimizer_v3) with `ai_readonly` role (parameterized query engine, 9 tools)
- **Workers**: Touch Index bug/FR, Blast Radius, Impact Gate, Backup — all via systemd or GH Actions with env var injection

---

## Known Vulnerabilities & Assessments

### P0 — Resolved

| ID | Description | Resolution |
|----|-------------|------------|
| SEC-001 | AWS Crypto Lake S3 credentials (access key + secret) hardcoded in `test_lakeapi_data.py`, committed to git | Git history purged (`git filter-repo`), keys removed from source. Pending: IAM rotation (blocked on AWS admin access) |

### P1 — Active

| ID | Description | Status |
|----|-------------|--------|
| SEC-010 | Real API keys in local `.env` (OpenRouter, Paperclip JWT, GitHub PAT) | ACCEPTED — `.env` is gitignored, local dev only, not a repo threat |

### P2 — Open

| ID | Description | Recommended Action |
|----|-------------|-------------------|
| SEC-004 | No dependency vulnerability scanning (no safety/bandit/snyk in CI) | Add `pip-audit` or `safety` CI job |
| SEC-014 | No automated key rotation for exchange/Paperclip/GitHub credentials | Implement automated rotation schedule or integrate Paperclip Secrets API |
| SEC-005 | Binance HMAC secret stored as plaintext `str` in memory | ACCEPTED risk for server-side process |

### P3 — Open

| ID | Description | Recommended Action |
|----|-------------|-------------------|
| SEC-007 | No pre-commit hook for local secrets audit | Add `.git/hooks/pre-commit` running `secrets_audit.py` |

### Confirmed Safe

| ID | Assessment |
|----|-----------|
| SEC-008 | Zero MEV/DeFi/DEX/cross-chain code — project is CEX-only (Binance Futures) |
| SEC-011 | HMAC-SHA256 implementation matches Binance spec |
| SEC-013 | CI secrets audit gate active and passing |
| SEC-016 | Rclone encrypted config handles OAuth tokens securely |

---

## Threat Model Summary

### Attack Surface

1. **Exchange API credentials**: Only accessible via env vars on the host running the execution engine. No git exposure.
2. **Paperclip API tokens**: JWT-based, short-lived (auto-injected per run). Stored in `.env` for workers.
3. **GitHub PAT**: Fine-grained, Actions read-only. Stored in `.env`. Used by deadman monitors.
4. **OpenRouter API key**: AI model access. Stored in `.env`. No commit exposure.
5. **PostgreSQL**: Local-only (`localhost:5432`). `ai_readonly` role for AI Consultant.
6. **Rclone**: OAuth tokens in encrypted config, not in git.
7. **LakeAPI S3**: Previously exposed (SEC-001), now cleaned from git. IAM rotation pending.

### Defense-in-Depth

- Layer 1 (Repo): `.gitignore` excludes `.env`, secrets audit CI gate, lock gate
- Layer 2 (CI): Secrets scan on push/PR, lock gate blocks unauthorized module changes
- Layer 3 (Runtime): Env vars only for credentials, no hardcoded secrets in tracked source
- Layer 4 (Network): Binance REST + WebSocket only, no smart contract interaction
- Layer 5 (Monitoring): Impact gate, blast radius worker, deadman switches, watchdog

---

## Decisions & Standards

1. **All credentials from env vars** — never from source code, config files, or command-line args
2. **Mainnet keys require CTO approval** — enforced by `.env.example` convention
3. **Testnet by default** — all Binance client instantiation defaults to testnet
4. **Paper trading fallback** — no real order execution without explicit opt-in
5. **Secrets audit on CI** — `secrets_audit.py` blocks merges on finding hardcoded credentials
6. **No MEV/DeFi exposure** — by design; project is CEX-only
7. **Lock gate for sensitive modules** — board-approved exceptions required for bypass
8. **Encrypted rclone config** — OAuth tokens not in plaintext
9. **Hindsight memory** — security assessments, vulnerability findings, and architecture decisions retained in memory bank (this document)

---

## Pending Security Actions

| Action | Owner | Blocker | Issue |
|--------|-------|---------|-------|
| Rotate AWS IAM keys (SEC-001) | CTO | AWS admin access | BTCAAAAA-15103 |
| Add dependency vulnerability scanning | SecurityAnalyst | Scheduling | None (proposed) |
| Add pre-commit secrets audit hook | SecurityAnalyst | Scheduling | None (proposed) |
| Implement automated key rotation | CTO / AutomationEngineer | Design | None (proposed) |
| Source real values for 6 placeholder secrets | SecurityAnalyst | Pending | BTCAAAAA-26527 |
