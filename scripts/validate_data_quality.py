"""
Data Quality Validation — Market Data SLI Monitor

Checks:
  1. Gap detection for all stored timeframes (15m, 1h, 1d)
  2. Expected row counts per month (completeness SLA) — skips current month
  3. Data continuity (no missing bars in last N days)
  4. Trailing edge recency (no stale data)

Usage:
    python scripts/validate_data_quality.py          # full check, exit code = PASS/FAIL
    python scripts/validate_data_quality.py --json    # machine-readable JSON output
    python scripts/validate_data_quality.py --sla     # only check SLA thresholds

Returns exit code 0 = PASS, 1 = FAIL.
"""

import argparse
import json
import sys
import time
from calendar import monthrange
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_manager.unified_manager import UnifiedDataManager

TIMEFRAMES = ['15m', '1h', '1d']
BINANCE_HORIZON_DAYS = 90
TF_MINUTES = {'15m': 15, '1h': 60, '1d': 2880}


def _expected_bars(tf: str, year: int, month: int) -> int:
    days = monthrange(year, month)[1]
    if tf == '15m':
        return days * 96
    elif tf == '1h':
        return days * 24
    elif tf == '1d':
        return days
    return 0


def check_gaps(manager: UnifiedDataManager, timeframes: list) -> dict:
    results = {}
    for tf in timeframes:
        gaps = manager.detect_gaps_in_binance_files(
            tf,
            start_date=datetime.now(timezone.utc) - timedelta(days=BINANCE_HORIZON_DAYS),
        )
        total_missing = sum(g['missing_bars'] for g in gaps)
        results[tf] = {
            'gaps_found': len(gaps),
            'total_missing_bars': total_missing,
            'gaps': [
                {
                    'gap_start': str(g['gap_start']),
                    'gap_end': str(g['gap_end']),
                    'missing_bars': g['missing_bars'],
                    'duration': str(g['duration']),
                }
                for g in gaps
            ],
        }
    return results


def check_completeness(data_dir: Path, timeframes: list) -> dict:
    now = datetime.now(timezone.utc)
    results = {}

    for tf in timeframes:
        pattern = f'**/BTCUSDT_PERP_{tf}_*.parquet'
        files = sorted(data_dir.glob(pattern))
        tf_results = {}

        for f in files:
            try:
                df = pd.read_parquet(f, columns=['timestamp'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            except Exception as e:
                tf_results[f.name] = {'error': str(e), 'pass': False}
                continue

            name = f.name.replace('BTCUSDT_PERP_', '').replace('.parquet', '')
            month_str = name.split('_')[-1]
            try:
                year, month = int(month_str[:4]), int(month_str[5:7])
            except (ValueError, IndexError):
                continue

            actual = len(df)
            tzinfo_from = df['timestamp'].min()
            tzinfo_to = df['timestamp'].max()

            is_current = (year == now.year and month == now.month)
            if is_current:
                max_expected_bars_by_now = (now.day - 1) * (96 if tf == '15m' else 24 if tf == '1h' else 1)
                max_expected_bars_by_now += (now.hour * 60 + now.minute) // TF_MINUTES.get(tf, 15)
                expected = _expected_bars(tf, year, month)
                missing_pct = round((expected - actual) / expected * 100, 2)
                gap_pct = round((max_expected_bars_by_now - actual) / max_expected_bars_by_now * 100, 2) if max_expected_bars_by_now > 0 else 0
                bar_pass = gap_pct < 10
            else:
                expected = _expected_bars(tf, year, month)
                gap_pct = round((expected - actual) / expected * 100, 2) if expected > 0 else 0
                bar_pass = actual >= expected

            tf_results[name] = {
                'expected_bars': expected,
                'actual_bars': actual,
                'missing_bars': max(0, expected - actual),
                'missing_pct': gap_pct,
                'range_start': str(tzinfo_from),
                'range_end': str(tzinfo_to),
                'is_current_month': is_current,
                'pass': bar_pass,
            }

        results[tf] = tf_results
    return results


def check_recency(data_dir: Path, timeframes: list) -> dict:
    sla_minutes_map = {'15m': 30, '1h': 120, '1d': 2880}
    results = {}
    now = datetime.now(timezone.utc)

    for tf in timeframes:
        pattern = f'**/BTCUSDT_PERP_{tf}_*.parquet'
        files = sorted(data_dir.glob(pattern))
        if not files:
            results[tf] = {'error': 'No files found', 'pass': False}
            continue

        latest_file = files[-1]
        try:
            df = pd.read_parquet(latest_file, columns=['timestamp'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        except Exception:
            results[tf] = {'error': str(e), 'pass': False}
            continue

        if df.empty:
            results[tf] = {'error': 'Empty file', 'pass': False}
            continue

        last_bar = df['timestamp'].max()
        age = now - last_bar
        age_minutes = age.total_seconds() / 60
        sla = sla_minutes_map.get(tf, 120)

        results[tf] = {
            'last_bar': str(last_bar),
            'age_minutes': round(age_minutes, 1),
            'sla_minutes': sla,
            'pass': age_minutes <= sla,
        }

    return results


def run_validation(manager: UnifiedDataManager, data_dir: Path, timeframes: list) -> dict:
    t0 = time.monotonic()
    gaps = check_gaps(manager, timeframes)
    completeness = check_completeness(data_dir, timeframes)
    recency = check_recency(data_dir, timeframes)

    all_pass = True
    failures = []

    for tf in timeframes:
        if gaps[tf]['gaps_found'] > 0:
            all_pass = False
            failures.append(f'{tf}: {gaps[tf]["gaps_found"]} gap(s), {gaps[tf]["total_missing_bars"]} missing bars')

    for tf in timeframes:
        for file_name, result in completeness.get(tf, {}).items():
            if not result.get('pass', True):
                all_pass = False
                failures.append(f'{tf}/{file_name}: expected ~{result["expected_bars"]} bars, got {result["actual_bars"]} ({result["missing_pct"]}% missing)')

    for tf in timeframes:
        if not recency[tf].get('pass', True):
            all_pass = False
            last_bar = recency[tf].get('last_bar', 'unknown')
            age = recency[tf].get('age_minutes', 0)
            sla = recency[tf].get('sla_minutes', 0)
            failures.append(f'{tf}: last bar {last_bar} is {age}min old (SLA: {sla}min)')

    duration = time.monotonic() - t0

    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'duration_seconds': round(duration, 2),
        'pass': all_pass,
        'failures': failures,
        'gaps': gaps,
        'completeness': completeness,
        'recency': recency,
    }


def main():
    parser = argparse.ArgumentParser(description='Market Data Quality Validation')
    parser.add_argument('--json', action='store_true', help='Output machine-readable JSON')
    parser.add_argument('--sla', action='store_true', help='Only check SLA thresholds (no full scan)')
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / 'data' / 'binance'
    timeframes = ['15m', '1h'] if args.sla else TIMEFRAMES

    manager = UnifiedDataManager(mode='live')
    report = run_validation(manager, data_dir, timeframes)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        status = 'PASS' if report['pass'] else 'FAIL'
        print(f'Data Quality Validation: [{status}]')
        print(f'Duration: {report["duration_seconds"]}s')
        print()

        for tf in TIMEFRAMES:
            g = report['gaps'].get(tf, {})
            if g.get('gaps_found', 0) == 0:
                print(f'  {tf}: ✅ 0 gaps')
            else:
                print(f'  {tf}: ❌ {g["gaps_found"]} gap(s), {g["total_missing_bars"]} missing bars')
                for gap in g.get('gaps', []):
                    print(f'       {gap["gap_start"]} → {gap["gap_end"]} ({gap["missing_bars"]} bars)')

        print()
        for tf in TIMEFRAMES:
            comp = report.get('completeness', {}).get(tf, {})
            for name, result in comp.items():
                mark = '✅' if result.get('pass') else '❌'
                lbl = ' (current month)' if result.get('is_current_month') else ''
                print(f'  {tf}/{name}: {mark} {result.get("actual_bars", "?")}/{result.get("expected_bars", "?")} bars{lbl}')

        print()
        for tf in TIMEFRAMES:
            r = report.get('recency', {}).get(tf, {})
            if 'error' in r:
                print(f'  {tf} recency: ❌ {r["error"]}')
            else:
                mark = '✅' if r.get('pass') else '❌'
                print(f'  {tf} recency: {mark} {r.get("age_minutes", "?")}min old')

        if not report['pass']:
            print()
            print('FAILURES:')
            for f in report['failures']:
                print(f'  ❌ {f}')

    sys.exit(0 if report['pass'] else 1)


if __name__ == '__main__':
    main()
