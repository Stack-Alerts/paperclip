#!/usr/bin/env python3
from pathlib import Path
import re

# Regex patterns tuned to your file format:
# **Block Script:** `...`
# **Implementation:** `...`
# **Documentation:** `...`
BLOCK_SCRIPT_RE = re.compile(r'\*\*Block Script:\*\*\s*`([^`]+)`', re.IGNORECASE)
IMPLEMENTATION_RE = re.compile(r'\*\*Implementation:\*\*\s*`([^`]+)`', re.IGNORECASE)
DOCUMENTATION_RE = re.compile(r'\*\*Documentation:\*\*\s*`([^`]+)`', re.IGNORECASE)

def extract_paths(md_path: Path):
    text = md_path.read_text(encoding="utf-8")

    # Try Block Script first, then fall back to Implementation
    m_block = BLOCK_SCRIPT_RE.search(text)
    if not m_block:
        m_block = IMPLEMENTATION_RE.search(text)

    m_doc = DOCUMENTATION_RE.search(text)

    block_script = m_block.group(1) if m_block else "NOT FOUND"
    documentation = m_doc.group(1) if m_doc else "NOT FOUND"

    return block_script, documentation

def main(root="."):
    root_path = Path(root)

    # Pick up your expert review + related md files in this folder
    md_files = sorted(
        p for p in root_path.glob("*.md")
        if (
            p.name.endswith("_expert_review.md")
            or p.name.endswith("_improvement_research.md")
            or p.name.endswith("_LUXALGO_SUCCESS.md")
        )
    )

    for md in md_files:
        block_script, documentation = extract_paths(md)

        print(f"Expert Report: {md.name}")
        print(f"Block Script: {block_script}")
        print(f"Document: {documentation}")
        print("-" * 80)

if __name__ == "__main__":
    main()
