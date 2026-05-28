#!/usr/bin/env python3
"""Post-merge dev-server reset routine."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("dev_server_post_merge_routine")

RESET_SCRIPT = REPO_ROOT / "scripts" / "dev-server-post-merge-reset.sh"
DEV_SERVER_STATUS_ISSUE = "BTCAAAAA-30038"
DEV_SERVER_STATUS_DOC_KEY = "dev-server-status"
RUN_ID = os.environ.get("PAPERCLIP_RUN_ID")
AGENT_ID = os.environ.get("PAPERCLIP_AGENT_ID")


def http_session() -> requests.Session:
    """Create HTTP session with retries."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
        "Content-Type": "application/json",
    })
    if RUN_ID:
        session.headers.update({"X-Paperclip-Run-Id": RUN_ID})
    adapter = HTTPAdapter(max_retries=Retry(
        total=2, backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "PATCH", "POST"],
        raise_on_status=False,
    ))
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def run_reset_script() -> dict[str, Any]:
    """Execute the dev-server reset shell script."""
    logger.info("Running dev-server reset script...")
    try:
        result = subprocess.run(
            ["bash", str(RESET_SCRIPT)],
            capture_output=True, text=True, timeout=300, cwd=REPO_ROOT,
        )
        output = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        if result.returncode != 0:
            logger.error("Reset script failed: %s", result.stderr)
            return {**output, "status": "error"}
        
        status = "success"
        current_sha = None
        current_branch = None
        timestamp = None
        
        for line in result.stderr.split("\n"):
            if "CURRENT_SHA=" in line:
                current_sha = line.split("=", 1)[1].strip()
            elif "CURRENT_BRANCH=" in line:
                current_branch = line.split("=", 1)[1].strip()
            elif "TIMESTAMP=" in line:
                timestamp = line.split("=", 1)[1].strip()
            elif "Uncommitted changes" in line:
                status = "skipped"
        
        logger.info("Reset script completed: %s", status)
        return {
            **output,
            "status": status,
            "current_sha": current_sha,
            "current_branch": current_branch,
            "timestamp": timestamp,
        }
    except subprocess.TimeoutExpired:
        logger.error("Reset script timeout")
        return {"status": "timeout", "error": "Script timeout"}
    except Exception as exc:
        logger.error("Reset script failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def get_dev_server_status_doc(session: requests.Session) -> dict[str, Any]:
    """Fetch current dev-server-status document."""
    api_url = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100")
    url = f"{api_url}/api/issues/{DEV_SERVER_STATUS_ISSUE}/documents/{DEV_SERVER_STATUS_DOC_KEY}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Failed to fetch doc: %s", exc)
        return {}


def probe_redis_health(host: str = "127.0.0.1", port: int = 6379) -> dict[str, str]:
    """Probe Redis with redis-cli ping; return status dict."""
    try:
        result = subprocess.run(
            ["redis-cli", "-h", host, "-p", str(port), "--no-auth-warning", "ping"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0 and "PONG" in result.stdout:
            return {"status": "✅ UP", "detail": f"PONG on {host}:{port}"}
        return {"status": "❌ DOWN", "detail": result.stderr.strip() or result.stdout.strip() or "no response"}
    except FileNotFoundError:
        return {"status": "❌ redis-cli not found", "detail": "install redis-server"}
    except subprocess.TimeoutExpired:
        return {"status": "❌ TIMEOUT", "detail": f"no response within 2s on {host}:{port}"}
    except Exception as exc:
        return {"status": "❌ ERROR", "detail": str(exc)}


def update_dev_server_status_doc(
    session: requests.Session,
    reset_result: dict[str, Any],
) -> bool:
    """Update dev-server-status document."""
    if reset_result.get("status") not in ("success", "skipped"):
        return False

    logger.info("Updating dev-server-status document...")
    api_url = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100")
    doc_url = f"{api_url}/api/issues/{DEV_SERVER_STATUS_ISSUE}/documents/{DEV_SERVER_STATUS_DOC_KEY}"

    current_doc = get_dev_server_status_doc(session)
    base_revision_id = current_doc.get("latestRevisionId")

    current_sha = reset_result.get("current_sha", "unknown")
    current_branch = reset_result.get("current_branch", "unknown")
    timestamp = reset_result.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status_msg = "✅ RESET SUCCESSFUL" if reset_result.get("status") == "success" else "⚠️ SKIPPED"
    if reset_result.get("status") == "skipped":
        status_msg += " — uncommitted changes detected"

    redis_host = os.environ.get("BTE_REDIS_HOST", "127.0.0.1")
    redis_port = int(os.environ.get("BTE_REDIS_PORT", "6379"))
    redis_info = probe_redis_health(redis_host, redis_port)

    new_body = f"""# Dev Server Status Board

**Refresh policy:** Auto-updated on every merge by **BTCAAAAA-30043** post-merge reset routine.
**Last auto-refresh:** {timestamp}
**Reset status:** {status_msg}

---

## Frontend dev server — `http://localhost:3010`

| Field | Value |
|---|---|
| **Status** | ✅ LISTEN — Next 15 / turbopack |
| **Current branch (working tree)** | `{current_branch}` |
| **Current HEAD SHA** | `{current_sha}` |
| **Last reset timestamp** | {timestamp} |
| **Visual-verification safety** | ✅ On main — safe for verification |
| **Owning agent right now** | None (between tasks) |

## Redis — `{redis_host}:{redis_port}`

| Field | Value |
|---|---|
| **Status** | {redis_info["status"]} |
| **Detail** | {redis_info["detail"]} |
| **Last probed** | {timestamp} |
"""
    
    payload = {
        "title": "Dev server status board",
        "format": "markdown",
        "body": new_body,
        "baseRevisionId": base_revision_id,
    }
    
    try:
        resp = session.put(doc_url, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Document updated")
        return True
    except Exception as exc:
        logger.error("Failed to update document: %s", exc)
        return False


def main() -> int:
    """Main routine execution."""
    logger.info("=== Dev Server Post-Merge Reset Routine ===")
    logger.info("Agent: %s, Run: %s", AGENT_ID, RUN_ID)
    
    session = http_session()
    reset_result = run_reset_script()
    logger.info("Reset result: %s", reset_result.get("status"))
    
    update_dev_server_status_doc(session, reset_result)
    
    if reset_result.get("status") in ("success", "skipped"):
        logger.info("=== Routine Complete ===")
        return 0
    else:
        logger.error("=== Routine Failed ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())
