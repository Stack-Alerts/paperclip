#!/usr/bin/env python3
"""
BTCAAAAA-39939 verification: confirm all 23 claude_local agents on the live
server have the exact 10-key env block from the
`claude-local-config-template` skill and adapterConfig.timeoutSec=3800.

Diff-style output: every drift is reported as a row, then a single
verdict line. The script exits non-zero if any agent fails so this can
be used as a CI gate.

This is the byte-for-byte verification the issue explicitly asks for:
"verify direct GET /api/agents/:id for all 23 agents has the exact 10-key
env block and timeoutSec=3800".
"""

import argparse
import json
import os
import sys
import urllib.request

SKILL_ID = "a2bab736-d451-4a5a-82e2-30e49a984907"
EXPECTED_TIMEOUT_SEC = 3800
EXPECTED_DESIRED_SKILL = (
    "company/73419cf3-bd37-4a7c-8782-311ccb47fced/claude-local-config-template"
)


def _api_url(path):
    base = os.environ["PAPERCLIP_API_URL"].rstrip("/")
    return f"{base}{path}"


def _request(method, path, body=None):
    headers = {
        "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
        "Content-Type": "application/json",
    }
    if os.environ.get("PAPERCLIP_RUN_ID"):
        headers["X-Paperclip-Run-Id"] = os.environ["PAPERCLIP_RUN_ID"]
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_api_url(path), data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode() or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw}


def load_canonical_env():
    skill = _request("GET", f"/api/companies/{os.environ['PAPERCLIP_COMPANY_ID']}/skills/{SKILL_ID}")
    md = (skill.get("currentVersion") or {}).get("fileInventory", [{}])[0].get("content", "")
    start = md.find("```json")
    if start < 0:
        raise RuntimeError("Could not locate canonical env block in skill SKILL.md")
    end = md.find("```", start + 7)
    if end < 0:
        raise RuntimeError("Could not locate end of canonical env block fence")
    return json.loads(md[start + 7:end].strip())


def list_claude_local_agents():
    out = _request("GET", f"/api/companies/{os.environ['PAPERCLIP_COMPANY_ID']}/agents")
    if not isinstance(out, list):
        raise RuntimeError(f"Unexpected agent list response shape: {type(out).__name__}")
    return [a for a in out if a.get("adapterType") == "claude_local"]


def diff_env(actual, expected):
    missing = [k for k in expected.keys() if k not in actual]
    extra = [k for k in actual.keys() if k not in expected]
    mismatched = []
    for k in expected.keys() & actual.keys():
        if actual[k] != expected[k]:
            mismatched.append({"key": k, "actual": actual[k], "expected": expected[k]})
    return missing, mismatched, extra


def main():
    p = argparse.ArgumentParser(description="BTCAAAAA-39939 verification")
    p.add_argument("--company-id", default=os.environ.get("PAPERCLIP_COMPANY_ID"))
    args = p.parse_args()
    if not args.company_id:
        sys.exit("PAPERCLIP_COMPANY_ID env var required")
    os.environ["PAPERCLIP_COMPANY_ID"] = args.company_id
    for key in ("PAPERCLIP_API_KEY", "PAPERCLIP_API_URL"):
        if not os.environ.get(key):
            sys.exit(f"{key} env var required")

    run_id = os.environ.get("PAPERCLIP_RUN_ID", "no-run-id")
    expected_env = load_canonical_env()
    expected_keys = sorted(expected_env.keys())
    if len(expected_keys) != 10:
        print(
            f"[verify] WARNING: canonical env block has {len(expected_keys)} keys, expected 10",
            file=sys.stderr,
        )

    agents = list_claude_local_agents()
    rows = []
    failures = 0
    for a in agents:
        full = _request("GET", f"/api/agents/{a['id']}")
        cfg = full.get("adapterConfig") or {}
        env = cfg.get("env") or {}
        timeout = cfg.get("timeoutSec")
        desired = ((cfg.get("paperclipSkillSync") or {}).get("desiredSkills")) or []

        missing, mismatched, extra = diff_env(env, expected_env)
        timeout_ok = int(timeout) == EXPECTED_TIMEOUT_SEC if timeout is not None else False
        skill_ok = EXPECTED_DESIRED_SKILL in desired
        clean = not missing and not mismatched and not extra and timeout_ok and skill_ok

        rows.append({
            "id": a["id"],
            "name": a.get("name", a["id"]),
            "urlKey": a.get("urlKey"),
            "env_key_count": len(env),
            "expected_key_count": len(expected_env),
            "missing_keys": missing,
            "mismatched": mismatched,
            "unexpected_keys": extra,
            "timeoutSec": timeout,
            "timeout_expected": EXPECTED_TIMEOUT_SEC,
            "timeout_ok": timeout_ok,
            "desired_skill_present": skill_ok,
            "desired_skills": desired,
            "clean": clean,
        })
        if not clean:
            failures += 1

    report = {
        "run_id": run_id,
        "skill_id": SKILL_ID,
        "scanned": len(agents),
        "expected_env_keys": expected_keys,
        "expected_timeout_sec": EXPECTED_TIMEOUT_SEC,
        "expected_desired_skill": EXPECTED_DESIRED_SKILL,
        "failures": failures,
        "verdict": "pass" if failures == 0 else "fail",
        "agents": rows,
    }
    print(json.dumps(report, indent=2))
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
