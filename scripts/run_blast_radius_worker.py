"""Blast Radius polling worker runner — thin wrapper around the unified CLI.

Sets up the environment (sys.path, .env) then delegates to the unified
Blast Radius CLI (``python -m blast_radius worker``).

Usage:
    python scripts/run_blast_radius_worker.py [--dry-run] [--force-reprocess]
    python scripts/run_blast_radius_worker.py --issue-id <uuid> [--old-status <status>]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def main() -> None:
    """Set up environment and delegate to the unified Blast Radius CLI."""
    from blast_radius.__main__ import main as cli_main

    sys.exit(cli_main())


if __name__ == "__main__":
    main()
