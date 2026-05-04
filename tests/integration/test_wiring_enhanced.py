"""
Enhanced Wiring Test - Institutional Grade Exit Verification

CRITICAL INSIGHT:
- Trade COUNT is ENTRY-driven (same signals = same count)
- Parameters affect EXIT quality (TP/SL ratios, PnL, duration)
- Must measure EXIT metrics, not just count

Enhanced Metrics (Phase 1.2 — BTCAAAAA-149):
1. Exit type distribution (TP1/TP2/TP3/SL/TIME ratios)
2. Average PnL per trade
3. Win rate %
4. Average bars held
5. PnL standard deviation
6. Sharpe ratio (per-trade, annualised)
7. Max drawdown

This proves parameters ARE working but affecting outcomes, not quantity.
The wiring_test_*.csv files produced by _generate_discovery_report() now
include all of these columns.

Author: BTC_Engine_v3
Date: 2026-02-13
Enhanced: UIEngineer 2026-05-04 (BTCAAAAA-149, Phase 1.2)
"""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def analyze_enhanced_wiring(csv_path: str) -> Dict[str, Any]:
    """
    Enhanced wiring analysis — check EXIT metrics, not just trade count.

    Reads the enhanced CSV produced by _generate_discovery_report():
      scenario_id, description, trade_count, win_rate_pct, total_pnl,
      avg_pnl_per_trade, sharpe_ratio, exit_tp1, exit_tp2, exit_tp3,
      exit_sl, exit_time, avg_bars_held, max_drawdown

    Args:
        csv_path: Path to wiring test CSV (enhanced format).

    Returns:
        Dict with detailed exit analysis per scenario plus summary.
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        return {'status': 'ERROR', 'message': f'CSV not found: {csv_path}'}

    df = pd.read_csv(csv_file)

    required_cols = {'scenario_id', 'description', 'trade_count'}
    enhanced_cols = {
        'win_rate_pct', 'total_pnl', 'avg_pnl_per_trade',
        'sharpe_ratio', 'exit_tp1', 'exit_tp2', 'exit_tp3',
        'exit_sl', 'exit_time', 'avg_bars_held', 'max_drawdown',
    }

    missing_required = required_cols - set(df.columns)
    if missing_required:
        return {
            'status': 'ERROR',
            'message': f'Missing required columns: {missing_required}. '
                       'Re-run wiring test to generate enhanced CSV.',
        }

    has_enhanced = enhanced_cols.issubset(set(df.columns))

    print()
    print("=" * 80)
    print("ENHANCED WIRING ANALYSIS - INSTITUTIONAL GRADE")
    print("=" * 80)
    print(f"\nCSV:     {csv_path}")
    print(f"Rows:    {len(df)}")
    print(f"Enhanced metrics available: {'YES' if has_enhanced else 'NO (legacy CSV)'}")
    print()

    # Basic trade count stats (preserved from original)
    trade_counts = df['trade_count'].tolist()
    unique_counts = set(trade_counts)
    print(f"Trade Count Distribution:")
    print(f"  Unique results:  {len(unique_counts)}")
    print(f"  Range:           {min(trade_counts)} – {max(trade_counts)}")
    print()

    wiring_issues = []
    if len(unique_counts) < len(df) * 0.5:
        wiring_issues.append(
            "Too many identical trade counts — parameters may not be wired!"
        )

    result: Dict[str, Any] = {
        'status': 'PLACEHOLDER' if not has_enhanced else 'OK',
        'rows': len(df),
        'unique_trade_counts': len(unique_counts),
        'trade_count_range': (min(trade_counts), max(trade_counts)),
        'wiring_issues': wiring_issues,
    }

    if not has_enhanced:
        print("LEGACY CSV — enhanced columns not present.")
        print("Re-run wiring test to get full exit metrics.")
        print("=" * 80)
        result['message'] = 'Legacy CSV — re-run to get enhanced metrics'
        return result

    # -----------------------------------------------------------------------
    # Enhanced analysis
    # -----------------------------------------------------------------------

    # Scenario-level summary
    print(f"{'Scenario':<40} {'Trades':>6} {'WinRate':>8} {'TotalPnL':>10} {'Sharpe':>7} {'TP1':>4} {'TP2':>4} {'TP3':>4} {'SL':>4} {'Time':>4}")
    print("-" * 95)
    for _, row in df.iterrows():
        print(
            f"{str(row['description'])[:39]:<40} "
            f"{int(row.get('trade_count', 0)):>6} "
            f"{float(row.get('win_rate_pct', 0)):>7.1f}% "
            f"${float(row.get('total_pnl', 0)):>9.2f} "
            f"{float(row.get('sharpe_ratio', 0)):>7.3f} "
            f"{int(row.get('exit_tp1', 0)):>4} "
            f"{int(row.get('exit_tp2', 0)):>4} "
            f"{int(row.get('exit_tp3', 0)):>4} "
            f"{int(row.get('exit_sl', 0)):>4} "
            f"{int(row.get('exit_time', 0)):>4}"
        )

    print()

    # Best performers
    if 'total_pnl' in df.columns and df['total_pnl'].notna().any():
        best_pnl_idx = df['total_pnl'].idxmax()
        best_sharpe_idx = df['sharpe_ratio'].idxmax()
        best_freq_idx = df['trade_count'].idxmax()

        print("GOLD WINNERS:")
        print(f"  Most Profitable: {df.loc[best_pnl_idx, 'description']}")
        print(f"    PnL: ${df.loc[best_pnl_idx, 'total_pnl']:.2f}  "
              f"WinRate: {df.loc[best_pnl_idx, 'win_rate_pct']:.1f}%  "
              f"Trades: {df.loc[best_pnl_idx, 'trade_count']}")
        print()
        print(f"  Best Sharpe:     {df.loc[best_sharpe_idx, 'description']}")
        print(f"    Sharpe: {df.loc[best_sharpe_idx, 'sharpe_ratio']:.3f}  "
              f"PnL: ${df.loc[best_sharpe_idx, 'total_pnl']:.2f}  "
              f"Trades: {df.loc[best_sharpe_idx, 'trade_count']}")
        print()
        print(f"  Most Frequent:   {df.loc[best_freq_idx, 'description']}")
        print(f"    Trades: {df.loc[best_freq_idx, 'trade_count']}  "
              f"WinRate: {df.loc[best_freq_idx, 'win_rate_pct']:.1f}%  "
              f"PnL: ${df.loc[best_freq_idx, 'total_pnl']:.2f}")
        print()

    # Wiring verification: check if EXIT METRICS vary (proves parameters work)
    exit_cols = ['exit_tp1', 'exit_tp2', 'exit_tp3', 'exit_sl', 'exit_time']
    exit_variety: Dict[str, int] = {}
    for col in exit_cols:
        if col in df.columns:
            exit_variety[col] = df[col].nunique()

    all_constant = all(v == 1 for v in exit_variety.values())
    if all_constant:
        wiring_issues.append(
            "All exit type columns are constant — parameters may not affect exit behaviour!"
        )
        print("WARNING: All exit distributions are identical across scenarios.")
    else:
        print("Exit Distribution Variety (unique values per exit type):")
        for col, count in exit_variety.items():
            status = 'OK' if count > 1 else 'CONSTANT'
            print(f"  {col:<10}: {count} unique values  [{status}]")
        print()

    # Wiring verdict
    if wiring_issues:
        print("WIRING ISSUES DETECTED:")
        for issue in wiring_issues:
            print(f"  - {issue}")
    else:
        print("All parameters appear to be wired correctly (exit metrics vary across scenarios).")

    print("=" * 80)
    print()

    result.update({
        'status': 'OK' if not wiring_issues else 'WIRING_ISSUES',
        'message': 'Enhanced analysis complete',
        'wiring_issues': wiring_issues,
        'exit_variety': exit_variety,
        'best_pnl_scenario': df.loc[df['total_pnl'].idxmax(), 'description'] if 'total_pnl' in df.columns else None,
    })
    return result


# ---------------------------------------------------------------------------
# Utility: find latest wiring test CSV
# ---------------------------------------------------------------------------

def find_latest_wiring_csv(results_dir: str = 'tests/integration/results') -> Optional[Path]:
    """
    Find the most recent wiring_test_*.csv or discovery_results_*.csv file.
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        return None

    candidates = (
        list(results_path.glob('wiring_test_*.csv'))
        + list(results_path.glob('discovery_results_*.csv'))
    )
    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        latest = find_latest_wiring_csv()
        if not latest:
            print("No wiring test CSV found in tests/integration/results/")
            print("Run the Wiring Test or Config Discovery from the Strategy Builder UI first.")
            sys.exit(1)
        csv_path = str(latest)
        print(f"Auto-detected latest CSV: {csv_path}")

    results = analyze_enhanced_wiring(csv_path)
    if results.get('wiring_issues'):
        sys.exit(1)
