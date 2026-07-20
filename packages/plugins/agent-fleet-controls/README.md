# Agent Fleet Controls

Compact global controls to pause and resume company agents in bulk.

The plugin adds an **Agents** button immediately to the right of Paperclip's version badge. Its compact popover provides six guarded actions:

- Pause all agents, including the CEO and CTO
- Resume all paused agents, including the CEO and CTO
- Pause all agents except the CEO and CTO
- Resume all paused agents except the CEO and CTO
- Resume only the CEO
- Resume only the CEO and CTO

Pause requests use Paperclip's board API, so active runs are cancelled and normal `agent.paused` activity records are written. Resume requests use the matching audited board endpoint. Actions are company-scoped, confirmed before execution, processed in bounded batches, and report partial failures without abandoning the remaining agents.

## Development

```bash
pnpm install
pnpm dev
pnpm dev:ui
pnpm typecheck
pnpm test
pnpm build
```

`pnpm dev` rebuilds the worker, manifest, and UI bundles into `dist/`. When this package is installed from a local path, Paperclip watches that rebuilt output and reloads the plugin worker. Local installs run trusted code from this folder on your machine.

This scaffold snapshots `@paperclipai/plugin-sdk` and `@paperclipai/shared` from a local Paperclip checkout at:

`/home/sirrus/paperclip-btcaaaaa-main/packages/plugins/sdk`

The packed tarballs live in `.paperclip-sdk/` for local development. Before publishing this plugin, switch those dependencies to published package versions once they are available on npm.

## Install Into Paperclip

```bash
paperclipai plugin install /home/sirrus/paperclip-plugins/agent-fleet-controls
```

## Version Control

The plugin is an independent Git repository. Stable work lands on `main`; development and local testing use feature branches such as `feat/agent-fleet-controls`. Keep `package.json` and `src/manifest.ts` on the same semantic version for every release.

## Build Options

- `pnpm build` uses esbuild presets from `@paperclipai/plugin-sdk/bundlers`.
- `pnpm build:rollup` uses rollup presets from the same SDK.
