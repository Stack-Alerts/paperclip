"""Simple HTTP server for the Blast Radius query API and webhook handler.

Endpoints
---------
GET  /api/blast-radius?files=path/a.py&files=path/b.py

POST /api/webhook/issue-status-changed
  Paperclip issue_status_changed webhook receiver.  Expects JSON body:
  {
    "event": "issue_status_changed",
    "issue": {"id": "<uuid>", ...},
    "previousStatus": "in_progress"
  }
  Calls ``process_issue()`` and returns the report result.

Returns JSON:
{
  "fr_impact_set": [...],
  "regression_set": [...],
  "downstream_set": [],
  "downstream_note": "Phase 2 dep graph not yet available"
}

Usage
-----
    python -m blast_radius.api_server              # default port 8765
    python -m blast_radius.api_server --port 9000
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from .query import query_blast_radius, to_json_dict
from .worker import process_issue

log = logging.getLogger(__name__)
DEFAULT_PORT = int(__import__("os").environ.get("BLAST_RADIUS_PORT", "8765"))


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # suppress default access log to stderr
        log.info(fmt, *args)

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return None
        try:
            raw = self.rfile.read(length)
            return json.loads(raw)
        except (json.JSONDecodeError, OSError):
            return None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/blast-radius":
            self._send_json(404, {"error": "not found"})
            return

        params = parse_qs(parsed.query)
        files = params.get("files", [])

        if not files:
            self._send_json(400, {"error": "at least one `files` query param is required"})
            return

        try:
            data = query_blast_radius(files)
            self._send_json(200, to_json_dict(data))
        except Exception as exc:
            log.error("Query failed: %s", exc)
            self._send_json(500, {"error": str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/webhook/issue-status-changed":
            self._send_json(404, {"error": "not found"})
            return

        body = self._read_body()
        if body is None:
            self._send_json(400, {"error": "invalid or empty JSON body"})
            return

        issue_id = body.get("issue", {}).get("id") or body.get("issue_id")
        if not issue_id:
            self._send_json(400, {"error": "missing issue.id or issue_id in payload"})
            return

        old_status = body.get("previousStatus") or body.get("old_status")
        dry_run = body.get("dry_run", False)

        log.info(
            "Webhook: issue_status_changed for %s (old_status=%s, dry_run=%s)",
            issue_id, old_status, dry_run,
        )

        try:
            result = process_issue(
                issue_id,
                dry_run=bool(dry_run),
                old_status=old_status,
            )
            if result is None:
                result = {"issue": issue_id, "status": "skipped", "reason": "not eligible"}
            self._send_json(200, result)
        except Exception as exc:
            log.error("Webhook processing failed for %s: %s", issue_id, exc)
            self._send_json(500, {"error": str(exc), "issue": issue_id})


def serve(port: int = DEFAULT_PORT) -> None:
    server = HTTPServer(("0.0.0.0", port), _Handler)
    log.info("Blast Radius API server listening on http://0.0.0.0:%d", port)
    server.serve_forever()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Blast Radius HTTP API server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    serve(port=args.port)
