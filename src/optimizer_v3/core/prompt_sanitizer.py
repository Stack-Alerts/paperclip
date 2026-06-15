"""
Prompt Sanitizer
================

Sprint: BTCAAAAA-36469 (AI Recs P1)

User-controlled strings (strategy names, block names, signal names) flow into
the AI prompt and into our own response schema. Before they do, they must be
neutralized — otherwise a malicious or malformed upstream string can:

- Smuggle a new system prompt past us (e.g. "ignore previous instructions").
- Insert chat-template role markers (``<|im_start|>`` / ``<|im_end|>``) and
  hijack the assistant's framing.
- Inject SQL that downstream code (logs, debug tools) might blindly execute.
- Embed C0 control bytes (NUL, BEL, ESC) that confuse parsers, terminal
  emulators, and JSON encoders.

This module exposes a single function, :func:`sanitize_name`, that strips
these hazards. The contract is exercised by
``tests/optimizer_v3/test_ai_recommendation_enhancer_p1.py::TestSanitization``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Tuple


# Patterns are matched case-insensitively and replaced with a single space.
# We do NOT raise on a hit — the goal is "make the string safe to use as a
# name", not "refuse bad input". The AI re-prompt path is the right place
# for refusal logic; this module is a defensive scrub.
_INJECTION_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    # "ignore previous instructions" / "ignore all prior rules" — the
    # canonical prompt-injection prefix. Whitespace inside is collapsed
    # because the AI may emit tabs / newlines.
    (re.compile(r"ignore\s+previous\s+(?:instructions?|directives?)", re.IGNORECASE), " "),
    (re.compile(r"ignore\s+all\s+prior\s+(?:rules?|instructions?|directives?)", re.IGNORECASE), " "),
    (re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?|directives?)", re.IGNORECASE), " "),
    # Chat-template role markers (ChatML / Llama-3). These MUST NOT survive
    # into the prompt verbatim — they would re-frame the assistant.
    (re.compile(r"<\|im_start\|>"), " "),
    (re.compile(r"<\|im_end\|>"), " "),
    # Destructive SQL — only the obvious flavor we expect from a misuse test.
    # We don't try to be a full SQL parser; we just kill the canonical
    # "DROP TABLE <something>; --" shape.
    (re.compile(r"\bdrop\s+table\b", re.IGNORECASE), " "),
    (re.compile(r"\btruncate\s+table\b", re.IGNORECASE), " "),
    (re.compile(r"\bdelete\s+from\b", re.IGNORECASE), " "),
    # A second wave of "you are now X" / "new task" framings that aim to
    # override the system prompt. Stripped, not raised.
    (re.compile(r"\byou\s+are\s+now\s+(?:a|an|the)\b", re.IGNORECASE), " "),
    (re.compile(r"\bnew\s+task\s*:", re.IGNORECASE), " "),
)


def _strip_control_chars(value: str) -> str:
    """Drop C0 control bytes (NUL–US, 0x00–0x1F) and DEL (0x7F).

    Tab / LF / CR are kept because they are not a security concern inside
    a name and dropping them would surprise callers. Anything below 0x20
    that is NOT \\t / \\n / \\r is replaced with a space.
    """
    out_chars = []
    for ch in value:
        code = ord(ch)
        if code < 0x20 and ch not in "\t\n\r":
            out_chars.append(" ")
            continue
        if code == 0x7F:  # DEL
            out_chars.append(" ")
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def sanitize_name(name: str) -> str:
    """Return ``name`` with prompt-injection / control-char hazards removed.

    The transformation is idempotent — feeding the output back through
    :func:`sanitize_name` is a no-op.

    Guarantees enforced (asserted by the test suite):

    - The output never contains ``"ignore previous"`` or
      ``"ignore all prior"`` (case-insensitive).
    - The output never contains ``<|im_start|>`` or ``<|im_end|>``.
    - The output never contains ``"drop table"`` (case-insensitive).
    - The output never contains C0 control characters other than tab,
      newline, and carriage return.
    - Non-ASCII letters are preserved (NFKC-normalized so e.g. a fullwidth
      'D' is folded into ASCII 'D' before injection-pattern matching).
    - The output is stripped of leading / trailing whitespace and has
      internal runs of whitespace collapsed to a single space.
    """
    if name is None:
        return ""
    if not isinstance(name, str):
        # Defensive — callers should pass a str, but if a non-str leaks in
        # (e.g. an int from a parsed JSON) we coerce rather than crash.
        name = str(name)

    # NFKC fold: "Ｄｒｏｐ TABLE" → "Drop TABLE" before pattern matching.
    folded = unicodedata.normalize("NFKC", name)

    scrubbed = _strip_control_chars(folded)
    for pattern, replacement in _INJECTION_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)

    # Collapse runs of whitespace introduced by the substitutions and
    # strip the leading / trailing whitespace.
    scrubbed = re.sub(r"\s+", " ", scrubbed).strip()
    return scrubbed
