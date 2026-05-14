#!/usr/bin/env python3
"""Provider health, agent assignment, and spend dashboard.

Polls provider usage APIs, reads agent model assignments from the
provider-monitor state file, and fetches Paperclip company metrics.
Generates a self-contained HTML dashboard page.

Usage:
    python scripts/provider_dashboard.py                    # write dashboard.html
    python scripts/provider_dashboard.py --output path.html # custom output path
    python scripts/provider_dashboard.py --serve             # serve via HTTP
    python scripts/provider_dashboard.py --serve --port 8765 # custom port
    python scripts/provider_dashboard.py --json              # print JSON data
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from scripts.provider_monitor import (
    MONITOR_STATE,
    PRO_AGENTS,
    STANDARD_AGENTS,
    PRO_MODEL_NORMAL,
    PRO_MODEL_DEGRADED,
    STANDARD_MODEL_NORMAL,
    STANDARD_MODEL_DEGRADED,
    UsageSnapshot,
    MonitorState,
    fetch_claude_usage,
    fetch_deepseek_balance,
    fetch_openrouter_credits,
    load_state,
    poll_all_providers,
)

API_TIMEOUT = 15
RETRY_STRATEGY = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    raise_on_status=False,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "dashboard.html"

MODEL_DISPLAY = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-sonnet-4-5": "Claude Sonnet 4.5",
    "openrouter/deepseek/deepseek-v4-pro": "DeepSeek V4 Pro (OR)",
    "openrouter/deepseek/deepseek-v4-flash": "DeepSeek V4 Flash (OR)",
}


def _paperclip_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {os.environ['PAPERCLIP_API_KEY']}",
        "Content-Type": "application/json",
    })
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _pc_base() -> str:
    return os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100")


def _pc_company() -> str:
    return os.environ["PAPERCLIP_COMPANY_ID"]


def fetch_dashboard() -> dict | None:
    try:
        with _paperclip_session() as sess:
            resp = sess.get(
                f"{_pc_base()}/api/companies/{_pc_company()}/dashboard",
                timeout=API_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"Dashboard API returned {resp.status_code}", file=sys.stderr)
            return None
    except requests.RequestException as e:
        print(f"Dashboard API request failed: {e}", file=sys.stderr)
        return None


def fetch_agents() -> list[dict] | None:
    try:
        with _paperclip_session() as sess:
            resp = sess.get(
                f"{_pc_base()}/api/companies/{_pc_company()}/agents",
                timeout=API_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"Agents API returned {resp.status_code}", file=sys.stderr)
            return None
    except requests.RequestException as e:
        print(f"Agents API request failed: {e}", file=sys.stderr)
        return None


def resolve_agent_models(state: MonitorState) -> dict[str, str]:
    pro = state.pro_model or PRO_MODEL_NORMAL
    std = state.standard_model or STANDARD_MODEL_NORMAL
    mapping: dict[str, str] = {}
    for name, _ in PRO_AGENTS:
        mapping[name] = pro
    for name, _ in STANDARD_AGENTS:
        mapping[name] = std
    return mapping


def collect_data() -> dict:
    snap = poll_all_providers()
    state = load_state()
    dashboard = fetch_dashboard()
    agents_raw = fetch_agents()
    agent_models = resolve_agent_models(state)

    return {
        "snapshot": snap,
        "state": state,
        "dashboard": dashboard,
        "agents_raw": agents_raw or [],
        "agent_models": agent_models,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── HTML generation ──────────────────────────────────────────────────────────


def _pct_class(pct: float | None) -> str:
    if pct is None:
        return "unknown"
    if pct >= 95:
        return "critical"
    if pct >= 80:
        return "warning"
    if pct <= 20:
        return "critical"
    if pct <= 40:
        return "warning"
    return "ok"


def _status_icon(available: bool) -> str:
    return "available" if available else "degraded"


def _render_provider_card(title: str, icon: str, rows: list[tuple[str, str, str]], error: str | None) -> str:
    rows_html = ""
    for label, value, cls_ in rows:
        rows_html += f'<div class="metric"><span class="label">{label}</span><span class="value {cls_}">{value}</span></div>\n'
    err_html = ""
    if error:
        err_html = f'<div class="card-error">{error}</div>'
    return f"""
    <div class="card">
        <h3>{icon} {title}</h3>
        {rows_html}
        {err_html}
    </div>"""


def _render_claude_card(snap: UsageSnapshot) -> str:
    rows: list[tuple[str, str, str]] = []
    if snap.claude_4hr_pct is not None:
        rows.append(("4-Hour Usage", f"{snap.claude_4hr_pct:.1f}%", _pct_class(snap.claude_4hr_pct)))
    else:
        rows.append(("4-Hour Usage", "Unknown", "unknown"))
    if snap.claude_7day_pct is not None:
        rows.append(("7-Day Usage", f"{snap.claude_7day_pct:.1f}%", _pct_class(snap.claude_7day_pct)))
    else:
        rows.append(("7-Day Usage", "Unknown", "unknown"))
    rows.append(("Availability", snap.claude_available and "Available" or "Degraded",
                 _status_icon(snap.claude_available)))
    return _render_provider_card("Claude Code Max", "\U0001F4BB", rows, snap.claude_error)


def _render_openrouter_card(snap: UsageSnapshot) -> str:
    rows: list[tuple[str, str, str]] = []
    if snap.openrouter_total is not None:
        rows.append(("Total Credits", f"${snap.openrouter_total:.2f}", "neutral"))
        rows.append(("Used", f"${snap.openrouter_used:.2f}", "neutral"))
        rows.append(("Remaining", f"${snap.openrouter_remaining:.2f}", _pct_class(100 - (snap.openrouter_pct_remaining or 100))))
    else:
        rows.append(("Credits", "Unknown", "unknown"))
    if snap.openrouter_pct_remaining is not None:
        rows.append(("Remaining %", f"{snap.openrouter_pct_remaining:.1f}%", _pct_class(100 - snap.openrouter_pct_remaining)))
    low_warning = snap.openrouter_remaining is not None and snap.openrouter_remaining <= 5.0
    if low_warning:
        rows.append(("Warning", "LOW CREDIT \u26a0\ufe0f", "critical"))
    return _render_provider_card("OpenRouter", "\U0001F310", rows, snap.openrouter_error)


def _render_deepseek_card(snap: UsageSnapshot) -> str:
    rows: list[tuple[str, str, str]] = []
    if snap.deepseek_balance_usd is not None:
        rows.append(("USD Balance", f"${snap.deepseek_balance_usd:.2f}", _pct_class(100 - (snap.deepseek_pct_remaining or 100))))
    else:
        rows.append(("USD Balance", "Unknown", "unknown"))
    if snap.deepseek_pct_remaining is not None:
        rows.append(("Remaining %", f"{snap.deepseek_pct_remaining:.1f}%", _pct_class(100 - snap.deepseek_pct_remaining)))
    return _render_provider_card("DeepSeek API", "\U0001F9E0", rows, snap.deepseek_error)


def _render_agent_map(agent_models: dict[str, str], agents_raw: list[dict]) -> str:
    agent_lookup = {a["name"]: a for a in agents_raw}

    groups: dict[str, list[dict]] = {}
    for name, model in agent_models.items():
        display = MODEL_DISPLAY.get(model, model)
        groups.setdefault(display, [])
        agent_info = agent_lookup.get(name, {})
        groups[display].append({
            "name": name,
            "status": agent_info.get("status", "unknown"),
            "budget": agent_info.get("budgetMonthlyCents", 0),
            "spent": agent_info.get("spentMonthlyCents", 0),
            "last_heartbeat": agent_info.get("lastHeartbeatAt"),
        })

    status_icons = {"running": "\u25b6", "idle": "\u23f8", "error": "\u26a0", "paused": "\u23f8\ufe0f"}

    html = '<div class="agent-groups">\n'
    for display_model, agents in sorted(groups.items()):
        running_count = sum(1 for a in agents if a["status"] == "running")
        html += f'<div class="agent-group"><h4>{display_model} <span class="badge">{len(agents)} agents, {running_count} running</span></h4>\n'
        html += '<div class="agent-grid">\n'
        for a in agents:
            icon = status_icons.get(a["status"], "?")
            spent_dollars = a["spent"] / 100
            budget_dollars = a["budget"] / 100
            hb = ""
            if a["last_heartbeat"]:
                try:
                    dt = datetime.fromisoformat(a["last_heartbeat"].replace("Z", "+00:00"))
                    delta = datetime.now(timezone.utc) - dt
                    mins = int(delta.total_seconds() / 60)
                    hb = f"{mins}m ago" if mins < 120 else f"{mins // 60}h ago"
                except (ValueError, TypeError):
                    hb = ""
            html += (
                f'<div class="agent-tile {a["status"]}">'
                f'<span class="agent-icon">{icon}</span>'
                f'<span class="agent-name">{a["name"]}</span>'
                f'<span class="agent-spend">${spent_dollars:.2f} / ${budget_dollars:.0f}</span>'
                f'<span class="agent-hb">{hb}</span>'
                f'</div>\n'
            )
        html += '</div></div>\n'
    html += '</div>\n'

    ungrouped = set(agent_models) - set(agent_models)
    if ungrouped:
        html += f'<div class="note">Ungrouped agents: {", ".join(sorted(ungrouped))}</div>\n'
    return html


def _render_spend(dashboard: dict | None, agent_models: dict[str, str], agents_raw: list[dict]) -> str:
    if not dashboard:
        return '<div class="card"><h3>\U0001f4b0 Spend / Usage</h3><div class="card-error">No dashboard data available</div></div>'

    costs = dashboard.get("costs", {})
    month_spend = costs.get("monthSpendCents", 0)
    month_budget = costs.get("monthBudgetCents", 0)
    utilization = costs.get("monthUtilizationPercent", 0)

    budget_dollars = month_budget / 100 if month_budget else None
    spend_dollars = month_spend / 100

    agent_counts = dashboard.get("agents", {})
    run_activity = dashboard.get("runActivity", [])

    rows = []
    rows.append((
        "Month-to-Date Spend",
        f"${spend_dollars:.2f}" + (f" of ${budget_dollars:.0f}" if budget_dollars else ""),
        "neutral"
    ))
    if month_budget:
        pct_spent = (month_spend / month_budget * 100) if month_budget else 0
        rows.append(("Budget Used", f"{pct_spent:.1f}%", _pct_class(pct_spent)))
    rows.append(("Active Agents", f"{agent_counts.get('active', 0)}", "neutral"))
    rows.append(("Running", f"{agent_counts.get('running', 0)}", "ok" if agent_counts.get('running', 0) > 0 else "unknown"))
    rows.append(("Paused", f"{agent_counts.get('paused', 0)}", "warning" if agent_counts.get('paused', 0) > 0 else "ok"))
    rows.append(("Error", f"{agent_counts.get('error', 0)}", "critical" if agent_counts.get('error', 0) > 0 else "ok"))

    rows_html = ""
    for label, value, cls_ in rows:
        rows_html += f'<div class="metric"><span class="label">{label}</span><span class="value {cls_}">{value}</span></div>\n'

    total_runs = sum(d.get("total", 0) for d in run_activity)
    total_succeeded = sum(d.get("succeeded", 0) for d in run_activity)
    total_failed = sum(d.get("failed", 0) for d in run_activity)

    chart_labels = json.dumps([d["date"][-5:] for d in run_activity[-14:]])
    chart_succeeded = json.dumps([d.get("succeeded", 0) for d in run_activity[-14:]])
    chart_failed = json.dumps([d.get("failed", 0) for d in run_activity[-14:]])

    chart_html = f"""
    <div class="run-activity">
        <h5>Run Activity (14-day)</h5>
        <div class="run-stats">
            <span>Total: {total_runs}</span>
            <span class="ok">Succeeded: {total_succeeded}</span>
            <span class="critical">Failed: {total_failed}</span>
        </div>
        <div class="bar-chart" id="run-chart"></div>
    </div>
    <script>
    (function() {{
        var container = document.getElementById('run-chart');
        var labels = {chart_labels};
        var succeeded = {chart_succeeded};
        var failed = {chart_failed};
        var maxVal = Math.max.apply(null, succeeded.map(function(s,i) {{ return s + (failed[i]||0); }})) || 1;
        var html = '';
        for (var i = 0; i < labels.length; i++) {{
            var s = succeeded[i] || 0;
            var f = failed[i] || 0;
            var sPct = (s / maxVal * 100).toFixed(1);
            var fPct = (f / maxVal * 100).toFixed(1);
            html += '<div class="bar-row">'
                + '<span class="bar-label">' + labels[i] + '</span>'
                + '<div class="bar-track">'
                + '<div class="bar bar-succeeded" style="width:' + sPct + '%" title="' + s + ' succeeded"></div>'
                + '<div class="bar bar-failed" style="width:' + fPct + '%" title="' + f + ' failed"></div>'
                + '</div>'
                + '<span class="bar-val">' + (s+f) + '</span>'
                + '</div>';
        }}
        container.innerHTML = html;
    }})();
    </script>
    """

    return f"""
    <div class="card">
        <h3>\U0001f4b0 Spend / Usage</h3>
        {rows_html}
        {chart_html}
    </div>"""


def _generate_html(data: dict) -> str:
    snap = data["snapshot"]
    state = data["state"]
    dashboard = data["dashboard"]
    agents_raw = data["agents_raw"]
    agent_models = data["agent_models"]
    generated_at = data["generated_at"]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BTC Trade Engine &mdash; Provider &amp; Agent Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, 'Segoe UI', system-ui, sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    min-height: 100vh;
}}
.header {{
    background: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 20px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.header h1 {{ font-size: 1.5rem; font-weight: 600; color: #58a6ff; }}
.header .ts {{ font-size: 0.8rem; color: #8b949e; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}
.provider-section {{ margin-bottom: 32px; }}
.section-title {{
    font-size: 1.1rem;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}}
.provider-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
}}
.card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
}}
.card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 12px; color: #e6edf3; }}
.card h4 {{ font-size: 0.9rem; font-weight: 600; margin-bottom: 8px; color: #8b949e; }}
.card h5 {{ font-size: 0.85rem; font-weight: 600; margin: 12px 0 8px; color: #8b949e; }}
.card-error {{ color: #f85149; font-size: 0.8rem; margin-top: 8px; padding: 6px 8px; background: #1d1115; border-radius: 4px; }}
.metric {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #21262d;
}}
.metric:last-child {{ border-bottom: none; }}
.metric .label {{ font-size: 0.85rem; color: #8b949e; }}
.metric .value {{ font-size: 0.9rem; font-weight: 500; font-variant-numeric: tabular-nums; }}
.value.ok {{ color: #3fb950; }}
.value.warning {{ color: #d29922; }}
.value.critical {{ color: #f85149; }}
.value.neutral {{ color: #c9d1d9; }}
.value.unknown {{ color: #6e7681; }}
.value.available {{ color: #3fb950; }}
.value.degraded {{ color: #f85149; }}

.agent-groups {{ margin-top: 8px; }}
.agent-group {{ margin-bottom: 20px; }}
.agent-group h4 {{ font-size: 0.9rem; font-weight: 600; color: #e6edf3; margin-bottom: 10px; }}
.badge {{ font-size: 0.75rem; color: #8b949e; font-weight: 400; }}
.agent-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
}}
.agent-tile {{
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.8rem;
}}
.agent-tile.running {{ border-color: #3fb950; }}
.agent-tile.idle {{ border-color: #30363d; }}
.agent-tile.error {{ border-color: #f85149; }}
.agent-tile.paused {{ border-color: #d29922; }}
.agent-icon {{ font-size: 0.7rem; margin-right: 4px; }}
.agent-name {{ font-weight: 600; color: #e6edf3; }}
.agent-spend {{ color: #8b949e; font-size: 0.75rem; }}
.agent-hb {{ color: #6e7681; font-size: 0.7rem; }}

.run-activity {{ margin-top: 12px; }}
.run-stats {{
    display: flex;
    gap: 16px;
    font-size: 0.8rem;
    color: #8b949e;
    margin-bottom: 10px;
}}
.run-stats .ok {{ color: #3fb950; }}
.run-stats .critical {{ color: #f85149; }}
.bar-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    font-size: 0.72rem;
}}
.bar-label {{ width: 38px; flex-shrink: 0; color: #6e7681; text-align: right; }}
.bar-track {{
    flex: 1;
    height: 14px;
    background: #0d1117;
    border-radius: 3px;
    overflow: hidden;
    display: flex;
}}
.bar {{
    height: 100%;
    transition: width 0.3s;
}}
.bar-succeeded {{ background: #3fb950; }}
.bar-failed {{ background: #f85149; }}
.bar-val {{ width: 28px; flex-shrink: 0; color: #8b949e; }}

.state-info {{
    font-size: 0.75rem;
    color: #6e7681;
    margin-top: 20px;
    padding: 10px 12px;
    background: #0d1117;
    border-radius: 4px;
    border: 1px solid #21262d;
}}
.state-info span {{ margin-right: 16px; }}

.footer {{
    text-align: center;
    padding: 16px;
    color: #484f58;
    font-size: 0.7rem;
    border-top: 1px solid #21262d;
}}

@media (max-width: 768px) {{
    .container {{ padding: 12px; }}
    .provider-grid {{ grid-template-columns: 1fr; }}
    .agent-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>BTC Trade Engine &mdash; Dashboard</h1>
    <span class="ts">Generated: {ts}</span>
</div>
<div class="container">

<div class="provider-section">
    <div class="section-title">Provider Health</div>
    <div class="provider-grid">
        {_render_claude_card(snap)}
        {_render_openrouter_card(snap)}
        {_render_deepseek_card(snap)}
    </div>
</div>

<div class="provider-section">
    <div class="section-title">Agent Assignments</div>
    {_render_agent_map(agent_models, agents_raw)}
</div>

<div class="provider-section">
    <div class="section-title">Spend &amp; Activity</div>
    <div class="provider-grid">
        {_render_spend(dashboard, agent_models, agents_raw)}
    </div>
</div>

<div class="state-info">
    Provider State: <strong>{state.current_provider_state}</strong>
    <span>| Pro Model: <strong>{state.pro_model or PRO_MODEL_NORMAL}</strong></span>
    <span>| Standard Model: <strong>{state.standard_model or STANDARD_MODEL_NORMAL}</strong></span>
    <span>| Last Switch: <strong>{state.last_switch_at or "never"}</strong></span>
    <span>| Checks in State: <strong>{len(state.checks)}</strong></span>
</div>

</div>
<div class="footer">
    BTC Trade Engine Dashboard &mdash; Auto-refresh disabled (static snapshot)
</div>
</body>
</html>"""


# ── HTTP server ──────────────────────────────────────────────────────────────


class _SingleFileHandler(SimpleHTTPRequestHandler):
    html_content: bytes = b""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.html_content)))
        self.end_headers()
        self.wfile.write(self.html_content)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def serve_html(html: str, port: int) -> None:
    _SingleFileHandler.html_content = html.encode("utf-8")
    server = HTTPServer(("0.0.0.0", port), _SingleFileHandler)
    print(f"Serving dashboard at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provider health, agent assignment, and spend dashboard"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"Output HTML file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--serve", action="store_true", help="Serve via HTTP instead of writing a file")
    parser.add_argument("--port", type=int, default=8765, help="HTTP server port (default: 8765)")
    parser.add_argument("--json", action="store_true", help="Print JSON data and exit")
    args = parser.parse_args()

    print("Collecting data...", file=sys.stderr)
    data = collect_data()

    if args.json:
        serializable = {
            "generated_at": data["generated_at"],
            "snapshot": data["snapshot"].to_dict(),
            "state": data["state"].to_dict(),
            "agent_models": data["agent_models"],
            "dashboard": data["dashboard"],
        }
        print(json.dumps(serializable, indent=2, default=str))
        return

    print("Generating HTML...", file=sys.stderr)
    html = _generate_html(data)

    if args.serve:
        serve_html(html, args.port)
    else:
        out_path = Path(args.output)
        out_path.write_text(html)
        print(f"Dashboard written to {out_path.resolve()}", file=sys.stderr)
        print(f"Open with: file://{out_path.resolve()}", file=sys.stderr)
        print(f"Or serve:   python scripts/provider_dashboard.py --serve", file=sys.stderr)


if __name__ == "__main__":
    main()
