import importlib.util
import os
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("claude_local_drift_check.py")
SPEC = importlib.util.spec_from_file_location("claude_local_drift_check", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


BASE = "http://paperclip.test/api"
RUN_ID = "test-run-1"
EXECUTION_ISSUE_ID = "BTCAAAAA-39915"


def _http_error(code: int, url: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "Forbidden", {}, None)


class ConfigurationAccessTest(unittest.TestCase):
    def test_restricted_configuration_view_stops_detection(self):
        forbidden = urllib.error.HTTPError(
            f"{BASE}/agents/agent-1/configuration",
            403,
            "Forbidden",
            {},
            None,
        )
        agent = {
            "id": "agent-1",
            "name": "RestrictedAgent",
            "adapterType": "claude_local",
        }
        expected_env = {key: "expected" for key in MODULE.EXPECTED_KEYS}
        error = None

        with (
            patch.object(MODULE, "load_canonical_env", return_value=expected_env),
            patch.object(MODULE, "list_claude_local_agents", return_value=[agent]),
            patch.object(MODULE, "fetch_agent", return_value={"adapterConfig": {}}),
            patch.object(MODULE, "_request", side_effect=forbidden),
            patch.object(MODULE, "open_incident", return_value={"identifier": "BTCAAAAA-1"}) as open_incident,
            patch.object(MODULE, "post_summary_comment"),
            patch.object(sys, "argv", ["claude_local_drift_check.py", "--mode", "open"]),
        ):
            try:
                MODULE.main()
            except BaseException as exc:
                error = exc

        self.assertIsInstance(error, RuntimeError)
        self.assertRegex(str(error), "cannot read agent configurations")
        open_incident.assert_not_called()


class PostSummaryCommentFallbackTest(unittest.TestCase):
    def _drifted_records(self, count: int = 1):
        return [
            {
                "name": f"agent-{i}",
                "incident_id": f"BTCAAAAA-{i}",
                "drift": {
                    "missing_keys": [],
                    "mismatched": [],
                    "unexpected_keys": [],
                    "timeout": {"matches": True, "actual": 3800, "expected": 3800},
                },
            }
            for i in range(count)
        ]

    def test_successful_umbrella_post_returns_umbrella_posted(self):
        with patch.dict(os.environ, {"PAPERCLIP_TASK_ID": EXECUTION_ISSUE_ID}, clear=False):
            with patch.object(MODULE, "_request", return_value={"id": "comment-1"}) as req:
                status = MODULE.post_summary_comment(self._drifted_records(), RUN_ID)
        self.assertEqual(status["umbrella_posted"], True)
        self.assertEqual(status["fallback_posted"], False)
        self.assertEqual(status["skipped_reason"], None)
        self.assertEqual(status["errors"], [])
        self.assertEqual(len(req.call_args_list), 1)
        called_path = req.call_args_list[0].args[1]
        self.assertIn(MODULE.UMBRELLA_ID, called_path)
        self.assertNotIn(EXECUTION_ISSUE_ID, called_path)

    def test_falls_back_to_execution_issue_on_403(self):
        forbidden = _http_error(403, f"{BASE}/issues/{MODULE.UMBRELLA_ID}/comments")
        with patch.dict(os.environ, {"PAPERCLIP_TASK_ID": EXECUTION_ISSUE_ID}, clear=False):
            with patch.object(
                MODULE, "_request", side_effect=[forbidden, {"id": "exec-comment"}]
            ) as req:
                status = MODULE.post_summary_comment(self._drifted_records(), RUN_ID)
        self.assertEqual(status["umbrella_posted"], False)
        self.assertEqual(status["fallback_posted"], True)
        self.assertEqual(status["skipped_reason"], None)
        self.assertEqual(len(status["errors"]), 1)
        self.assertEqual(status["errors"][0]["attempt"], "umbrella")
        self.assertEqual(status["errors"][0]["status"], 403)
        self.assertEqual(len(req.call_args_list), 2)
        fallback_path = req.call_args_list[1].args[1]
        self.assertIn(EXECUTION_ISSUE_ID, fallback_path)
        self.assertIn("/api/issues/", fallback_path)

    def test_falls_back_on_401(self):
        forbidden = _http_error(401, f"{BASE}/issues/{MODULE.UMBRELLA_ID}/comments")
        with patch.dict(os.environ, {"PAPERCLIP_TASK_ID": EXECUTION_ISSUE_ID}, clear=False):
            with patch.object(
                MODULE, "_request", side_effect=[forbidden, {"id": "exec-comment"}]
            ):
                status = MODULE.post_summary_comment(self._drifted_records(), RUN_ID)
        self.assertEqual(status["fallback_posted"], True)
        self.assertEqual(status["umbrella_posted"], False)
        self.assertEqual(status["errors"][0]["status"], 401)

    def test_records_skip_when_no_execution_issue_id(self):
        forbidden = _http_error(403, f"{BASE}/issues/{MODULE.UMBRELLA_ID}/comments")
        env = {k: v for k, v in os.environ.items() if k != "PAPERCLIP_TASK_ID"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(
                MODULE, "_request", side_effect=[forbidden]
            ) as req:
                status = MODULE.post_summary_comment(self._drifted_records(), RUN_ID)
        self.assertEqual(status["umbrella_posted"], False)
        self.assertEqual(status["fallback_posted"], False)
        self.assertEqual(status["skipped_reason"], "execution_issue_id_missing")
        self.assertEqual(len(req.call_args_list), 1)

    def test_records_both_errors_when_fallback_also_fails(self):
        forbidden = _http_error(403, f"{BASE}/issues/{MODULE.UMBRELLA_ID}/comments")
        fallback_err = _http_error(
            500, f"{BASE}/issues/{EXECUTION_ISSUE_ID}/comments"
        )
        with patch.dict(os.environ, {"PAPERCLIP_TASK_ID": EXECUTION_ISSUE_ID}, clear=False):
            with patch.object(MODULE, "_request", side_effect=[forbidden, fallback_err]):
                status = MODULE.post_summary_comment(self._drifted_records(), RUN_ID)
        self.assertEqual(status["umbrella_posted"], False)
        self.assertEqual(status["fallback_posted"], False)
        self.assertEqual(len(status["errors"]), 2)
        self.assertEqual(status["errors"][1]["attempt"], "execution_issue")
        self.assertEqual(status["errors"][1]["status"], 500)

    def test_propagates_non_authorization_error(self):
        server_err = _http_error(500, f"{BASE}/issues/{MODULE.UMBRELLA_ID}/comments")
        with patch.dict(os.environ, {"PAPERCLIP_TASK_ID": EXECUTION_ISSUE_ID}, clear=False):
            with patch.object(MODULE, "_request", side_effect=[server_err]):
                with self.assertRaises(urllib.error.HTTPError):
                    MODULE.post_summary_comment(self._drifted_records(), RUN_ID)


if __name__ == "__main__":
    unittest.main()
