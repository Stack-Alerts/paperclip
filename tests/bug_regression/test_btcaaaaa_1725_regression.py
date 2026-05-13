"""
Regression tests for BTCAAAAA-1725: only transition successfully processed bug
issues to done, not all input issues.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1725
Fixed in commits: 9d75eaf2, 337266c8
Components: src/touch_index/__main__.py, src/touch_index/bug_worker.py,
            scripts/run_touch_index_bug_worker.py

Root cause: the transition-to-done loop in both __main__._run_bug_cli() and
scripts/run_touch_index_bug_worker.py iterated over the input issues list
instead of the result list returned by run_bug_worker().  When ingest_bug_issue
raised an exception (e.g. DB connection failure), the issue was not present in
results but was still transitioned to done, creating a data gap with no retry
opportunity.

Fix:
- Add issue_id field to BugIngestionResult dataclass
- Populate it in both return paths of ingest_bug_issue
- Change transition loops to iterate results (successfully processed)
  instead of issues (all input)

This file re-exports the existing TestMain and TestBugRunnerDelegation tests
so the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1725"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
)

from tests.test_touch_index.test_bug_runner import (  # noqa: E402, F401
    TestBugRunnerDelegation,
)
