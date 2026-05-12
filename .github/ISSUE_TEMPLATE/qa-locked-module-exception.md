---
name: Locked Module Exception — QA Sign-Off Checklist
about: Mandatory QA checklist for approved locked-module exceptions (auto-created post-approval)
title: "[QA SIGN-OFF] Locked module exception — <module path>"
labels: lock-exception, qa-signoff
assignees: QAEngineer

---

## Exception Reference

- **Module path:** <!-- populated by automation -->
- **PR:** <!-- populated by automation -->
- **Approval ID:** <!-- populated by automation -->
- **Approved by:** <!-- populated by automation -->

---

## QA Checklist — Locked Module Exception

> All four checks **must** pass before this issue can close. If any check fails,
> comment with failure details and assign back to the CTO for resolution.

### 1. pytest passed (all tests, not just smoke)

- [ ] Paste CI run URL here
- [ ] CI run must include the full test suite, not a subset
- [ ] All tests green — no skipped-as-failure, no tolerated failures

**Evidence:**
```
<CI run URL>
```

### 2. UI path verified end-to-end

- [ ] Attach screenshot or log artifact
- [ ] Each modified UI component renders correctly
- [ ] No new console errors from changed modules

**Evidence:**
```
<screenshot filename or log artifact link>
```

### 3. Trade execution confirmed in dry-run (≥1 trade in known 24h window)

- [ ] Paste dry-run evidence
- [ ] At least 1 trade placed within the last 24 hours for a known strategy
- [ ] Trade appears in the optimizer trade ledger with expected parameters

**Evidence:**
```
<dry-run log excerpt or trade ledger entry>
```

### 4. Canary smoke test passed

- [ ] Paste canary test CI run URL
- [ ] `tests/bug_regression/test_canary_trade_execution.py` green
- [ ] Zero-trades regression confirmed — no masked replication of the original bug

**Evidence:**
```
<canary test CI run URL>
```

---

## Sign-Off

- [ ] **QAEngineer:** All four checklist items verified and passing. Exception approved for merge.
