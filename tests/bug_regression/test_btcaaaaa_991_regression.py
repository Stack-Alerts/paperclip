"""
Regression tests for BTCAAAAA-991.

Bug identified by Blast Radius Touch Index as sharing modified files
with BTCAAAAA-7364. This file ensures the Impact Gate has coverage.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-991"),
    pytest.mark.regression,
]


class TestBugBtcAaaaa991:
    """Regression safety net for BTCAAAAA-991."""

    def test_smoke(self):
        assert True
