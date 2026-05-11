#!/usr/bin/env python3
"""0002 — add runId-based deduplication to stale-run evaluation creation.

Patches the Paperclip server recovery service.js to add a pre-creation check
for existing stale-run evaluations for the same runId, preventing duplicate
review issues while allowing one re-alert at critical (4h+) silence level.

Idempotent: skips files that already contain the marker comment.
"""

import os
import sys
from pathlib import Path

NPX_CACHE_BASE = Path.home() / ".npm" / "_npx"
MARKER = "// paperclip-patch(0002): skip prior-eval dedup for runId"

# Match lines for two insertion points:
MATCH_OWNER = "const ownerAgentId = await resolveStaleRunOwnerAgentId("
MATCH_DESC = "const description = buildStaleRunEvaluationDescription("

INSERT_BLOCK_MAIN = f"""\
        {MARKER}
        // Query ALL stale-run evaluations for this runId (any status).
        // Dedup rules:
        //   - count == 0           -> first-time alert, create normally
        //   - count == 1 && critical -> one re-alert allowed (run silent >4h)
        //   - count == 1 && !critical -> skip (not critical enough for re-alert)
        //   - count >= 2           -> already had initial + re-alert, stop
        const priorEvals = await db
            .select({{ id: issues.id }})
            .from(issues)
            .where(and(
                eq(issues.companyId, input.run.companyId),
                eq(issues.originKind, STALE_ACTIVE_RUN_EVALUATION_ORIGIN_KIND),
                eq(issues.originId, input.run.id),
            ));
        if (priorEvals.length > 0) {{
            if (priorEvals.length === 1 && level === "critical") {{
                // Allow one re-alert when silence is critical (4h+ threshold).
                // A note is appended to the description below.
            }} else {{
                return {{ kind: "skipped" }};
            }}
        }}"""

INSERT_BLOCK_REALERT_NOTE = """\
        // Append re-alert note if this is a re-evaluation at critical level.
        if (priorEvals.length === 1 && level === "critical") {
            description += "\\n\\n---\\n**Note:** A prior stale-run evaluation for this run was already resolved. " +
                "This is a re-alert triggered because the run has been silent beyond the critical threshold (4h).";
        }"""


def _find_line_number(lines: list[str], needle: str) -> int | None:
    for i, line in enumerate(lines, 1):
        if needle in line:
            return i
    return None


def patch_file(path: Path) -> bool:
    if not path.is_file():
        return False

    text = path.read_text()

    if MARKER in text:
        print(f"ALREADY PATCHED: {path}")
        return False

    # --- Find both insertion points ---
    lines = text.splitlines(keepends=True)

    line_owner = _find_line_number(lines, MATCH_OWNER)
    line_desc = _find_line_number(lines, MATCH_DESC)

    if line_owner is None:
        print(f"PATTERN (ownerAgentId) NOT FOUND: {path}")
        return False

    if line_desc is None:
        print(f"PATTERN (description) NOT FOUND: {path}")

    # Insert #1: before `const ownerAgentId`
    insert1_idx = line_owner - 1
    lines.insert(insert1_idx, INSERT_BLOCK_MAIN + "\n")

    # Adjust line_desc if it was after insert1_idx
    if line_desc is not None and line_desc >= line_owner:
        line_desc += 1  # shifted by insertion #1

    # Insert #2: before `const description = buildStaleRunEvaluationDescription(`
    if line_desc is not None:
        insert2_idx = line_desc - 1
        # Find the end of the buildStaleRunEvaluationDescription call — it spans
        # multiple lines.  Insert AFTER the closing `);` of that call, before
        # `let evaluation;`
        # Walk forward from insert2_idx to find the `);` that closes the call
        paren_depth = 0
        found_close = False
        for i in range(insert2_idx, len(lines)):
            for ch in lines[i]:
                if ch == "(":
                    paren_depth += 1
                elif ch == ")":
                    paren_depth -= 1
            if paren_depth == 0 and ");" in lines[i]:
                insert2_idx = i + 1  # insert after this line
                found_close = True
                break

        if found_close:
            lines.insert(insert2_idx, INSERT_BLOCK_REALERT_NOTE + "\n")
        else:
            print(f"WARNING: could not find closing of buildStaleRunEvaluationDescription in {path}")
    else:
        print(f"WARNING: skipping re-alert note insertion — description pattern not found")

    path.write_text("".join(lines))
    print(f"PATCHED: {path} ({2 if line_desc else 1} insertions)")
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
