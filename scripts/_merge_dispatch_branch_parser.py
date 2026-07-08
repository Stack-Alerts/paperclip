"""Branch-name parser and ANSI escape stripper for the merge-dispatch family.

BTCAAAAA-38473 Gap 6 — centralizes two pure helpers that previously lived as
inline regex (branch parsing) or were absent entirely (log sanitization):

* ``parse_branch(branch_name)`` — recognizes Paperclip fix branches like
  ``fix/BTCAAAAA-38473-dispatch-polish`` and rejects anything else (feature
  branches, chore/lock branches, plain text, etc.). Returns a small dict with
  ``identifier`` (e.g. ``BTCAAAAA-38473``), ``slug`` (e.g.
  ``dispatch-polish`` or empty string when the branch has no slug), and
  ``raw`` (the original input). Returns ``None`` for non-matching input.
* ``strip_ansi(text)`` — removes CSI escape sequences so log lines bound for
  Paperclip markdown comments render cleanly without raw escape codes leaking
  into the rendered board view.

These helpers are pure (no I/O, no globals) so they are trivially unit-tested
in isolation and cheap to import from any dispatch-related script.
"""

from __future__ import annotations

import re
from typing import Optional

# Paperclip fix-branch shape: fix/BTCAAAAA-<id>(-<slug>)?
# The identifier is mandatory; the slug is optional. Branch tips may carry
# an ``origin/`` prefix (from ``git branch -r --contains``) which the parser
# strips before matching.
_ID = r"(?P<identifier>BTCAAAAA-\d+)"
_SLUG = r"(?:-(?P<slug>[A-Za-z0-9][A-Za-z0-9-]*))?"
_BRANCH_RE = re.compile(
    r"^(?:origin/)?fix/" + _ID + _SLUG + r"$"
)

# CSI escape sequences (ESC [ ... letter). Color codes from ``logging``
# handlers (e.g. ``\x1b[32m``) leak into Paperclip markdown and render as
# literal characters. Strip the whole sequence, parameters and final byte.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def parse_branch(branch_name: str) -> Optional[dict]:
    """Parse a Paperclip fix branch name.

    Returns ``{"identifier": "BTCAAAAA-XXXXX", "slug": "word-word" | "",
    "raw": <input>}`` on match, or ``None`` for non-matching input.
    """
    if not branch_name:
        return None
    match = _BRANCH_RE.match(branch_name)
    if match is None:
        return None
    return {
        "identifier": match.group("identifier"),
        "slug": match.group("slug") or "",
        "raw": branch_name,
    }


def strip_ansi(text: str) -> str:
    """Remove CSI ANSI escape sequences from ``text``.

    Used to sanitize log output bound for Paperclip markdown comments so the
    board renders plain text instead of raw escape codes.
    """
    return _ANSI_RE.sub("", text)