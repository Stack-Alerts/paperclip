"""
Regression tests for BTCAAAAA-8034: Routine self-close fix — Blast Radius worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-8034
Fixed: patch-routine-selfclose.sh applied to heartbeat.js

Root cause: releaseIssueExecutionAndPromote() in heartbeat.js clears the
execution lock but never calls issuesSvc.update() with status:"done" when
the run status is "succeeded" and the issue originKind is
"routine_execution". This leaves a growing tail of stuck in_progress
routine instances.

Fix: Added a conditional in releaseIssueExecutionAndPromote() that
transitions routine_execution issues to "done" when the heartbeat run
succeeds.

This file validates that the patch is present and correct in the running
Paperclip server instance.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-8034"),
    pytest.mark.regression,
]


def _get_running_server_heartbeat() -> Path | None:
    """Find the heartbeat.js used by the currently running paperclip server."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "paperclipai run"],
            capture_output=True, text=True, timeout=5,
        )
        if not result.stdout.strip():
            return None
        pid = result.stdout.strip().splitlines()[0]
        result = subprocess.run(
            ["ps", "-p", pid, "-o", "args="],
            capture_output=True, text=True, timeout=5,
        )
        cmdline = result.stdout.strip()
        if ".npm/_npx/" not in cmdline:
            return None
        parts = cmdline.split(".npm/_npx/")
        if len(parts) < 2:
            return None
        npx_hash = parts[1].split("/")[0]
        return (
            Path.home()
            / ".npm"
            / "_npx"
            / npx_hash
            / "node_modules"
            / "@paperclipai"
            / "server"
            / "dist"
            / "services"
            / "heartbeat.js"
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
        return None


class TestRoutineSelfClosePatch:
    """Validate the routine self-close patch in heartbeat.js."""

    PATCH_SENTINEL = "self-close routine"
    PATCH_FIX_COMMENT = "// Fix: self-close routine execution issues when the run succeeds"
    PATCH_CONDITION = (
        "if (run.status === 'succeeded'"
        " && issue.originKind === 'routine_execution'"
        " && issue.status !== 'done'"
        " && issue.status !== 'cancelled')"
    )

    def test_patch_applied_to_running_server(self) -> None:
        """The running Paperclip server's heartbeat.js must have the fix."""
        hb = _get_running_server_heartbeat()
        if hb is None:
            pytest.skip("No running Paperclip server detected")
        content = hb.read_text(encoding="utf-8")
        assert self.PATCH_SENTINEL in content, (
            f"Patch sentinel {self.PATCH_SENTINEL!r} not found in {hb}"
        )
        assert self.PATCH_FIX_COMMENT in content, (
            f"Patch comment {self.PATCH_FIX_COMMENT!r} not found in {hb}"
        )

    def test_patch_logic_is_correct(self) -> None:
        """Verify the patched condition transitions routine_execution to done."""
        hb = _get_running_server_heartbeat()
        if hb is None:
            pytest.skip("No running Paperclip server detected")
        content = hb.read_text(encoding="utf-8")
        stripped_cond = self.PATCH_CONDITION.replace(" ", "").replace("\n", "")
        assert stripped_cond in content.replace(" ", "").replace("\n", ""), (
            "Patch condition not found in heartbeat.js"
        )
        assert "status: 'done'" in content, "Patch must set status to 'done'"

    def test_patch_script_exists_and_has_correct_logic(self) -> None:
        """The patch script must exist and contain the correct fix logic."""
        script = (
            Path(__file__).resolve().parents[2]
            / "scripts"
            / "patch-routine-selfclose.sh"
        )
        assert script.is_file(), f"Patch script not found at {script}"
        content = script.read_text(encoding="utf-8")
        assert "self-close routine" in content
        assert "routine_execution" in content
        assert "status: 'done'" in content
        assert "releaseIssueExecutionAndPromote" in content

    def test_no_fix_label_idle_on_rerun(self) -> None:
        """The sentinel comment prevents double-application."""
        hb = _get_running_server_heartbeat()
        if hb is None:
            pytest.skip("No running Paperclip server detected")
        content = hb.read_text(encoding="utf-8")
        assert content.count(self.PATCH_FIX_COMMENT) == 1, (
            "Patch was applied more than once — expected exactly one occurrence"
        )

    def test_patch_script_is_idempotent(self) -> None:
        """Verify the patch script's idempotency guard is correct."""
        script = (
            Path(__file__).resolve().parents[2]
            / "scripts"
            / "patch-routine-selfclose.sh"
        )
        content = script.read_text(encoding="utf-8")
        assert 'grep -q "self-close routine"' in content, (
            "Patch script must check for sentinel before applying"
        )
        assert 'echo "Fix already applied' in content, (
            "Patch script must print already-applied message"
        )
