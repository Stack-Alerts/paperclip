#!/usr/bin/env python3
"""
ITM Section H.2 — Binance Testnet Environment Validator

Validates that the runtime environment is correctly configured for the
testnet dry run. Exits with code 0 if all checks pass, 1 if any fail.

Usage:
    python scripts/validate_testnet_env.py
    python scripts/validate_testnet_env.py --strict  # also check testnet connectivity
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Simple .env loader."""
    env_path = Path(__file__).parent.parent / ".env"
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
            if key not in os.environ:
                os.environ[key] = value


_CHECKS: list[dict] = []


def _check(name: str, condition: bool, hint: str = "") -> None:
    _CHECKS.append({"name": name, "passed": condition, "hint": hint})


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(
        description="Validate ITM testnet deployment environment"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also validate Binance testnet connectivity (requires credentials)",
    )
    args = parser.parse_args()

    paper_trading = os.environ.get("ITM_PAPER_TRADING", "true").lower() in ("true", "1", "yes")

    _check(
        "ITM_PAPER_TRADING defaults to true (safe mode)",
        paper_trading,
        hint="Set ITM_PAPER_TRADING=false only after CTO sign-off for live testnet",
    )

    _check(
        ".env file exists",
        Path(__file__).parent.parent.joinpath(".env").exists(),
        hint="Copy .env.example to .env and configure",
    )

    _check(
        "VENV exists",
        Path(__file__).parent.parent.joinpath("venv").exists(),
        hint="Run: python -m venv venv && venv/bin/pip install -r requirements.txt",
    )

    if paper_trading:
        _check(
            "Paper mode: Binance testnet credentials NOT required",
            True,
            hint="Credentials are optional in paper mode",
        )
    else:
        key = os.environ.get("BINANCE_TESTNET_API_KEY", "")
        secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
        placeholders = {"", "your_testnet_api_key_here", "your_testnet_api_secret_here"}
        _check(
            "BINANCE_TESTNET_API_KEY configured",
            key not in placeholders,
            hint="Set in .env from https://testnet.binancefuture.com",
        )
        _check(
            "BINANCE_TESTNET_API_SECRET configured",
            secret not in placeholders,
            hint="Set in .env from https://testnet.binancefuture.com",
        )

    if args.strict and not paper_trading:
        try:
            from src.itm.engine.binance_client import BinanceClient
            client = BinanceClient.from_env(use_testnet=True)
            pos = client.get_position_size("BTCUSDT")
            _check("Binance Futures Testnet connectivity", True)
        except Exception as exc:
            _check(
                "Binance Futures Testnet connectivity",
                False,
                hint=f"Connection failed: {exc}",
            )

    print(f"\n{'='*60}")
    print(f"ITM TESTNET DEPLOYMENT ENVIRONMENT CHECK")
    print(f"{'='*60}")
    all_passed = True
    for check in _CHECKS:
        status = "PASS" if check["passed"] else "FAIL"
        if not check["passed"]:
            all_passed = False
        print(f"  [{status}] {check['name']}")
        if check["hint"] and not check["passed"]:
            print(f"         → {check['hint']}")
    print(f"{'='*60}")
    print(f"OVERALL: {'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")
    print(f"{'='*60}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
