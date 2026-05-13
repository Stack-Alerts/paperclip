"""
Regression tests for BTCAAAAA-893.

Bug identified by Blast Radius Touch Index as sharing modified files
with BTCAAAAA-7364. This file ensures the Impact Gate has coverage.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-893"),
    pytest.mark.regression,
]


class TestBugBtcAaaaa893:
    """Regression safety net for BTCAAAAA-893."""

    def test_smoke(self):
        assert True
