"""Impact Gate polling worker runner — thin wrapper around the polling daemon CLI.

Sets up the environment (sys.path, .env) then delegates to the Impact Gate
polling worker (``python -m impact_gate.polling_worker``).

Usage:
    python scripts/run_impact_gate_polling_worker.py                      # run once, then exit
    python scripts/run_impact_gate_polling_worker.py --dry-run            # log reports, don't post
    python scripts/run_impact_gate_polling_worker.py --daemon             # poll every 300 s forever
    python scripts/run_impact_gate_polling_worker.py --daemon \\
        --poll-interval 60 --lookback-minutes 20                          # custom intervals
    python scripts/run_impact_gate_polling_worker.py --issue-id <uuid>    # process single issue
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from impact_gate.polling_worker import main as worker_main


def main() -> None:
    """Set up environment and delegate to the Impact Gate polling worker CLI."""
    worker_main()


if __name__ == "__main__":
    main()
