# Local plugin stack — install + recovery guide

This document explains how to set up the Paperclip plugin stack used
in this workspace from a fresh checkout, including the **Git Merges**
plugin (in this repo) and the **Agent Config Presets** plugin (a
separate repo).

If you ever lose this machine and need to rebuild from GitHub, this is
the canonical recipe.

## TL;DR

```sh
# 1. Paperclip source (this repo)
git clone git@github.com:Stack-Alerts/paperclip.git paperclip-plugin-dev
cd paperclip-plugin-dev
pnpm install

# 2. BTC-Trade-Engine-PaperClip (the script's source repo)
git clone git@github.com:Stack-Alerts/BTC-Trade-Engine-PaperClip.git

# 3. Build the Git Merges plugin
pnpm --filter @paperclipai/plugin-git-merges build

# 4. Patch the running Paperclip npx cache for local-path plugin support
#    (see "Required patches" below)

# 5. Start Paperclip and install the plugins
cd paperclip-plugin-dev
nohup /home/sirrus/.npm/_npx/43414d9b790239bb/node_modules/.bin/paperclipai \
    run --instance default > /tmp/paperclip-restart.log 2>&1 &
pnpm paperclipai plugin install --api-base http://127.0.0.1:3100 \
    ./packages/plugins/plugin-git-merges
pnpm paperclipai plugin install --api-base http://127.0.0.1:3100 \
    /home/sirrus/dev/paperclip-plugins/agent-config-presets
```

## Components

| Plugin | Source | Role |
|--------|--------|------|
| **Git Merges** | This repo, `packages/plugins/plugin-git-merges/` | Runs `merge_queue_status.py`, renders the merge-queue dashboard with diff-vs-last |
| **Agent Config Presets** | `git@github.com:Stack-Alerts/paperclip-agent-config-presets.git` (clone to `~/dev/paperclip-plugins/agent-config-presets`) | Saves + applies adapter/permission presets to agents; the "Presets" sidebar link |
| **merge_queue_status.py** | `BTC-Trade-Engine-PaperClip` repo, branch `origin/fix/BTCAAAAA-38557-merge-ready-watcher` | The script Git Merges shells out to |

## Prereqs

- Node ≥ 20 (Node 22 LTS recommended)
- pnpm 9.x (`npm i -g pnpm`)
- A POSIX shell (bash/zsh)
- Git with SSH access to the Stack-Alerts orgs on GitHub
- A running PostgreSQL or `embedded-postgres` (paperclip handles the latter automatically)

## Detailed setup

### 1. Clone the repos

```sh
# Paperclip source — the repo this file lives in
git clone git@github.com:Stack-Alerts/paperclip.git paperclip-plugin-dev
cd paperclip-plugin-dev
git fetch --all

# BTC-Trade-Engine-PaperClip — the repo with the merge_queue_status.py script
git clone git@github.com:Stack-Alerts/BTC-Trade-Engine-PaperClip.git

# Agent Config Presets plugin — the "Presets" sidebar entry
mkdir -p ~/dev/paperclip-plugins
git clone git@github.com:Stack-Alerts/paperclip-agent-config-presets.git \
    ~/dev/paperclip-plugins/agent-config-presets
```

### 2. Install dependencies + build

```sh
cd paperclip-plugin-dev
pnpm install
pnpm build   # builds shared, sdk, server, ui, cli, and all plugins

# Verify the Git Merges plugin built cleanly
ls packages/plugins/plugin-git-merges/dist/{manifest.js,worker.js,ui/index.js}
```

### 3. Set up the script worktree

The Git Merges plugin defaults to running the script out of a
dedicated git worktree because the script was reverted from the main
branch of `BTC-Trade-Engine-PaperClip` on 2026-06-27.

```sh
cd BTC-Trade-Engine-PaperClip
git worktree add /home/sirrus/btc-test-worktrees/fix-38557 \
    origin/fix/BTCAAAAA-38557-merge-ready-watcher

# Symlink .env so the script's loader finds PAPERCLIP_API_KEY,
# PAPERCLIP_API_URL, and PAPERCLIP_COMPANY_ID
ln -s /home/sirrus/projects/BTC-Trade-Engine-PaperClip/.env \
      /home/sirrus/btc-test-worktrees/fix-38557/.env

# Smoke-test the script end-to-end
/home/sirrus/projects/BTC-Trade-Engine-PaperClip/venv/bin/python3 \
    /home/sirrus/btc-test-worktrees/fix-38557/scripts/merge_queue_status.py --quiet
```

If the script is eventually merged into `main`, you can skip the
worktree and point the plugin at `BTC-Trade-Engine-PaperClip` directly.

### 4. Required patches (Paperclip npx cache)

Paperclip's `npx paperclipai@latest` workflow installs in
`~/.npm/_npx/<hash>/node_modules/`. Three patches are required for
local-path plugins (like this one) to load successfully because the
upstream host has known gaps. These patches live in the running cache
and are gitignored — they're regenerated automatically on each
`pnpm build`, but you'll need to re-apply them if the cache is wiped.

#### 4.1 — Fix `DEV_TSX_LOADER_PATH` (tsx-loader is in the wrong sub-path)

```sh
NPX_CACHE=/home/sirrus/.npm/_npx/43414d9b790239bb/node_modules
sed -i 's|"../../../cli/node_modules/tsx/dist/loader.mjs"|"../../../../tsx/dist/loader.mjs"|' \
    "$NPX_CACHE/@paperclipai/server/dist/services/plugin-loader.js"
```

#### 4.2 — Preserve `packagePath` across the manifest-refresh

The new worker manifest is built without `packagePath`, which makes
the `packagePath && exists(DEV_TSX_LOADER_PATH)` branch skip. Patch the
loader to preserve the field:

```sh
NPX_CACHE=/home/sirrus/.npm/_npx/43414d9b790239bb/node_modules
sed -i 's|activePlugin = await refreshPluginManifestFromPackage(activePlugin, packageRoot);|activePlugin = await refreshPluginManifestFromPackage(activePlugin, packageRoot);\n            activePlugin.packagePath = activePlugin.packagePath ?? plugin.packagePath;|' \
    "$NPX_CACHE/@paperclipai/server/dist/services/plugin-loader.js"
```

#### 4.3 — Bundle the worker (don't rely on runtime `.ts` resolution)

The plugin SDK and shared package both use `tsc` to build, which
leaves `import "@paperclipai/shared"` as a bare external import in
the SDK's `dist/index.js`. At runtime Node tries to resolve
`@paperclipai/shared` via the workspace's `exports` map, which
points at `./src/index.ts` — and the host's tsx loader is not
applied transitively to that path. Symptom: on worker startup,
`ERR_UNKNOWN_FILE_EXTENSION: Unknown file extension ".ts" for
.../packages/shared/src/index.ts`.

Fix: the plugin's own `build` script bundles the worker with
esbuild so the SDK + shared are inlined into a single self-contained
file. The plugin's `package.json` already has this set as the
`build` script — if you copied the source elsewhere, make sure the
`build` script in your `package.json` includes the
`pnpm exec esbuild src/worker.ts --bundle ...` invocation, not a
plain `tsc`.

#### 4.4 — Fix `paperclipai-patched` wrapper script

The wrapper at `~/.local/bin/paperclipai-patched` has a hard-coded
cache path that goes stale as soon as npx rotates to a new cache
hash. Replace it with a runtime-resolved path, or invoke the binary
directly:

```sh
# Option A — direct invocation (recommended until the wrapper is fixed):
nohup /home/sirrus/.npm/_npx/43414d9b790239bb/node_modules/.bin/paperclipai \
    run --instance default > /tmp/paperclip-restart.log 2>&1 &

# Option B — fix the wrapper by computing the cache hash at startup.
# Edit ~/.local/bin/paperclipai-patched and replace the hard-coded
# "exec /home/sirrus/.npm/_npx/0aa74679bec75e15/..." line with:
#   CACHE=$(ls -td ~/.npm/_npx/*/node_modules 2>/dev/null \
#     | xargs -I{} sh -c '[ -d {}/paperclipai ] && echo {}' | head -1)
#   exec "$CACHE/.bin/paperclipai" "$@"
```

#### 4.5 — Patch the Paperclip Service Worker (`sw.js`)

Paperclip ships a `sw.js` whose `fetch` handler can resolve to
`undefined` from the network-failure fallback:

```js
.catch(() => {
  if (request.mode === "navigate") {
    return caches.match("/") || new Response("Offline", { status: 503 });
  }
  return caches.match(request);   // ← undefined when not cached
})
```

`event.respondWith(undefined)` makes Chrome reject the FetchEvent
("Failed to convert value to 'Response'"), which leaves the host
bundle in a half-loaded state and the page stuck on its spinner.
Compounding this, the service-worker update race means an old,
buggy SW can control a tab while a new one activates, producing
**intermittent** "Loading…" hangs after a fresh plugin install.

Patch `sw.js` so the fallback always returns a `Response` and the
new SW force-reloads any tabs that were under the old SW:

```sh
# Three locations to patch — the SW gets copied from public/ → dist/ by
# Vite, and from dist/ → the npx cache by the install workflow. Any build
# that re-runs (e.g. UI dev-watch) re-copies from public/, so all three
# must be patched or the next build reverts the fix.
SWJS='const CACHE_NAME = "paperclip-v2";
const OFFLINE_FALLBACK = "/";

self.addEventListener("install", () => { self.skipWaiting(); });

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
    await self.clients.claim();
    // Only force-reload when there was a previous cache — the very
    // first install must NOT reload every open tab.
    if (keys.length > 0) {
      const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of clients) {
        try { await client.navigate(client.url); } catch {}
      }
    }
  })());
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.pathname.startsWith("/api")) return;
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && url.origin === self.location.origin) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(async () => {
        if (request.mode === "navigate") {
          const cached = (await caches.match(OFFLINE_FALLBACK)) ||
            (await caches.match(request)) ||
            new Response("Offline", { status: 503 });
          return cached;
        }
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response("Offline", { status: 503 });
      })
  );
});'

# 1. Source — Vite copies this to dist/ on every build
PAPERCLIP_UI=/home/sirrus/projects/paperclip/ui
[ -f "$PAPERCLIP_UI/public/sw.js" ] && cp "$PAPERCLIP_UI/public/sw.js" "$PAPERCLIP_UI/public/sw.js.bak"
echo "$SWJS" > "$PAPERCLIP_UI/public/sw.js"

# 2. Vite dist — must match public/ or the next build reverts
[ -f "$PAPERCLIP_UI/dist/sw.js" ] && cp "$PAPERCLIP_UI/dist/sw.js" "$PAPERCLIP_UI/dist/sw.js.bak"
echo "$SWJS" > "$PAPERCLIP_UI/dist/sw.js"

# 3. npx cache — runtime copy that the browser actually fetches
NPX_CACHE=/home/sirrus/.npm/_npx/43414d9b790239bb/node_modules
SW="$NPX_CACHE/@paperclipai/server/ui-dist/sw.js"
[ -f "$SW" ] && cp "$SW" "$SW.bak"
echo "$SWJS" > "$SW"

# Verify all three are in sync and valid JS.
md5sum "$PAPERCLIP_UI/public/sw.js" "$PAPERCLIP_UI/dist/sw.js" "$SW"
node --check "$SW" && echo "sw.js OK"
```

After patching, **hard refresh** the browser once so the new SW
takes over. If the page still hangs after a fresh install,
close all `127.0.0.1:3100` tabs and reopen — this guarantees every
tab is born under the new SW.

### 5. Start Paperclip and install the plugins

```sh
# Start (direct invocation, see §4.3).
nohup /home/sirrus/.npm/_npx/43414d9b790239bb/node_modules/.bin/paperclipai \
    run --instance default > /tmp/paperclip-restart.log 2>&1 &

# Wait for health.
for i in $(seq 1 30); do
  curl -s http://127.0.0.1:3100/api/health >/dev/null && break
  sleep 1
done

# Install the Git Merges plugin (this repo).
cd paperclip-plugin-dev
pnpm paperclipai plugin install --api-base http://127.0.0.1:3100 \
    ./packages/plugins/plugin-git-merges

# Install the Agent Config Presets plugin (separate repo).
pnpm paperclipai plugin install --api-base http://127.0.0.1:3100 \
    ~/dev/paperclip-plugins/agent-config-presets
```

After install, restart Paperclip one more time so the
`plugin-dev-watcher` registers both plugins for hot-reload:

```sh
pkill -KILL -f "paperclipai run"
nohup /home/sirrus/.npm/_npx/43414d9b790239bb/node_modules/.bin/paperclipai \
    run --instance default > /tmp/paperclip-restart.log 2>&1 &
```

### 6. Verify

```sh
# Plugin list — both should be status: ready.
curl -s http://127.0.0.1:3100/api/plugins | python3 -m json.tool \
    | python3 -c "import json,sys; [print(p['pluginKey'], p['status']) for p in json.load(sys.stdin)]"

# Trigger a Git Merges scan.
curl -s -X POST -H 'Content-Type: application/json' --max-time 90 \
    -d '{"force":true}' \
    http://127.0.0.1:3100/api/plugins/paperclip.git-merges/actions/run-scan

# Snapshot should show ~13 in-review blocks.
curl -s -X POST -H 'Content-Type: application/json' \
    -d '{}' http://127.0.0.1:3100/api/plugins/paperclip.git-merges/data/git-merges-snapshot \
    | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print('blocks:', len(d['blocks']), 'previousBlocks:', len(d['previousBlocks'] or []))"
```

Open `http://127.0.0.1:3100/BTCAAAAA/git-merges` in the browser. The
**Git Merges** link should appear in the left sidebar directly under
**Presets**. Click it to land on the block-based dashboard.

## Recovery checklist (TL;DR)

If you're rebuilding from scratch and only have this repo:

- [ ] `pnpm install && pnpm build` in `paperclip-plugin-dev`
- [ ] Verify `dist/manifest.js`, `dist/worker.js`, `dist/ui/index.js` exist in `packages/plugins/plugin-git-merges/`
- [ ] `git worktree add …fix-38557 origin/fix/BTCAAAAA-38557-merge-ready-watcher` and symlink `.env` (see §3)
- [ ] Apply the three `plugin-loader.js` patches, fix the wrapper, and patch `sw.js` (see §4)
- [ ] Start Paperclip (direct invocation, see §5)
- [ ] Install both plugins
- [ ] Restart Paperclip
- [ ] Smoke-test the Git Merges plugin via `actions/run-scan`

## Pointers to upstream documentation

- Paperclip plugin authoring: see `adapter-plugin.md` in this repo
- Paperclip plugin SDK: `packages/plugins/sdk/README.md`
- Paperclip CLI: `cli/`
