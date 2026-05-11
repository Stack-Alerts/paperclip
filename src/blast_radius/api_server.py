"""Simple HTTP server for the Blast Radius query API.

Endpoint
--------
GET /api/blast-radius?files=path/a.py&files=path/b.py

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
