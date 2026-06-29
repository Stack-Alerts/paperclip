# @paperclipai/plugin-git-merges

A Paperclip plugin that runs the BTC-Trade-Engine-PaperClip
`scripts/merge_queue_status.py` script on a schedule and renders the
output as a **block-based dashboard panel with diff-vs-last tracking**.

## What you get

- A **Git Merges** link in the left sidebar's **Work** section,
  positioned right under the existing **Presets** link from
  `paperclip.agent-config-presets` (via `order: 110` vs that plugin's
  `order: 50`).
- A **Git Merges** page at `/:companyPrefix/git-merges` with three
  tabs under a single **Merge queue** card:
  - **Blocks** — one card per in-review PR showing
    - status pill (`ready to merge` / `waiting on CI` / `CI failing` /
      `no PR found` / `no Fix-SHA` / `unknown`),
    - title, Paperclip issue link (`/BTCAAAAA/issues/<identifier>`), and
      GitHub PR link (`/Stack-Alerts/BTC-Trade-Engine-PaperClip/pull/<n>`),
    - progress bar with `<passed>/<total>` checks and a striped overlay
      for the failing/pending portion,
    - per-check list with state icons (`✓` passed, `✗` failed/missing,
      `⏳` pending).
  - **Diff vs last** — the same cards, with a badge (`new` / `gone` /
    `Δ status,progress,checks`) showing what changed since the
    previous scan. Added blocks (newly in-review), removed blocks (no
    longer in-review), and changed blocks are highlighted.
  - **Raw** — the full text output of the script, with **Copy output**
    and (if any) **Copy stderr** buttons.
- **Run scan now** / **Clear output** / **Refresh** / **Save changes**
  buttons.
- **Auto-refresh** section: master toggle + interval slider (1–60 min)
  with quick chips (1m / 2m / 5m / 10m / 15m / 30m / 60m).
- **Time block** section: master toggle + start/end hour dropdowns +
  preset chips (8am–4pm, 9am–6pm, 24/7, 5min·8am–4pm).
- **Recent scans** list with timestamps, durations, and exit codes.
- A **Git Merges Settings** page (instance settings) for full editor
  control over script path, intervals, time block, capture limits, etc.

## Block parsing

The worker shells out to `scripts/merge_queue_status.py --quiet` and
parses the human-readable table with a dedicated parser
(`src/parser.ts`). Each row is mapped to:

```ts
type MergeBlock = {
  index: number;              // 1-based position in the queue
  issueUuid: string;           // Paperclip issue UUID
  issueIdentifier: string | null;  // BTCAAAAA-N (resolved via API)
  title: string;
  inReviewFor: string;        // "12m" / "1h 32m" etc.
  fixSha: string | null;
  fixShaMissing: boolean;
  prNumber: number | null;
  prMergeable: string | null;  // clean / dirty / blocked
  prTitle: string | null;
  status: "ready" | "waiting" | "failing" | "no-pr" | "no-sha" | "unknown";
  statusLabel: string;
  progressPassed: number | null;
  progressTotal: number | null;
  checks: MergeCheck[];        // per-required-check list
  diffKey: string;             // stable across scans for diffs
};
```

### Issue identifier resolution

After parsing, the worker hits the Paperclip REST API
(`GET /api/issues/:uuid`) to translate each UUID to its
`BTCAAAAA-N` identifier so the UI can link to the issue page.
The API key + base URL are read from `.env` in the configured
`repoPath`. Successful mappings are cached in instance state so
issues that leave the queue still resolve cleanly.

If the lookup fails (offline, missing API key, etc.), the UI falls
back to the UUID prefix and still works — just with less friendly
links.

## Compare view (diff-vs-last)

The worker snapshots the previous scan's parsed blocks to
`previous-blocks` in instance state at the START of each scan
(before the script runs). The diff is computed client-side:

- **Added**: a block in the current scan that wasn't in the previous.
- **Removed**: a block in the previous scan that's no longer there.
- **Changed**: a block that's in both scans but with different
  status / PR / fix-SHA / progress / checks / title.
- **Unchanged**: identical on both sides.

The badge next to each card tells you which kind it is and what
specifically changed (e.g. `Δ progress,checks`).

## Default configuration

The default configuration is hardcoded to the local BTC checkout on
this workstation:

| Setting          | Default value |
|------------------|---------------|
| `pythonPath`     | `/home/sirrus/projects/BTC-Trade-Engine-PaperClip/venv/bin/python3` |
| `repoPath`       | `/home/sirrus/btc-test-worktrees/fix-38557` |
| `scriptPath`     | `scripts/merge_queue_status.py` |
| `autoRefreshEnabled` | `true` |
| `autoRefreshIntervalSeconds` | `300` (5 min) |
| `timeBlockEnabled` | `true` |
| `timeBlockStartHour` | `8` |
| `timeBlockEndHour`   | `16` |
| `showJson`       | `false` |
| `maxOutputChars` | `200_000` |
| `scanTimeoutSeconds` | `120` |

The default `repoPath` is a dedicated git worktree
(`/home/sirrus/btc-test-worktrees/fix-38557`) tracking
`origin/fix/BTCAAAAA-38557-merge-ready-watcher` — that's the branch
that introduced `scripts/merge_queue_status.py`. The script was
reverted from the local main branch on 2026-06-27, so pointing the
plugin at the main BTC checkout (the previous default) makes every
scan fail with exit 2 (`[Errno 2] No such file or directory`). If the
script lands on `main`, change `repoPath` back to
`/home/sirrus/projects/BTC-Trade-Engine-PaperClip`.

If the worktree doesn't exist yet, create it with:

```sh
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip
git worktree add /home/sirrus/btc-test-worktrees/fix-38557 \
    origin/fix/BTCAAAAA-38557-merge-ready-watcher
ln -s /home/sirrus/projects/BTC-Trade-Engine-PaperClip/.env \
      /home/sirrus/btc-test-worktrees/fix-38557/.env
```

The `.env` symlink is needed because the script reads `.env` from the
repo root, and worktrees don't carry untracked files from the main
checkout.

Change any of the settings from the **Git Merges Settings** page; the
host restarts the worker on save, and the new setup reads the fresh
config from the host's stored config.

## Install

```sh
# from the repo root
pnpm --filter @paperclipai/plugin-git-merges build
pnpm paperclipai plugin install ./packages/plugins/plugin-git-merges
```

Or, once this repo is published, install the plugin from the Paperclip
plugin manager.

## Architecture

```
+-----------------+      data getData     +-------------------+
|   worker.ts     |  <------------------  |   ui/index.tsx    |
|                 |  --------------------> |                   |
|  - jobs.        |                         |  - page slot      |
|    register     |  actions (performAction)|  - sidebar slot   |
|  - actions.     |  --------------------> |  - settingsPage   |
|    register     |                         |                   |
|  - data.        |                         |                   |
|    register     |                         |                   |
+--------+--------+                         +-------------------+
         |
         v
   spawn(python3) on cwd = repoPath
   parse stdout → MergeBlock[]
   fetch identifiers via Paperclip REST API
   persist latest + previous-blocks + history to instance state
```

### Auto-refresh cadence

The manifest declares a `*/5 * * * *` cron so the host invokes the job
handler every 5 minutes. Inside the handler the worker re-checks the
user-configured interval (`autoRefreshIntervalSeconds`) and time block,
so the actual cadence is whatever the user picked (1–60 min) without
redeploying. The plugin reads/writes the user config from instance
state via the standard `plugin.state` SDK calls.

### Live output (polling)

The host's stream bridge isn't always wired up in every release, so
this plugin uses polling instead of SSE: the UI calls
`usePluginData("git-merges-snapshot")` every 1.5 s while a scan is
running and every 30 s otherwise. The worker also writes a *partial*
record to `latest-scan` every 500 ms during the scan, so the UI sees
output streaming in chunks rather than only after the scan finishes.

### Time-block semantics

The block is inclusive on the start hour, exclusive on the end hour, in
**local server time**. Wrapping midnight is supported: `start=22,
end=6` matches 22:00–00:00 and 00:00–06:00.

## Notes

- The plugin intentionally does not shell out via `gh` itself; it
  delegates everything to the existing script. The script already
  handles `.env` loading from the BTC repo root.
- ANSI colour codes are stripped from the captured output before it
  reaches the UI so the panel stays readable.
- Scans are non-overlapping: the worker refuses to start a new scan if
  one is already running, except for manual scans triggered via **Run
  scan now** (which always pass `force: true`).
- The plugin keeps the last 12 completed scans in instance state.
- The output buffer is clamped to `maxOutputChars` (default 200k) per
  scan to prevent unbounded memory growth.
- The plugin reads `.env` itself (an ESM-safe loader in
  `src/worker.ts`) to look up the Paperclip API key when resolving
  issue identifiers. It does NOT pass the worker's environment to the
  spawned python child — only a minimal whitelist
  (`PATH`, `HOME`, `LANG`, `LC_ALL`, `TZ`, `PYTHONUNBUFFERED`) is
  forwarded. The script reads credentials from `.env` itself.
- The plugin validates that `scriptPath` doesn't escape `repoPath`
  (e.g. `../../etc/passwd`) and turns a malicious-looking path into a
  synthetic failed scan rather than letting the python child spawn
  whatever it likes.
