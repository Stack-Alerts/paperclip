"""Unit tests for blast_radius.api_server — no live network required."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from blast_radius.api_server import _Handler, serve, DEFAULT_PORT
from blast_radius.query import BlastRadiusData


class TestHandler:
    def _make_handler(self, path: str):
        handler = _Handler.__new__(_Handler)
        handler.path = path
        handler.command = "GET"
        handler.headers = MagicMock()
        handler.rfile = MagicMock()
        handler.wfile = MagicMock()
        handler.client_address = ("127.0.0.1", 12345)
        handler.server = MagicMock()
        handler.close_connection = True
        handler.requestline = f"GET {path} HTTP/1.1"
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        return handler

    def test_404_on_wrong_path(self):
        handler = self._make_handler("/api/other")
        handler._send_json = MagicMock()
        handler.do_GET()

        handler._send_json.assert_called_once_with(404, {"error": "not found"})

    def test_400_on_missing_files(self):
        handler = self._make_handler("/api/blast-radius")
        handler._send_json = MagicMock()
        handler.do_GET()

        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        assert args[0] == 400
        assert "files" in args[1]["error"]

    def test_200_queries_and_returns_result(self, monkeypatch):
        handler = self._make_handler("/api/blast-radius?files=src/foo.py&files=src/bar.py")
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
        handler = self._make_handler("/api/blast-radius?files=src/bad.py")
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
        handler = self._make_handler("/api/blast-radius")

        handler._send_json(200, {"status": "ok"})

        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/json")
        handler.end_headers.assert_called_once()
        written = b"".join(c[0][0] for c in handler.wfile.write.call_args_list)
        payload = json.loads(written.decode())
        assert payload == {"status": "ok"}


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
