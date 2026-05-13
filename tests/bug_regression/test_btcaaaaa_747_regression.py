"""
Regression tests for BTCAAAAA-747: implement NautilusCodeGenerator production
module + builder UI hook.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-747
Fixed in commit: 26ed89ec
Component: src/strategy_builder/core/nautilus_code_generator.py

Root cause: NautilusTrader strategy code generation was missing — the Strategy
Builder UI had no way to produce production-ready NautilusTrader strategy Python
files. Fix implemented NautilusCodeGenerator with full strategy code generation
(imports, class definition, on_start/on_tick methods, signal evaluation, and
order management).
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-747"),
    pytest.mark.regression,
]

from tests.strategy_builder.core.test_nautilus_code_generator import (  # noqa: E402, F401
    TestNautilusCodeGenerator,
)
