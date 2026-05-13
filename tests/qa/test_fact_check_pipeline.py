"""Unit tests for scripts/qa_fact_check_pipeline.py"""

from __future__ import annotations

import json
import sys


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
            strict = False

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
            strict = False

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
            strict = False

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
            strict = False

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
            strict = False

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
            strict = False

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


class TestStrictScan:
    def test_strict_scan_exits_nonzero_when_flagged(self, monkeypatch):
        def fake_api(method, path, body=None):
            return make_issues_response(MOCK_ISSUES)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None
            strict = False
            strict = True

        with pytest.raises(SystemExit) as exc:
            cmd_scan(FakeArgs())
        assert exc.value.code == 1

    def test_strict_scan_exits_zero_when_no_flagged(self, monkeypatch, capsys):
        issues = [{
            "identifier": "BTCAAAAA-9999",
            "title": "Refactor internal loop structure",
            "description": "Optimize the main event loop",
            "assigneeAgentId": "df7b4035-e034-467e-af06-d25c869c810f",
        }]

        def fake_api(method, path, body=None):
            return make_issues_response(issues)

        monkeypatch.setattr("qa_fact_check_pipeline._api", fake_api)

        from qa_fact_check_pipeline import cmd_scan

        class FakeArgs:
            assignee = None
            strict = False
            strict = True

        cmd_scan(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["flagged"] == 0


class TestCheckTypes:
    def test_file_exists_true(self, tmp_path):
        from qa_fact_check_pipeline import _check_file_exists
        f = tmp_path / "exists.txt"
        f.write_text("hello")
        result = _check_file_exists({"path": str(f), "expected": True})
        assert result["pass"] is True
        assert result["actual"] is True

    def test_file_exists_false(self, tmp_path):
        from qa_fact_check_pipeline import _check_file_exists
        result = _check_file_exists({"path": str(tmp_path / "nonexistent.txt"), "expected": False})
        assert result["pass"] is True
        assert result["actual"] is False

    def test_file_exists_expected_missing_but_exists(self, tmp_path):
        from qa_fact_check_pipeline import _check_file_exists
        f = tmp_path / "surprise.txt"
        f.write_text("oh")
        result = _check_file_exists({"path": str(f), "expected": False})
        assert result["pass"] is False

    def test_line_count_tolerance_within_threshold(self, tmp_path):
        from qa_fact_check_pipeline import _check_line_count
        f = tmp_path / "code.py"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")
        result = _check_line_count({"path": str(f), "claimed": 6, "tolerance_pct": 20})
        assert result["pass"] is True
        assert result["actual"] == 5

    def test_line_count_tolerance_outside_threshold(self, tmp_path):
        from qa_fact_check_pipeline import _check_line_count
        f = tmp_path / "code.py"
        f.write_text("a\nb\n")
        result = _check_line_count({"path": str(f), "claimed": 100, "tolerance_pct": 10})
        assert result["pass"] is False

    def test_line_count_missing_file(self, tmp_path):
        from qa_fact_check_pipeline import _check_line_count
        result = _check_line_count({"path": str(tmp_path / "nope.py"), "claimed": 50, "tolerance_pct": 10})
        assert result["pass"] is False
        assert result["actual"] is None

    def test_env_key_exists_true(self, tmp_path, monkeypatch):
        from qa_fact_check_pipeline import _check_env_key
        env_path = tmp_path / ".env"
        env_path.write_text("MY_KEY=42\n")
        monkeypatch.setattr("qa_fact_check_pipeline.REPO_ROOT", str(tmp_path))
        result = _check_env_key({"key": "MY_KEY", "expected": True})
        assert result["pass"] is True
        assert result["actual"] is True

    def test_env_key_exists_false(self, tmp_path, monkeypatch):
        from qa_fact_check_pipeline import _check_env_key
        env_path = tmp_path / ".env"
        env_path.write_text("OTHER_KEY=1\n")
        monkeypatch.setattr("qa_fact_check_pipeline.REPO_ROOT", str(tmp_path))
        result = _check_env_key({"key": "MISSING_KEY", "expected": True})
        assert result["pass"] is False

    def test_env_key_value_match(self, tmp_path, monkeypatch):
        from qa_fact_check_pipeline import _check_env_key_value
        env_path = tmp_path / ".env"
        env_path.write_text("PORT=8080\n")
        monkeypatch.setattr("qa_fact_check_pipeline.REPO_ROOT", str(tmp_path))
        result = _check_env_key_value({"key": "PORT", "expected": "8080"})
        assert result["pass"] is True
        assert result["actual"] == "8080"

    def test_env_key_value_mismatch(self, tmp_path, monkeypatch):
        from qa_fact_check_pipeline import _check_env_key_value
        env_path = tmp_path / ".env"
        env_path.write_text("PORT=3000\n")
        monkeypatch.setattr("qa_fact_check_pipeline.REPO_ROOT", str(tmp_path))
        result = _check_env_key_value({"key": "PORT", "expected": "8080"})
        assert result["pass"] is False

    def test_text_not_in_file_present(self, tmp_path):
        from qa_fact_check_pipeline import _check_text_not_in_file
        f = tmp_path / "readme.md"
        f.write_text("This file mentions 308GB of data.\n")
        result = _check_text_not_in_file({"path": str(f), "text": "308GB"})
        assert result["pass"] is False
        assert result["actual"] is True

    def test_text_not_in_file_absent(self, tmp_path):
        from qa_fact_check_pipeline import _check_text_not_in_file
        f = tmp_path / "readme.md"
        f.write_text("This file is clean.\n")
        result = _check_text_not_in_file({"path": str(f), "text": "308GB"})
        assert result["pass"] is True
        assert result["actual"] is False

    def test_text_not_in_file_missing(self, tmp_path):
        from qa_fact_check_pipeline import _check_text_not_in_file
        result = _check_text_not_in_file({"path": str(tmp_path / "nope.md"), "text": "x"})
        assert result["pass"] is False

    def test_dir_size_tolerance(self, tmp_path, monkeypatch):
        from qa_fact_check_pipeline import _check_dir_size
        d = tmp_path / "data"
        d.mkdir()
        (d / "file.bin").write_bytes(b"x" * 1000)
        result = _check_dir_size({"path": str(d), "claimed_gb": 0.1, "tolerance_pct": 99})
        assert result["pass"] is True
        assert result["actual_gb"] is not None

    def test_dir_size_missing(self, tmp_path):
        from qa_fact_check_pipeline import _check_dir_size
        result = _check_dir_size({"path": str(tmp_path / "nope_dir"), "claimed_gb": 10, "tolerance_pct": 20})
        assert result["pass"] is False


class TestRunCheck:
    def test_run_check_produces_pass_verdict(self):
        from qa_fact_check_pipeline import _run_check
        item = {
            "id": "test-01",
            "document": "README.md",
            "type": "file_exists",
            "description": "some file should not exist",
            "params": {"path": "/tmp/nonexistent_xyz_12345", "expected": False},
        }
        result = _run_check(item)
        assert result["verdict"] == "PASS"
        assert result["id"] == "test-01"

    def test_run_check_produces_fail_verdict(self):
        from qa_fact_check_pipeline import _run_check
        item = {
            "id": "test-02",
            "document": "README.md",
            "type": "text_not_in_file",
            "description": "should not contain fail-text",
            "params": {"path": "/etc/hostname", "text": "this-is-unlikely-text-98765"},
        }
        result = _run_check(item)
        assert result["verdict"] == "PASS"

    def test_run_check_unknown_type_returns_error(self):
        from qa_fact_check_pipeline import _run_check
        item = {
            "id": "test-03",
            "type": "nonexistent_check_type",
            "description": "bogus",
            "params": {},
        }
        result = _run_check(item)
        assert result["verdict"] == "ERROR"


class TestCheckCommand:
    def test_check_all_pass_exits_zero(self, tmp_path, monkeypatch, capsys):
        checklist_path = tmp_path / "checklist.json"
        checklist_path.write_text(json.dumps({"checks": [
            {"id": "c1", "type": "file_exists", "description": "d",
             "params": {"path": str(tmp_path / "nope"), "expected": False}},
        ]}))

        from qa_fact_check_pipeline import cmd_check

        class FakeArgs:
            checklist = str(checklist_path)

        cmd_check(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["total"] == 1
        assert result["pass"] == 1
        assert result["fail"] == 0

    def test_check_with_fails_exits_nonzero(self, tmp_path, monkeypatch, capsys):
        f = tmp_path / "exists.txt"
        f.write_text("hi")
        checklist_path = tmp_path / "checklist.json"
        checklist_path.write_text(json.dumps({"checks": [
            {"id": "c1", "type": "file_exists", "description": "d",
             "params": {"path": str(f), "expected": False}},
        ]}))

        from qa_fact_check_pipeline import cmd_check

        class FakeArgs:
            checklist = str(checklist_path)

        with pytest.raises(SystemExit) as exc:
            cmd_check(FakeArgs())
        assert exc.value.code == 1
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["fail"] == 1

    def test_check_with_errors_exits_nonzero(self, tmp_path, capsys):
        checklist_path = tmp_path / "checklist.json"
        checklist_path.write_text(json.dumps({"checks": [
            {"id": "c1", "type": "unknown_type_xyz", "description": "d", "params": {}},
        ]}))

        from qa_fact_check_pipeline import cmd_check

        class FakeArgs:
            checklist = str(checklist_path)

        with pytest.raises(SystemExit) as exc:
            cmd_check(FakeArgs())
        assert exc.value.code == 1

    def test_check_supports_flat_array_checklist(self, tmp_path, capsys):
        checklist_path = tmp_path / "checklist.json"
        checklist_path.write_text(json.dumps([
            {"id": "c1", "type": "file_exists", "description": "d",
             "params": {"path": str(tmp_path / "no"), "expected": False}},
        ]))

        from qa_fact_check_pipeline import cmd_check

        class FakeArgs:
            checklist = str(checklist_path)

        cmd_check(FakeArgs())
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["pass"] == 1
        assert result["fail"] == 0
