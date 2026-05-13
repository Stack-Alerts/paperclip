"""
Regression tests for BTCAAAAA-170.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-170
Component: src/touch_index/comment_extractor.py

This file was backfilled by BTCAAAAA-25274 (blocking issue auto-created
by the Impact Gate when issue 170 appeared in a blast-radius regression
set with no corresponding test file).  The original bug context is not
recoverable from the available repository data.

The regression set links this issue to the comment_extractor module;
these tests re-export the canonical comment_extractor unit tests so the
Impact Gate runner can discover them by bug ID.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-170"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_comment_extractor import (  # noqa: E402, F401
    TestNormalise,
    TestExtractFilesFromText,
    TestExtractFilesFromComments,
    TestFetchAndExtract,
    TestFetchIssueComments,
)
