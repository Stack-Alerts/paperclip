#!/usr/bin/env python3
"""QA Research Fact-Check Pipeline. BTCAAAAA-22886 / BTCAAAAA-3223."""

from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

COMPANY_ID = "73419cf3-bd37-4a7c-8782-311ccb47fced"
API_BASE = "http://127.0.0.1:3100"
AGENTS = {
    "general_researcher": "df7b4035-e034-467e-af06-d25c869c810f",
    "strategy_researcher": "e3fcab65-c9a3-45bd-97e8-5145d3d6db5e",
    "security_analyst": "840eb9ff-f746-47da-9fdc-f0ec9d071155",
    "test_manager": "d53906e4-5660-4a47-bef4-148a69979b20",
}
ROUTING = {"btc": AGENTS["general_researcher"], "blockchain": AGENTS["general_researcher"],
            "exchange": AGENTS["general_researcher"], "nautilus": AGENTS["general_researcher"],
            "strategy": AGENTS["strategy_researcher"], "signal": AGENTS["strategy_researcher"],
            "indicator": AGENTS["strategy_researcher"], "security": AGENTS["security_analyst"],
            "risk": AGENTS["security_analyst"]}


def _api(method, path, body=None):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _route(desc):
    for kw, aid in ROUTING.items():
        if kw in desc.lower():
            return aid
    return AGENTS["test_manager"]


def cmd_scan(args):
    issues = _api("GET", f"/api/companies/{COMPANY_ID}/issues?status=in_progress")
    items = issues.get("items", []) if isinstance(issues, dict) else issues
    if args.assignee:
        items = [i for i in items if i.get("assigneeAgentId") == args.assignee]
    flagged = []
    for i in items:
        combined = f'{i.get("title", "")} {i.get("description", "")}'.lower()
        keywords = ["tooltip", "label", "copy", "text", "message", "description"]
        if any(k in combined for k in keywords):
            flagged.append({"id": i.get("identifier"), "title": i.get("title"),
                            "reviewer": _route(combined)})
    print(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                       "scanned": len(items), "flagged": len(flagged),
                       "items": flagged}, indent=2))


def cmd_verify(args):
    issue = _api("GET", f"/api/issues/{args.issue_id}")
    print(json.dumps({"issue": args.issue_id, "reviewer": _route(
        f'{issue.get("title", "")} {issue.get("description", "")}'),
        "verdict": "PENDING"}, indent=2))


def cmd_route(args):
    issue = _api("GET", f"/api/issues/{args.issue_id}")
    reviewer = _route(f'{issue.get("title", "")} {issue.get("description", "")}')
    names = {v: k for k, v in AGENTS.items()}
    print(json.dumps({"issue": args.issue_id, "routed_to": names.get(reviewer, reviewer)}, indent=2))


def main():
    p = argparse.ArgumentParser(description="QA Fact-Check Pipeline")
    s = p.add_subparsers(dest="command", required=True)
    sp = s.add_parser("scan"); sp.add_argument("--assignee")
    s.add_parser("verify").add_argument("issue_id")
    s.add_parser("route").add_argument("issue_id")
    args = p.parse_args()
    {"scan": cmd_scan, "verify": cmd_verify, "route": cmd_route}[args.command](args)


if __name__ == "__main__":
    main()
