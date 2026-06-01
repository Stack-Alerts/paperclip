#!/usr/bin/env python3
"""Tests for token_gap_escalation_blocker_verification.py"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Import the module
import token_gap_escalation_blocker_verification as tgev


class TestAuthBlockerDetection(unittest.TestCase):
    """Test auth keyword detection."""

    def test_detects_github_token_keyword(self):
        """Should detect GH_TOKEN in issue title."""
        assert tgev.is_auth_blocker("GH_TOKEN merge failure", "", []) is True

    def test_detects_github_token_in_description(self):
        """Should detect github token in description."""
        assert tgev.is_auth_blocker("", "API error: github token 401", []) is True

    def test_detects_branch_protection(self):
        """Should detect branch protection in title."""
        assert tgev.is_auth_blocker("Branch protection rule blocked", "", []) is True

    def test_detects_403_forbidden(self):
        """Should detect 403 Forbidden error."""
        assert tgev.is_auth_blocker("", "HTTP 403 Forbidden on api.github.com", []) is True

    def test_detects_auth_label(self):
        """Should detect auth label."""
        assert tgev.is_auth_blocker("Some issue", "", ["GITHUB_TOKEN"]) is True

    def test_detects_pab_label(self):
        """Should detect PAT (Personal Access Token) label."""
        assert tgev.is_auth_blocker("", "", ["PAT-token-expired"]) is True

    def test_rejects_non_auth_issue(self):
        """Should reject CTO backup chain blocker."""
        assert tgev.is_auth_blocker("CTO design task", "Waiting for CTO approval", []) is False

    def test_rejects_dependency_blocker(self):
        """Should reject dependency blocker."""
        assert tgev.is_auth_blocker("Blocked on PR merge", "Waiting for PR merge", []) is False

    def test_rejects_no_keywords(self):
        """Should reject issue with no auth keywords."""
        assert tgev.is_auth_blocker("Generic blocker", "Some generic blocking issue", []) is False


class TestBlockerVerification(unittest.TestCase):
    """Test blockedBy verification logic."""

    def test_empty_blocked_by_returns_false(self):
        """Should return False for empty blockedBy."""
        with patch('token_gap_escalation_blocker_verification._api_request') as mock_api:
            mock_api.return_value = {"id": "issue1", "blockedBy": []}
            result = tgev.check_blocker_is_auth_related("issue1")
            assert result is False

    def test_auth_related_blocker_returns_true(self):
        """Should return True if blocker is auth-related."""
        with patch('token_gap_escalation_blocker_verification._api_request') as mock_api:
            mock_api.return_value = {
                "id": "issue1",
                "blockedBy": [
                    {
                        "id": "blocker1",
                        "title": "GH_TOKEN not set",
                        "labels": []
                    }
                ]
            }
            result = tgev.check_blocker_is_auth_related("issue1")
            assert result is True

    def test_non_auth_blocker_returns_false(self):
        """Should return False if blocker is not auth-related."""
        with patch('token_gap_escalation_blocker_verification._api_request') as mock_api:
            mock_api.return_value = {
                "id": "issue1",
                "blockedBy": [
                    {
                        "id": "blocker1",
                        "title": "CTO design task",
                        "labels": []
                    }
                ]
            }
            result = tgev.check_blocker_is_auth_related("issue1")
            assert result is False

    def test_multiple_blockers_auth_match_returns_true(self):
        """Should return True if any of multiple blockers is auth-related."""
        with patch('token_gap_escalation_blocker_verification._api_request') as mock_api:
            mock_api.return_value = {
                "id": "issue1",
                "blockedBy": [
                    {
                        "id": "blocker1",
                        "title": "CTO review",
                        "labels": []
                    },
                    {
                        "id": "blocker2",
                        "title": "GitHub 403 Forbidden error",
                        "labels": []
                    }
                ]
            }
            result = tgev.check_blocker_is_auth_related("issue1")
            assert result is True

    def test_multiple_blockers_no_auth_match_returns_false(self):
        """Should return False if none of multiple blockers is auth-related."""
        with patch('token_gap_escalation_blocker_verification._api_request') as mock_api:
            mock_api.return_value = {
                "id": "issue1",
                "blockedBy": [
                    {
                        "id": "blocker1",
                        "title": "CTO review",
                        "labels": []
                    },
                    {
                        "id": "blocker2",
                        "title": "Dependency PR merge",
                        "labels": []
                    }
                ]
            }
            result = tgev.check_blocker_is_auth_related("issue1")
            assert result is False


class TestDedup(unittest.TestCase):
    """Test dedup window logic."""

    def test_first_escalation_allowed(self):
        """Should allow first escalation (no dedup record)."""
        with patch('token_gap_escalation_blocker_verification.load_escalations_state') as mock_state:
            mock_state.return_value = {}
            result = tgev.should_escalate_issue("issue1")
            assert result is True

    def test_recent_escalation_blocked(self):
        """Should block escalation within 24h."""
        with patch('token_gap_escalation_blocker_verification.load_escalations_state') as mock_state:
            recent_time = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            mock_state.return_value = {"issue1:escalated": recent_time}
            result = tgev.should_escalate_issue("issue1")
            assert result is False

    def test_old_escalation_allowed(self):
        """Should allow escalation after 24h."""
        with patch('token_gap_escalation_blocker_verification.load_escalations_state') as mock_state:
            old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            mock_state.return_value = {"issue1:escalated": old_time}
            result = tgev.should_escalate_issue("issue1")
            assert result is True


if __name__ == '__main__':
    unittest.main()
