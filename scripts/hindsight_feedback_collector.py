#!/usr/bin/env python3
"""Hindsight Memory Plugin feedback collector.

Agents report memory quality via structured feedback. Stores JSON-lines
log and generates aggregated reports for quality trending.

Usage:
  # Submit feedback
  python scripts/hindsight_feedback_collector.py submit \
    --agent AutomationEngineer \
    --recall-quality 4 \
    --retain-relevance 3 \
    --helpfulness 5 \
    --notes "Auto-recall pulled stale context from 2 weeks ago"

  # Submit minimal (defaults to 3=neutral)
  python scripts/hindsight_feedback_collector.py submit \
    --agent QAEngineer \
    --helpfulness 2 \
    --notes "Recalled facts were about the wrong issue"

  # View summary report
  python scripts/hindsight_feedback_collector.py report

  # View report as JSON
  python scripts/hindsight_feedback_collector.py report --json
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

FEEDBACK_DIR = os.path.expanduser("~/.paperclip/hindsight_feedback")
ENTRIES_FILE = os.path.join(FEEDBACK_DIR, "feedback_entries.jsonl")
REPORT_FILE = os.path.join(FEEDBACK_DIR, "feedback_report.json")

RATING_SCALE = {1: "poor", 2: "below_average", 3: "neutral", 4: "good", 5: "excellent"}


def ensure_dir():
    os.makedirs(FEEDBACK_DIR, exist_ok=True)


def submit_feedback(args):
    ensure_dir()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": args.agent,
        "run_id": args.run_id,
        "issue_id": args.issue_id,
        "ratings": {
            "recall_quality": args.recall_quality,
            "retain_relevance": args.retain_relevance,
            "helpfulness": args.helpfulness,
        },
        "notes": args.notes or "",
    }

    entry["ratings"] = {k: v for k, v in entry["ratings"].items() if v is not None}

    with open(ENTRIES_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Feedback recorded: {entry['agent']} rated helpfulness {entry['ratings'].get('helpfulness', 'N/A')}")
    return entry


def load_entries():
    entries = []
    if not os.path.exists(ENTRIES_FILE):
        return entries
    with open(ENTRIES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def generate_report(as_json=False):
    entries = load_entries()
    if not entries:
        msg = {"error": "No feedback entries found"} if as_json else "No feedback entries found."
        print(json.dumps(msg) if as_json else msg)
        return

    by_agent = defaultdict(list)
    for e in entries:
        by_agent[e["agent"]].append(e)

    agent_stats = {}
    total_ratings = defaultdict(list)

    for agent, agent_entries in sorted(by_agent.items()):
        stats = {
            "count": len(agent_entries),
            "first_seen": agent_entries[0]["timestamp"],
            "last_seen": agent_entries[-1]["timestamp"],
            "averages": {},
        }
        for metric in ["recall_quality", "retain_relevance", "helpfulness"]:
            vals = [e["ratings"][metric] for e in agent_entries if metric in e.get("ratings", {})]
            if vals:
                avg = round(sum(vals) / len(vals), 2)
                stats["averages"][metric] = {
                    "mean": avg,
                    "n": len(vals),
                    "label": RATING_SCALE.get(round(avg), "unknown"),
                }
                total_ratings[metric].extend(vals)
        agent_stats[agent] = stats

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "unique_agents": len(by_agent),
        "agents": agent_stats,
        "global_averages": {},
    }
    for metric, vals in total_ratings.items():
        report["global_averages"][metric] = {
            "mean": round(sum(vals) / len(vals), 2),
            "n": len(vals),
            "label": RATING_SCALE.get(round(sum(vals) / len(vals)), "unknown"),
        }

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2, default=str)

    if as_json:
        print(json.dumps(report, indent=2, default=str))
        return

    print("=== Hindsight Memory Feedback Report ===")
    print(f"Entries: {report['total_entries']} | Agents: {report['unique_agents']}")
    print()
    for metric, data in report["global_averages"].items():
        print(f"  {metric:25s}  avg={data['mean']:.1f}  ({data['label']})  n={data['n']}")
    print()
    for agent in sorted(report["agents"]):
        stats = report["agents"][agent]
        print(f"  [{agent}]  {stats['count']} reports")
        for metric, data in stats["averages"].items():
            bar = "█" * round(data["mean"]) + "░" * (5 - round(data["mean"]))
            print(f"    {metric:23s}  {bar}  {data['mean']:.1f}")
        agent_entries_list = by_agent[agent]
        latest = agent_entries_list[-1]
        if latest.get("notes"):
            print(f"    latest note: {latest['notes'][:80]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Hindsight memory feedback collector")
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="Submit a feedback entry")
    p_submit.add_argument("--agent", required=True, help="Agent name (e.g. AutomationEngineer)")
    p_submit.add_argument("--run-id", default=None, help="Optional Paperclip run ID")
    p_submit.add_argument("--issue-id", default=None, help="Optional issue ID")
    p_submit.add_argument("--recall-quality", type=int, choices=range(1, 6), default=None,
                          help="Recall accuracy rating (1-5)")
    p_submit.add_argument("--retain-relevance", type=int, choices=range(1, 6), default=None,
                          help="Retention relevance rating (1-5)")
    p_submit.add_argument("--helpfulness", type=int, choices=range(1, 6), default=None,
                          help="Overall helpfulness rating (1-5)")
    p_submit.add_argument("--notes", default=None, help="Free-text qualitative feedback")

    p_report = sub.add_parser("report", help="Generate feedback summary report")
    p_report.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "submit":
        submit_feedback(args)
    elif args.command == "report":
        generate_report(as_json=args.json)


if __name__ == "__main__":
    main()
