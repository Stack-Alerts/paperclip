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
            lambda issue_id, dry_run=False, old_status=None: {
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
            lambda issue_id, dry_run=False, old_status=None: {
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
            lambda issue_id, dry_run=False, old_status=None: None,
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
            lambda issue_id, dry_run=False, old_status=None: (
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

        def tracking_process(issue_id, dry_run=False, old_status=None):
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
    def __init__(self, identifier, files_indexed, source, skipped_no_commits):
        self.issue_identifier = identifier
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

        handler.do_POST()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 200
        assert args[1]["issue"] == "BTCAAAAA-1200"
        assert args[1]["files_indexed"] == 3
        assert args[1]["source"] == "comments"
        assert args[1]["skipped_no_commits"] is False

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
