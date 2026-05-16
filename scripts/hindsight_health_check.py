#!/usr/bin/env python3
"""Health-check monitor for the Hindsight API memory plugin.

Checks the Hindsight API health endpoint and Prometheus metrics to verify
the service is running and memory usage is within the configured threshold.

Usage:
    python scripts/hindsight_health_check.py
    python scripts/hindsight_health_check.py --json
    python scripts/hindsight_health_check.py --memory-threshold-gb 2.5
    python scripts/hindsight_health_check.py --dry-run

Exit codes:
    0 — healthy
    1 — unhealthy (API unreachable, memory exceeds threshold)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger("hindsight_health_check")

API_BASE_URL = os.environ.get("HINDSIGHT_API_URL", "http://127.0.0.1:8888")
DEFAULT_MEMORY_THRESHOLD_GB = 2.0
REQUEST_TIMEOUT_S = 10

STATE_DIR = Path.home() / ".paperclip" / "hindsight_monitor"
STATE_FILE = STATE_DIR / "hindsight_health_state.json"


def _parse_metric_value(metrics_text: str, metric_name: str) -> float | None:
    """Extract a gauge metric value from Prometheus text format."""
    pattern = rf"^{metric_name}\s+([0-9.e+\-]+)"
    for line in metrics_text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        match = re.match(pattern, line)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def check_health(memory_threshold_gb: float = DEFAULT_MEMORY_THRESHOLD_GB) -> dict:
    now = datetime.now(timezone.utc)

    base = {
        "timestamp": now.isoformat(),
        "memory_threshold_gb": memory_threshold_gb,
        "api_healthy": False,
        "api_detail": "",
        "service_active": False,
        "memory_gb": 0.0,
        "issues": [],
    }

    try:
        resp = requests.get(
            f"{API_BASE_URL}/health", timeout=REQUEST_TIMEOUT_S
        )
        base["api_healthy"] = resp.status_code == 200
        base["api_detail"] = resp.text.strip()
    except requests.RequestException as exc:
        base["issues"].append(f"API unreachable: {exc}")
        base["api_detail"] = str(exc)

    if base["api_healthy"]:
        base["service_active"] = True
        try:
            metrics_resp = requests.get(
                f"{API_BASE_URL}/metrics", timeout=REQUEST_TIMEOUT_S
            )
            if metrics_resp.status_code == 200:
                rss_bytes = _parse_metric_value(
                    metrics_resp.text, "process_resident_memory_bytes"
                )
                if rss_bytes is not None:
                    base["memory_gb"] = round(rss_bytes / (1024 ** 3), 3)
                else:
                    base["issues"].append("Could not parse memory metric")
            else:
                base["issues"].append(
                    f"Metrics endpoint returned {metrics_resp.status_code}"
                )
        except requests.RequestException as exc:
            base["issues"].append(f"Metrics fetch failed: {exc}")

    healthy = True
    status = "healthy"

    if not base["api_healthy"]:
        healthy = False
        status = "unhealthy"

    if base["memory_gb"] > memory_threshold_gb:
        healthy = False
        status = "unhealthy"
        base["issues"].append(
            f"Memory {base['memory_gb']}GB exceeds threshold {memory_threshold_gb}GB"
        )

    if base["memory_gb"] > memory_threshold_gb * 0.85:
        if healthy:
            status = "warning"

    base["status"] = status
    base["healthy"] = healthy

    return base


def write_state(result: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(result, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="Health-check monitor for the Hindsight API memory plugin",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON summary to stdout",
    )
    parser.add_argument(
        "--memory-threshold-gb",
        type=float,
        default=DEFAULT_MEMORY_THRESHOLD_GB,
        metavar="GB",
        help=f"Memory threshold in GB (default: {DEFAULT_MEMORY_THRESHOLD_GB})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run health check but do not write state file",
    )
    args = parser.parse_args()

    result = check_health(memory_threshold_gb=args.memory_threshold_gb)

    if not args.dry_run:
        write_state(result)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        status_icon = "OK" if result["healthy"] else "FAIL"
        status_label = result["status"].upper()
        print(f"Hindsight API Health: {status_icon} ({status_label})")
        print(f"  API reachable:   {result['api_healthy']}")
        print(f"  Memory:          {result['memory_gb']} GB")
        print(f"  Threshold:       {result['memory_threshold_gb']} GB")
        issues_str = ", ".join(result["issues"]) if result["issues"] else "none"
        print(f"  Issues:          {issues_str}")
        print(f"  Checked at:      {result['timestamp']}")

    return 0 if result["healthy"] else 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    sys.exit(main())
