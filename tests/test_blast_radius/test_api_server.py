"""Unit tests for blast_radius.api_server — no live network required."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from blast_radius.api_server import _Handler, serve, DEFAULT_PORT
from blast_radius.query import BlastRadiusData


def _make_handler(path: str, method: str = "GET", body: bytes | None = None):
    handler = _Handler.__new__(_Handler)
    handler.path = path
    handler.command = method
    handler.headers = MagicMock()
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = body or b""
    handler.wfile = MagicMock()
    handler.client_address = ("127.0.0.1", 12345)
    handler.server = MagicMock()
    handler.close_connection = True
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


# ---------------------------------------------------------------------------
# GET /api/blast-radius
# ---------------------------------------------------------------------------


class TestHandlerGet:
    def test_404_on_wrong_path(self):
        handler = _make_handler("/api/other")
        handler._send_json = MagicMock()
        handler.do_GET()

        handler._send_json.assert_called_once_with(404, {"error": "not found"})

    def test_400_on_missing_files(self):
        handler = _make_handler("/api/blast-radius")
        handler._send_json = MagicMock()
        handler.do_GET()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "files" in args[1]["error"]

    def test_200_queries_and_returns_result(self, monkeypatch):
        handler = _make_handler("/api/blast-radius?files=src/foo.py&files=src/bar.py")
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server.query_blast_radius",
            lambda files: BlastRadiusData(),
        )

        handler.do_GET()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["fr_impact_set"] == []

    def test_500_on_query_error(self, monkeypatch):
        handler = _make_handler("/api/blast-radius?files=src/bad.py")
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server.query_blast_radius",
            lambda files: (_ for _ in ()).throw(RuntimeError("DB crashed")),
        )

        handler.do_GET()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 500
        assert "DB crashed" in args[1]["error"]

    def test_send_json_writes_correct_payload(self):
        handler = _make_handler("/api/blast-radius")

        handler._send_json(200, {"status": "ok"})

        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/json")
        handler.end_headers.assert_called_once()
        written = b"".join(c[0][0] for c in handler.wfile.write.call_args_list)
        payload = json.loads(written.decode())
        assert payload == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/webhook/issue-status-changed
# ---------------------------------------------------------------------------


class TestHandlerPost:
    def test_404_on_wrong_path(self):
        handler = _make_handler("/api/other", method="POST")
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once_with(404, {"error": "not found"})

    def test_400_on_empty_body(self):
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
        )
        handler.headers.get.return_value = "0"
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "invalid" in args[1]["error"]

    def test_400_on_missing_issue_id(self):
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps({"event": "issue_status_changed"}).encode(),
        )
        handler.headers.get.return_value = str(len(
            json.dumps({"event": "issue_status_changed"})
        ))
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "missing" in args[1]["error"]

    def test_200_processes_issue_from_nested_payload(self, monkeypatch):
        payload = {
            "event": "issue_status_changed",
            "issue": {"id": "issue-uuid-42", "identifier": "BTCAAAAA-100"},
            "previousStatus": "in_progress",
        }
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: {
                "issue": "BTCAAAAA-100",
                "dry_run": False,
            },
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-100"

    def test_200_processes_issue_from_flat_payload(self, monkeypatch):
        payload = {
            "issue_id": "issue-uuid-42",
            "old_status": "in_progress",
        }
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: {
                "issue": "BTCAAAAA-100",
                "dry_run": False,
            },
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-100"

    def test_200_handles_skipped_result(self, monkeypatch):
        payload = {
            "issue_id": "issue-uuid-99",
            "old_status": "in_progress",
        }
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: None,
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["status"] == "skipped"

    def test_500_on_processing_error(self, monkeypatch):
        payload = {
            "issue_id": "issue-uuid-500",
        }
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: (
                (_ for _ in ()).throw(RuntimeError("API timeout"))
            ),
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 500
        assert "API timeout" in args[1]["error"]

    def test_passes_dry_run_flag(self, monkeypatch):
        payload = {
            "issue_id": "issue-uuid-42",
            "dry_run": True,
        }
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        captured = {}

        def tracking_process(issue_id, dry_run=False, old_status=None, force_reprocess=False):
            captured["dry_run"] = dry_run
            return {"issue": "BTCAAAAA-100", "dry_run": dry_run}

        monkeypatch.setattr(
            "blast_radius.api_server.process_issue",
            tracking_process,
        )

        handler.do_POST()

        assert captured["dry_run"] is True
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[1]["dry_run"] is True

    def test_passes_force_reprocess_flag(self, monkeypatch):
        payload = {
            "issue_id": "issue-uuid-42",
            "force_reprocess": True,
        }
        handler = _make_handler(
            "/api/webhook/issue-status-changed",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        captured = {}

        def tracking_process(issue_id, dry_run=False, old_status=None, force_reprocess=False):
            captured["force_reprocess"] = force_reprocess
            return {"issue": "BTCAAAAA-100", "dry_run": dry_run}

        monkeypatch.setattr(
            "blast_radius.api_server.process_issue",
            tracking_process,
        )

        handler.do_POST()

        assert captured["force_reprocess"] is True
        handler._send_json.assert_called_once()


# ---------------------------------------------------------------------------
# _read_body
# ---------------------------------------------------------------------------


class TestReadBody:
    def test_returns_none_on_zero_length(self):
        handler = _make_handler("/")
        handler.headers.get.return_value = "0"
        assert handler._read_body() is None

    def test_returns_none_on_bad_json(self):
        handler = _make_handler("/")
        handler.headers.get.return_value = "5"
        handler.rfile.read.return_value = b"NOT J"
        assert handler._read_body() is None

    def test_returns_parsed_json(self):
        handler = _make_handler("/")
        handler.headers.get.return_value = "20"
        handler.rfile.read.return_value = b'{"key": "value"}'
        assert handler._read_body() == {"key": "value"}


# ---------------------------------------------------------------------------
# serve()
# ---------------------------------------------------------------------------


class TestServe:
    def test_default_port(self):
        assert DEFAULT_PORT == 8765

    def test_serve_creates_http_server(self, monkeypatch):
        server_instance = MagicMock()
        server_cls = MagicMock(return_value=server_instance)

        monkeypatch.setattr("blast_radius.api_server.HTTPServer", server_cls)

        serve(port=9999)

        server_cls.assert_called_once_with(("0.0.0.0", 9999), _Handler)
        server_instance.serve_forever.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/webhook/fr-issue-event
# ---------------------------------------------------------------------------


class _MockResult:
    def __init__(self, identifier, files_indexed, source, skipped_no_commits, issue_id="00000000-0000-0000-0000-000000000000"):
        self.issue_identifier = identifier
        self.issue_id = issue_id
        self.files_indexed = files_indexed
        self.source = source
        self.skipped_no_commits = skipped_no_commits


class TestHandlerFrWebhook:
    def test_404_on_wrong_path(self):
        handler = _make_handler("/api/webhook/issue-status-changed", method="POST")
        handler._send_json = MagicMock()
        handler.do_POST()
        # Should route to the existing status-changed handler, not 404
        args = handler._send_json.call_args[0]
        assert args[0] != 404 or "not found" not in args[1].get("error", "")

    def test_400_on_empty_body(self):
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
        )
        handler.headers.get.return_value = "0"
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "invalid" in args[1]["error"]

    def test_400_on_missing_issue_id(self):
        payload = {"event": "issue_created"}
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "missing" in args[1]["error"]

    def test_200_skipped_when_not_fdr_issue(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue": {"id": "non-fdr-uuid"},
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        def mock_process(engine, issue_id, dry_run=False):
            return None  # not an FDR-labelled issue

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            mock_process,
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["status"] == "skipped"

    def test_200_ingests_fr_issue_successfully(self, monkeypatch):
        payload = {
            "event": "issue_updated",
            "issue": {"id": "fdr-uuid-42"},
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1200", 3, "comments", False,
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-1200"
        assert args[1]["files_indexed"] == 3
        assert args[1]["source"] == "comments"
        assert args[1]["skipped_no_commits"] is False
        assert args[1]["transitioned_to_done"] is True

    def test_passes_dry_run_flag(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue": {"id": "fdr-uuid-42"},
            "dry_run": True,
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        captured = {}

        def tracking_process(engine, issue_id, dry_run=False):
            captured["dry_run"] = dry_run
            return _MockResult("BTCAAAAA-1200", 1, "comments", False)

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            tracking_process,
        )

        handler.do_POST()

        assert captured["dry_run"] is True

    def test_500_on_processing_error(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue": {"id": "fdr-uuid-500"},
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: (
                (_ for _ in ()).throw(RuntimeError("DB connection failed"))
            ),
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 500
        assert "DB connection failed" in args[1]["error"]

    def test_handles_flat_issue_id_payload(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue_id": "flat-uuid-99",
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        captured = {}

        def tracking_process(engine, issue_id, dry_run=False):
            captured["issue_id"] = issue_id
            return _MockResult("BTCAAAAA-99", 1, "git", False)

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            tracking_process,
        )

        handler.do_POST()

        assert captured["issue_id"] == "flat-uuid-99"
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200

    def test_200_transitions_to_done(self, monkeypatch):
        """When dry_run=false, issue is transitioned to done."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "fdr-uuid-42"},
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2000", 2, "comments", False, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["transitioned_to_done"] is True

    def test_validate_true_passes_validation(self, monkeypatch):
        """validate=true: FR quality checks pass, validation_passed=true."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "fdr-uuid-42"},
            "validate": True,
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2001", 3, "git", False, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )
        quality_report = MagicMock()
        quality_report.passed = True
        monkeypatch.setattr(
            "touch_index.quality.run_quality_checks",
            lambda engine: quality_report,
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["validation_passed"] is True

    def test_validate_true_fails_validation(self, monkeypatch):
        """validate=true: FR quality checks fail, validation_passed=false."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "fdr-uuid-42"},
            "validate": True,
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2002", 0, "none", True, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )
        quality_report = MagicMock()
        quality_report.passed = False
        monkeypatch.setattr(
            "touch_index.quality.run_quality_checks",
            lambda engine: quality_report,
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["validation_passed"] is False

    def test_validate_true_validation_error(self, monkeypatch):
        """validate=true: FR quality checks raise, validation_passed=false."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "fdr-uuid-42"},
            "validate": True,
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2003", 1, "comments", False, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )
        monkeypatch.setattr(
            "touch_index.quality.run_quality_checks",
            lambda engine: (_ for _ in ()).throw(RuntimeError("DB error")),
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["validation_passed"] is False

    def test_validate_false_no_validation(self, monkeypatch):
        """validate=false: FR quality checks not run, no validation_passed."""
        payload = {
            "event": "issue_created",
            "issue": {"id": "fdr-uuid-42"},
            "validate": False,
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2004", 2, "git", False, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )
        mock_quality = MagicMock()
        monkeypatch.setattr(
            "touch_index.quality.run_quality_checks",
            mock_quality,
        )

        handler.do_POST()

        mock_quality.assert_not_called()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert "validation_passed" not in args[1]

    def test_validate_not_in_body_no_validation(self, monkeypatch):
        """validate absent: FR quality checks not run, no validation_passed."""
        payload = {
            "event": "issue_created",
            "issue": {"id": "fdr-uuid-42"},
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2005", 3, "git", False, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )
        mock_quality = MagicMock()
        monkeypatch.setattr(
            "touch_index.quality.run_quality_checks",
            mock_quality,
        )

        handler.do_POST()

        mock_quality.assert_not_called()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert "validation_passed" not in args[1]

    def test_transition_failure_logged(self, monkeypatch):
        """When transition_issue_status raises, transitioned_to_done is false."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "fdr-uuid-42"},
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2006", 1, "comments", False, "fdr-uuid-42",
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: (_ for _ in ()).throw(RuntimeError("API error")),
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["transitioned_to_done"] is False

    def test_dry_run_skips_transition(self, monkeypatch):
        """When dry_run=true, transition_issue_status is not called."""
        payload = {
            "event": "issue_created",
            "issue": {"id": "fdr-uuid-42"},
            "dry_run": True,
        }
        handler = _make_handler(
            "/api/webhook/fr-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_fr_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.fr_worker.process_fr_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-2007", 0, "git", False, "fdr-uuid-42",
            ),
        )
        mock_transition = MagicMock()
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            mock_transition,
        )

        handler.do_POST()

        mock_transition.assert_not_called()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["transitioned_to_done"] is False

class TestHandlerBugWebhook:
    def test_404_on_wrong_path(self):
        handler = _make_handler("/api/webhook/issue-status-changed", method="POST")
        handler._send_json = MagicMock()
        handler.do_POST()
        # Should route to the existing status-changed handler, not 404
        args = handler._send_json.call_args[0]
        assert args[0] != 404 or "not found" not in args[1].get("error", "")

    def test_400_on_empty_body(self):
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
        )
        handler.headers.get.return_value = "0"
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "invalid" in args[1]["error"]

    def test_400_on_missing_issue_id(self):
        payload = {"event": "issue_created"}
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()
        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "missing" in args[1]["error"]

    def test_200_skipped_when_fdr_issue(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue": {"id": "fdr-uuid"},
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        def mock_process(engine, issue_id, dry_run=False):
            return None  # FDR-labelled issue, skipped by process_bug_issue

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            mock_process,
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["status"] == "skipped"

    def test_200_ingests_bug_issue_successfully(self, monkeypatch):
        payload = {
            "event": "issue_updated",
            "issue": {"id": "bug-uuid-42"},
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1300", 2, "git", False,
            ),
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-1300"
        assert args[1]["files_indexed"] == 2
        assert args[1]["source"] == "git"
        assert args[1]["skipped_no_commits"] is False
        assert args[1]["transitioned_to_done"] is True

    def test_passes_dry_run_flag(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue": {"id": "bug-uuid-42"},
            "dry_run": True,
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        captured = {}

        def tracking_process(engine, issue_id, dry_run=False):
            captured["dry_run"] = dry_run
            return _MockResult("BTCAAAAA-1300", 1, "git", False)

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            tracking_process,
        )
        monkeypatch.setattr(
            "touch_index.paperclip_client.transition_issue_status",
            lambda issue_id, status: None,
        )

        handler.do_POST()

        assert captured["dry_run"] is True

    def test_500_on_processing_error(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue": {"id": "bug-uuid-500"},
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: (
                (_ for _ in ()).throw(RuntimeError("DB connection failed"))
            ),
        )

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 500
        assert "DB connection failed" in args[1]["error"]

    def test_handles_flat_issue_id_payload(self, monkeypatch):
        payload = {
            "event": "issue_created",
            "issue_id": "flat-bug-uuid-99",
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        captured = {}

        def tracking_process(engine, issue_id, dry_run=False):
            captured["issue_id"] = issue_id
            return _MockResult("BTCAAAAA-99", 1, "git", False)

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            tracking_process,
        )

        handler.do_POST()

        assert captured["issue_id"] == "flat-bug-uuid-99"
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200

    def test_validate_true_passes_validation(self, monkeypatch):
        """validate=true: validation runs and passes, validation_passed=true in response."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "bug-uuid-42"},
            "validate": True,
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1301", 2, "git", False,
            ),
        )
        quality_report = MagicMock()
        quality_report.passed = True
        monkeypatch.setattr(
            "touch_index.quality.run_bug_quality_checks",
            lambda engine: quality_report,
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-1301"
        assert args[1]["validation_passed"] is True

    def test_validate_true_fails_validation(self, monkeypatch):
        """validate=true: validation fails, validation_passed=false in response."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "bug-uuid-42"},
            "validate": True,
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1302", 0, "none", True,
            ),
        )
        quality_report = MagicMock()
        quality_report.passed = False
        monkeypatch.setattr(
            "touch_index.quality.run_bug_quality_checks",
            lambda engine: quality_report,
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-1302"
        assert args[1]["validation_passed"] is False

    def test_validate_true_validation_error(self, monkeypatch):
        """validate=true: validation raises, validation_passed=false in response."""
        payload = {
            "event": "issue_updated",
            "issue": {"id": "bug-uuid-42"},
            "validate": True,
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1303", 1, "comments", False,
            ),
        )
        monkeypatch.setattr(
            "touch_index.quality.run_bug_quality_checks",
            lambda engine: (_ for _ in ()).throw(RuntimeError("DB error")),
        )

        handler.do_POST()

        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["validation_passed"] is False

    def test_validate_false_no_validation_in_response(self, monkeypatch):
        """validate=false: validation not run, no validation_passed in response."""
        payload = {
            "event": "issue_created",
            "issue": {"id": "bug-uuid-42"},
            "validate": False,
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1304", 2, "git", False,
            ),
        )
        mock_quality = MagicMock()
        monkeypatch.setattr(
            "touch_index.quality.run_bug_quality_checks",
            mock_quality,
        )

        handler.do_POST()

        mock_quality.assert_not_called()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert "validation_passed" not in args[1]

    def test_validate_not_in_body_no_validation(self, monkeypatch):
        """validate absent from body: validation not run, no validation_passed in response."""
        payload = {
            "event": "issue_created",
            "issue": {"id": "bug-uuid-42"},
        }
        handler = _make_handler(
            "/api/webhook/bug-issue-event",
            method="POST",
            body=json.dumps(payload).encode(),
        )
        handler.headers.get.return_value = str(len(json.dumps(payload)))
        handler._send_json = MagicMock()

        monkeypatch.setattr(
            "blast_radius.api_server._get_bug_engine",
            lambda: MagicMock(),
        )
        monkeypatch.setattr(
            "touch_index.bug_worker.process_bug_issue",
            lambda engine, issue_id, dry_run=False: _MockResult(
                "BTCAAAAA-1305", 3, "git", False,
            ),
        )
        mock_quality = MagicMock()
        monkeypatch.setattr(
            "touch_index.quality.run_bug_quality_checks",
            mock_quality,
        )

        handler.do_POST()

        mock_quality.assert_not_called()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert "validation_passed" not in args[1]
