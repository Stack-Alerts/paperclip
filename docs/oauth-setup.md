# OAuth & Credential Setup Guide

**Owner:** DocWriter / PlatformEngineer
**Audience:** Trade Engineers, Platform Engineers, AI Agents
**Last Updated:** 2026-05-12

## Overview

This document describes how to obtain, configure, and rotate credentials for all external services used by the BTC Trade Engine.

### Service Credential Map

| Service | Purpose | Env Variables | Security Level |
|---------|---------|---------------|----------------|
| LakeAPI | BTC/USDT market data via S3 | `LAKEAPI_KEY`, `LAKEAPI_SECRET`, `LAKEAPI_REGION` | Confidential |
| Binance Testnet | Paper trading / integration tests | `BINANCE_TESTNET_API_KEY`, `BINANCE_TESTNET_API_SECRET` | Internal |
| Binance Mainnet | Live production trading | `BINANCE_MAINNET_API_KEY`, `BINANCE_MAINNET_API_SECRET` | **Critical** |
| OpenRouter | AI-enhanced recommendations | `OPENROUTER_API_KEY` | Confidential |
| Paperclip API | Touch Index, Blast Radius, Impact Gate workers | `PAPERCLIP_API_KEY`, `PAPERCLIP_COMPANY_ID` | Confidential |
| PostgreSQL | Strategy database | `POSTGRES_USER`, `POSTGRES_PASSWORD` | Confidential |

---

## 1. LakeAPI (Market Data)

**Required for:** All data acquisition operations via `src/data_manager/`.

### 1.1 Obtain Credentials

1. Sign up at [cryptolake.com](https://cryptolake.com)
2. Navigate to **Settings → API Keys**
3. Generate an access key / secret pair
4. Note your assigned S3 region (usually `eu-west-1`)

### 1.2 Configure

```ini
LAKEAPI_KEY=your_access_key_here
LAKEAPI_SECRET=your_secret_key_here
LAKEAPI_REGION=eu-west-1
LAKEAPI_LIMIT_GB=300
```

### 1.3 Usage Limits

- Default plan: 300 GB/month transfer
- Monitor via `LAKEAPI_LIMIT_GB` — the application will warn before exceeding the configured limit
- Exceeding the plan limit may incur overage charges from LakeAPI

### 1.4 Rotation

```bash
# 1. Generate new key pair at cryptolake.com
# 2. Update .env
# 3. Verify connectivity
python -c "
from src.data_manager.lake_api import LakeAPIClient
client = LakeAPIClient()
print('LakeAPI connectivity OK:', client.check_connection())
"
```

---

## 2. Binance API (Exchange)

### 2.1 Testnet (Paper Trading)

**Required for:** `run_testnet_dry_run.py`, integration tests, ITM dry-run runner.

#### Obtain

1. Go to [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with GitHub account (or register)
3. Navigate to **API Management** → **Create API Key**
4. Copy both API Key and Secret Key

#### Configure

```ini
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here
```

#### Verify

```bash
python -c "
from src.itm.engine.binance_client import BinanceClient
client = BinanceClient.from_env(use_testnet=True)
balance = client.get_balance()
print('Testnet balance:', balance)
"
```

#### Testnet Limitations

- USDT Futures only (no spot or coin-margined)
- Position limits apply (see testnet docs)
- Order book depth may differ from mainnet
- **The dry run runner hard-codes `use_testnet=True`** — mainnet override raises `ValueError`

### 2.2 Mainnet (Live Trading)

**⚠️ CRITICAL: CTO approval required before mainnet keys are set.**

#### Approval Gate

1. File a request via the lock gate exception process (see `docs/runbook-module-lock.md`)
2. CTO must explicitly sign off in a Paperclip issue
3. Only uncomment mainnet keys after the sign-off issue is closed

#### Obtain

1. Log in to [binance.com](https://binance.com)
2. Go to **API Management** → **Create API**
3. Restrict to **USDT-M Futures** only
4. Disable withdrawals (withdrawal permission must remain unchecked)
5. Set IP whitelist to the deployment server's public IP
6. Save the API Key and Secret Key — the secret key is only shown once

#### Configure

```ini
# CTO APPROVAL REQUIRED — do not uncomment without sign-off
# BINANCE_MAINNET_API_KEY=live_api_key_here
# BINANCE_MAINNET_API_SECRET=live_api_secret_here
```

#### Safety Checklist

- [ ] API key IP-restricted to deployment server
- [ ] Withdrawal permission **disabled**
- [ ] Trading restricted to USDT-M Futures only
- [ ] Rate limits understood (1200 weight per minute)
- [ ] Emergency kill-switch procedure documented
- [ ] Maximum position size configured in `.env`

#### Key Management Rules

- **Never commit mainnet keys to git** — `.env` is in `.gitignore`
- **Never share mainnet keys via chat, email, or issue comments**
- **Rotate mainnet keys every 90 days** (or immediately after a security incident)
- **Test with testnet first** — always validate new strategies on testnet before mainnet

---

## 3. OpenRouter (AI Recommendations)

**Optional:** Provides AI-enhanced strategy recommendations.

### 3.1 Obtain

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Navigate to **Keys**
3. Create a new API key
4. Add credit to your account (pay-as-you-go)

### 3.2 Configure

```ini
OPENROUTER_API_KEY=sk-or-v1-your_key_here
AI_MODEL=anthropic/claude-4.5-sonnet
```

### 3.3 Verify

```bash
python -c "
from src.ai_consultant.client import AIConsultantClient
client = AIConsultantClient()
print('AI connectivity OK:', client.check_health())
"
```

### 3.4 Cost Monitoring

- Track usage at [openrouter.ai/activity](https://openrouter.ai/activity)
- Set spending limits in the OpenRouter dashboard
- The application logs per-request token usage

---

## 4. Paperclip API (Project Management)

**Required for:** Touch Index workers, Blast Radius worker, Impact Gate worker.

### 4.1 Obtain

1. Log in to your Paperclip instance (self-hosted or cloud)
2. Go to **Settings → API Keys**
3. Generate a new Bearer token
4. Copy the Company UUID from the company settings page URL

### 4.2 Configure

```ini
PAPERCLIP_API_URL=https://api.paperclip.example.com
PAPERCLIP_API_KEY=your_paperclip_api_key_here
PAPERCLIP_COMPANY_ID=00000000-0000-0000-0000-000000000000
```

### 4.3 Verify

```bash
python -c "
from src.touch_index.paperclip_client import PaperclipClient
client = PaperclipClient()
print('Paperclip connectivity OK:', client.check_connection())
"
```

---

## 5. PostgreSQL Database

### 5.1 Initial Setup

Follow the PostgreSQL setup in [User Guide](user-guide.md#12-installation).

### 5.2 Credential Configuration

```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=optimizer_v3
POSTGRES_USER=optimizer_admin
POSTGRES_PASSWORD=secure_password_change_me

# AI read-only role (separate password)
AI_READONLY_PASSWORD=change_me_ai_readonly
```

### 5.3 Password Guidelines

- Minimum 16 characters
- Mix of uppercase, lowercase, digits, and special characters
- Use different passwords for `POSTGRES_PASSWORD` and `AI_READONLY_PASSWORD`
- Store in a password manager (e.g., Bitwarden, 1Password)

---

## 6. Security Best Practices

### 6.1 .env File Security

```bash
# .env is already in .gitignore — verify
grep "^\.env$" .gitignore

# Restrict file permissions
chmod 600 .env

# Never copy .env to world-readable locations
# Never paste .env contents into issues or chat
```

### 6.2 Credential Rotation Schedule

| Credential | Rotation Frequency | Trigger |
|------------|-------------------|---------|
| Binance testnet keys | Every 90 days | Calendar reminder |
| Binance mainnet keys | Every 90 days | Calendar reminder + CTO approval |
| LakeAPI keys | Every 180 days | Calendar reminder |
| OpenRouter API key | Every 180 days | Calendar reminder |
| Paperclip API key | Every 180 days | Calendar reminder |
| PostgreSQL passwords | Every 180 days | Calendar reminder |

### 6.3 Incident Response: Leaked Credentials

If credentials are accidentally exposed (e.g., committed to git, posted in chat):

1. **Immediately** revoke the credential at the source (Binance / LakeAPI / OpenRouter / Paperclip)
2. **Rotate** to a new credential
3. **Audit** git history for the leaked credential:
   ```bash
   git log --all --oneline --diff-filter=A -- .env
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   ```
4. **Notify** the CTO and Security Officer

### 6.4 Environment Separation

| Environment | Binance | Data Source | Risk Level |
|-------------|---------|-------------|------------|
| Development | Testnet | LakeAPI (limited) | Low |
| Testing | Testnet | LakeAPI (cached) | Low |
| Staging | Testnet | LakeAPI | Medium |
| Production | **Mainnet** | LakeAPI | **High** |

---

## Appendix A: Credential Health Check

Run this to verify all configured services:

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

checks = {
    'LakeAPI': all([os.getenv('LAKEAPI_KEY'), os.getenv('LAKEAPI_SECRET')]),
    'Binance Testnet': all([os.getenv('BINANCE_TESTNET_API_KEY'), os.getenv('BINANCE_TESTNET_API_SECRET')]),
    'OpenRouter': bool(os.getenv('OPENROUTER_API_KEY')),
    'Paperclip': all([os.getenv('PAPERCLIP_API_KEY'), os.getenv('PAPERCLIP_COMPANY_ID')]),
    'PostgreSQL': all([os.getenv('POSTGRES_USER'), os.getenv('POSTGRES_PASSWORD')]),
}
for name, ok in checks.items():
    status = '\033[92mOK\033[0m' if ok else '\033[91mMISSING\033[0m'
    print(f'  {status} {name}')
"
```

## Appendix B: .env Template Reference

The canonical template is at `.env.example`. **Always use this as reference** when setting up a new environment. Do not guess variable names.
