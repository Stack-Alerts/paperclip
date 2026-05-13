"""
Regression tests for BTCAAAAA-1275.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1275

Fix: declare requests dep + document PAPERCLIP_* env vars.

- Added ``requests`` to pyproject.toml (used by paperclip_client and comment_extractor).
- Documented PAPERCLIP_API_URL, PAPERCLIP_API_KEY, and PAPERCLIP_COMPANY_ID in
  .env.example for the touch_index bug/FR workers.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1275"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestRequestsDependencyImportable:
    """Verify ``requests`` is declared and importable post-BTCAAAAA-1275."""

    def test_requests_importable(self) -> None:
        import requests
        assert requests is not None

    def test_requests_has_get(self) -> None:
        import requests
        assert callable(requests.get)


class TestPaperclipEnvVarsDocumented:
    """Verify PAPERCLIP_* env vars are documented in .env.example."""

    @pytest.fixture()
    def env_example_text(self) -> str:
        path = REPO_ROOT / ".env.example"
        assert path.exists(), ".env.example not found"
        return path.read_text(encoding="utf-8")

    def test_paperclip_api_url_documented(self, env_example_text: str) -> None:
        assert "PAPERCLIP_API_URL" in env_example_text

    def test_paperclip_api_key_documented(self, env_example_text: str) -> None:
        assert "PAPERCLIP_API_KEY" in env_example_text

    def test_paperclip_company_id_documented(self, env_example_text: str) -> None:
        assert "PAPERCLIP_COMPANY_ID" in env_example_text
