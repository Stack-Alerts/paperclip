"""Regression tests for BTCAAAAA-25851: Backup Dead-Man's-Switch Monitor.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25851
Component: scripts/backup_deadman_switch.py,
            .github/workflows/backup-deadman-switch.yml,
            deploy/systemd/paperclip-backup.service,
            deploy/systemd/paperclip-backup.timer,
            docs/runbook-backup-restore.md

Root cause: N/A — monitoring infrastructure enhancement. The dead-man switch
monitors Paperclip backup liveness every 30 min via GitHub Actions by reading
the last-success.json state file and creating critical alert issues assigned to
CTO when the offsite backup exceeds the threshold (interval + grace period).
This enhancement adds unit tests, a regression test shim, GH Actions step
summary, and log rotation to the dead-man switch.

This file re-exports the existing dead-man switch unit tests from
tests/test_scripts/test_backup_deadman_switch.py so the Impact Gate runner
can discover them by issue ID. The canonical tests live in
tests/test_scripts/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25851"),
    pytest.mark.regression,
]

from tests.test_scripts.test_backup_deadman_switch import (  # noqa: E402, F401
    TestReadLastSuccess,
    TestGetBackupAgeHours,
    TestFindExistingAlert,
    TestCreateAlert,
    TestRun,
)
