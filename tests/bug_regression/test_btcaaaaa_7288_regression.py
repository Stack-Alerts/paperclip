"""
Regression tests for BTCAAAAA-7288: add SKIPPED gate status to impact gate scan,
extend secrets audit to .md files, add BTC-Trade-Engine-PaperClip prefix to
comment_extractor, add bug worker runbook.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-7288
Fixed in commit: 1a56db58

Components:
  - scripts/scan_fix_issues_done.py — added SKIPPED to _GATE_HEADER_RE and gated dict
  - scripts/audit/secrets_audit.py — extended scan to docs/**/*.md
  - src/touch_index/comment_extractor.py — added BTC-Trade-Engine-PaperClip prefix
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-7288"),
    pytest.mark.regression,
]

from tests.test_impact_gate.test_scan_done import (  # noqa: E402, F401
    TestGateHeaderRegex,
    TestCheckGateStatus,
    TestScanFunction,
)

from tests.test_touch_index.test_comment_extractor import (  # noqa: E402, F401
    TestNormalise,
)


class TestSecretsAuditMdFiles:
    """Verify secrets_audit scan_file() handles .md files (extended in BTCAAAAA-7288)."""

    def test_scan_file_finds_aws_key_in_md(self):
        from pathlib import Path
        from scripts.audit.secrets_audit import scan_file

        fp = Path("/tmp/_test_secrets_audit_7288.md")
        fp.write_text('AWS_ACCESS_KEY="AKIAIOSFODNN7EXAMPLE"')
        try:
            findings = scan_file(fp)
            assert any("hardcoded_aws_access_key" in f for f in findings)
        finally:
            fp.unlink(missing_ok=True)

    def test_scan_file_ignores_benign_md(self):
        from pathlib import Path
        from scripts.audit.secrets_audit import scan_file

        fp = Path("/tmp/_test_secrets_audit_7288_benign.md")
        fp.write_text("# Runbook\n\nUse os.environ for credentials.\n")
        try:
            findings = scan_file(fp)
            assert findings == []
        finally:
            fp.unlink(missing_ok=True)

    def test_scan_file_finds_api_key_in_md(self):
        from pathlib import Path
        from scripts.audit.secrets_audit import scan_file

        fp = Path("/tmp/_test_secrets_audit_7288_api.md")
        fp.write_text('api_key="deadbeef12345678"')
        try:
            findings = scan_file(fp)
            assert any("hardcoded_api_key" in f for f in findings)
        finally:
            fp.unlink(missing_ok=True)

    def test_docs_dir_is_configured(self):
        from scripts.audit.secrets_audit import DOCS_DIR

        assert DOCS_DIR == Path(__file__).parents[2] / "docs"
