#!/usr/bin/env python3
"""Fail a PR if it claims to revert something but omits the caller audit.

Enforces the `paperclip-create-revert-pr` skill (see
`docs/process/paperclip-create-revert-pr.md`). The rule:

    If the PR title or body contains a revert verb (`revert`, `reverts`,
    `reverting`), the body MUST contain the literal heading `## Caller audit`.

The check is intentionally simple — the *content* of the table is reviewed
by a human; this script only guarantees the heading is present so reviewers
have something to review.

Usage (local):
    python3 scripts/check_revert_pr_caller_audit.py \
        --title-file <(gh pr view 118 --json title -q .title) \
        --body-file <(gh pr view 118 --json body -q .body)

Usage (GitHub Actions): see
    .github/workflows/pr-revert-caller-audit-check.yml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REVERT_VERB = re.compile(r"\brevert(?:s|ed|ing)?\b", re.IGNORECASE)
CALLER_AUDIT_HEADING = re.compile(r"^##\s+Caller audit\s*$", re.MULTILINE)


def _read(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _strip_quotes_and_code(body: str) -> str:
    """Drop fenced code blocks and blockquote lines so revert verbs inside
    example snippets or quoted prior text don't trip the gate."""
    no_fences = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    no_quotes = "\n".join(
        line for line in no_fences.splitlines() if not line.lstrip().startswith(">")
    )
    return no_quotes


def check(title: str, body: str) -> tuple[bool, str]:
    scanned = f"{title}\n{_strip_quotes_and_code(body)}"
    is_revert = bool(REVERT_VERB.search(scanned))
    if not is_revert:
        return True, "PR does not reference a revert — caller-audit gate not required."
    if CALLER_AUDIT_HEADING.search(body):
        return True, "Revert PR contains the `## Caller audit` heading — gate satisfied."
    return False, (
        "Revert PR is missing the `## Caller audit` heading in its description.\n"
        "See docs/process/paperclip-create-revert-pr.md for the required shape."
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title-file", help="Path containing the PR title.")
    parser.add_argument("--body-file", help="Path containing the PR body markdown.")
    parser.add_argument("--title", help="PR title (overrides --title-file).")
    parser.add_argument("--body", help="PR body (overrides --body-file).")
    args = parser.parse_args(argv)

    title = args.title if args.title is not None else _read(args.title_file)
    body = args.body if args.body is not None else _read(args.body_file)

    ok, message = check(title, body)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
