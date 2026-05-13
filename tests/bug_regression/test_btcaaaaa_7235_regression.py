"""
Regression tests for BTCAAAAA-7235: move bare-filename allowlist from
_is_source_file to comment_extractor only.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-7235
Component: src/touch_index/git_extractor.py, src/touch_index/comment_extractor.py

This file re-exports the canonical unit tests from test_git_extractor.py and
test_comment_extractor.py so the Impact Gate runner can discover them by bug ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-7235"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_git_extractor import (  # noqa: E402, F401
    TestIsSourceFile,
    TestGetCommitHashes,
    TestGetFilesForCommit,
    TestGetFilesForIssue,
    TestGetAllReferencedIssueIds,
    TestRunErrorHandling,
)

from tests.test_touch_index.test_comment_extractor import (  # noqa: E402, F401
    TestHasAllowedPrefix,
    TestNormalise,
    TestExtractFilesFromText,
    TestExtractFilesFromComments,
    TestFetchAndExtract,
    TestFetchIssueComments,
)
