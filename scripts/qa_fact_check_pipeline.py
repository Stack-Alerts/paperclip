#!/usr/bin/env python3
"""QA Research Fact-Check Pipeline. BTCAAAAA-22886 / BTCAAAAA-25559."""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    output = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "scanned": len(items), "flagged": len(flagged),
              "items": flagged}
    print(json.dumps(output, indent=2))
    if args.strict and flagged:
        sys.exit(1)


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


# ── check command: automated factual-accuracy verification ──────────────

CHECK_TYPES = {}


def _register(name):
    def deco(fn):
        CHECK_TYPES[name] = fn
        return fn
    return deco


def _safe_int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _line_count(filepath):
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def _dir_size_gb(dirpath):
    if not os.path.isdir(dirpath):
        return None
    total = 0
    for root, _, files in os.walk(dirpath):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return round(total / (1024 ** 3), 2)


def _env_get(key):
    for fname in (".env", ".env.example"):
        fp = os.path.join(REPO_ROOT, fname)
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#"):
                        continue
                    if "=" in line and line.split("=", 1)[0].strip() == key:
                        return line.split("=", 1)[1].strip()
        except OSError:
            pass
    return None


@_register("file_exists")
def _check_file_exists(params):
    path = os.path.join(REPO_ROOT, params["path"])
    exists = os.path.exists(path)
    expected = params.get("expected", True)
    return {"actual": exists, "pass": exists == expected,
            "detail": f"path={params['path']} exists={exists}"}


@_register("line_count_tolerance")
def _check_line_count(params):
    path = os.path.join(REPO_ROOT, params["path"])
    actual = _line_count(path)
    if actual is None:
        return {"actual": None, "pass": False,
                "detail": f"file {params['path']} not found or unreadable"}
    claimed = params["claimed"]
    tolerance = params.get("tolerance_pct", 10)
    deviation = abs(actual - claimed) / max(claimed, 1) * 100
    passed = deviation <= tolerance
    return {"actual": actual, "claimed": claimed, "pass": passed,
            "detail": f"actual={actual} claimed={claimed} deviation={deviation:.1f}%"}


@_register("version_min")
def _check_version_min(params):
    pkg = params["package"]
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {pkg}; print({pkg}.__version__)"],
            capture_output=True, text=True, timeout=10)
        actual = result.stdout.strip()
    except Exception:
        return {"actual": None, "pass": False,
                "detail": f"cannot import {pkg}"}
    from packaging.version import Version
    passed = Version(actual) >= Version(params["min_version"])
    return {"actual": actual, "min_required": params["min_version"], "pass": passed,
            "detail": f"installed={actual} required>={params['min_version']}"}


@_register("env_key_exists")
def _check_env_key(params):
    val = _env_get(params["key"])
    exists = val is not None
    expected = params.get("expected", True)
    return {"actual": exists, "pass": exists == expected,
            "detail": f"key={params['key']} found_in_env={exists} value={val}"}


@_register("env_key_value")
def _check_env_key_value(params):
    val = _env_get(params["key"])
    if val is None:
        return {"actual": None, "pass": False,
                "detail": f"key={params['key']} not found in .env or .env.example"}
    expected = str(params["expected"])
    passed = val == expected
    return {"actual": val, "expected": expected, "pass": passed,
            "detail": f"key={params['key']} actual={val} expected={expected}"}


@_register("dir_size_tolerance")
def _check_dir_size(params):
    actual_gb = _dir_size_gb(os.path.join(REPO_ROOT, params["path"]))
    if actual_gb is None:
        return {"actual": None, "pass": False,
                "detail": f"dir {params['path']} not found"}
    claimed = params["claimed_gb"]
    tolerance = params.get("tolerance_pct", 20)
    deviation = abs(actual_gb - claimed) / max(claimed, 1) * 100
    passed = deviation <= tolerance
    return {"actual_gb": actual_gb, "claimed_gb": claimed, "pass": passed,
            "detail": f"actual={actual_gb}GB claimed={claimed}GB deviation={deviation:.1f}%"}


@_register("text_not_in_file")
def _check_text_not_in_file(params):
    path = os.path.join(REPO_ROOT, params["path"])
    if not os.path.isfile(path):
        return {"actual": None, "pass": False,
                "detail": f"file {params['path']} not found"}
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
        return {"actual": None, "pass": False,
                "detail": f"cannot read {params['path']}"}
    found = params["text"] in content
    passed = not found
    return {"actual": found, "pass": passed,
            "detail": f"text_present={found} in {params['path']}"}


def _run_check(item):
    check_type = item["type"]
    if check_type not in CHECK_TYPES:
        return {**item, "verdict": "ERROR", "error": f"unknown check type: {check_type}"}
    try:
        result = CHECK_TYPES[check_type](item.get("params", {}))
    except Exception as exc:
        return {**item, "verdict": "ERROR", "error": str(exc)}
    verdict = "PASS" if result["pass"] else "FAIL"
    return {**item, "verdict": verdict, "result": result}


def cmd_check(args):
    with open(args.checklist) as f:
        checklist = json.load(f)
    items = checklist.get("checks", checklist) if isinstance(checklist, dict) else checklist
    results = [_run_check(item) for item in items]
    verdicts = [r["verdict"] for r in results]
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checklist": args.checklist,
        "total": len(results),
        "pass": verdicts.count("PASS"),
        "fail": verdicts.count("FAIL"),
        "error": verdicts.count("ERROR"),
        "results": results,
    }
    print(json.dumps(summary, indent=2))
    if summary["fail"] > 0 or summary["error"] > 0:
        sys.exit(1)


# ── main ────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="QA Fact-Check Pipeline")
    s = p.add_subparsers(dest="command", required=True)

    sp = s.add_parser("scan")
    sp.add_argument("--assignee")
    sp.add_argument("--strict", action="store_true",
                    help="exit non-zero when flagged items are found")

    s.add_parser("verify").add_argument("issue_id")
    s.add_parser("route").add_argument("issue_id")

    spc = s.add_parser("check")
    spc.add_argument("checklist", help="path to checklist JSON file")

    args = p.parse_args()
    {"scan": cmd_scan, "verify": cmd_verify, "route": cmd_route,
     "check": cmd_check}[args.command](args)


if __name__ == "__main__":
    main()
