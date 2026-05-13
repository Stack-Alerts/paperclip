#!/usr/bin/env python3
"""Blast Radius CLI — thin wrapper around the unified CLI (python -m blast_radius).

Usage
-----
    blast-radius query --files src/optimizer_v3/database/config.py src/strategies/base.py
    blast-radius generate --issue-id <paperclip-issue-id> [--dry-run]
    blast-radius serve [--port 8765]
    blast-radius worker [--dry-run]
    blast-radius worker --loop 300 [--dry-run]
    blast-radius worker --issue-id <uuid> [--old-status <status>] [--dry-run]

All subcommands delegate to ``python -m blast_radius``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")


def main() -> int:
    from blast_radius.__main__ import main as cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
