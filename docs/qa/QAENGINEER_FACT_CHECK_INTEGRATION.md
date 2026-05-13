# QAEngineer Fact-Check Integration

**Owner:** QAEngineer
**Status:** Active
**Related Issues:** BTCAAAAA-22887, BTCAAAAA-22886, BTCAAAAA-3223, BTCAAAAA-3225
**References:** `docs/qa/FACT_CHECK_PIPELINE.md` (TestManager-owned pipeline)

---

## 1. Purpose

Define the specific fact-checking step within QAEngineer's standard QA workflow. This is the QAEngineer's integration point with the broader Research Fact-Checking QA Pipeline owned by TestManager.

While TestManager owns the pipeline infrastructure (automated scans, routing matrix, quarterly sweeps), QAEngineer owns the **invocation gate** — ensuring every issue under review passes fact-check before release sign-off.

---

## 2. When Fact-Check Triggers (QAEngineer's Workflow)

Fact-checking is triggered in the following contexts during QAEngineer's review:

### 2.1 Standard QA Review — Every Issue

During every QA review heartbeat, QAEngineer runs:

```bash
python scripts/qa_fact_check_pipeline.py scan
```

This scans all `in_progress` issues for copy-touch content. If the scan returns flagged items, QAEngineer blocks sign-off until fact-check is resolved.

### 2.2 Manual Trigger — Suspicious Text Detected

During manual QA (UI testing, code review, checklist verification), if QAEngineer spots text that appears:
- Factually suspect (wrong values, outdated references)
- Misleading (implies capability that doesn't exist)
- Inconsistent with observed system behavior

QAEngineer immediately triggers fact-check by creating a child issue:

```json
POST /api/companies/{companyId}/issues
{
  "title": "Fact-check: <specific claim>",
  "description": "<claim text, location, concern>",
  "parentId": "<current QA issue id>",
  "assigneeAgentId": "<routed reviewer per matrix>",
  "labels": ["copy-touch", "fact-check"],
  "priority": "high",
  "status": "todo"
}
```

### 2.3 Release Gate — Mandatory Check

Before any release sign-off (as part of the Pre-Deployment Validation Checklist), QAEngineer verifies:
- Fact-check scan has been run on all issues in the release scope
- All flagged items have a `FACT CHECK: PASSED` comment from the assigned reviewer
- No unresolved fact-check child issues remain

### 2.4 Re-Review After Rework

When a previously failed fact-check is re-submitted:
1. Re-run `python scripts/qa_fact_check_pipeline.py verify BTCAAAAA-XXXX` on the fixed issue
2. Verify the reviewer has posted a new `FACT CHECK: PASSED` comment
3. Do not assume previous findings are resolved without re-verification

---

## 3. How Results Are Recorded

### 3.1 Triggering a Fact-Check (QAEngineer → Reviewer)

QAEngineer records the fact-check trigger as a comment on the current QA issue:

```
## Fact-Check Required

- **Issue under review**: BTCAAAAA-XXXX
- **Trigger**: [scan result / manual detection / release gate]
- **Claims to verify**: [list specific claims or "per scan output"]
- **Routed to**: [Reviewer Name] (@agentId)
- **Child issue**: [BTCAAAAA-XXX](/BTCAAAAA/issues/BTCAAAAA-XXX)
- **Expected SLA**: 30 min / 60 min (deep research)
```

### 3.2 Recording Results — Verdict Comment

QAEngineer records the fact-check outcome in the release gate comment (or QA verdict comment):

**If all facts pass:**

```markdown
### Fact-Check Status: PASSED

- Issue: BTCAAAAA-XXXX
- Reviewer: [Name]
- Verification method: [scan / manual review / reviewer comment]
- Claims verified: N
- Failures: 0
```

**If any fact fails:**

```markdown
### Fact-Check Status: FAILED

- Issue: BTCAAAAA-XXXX
- Reviewer: [Name]
- Failed claims: [list each with exact text and reason]
- Failure type(s): [false_claim | misleading_implication | outdated_information | missing_caveat | contradictory_text | unsubstantiated_numerical_claim]
- Child issue(s): [BTCAAAAA-XXX](/BTCAAAAA/issues/BTCAAAAA-XXX)
- Status: blocked — see child issue(s) for required fixes
```

### 3.3 Atomic Contract

The fact-check verdict follows the same atomic rule as the main QA verdict (per BTCAAAAA-1476):
- Post the fact-check comment first
- Then PATCH the issue status
- If either fails, roll back both

---

## 4. Integration with Release Gate

### 4.1 Pre-Deployment Validation Checklist Addition

The following items are added to the Pre-Deployment Validation Checklist (inserted between "Paper-Trading Validation" and "Locked Module Exception"):

```markdown
### Fact-Check Verification
- [ ] `python scripts/qa_fact_check_pipeline.py scan` run against all issues in release scope
- [ ] All flagged items have `FACT CHECK: PASSED` from assigned reviewer
- [ ] No unresolved fact-check child issues exist
- [ ] UI text reviewed for suspicious/outdated claims during manual QA
- [ ] Fact-check status recorded in release sign-off comment
```

### 4.2 Release Smoke Test Integration

The fact-check step runs alongside the UI smoke test suite:

```bash
# Step 1: Run fact-check scan
python scripts/qa_fact_check_pipeline.py scan

# Step 2: Run UI smoke tests
QT_QPA_PLATFORM=offscreen pytest tests/ui_qt -v --tb=short -m "smoke or qt_real"
```

### 4.3 Release Sign-Off Comment Template

The release smoke test verdict comment is extended to include fact-check status:

```
## Release Smoke Test

- Suite: `tests/ui_qt` (qt_real marker)
- Command: `QT_QPA_PLATFORM=offscreen pytest tests/ui_qt -v --tb=short`
- Result: PASS / FAIL
- Tests run: N
- Tests passed: N
- Tests failed: N (list failing tests if any)

### Fact-Check Status: PASSED / FAILED
- Issues scanned: N
- Items flagged: N
- Items cleared: N
- Unresolved: N

- Screenshot artifacts: [attach if available]
- Sign-off: QAEngineer [PASS/FAIL]
```

---

## 5. Related Documents

- `docs/qa/FACT_CHECK_PIPELINE.md` — TestManager-owned fact-check pipeline infrastructure
- BTCAAAAA-22886 — Parent: Research Fact-Checking in QA Pipeline
- BTCAAAAA-22887 — Define fact-check step in QA workflow
- BTCAAAAA-3223 — Enhance QA With Research Fact Checking
- BTCAAAAA-3225 — Content QA / Fact-Check Gate
