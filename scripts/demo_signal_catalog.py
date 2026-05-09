#!/usr/bin/env python3
"""
CLI harness for SignalCatalogService — BTCAAAAA-687

Demonstrates:
- Full registry load (all 83+ blocks)
- Live stat augmentation (if DB available via .env)
- Context string generation and token estimate
- Signal search
- get_signal_info / list_signals_by_type tool-call outputs

Usage:
    python scripts/demo_signal_catalog.py
    python scripts/demo_signal_catalog.py --no-stats
    python scripts/demo_signal_catalog.py --search "oscillator momentum"
    python scripts/demo_signal_catalog.py --signal RSI_OVERSOLD
    python scripts/demo_signal_catalog.py --category OSCILLATORS
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.ai_consultant.signal_catalog import SignalCatalogService
from src.optimizer_v3.database.config import get_db_url


def _separator(label: str = "", width: int = 70) -> None:
    if label:
        side = (width - len(label) - 2) // 2
        print("=" * side + f" {label} " + "=" * (width - side - len(label) - 2))
    else:
        print("=" * width)


def main() -> None:
    parser = argparse.ArgumentParser(description="Signal Catalog Service demo")
    parser.add_argument("--no-stats", action="store_true", help="Skip live DB stats")
    parser.add_argument("--search", metavar="QUERY", help="Search blocks by keyword")
    parser.add_argument("--signal", metavar="NAME", help="Get info for a specific signal")
    parser.add_argument("--category", metavar="CAT", help="List signals by category")
    parser.add_argument("--context-only", action="store_true", help="Only print the context string")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Determine DB URL
    # ------------------------------------------------------------------
    db_url: str | None = None
    if not args.no_stats:
        try:
            db_url = get_db_url()
        except Exception:
            print("[WARN] Could not load DB config; running without live stats.\n")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    _separator("Signal Catalog Service — BTCAAAAA-687")
    print(f"Loading registry from: {ROOT}/src/detectors/building_blocks/")
    if db_url:
        print(f"Live stats: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    else:
        print("Live stats: disabled")
    print()

    t0 = time.perf_counter()
    svc = SignalCatalogService(db_url=db_url)
    svc.load(with_live_stats=not args.no_stats)
    elapsed = time.perf_counter() - t0

    print(f"Loaded in {elapsed:.2f}s:")
    print(f"  Blocks  : {svc.block_count}")
    print(f"  Signals : {svc.signal_count}")
    print(f"  Stats   : {svc._stats_source}")
    print(f"  Cats    : {', '.join(svc.categories)}")

    # ------------------------------------------------------------------
    # Context string
    # ------------------------------------------------------------------
    _separator("Context String")
    ctx = svc.context_string()
    if args.context_only:
        print(ctx)
        return

    token_estimate = len(ctx) / 4
    print(f"Length: {len(ctx)} chars | Est. tokens: ~{token_estimate:.0f}")
    print()
    print(ctx)

    # ------------------------------------------------------------------
    # Optional: search
    # ------------------------------------------------------------------
    if args.search:
        _separator(f"Search: '{args.search}'")
        results = svc.search(args.search)
        print(f"Found {len(results)} result(s):")
        for r in results[:10]:
            signals_preview = ", ".join(r["signals"][:5])
            print(f"  [{r['category']}] {r['name']} (wt={r['weight']}) — {signals_preview}")

    # ------------------------------------------------------------------
    # Optional: get_signal_info
    # ------------------------------------------------------------------
    if args.signal:
        _separator(f"Signal Info: {args.signal}")
        info = svc.get_signal_info(args.signal)
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"Signal '{args.signal}' not found in catalog.")

    # ------------------------------------------------------------------
    # Optional: list_signals_by_type
    # ------------------------------------------------------------------
    if args.category:
        _separator(f"Signals by Type: {args.category}")
        results = svc.list_signals_by_type(args.category)
        print(f"Found {len(results)} signal(s) in '{args.category}':")
        for r in results[:20]:
            wr = r.get("stats", {}) or {}
            wr_str = f" wr={wr.get('win_rate', '?')}" if wr and wr.get("win_rate") else ""
            print(f"  {r['signal']} ({r['block']}){wr_str}")
        if len(results) > 20:
            print(f"  … and {len(results) - 20} more")

    # ------------------------------------------------------------------
    # Demo: tool-call examples (when no args given)
    # ------------------------------------------------------------------
    if not any([args.search, args.signal, args.category]):
        _separator("Demo: get_signal_info('BULLISH')")
        info = svc.get_signal_info("BULLISH")
        if info:
            print(f"Emitted by {len(info['emitted_by'])} blocks: {info['emitted_by'][:5]} ...")

        _separator("Demo: list_signals_by_type('OSCILLATORS')")
        osc_sigs = svc.list_signals_by_type("OSCILLATORS")
        print(f"Found {len(osc_sigs)} signals in OSCILLATORS:")
        for r in osc_sigs[:10]:
            print(f"  {r['signal']} — {r['block']}")

        _separator("Demo: search('momentum bullish')")
        hits = svc.search("momentum bullish")
        print(f"Found {len(hits)} blocks matching 'momentum bullish':")
        for r in hits[:5]:
            print(f"  [{r['category']}] {r['name']}")

    _separator()
    print("Done.")


if __name__ == "__main__":
    main()
