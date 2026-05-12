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

POST /api/webhook/fr-issue-event
  Paperclip issue_created / issue_updated webhook receiver for FDR (Feature
  Design Requirement) issues.  Expects JSON body:
  {
    "event": "issue_created",
    "issue": {"id": "<uuid>", ...}
  }
  Calls ``touch_index.fr_worker.process_fr_issue()`` to upsert file
  references from done-comments, git commits, or the issue description.
  Returns the ingestion result.

POST /api/webhook/bug-issue-event
  Paperclip issue_created / issue_updated webhook receiver for bug (non-FDR)
  issues.  Expects JSON body:
  {
    "event": "issue_created",
    "issue": {"id": "<uuid>", ...}
  }
  Calls ``touch_index.bug_worker.process_bug_issue()`` to upsert file
  references from git commits or issue comments.
  Returns the ingestion result.

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
from typing import Any


log = logging.getLogger(__name__)
DEFAULT_PORT = int(__import__("os").environ.get("BLAST_RADIUS_PORT", "8765"))

# Lazy engines for webhook ingestion (created once, then reused across requests).
_FR_ENGINE = None
_BUG_ENGINE = None


def _get_fr_engine():
    global _FR_ENGINE
    if _FR_ENGINE is None:
        from touch_index.db import get_engine, health_check

        _FR_ENGINE = get_engine()
        if not health_check(_FR_ENGINE):
            log.error("FR webhook: DB health check failed — engine unusable")
            _FR_ENGINE = None
            raise RuntimeError("Database health check failed")
    return _FR_ENGINE


def _get_bug_engine():
    global _BUG_ENGINE
    if _BUG_ENGINE is None:
        from touch_index.db import get_engine, health_check

        _BUG_ENGINE = get_engine()
        if not health_check(_BUG_ENGINE):
            log.error("Bug webhook: DB health check failed — engine unusable")
            _BUG_ENGINE = None
            raise RuntimeError("Database health check failed")
    return _BUG_ENGINE


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
            self._send_json(
                400, {"error": "at least one `files` query param is required"}
            )
            return

        try:
            data = query_blast_radius(files)
            self._send_json(200, to_json_dict(data))
        except Exception as exc:
            log.error("Query failed: %s", exc)
            self._send_json(500, {"error": str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/webhook/bug-issue-event":
            self._handle_bug_webhook()
            return

        if parsed.path == "/api/webhook/fr-issue-event":
            self._handle_fr_webhook()
            return

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
        force_reprocess = body.get("force_reprocess", False)

        log.info(
            "Webhook: issue_status_changed for %s (old_status=%s, dry_run=%s, force_reprocess=%s)",
            issue_id,
            old_status,
            dry_run,
            force_reprocess,
        )

        try:
            result = process_issue(
                issue_id,
                dry_run=bool(dry_run),
                old_status=old_status,
                force_reprocess=bool(force_reprocess),
            )
            if result is None:
                result = {
                    "issue": issue_id,
                    "status": "skipped",
                    "reason": "not eligible",
                }
            self._send_json(200, result)
        except Exception as exc:
            log.error("Webhook processing failed for %s: %s", issue_id, exc)
            self._send_json(500, {"error": str(exc), "issue": issue_id})

    # ------------------------------------------------------------------
    # FR issue webhook
    # ------------------------------------------------------------------

    def _handle_fr_webhook(self):
        """Handle POST /api/webhook/fr-issue-event (FR issue created/updated).

        Expects JSON body:
        {
            "event": "issue_created",
            "issue": {"id": "<uuid>", ...},
            "dry_run": false,
            "validate": false
        }

        Transitions the issue to done after successful ingestion
        unless dry_run is true.  If validate is true, runs
        FR data quality checks after ingestion and includes the result
        in the response.
        """
        body = self._read_body()
        if body is None:
            self._send_json(400, {"error": "invalid or empty JSON body"})
            return

        issue_id = body.get("issue", {}).get("id") or body.get("issue_id")
        if not issue_id:
            self._send_json(400, {"error": "missing issue.id or issue_id in payload"})
            return

        event_type = body.get("event", "unknown")
        dry_run = body.get("dry_run", False)
        validate = body.get("validate", False)

        log.info(
            "FR webhook: %s for issue %s (dry_run=%s, validate=%s)",
            event_type,
            issue_id,
            dry_run,
            validate,
        )

        try:
            from touch_index.fr_worker import process_fr_issue
            from touch_index.paperclip_client import transition_issue_status
            from touch_index.quality import run_quality_checks

            engine = _get_fr_engine()
            result = process_fr_issue(engine, issue_id, dry_run=bool(dry_run))
            if result is None:
                self._send_json(
                    200,
                    {
                        "issue": issue_id,
                        "status": "skipped",
                        "reason": "not an FDR-labelled issue or not found",
                    },
                )
                return

            transitioned = False
            if not dry_run:
                try:
                    transition_issue_status(result.issue_id, "done")
                    transitioned = True
                    log.info("FR webhook: marked %s as done", result.issue_identifier)
                except Exception as exc:
                    log.error(
                        "FR webhook: failed to mark %s as done: %s",
                        result.issue_identifier,
                        exc,
                    )

            validation_passed: bool | None = None
            if validate:
                try:
                    report = run_quality_checks(engine)
                    validation_passed = report.passed
                    if not report.passed:
                        log.error(
                            "FR webhook: VALIDATION FAILED after ingestion for %s",
                            result.issue_identifier,
                        )
                    else:
                        log.info(
                            "FR webhook: VALIDATION PASSED for %s",
                            result.issue_identifier,
                        )
                except Exception as exc:
                    log.error(
                        "FR webhook: validation error for %s: %s",
                        result.issue_identifier,
                        exc,
                    )
                    validation_passed = False

            response: dict[str, Any] = {
                "issue": result.issue_identifier,
                "files_indexed": result.files_indexed,
                "source": result.source,
                "skipped_no_commits": result.skipped_no_commits,
                "transitioned_to_done": transitioned,
            }
            if validation_passed is not None:
                response["validation_passed"] = validation_passed
            self._send_json(200, response)
        except Exception as exc:
            log.error("FR webhook processing failed for %s: %s", issue_id, exc)
            self._send_json(500, {"error": str(exc), "issue": issue_id})

    # ------------------------------------------------------------------
    # Bug issue webhook
    # ------------------------------------------------------------------

    def _handle_bug_webhook(self):
        """Handle POST /api/webhook/bug-issue-event (bug issue created/updated).

        Expects JSON body:
        {
            "event": "issue_created",
            "issue": {"id": "<uuid>", ...},
            "dry_run": false,
            "validate": false
        }

        Transitions the issue to done after successful ingestion
        unless dry_run is true.  If validate is true, runs
        bug data quality checks after ingestion and includes the result
        in the response.
        """
        body = self._read_body()
        if body is None:
            self._send_json(400, {"error": "invalid or empty JSON body"})
            return

        issue_id = body.get("issue", {}).get("id") or body.get("issue_id")
        if not issue_id:
            self._send_json(400, {"error": "missing issue.id or issue_id in payload"})
            return

        event_type = body.get("event", "unknown")
        dry_run = body.get("dry_run", False)
        validate = body.get("validate", False)

        log.info(
            "Bug webhook: %s for issue %s (dry_run=%s, validate=%s)",
            event_type,
            issue_id,
            dry_run,
            validate,
        )

        try:
            from touch_index.bug_worker import process_bug_issue
            from touch_index.paperclip_client import transition_issue_status
            from touch_index.quality import run_bug_quality_checks

            engine = _get_bug_engine()
            result = process_bug_issue(engine, issue_id, dry_run=bool(dry_run))
            if result is None:
                self._send_json(
                    200,
                    {
                        "issue": issue_id,
                        "status": "skipped",
                        "reason": "not a bug issue (FDR-labelled or not found)",
                    },
                )
                return

            transitioned = False
            if not dry_run:
                try:
                    transition_issue_status(result.issue_id, "done")
                    transitioned = True
                    log.info("Bug webhook: marked %s as done", result.issue_identifier)
                except Exception as exc:
                    log.error(
                        "Bug webhook: failed to mark %s as done: %s",
                        result.issue_identifier,
                        exc,
                    )

            validation_passed: bool | None = None
            if validate:
                try:
                    report = run_bug_quality_checks(engine)
                    validation_passed = report.passed
                    if not report.passed:
                        log.error(
                            "Bug webhook: VALIDATION FAILED after ingestion for %s",
                            result.issue_identifier,
                        )
                    else:
                        log.info(
                            "Bug webhook: VALIDATION PASSED for %s",
                            result.issue_identifier,
                        )
                except Exception as exc:
                    log.error(
                        "Bug webhook: validation error for %s: %s",
                        result.issue_identifier,
                        exc,
                    )
                    validation_passed = False

            response: dict[str, Any] = {
                "issue": result.issue_identifier,
                "files_indexed": result.files_indexed,
                "source": result.source,
                "skipped_no_commits": result.skipped_no_commits,
                "transitioned_to_done": transitioned,
            }
            if validation_passed is not None:
                response["validation_passed"] = validation_passed
            self._send_json(200, response)
        except Exception as exc:
            log.error("Bug webhook processing failed for %s: %s", issue_id, exc)
            self._send_json(500, {"error": str(exc), "issue": issue_id})


def serve(port: int = DEFAULT_PORT) -> None:
    server = HTTPServer(("0.0.0.0", port), _Handler)
    log.info("Blast Radius API server listening on http://0.0.0.0:%d", port)
    server.serve_forever()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    parser = argparse.ArgumentParser(description="Blast Radius HTTP API server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    serve(port=args.port)
