"""Blast Radius Report markdown renderer."""

from __future__ import annotations

from .query import BlastRadiusData


COMPANY_PREFIX = "BTCAAAAA"


def _issue_link(identifier: str) -> str:
    return f"[{identifier}](/{COMPANY_PREFIX}/issues/{identifier})"


def _agent_mention(agent_id: str, agent_name: str | None = None) -> str:
    label = agent_name or agent_id
    return f"[@{label}](agent://{agent_id})"


def render_report(
    issue_identifier: str,
    issue_title: str,
    touched_files: list[str],
    data: BlastRadiusData,
    agent_names: dict[str, str] | None = None,
) -> str:
    """Render the Blast Radius Report markdown.

    *agent_names* maps agent_id → display name for @-mention rendering.
    Pass an empty dict (or None) to fall back to raw agent IDs.
    """
    agent_names = agent_names or {}

    file_list = "\n".join(f"- `{f}`" for f in sorted(touched_files)) or "_None_"

    # FR Impact Set
    if data.fr_impact_set:
        fr_lines = []
        for fr in data.fr_impact_set:
            owner_mention = _agent_mention(
                fr.fr_owner_agent_id,
                agent_names.get(fr.fr_owner_agent_id),
            )
            fr_lines.append(
                f"- {_issue_link(fr.fr_identifier)} — owner: {owner_mention}"
            )
        fr_section = "\n".join(fr_lines)
    else:
        fr_section = "_None_"

    # Regression Risk
    if data.regression_set:
        bug_lines = [
            f"- {_issue_link(r.bug_identifier)}"
            for r in data.regression_set
        ]
        bug_section = "\n".join(bug_lines)
    else:
        bug_section = "_None_"

    # Downstream
    if data.downstream_set:
        ds_lines = [f"- `{f}`" for f in data.downstream_set]
        ds_section = "\n".join(ds_lines)
    else:
        ds_section = (
            "_Not available yet — Phase 2 dependency graph will populate this section._"
        )

    return f"""\
## Blast Radius Report

**Fix:** {_issue_link(issue_identifier)} — {issue_title}
**Touched files:**

{file_list}

### FR Impact Set

{fr_section}

### Regression Risk

{bug_section}

### Downstream (Phase 2 — dep graph pending)

{ds_section}
"""


def extract_touched_files(description: str) -> list[str]:
    """Parse touched file paths from an issue description.

    Supports two formats (first match wins):

    1. JSON code block:
       ```json
       {"touchedFiles": ["src/foo.py", "src/bar.py"]}
       ```

    2. Markdown section:
       ## Touched Files
       - src/foo.py
       - src/bar.py
    """
    import json
    import re

    # JSON block
    json_block = re.search(
        r"```(?:json)?\s*\{[^`]*\"touchedFiles\"\s*:\s*(\[[^\]]*\])[^`]*\}\s*```",
        description,
        re.DOTALL,
    )
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass

    # Also try a bare JSON object anywhere in the description
    bare = re.search(
        r'"touchedFiles"\s*:\s*(\[[^\]]*\])',
        description,
        re.DOTALL,
    )
    if bare:
        try:
            return json.loads(bare.group(1))
        except json.JSONDecodeError:
            pass

    # Markdown list under a ## Touched Files section
    section = re.search(
        r"##\s*Touched Files\s*\n((?:\s*[-*]\s*\S+\s*\n?)+)",
        description,
        re.IGNORECASE,
    )
    if section:
        lines = section.group(1).strip().splitlines()
        return [
            re.sub(r"^[-*]\s+`?|`?$", "", line).strip()
            for line in lines
            if line.strip()
        ]

    return []
