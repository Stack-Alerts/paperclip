#!/usr/bin/env python3
"""
ITM Section H.2 — Testnet Dry Run Launcher
=============================================
Launch script for the 48-72h continuous testnet dry run.

Usage
-----
::

    # From project root:
    source .env
    python scripts/run_testnet_dry_run.py

    # With custom runtime:
    python scripts/run_testnet_dry_run.py --min-hours 72

    # With custom strategy directory:
    python scripts/run_testnet_dry_run.py --strategy-dir path/to/strategies

    # Quick smoke test (1 hour):
    python scripts/run_testnet_dry_run.py --min-hours 1

Environment variables required
--------------------------------
  BINANCE_TESTNET_API_KEY     — Binance Futures Testnet API key
  BINANCE_TESTNET_API_SECRET  — Binance Futures Testnet API secret

Both must be set and non-empty. Testnet keys can be obtained from:
  https://testnet.binancefuture.com

Safety
------
This script ALWAYS targets Binance Futures TESTNET. It will refuse to run if
the testnet credentials are not configured.

After the run completes, the dry-run report is saved to:
  logs/dry_run/dry_run_report.md
  logs/dry_run/final_snapshot.json

These files should be reviewed, and the CTO report must be uploaded as an
issue document (key: ``dry-run-report``) on BTCAAAAA-224.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is in sys.path
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Simple .env loader (no dependency on python-dotenv)."""
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            # Only set if not already in environment
            if key not in os.environ:
                os.environ[key] = value


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _configure_logging(log_dir: Path) -> None:
    """Configure logging for the dry run session."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "dry_run.log"

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=handlers,
        force=True,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("websocket").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured — writing to %s", log_file)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ITM Section H.2 — Testnet Dry Run (48-72h)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--min-hours",
        type=float,
        default=48.0,
        metavar="HOURS",
        help="Minimum run duration in hours (default: 48)",
    )
    parser.add_argument(
        "--strategy-dir",
        type=str,
        default="user_strategies",
        metavar="DIR",
        help="Directory containing Strategy Builder JSON exports (default: user_strategies)",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/dry_run",
        metavar="DIR",
        help="Directory to write run logs and report (default: logs/dry_run)",
    )
    parser.add_argument(
        "--status-interval",
        type=float,
        default=900.0,
        metavar="SECS",
        help="Status log interval in seconds (default: 900 = 15 min)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    _load_dotenv()
    args = _parse_args()

    log_dir = Path(args.log_dir)
    if not log_dir.is_absolute():
        log_dir = _PROJECT_ROOT / log_dir

    _configure_logging(log_dir)
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("ITM SECTION H.2 — TESTNET DRY RUN LAUNCHER")
    logger.info("Target exchange: Binance Futures TESTNET (NOT MAINNET)")
    logger.info("Min runtime: %.0f hours", args.min_hours)
    logger.info("Strategy dir: %s", args.strategy_dir)
    logger.info("Log dir: %s", log_dir)
    logger.info("=" * 70)

    from src.itm.dry_run.runner import DryRunRunner, DryRunRunnerConfig

    config = DryRunRunnerConfig(
        min_runtime_hours=args.min_hours,
        strategy_dir=args.strategy_dir,
        status_log_interval_secs=args.status_interval,
        log_dir=str(log_dir),
    )

    runner = DryRunRunner(config=config)

    try:
        result = runner.run()
    except RuntimeError as exc:
        logger.error("STARTUP FAILED: %s", exc)
        print(f"\n[ERROR] {exc}\n", file=sys.stderr)
        return 1

    # Print final criteria summary to stdout
    criteria = result.get("criteria", {})
    all_passing = criteria.get("all_passing", False)

    print("\n" + "=" * 70)
    print("DRY RUN COMPLETE")
    print("=" * 70)
    for k, v in criteria.items():
        if k != "all_passing" and k != "evaluated_at":
            print(f"  {k}: {v}")
    print("-" * 70)
    print(f"  OVERALL: {'✓ ALL CRITERIA PASSING' if all_passing else '✗ SOME CRITERIA FAILED'}")
    print("=" * 70)
    print(f"\nFull report: {result.get('report_path', 'logs/dry_run/dry_run_report.md')}")
    print("\nNext steps:")
    if all_passing:
        print("  1. Upload dry_run_report.md as issue document 'dry-run-report' on BTCAAAAA-224")
        print("  2. Request CTO sign-off on the report")
        print("  3. Board go/no-go review")
    else:
        print("  1. Review failure details in the report")
        print("  2. Address issues and re-run dry run before proceeding")

    return 0 if all_passing else 1


if __name__ == "__main__":
    sys.exit(main())
