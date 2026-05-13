"""
Regression tests for BTCAAAAA-687: P1.1 Signal Catalog Service.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-687
Fixed in commit: b1882390
Component: src/ai_consultant/signal_catalog.py

Root cause: Signal catalog service was missing — AI Consultant had no structured
catalog of building blocks, signals, and signal tiers to reference when generating
strategy code. Fix implemented SignalCatalogService with registry loading, context
string generation, search, and signal info lookups.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-687"),
    pytest.mark.regression,
]

from tests.ai_consultant.test_signal_catalog import (  # noqa: E402, F401
    TestRegistryLoading,
    TestContextString,
    TestSearch,
    TestGetSignalInfo,
    TestListSignalsByType,
    TestLiveStatsMock,
)
