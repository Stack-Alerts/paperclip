"""Branch-name parser, ANSI escape stripper, and pre-completion warning marker.

Centralized pure helpers shared across the merge-dispatch family and the
pre-completion diff-check cron. Keeping them in one file avoids the
"copy-pasted regex drifted from the writer" hazard that the audit flagged
(BTCAAAAA-38473 Gap 6, BTCAAAAA-39070):

* ``parse_branch(branch_name)`` — recognizes Paperclip fix branches like
  ``fix/BTCAAAAA-38473-dispatch-polish`` and rejects anything else (feature
  branches, chore/lock branches, plain text, etc.). Returns a small dict with
  ``identifier`` (e.g. ``BTCAAAAA-38473``), ``slug`` (e.g.
  ``dispatch-polish`` or empty string when the branch has no slug), and
  ``raw`` (the original input). Returns ``None`` for non-matching input.
* ``strip_ansi(text)`` — removes CSI escape sequences so log lines bound for
  Paperclip markdown comments render cleanly without raw escape codes leaking
  into the rendered board view.
* ``has_precompletion_marker(text)`` — returns True when a comment body
  contains the line-anchored ``Pre-Completion Diff Warning`` marker emitted
  by ``scripts/precompletion_diff_check.py``. Used both by that script (to
  short-circuit the 60-minute idempotency window when the state file is
  lost) and by future dispatch tools that want to detect prior warnings.

These helpers are pure (no I/O, no globals) so they are trivially unit-tested
in isolation and cheap to import from any dispatch- or cron-related script.
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

# Line-anchored marker emitted by ``scripts/precompletion_diff_check.py`` on
# every warning comment (BTCAAAAA-39070). Authored in Markdown so it is
# intentionally tolerant of leading emphasis wrappers (``**``, ``_``,
# backticks) and the ``##`` heading prefix, and the optional trailing ``_``
# lets us accept closing-emphasis bodies like ``_Pre-Completion Diff
# Warning_`` (the warning body's footer line uses that pattern). The
# tolerance mirrors ``FIX_SHA_NONE_PATTERN`` / ``NO_SHA_TAG_PATTERN`` in
# ``scripts/closure_gate_routine.py``. The marker MUST be line-anchored so
# mid-line prose like "I posted a Pre-Completion Diff Warning earlier today"
# does not collide with the suppress check.
PRECOMPLETION_WARNING_MARKER = (
    r"^[ \t]*(?:[#*_~`]*[ \t]*)?Pre-Completion Diff Warning_?\b"
)
_PRECOMPLETION_WARNING_RE = re.compile(
    PRECOMPLETION_WARNING_MARKER,
    re.MULTILINE | re.IGNORECASE,
)


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


def has_precompletion_marker(text: Optional[str]) -> bool:
    """Return True if ``text`` carries the pre-completion diff-warning marker.

    The marker is a line-anchored ``Pre-Completion Diff Warning`` heading at
    the top of every warning comment posted by the
    ``scripts/precompletion_diff_check.py`` cron. Detecting it lets callers
    decide whether an issue has already been warned about — independent of
    any state file — so idempotency is robust to a wiped ``data/`` directory.
    """
    if not text:
        return False
    return _PRECOMPLETION_WARNING_RE.search(text) is not None