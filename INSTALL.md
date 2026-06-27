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
`~/.npm/_npx/<hash>/node_modules/`. Two patches are required for
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

#### 4.3 — Fix `paperclipai-patched` wrapper script

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
- [ ] Apply the two `plugin-loader.js` patches and fix the wrapper (see §4)
- [ ] Start Paperclip (direct invocation, see §5)
- [ ] Install both plugins
- [ ] Restart Paperclip
- [ ] Smoke-test the Git Merges plugin via `actions/run-scan`

## Pointers to upstream documentation

- Paperclip plugin authoring: see `adapter-plugin.md` in this repo
- Paperclip plugin SDK: `packages/plugins/sdk/README.md`
- Paperclip CLI: `cli/`
