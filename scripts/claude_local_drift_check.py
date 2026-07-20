#!/usr/bin/env python3
"""
claude_local adapterConfig drift detector (CTO-owned daily routine).

Compares every claude_local agent's effective adapterConfig against the canonical
env block from the company skill `claude-local-config-template`
(id: a2bab736-d451-4a5a-82e2-30e49a984907), plus adapterConfig.timeoutSec=3800.

Modes:
  --mode check   (default) Report only.
  --mode open    Report AND open one medium-priority incident per drifted agent
                 under BTCAAAAA-39905 (umbrella), assigned to CEO. Post one
                 summary comment on the umbrella.

Outputs structured JSON to stdout for piping.

Owner umbrella: BTCAAAAA-39905
Routine issue : BTCAAAAA-39915 (this daily execution)
Detector spec : BTCAAAAA-39911
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

SKILL_ID = "a2bab736-d451-4a5a-82e2-30e49a984907"
UMBRELLA_ID = "b1a43d5f-1a00-433c-b501-f170d16c1539"
GOAL_ID = "571cd69e-0fc2-4b78-a828-7502777038b1"
CEO_AGENT_ID = "73e7ef43-1337-47f8-9cf2-8db91ebcf555"
EXPECTED_TIMEOUT_SEC = 3800
EXPECTED_KEYS = [
    "ANTHROPIC_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_TIMEOUT_MS",
    "ANTHROPIC_SMALL_FAST_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
]


def _api_url(path):
    base = os.environ["PAPERCLIP_API_URL"].rstrip("/")
    return f"{base}{path}"


def _request(method, path, body=None, *, run_id=None):
    headers = {
        "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
        "Content-Type": "application/json",
    }
    if run_id:
        headers["X-Paperclip-Run-Id"] = run_id
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
    company_id = os.environ["PAPERCLIP_COMPANY_ID"]
    out = _request("GET", f"/api/companies/{company_id}/agents")
    if not isinstance(out, list):
        raise RuntimeError(f"Unexpected agent list response shape: {type(out).__name__}")
    return [a for a in out if a.get("adapterType") == "claude_local"]


def fetch_agent(agent_id):
    return _request("GET", f"/api/agents/{agent_id}")


def assert_configuration_access(agent_id):
    try:
        _request("GET", f"/api/agents/{agent_id}/configuration")
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "Drift detector cannot read agent configurations; "
                "grant configuration-read access or run it as an authorized agent"
            ) from exc
        raise


def _unwrap(env_value):
    if isinstance(env_value, dict):
        return env_value.get("value")
    return env_value


def compare_agent(actual_env, expected_env):
    missing, mismatched, unexpected = [], [], []
    actual = actual_env or {}
    for key in EXPECTED_KEYS:
        if key not in actual:
            missing.append(key)
            continue
        actual_value = _unwrap(actual[key])
        expected_value = _unwrap(expected_env[key])
        if str(actual_value) != str(expected_value):
            mismatched.append({
                "key": key,
                "actual": actual_value,
                "expected": expected_value,
            })
    for key in actual.keys():
        if key not in EXPECTED_KEYS:
            unexpected.append(key)
    return missing, mismatched, unexpected


def compare_timeout(actual_timeout):
    if actual_timeout is None:
        return {"matches": False, "actual": None, "expected": EXPECTED_TIMEOUT_SEC}
    return {
        "matches": int(actual_timeout) == EXPECTED_TIMEOUT_SEC,
        "actual": actual_timeout,
        "expected": EXPECTED_TIMEOUT_SEC,
    }


def open_incident(agent, drift, run_id):
    summary_lines = [
        f"## claude_local drift detected: {agent['name']}",
        "",
        f"- Agent: {agent['name']} (`{agent['id']}`)",
        f"- adapterType: {agent.get('adapterType')}",
        f"- Detected by run: `{run_id}`",
        "",
        "### Drift details",
        "",
    ]
    if drift["missing_keys"]:
        summary_lines.append(
            f"- **Missing keys** ({len(drift['missing_keys'])}): "
            f"{', '.join(drift['missing_keys'])}"
        )
    if drift["mismatched"]:
        lines = [
            f"  - `{m['key']}`: actual=`{m['actual']}` expected=`{m['expected']}`"
            for m in drift["mismatched"]
        ]
        summary_lines.append(f"- **Mismatched values** ({len(drift['mismatched'])}):")
        summary_lines.extend(lines)
    if drift["unexpected_keys"]:
        summary_lines.append(
            f"- **Unexpected keys**: {', '.join(drift['unexpected_keys'])}"
        )
    if drift["timeout"] and not drift["timeout"]["matches"]:
        summary_lines.append(
            f"- **timeoutSec**: actual=`{drift['timeout']['actual']}` "
            f"expected=`{drift['timeout']['expected']}`"
        )
    summary_lines.extend([
        "",
        "### Recovery",
        "",
        f"Re-sync canonical block from skill `{SKILL_ID}` to `{agent['id']}` and "
        "re-apply adapterConfig.env with the verbatim env block + "
        "`timeoutSec: 3800`. Reference: "
        "[BTCAAAAA-39905](/BTCAAAAA/issues/BTCAAAAA-39905) (umbrella) and "
        f"[skill {SKILL_ID}](/BTCAAAAA/skills/{SKILL_ID}).",
        "",
        "### Regression-prevention evidence chain",
        "",
        "- [BTCAAAAA-27163](/BTCAAAAA/issues/BTCAAAAA-27163), "
        "[BTCAAAAA-27164](/BTCAAAAA/issues/BTCAAAAA-27164), "
        "[BTCAAAAA-27165](/BTCAAAAA/issues/BTCAAAAA-27165) — earlier PM env-reset cascade",
        "- [BTCAAAAA-27356](/BTCAAAAA/issues/BTCAAAAA-27356), "
        "[BTCAAAAA-27357](/BTCAAAAA/issues/BTCAAAAA-27357) — ANTHROPIC_BASE_URL drift",
        "- [BTCAAAAA-39896](/BTCAAAAA/issues/BTCAAAAA-39896) — PEM + DevelopmentManager 4-day down",
        "- [BTCAAAAA-39899](/BTCAAAAA/issues/BTCAAAAA-39899) — CEO manual PATCH recovery",
        "",
        "Detect-and-triage: [BTCAAAAA-39911](/BTCAAAAA/issues/BTCAAAAA-39911), "
        f"[BTCAAAAA-39915](/BTCAAAAA/issues/BTCAAAAA-39915) (run `{run_id}`)",
    ])
    description = "\n".join(summary_lines)

    payload = {
        "title": f"claude_local drift detected: {agent['name']}",
        "description": description,
        "priority": "medium",
        "status": "todo",
        "parentId": UMBRELLA_ID,
        "goalId": GOAL_ID,
        "assigneeAgentId": CEO_AGENT_ID,
        "billingCode": "platform-fleet",
    }
    return _request(
        "POST",
        f"/api/companies/{os.environ['PAPERCLIP_COMPANY_ID']}/issues",
        payload,
        run_id=run_id,
    )


def post_summary_comment(drifted, run_id):
    if not drifted:
        body = (
            f"## claude_local drift check — clean run\n\n"
            f"- Run: `{run_id}`\n- Drifted agents: 0\n"
        )
    else:
        lines = [
            "## claude_local drift check — drift detected",
            "",
            f"- Run: `{run_id}`",
            f"- Drifted agents: {len(drifted)}",
            "",
            "| Agent | Missing | Mismatched | Unexpected | timeoutSec | Incident |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for d in drifted:
            missing = len(d["drift"]["missing_keys"])
            mismatched = len(d["drift"]["mismatched"])
            unexpected = len(d["drift"]["unexpected_keys"])
            t = d["drift"]["timeout"]
            t_match = "✓" if t and t["matches"] else f"`{t['actual'] if t else 'n/a'}`"
            inc_id = d.get("incident_id", "—")
            if isinstance(inc_id, str) and inc_id.startswith("ERROR"):
                inc_link = inc_id
            else:
                inc_link = f"[{inc_id}](/BTCAAAAA/issues/{inc_id})"
            lines.append(
                f"| {d['name']} | {missing} | {mismatched} | {unexpected} | "
                f"{t_match} | {inc_link} |"
            )
        lines.extend([
            "",
            "Each drifted agent has a medium-priority incident under this umbrella, "
            "assigned to CEO. Reference skill: "
            f"[claude-local-config-template](/BTCAAAAA/skills/{SKILL_ID}).",
        ])
        body = "\n".join(lines)
    return _request(
        "POST",
        f"/api/issues/{UMBRELLA_ID}/comments",
        {"body": body},
        run_id=run_id,
    )


def main():
    p = argparse.ArgumentParser(description="claude_local adapterConfig drift detector")
    p.add_argument("--mode", choices=["check", "open"], default="check")
    p.add_argument("--company-id", default=os.environ.get("PAPERCLIP_COMPANY_ID"))
    p.add_argument("--skill-id", default=SKILL_ID)
    args = p.parse_args()

    if not args.company_id:
        sys.exit("PAPERCLIP_COMPANY_ID env var required")
    os.environ["PAPERCLIP_COMPANY_ID"] = args.company_id
    for key in ("PAPERCLIP_API_KEY", "PAPERCLIP_API_URL"):
        if not os.environ.get(key):
            sys.exit(f"{key} env var required")
    run_id = os.environ.get("PAPERCLIP_RUN_ID", "no-run-id")

    print(f"[drift-check] loading canonical env block from skill {args.skill_id}", file=sys.stderr)
    expected_env = load_canonical_env()

    print("[drift-check] listing claude_local agents", file=sys.stderr)
    agents = list_claude_local_agents()
    print(f"[drift-check] {len(agents)} claude_local agents", file=sys.stderr)

    probe_agent = next(
        (agent for agent in agents if agent["id"] != os.environ.get("PAPERCLIP_AGENT_ID")),
        None,
    )
    if probe_agent:
        assert_configuration_access(probe_agent["id"])

    drifted, clean = [], []
    for a in agents:
        full = fetch_agent(a["id"])
        cfg = full.get("adapterConfig") or {}
        env = cfg.get("env") or {}
        missing, mismatched, unexpected = compare_agent(env, expected_env)
        timeout = compare_timeout(cfg.get("timeoutSec"))
        record = {
            "id": a["id"],
            "name": a.get("name", a["id"]),
            "urlKey": a.get("urlKey"),
            "drift": {
                "missing_keys": missing,
                "mismatched": mismatched,
                "unexpected_keys": unexpected,
                "timeout": timeout,
            },
        }
        if missing or mismatched or unexpected or not timeout["matches"]:
            drifted.append(record)
        else:
            clean.append({"id": a["id"], "name": record["name"]})

    report = {
        "run_id": run_id,
        "mode": args.mode,
        "skill_id": args.skill_id,
        "umbrella_id": UMBRELLA_ID,
        "scanned": len(agents),
        "drifted_count": len(drifted),
        "clean_count": len(clean),
        "drifted": drifted,
        "clean": clean,
    }

    if args.mode == "open":
        for record in drifted:
            try:
                inc = open_incident(
                    {"id": record["id"], "name": record["name"]},
                    record["drift"],
                    run_id,
                )
                record["incident_id"] = inc.get("identifier", inc.get("id", "ERROR"))
            except Exception as e:
                record["incident_id"] = f"ERROR:{e}"
        post_summary_comment(drifted, run_id)
        report["drifted"] = drifted

    print(json.dumps(report, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
