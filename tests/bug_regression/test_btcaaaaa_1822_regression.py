"""
Regression tests for BTCAAAAA-1822: emit --json-summary before SystemExit in
bug worker no-issues path.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1822
Fixed in commit: 462c1b06
Component: src/touch_index/__main__.py, tests/test_touch_index/test_bug_worker.py

Root cause: The bug worker's no-issues early-return path in _run_bug_cli()
skipped --json-summary emission when --validate failed.  The --json-summary
was only emitted on the pass branch, so validation-failure exit never
produced the expected JSON output.  Same fix applied to the FR worker's
no-issues path for consistency.

Fix:
- In _run_bug_cli() and _run_fr_cli(): emit --json-summary with quality
  report before raising SystemExit(1) when --validate fails with no issues.
- Added test_main_validate_no_issues_failed_with_json_summary to TestMain
  covering the --json-summary --validate failure edge case.

This file re-exports the existing TestMain unit tests from
tests/test_touch_index/test_bug_worker.py so the Impact Gate runner can
discover them by issue ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1822"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
)
