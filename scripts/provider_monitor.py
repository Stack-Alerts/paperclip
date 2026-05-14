#!/usr/bin/env python3
"""Provider usage monitor and agent model switching automation.

Polls DeepSeek, OpenRouter, and Claude Code Max usage/billing APIs,
company budget data from Paperclip dashboard, evaluates switching triggers,
and patches agent adapter config models via the Paperclip API. Implements
hysteresis to prevent thrashing.

Switching triggers (priority order):
  1. Claude rate-limit exhaust (4hr >=95%, 7day >=95%) — MUST switch
  2. Budget critical (>=95% monthly budget spent) — degrade all to cheapest
  3. Budget warning (>=90% monthly budget spent) — degrade standard tier
  4. Budget caution (>=80% monthly budget spent) — alert only
  5. Claude recovery — restore normal models

Usage:
    python scripts/provider_monitor.py                # live run
    python scripts/provider_monitor.py --dry-run      # log only, no API patches
    python scripts/provider_monitor.py --json-summary # print JSON summary and exit
    python scripts/provider_monitor.py --no-switch    # poll and alert, skip agent patches
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

MONITOR_LOG = Path.home() / ".paperclip" / "provider_monitor.log"
MONITOR_STATE = Path.home() / ".paperclip" / "provider_monitor_state.json"
MAX_LOG_BYTES = 1 * 1024 * 1024

API_TIMEOUT = 15
RETRY_STRATEGY = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=["GET", "PATCH", "POST"],
    raise_on_status=False,
)

ANTHROPIC_USAGE_BASE = "https://api.anthropic.com"
DEEPSEEK_BALANCE_URL = "https://api.deepseek.com/user/balance"
OPENROUTER_CREDITS_URL = "https://openrouter.ai/api/v1/credits"

ALERT_ISSUE_ID = "0f1b072b-c5a3-4bec-a3c3-3c5e28b0ba07"
CTO_AGENT_ID = "41b5ede6-e209-40ba-b923-dc969c722e6d"

DEGRADE_COOLDOWN_MIN = 30
UPGRADE_COOLDOWN_MIN = 15

# Budget-driven switching thresholds (% of monthly budget spent)
BUDGET_ALERT_PCT = 80
BUDGET_DEGRADE_STANDARD_PCT = 90
BUDGET_DEGRADE_ALL_PCT = 95
BUDGET_RECOVER_PCT = 70
BUDGET_DEGRADE_COOLDOWN_MIN = 60
BUDGET_UPGRADE_COOLDOWN_MIN = 30

MONITOR_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(MONITOR_LOG),
        logging.StreamHandler() if os.isatty(0) else logging.NullHandler(),
    ],
)
logger = logging.getLogger("provider_monitor")

PRO_AGENTS = [
    ("CEO", "73e7ef43-1337-47f8-9cf2-8db91ebcf555"),
    ("CTO", "41b5ede6-e209-40ba-b923-dc969c722e6d"),
    ("Architect", "73eaab54-0d5f-4a5c-a9f9-0019064ee418"),
    ("AutomationEngineer", "2b9152a6-07f6-4ae9-87fa-c824012c9ff6"),
    ("PlatformEngineer", "58cd0e89-a143-4102-98aa-45a412a70248"),
    ("DevelopmentManager", "270cc7ed-d6cd-4df6-ab50-abf7c0e8ea15"),
    ("SecurityAnalyst", "840eb9ff-f746-47da-9fdc-f0ec9d071155"),
    ("NautilusEngineer", "a472d315-3e2e-4c3b-a1ba-a931295628cc"),
]

STANDARD_AGENTS = [
    ("LinuxSpecialist", "a1d7dba5-6b71-4fff-86cb-8ee1734a35c5"),
    ("RiskAnalyst", "24041495-386b-4be7-ae8b-7fc0c0ed5c9d"),
    ("BacktestAnalyst", "79beb038-0309-4e15-95c8-d310455dfb0e"),
    ("GeneralResearcher", "df7b4035-e034-467e-af06-d25c869c810f"),
    ("UIEngineer", "9113b321-771b-481d-8ae7-33765ed9b1f5"),
    ("DocWriter", "5ed47769-f44e-48f6-a6d6-630479b230bf"),
    ("StrategyResearcher", "e3fcab65-c9a3-45bd-97e8-5145d3d6db5e"),
    ("PlatformEngineeringManager", "0a0cdb2a-80fe-46e9-b238-74ed993713c0"),
    ("IntelAnalyst", "05c8ae3b-18cb-4afd-9750-0d88b41dec7f"),
    ("DataEngineer", "000f41e8-8514-4100-94f7-93ea4b9876af"),
    ("TestManager", "d53906e4-5660-4a47-bef4-148a69979b20"),
    ("QAEngineer", "7be86124-a201-41be-82c6-6f4de9efe90e"),
    ("DatabaseAdministrator", "f680b3fd-945b-4e0b-ae42-1f9639a4cbd3"),
    ("ProductStrategist", "6c096a34-3e7e-4529-b851-1f7353f476d2"),
    ("RepoSteward", "f2fb75fd-a40d-4ee9-a7d0-6920808d2c4c"),
]

PRO_MODEL_NORMAL = "claude-sonnet-4-6"
PRO_MODEL_DEGRADED = "openrouter/deepseek/deepseek-v4-pro"
STANDARD_MODEL_NORMAL = "openrouter/deepseek/deepseek-v4-pro"
STANDARD_MODEL_DEGRADED = "openrouter/deepseek/deepseek-v4-flash"


@dataclass
class UsageSnapshot:
    deepseek_balance_usd: float | None = None
    deepseek_pct_remaining: float | None = None
    openrouter_total: float | None = None
    openrouter_used: float | None = None
    openrouter_remaining: float | None = None
    openrouter_pct_remaining: float | None = None
    claude_4hr_pct: float | None = None
    claude_7day_pct: float | None = None
    claude_available: bool = False
    claude_error: str | None = None
    deepseek_error: str | None = None
    openrouter_error: str | None = None
    month_spend_cents: int | None = None
    month_budget_cents: int | None = None
    budget_pct: float | None = None
    dashboard_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "deepseek_balance_usd": self.deepseek_balance_usd,
            "deepseek_pct_remaining": self.deepseek_pct_remaining,
            "openrouter_total": self.openrouter_total,
            "openrouter_used": self.openrouter_used,
            "openrouter_remaining": self.openrouter_remaining,
            "openrouter_pct_remaining": self.openrouter_pct_remaining,
            "claude_4hr_pct": self.claude_4hr_pct,
            "claude_7day_pct": self.claude_7day_pct,
            "claude_available": self.claude_available,
            "claude_error": self.claude_error,
            "deepseek_error": self.deepseek_error,
            "openrouter_error": self.openrouter_error,
            "month_spend_cents": self.month_spend_cents,
            "month_budget_cents": self.month_budget_cents,
            "budget_pct": self.budget_pct,
            "dashboard_error": self.dashboard_error,
        }



@dataclass
class BudgetSnapshot:
    month_spend_cents: int | None = None
    month_budget_cents: int | None = None
    budget_pct: float | None = None
    dashboard_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "month_spend_cents": self.month_spend_cents,
            "month_budget_cents": self.month_budget_cents,
            "budget_pct": self.budget_pct,
            "dashboard_error": self.dashboard_error,
        }


@dataclass
class MonitorState:
    last_switch_at: str | None = None
    last_switch_direction: str | None = None
    current_provider_state: str = "unknown"
    pro_model: str | None = None
    standard_model: str | None = None
    alert_sent_d2: bool = False
    budget_degraded_level: str | None = None
    last_budget_switch_at: str | None = None
    budget_alert_sent: bool = False
    checks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "last_switch_at": self.last_switch_at,
            "last_switch_direction": self.last_switch_direction,
            "current_provider_state": self.current_provider_state,
            "pro_model": self.pro_model,
            "standard_model": self.standard_model,
            "alert_sent_d2": self.alert_sent_d2,
            "budget_degraded_level": self.budget_degraded_level,
            "last_budget_switch_at": self.last_budget_switch_at,
            "budget_alert_sent": self.budget_alert_sent,
            "checks": self.checks[-50:],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MonitorState":
        return cls(
            last_switch_at=d.get("last_switch_at"),
            last_switch_direction=d.get("last_switch_direction"),
            current_provider_state=d.get("current_provider_state", "unknown"),
            pro_model=d.get("pro_model"),
            standard_model=d.get("standard_model"),
            alert_sent_d2=d.get("alert_sent_d2", False),
            budget_degraded_level=d.get("budget_degraded_level"),
            last_budget_switch_at=d.get("last_budget_switch_at"),
            budget_alert_sent=d.get("budget_alert_sent", False),
            checks=d.get("checks", []),
        )


def _rotate_log_if_needed() -> None:
    if MONITOR_LOG.exists() and MONITOR_LOG.stat().st_size > MAX_LOG_BYTES:
        bak = MONITOR_LOG.with_suffix(".log.1")
        bak.write_text(MONITOR_LOG.read_text())
        MONITOR_LOG.write_text("")
        logger.info("Rotated monitor log (size exceeded %d bytes)", MAX_LOG_BYTES)


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


def load_state() -> MonitorState:
    if MONITOR_STATE.exists():
        try:
            return MonitorState.from_dict(json.loads(MONITOR_STATE.read_text()))
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt state file, starting fresh")
    return MonitorState()


def save_state(state: MonitorState) -> None:
    MONITOR_STATE.write_text(json.dumps(state.to_dict(), indent=2))


# ── Provider polling ──────────────────────────────────────────────────────────


def fetch_deepseek_balance() -> tuple[float | None, float | None, str | None]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None, None, "DEEPSEEK_API_KEY not set"
    try:
        resp = requests.get(
            DEEPSEEK_BALANCE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=API_TIMEOUT,
        )
        if resp.status_code != 200:
            return None, None, f"DeepSeek API returned {resp.status_code}"
        data = resp.json()
        if not data.get("is_available"):
            return None, None, "DeepSeek API reports unavailable"
        balances = data.get("balance_infos", [])
        usd_balance = None
        topped_up = None
        for b in balances:
            if b.get("currency") == "USD":
                usd_balance = float(b.get("total_balance", 0))
                topped_up = float(b.get("topped_up_balance", 0))
                break
        if usd_balance is None:
            return None, None, "No USD balance found in DeepSeek response"
        pct = compute_deepseek_pct(usd_balance, topped_up)
        return usd_balance, pct, None
    except requests.RequestException as e:
        return None, None, f"DeepSeek API request failed: {e}"
    except (ValueError, KeyError, TypeError) as e:
        return None, None, f"DeepSeek API parse error: {e}"


def compute_deepseek_pct(balance_usd: float, topped_up: float | None = None) -> float:
    if balance_usd <= 0:
        return 0.0
    if topped_up and topped_up > 0:
        return round((balance_usd / topped_up) * 100.0, 1)
    if balance_usd >= 50.0:
        return 100.0
    return round((balance_usd / 50.0) * 100.0, 1)


def fetch_openrouter_credits() -> tuple[float | None, float | None, float | None, str | None]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return None, None, None, "OPENROUTER_API_KEY not set"
    try:
        resp = requests.get(
            OPENROUTER_CREDITS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=API_TIMEOUT,
        )
        if resp.status_code != 200:
            return None, None, None, f"OpenRouter API returned {resp.status_code}"
        data = resp.json().get("data", {})
        total = float(data.get("total_credits", 0))
        used = float(data.get("total_usage", 0))
        remaining = max(total - used, 0.0)
        pct = round((remaining / total * 100.0), 1) if total > 0 else 0.0
        return total, used, remaining, None
    except requests.RequestException as e:
        return None, None, None, f"OpenRouter API request failed: {e}"
    except (ValueError, KeyError, TypeError) as e:
        return None, None, None, f"OpenRouter API parse error: {e}"


def fetch_claude_usage() -> tuple[float | None, float | None, bool, str | None]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None, None, False, "ANTHROPIC_API_KEY not set — Claude usage unavailable"
    try:
        url = f"{ANTHROPIC_USAGE_BASE}/v1/usage?workspace_id={os.environ.get('ANTHROPIC_WORKSPACE_ID', '')}"
        resp = requests.get(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=API_TIMEOUT,
        )
        if resp.status_code == 404:
            return None, None, False, "Anthropic usage endpoint not available (404)"
        if resp.status_code != 200:
            return None, None, False, f"Anthropic usage API returned {resp.status_code}"
        data = resp.json()
        limits = data.get("usage_limits", {})
        tokens_4hr = limits.get("tokens_per_4_hours", {})
        tokens_7day = limits.get("tokens_per_7_days", {})
        used_4h = float(tokens_4hr.get("used", 0))
        limit_4h = float(tokens_4hr.get("limit", 1))
        used_7d = float(tokens_7day.get("used", 0))
        limit_7d = float(tokens_7day.get("limit", 1))
        pct_4h = round((used_4h / limit_4h * 100.0), 1) if limit_4h > 0 else 0.0
        pct_7d = round((used_7d / limit_7d * 100.0), 1) if limit_7d > 0 else 0.0
        available = pct_4h < 95.0 and pct_7d < 95.0
        return pct_4h, pct_7d, available, None
    except requests.RequestException as e:
        return None, None, False, f"Anthropic usage API request failed: {e}"
    except (ValueError, KeyError, TypeError) as e:
        return None, None, False, f"Anthropic usage API parse error: {e}"


def fetch_budget_data() -> tuple[int | None, int | None, float | None, str | None]:
    """Poll Paperclip company dashboard for monthly spend and budget."""
    try:
        with _paperclip_session() as sess:
            resp = sess.get(
                f"{_pc_base()}/api/companies/{_pc_company()}/dashboard",
                timeout=API_TIMEOUT,
            )
            if resp.status_code != 200:
                return None, None, None, f"Dashboard API returned {resp.status_code}"
            data = resp.json()
            costs = data.get("costs", {})
            month_spend = costs.get("monthSpendCents")
            month_budget = costs.get("monthBudgetCents")
            if month_spend is None:
                return None, None, None, "Dashboard response missing monthSpendCents"
            pct = None
            if month_budget and month_budget > 0:
                pct = round((month_spend / month_budget) * 100.0, 1)
            return month_spend, month_budget, pct, None
    except requests.RequestException as e:
        return None, None, None, f"Dashboard API request failed: {e}"
    except (ValueError, KeyError, TypeError) as e:
        return None, None, None, f"Dashboard API parse error: {e}"


def poll_all_providers() -> UsageSnapshot:
    snap = UsageSnapshot()

    ds_balance, ds_pct, ds_err = fetch_deepseek_balance()
    snap.deepseek_balance_usd = ds_balance
    snap.deepseek_pct_remaining = ds_pct
    snap.deepseek_error = ds_err
    if ds_err:
        logger.warning("DeepSeek: %s", ds_err)
    else:
        logger.info("DeepSeek: $%.2f (%.1f%%)", ds_balance, ds_pct)

    or_total, or_used, or_remaining, or_err = fetch_openrouter_credits()
    snap.openrouter_total = or_total
    snap.openrouter_used = or_used
    snap.openrouter_remaining = or_remaining
    snap.openrouter_error = or_err
    if or_err:
        logger.warning("OpenRouter: %s", or_err)
    else:
        or_pct = round((or_remaining / or_total * 100.0), 1) if or_total and or_total > 0 else 0.0
        snap.openrouter_pct_remaining = or_pct
        logger.info("OpenRouter: %.1f credits remaining (%.1f%%)", or_remaining, or_pct)

    c4, c7, c_avail, c_err = fetch_claude_usage()
    snap.claude_4hr_pct = c4
    snap.claude_7day_pct = c7
    snap.claude_available = c_avail
    snap.claude_error = c_err
    if c_err:
        logger.info("Claude: %s", c_err)
    else:
        logger.info("Claude: 4hr=%.1f%% 7day=%.1f%% available=%s", c4, c7, c_avail)

    spend, budget, pct, b_err = fetch_budget_data()
    snap.month_spend_cents = spend
    snap.month_budget_cents = budget
    snap.budget_pct = pct
    snap.dashboard_error = b_err
    if b_err:
        logger.warning("Budget: %s", b_err)
    else:
        budget_dollars = budget / 100 if budget else 0
        spend_dollars = spend / 100 if spend else 0
        logger.info("Budget: $%.2f / $%.0f (%.1f%%)", spend_dollars, budget_dollars, pct or 0)

    return snap


# ── Trigger evaluation ──────────────────────────────────────────────────────


def _cooldown_remaining(state: MonitorState, direction: str, cooldown_min: int) -> float:
    """Return minutes remaining in cooldown for a given switch direction.

    For budget-driven directions (budget_degrade / budget_upgrade), reads from
    last_budget_switch_at. For Claude-driven directions (degrade / upgrade),
    reads from last_switch_at.
    """
    ts = None
    if direction in ("budget_degrade", "budget_upgrade"):
        ts = state.last_budget_switch_at
    else:
        ts = state.last_switch_at

    if not ts or state.last_switch_direction != direction:
        return 0.0
    try:
        last = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return 0.0
    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60.0
    return max(0.0, cooldown_min - elapsed)


@dataclass
class SwitchingDecision:
    action: str
    pro_model: str | None = None
    standard_model: str | None = None
    reason: str = ""
    blocked_by_hysteresis: bool = False
    alert_only: bool = False


def evaluate_triggers(snap: UsageSnapshot, state: MonitorState) -> SwitchingDecision:
    claude_degrade_cooldown = _cooldown_remaining(state, "degrade", DEGRADE_COOLDOWN_MIN)
    claude_upgrade_cooldown = _cooldown_remaining(state, "upgrade", UPGRADE_COOLDOWN_MIN)
    budget_degrade_cooldown = _cooldown_remaining(state, "budget_degrade", BUDGET_DEGRADE_COOLDOWN_MIN)
    budget_upgrade_cooldown = _cooldown_remaining(state, "budget_upgrade", BUDGET_UPGRADE_COOLDOWN_MIN)

    c1_active = snap.claude_4hr_pct is not None and snap.claude_4hr_pct >= 95.0
    c2_active = snap.claude_7day_pct is not None and snap.claude_7day_pct >= 95.0
    claude_degraded = state.current_provider_state == "claude_degraded"
    budget_degraded = state.budget_degraded_level is not None

    bp = snap.budget_pct

    # OpenRouter credit alert flag management
    or_low = (
        snap.openrouter_remaining is not None
        and (snap.openrouter_remaining <= 5.0
             or (snap.openrouter_pct_remaining is not None
                  and snap.openrouter_pct_remaining <= 10.0))
    )
    or_ok = (
        snap.openrouter_remaining is not None
        and snap.openrouter_remaining > 5.0
        and (snap.openrouter_pct_remaining is None or snap.openrouter_pct_remaining > 10.0)
    )
    if or_ok and state.alert_sent_d2:
        logger.info("OpenRouter recovered, clearing alert flag")
        state.alert_sent_d2 = False

    # Priority 1: Claude rate-limit exhaust (MUST switch)
    if c1_active and c2_active:
        if claude_degraded:
            return SwitchingDecision(action="noop", reason="Already degraded (C1+C2 active)")
        if claude_degrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"C1+C2 degrade blocked by hysteresis ({claude_degrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="degrade_c1c2",
            pro_model=STANDARD_MODEL_DEGRADED,
            standard_model=STANDARD_MODEL_DEGRADED,
            reason=f"Claude 4hr={snap.claude_4hr_pct:.1f}% 7day={snap.claude_7day_pct:.1f}% -- both >=95%, both tiers -> OR V4 Flash",
        )

    if c1_active:
        if claude_degraded:
            return SwitchingDecision(action="noop", reason="Already degraded (C1 active)")
        if claude_degrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"C1 degrade blocked by hysteresis ({claude_degrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="degrade_c1",
            pro_model=PRO_MODEL_DEGRADED,
            standard_model=STANDARD_MODEL_NORMAL,
            reason=f"Claude 4hr={snap.claude_4hr_pct:.1f}% >= 95% -- degrading pro tier to OR V4 Pro",
        )

    if c2_active:
        if claude_degraded:
            return SwitchingDecision(action="noop", reason="Already degraded (C2 active)")
        if claude_degrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"C2 degrade blocked by hysteresis ({claude_degrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="degrade_c2",
            pro_model=PRO_MODEL_NORMAL,
            standard_model=STANDARD_MODEL_DEGRADED,
            reason=f"Claude 7day={snap.claude_7day_pct:.1f}% >= 95% -- degrading standard tier to OR V4 Flash",
        )

    # Priority 2: OpenRouter credit alert
    if or_low and not state.alert_sent_d2:
        return SwitchingDecision(
            action="alert_or",
            reason=f"OpenRouter credits low: {snap.openrouter_remaining:.1f} remaining ({snap.openrouter_pct_remaining:.1f}%)",
            alert_only=True,
        )

    # Priority 3: Budget thresholds (only when Claude is available)
    # B3: >=95% budget spent -- degrade all tiers to cheapest (OR V4 Flash)
    if bp is not None and bp >= BUDGET_DEGRADE_ALL_PCT:
        if claude_degraded:
            return SwitchingDecision(action="noop", reason="Claude already degraded, budget B3 not applicable")
        if budget_degraded and state.budget_degraded_level in ("b3", "b2", "b1"):
            return SwitchingDecision(action="noop", reason=f"Already at budget level {state.budget_degraded_level} (B3={bp:.1f}%)")
        if budget_degrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"Budget B3 degrade blocked by hysteresis ({budget_degrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="degrade_budget_b3",
            pro_model=STANDARD_MODEL_DEGRADED,
            standard_model=STANDARD_MODEL_DEGRADED,
            reason=f"Budget {bp:.1f}% >= {BUDGET_DEGRADE_ALL_PCT}% spent -- all tiers -> OR V4 Flash to conserve budget",
        )

    # B2: >=90% budget spent -- degrade standard tier to OR V4 Flash
    if bp is not None and bp >= BUDGET_DEGRADE_STANDARD_PCT:
        if claude_degraded:
            return SwitchingDecision(action="noop", reason="Claude already degraded, budget B2 not applicable")
        if budget_degraded and state.budget_degraded_level in ("b3", "b2"):
            return SwitchingDecision(action="noop", reason=f"Already at budget level {state.budget_degraded_level} (B2={bp:.1f}%)")
        if budget_degrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"Budget B2 degrade blocked by hysteresis ({budget_degrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="degrade_budget_b2",
            pro_model=PRO_MODEL_NORMAL,
            standard_model=STANDARD_MODEL_DEGRADED,
            reason=f"Budget {bp:.1f}% >= {BUDGET_DEGRADE_STANDARD_PCT}% spent -- standard tier -> OR V4 Flash",
        )

    # B1: >=80% budget spent -- alert only (no model changes).
    # Skip if already budget-degraded (b2/b3 already triggered above).
    if bp is not None and bp >= BUDGET_ALERT_PCT:
        if budget_degraded:
            return SwitchingDecision(action="noop", reason=f"Budget at {bp:.1f}%, already budget-degraded ({state.budget_degraded_level})")
        if not state.budget_alert_sent:
            state.budget_alert_sent = True
            return SwitchingDecision(
                action="alert_budget",
                reason=f"Budget {bp:.1f}% >= {BUDGET_ALERT_PCT}% spent -- monitor for potential provider switch",
                alert_only=True,
            )
        return SwitchingDecision(action="noop", reason=f"Budget at {bp:.1f}% (alert already sent)")

    # Budget recovery: spend drops below BUDGET_RECOVER_PCT
    if budget_degraded and bp is not None and bp <= BUDGET_RECOVER_PCT:
        if budget_upgrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"Budget upgrade blocked by hysteresis ({budget_upgrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="upgrade_budget",
            pro_model=PRO_MODEL_NORMAL,
            standard_model=STANDARD_MODEL_NORMAL,
            reason=f"Budget recovered to {bp:.1f}% (threshold: {BUDGET_RECOVER_PCT}%) -- restoring normal models",
        )

    # Clear budget alert flag when below threshold
    if bp is not None and bp < BUDGET_ALERT_PCT and state.budget_alert_sent:
        logger.info("Budget below alert threshold, clearing budget_alert_sent flag")
        state.budget_alert_sent = False

    # Priority 4: Claude recovery (U1) -- AND gate
    if claude_degraded:
        if not snap.claude_available:
            return SwitchingDecision(
                action="noop",
                reason=f"U1 upgrade blocked: claude_available=False (4hr={snap.claude_4hr_pct}% 7day={snap.claude_7day_pct}%)",
            )
        if claude_upgrade_cooldown > 0:
            return SwitchingDecision(
                action="noop",
                reason=f"U1 upgrade blocked by hysteresis ({claude_upgrade_cooldown:.0f}m remaining)",
                blocked_by_hysteresis=True,
            )
        return SwitchingDecision(
            action="upgrade_u1",
            pro_model=PRO_MODEL_NORMAL,
            standard_model=STANDARD_MODEL_NORMAL,
            reason=f"Claude recovered (4hr={snap.claude_4hr_pct:.1f}%, 7day={snap.claude_7day_pct:.1f}%) -- restoring normal models",
        )

    return SwitchingDecision(action="noop", reason="All conditions nominal")

# ── Agent switching ──────────────────────────────────────────────────────────


def patch_agent_model(agent_id: str, model: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("DRY-RUN: Would patch agent %s -> model %s", agent_id, model)
        return True
    try:
        with _paperclip_session() as sess:
            resp = sess.patch(
                f"{_pc_base()}/api/agents/{agent_id}",
                json={"adapterConfig": {"model": model}},
                timeout=API_TIMEOUT,
            )
            if resp.status_code == 200:
                logger.info("Patched agent %s -> model %s", agent_id, model)
                return True
            else:
                logger.error(
                    "Failed to patch agent %s: %d %s",
                    agent_id, resp.status_code, resp.text[:200],
                )
                return False
    except requests.RequestException as e:
        logger.error("Patch agent %s failed: %s", agent_id, e)
        return False


def apply_switch(decision: SwitchingDecision, state: MonitorState, dry_run: bool) -> bool:
    if decision.action == "noop" or decision.alert_only:
        if decision.alert_only:
            logger.warning("ALERT: %s", decision.reason)
        return True

    pro_model = decision.pro_model
    std_model = decision.standard_model
    any_failed = False

    for name, agent_id in PRO_AGENTS:
        if pro_model:
            ok = patch_agent_model(agent_id, pro_model, dry_run)
            if not ok:
                any_failed = True

    for name, agent_id in STANDARD_AGENTS:
        if std_model:
            ok = patch_agent_model(agent_id, std_model, dry_run)
            if not ok:
                any_failed = True

    if not dry_run:
        now_ts = datetime.now(timezone.utc).isoformat()
        if decision.action.startswith("degrade_budget"):
            state.last_budget_switch_at = now_ts
            state.last_switch_direction = "budget_degrade"
            if decision.action == "degrade_budget_b3":
                state.budget_degraded_level = "b3"
            elif decision.action == "degrade_budget_b2":
                state.budget_degraded_level = "b2"
            state.pro_model = pro_model
            state.standard_model = std_model
        elif decision.action == "upgrade_budget":
            state.last_budget_switch_at = now_ts
            state.last_switch_direction = "budget_upgrade"
            state.budget_degraded_level = None
            state.pro_model = pro_model
            state.standard_model = std_model
        else:
            direction = "degrade" if decision.action.startswith("degrade") else "upgrade"
            state.last_switch_at = now_ts
            state.last_switch_direction = direction
            state.current_provider_state = "claude_degraded" if direction == "degrade" else "normal"
            state.pro_model = pro_model
            state.standard_model = std_model
        save_state(state)

    logger.info("Switch applied: %s (pro=%s, std=%s, failed=%s)",
                decision.action, pro_model, std_model, any_failed)
    return not any_failed


# ── Board alert ──────────────────────────────────────────────────────────────


def post_board_alert(reason: str, dry_run: bool) -> None:
    body = (
        f"## Provider Monitor Alert\n\n"
        f"**{reason}**\n\n"
        f"Manual top-up required. This is an automated alert from the provider "
        f"usage monitor (`scripts/provider_monitor.py`).\n\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
    )
    if dry_run:
        logger.info("DRY-RUN: Would post board alert to [BTCAAAAA-26420](/BTCAAAAA/issues/BTCAAAAA-26420)")
        logger.info("Alert body: %s", body[:200])
        return
    try:
        with _paperclip_session() as sess:
            resp = sess.post(
                f"{_pc_base()}/api/issues/{ALERT_ISSUE_ID}/comments",
                json={"body": body},
                timeout=API_TIMEOUT,
            )
            if resp.status_code in (200, 201):
                logger.info("Board alert posted to BTCAAAAA-26420")
            else:
                logger.error("Failed to post board alert: %d %s", resp.status_code, resp.text[:200])
    except requests.RequestException as e:
        logger.error("Board alert post failed: %s", e)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provider usage monitor and agent model switching automation"
    )
    parser.add_argument("--dry-run", action="store_true", help="Log actions without patching agents")
    parser.add_argument("--json-summary", action="store_true", help="Print JSON summary and exit")
    parser.add_argument("--no-switch", action="store_true", help="Poll and alert, skip agent model patches")
    args = parser.parse_args()

    _rotate_log_if_needed()

    state = load_state()
    snap = poll_all_providers()
    decision = evaluate_triggers(snap, state)

    if args.json_summary:
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "usage": snap.to_dict(),
            "decision": {
                "action": decision.action,
                "reason": decision.reason,
                "pro_model": decision.pro_model,
                "standard_model": decision.standard_model,
                "alert_only": decision.alert_only,
                "blocked_by_hysteresis": decision.blocked_by_hysteresis,
            },
            "budget": {
                "month_spend_cents": snap.month_spend_cents,
                "month_budget_cents": snap.month_budget_cents,
                "budget_pct": snap.budget_pct,
                "degraded_level": state.budget_degraded_level,
                "alert_sent": state.budget_alert_sent,
            },
        }
        print(json.dumps(summary, indent=2))
        return

    logger.info("Decision: %s — %s", decision.action, decision.reason)

    check_record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": decision.action,
        "reason": decision.reason,
        "usage": snap.to_dict(),
    }
    state.checks.append(check_record)
    if len(state.checks) > 50:
        state.checks = state.checks[-50:]

    if decision.alert_only and decision.action == "alert_or":
        post_board_alert(decision.reason, args.dry_run)
        state.alert_sent_d2 = True
        save_state(state)
        logger.info("OR credit alert sent, alert_sent_d2 flag set")
        return

    if decision.alert_only and decision.action == "alert_budget":
        post_board_alert(decision.reason, args.dry_run)
        save_state(state)
        logger.info("Budget alert sent, budget_alert_sent flag set")
        return

    if args.no_switch:
        logger.info("--no-switch flag set, skipping agent model patches")
        save_state(state)
        return

    if decision.action not in ("noop", "alert_or"):
        apply_switch(decision, state, args.dry_run)

    save_state(state)



if __name__ == "__main__":
    main()
