"""
Regression tests for BTCAAAAA-1709: remove duplicate main() CLI from bug_worker.py,
consolidate in __main__._run_bug_cli().

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1709
Fixed in commits: a8469598, 2f8a7d0e
Components: src/touch_index/__main__.py, src/touch_index/bug_worker.py

Root cause: bug_worker.py had its own main() CLI entry point that duplicated
the dispatch logic in __main__.py.  This consolidation moved the bug-close
CLI into __main__._run_bug_cli(), matching the fr_worker pattern where
__main__ owns all worker dispatch.  The __main__.main() function now
dispatches "bug" to _run_bug_cli() instead of calling bug_worker.main()
directly.

This file re-exports the existing canonical unit tests from
tests/test_touch_index/test_bug_worker.py and
tests/test_touch_index/test___main__.py so the Impact Gate runner can
discover them by issue ID.  The canonical tests live in those files
and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1709"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
)

from tests.test_touch_index.test___main__ import (  # noqa: E402, F401
    TestMainDispatch,
    TestHelp,
)
