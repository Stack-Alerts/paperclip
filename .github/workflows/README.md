# Workflow cadence-vs-threshold policy

This directory holds GitHub Actions workflows. Several of them are monitors
that alert when something else has gone silent. **The cadence-vs-threshold
policy below is the contract those monitors must honor.**

## Why this exists

GitHub Actions scheduled events are **dropped, not queued**, when capacity is
constrained (see [GitHub's docs](https://docs.github.com/en/actions/using-github-actions/events-that-trigger-workflows#schedule)).
On this repo the `*/15` and `*/30` cron slots miss roughly 50% of their
scheduled firings under load, and the longest observed gap between two
scheduled runs of `deadman-switch-monitor.yml` was **118 min** versus a
30 min designed cadence.

If a monitor's alert threshold is tuned to the **designed** cadence, it will
chronically false-positive under realistic GH Actions load. If it is tuned
to the **observed** cadence, real stalls take too long to surface.

The policy below sets the threshold against the observed cadence with a
bounded multiplier.

## Policy

For every scheduled monitor workflow:

1. **Designed cadence** is whatever the `cron:` expression says (e.g. `*/15`
   → 15 min). Document it in the workflow file's header comment.

2. **Observed cadence** is what the workflow actually fires at under normal
   load. Measure it with `scripts/audit_cron_slot_dropping.py` over a 7-day
   window.

3. **Alert threshold** is set to `max(3 × designed_cadence, observed_p95_gap)`
   and is the **default** in both:
   - `workflow_dispatch.inputs.threshold.default`
   - the script's `MONITOR_THRESHOLD_MINUTES` constant

   The script reads the threshold from an env var so operators can override
   per-deployment without editing source.

4. **Threshold must be ≥ 3× designed cadence.** PRs that propose a tighter
   threshold must include a written justification (typically "self-hosted
   runner with sub-minute observability, not GH Actions cron").

5. **Threshold must be env-var configurable**, not a hard-coded literal.
   Standard env var names:
   - `<SCRIPT_SNAKE_CASE>_THRESHOLD_MINUTES` (e.g. `DEADMAN_MONITOR_THRESHOLD_MINUTES`)

6. **Self-hosted monitors** that depend on GH Actions to fire (any
   `on: schedule:` block) are treated as GH Actions cron for threshold
   purposes, even if the *target* workflow is self-hosted.

## Current monitors

| Workflow | Cron | Designed cadence | Default threshold | Multiplier | Notes |
|---|---|---|---|---|---|
| `deadman-switch-monitor.yml` | `15,45 * * * *` | 30 min | **90 min** | 3× | Raised from 45 (BTCAAAAA-37890). |
| `backup-deadman-switch-monitor.yml` | `12,42 * * * *` | 30 min | **180 min** | 6× primary cadence | Raised from 90 (BTCAAAAA-37890). |
| `deadman-switch-local-monitor.yml` | `5,20,35,50 * * * *` | 15 min | 45 min | 3× | Reads local state file (not GH cron); observed cadence is designed cadence. |
| `paperclip-recovery-monitor.yml` | `*/30 * * * *` | 30 min | 90 min | 3× | TBD — verify with audit. |
| `blast-radius-monitor.yml` | `*/30 * * * *` | 30 min | (script default) | TBD | Verify. |
| `closure-gate-routine.yml` | `*/15 * * * *` | 15 min | (script default) | TBD | Verify. |
| `traceability-monitor.yml` | `*/30 * * * *` | 30 min | (script default) | TBD | Verify. |

## How to audit a workflow

```sh
# Default: audit the last 7 days for every workflow with a schedule trigger
python scripts/audit_cron_slot_dropping.py

# Audit a specific workflow over 14 days
python scripts/audit_cron_slot_dropping.py --workflow deadman-switch-monitor.yml --days 14
```

The script prints, per workflow:

- designed cadence (parsed from `cron:`)
- observed p50, p95, max gap between scheduled firings
- slot-drop rate (missing slots / expected slots)
- whether the current default threshold would suppress observed false positives

If a workflow is not on the table above, run the audit and add a row.
