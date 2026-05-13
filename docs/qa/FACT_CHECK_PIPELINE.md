# QA Research Fact-Check Pipeline

**Owner:** TestManager | **Status:** Active | **Issues:** BTCAAAAA-22886, BTCAAAAA-3223, BTCAAAAA-25560
**Integration:** `docs/qa/QAENGINEER_FACT_CHECK_INTEGRATION.md` (QAEngineer integration)
**Script:** `scripts/qa_fact_check_pipeline.py`

---

## 1. Overview

The Fact-Check Pipeline is the automated infrastructure for verifying factual accuracy of all user-facing text in the BTC-Trade-Engine: tooltips, UI labels, data annotations, educational claims, strategy descriptions, and error messages.

TestManager owns the pipeline infrastructure — the script, routing matrix, automated scans, and quarterly sweep schedule. QAEngineer owns the **invocation gate** (triggering fact-checks during review). Reviewers (GeneralResearcher, StrategyResearcher, SecurityAnalyst) own the research and verdict.

---

## 2. Scope

All text surfaces that reach users or agents:

| Surface | Example | Reviewer |
|---------|---------|----------|
| Tooltips | "RSI > 70 indicates overbought" | GeneralResearcher |
| UI labels | "NautilusTrader Backend: Connected" | GeneralResearcher |
| Data annotations | Chart annotations, signal descriptions | StrategyResearcher |
| Educational claims | "Zigzag detects 5% reversals" | GeneralResearcher |
| Strategy descriptions | "EMA crossover strategy (fast=12, slow=26)" | StrategyResearcher |
| Error messages | "Insufficient data for 15m bar" | GeneralResearcher |
| Security labels | "API key encrypted at rest" | SecurityAnalyst |
| Onboarding text | Training manual claims | GeneralResearcher |
| README / docs | Project README, user guide | GeneralResearcher |

---

## 3. Reviewer Routing Matrix

### 3.1 Routing Logic

The pipeline's `_route()` function maps issue content keywords to reviewer agent IDs:

| Keyword(s) | Reviewer Agent | Agent ID |
|------------|---------------|----------|
| `btc`, `blockchain`, `exchange`, `nautilus` | GeneralResearcher | `df7b4035-e034-467e-af06-d25c869c810f` |
| `strategy`, `signal`, `indicator` | StrategyResearcher | `e3fcab65-c9a3-45bd-97e8-5145d3d6db5e` |
| `security`, `risk` | SecurityAnalyst | `840eb9ff-f746-47da-9fdc-f0ec9d071155` |
| *(no match)* | TestManager (default) | `d53906e4-5660-4a47-bef4-148a69979b20` |

The first keyword match wins. Order is: btc, blockchain, exchange, nautilus, strategy, signal, indicator, security, risk. If no keyword matches, the issue routes to TestManager as default.

### 3.2 Updating the Matrix

**When to update:**
- New agent joins the org with a relevant expertise domain
- Existing reviewer's scope changes
- New keyword domain emerges in product text

**How to update:**
1. Edit `scripts/qa_fact_check_pipeline.py` lines 11–21 (the `AGENTS` dict and `ROUTING` dict).
2. Validate with: `python scripts/qa_fact_check_pipeline.py route <issue-id>`
3. Update this document's matrix table above to match.

---

## 4. Pipeline Commands

### 4.1 `scan` — Scan In-Progress Issues

```bash
python scripts/qa_fact_check_pipeline.py scan
python scripts/qa_fact_check_pipeline.py scan --assignee <agent-id>
```

**Behavior:**
1. Fetches all issues with `status=in_progress` from the API.
2. If `--assignee` is provided, filters to only issues assigned to that agent.
3. Checks each issue's title + description for keywords: `tooltip`, `label`, `copy`, `text`, `message`, `description`.
4. If keywords found, routes the issue to a reviewer via the routing matrix.
5. Outputs JSON with timestamp, scan count, flagged count, and flagged items.

**Output format:**
```json
{
  "timestamp": "2026-05-13T12:00:00.000000+00:00",
  "scanned": 15,
  "flagged": 3,
  "items": [
    {"id": "BTCAAAAA-XXXX", "title": "Fix RSI tooltip", "reviewer": "df7b4035-..."},
    ...
  ]
}
```

**Typical use cases:**
- QAEngineer during standard QA review heartbeat (QAENGINEER_FACT_CHECK_INTEGRATION.md 2.1)
- Release gate pre-deployment scan (QAENGINEER_FACT_CHECK_INTEGRATION.md 2.3)
- TestManager quarterly sweep

### 4.2 `verify` — Check a Specific Issue

```bash
python scripts/qa_fact_check_pipeline.py verify BTCAAAAA-XXXX
```

**Behavior:**
1. Fetches the issue by ID.
2. Routes it via the reviewer matrix.
3. Outputs a JSON response showing the reviewer assignment and `verdict: "PENDING"`.

**Output format:**
```json
{
  "issue": "BTCAAAAA-XXXX",
  "reviewer": "df7b4035-...",
  "verdict": "PENDING"
}
```

### 4.3 `route` — Preview Routing Assignment

```bash
python scripts/qa_fact_check_pipeline.py route BTCAAAAA-XXXX
```

**Behavior:**
1. Fetches the issue by ID.
2. Routes it via the review matrix.
3. Outputs the human-readable reviewer name.

**Output format:**
```json
{
  "issue": "BTCAAAAA-XXXX",
  "routed_to": "general_researcher"
}
```

**Use case:** Pre-flight check before assigning a fact-check child issue to determine the correct reviewer.

---

## 5. Failure Criteria

When a reviewer evaluates a claim, they classify each failure into one of these categories:

| # | Criterion | Description | Example |
|---|-----------|-------------|---------|
| 1 | **False claim** | Statement is objectively wrong | "NautilusTrader v1.221.0" when installed version is 1.226.0 |
| 2 | **Misleading implication** | True statement that implies a falsehood | "45GB historical data" when data includes duplicates / cache |
| 3 | **Outdated information** | Was correct but no longer accurate | Reference to a file path that has been moved |
| 4 | **Missing caveat** | Fails to note limitations or conditions | "Backtest accuracy 99%" without mentioning look-ahead bias risk |
| 5 | **Contradictory text** | Two statements that conflict | Line 29 says "45GB" but line 120 says "308GB" |
| 6 | **Unsubstantiated numerical claim** | Number without evidence or methodology | "2,500+ lines of institutional-grade code" |

---

## 6. Workflow (End-to-End)

### 6.1 Trigger

Triggers originate from:
- **QAEngineer scan** (highest frequency — every standard QA review) — see QAENGINEER_FACT_CHECK_INTEGRATION.md 2.1
- **Manual detection** by any agent during code review, UI testing, or documentation work
- **TestManager quarterly sweep** — full pipeline scan of all active issues and docs
- **Release gate** — mandatory pre-deployment scan (see QAENGINEER_FACT_CHECK_INTEGRATION.md 4.1)

### 6.2 Route

The trigger either:
- Uses `python scripts/qa_fact_check_pipeline.py route <issue-id>` to determine the correct reviewer
- Or relies on the scan output which already includes routed reviewer IDs

### 6.3 Review

The assigned reviewer:
1. Reads the flagged claim(s) in context (issue title, description, linked files).
2. Researches the claim against the actual codebase, data, system behavior, or external reference.
3. For each claim, assigns PASS or FAIL with a specific failure criterion (see 5).
4. Posts a structured verdict comment on the issue.

### 6.4 Verdict Comment

**PASS verdict:**
```
COPY QA: PASSED

Verified claims:
- <claim 1> — PASS
- <claim 2> — PASS
```

**FAIL verdict:**
```
COPY QA: FAILED

Failed claims:
- <claim 1> — FAIL (false_claim): <reason>
- <claim 2> — FAIL (outdated_information): <reason>

Child issues created:
- BTCAAAAA-XXXX: Fix <claim 1> in <location>
```

### 6.5 Remediation

If FAILED:
1. Create child issue(s) assigned to the fix owner (usually the original author or DocWriter for doc fixes).
2. Set child issue label `copy-touch`.
3. Fix the claims in the source documents or code.
4. Reviewer re-verifies the fix.
5. Reviewer posts new `COPY QA: PASSED` comment.

### 6.6 Gate Clearance

Gate clears when:
1. All flagged issues have a `COPY QA: PASSED` or `FACT CHECK: PASSED` comment from the assigned reviewer.
2. No unresolved fact-check child issues remain.
3. If the fact-check was a release gate requirement, QAEngineer records the status in the release sign-off comment (see QAENGINEER_FACT_CHECK_INTEGRATION.md 4.3).

---

## 7. Quarterly Sweep (TestManager)

Every quarter, TestManager runs a full pipeline sweep:

1. **Full scan:** `python scripts/qa_fact_check_pipeline.py scan` — covers all in-progress issues.
2. **Documentation audit:** Spot-check key docs against actual system state (README, training-manual, user-guide).
3. **Matrix review:** Check if any new agents or keyword domains should be added to the routing matrix.
4. **Script audit:** Verify the pipeline script still works against the current API.
5. **Report:** Post a summary in the company channel with findings and any child issues created.

---

## 8. Pipeline Configuration

### 8.1 Constants in `scripts/qa_fact_check_pipeline.py`

| Constant | Value | Description |
|----------|-------|-------------|
| `COMPANY_ID` | `73419cf3-bd37-4a7c-8782-311ccb47fced` | Company UUID for API calls |
| `API_BASE` | `http://127.0.0.1:3100` | Local API base URL |
| `AGENTS` | Dict of name to UUID | Maps agent roles to their agent IDs |
| `ROUTING` | Dict of keyword to agent ID | Maps content keywords to reviewer agent IDs |

### 8.2 Agent IDs Reference

| Role | Agent ID |
|------|----------|
| GeneralResearcher | `df7b4035-e034-467e-af06-d25c869c810f` |
| StrategyResearcher | `e3fcab65-c9a3-45bd-97e8-5145d3d6db5e` |
| SecurityAnalyst | `840eb9ff-f746-47da-9fdc-f0ec9d071155` |
| TestManager | `d53906e4-5660-4a47-bef4-148a69979b20` |

---

## 9. Extending the Pipeline

### 9.1 Adding a New Keyword Route

1. Add keyword to agent mapping to the `ROUTING` dict (line 17-21).
2. If the agent is new, add to `AGENTS` dict (line 11-16) with the agent's UUID.
3. Update this document's 3.1 matrix.
4. Run validation: `python scripts/qa_fact_check_pipeline.py route <known-issue>`.

### 9.2 Adding a New Subcommand

New subcommands are added via `argparse` in the `main()` function (line 71-78):
1. Define a new subparser with `s.add_parser("<name>")`.
2. Add arguments with `.add_argument()`.
3. Define a `cmd_<name>()` function and add it to the dispatch dict in `main()`.

---

## 10. Script Technical Reference

### 10.1 Dependencies

- Python 3.10+
- Standard library only (`argparse`, `json`, `sys`, `datetime`, `urllib.request`)
- No external packages required

### 10.2 API Dependencies

The pipeline communicates with the local Paperclip API at `http://127.0.0.1:3100`:
- `GET /api/companies/{companyId}/issues?status=in_progress` — list issues by status
- `GET /api/issues/{issueId}` — get a single issue

### 10.3 Error Handling

The script does not implement retry logic. API failures (`urlopen` errors) propagate as exceptions. Run within a monitored context (CI or watchdog) for production use.

---

## 11. Role Boundaries

| Role | Owns |
|------|------|
| **TestManager** | Pipeline infrastructure, routing matrix, script maintenance, quarterly sweeps, default reviewer |
| **QAEngineer** | Invocation gate (triggering fact-checks during review), recording results in release sign-off |
| **GeneralResearcher** | BTC/Nautilus/exchange/blockchain fact research and verdict |
| **StrategyResearcher** | Strategy/signal/indicator fact research and verdict |
| **SecurityAnalyst** | Security/risk claim fact research and verdict |
| **DocWriter** | Fixing doc inaccuracies flagged by fact-checks |

---

## 12. Related Documents

- `docs/qa/QAENGINEER_FACT_CHECK_INTEGRATION.md` — QAEngineer integration with this pipeline
- `docs/qa/BTCAAAAA-22893-factual-accuracy-audit.md` — Example audit report (README + training-manual.md)
- `scripts/qa_fact_check_pipeline.py` — Pipeline implementation
- BTCAAAAA-22886 — Parent: Research Fact-Checking in QA Pipeline
- BTCAAAAA-22887 — Define fact-check step in QA workflow
- BTCAAAAA-3223 — Enhance QA With Research Fact Checking
- BTCAAAAA-3225 — Content QA / Fact-Check Gate
