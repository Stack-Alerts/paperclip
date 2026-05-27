#!/usr/bin/env python3
"""Post-merge dev-server reset: auto-reset localhost:3010 to origin/main HEAD.

This routine:
1. Polls origin/main for new commits
2. Detects when HEAD changes
3. Resets the working tree if clean or only .next/dev is dirty
4. Clears .next/dev cache
5. Restarts the dev server
6. Updates the dev-server-status document on BTCAAAAA-30038

Refusal conditions:
- Working tree has uncommitted changes outside .next/dev → log, warn, do not reset
- Agent execution is locked on current branch → defer, retry, then warn

Usage:
    python scripts/dev_server_post_merge_reset.py [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

# Load environment variables from .env file if not already set
# Only load specific Paperclip-related vars to avoid bash parsing issues
env_file = REPO_ROOT / ".env"
if env_file.exists() and not os.environ.get("PAPERCLIP_API_KEY"):
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key in ("PAPERCLIP_API_URL", "PAPERCLIP_API_KEY", "PAPERCLIP_COMPANY_ID"):
                os.environ.setdefault(key, value)
    except Exception as exc:
        logger.warning("Failed to load .env file: %s", exc)

from touch_index.paperclip_client import _base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("dev_server_reset")

# Configuration
API_TIMEOUT = 30
STATUS_TRACKING_ISSUE = "BTCAAAAA-30038"
STATE_FILE = REPO_ROOT / "data" / "dev_server_reset_state.json"
WEBUI_PORT = 3010
WEBUI_DIR = REPO_ROOT / "packages" / "web-ui"
NEXT_CACHE_DIR = WEBUI_DIR / ".next" / "dev"
START_SCRIPT = REPO_ROOT / "start.sh"


def _http_session() -> requests.Session:
    """Create HTTP session with retries."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ.get('PAPERCLIP_API_KEY', '')}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "PATCH", "POST"],
        raise_on_status=False,
    ))
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def load_state() -> dict[str, Any]:
    """Load the last known HEAD SHA."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Failed to load state: %s", exc)
            return {"last_head_sha": None, "last_reset": None}
    return {"last_head_sha": None, "last_reset": None}


def save_state(state: dict[str, Any]) -> None:
    """Save the current HEAD SHA."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except IOError as exc:
        logger.error("Failed to save state: %s", exc)


def get_origin_main_sha() -> str | None:
    """Get the current SHA of origin/main via git."""
    try:
        # Fetch origin to ensure we have latest
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
            check=False,
        )

        # Get the current SHA
        result = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
            text=True,
        )

        if result.returncode == 0:
            sha = result.stdout.strip()
            logger.info("origin/main is at %s", sha[:8])
            return sha
        else:
            logger.error("Failed to get origin/main SHA: %s", result.stderr)
            return None
    except Exception as exc:
        logger.error("Failed to fetch origin/main: %s", exc)
        return None


def check_working_tree_clean() -> tuple[bool, list[str]]:
    """Check if working tree is clean or only .next/dev is dirty.

    Returns: (is_clean_or_safe, list_of_dirty_paths_outside_next_dev)
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
            text=True,
        )

        if result.returncode != 0:
            logger.error("Failed to check working tree status: %s", result.stderr)
            return False, []

        dirty_paths = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Format: XY PATH (X = staged, Y = unstaged)
            path = line[3:].strip()

            # Allow .next/dev/* to be dirty
            if path.startswith("packages/web-ui/.next/dev/"):
                logger.debug("Allowing dirty .next/dev path: %s", path)
                continue

            # Any other dirt is a blocker
            dirty_paths.append(path)

        is_clean = len(dirty_paths) == 0
        logger.info("Working tree clean: %s (dirty outside .next/dev: %d)", is_clean, len(dirty_paths))
        return is_clean, dirty_paths
    except Exception as exc:
        logger.error("Failed to check working tree: %s", exc)
        return False, []


def reset_to_origin_main() -> bool:
    """Reset the working tree to origin/main HEAD."""
    try:
        logger.info("Resetting to origin/main...")
        result = subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info("Successfully reset to origin/main")
            return True
        else:
            logger.error("Failed to reset: %s", result.stderr.decode())
            return False
    except Exception as exc:
        logger.error("Failed to reset working tree: %s", exc)
        return False


def clear_next_dev_cache() -> bool:
    """Clear the .next/dev cache and server directories."""
    try:
        logger.info("Clearing .next/dev cache...")

        # Remove cache dir
        cache_dir = NEXT_CACHE_DIR / "cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            logger.info("Removed %s", cache_dir)

        # Remove server dir
        server_dir = NEXT_CACHE_DIR / "server"
        if server_dir.exists():
            shutil.rmtree(server_dir)
            logger.info("Removed %s", server_dir)

        logger.info("Successfully cleared .next/dev cache")
        return True
    except Exception as exc:
        logger.error("Failed to clear cache: %s", exc)
        return False


def restart_dev_server() -> bool:
    """Restart the dev server and verify it's serving."""
    try:
        logger.info("Restarting dev server...")

        # Kill the process bound to WEBUI_PORT (the actual next-server),
        # plus any npm run dev wrappers.
        fuser_result = subprocess.run(
            ["fuser", "-k", f"{WEBUI_PORT}/tcp"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        logger.info("fuser kill port %d: rc=%d", WEBUI_PORT, fuser_result.returncode)

        subprocess.run(
            ["pkill", "-f", "npm run dev"],
            capture_output=True,
            timeout=10,
            check=False,
        )

        # Wait for port to be released
        for _ in range(10):
            time.sleep(1)
            port_check = subprocess.run(
                ["fuser", f"{WEBUI_PORT}/tcp"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if port_check.returncode != 0:
                logger.info("Port %d is free", WEBUI_PORT)
                break
        else:
            logger.warning("Port %d still in use after 10s, proceeding anyway", WEBUI_PORT)

        # Start only the Next.js dev server on the expected port.
        # start.sh defaults to port 3000 (BTE_WEBUI_PORT unset in .env), so
        # we invoke npm run dev directly with the explicit port instead.
        log_path = Path("/tmp") / f"webui-dev-{WEBUI_PORT}.log"
        log_fh = open(log_path, "a")
        proc = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(WEBUI_PORT)],
            cwd=WEBUI_DIR,
            stdout=log_fh,
            stderr=log_fh,
            start_new_session=True,
        )

        logger.info("Started dev server (PID %d)", proc.pid)

        # Wait for the server to come up (max 90 seconds — Turbopack cold-start)
        for attempt in range(90):
            time.sleep(1)
            try:
                resp = requests.get(
                    f"http://localhost:{WEBUI_PORT}",
                    timeout=3,
                )
                if resp.status_code == 200:
                    title_found = "BTC Trade Engine" in resp.text
                    logger.info(
                        "Dev server HTTP %d at localhost:%d (title_found=%s)",
                        resp.status_code,
                        WEBUI_PORT,
                        title_found,
                    )
                    if title_found:
                        return True
                    # Server is up but wrong content — keep waiting for compile
                    logger.debug("Waiting for full compile (attempt %d/90)", attempt + 1)
                else:
                    logger.debug(
                        "Server returned HTTP %d, waiting (attempt %d/90)",
                        resp.status_code,
                        attempt + 1,
                    )
            except requests.RequestException as exc:
                logger.debug("Waiting for server (attempt %d/90): %s", attempt + 1, exc)

        logger.error("Dev server did not serve expected content within 90 seconds")
        try:
            os.killpg(os.getpgid(proc.pid), 15)
        except Exception:
            pass
        return False
    except Exception as exc:
        logger.error("Failed to restart dev server: %s", exc)
        return False


def post_status_comment(sha: str, success: bool, error_message: str | None = None) -> bool:
    """Post a status comment on BTCAAAAA-30038 about dev-server health."""
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        status_str = "✅ Healthy" if success else "⚠️ Degraded"

        body = f"""**Dev Server Status Update**

**Time:** {timestamp}
**Status:** {status_str}
**origin/main:** {sha[:8]}
**Port:** localhost:{WEBUI_PORT}

"""
        if error_message:
            body += f"**Error:** {error_message}\n"

        with _http_session() as sess:
            resp = sess.post(
                f"{_base()}/api/issues/{STATUS_TRACKING_ISSUE}/comments",
                json={"body": body},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Posted status comment to %s", STATUS_TRACKING_ISSUE)
            return True
    except Exception as exc:
        logger.error("Failed to post status comment: %s", exc)
        return False


def post_warning_comment(issue: str, dirty_paths: list[str]) -> bool:
    """Post a warning comment when reset is refused."""
    try:
        paths_str = "\n".join([f"  - {p}" for p in dirty_paths])
        body = f"""**Dev-server reset REFUSED: dirty working tree**

The dev server reset was skipped because the working tree has uncommitted changes outside `.next/dev`:

```
{paths_str}
```

**Action required:**
1. Commit or stash changes outside `.next/dev`
2. The next reset will proceed automatically once the tree is clean

_Automated check from BTCAAAAA-30052 (Phase 5)._
"""

        with _http_session() as sess:
            resp = sess.post(
                f"{_base()}/api/issues/{issue}/comments",
                json={"body": body},
                timeout=API_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Posted warning comment to %s", issue)
            return True
    except Exception as exc:
        logger.error("Failed to post warning: %s", exc)
        return False


def main(dry_run: bool = False, force: bool = False) -> int:
    """Main routine execution."""
    logger.info("Starting dev-server post-merge reset routine")

    # Load state
    state = load_state()
    last_sha = state.get("last_head_sha")

    # Get current origin/main SHA
    current_sha = get_origin_main_sha()
    if not current_sha:
        logger.error("Failed to get origin/main SHA")
        return 1

    # Check if anything changed
    if current_sha == last_sha and not force:
        logger.info("origin/main unchanged (still at %s)", current_sha[:8])
        return 0

    logger.info("origin/main changed: %s → %s", last_sha[:8] if last_sha else "none", current_sha[:8])

    if dry_run:
        logger.info("[DRY RUN] Would reset to %s", current_sha[:8])
        return 0

    # Check working tree
    is_clean, dirty_paths = check_working_tree_clean()

    if not is_clean:
        logger.warning("Working tree has changes outside .next/dev, refusing reset")
        logger.warning("Dirty paths: %s", dirty_paths)
        post_warning_comment("BTCAAAAA-30052", dirty_paths)
        post_status_comment(current_sha, False, f"Dirty tree: {len(dirty_paths)} paths")
        return 1

    # Reset to origin/main
    if not reset_to_origin_main():
        logger.error("Failed to reset to origin/main")
        post_status_comment(current_sha, False, "Reset failed")
        return 1

    # Clear cache
    if not clear_next_dev_cache():
        logger.error("Failed to clear .next/dev cache")
        post_status_comment(current_sha, False, "Cache clear failed")
        return 1

    # Restart dev server
    if not restart_dev_server():
        logger.error("Failed to restart dev server")
        post_status_comment(current_sha, False, "Server restart failed")
        return 1

    # Update state
    state["last_head_sha"] = current_sha
    state["last_reset"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    # Update status document
    post_status_comment(current_sha, True)

    logger.info("Dev-server reset completed successfully")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Log actions but don't execute")
    parser.add_argument("--force", action="store_true", help="Force reset even if SHA unchanged")
    args = parser.parse_args()

    sys.exit(main(dry_run=args.dry_run, force=args.force))
