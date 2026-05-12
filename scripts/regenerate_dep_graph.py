#!/usr/bin/env python3
"""Regenerate dep_graph.json — entry point for the nightly dep-graph-refresh CI job.

Delegates to static_dep_graph.build_graph() which uses AST to parse
all Python imports in the repo and writes the result to dep_graph.json.

Exit code is always 0 — parse errors are informational only and should
not cause the CI step to fail (the graph is still written successfully).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from static_dep_graph import ROOT, build_graph


def main() -> int:
    print(f"Regenerating dependency graph for {ROOT} ...")
    t0 = time.perf_counter()
    graph = build_graph(ROOT)
    elapsed = time.perf_counter() - t0

    stats = graph["stats"]
    print(f"\n=== Build Stats ===")
    print(f"  Total .py files : {stats['total_files']}")
    print(f"  Parsed          : {stats['parsed_files']}")
    print(f"  Parse errors    : {stats['error_files']}")
    print(f"  Parse rate      : {stats['parse_rate_pct']}%")
    print(f"  Edges (imports) : {stats['edge_count']}")
    print(f"  Build time      : {elapsed:.3f}s")

    if graph["parse_errors"]:
        print(f"\nWARNING: {len(graph['parse_errors'])} unparseable files:")
        for f in graph["parse_errors"]:
            print(f"  {f}")

    output_path = ROOT / "dep_graph.json"
    output_path.write_text(json.dumps(graph, indent=2))
    print(f"\nGraph written to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
