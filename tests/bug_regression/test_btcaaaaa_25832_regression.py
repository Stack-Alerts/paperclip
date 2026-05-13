"""Regression tests for BTCAAAAA-25832: done-guard prevents reopen loops.

Verifies the three-layer guard:
1. paperclip_client: transition_issue_status_board refuses done→non-done
2. impact_gate/worker: _post_comment + process_issue mute when done
3. blast_radius/generator: _post_comment skips when done
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25832"),
    pytest.mark.regression,
]


def _mock_session(methods=None):
    m = MagicMock()
    m.__enter__.return_value = m
    if methods:
        for name, ret in methods.items():
            getattr(m, name).return_value = ret
    return m


def _issue_desc(files):
    return json.dumps({"touchedFiles": list(files)})


def _fake_br_data():
    from blast_radius.query import BlastRadiusData
    return BlastRadiusData()


def _pass_result():
    return {
        "timestamp": "2026-01-01T00:00:00",
        "status": "PASS",
        "summary": {"total": 10, "passed": 10, "failed": 0, "errors": 0},
        "fr_results": {},
        "bug_results": {},
    }


# ---------------------------------------------------------------------------
# paperclip_client — get_issue_status / is_issue_done / transition guard
# ---------------------------------------------------------------------------


class TestGetIssueStatus:
    def test_returns_status_from_issue(self):
        from touch_index.paperclip_client import get_issue_status

        mock_sess = _mock_session()
        mock_sess.get.return_value.status_code = 200
        mock_sess.get.return_value.json.return_value = {"status": "done"}

        with patch("touch_index.paperclip_client._session", return_value=mock_sess):
            assert get_issue_status("uuid-1") == "done"

    def test_returns_none_on_404(self):
        from touch_index.paperclip_client import get_issue_status

        mock_sess = _mock_session()
        mock_sess.get.return_value.status_code = 404

        with patch("touch_index.paperclip_client._session", return_value=mock_sess):
            assert get_issue_status("missing") is None

    def test_returns_none_on_error(self):
        from touch_index.paperclip_client import get_issue_status

        mock_sess = _mock_session()
        mock_sess.get.side_effect = ConnectionError("no network")

        with patch("touch_index.paperclip_client._session", return_value=mock_sess):
            assert get_issue_status("uuid-x") is None


class TestIsIssueDone:
    def test_true_when_status_is_done(self):
        from touch_index.paperclip_client import is_issue_done
        with patch("touch_index.paperclip_client.get_issue_status", return_value="done"):
            assert is_issue_done("uuid-1") is True

    def test_false_when_status_is_in_review(self):
        from touch_index.paperclip_client import is_issue_done
        with patch("touch_index.paperclip_client.get_issue_status", return_value="in_review"):
            assert is_issue_done("uuid-1") is False

    def test_false_when_status_is_in_progress(self):
        from touch_index.paperclip_client import is_issue_done
        with patch("touch_index.paperclip_client.get_issue_status", return_value="in_progress"):
            assert is_issue_done("uuid-1") is False

    def test_false_when_issue_not_found(self):
        from touch_index.paperclip_client import is_issue_done
        with patch("touch_index.paperclip_client.get_issue_status", return_value=None):
            assert is_issue_done("missing") is False

    def test_false_when_status_empty_string(self):
        from touch_index.paperclip_client import is_issue_done
        with patch("touch_index.paperclip_client.get_issue_status", return_value=""):
            assert is_issue_done("uuid-x") is False


class TestTransitionGuard:
    def test_refuses_done_to_in_progress(self):
        from touch_index.paperclip_client import transition_issue_status_board

        mock_sess = _mock_session()
        with patch("touch_index.paperclip_client.is_issue_done", return_value=True), \
             patch("touch_index.paperclip_client._board_session", return_value=mock_sess):
            transition_issue_status_board("uuid-1", "in_progress")
            mock_sess.patch.assert_not_called()

    def test_refuses_done_to_in_review(self):
        from touch_index.paperclip_client import transition_issue_status_board

        mock_sess = _mock_session()
        with patch("touch_index.paperclip_client.is_issue_done", return_value=True), \
             patch("touch_index.paperclip_client._board_session", return_value=mock_sess):
            transition_issue_status_board("uuid-1", "in_review")
            mock_sess.patch.assert_not_called()

    def test_allows_done_to_done(self):
        from touch_index.paperclip_client import transition_issue_status_board

        mock_sess = _mock_session()
        with patch("touch_index.paperclip_client.is_issue_done", return_value=True), \
             patch("touch_index.paperclip_client._board_session", return_value=mock_sess):
            transition_issue_status_board("uuid-1", "done")
            mock_sess.patch.assert_called_once()

    def test_allows_in_progress_to_done(self):
        from touch_index.paperclip_client import transition_issue_status_board

        mock_sess = _mock_session()
        with patch("touch_index.paperclip_client.is_issue_done", return_value=False), \
             patch("touch_index.paperclip_client._board_session", return_value=mock_sess):
            transition_issue_status_board("uuid-1", "done")
            mock_sess.patch.assert_called_once()

    def test_allows_in_progress_to_in_review_when_not_done(self):
        from touch_index.paperclip_client import transition_issue_status_board

        mock_sess = _mock_session()
        with patch("touch_index.paperclip_client.is_issue_done", return_value=False), \
             patch("touch_index.paperclip_client._board_session", return_value=mock_sess):
            transition_issue_status_board("uuid-1", "in_review")
            mock_sess.patch.assert_called_once()


# ---------------------------------------------------------------------------
# impact_gate/worker — _post_comment done-guard
# ---------------------------------------------------------------------------


class TestImpactGatePostCommentGuard:
    def test_skips_comment_when_issue_done(self, monkeypatch):
        import impact_gate.worker as worker_mod

        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._board_session", lambda: mock_sess)
        monkeypatch.setattr("touch_index.paperclip_client.is_issue_done", lambda _: True)

        result = worker_mod._post_comment("uuid-done", "body")
        assert result is False
        mock_sess.post.assert_not_called()

    def test_posts_comment_when_issue_not_done(self, monkeypatch):
        import impact_gate.worker as worker_mod

        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._board_session", lambda: mock_sess)
        monkeypatch.setattr("touch_index.paperclip_client.is_issue_done", lambda _: False)

        result = worker_mod._post_comment("uuid-active", "body")
        assert result is True
        mock_sess.post.assert_called_once()

    def test_posts_when_guard_check_fails(self, monkeypatch):
        import impact_gate.worker as worker_mod

        mock_sess = MagicMock()
        monkeypatch.setattr("impact_gate.worker._board_session", lambda: mock_sess)
        monkeypatch.setattr(
            "touch_index.paperclip_client.is_issue_done",
            lambda _: (_ for _ in ()).throw(ConnectionError("fail")),
        )

        result = worker_mod._post_comment("uuid-active", "body")
        assert result is True
        mock_sess.post.assert_called_once()


# ---------------------------------------------------------------------------
# impact_gate/worker — process_issue mute when done
# ---------------------------------------------------------------------------


class TestProcessIssueMuteWhenDone:
    def test_skips_when_status_done_no_force(self, monkeypatch):
        import impact_gate.worker as worker_mod

        monkeypatch.setattr(worker_mod, "_get_issue", lambda _: {
            "status": "done", "identifier": "BTCAAAAA-999"
        })

        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment",
                            lambda iid, body: posted.append((iid, body)) or True)

        r = worker_mod.process_issue("uuid-done", dry_run=False)
        assert r["gate_status"] == "SKIPPED"
        assert r["reason"] == "status=done"
        assert len(posted) == 0

    def test_mutes_comments_when_status_done_and_force(self, monkeypatch):
        import impact_gate.worker as worker_mod

        monkeypatch.setattr(worker_mod, "_get_issue", lambda _: {
            "status": "done",
            "identifier": "BTCAAAAA-999",
            "description": _issue_desc(["src/a.py", "src/b.py"]),
        })
        monkeypatch.setattr(worker_mod, "_has_bypass_label", lambda _: False)

        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment",
                            lambda iid, body: posted.append((iid, body)) or True)
        transitions = []
        monkeypatch.setattr("impact_gate.worker.transition_issue_status_board",
                            lambda iid, st: transitions.append((iid, st)))

        monkeypatch.setattr(worker_mod, "run_impact_gate", lambda fr_set, bug_set: _pass_result())
        monkeypatch.setattr("impact_gate.worker.query_blast_radius", lambda fps: _fake_br_data())

        r = worker_mod.process_issue("uuid-done", dry_run=False, force=True)
        assert r["gate_status"] == "PASS"
        assert len(posted) == 0, "no comments on mute"
        assert len(transitions) == 0, "no transitions on mute"

    def test_does_not_mute_when_status_in_review_no_force(self, monkeypatch):
        import impact_gate.worker as worker_mod

        monkeypatch.setattr(worker_mod, "_get_issue", lambda _: {
            "status": "in_review",
            "identifier": "BTCAAAAA-888",
            "description": _issue_desc(["src/a.py"]),
        })
        monkeypatch.setattr(worker_mod, "_has_bypass_label", lambda _: False)

        posted = []
        monkeypatch.setattr(worker_mod, "_post_comment",
                            lambda iid, body: posted.append((iid, body)) or True)
        transitions = []
        monkeypatch.setattr("impact_gate.worker.transition_issue_status_board",
                            lambda iid, st: transitions.append((iid, st)))

        monkeypatch.setattr(worker_mod, "run_impact_gate", lambda fr_set, bug_set: _pass_result())
        monkeypatch.setattr("impact_gate.worker.query_blast_radius", lambda fps: _fake_br_data())

        r = worker_mod.process_issue("uuid-in-review", dry_run=False)
        assert r["gate_status"] == "PASS"
        assert any("PASS" in str(c) for c in posted), "pass comment posted"
        assert len(transitions) == 1, "transition to done"
        assert transitions[0][1] == "done"


# ---------------------------------------------------------------------------
# blast_radius/generator — _post_comment done-guard
# ---------------------------------------------------------------------------


class TestBlastRadiusPostCommentGuard:
    def test_skips_comment_when_issue_done(self):
        from blast_radius.generator import _post_comment

        mock_sess = _mock_session()
        with patch("blast_radius.generator._session", return_value=mock_sess), \
             patch("touch_index.paperclip_client.is_issue_done", return_value=True):
            _post_comment("uuid-done", "body")
            mock_sess.post.assert_not_called()

    def test_posts_comment_when_issue_not_done(self):
        from blast_radius.generator import _post_comment

        mock_sess = _mock_session()
        with patch("blast_radius.generator._session", return_value=mock_sess), \
             patch("touch_index.paperclip_client.is_issue_done", return_value=False), \
             patch("blast_radius.generator._run_headers", return_value={}):
            _post_comment("uuid-active", "body")
            assert mock_sess.post.call_count == 1

    def test_posts_when_guard_check_fails(self):
        from blast_radius.generator import _post_comment

        mock_sess = _mock_session()
        with patch("blast_radius.generator._session", return_value=mock_sess), \
             patch("touch_index.paperclip_client.is_issue_done",
                   side_effect=RuntimeError("fail")), \
             patch("blast_radius.generator._run_headers", return_value={}):
            _post_comment("uuid-active", "body")
            assert mock_sess.post.call_count == 1
