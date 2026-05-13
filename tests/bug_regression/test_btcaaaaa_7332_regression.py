"""
Regression tests for BTCAAAAA-7332: DictWrapper mapping protocol to support ** unpacking.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-7332
Fixed in commit: dce22f64
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: DictWrapper only had __getattr__, which caused Python's ** unpacking
protocol to fail because .keys() fell through to __getattr__ and returned None.

Fix: Added keys(), __getitem__, __iter__, __len__ methods that delegate to the
underlying dict when self._data is a dict, with safe fallbacks otherwise.
"""
from __future__ import annotations

import pytest

from src.strategy_builder.ui.backtest_config_panel import DictWrapper

pytestmark = [
    pytest.mark.bug("BTCAAAAA-7332"),
    pytest.mark.regression,
]


def test_dictwrapper_keys_returns_dict_keys():
    dw = DictWrapper({"a": 1, "b": 2})
    assert set(dw.keys()) == {"a", "b"}


def test_dictwrapper_keys_empty_dict():
    assert list(DictWrapper({}).keys()) == []


def test_dictwrapper_keys_non_dict():
    assert list(DictWrapper(None).keys()) == []


def test_dictwrapper_getitem():
    dw = DictWrapper({"a": 1, "b": 2})
    assert dw["a"] == 1
    assert dw["b"] == 2


def test_dictwrapper_getitem_raises_keyerror():
    dw = DictWrapper({"a": 1})
    with pytest.raises(KeyError):
        _ = dw["nonexistent"]


def test_dictwrapper_iter():
    dw = DictWrapper({"a": 1, "b": 2})
    assert set(dw) == {"a", "b"}


def test_dictwrapper_iter_non_dict():
    assert list(DictWrapper(None)) == []


def test_dictwrapper_len():
    assert len(DictWrapper({"a": 1, "b": 2})) == 2


def test_dictwrapper_len_empty():
    assert len(DictWrapper({})) == 0


def test_dictwrapper_len_non_dict():
    assert len(DictWrapper(None)) == 0


def test_dictwrapper_unpacking():
    result = {**DictWrapper({"a": 1, "b": 2})}
    assert result == {"a": 1, "b": 2}


def test_dictwrapper_unpacking_empty():
    result = {**DictWrapper({})}
    assert result == {}


def test_dictwrapper_unpacking_with_kwargs():
    def dummy(**kwargs):
        return kwargs

    result = dummy(timeframe="15m", **DictWrapper({"a": 1}))
    assert result == {"timeframe": "15m", "a": 1}


def test_dictwrapper_attribute_access_preserved():
    """Regression: attribute access must still work after adding mapping protocol."""
    dw = DictWrapper({"name": "test_block", "parameters": {"p1": 1}, "signal_name": "AT_ASIA_50"})
    assert dw.name == "test_block"
    assert dw.parameters.p1 == 1
    assert dw.signal_name == "AT_ASIA_50"


def test_dictwrapper_nested_dict_access():
    dw = DictWrapper({"exit_conditions": [{"signal_name": "EXIT_1"}]})
    assert dw.exit_conditions[0].signal_name == "EXIT_1"


def test_dictwrapper_missing_attr_returns_none():
    dw = DictWrapper({"a": 1})
    assert dw.nonexistent is None
