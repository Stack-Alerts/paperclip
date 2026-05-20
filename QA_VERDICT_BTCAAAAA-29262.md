# QA Verification Report: BTCAAAAA-29262

**Issue:** QA: verify scan-done data-error fix (BTCAAAAA-29260)
**Branch:** fix/BTCAAAAA-29260-scan-done-data-error
**Date:** 2026-05-19
**Status:** ✅ PASS (Steps 1-4 complete; Step 5 requires post-merge monitoring)

---

## Verification Results

### Step 1: Producer Script Verification ✅

**Command:** `python3 scripts/scan_fix_issues_done.py --json-summary`

**Results:**
- ✅ JSON output includes `ungated_issues` field (list)
- ✅ JSON output includes `dry_run` field (boolean)
- **Output Sample:**
  ```json
  {
    "timestamp": "2026-05-19T19:55:12.678647Z",
    "total_done_fix_issues": 299,
    "gated": {"pass": 84, "fail": 33, "bypassed": 0, "error": 39, "skipped": 113},
    "ungated_count": 30,
    "ungated_issues": [...30 issue objects...],
    "last_24h": 0,
    "days_back": null,
    "dry_run": false
  }
  ```

### Step 2: Invariant Verification ✅

**Requirement:** `ungated_count == len(ungated_issues)`

**Test Results:**
- ✅ ungated_count: 30
- ✅ len(ungated_issues): 30
- ✅ Invariant satisfied: 30 == 30

### Step 3: Consumer (scan_done_alert.py) Verification ✅

**Test Case 3a: Missing ungated_issues field**

Created fixture with `ungated_count > 0` but no `ungated_issues` field:
```json
{
  "ungated_count": 3,
  "total_done_fix_issues": 10,
  "gated": {...},
  "last_24h": 5,
  "dry_run": false
}
```

**Results:**
- ✅ DATA ERROR alert created with `priority: critical`
- ✅ **idempotencyKey is date-only:** `impact-gate-scan-done-error:2026-05-19` (no count suffix)
- ✅ Body includes diagnostic information
- ✅ Diagnosis correctly identifies missing field
- ✅ Scan output top-level shape diagnostic rendered

**Sample Alert Payload:**
```json
{
  "title": "Impact Gate Scan-Done DATA ERROR — 2026-05-19 (3 missing)",
  "description": "## ⚠️ Data Population Error\n\nThe Impact Gate scan-done found **ungated_count > 0** but **ungated_issues list is empty**.\nThis indicates a data serialization or buffering bug in the scan pipeline.\n\n**Reported ungated_count:** 3\n**Ungated issues list:** empty (length=0)\n**Diagnosis:** `ungated_issues` field is **missing** from scan output (likely a stale producer that predates BTCAAAAA-28999).\n\n### Scan output top-level shape\n\n- `timestamp`: '2026-05-19T19:53:29.902594Z'\n- `total_done_fix_issues`: 10\n- `gated`: dict (keys=['bypassed', 'error', 'fail', 'pass', 'skipped'])\n- `ungated_count`: 3\n- `last_24h`: 5\n- `days_back`: None\n- `dry_run`: False",
  "priority": "critical",
  "status": "todo",
  "idempotencyKey": "impact-gate-scan-done-error:2026-05-19"
}
```

**Test Case 3b: Empty ungated_issues list**

Created fixture with field present but empty:
```json
{
  "ungated_count": 2,
  "ungated_issues": [],
  "total_done_fix_issues": 10,
  "gated": {...},
  "dry_run": false
}
```

**Results:**
- ✅ DATA ERROR alert created with `priority: critical`
- ✅ **idempotencyKey is date-only:** `impact-gate-scan-done-error:2026-05-19` (no count suffix)
- ✅ Diagnosis correctly identifies empty-list case
- ✅ Dry-run mode works correctly (no POST performed)

### Step 4: Regression Tests ✅

**Command:** `pytest tests/test_impact_gate/test_scan_result_shape.py tests/test_impact_gate/test_scan_done_alert.py -v`

**Test Coverage:**
- `test_scan_result_shape.py`: 4 tests
  - ✅ test_result_includes_ungated_issues_field
  - ✅ test_ungated_count_matches_ungated_issues_length
  - ✅ test_partial_gated_partial_ungated
  - ✅ test_dry_run_field_persisted

- `test_scan_done_alert.py`: 20 tests
  - ✅ TestFindTodaysAlert (4 tests)
  - ✅ TestDataErrorGuard (5 tests covering both missing-field and empty-list modes)
  - ✅ TestCreateAlert (11 tests)

**Results:** ✅ **24/24 tests PASSED**

---

## Verification Summary

| Criterion | Status |
|-----------|--------|
| Producer includes `ungated_issues` | ✅ PASS |
| Producer includes `dry_run` | ✅ PASS |
| Invariant: `ungated_count == len(ungated_issues)` | ✅ PASS |
| Consumer detects missing-field error | ✅ PASS |
| Consumer detects empty-list error | ✅ PASS |
| DATA ERROR alert marked as CRITICAL | ✅ PASS |
| idempotencyKey is date-only (no count suffix) | ✅ PASS |
| Diagnostic information in alert body | ✅ PASS |
| Dry-run flag respected | ✅ PASS |
| All regression tests pass (24/24) | ✅ PASS |

---

## Step 5: Post-Merge Monitoring (Pending)

**Requirement:** After the PR merges to main, monitor the next 3 consecutive scheduled `impact-gate-scan-done` CI runs and confirm no DATA ERROR alert fires (unless real data corruption occurs).

**Status:** ⏳ Requires PR merge and post-deployment monitoring

**Monitoring Plan:**
1. Merge fix/BTCAAAAA-29260-scan-done-data-error to main
2. Watch the next 3 scheduled scan-done runs in CI
3. Verify no DATA ERROR alerts fire (idempotencyKey `impact-gate-scan-done-error:*`)
4. Update issue with final monitoring results

---

## Deployment Readiness

✅ **QA: PASS** — All pre-deployment validation complete
- Code changes reviewed and tested
- Invariants verified at producer and consumer
- Defensive guard properly detects both error modes
- All regression tests passing
- Ready for merge and deployment

**Remaining Action:** Monitor 3 post-merge CI runs (Step 5) to confirm no false-positive alerts in production data.
