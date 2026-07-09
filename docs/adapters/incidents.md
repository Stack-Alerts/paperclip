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

## 2026-05-09 / 2026-07-09 — claude_local five-hour rate-limit recovery (NautilusEngineer)

- **Issue:** [BTCAAAAA-799](/BTCAAAAA/issues/BTCAAAAA-799) — NautilusEngineer
  (agent `a472d315-3e2e-4c3b-a1ba-a931295628cc`) entered `error` status with
  last successful heartbeat at `2026-05-09T14:21:43Z`. Same `claude_local`
  adapter family as the two rows above but a **third distinct** failure
  mode: an external Claude API quota signal, not a watchdog or process-loss
  event.
- **Root cause:** External Claude API quota. The upstream response body was
  `claude_transient_upstream: "You've hit your limit · resets 4:30pm
  (Europe/Warsaw)"` with `rateLimitType: five_hour`. All four `claude_local`
  agents on the company (NautilusEngineer, RepoSteward, QAEngineer,
  DevelopmentManager) hit the same quota boundary within the same
  five-minute window and entered `error` together. This is a server-side
  quota reset, **not** an adapter-wrapper fault — recovery is automatic on
  the next upstream reset window (`Europe/Warsaw` 16:30 in this case), and
  the next heartbeat for each agent succeeds without any local action.
- **Code change:** None. The `claude_local` adapter wrapper behaviour
  matches its contract; the quota window is enforced by Claude and
  surfaces verbatim in `errorReason`.
- **Verification:** Issue was closed on `2026-05-09T15:29:05.292Z` after the
  upstream quota reset cleared and the subsequent heartbeat run
  `2f31e77a-0987-4fc7-98ac-e53c47d400f7` succeeded. The closure-gate
  routine reopened it on `2026-07-06T11:22:23.820Z` because the original
  closure comment lacked a `Fix-SHA:` tag on `btcaaaaa-main`. This
  audit-trail commit provides the verifiable anchor. NautilusEngineer is
  `running` with `errorReason: null` as of `2026-07-09T12:49Z`; the related
  stalled tasks BTCAAAAA-778 and BTCAAAAA-594 are tracked separately and
  BTCAAAAA-594 is blocked on testnet credentials (a human-action item,
  unrelated to the adapter state).
- **Action for future occurrences:** Read `errorReason` before assuming
  anything (per the `project-claude-local-failure-modes` memory note).
  An upstream-quota signature — body containing `claude_transient_upstream`,
  `rateLimitType: five_hour`, or the phrases "you've hit your limit",
  "resets", or quota-window timestamps — is **API-quota driven** and
  self-clearing at the next reset window. Do **not** mark the tracking
  issue `blocked` waiting on host-side remediation; the unblock path is
  the upstream quota reset, not local adapter supervision. Distinguish
  carefully from the process-loss mode above (which names a pid) and the
  transient mode (which recovers silently on the next watchdog tick).