// worker.ts — paperclip-pause plugin worker
//
// Tracks a single global pause flag in plugin_state at instance scope.
// The host's top bar renders the Pause/Run button from this plugin's
// sidebar slot. When clicked:
//   1. UI calls ctx.data/state to read & write the flag (this worker).
//   2. UI calls POST /api/agents/:id/pause for each agent in the
//      current company (using the user's browser session). The host's
//      heartbeat already skips dispatch when paused_at is set — running
//      runs are NOT cancelled (no work loss).
//
// Source for the rebuild artifact at dist/worker.js. This file mirrors
// dist/worker.js so future `pnpm build` invocations don't regress any
// registered state / data / actions.

import { definePlugin, runWorker, type PaperclipPlugin } from "@paperclipai/plugin-sdk";

import {
  ACTION_KEYS,
  DATA_KEYS,
  JOB_KEYS,
  PLUGIN_ID,
  STATE_KEYS,
} from "./constants.js";

type PausedState = {
  paused: boolean;
  pausedAt: string | null;
  pausedBy: string | null;
  pausedReason: string | null;
  summary: {
    agents: number;
    companies: number;
    computedAt: string | null;
  };
};

const DEFAULT_STATE: PausedState = {
  paused: false,
  pausedAt: null,
  pausedBy: null,
  pausedReason: null,
  summary: { agents: 0, companies: 0, computedAt: null },
};

// Minimal ctx shape we actually use. The real PluginContext has many more
// methods, but this narrow type avoids dragging the SDK's `ScopeKey` union
// into our callers (where {scopeKind: string, stateKey: string} is enough).
type PauseCtx = {
  state: {
    get: (q: { scopeKind: string; stateKey: string }) => Promise<unknown>;
    set: (q: { scopeKind: string; stateKey: string }, v: unknown) => Promise<void>;
  };
  logger: {
    info: (msg: string, meta?: Record<string, unknown>) => void;
  };
};

async function readState(ctx: PauseCtx): Promise<PausedState> {
  const [pausedRaw, byRaw, atRaw, reasonRaw, agentsRaw, companiesRaw, summaryAtRaw] = await Promise.all([
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.paused }).catch(() => null),
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.pausedBy }).catch(() => null),
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.pausedAt }).catch(() => null),
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.pausedReason }).catch(() => null),
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.summaryAgents }).catch(() => null),
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.summaryCompanies }).catch(() => null),
    ctx.state.get({ scopeKind: "instance", stateKey: STATE_KEYS.summaryAt }).catch(() => null),
  ]);

  return {
    paused: pausedRaw === true,
    pausedAt: typeof atRaw === "string" ? atRaw : null,
    pausedBy: typeof byRaw === "string" ? byRaw : null,
    pausedReason: typeof reasonRaw === "string" ? reasonRaw : null,
    summary: {
      agents: typeof agentsRaw === "number" ? agentsRaw : 0,
      companies: typeof companiesRaw === "number" ? companiesRaw : 0,
      computedAt: typeof summaryAtRaw === "string" ? summaryAtRaw : null,
    },
  };
}

async function writeState(ctx: PauseCtx, state: PausedState): Promise<void> {
  await Promise.all([
    ctx.state.set({ scopeKind: "instance", stateKey: STATE_KEYS.paused }, state.paused).catch(() => null),
    ctx.state
      .set({ scopeKind: "instance", stateKey: STATE_KEYS.pausedAt }, state.pausedAt)
      .catch(() => null),
    ctx.state
      .set({ scopeKind: "instance", stateKey: STATE_KEYS.pausedBy }, state.pausedBy)
      .catch(() => null),
    ctx.state
      .set({ scopeKind: "instance", stateKey: STATE_KEYS.pausedReason }, state.pausedReason)
      .catch(() => null),
    ctx.state
      .set({ scopeKind: "instance", stateKey: STATE_KEYS.summaryAgents }, state.summary.agents)
      .catch(() => null),
    ctx.state
      .set({ scopeKind: "instance", stateKey: STATE_KEYS.summaryCompanies }, state.summary.companies)
      .catch(() => null),
    ctx.state
      .set({ scopeKind: "instance", stateKey: STATE_KEYS.summaryAt }, state.summary.computedAt)
      .catch(() => null),
  ]);
}

export const pluginInstance: PaperclipPlugin = definePlugin({
  async setup(ctx) {
    // The actual PluginContext is wider than PauseCtx but structural.
    const pctx = ctx as unknown as PauseCtx;

    // ---------------------------------------------------------------------
    // Data providers
    // ---------------------------------------------------------------------

    ctx.data.register(DATA_KEYS.state, async () => {
      return await readState(pctx);
    });

    // ---------------------------------------------------------------------
    // Actions
    // ---------------------------------------------------------------------

    ctx.actions.register(ACTION_KEYS.setPaused, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const paused = p.paused === true;
      const reason = typeof p.reason === "string" ? p.reason : null;
      const by = typeof p.actorId === "string" ? p.actorId : "board";

      const current = await readState(pctx);
      const next: PausedState = {
        paused,
        pausedAt: paused ? new Date().toISOString() : null,
        pausedBy: paused ? by : null,
        pausedReason: paused ? reason : null,
        // Preserve the previous cached summary on a toggle — the UI
        // calls refresh-summary (or the scheduled job does) to recompute.
        summary: current.summary,
      };

      await writeState(pctx, next);

      pctx.logger.info(
        `paperclip-pause: set-paused=${paused} actor=${by} reason=${reason ?? "(none)"}`,
      );

      return { ok: true, paused, pausedAt: next.pausedAt };
    });

    ctx.actions.register(ACTION_KEYS.refreshSummary, async (params: unknown) => {
      const p = (params ?? {}) as Record<string, unknown>;
      const agentsRaw = typeof p.agents === "number" ? p.agents : 0;
      const companiesRaw = typeof p.companies === "number" ? p.companies : 0;
      const current = await readState(pctx);
      const next: PausedState = {
        ...current,
        summary: {
          agents: agentsRaw,
          companies: companiesRaw,
          computedAt: new Date().toISOString(),
        },
      };
      await writeState(pctx, next);
      return { ok: true, summary: next.summary };
    });

    // ---------------------------------------------------------------------
    // Scheduled job
    // ---------------------------------------------------------------------

    ctx.jobs.register(JOB_KEYS.reconcilePausedAgents, async () => {
      const current = await readState(pctx);
      if (!current.paused) return;
      pctx.logger.info(
        `paperclip-pause: heartbeat: paused=${current.paused} pausedAt=${current.pausedAt ?? "(none)"} pausedBy=${current.pausedBy ?? "(unknown)"} summary=${JSON.stringify(current.summary)}`,
      );
    });
  },
});

// Allow running the worker directly via `node ./dist/worker.js` for
// development.
export default pluginInstance;
if (process.argv[1] && process.argv[1].endsWith("worker.js")) {
  runWorker(pluginInstance, import.meta.url);
}
