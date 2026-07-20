import importlib.util
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


class ConfigurationAccessTest(unittest.TestCase):
    def test_restricted_configuration_view_stops_detection(self):
        forbidden = urllib.error.HTTPError(
            "http://paperclip.test/api/agents/agent-1/configuration",
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


if __name__ == "__main__":
    unittest.main()
