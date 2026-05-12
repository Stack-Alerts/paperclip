"""
Regression tests for BTCAAAAA-3233: handle git subprocess TimeoutExpired in bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-3233
Fixed in commit: 1c2cd89
Component: src/touch_index/git_extractor.py

Root cause: the ``_run()`` function in ``git_extractor.py`` caught
``FileNotFoundError`` and ``OSError`` but not ``subprocess.TimeoutExpired``,
which is raised when a git command exceeds the 30-second timeout on a large
repo. The unhandled exception propagated through the bug worker's file
extraction pipeline, crashing ingestion for that issue.

This file re-exports the existing ``TestRunErrorHandling`` tests from
``tests/test_touch_index/test_git_extractor.py`` so the Impact Gate runner
can discover them by bug ID. The canonical tests live in
``tests/test_touch_index/test_git_extractor.py`` and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-3233"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_git_extractor import (  # noqa: E402, F401
    TestRunErrorHandling,
)
