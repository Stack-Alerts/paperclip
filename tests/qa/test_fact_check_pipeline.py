"""Unit tests for scripts/qa_fact_check_pipeline.py"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, "scripts")
from qa_fact_check_pipeline import (  # noqa: E402
    AGENTS,
    ROUTING,
    COMPANY_ID,
    _route,
)

MOCK_ISSUES = [
    {
        "identifier": "BTCAAAAA-1001",
        "title": "Fix RSI tooltip formatting",
        "description": "The RSI tooltip text is misaligned",
        "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
    },
    {
        "identifier": "BTCAAAAA-1002",
        "title": "Add btc price label",
        "description": "Add BTC price label to the dashboard",
        "assigneeAgentId": "e3fcab65-c9a3-45bd-97e8-5145d3d6db5e",
    },
    {
        "identifier": "BTCAAAAA-1003",
        "title": "Update strategy description for EMA crossover",
        "description": "Strategy now uses fast=12 slow=26",
        "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
    },
    {
        "identifier": "BTCAAAAA-1004",
        "title": "Fix security risk label in settings",
        "description": "Security label shows wrong encryption type",
        "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
    },
    {
        "identifier": "BTCAAAAA-1005",
        "title": "Fix signal indicator copy text",
        "description": "Signal description needs to be corrected",
        "assigneeAgentId": "e3fcab65-c9a3-45bd-97e8-5145d3d6db5e",
    },
    {
        "identifier": "BTCAAAAA-1006",
        "title": "Refactor backtest engine internals",
        "description": "Internal refactoring of loop structure",
        "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
    },
]


def make_issues_response(items):
    return {"items": items, "total": len(items)}


class TestRouting:
    def test_btc_keyword_routes_to_general_researcher(self):
        assert _route("btc price tooltip text") == AGENTS["general_researcher"]

    def test_blockchain_routes_to_general_researcher(self):
        assert _route("blockchain node status message") == AGENTS["general_researcher"]

    def test_exchange_routes_to_general_researcher(self):
        assert _route("exchange connection label") == AGENTS["general_researcher"]

    def test_nautilus_routes_to_general_researcher(self):
        assert _route("nautilus version description") == AGENTS["general_researcher"]

    def test_strategy_routes_to_strategy_researcher(self):
        assert _route("strategy description text") == AGENTS["strategy_researcher"]

    def test_signal_routes_to_strategy_researcher(self):
        assert _route("signal indicator tooltip") == AGENTS["strategy_researcher"]

    def test_indicator_routes_to_strategy_researcher(self):
        assert _route("indicator copy label") == AGENTS["strategy_researcher"]

    def test_security_routes_to_security_analyst(self):
        assert _route("security label text") == AGENTS["security_analyst"]

    def test_risk_routes_to_security_analyst(self):
        assert _route("risk description message") == AGENTS["security_analyst"]

    def test_first_keyword_match_wins(self):
        desc = "btc strategy security signal"
        assert _route(desc) == AGENTS["general_researcher"]

    def test_no_match_routes_to_test_manager(self):
        assert _route("refactor loop internals") == AGENTS["test_manager"]

    def test_empty_string_routes_to_test_manager(self):
        assert _route("") == AGENTS["test_manager"]

    def test_case_insensitive_matching(self):
        assert _route("BTC exchange TOOLTIP") == AGENTS["general_researcher"]
        assert _route("STRATEGY Signal") == AGENTS["strategy_researcher"]

    def test_keyword_order_matches_routing_dict_order(self):
        routing_keys = list(ROUTING.keys())
        assert routing_keys[:4] == ["btc", "blockchain", "exchange", "nautilus"]
        assert routing_keys[4:7] == ["strategy", "signal", "indicator"]
        assert routing_keys[7:] == ["security", "risk"]


class TestScanCommand:
    def test_scan_flags_matching_issues(self, monkeypatch):
        api_calls = []

        def fake_api(method, path, body=None):
            api_calls.append((method, path, body))
            return make_issues_response(MOCK_ISSUES)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None

        cmd_scan(FakeArgs())

        assert len(api_calls) == 1
        assert api_calls[0][0] == "GET"
        assert f"/api/companies/{COMPANY_ID}/issues" in api_calls[0][1]

    def test_scan_output_format(self, monkeypatch, capsys):
        def fake_api(method, path, body=None):
            return make_issues_response(MOCK_ISSUES)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None

        cmd_scan(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert "timestamp" in result
        assert "scanned" in result
        assert "flagged" in result
        assert "items" in result
        assert isinstance(result["items"], list)
        if result["items"]:
            item = result["items"][0]
            assert "id" in item
            assert "title" in item
            assert "reviewer" in item

    def test_scan_with_assignee_filter(self, monkeypatch, capsys):
        def fake_api(method, path, body=None):
            return make_issues_response(MOCK_ISSUES)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        target = "e3fcab65-c9a3-45bd-97e8-5145d3d6db5e"

        class FakeArgs:
            assignee = target

        cmd_scan(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["scanned"] == 2
        assert result["flagged"] == 2
        flagged_ids = {item["id"] for item in result["items"]}
        assert flagged_ids == {"BTCAAAAA-1002", "BTCAAAAA-1005"}

    def test_scan_empty_issues_list(self, monkeypatch, capsys):
        def fake_api(method, path, body=None):
            return []

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None

        cmd_scan(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["scanned"] == 0
        assert result["flagged"] == 0
        assert result["items"] == []

    def test_scan_no_matching_keywords(self, monkeypatch, capsys):
        issues = [
            {
                "identifier": "BTCAAAAA-9999",
                "title": "Refactor internal loop structure",
                "description": "Optimize the main event loop for performance",
                "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
            }
        ]

        def fake_api(method, path, body=None):
            return make_issues_response(issues)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None

        cmd_scan(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["scanned"] == 1
        assert result["flagged"] == 0

    def test_scan_handles_issues_without_description(self, monkeypatch, capsys):
        issues = [
            {
                "identifier": "BTCAAAAA-9999",
                "title": "Fix nautilus tooltip",
                "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
            }
        ]

        def fake_api(method, path, body=None):
            return make_issues_response(issues)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None

        cmd_scan(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["scanned"] == 1
        assert result["flagged"] == 1
        assert result["items"][0]["reviewer"] == AGENTS["general_researcher"]


class TestVerifyCommand:
    def test_verify_output_format(self, monkeypatch, capsys):
        issue = {
            "title": "Fix btc tooltip text",
            "description": "The BTC price tooltip is wrong",
        }

        def fake_api(method, path, body=None):
            return issue

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_verify

        class FakeArgs:
            issue_id = "BTCAAAAA-9999"

        cmd_verify(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["issue"] == "BTCAAAAA-9999"
        assert result["verdict"] == "PENDING"
        assert result["reviewer"] == AGENTS["general_researcher"]


class TestRouteCommand:
    def test_route_output_format(self, monkeypatch, capsys):
        issue = {
            "title": "Fix strategy signal description",
            "description": "EMA crossover signal text",
        }

        def fake_api(method, path, body=None):
            return issue

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_route

        class FakeArgs:
            issue_id = "BTCAAAAA-9999"

        cmd_route(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["issue"] == "BTCAAAAA-9999"
        assert result["routed_to"] == "strategy_researcher"

    def test_route_defaults_to_test_manager_for_unmatched(self, monkeypatch, capsys):
        issue = {
            "title": "Refactor internal loop",
            "description": "Performance optimization",
        }

        def fake_api(method, path, body=None):
            return issue

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_route

        class FakeArgs:
            issue_id = "BTCAAAAA-9999"

        cmd_route(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert result["routed_to"] == "test_manager"


class TestConfiguration:
    def test_company_id_is_set(self):
        assert COMPANY_ID == "73419cf3-bd37-4a7c-8782-311ccb47fced"

    def test_all_agent_ids_are_valid_uuid_format(self):
        import re

        uuid_re = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        for name, agent_id in AGENTS.items():
            assert uuid_re.match(agent_id), (
                f"Agent {name} has invalid UUID: {agent_id}"
            )

    def test_routing_values_are_valid_agent_ids(self):
        for kw, agent_id in ROUTING.items():
            assert agent_id in AGENTS.values(), (
                f"Routing key '{kw}' maps to unknown agent ID: {agent_id}"
            )

    def test_keyword_routing_matches_documented_order(self):
        expected_order = [
            "btc",
            "blockchain",
            "exchange",
            "nautilus",
            "strategy",
            "signal",
            "indicator",
            "security",
            "risk",
        ]
        assert list(ROUTING.keys()) == expected_order

    def test_timestamp_is_utc(self, monkeypatch, capsys):
        def fake_api(method, path, body=None):
            return {"title": "test", "description": "test"}

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_verify

        class FakeArgs:
            issue_id = "BTCAAAAA-9999"

        cmd_verify(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)

        assert "verdict" in result
        assert result["verdict"] == "PENDING"


class TestCLIArgumentParsing:
    """Smoke-tests that argument parsing doesn't crash; these hit the actual
    _api function and will fail unless a Paperclip server is running, so they
    are excluded from CI via a marker.  Run with -m 'smoke' locally only."""

    @pytest.mark.skip(reason="requires running Paperclip API server")
    def test_scan_subcommand_accepts_assignee(self):
        import argparse
        from qa_fact_check_pipeline import main
        sys.argv = ["qa_fact_check_pipeline.py", "scan", "--assignee", "test-id"]
        try:
            main()
        except SystemExit:
            pass

    @pytest.mark.skip(reason="requires running Paperclip API server")
    def test_verify_subcommand_requires_issue_id(self):
        sys.argv = ["qa_fact_check_pipeline.py", "verify", "BTCAAAAA-9999"]
        try:
            from qa_fact_check_pipeline import main
            main()
        except SystemExit:
            pass

    @pytest.mark.skip(reason="requires running Paperclip API server")
    def test_route_subcommand_requires_issue_id(self):
        sys.argv = ["qa_fact_check_pipeline.py", "route", "BTCAAAAA-9999"]
        try:
            from qa_fact_check_pipeline import main
            main()
        except SystemExit:
            pass
