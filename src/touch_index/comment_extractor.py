"""Extract file paths from Paperclip issue comments and descriptions.

Used primarily for FDR issues where the implementing agent posts a done-comment
that mentions the files they changed (e.g. ``src/optimizer_v3/database/...``).

Extraction priority:
  1. Backtick-wrapped paths: `src/foo/bar.py`
  2. Bare path strings starting with src/, tests/, scripts/, alembic/
  3. Paths following "Fix applied to ..." or "Commit ... touches ..." patterns

Normalisation: strip leading `BTC_Engine_v3/` or `projects/*/` repo prefixes
so all paths are repo-relative (e.g. `src/foo/bar.py`).
"""

from __future__ import annotations

import re
from typing import Sequence

_CODE_EXTS = r"(?:py|js|ts|sql)"

# Backtick-wrapped paths
_RE_BACKTICK = re.compile(r"`([a-zA-Z0-9_/\-\.]+\.(?:" + _CODE_EXTS + r"))`")

# Bare paths starting with a known root
_RE_PATH = re.compile(
    r"(?:^|[\s(\[])(?:BTC_Engine_v3/|projects/[^/]+/)?"
    r"((?:src|tests|scripts|alembic)/[a-zA-Z0-9_/\-\.]+\.(?:" + _CODE_EXTS + r"))"
)

_STRIP_PREFIXES = (
    "BTC_Engine_v3/",
    "BTC-Trade-Engine-PaperClip/",
    "projects/",
)


def _normalise(path: str) -> str:
    for prefix in _STRIP_PREFIXES:
        if path.startswith(prefix):
            rest = path[len(prefix) :]
            # "projects/X/..." — also strip the project directory
            if prefix == "projects/":
                parts = rest.split("/", 1)
                return parts[1] if len(parts) > 1 else parts[0]
            return rest
    return path


def extract_files_from_text(text: str) -> list[str]:
    """Return deduplicated, normalised source file paths found in `text`."""
    found: set[str] = set()

    for m in _RE_BACKTICK.finditer(text):
        found.add(_normalise(m.group(1)))

    for m in _RE_PATH.finditer(text):
        found.add(_normalise(m.group(1)))

    return sorted(found)


def extract_files_from_comments(comments: Sequence[dict]) -> list[str]:
    """Aggregate file paths across all comment bodies."""
    found: set[str] = set()
    for comment in comments:
        body = comment.get("body", "")
        found.update(extract_files_from_text(body))
    return sorted(found)


def fetch_and_extract(issue_id: str) -> list[str]:
    """Fetch comments for an issue via Paperclip API and extract file paths."""
    import os
    import requests

    url = f"{os.environ['PAPERCLIP_API_URL']}/api/issues/{issue_id}/comments"
    headers = {"Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return extract_files_from_comments(resp.json())
