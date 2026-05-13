"""
Regression tests for BTCAAAAA-1789: reorder validate before json-summary in bug
worker polling path.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1789
Fixed in commit: 674486f2
Component: src/touch_index/__main__.py, tests/test_touch_index/test_bug_worker.py

Root cause: The bug worker's polling path emitted --json-summary before running
--validate, so the quality report was never included in the JSON output.

Fix:
- Reorder to match the FR worker's control flow: validate first, then emit
  json-summary with quality_report included.
- Added two tests covering --json-summary --validate in polling mode (with and
  without issues) to verify the quality report is included in JSON output.

This file re-exports the existing unit tests from tests/test_touch_index/
so the Impact Gate runner can discover them by issue ID. The canonical tests
live in tests/test_touch_index/test_bug_worker.py and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1789"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import TestBugJsonSummary  # noqa: E402, F401
