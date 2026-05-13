# BTCAAAAA-15027: Impact Gate false positive: auto-generated Blast Radius worker template issues blocked

**Status**: CLOSED — fix verified and deployed  
**Agent**: PlatformEngineer  
**Date**: 2026-05-13

## Root Cause

`_is_fix_issue` in `src/blast_radius/worker.py:111` used Python substring matching (`any(kw in title_lower for kw in ...)`) against issue titles. This caused false positives for auto-generated Blast Radius worker template/comment issues whose titles contained "fix", "bug", "regression", or "hotfix" as substrings (e.g., "Impact Gate: scan for fix issues done").

These false positives caused the Impact Gate scan-done process to:
1. Incorrectly classify non-fix issues as fix issues
2. Attempt Impact Gating on them
3. Create false blocking issues when tests failed or weren't found

## Fix

**Commit `2268ba0f`**: Changed `_is_fix_issue` to use `re.match(r"(?:fix|bug|bugfix|regression|hotfix)\b", title, re.IGNORECASE)` — the keyword must be the **first word** of the title, not anywhere in the string.

**Commit `554e7f45`**: Applied the same fix to `impact_gate/worker.py`'s standalone instance.

## Consumers Verified

| Consumer | Source of `_is_fix_issue` | Status |
|---|---|---|
| `src/blast_radius/worker.py` | Canonical definition | ✅ Fixed |
| `scripts/scan_fix_issues_done.py` | Imports from `blast_radius.worker` | ✅ Fixed |
| `scripts/run_impact_gate_worker.py` | Imports from `blast_radius.worker` | ✅ Fixed |

## Regression Tests

| Test file | Description | Status |
|---|---|---|
| `tests/test_blast_radius/test_worker.py::TestIsFixIssue::test_substring_fix_in_title_is_not_false_positive` | Blast Radius worker | ✅ 15 passed |
| `tests/test_impact_gate/test_scan_done.py::TestIsFixIssue::test_substring_fix_in_title_is_not_false_positive` | Scan-done script | ✅ 9 passed |
| `tests/test_impact_gate/test_runner.py::TestFetchInReviewFixIssues::test_substring_fix_in_title_is_not_false_positive` | Runner script | ✅ 11 passed |
| `tests/bug_regression/test_btcaaaaa_20256_regression.py` | Bug regression re-export | ✅ 56 passed |

## Commits

```
2268ba0f fix(blast-radius): narrow fix/bug issue title matching to first-word pattern
554e7f45 fix(impact-gate): narrow fix/bug issue title matching to first-word pattern
3eb40a12 test(impact-gate): add regression test for false-positive fix issue title matching
c771a7d9 test(impact-gate): add false-positive regression test for _fetch_in_review_fix_issues
```

All commits present on `origin/main`.
