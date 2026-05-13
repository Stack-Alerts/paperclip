"""
Regression tests for BTCAAAAA-129: _reload_current_version() must include
strategy_type in config_dict so the auto-fix value survives a DB reload.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-129
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: _reload_current_version() was missing 'strategy_type' in
config_dict, causing the UI to revert to the default 'Bullish' type after
auto-fix + save, wiping out the user-chosen / auto-fixed strategy_type on
next save.

This file re-exports the existing unit tests from
tests/strategy_builder/test_auto_fix_db_persistence.py so the Impact Gate
runner can discover them by bug ID.  The canonical tests live in
tests/strategy_builder/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-129"),
    pytest.mark.regression,
]

from tests.strategy_builder.test_auto_fix_db_persistence import (  # noqa: E402, F401
    TestAutoFixDbPersistence,
)
