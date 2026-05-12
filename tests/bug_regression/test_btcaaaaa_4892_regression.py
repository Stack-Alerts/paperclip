"""
Regression tests for BTCAAAAA-4892: remove misleading default from _emit_json_summary worker param.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-4892
Fixed in commit: e30e0cb
Component: src/touch_index/__main__.py

Root cause: the ``_emit_json_summary()`` function in ``__main__.py`` had a
misleading default ``worker: str = "bug"`` on its ``worker`` parameter. All
callers always passed ``worker`` explicitly, but the default meant that a
future caller who forgot to pass it would silently produce output claiming
to be the "bug" worker when it might be the FR worker (or vice versa).

``worker`` is now a required positional parameter with no default, so the
compiler/interpreter will catch any missing argument at definition time
rather than silently producing misleading output.

This file re-exports the existing ``TestEmitJsonSummaryRequiresWorker`` tests
from ``tests/test_touch_index/test_bug_worker.py`` so the Impact Gate runner
can discover them by bug ID. The canonical tests live in
``tests/test_touch_index/test_bug_worker.py`` and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-4892"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestEmitJsonSummaryRequiresWorker,
)
