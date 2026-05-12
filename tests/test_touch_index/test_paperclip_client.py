"""Unit tests for paperclip_client.py retry and API helpers.

All external HTTP I/O is mocked so tests run offline.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from urllib3.util import Retry as RetryStrategy


class TestRetryStrategy:
    """Verify the retry strategy is configured correctly."""

    def test_retry_on_session(self):
        """_session() mounts an adapter with the retry strategy."""
        from touch_index.paperclip_client import _session, _RETRY_STRATEGY

        # We need env vars for the session constructor
        with patch.dict(os.environ, {
            "PAPERCLIP_API_KEY": "test-key",
            "PAPERCLIP_API_URL": "https://api.example.com",
            "PAPERCLIP_COMPANY_ID": "test-company",
        }, clear=True):
            s = _session()
            # HTTPAdapter uses an internal Retry object; we verify via the
            # adapter's get_connection method but the simplest check is that
            # the session has adapters mounted for both protocols.
            https_adapter = s.get_adapter("https://api.example.com/foo")
            http_adapter = s.get_adapter("http://api.example.com/foo")
            assert https_adapter.max_retries is not None
            assert http_adapter.max_retries is not None
            # Both adapters use the same retry instance
            assert https_adapter.max_retries.total == 3
            assert http_adapter.max_retries.total == 3
            assert https_adapter.max_retries.backoff_factor == 0.5
            assert http_adapter.max_retries.backoff_factor == 0.5

    def test_retry_on_board_session(self):
        """_board_session() mounts an adapter with the same retry strategy."""
        from touch_index.paperclip_client import _board_session

        with patch.dict(os.environ, {
            "PAPERCLIP_API_KEY": "test-key",
            "PAPERCLIP_API_URL": "https://api.example.com",
            "PAPERCLIP_COMPANY_ID": "test-company",
        }, clear=True):
            s = _board_session()
            https_adapter = s.get_adapter("https://api.example.com/foo")
            assert https_adapter.max_retries.total == 3
            assert https_adapter.max_retries.backoff_factor == 0.5

    def test_retry_status_codes(self):
        """Retry should cover 408, 429, 5xx."""
        from touch_index.paperclip_client import _RETRY_STRATEGY

        assert isinstance(_RETRY_STRATEGY, RetryStrategy)
        assert 408 in _RETRY_STRATEGY.status_forcelist
        assert 429 in _RETRY_STRATEGY.status_forcelist
        assert 500 in _RETRY_STRATEGY.status_forcelist
        assert 502 in _RETRY_STRATEGY.status_forcelist
        assert 503 in _RETRY_STRATEGY.status_forcelist
        assert 504 in _RETRY_STRATEGY.status_forcelist

    def test_retry_allowed_methods(self):
        """GET, PATCH, and POST should be retryable."""
        from touch_index.paperclip_client import _RETRY_STRATEGY

        assert "GET" in _RETRY_STRATEGY.allowed_methods
        assert "PATCH" in _RETRY_STRATEGY.allowed_methods
        assert "POST" in _RETRY_STRATEGY.allowed_methods

    def test_retry_count(self):
        """Should retry up to 3 times."""
        from touch_index.paperclip_client import _RETRY_STRATEGY

        assert _RETRY_STRATEGY.total == 3
