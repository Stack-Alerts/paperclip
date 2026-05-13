# BTCAAAAA-25464 — QA: Fix: Add rate limiting and dedup to Impact Gate sub-issue creation

**Status:** PASSED
**Verification date:** 2026-05-13
**Verified by:** QAEngineer

## Changes Verified

Two commits from CTO:

| Commit | Description |
|---|---|
| `d7fc8397` | Initial implementation: add rate limiting and dedup to blocking sub-issue creation |
| `95ade511` | Fix: refactor rate limiting into `_maybe_throttle()` closure with proper elapsed-time tracking; add throttle before dedup search; expand and add new tests |

## Implementation Summary

### Rate Limiting (`src/impact_gate/worker.py:519-529`)

- `_maybe_throttle()` closure ensures at least `BLOCKING_ISSUE_CREATE_INTERVAL` (1.0s) between API mutation calls
- Applied before: (a) dedup search API call, (b) blocking issue create API call
- Tracks `_last_create_time` via `nonlocal` to maintain state across FR and bug creation loops
- First call in a `process_issue()` run is always free (no delay)

### Deduplication (`src/impact_gate/worker.py:57-92`)

- `_build_dedup_key()` generates deterministic HTML comment marker: `<!-- dedup:impact-gate:{fix}:{item}:{type} -->`
- `_find_existing_blocking_issue()` searches existing issues for matching dedup key before creating a duplicate
- Applied in both FR and bug creation loops: skip create if existing blocking issue found

## Test Results

### Impact Gate Test Suite (140 tests)

All 140 tests passed. 53 worker tests specifically cover rate limiting and dedup.

**Rate limiting tests:**
- `test_rate_limiting_applied_between_creates` — 2 FR failures → 3 throttle calls
- `test_rate_limiting_across_fr_and_bug_loops` — 1 FR + 1 bug → 3 throttle calls across loops
- `test_rate_limiting_dedup_hit_skips_create` — dedup match → 0 extra throttle calls

**Dedup tests:**
- `test_fail_dedup_skips_duplicate` — existing blocking issue found → no duplicate
- `test_returns_issue_when_dedup_key_matches` — correct HTML comment key matching
- `test_returns_none_when_no_body_match` — no false positive
- `test_returns_none_on_api_error` — graceful degradation

**Resilience tests:**
- `test_create_blocking_issue_failure_continues_loop` — API failure for item 1 doesn't block item 2

### Coverage (impact_gate.worker: 92%)

## QA Verdict

**QA: PASS**

- Acceptance criteria: all met
- Rate limiting: `_maybe_throttle()` with 1.0s interval applied before all API mutations
- Deduplication: deterministic HTML-comment dedup key with paginated search
- Test coverage: comprehensive (92% worker coverage, all key paths tested)
- Regressions: none
- Sign-off: ready for next stage
