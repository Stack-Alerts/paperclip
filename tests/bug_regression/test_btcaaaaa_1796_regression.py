"""
Regression tests for BTCAAAAA-1796: add fetch_issue_comments and refactor
fetch_and_extract to use centralized API call.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1796
Component: src/touch_index/paperclip_client.py, src/touch_index/comment_extractor.py

This file re-exports the canonical unit tests from test_comment_extractor.py
so the Impact Gate runner can discover them by bug ID.  The canonical tests
live in tests/test_touch_index/test_comment_extractor.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1796"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_comment_extractor import (  # noqa: E402, F401
    TestNormalise,
    TestExtractFilesFromText,
    TestExtractFilesFromComments,
    TestFetchAndExtract,
    TestFetchIssueComments,
)
