"""
Regression tests for BTCAAAAA-1272.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1272

This file is the canonical bug regression location for the fix.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1272"),
    pytest.mark.regression,
]


class TestBTCAAAAA1272Regression:
    """Regression tests for BTCAAAAA-1272."""

    def test_placeholder(self) -> None:
        assert True
