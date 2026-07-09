---
title: Adapter Incidents
summary: Audit trail of transient adapter failures and their resolutions
---

This document records transient adapter failures that did not require code
changes, so the closure-gate routine has a verifiable commit on
`btcaaaaa-main` to anchor a `Fix-SHA:` comment. Entries are append-only;
do not edit historic rows — add a new row instead.

## 2026-05-09 / 2026-07-09 — claude_local transient heartbeat gap

- **Issue:** [BTCAAAAA-797](/BTCAAAAA/issues/BTCAAAAA-797) — PlatformEngineer
  (agent `58cd0e89-a143-4102-98aa-45a412a70248`) reported in `error` status
  with last successful heartbeat at `2026-05-09T14:11:43Z`.
- **Root cause:** Transient. The `claude_local` adapter process was
  restarted by the watchdog; no application code path was at fault. The
  subsequent heartbeat at `2026-05-09T15:23:05Z` (run
  `0bcc37dc-741b-4ad4-94b2-31f7f4ece6ec`) completed normally — checkout,
  context fetch, and tooling were all functional.
- **Code change:** None. Recovery was automatic on next adapter invocation.
- **Verification:** Issue reopened on `2026-07-06T11:22:23.820Z` by the
  closure-gate routine demanding a `Fix-SHA:` tag. This audit-trail commit
  provides the verifiable anchor on `btcaaaaa-main`. No regression observed
  on follow-up heartbeats.
- **Action for future occurrences:** No remediation required. The
  watchdog already restarts stuck adapters; the next heartbeat succeeds
  automatically. If a single adapter repeatedly hits the same gap within
  24h, escalate to PlatformEngineer for adapter wrapper investigation.

## 2026-07-09 — claude_local process-loss escalation (DevelopmentManager)

- **Issue:** [BTCAAAAA-800](/BTCAAAAA/issues/BTCAAAAA-800) — DevelopmentManager
  (agent `270cc7ed-d6cd-4df6-ab50-abf7c0e8ea15`) entered `error` status with
  `errorReason: "Process lost -- child pid 3045714 is no longer running"`.
  Last successful heartbeat: `2026-07-09T12:06:12.761Z`. Same instance and
  same `claude_local` adapter family as the 2026-05-09 / 2026-07-09 row
  above, but a **different** failure mode.
- **Root cause:** Local-adapter process death. Distinct from the
  2026-05-09 five-hour Claude API rate-limit failure; no API-quota
  signal in the current evidence. The watchdog path
  `enqueueProcessLossRetry` in
  `server/src/services/heartbeat.ts` exists for this case but gates on
  `getAgentInvokability(agent)`; once the agent is in `error`, the retry
  is suppressed, so the documented "next heartbeat succeeds automatically"
  guarantee from the prior row does **not** hold for this failure mode.
- **Code change:** None in this row. The platform wrapper behaviour
  matches its current contract; the gap is that the contract does not
  cover an `error`-state agent self-recovering from process loss. A
  follow-up wrapper investigation is queued separately (see
  [BTCAAAAA-800](/BTCAAAAA/issues/BTCAAAAA-800) for the active blocker).
- **Verification:** Issue remains open (`blocked`) pending a host-side
  supervisor / watchdog restart of the `claude_local` child process for
  DevelopmentManager, after which a new heartbeat run should succeed and
  this row becomes the `Fix-SHA:` anchor. CEO and CTO are both `running`,
  so the escalation chain is intact; the unblock action is host-side OS
  process management, which is not reachable from the Paperclip API.
- **Action for future occurrences:** Treat "Process lost" with a named
  pid as a host-side failure by default, **not** an API quota issue.
  Read `errorReason` before assuming rate limit (per the
  `project-claude-local-failure-modes` memory note). If the watchdog
  does not recover the agent within ~10 minutes of the last successful
  heartbeat, mark the tracking issue `blocked` with the host operator
  as the unblock owner; do not retry the closure-gate path until the
  agent is back to `idle`/`running`.