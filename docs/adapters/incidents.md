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