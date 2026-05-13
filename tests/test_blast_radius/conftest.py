import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set default env vars for tests that need Paperclip config."""
    monkeypatch.setenv("PAPERCLIP_API_URL", "https://api.paperclip.test")
    monkeypatch.setenv("PAPERCLIP_API_KEY", "test-api-key")
    monkeypatch.setenv("PAPERCLIP_COMPANY_ID", "test-company-id")
    monkeypatch.delenv("BLAST_RADIUS_STATE_FILE", raising=False)
