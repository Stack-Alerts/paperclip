"""
Regression tests for BTCAAAAA-2105: apply ruff format to touch_index
FR ingestion worker and related modules.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-2105
Component: src/touch_index/comment_extractor.py
           tests/test_touch_index/test_bug_worker.py
           tests/test_touch_index/test_comment_extractor.py
           tests/test_touch_index/test_git_extractor.py

This file re-exports the canonical unit tests from the affected test
modules so the Impact Gate runner can discover them by bug ID.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2105"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_comment_extractor import (  # noqa: E402, F401
    TestNormalise,
    TestExtractFilesFromText,
    TestExtractFilesFromComments,
    TestFetchAndExtract,
    TestFetchIssueComments,
)

from tests.test_touch_index.test_git_extractor import (  # noqa: E402, F401
    TestIsSourceFile,
    TestGetCommitHashes,
    TestGetFilesForCommit,
    TestGetFilesForIssue,
    TestGetAllReferencedIssueIds,
    TestRunErrorHandling,
)

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestParseCompletedAt,
    TestIngestBugIssue,
    TestRunBugWorker,
    TestProcessBugIssue,
    TestBugWorkerDryRun,
    TestMain,
)
