#!/usr/bin/env python3
"""0002 — add runId-based deduplication to stale-run evaluation creation.

Patches the Paperclip server recovery service.js to add a pre-creation check
for ANY existing stale-run evaluation (including done/cancelled ones) for the
same runId, preventing duplicate review issues.

Idempotent: skips files that already contain the marker comment.
"""

import os
import re
import sys
from pathlib import Path

NPX_CACHE_BASE = Path.home() / ".npm" / "_npx"
MARKER = "// paperclip-patch(0002): skip prior-eval dedup for runId"
MATCH = "const ownerAgentId = await resolveStaleRunOwnerAgentId("

INSERT_BLOCK = f"""\
        {MARKER}
        // Skip stale-run evaluation when a prior evaluation already exists for this
        // runId (including done/cancelled ones): completing a stale-run evaluation
        // and having the recovery scan re-detect the same silent run would create a
        // new evaluation issue, producing duplicate noise that cannot be actioned.
        const prior = await db
            .select({{ id: issues.id }})
            .from(issues)
            .where(and(
                eq(issues.companyId, input.run.companyId),
                eq(issues.originKind, STALE_ACTIVE_RUN_EVALUATION_ORIGIN_KIND),
                eq(issues.originId, input.run.id),
            ))
            .limit(1);
        if (prior.length > 0) {{
            return {{ kind: "skipped" }};
        }}"""


def patch_file(path: Path) -> bool:
    if not path.is_file():
        return False

    text = path.read_text()

    if MARKER in text:
        print(f"ALREADY PATCHED: {path}")
        return False

    # Find the insertion point
    match_line = None
    for i, line in enumerate(text.splitlines(), 1):
        if MATCH in line:
            match_line = i
            break

    if match_line is None:
        print(f"PATTERN NOT FOUND: {path} (unexpected file structure)")
        return False

    lines = text.splitlines(keepends=True)
    insert_index = match_line - 1  # 0-indexed
    lines.insert(insert_index, INSERT_BLOCK + "\n")
    path.write_text("".join(lines))
    print(f"PATCHED: {path} (inserted before line {match_line})")
    return True


def main() -> int:
    patched = 0
    already = 0
    not_found = 0

    if not NPX_CACHE_BASE.is_dir():
        print(f"npx cache directory not found: {NPX_CACHE_BASE}")
        return 1

    for cache_dir in sorted(NPX_CACHE_BASE.iterdir()):
        target = (
            cache_dir
            / "node_modules"
            / "@paperclipai"
            / "server"
            / "dist"
            / "services"
            / "recovery"
            / "service.js"
        )
        if not target.is_file():
            continue

        if MARKER in target.read_text():
            print(f"ALREADY PATCHED: {target}")
            already += 1
            continue

        if patch_file(target):
            patched += 1
        else:
            not_found += 1

    print()
    print("--- Summary ---")
    print(f"Patched:        {patched}")
    print(f"Already fixed:  {already}")
    print(f"Not found:      {not_found}")
    print()

    if not_found > 0 and patched == 0 and already == 0:
        return 1

    if patched > 0:
        print("RESTART REQUIRED: The Paperclip server must be restarted for the change to take effect.")
        print("  pkill -f 'paperclipai run' || true")
        print(f"  cd {Path.cwd()}")
        print("  nohup npx paperclipai@latest run > /dev/null 2>&1 &")

    return 0


if __name__ == "__main__":
    sys.exit(main())
