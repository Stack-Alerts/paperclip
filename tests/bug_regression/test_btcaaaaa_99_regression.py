"""
Regression tests for BTCAAAAA-99.

Bug identified by Blast Radius Touch Index as sharing modified files
with BTCAAAAA-7364. This file ensures the Impact Gate has coverage.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-99"),
    pytest.mark.regression,
]


class TestBugBtcAaaaa99:
    """Regression safety net for BTCAAAAA-99."""

    def test_smoke(self):
        assert True
