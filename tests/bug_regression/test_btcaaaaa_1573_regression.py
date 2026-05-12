"""
Regression tests for BTCAAAAA-1573: HTTP sessions not closed in blast_radius generator.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1573
Fixed in commits: 705b638, 80ebca4
Components: src/blast_radius/generator.py, scripts/patch-routine-selfclose.sh

Root cause: _get_issue(), _get_agent_name(), and _post_comment() were creating
HTTP sessions via _session() without closing them (no context manager). This
left connections open after each call.

Fix: Updated all three functions to use 'with _session() as sess:' and added
mock_sess.__enter__.return_value in tests to support the context manager
protocol in mocked session objects.

This file re-exports the existing unit tests from test_generator.py so the
Impact Gate runner can discover them by bug ID. The canonical tests live in
tests/test_blast_radius/test_generator.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1573"),
    pytest.mark.regression,
]

from tests.test_blast_radius.test_generator import (  # noqa: E402, F401
    TestGetAgentName,
    TestPostComment,
    TestGetIssue,
    TestRunHeaders,
)
