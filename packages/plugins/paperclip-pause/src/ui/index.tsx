// src/ui/index.tsx — paperclip-pause plugin UI
//
// The host renders this file at `./dist/ui/index.js`. It exports a
// `PauseRunButton` React function component matching the manifest's
// `slots[0].exportName`. The host's plugin slot system auto-registers
// the exported function via `registerPluginReactComponent` on bundle
// load, so we DO NOT call that function ourselves here.
//
// The button is intentionally self-contained:
//   - Reads the current pause flag via `usePluginData("state")`.
//   - Calls the plugin's `set-paused` action with `{paused: <new value>}`.
//   - When the user clicks "Pause", the UI also POSTs to the host's
//     `POST /api/agents/:id/pause` for each agent in the current company
//     (using the existing browser session) — that's how the fleet actually
//     pauses. The plugin worker only tracks the source-of-truth flag;
//     the heartbeat already skips dispatch when `paused_at` is set.
//
// When the system is paused, the button switches to "Run" (a single click
// resumes), and a subtle red "PAUSED" indicator is rendered next to it.
// On every render we re-pull `state` (cheap 5s poll) so multiple tabs
// stay in sync.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  usePluginData,
  usePluginAction,
  useHostContext,
  type PluginHostContext,
} from "@paperclipai/plugin-sdk/ui";

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

async function postAgentPause(agentId: string, paused: boolean) {
  const path = `/api/agents/${encodeURIComponent(agentId)}/${paused ? "pause" : "resume"}`;
  return fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: "{}",
  });
}

async function listAgentsForCompany(companyId: string) {
  const r = await fetch(
    `/api/companies/${encodeURIComponent(companyId)}/agents?limit=500`,
    { credentials: "include", headers: { Accept: "application/json" } },
  );
  if (!r.ok) return [];
  const json = (await r.json()) as { items?: Array<{ id: string }> };
  return Array.isArray(json.items) ? json.items : [];
}

function formatRelative(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.round(secs / 60)}m ago`;
  return `${Math.round(secs / 3600)}h ago`;
}

export function PauseRunButton({ context }: { context: PluginHostContext }) {
  const host = useHostContext();
  const companyId = host.companyId ?? context.companyId ?? null;

  // Re-poll every 5s so multiple tabs / the top bar stay in sync after
  // a different tab toggles the flag.
  const [pollTick, setPollTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setPollTick((n) => n + 1), 5_000);
    return () => clearInterval(t);
  }, []);

  const stateResult = usePluginData("state", { _tick: pollTick });
  const setPaused = usePluginAction("set-paused");
  const refreshSummary = usePluginAction("refresh-summary");

  const state: PausedState = useMemo(() => {
    const data = stateResult && stateResult.data;
    return data && typeof data === "object" ? (data as PausedState) : DEFAULT_STATE;
  }, [stateResult]);

  const [busy, setBusy] = useState<"pause" | "run" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const applyToFleet = useCallback(
    async (paused: boolean) => {
      setError(null);
      if (!companyId) {
        return { okCount: 0, failCount: 0, companies: 0 };
      }
      try {
        const agents = await listAgentsForCompany(companyId);
        if (agents.length === 0) {
          return { okCount: 0, failCount: 0, companies: 1 };
        }
        let okCount = 0;
        let failCount = 0;
        await Promise.all(
          agents.map(async (a) => {
            try {
              const r = await postAgentPause(a.id, paused);
              if (r.ok) okCount++;
              else failCount++;
            } catch {
              failCount++;
            }
          }),
        );
        return { okCount, failCount, companies: 1 };
      } catch (e) {
        setError((e as Error)?.message ?? "Failed to apply pause to fleet");
        return { okCount: 0, failCount: 0, companies: 0 };
      }
    },
    [companyId],
  );

  const onToggle = useCallback(async () => {
    if (busy) return;
    const next = !state.paused;
    setBusy(next ? "pause" : "run");
    try {
      // 1. Flip the source-of-truth flag via the plugin worker.
      await setPaused({
        companyId: companyId ?? undefined,
        paused: next,
        actorId: host.userId ?? "board",
        reason: "Top-bar Pause/Run toggle",
      });
      // 2. Apply to the fleet via the host's existing agent pause endpoints.
      const summary = await applyToFleet(next);
      // 3. Tell the worker to refresh the cached counts so the next /state
      //    poll reflects what actually happened on the host side.
      await refreshSummary({
        companyId: companyId ?? undefined,
        agents: summary.okCount,
        companies: summary.companies ?? 0,
      });
    } catch (e) {
      setError((e as Error)?.message ?? "Failed to toggle pause state");
    } finally {
      setBusy(null);
    }
  }, [busy, state.paused, companyId, host.userId, setPaused, applyToFleet, refreshSummary]);

  // Clear error after a few seconds.
  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 5000);
    return () => clearTimeout(t);
  }, [error]);

  const buttonLabel = state.paused ? "Run" : "Pause";
  const buttonColor = state.paused ? "#16a34a" : "#dc2626";
  const buttonHover = state.paused ? "#15803d" : "#b91c1c";

  const subtitle =
    state.paused && state.summary.agents > 0
      ? `${state.summary.agents} agent${state.summary.agents === 1 ? "" : "s"} paused`
      : state.paused
        ? "Pause requested"
        : state.summary.agents > 0
          ? `${state.summary.agents} agent${state.summary.agents === 1 ? "" : "s"} active`
          : "";

  return (
    <div
      data-testid="pause-run-button"
      data-paused={state.paused ? "true" : "false"}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        marginLeft: 8,
      }}
      title={
        state.paused
          ? `System paused${state.pausedAt ? " " + formatRelative(state.pausedAt) : ""}${state.pausedBy ? " by " + state.pausedBy : ""}`
          : "System running — click Pause to halt agent dispatch (running agents continue their in-flight work)"
      }
    >
      {state.paused ? (
        <span
          aria-hidden="true"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            padding: "2px 8px",
            borderRadius: 9999,
            background: "rgba(220, 38, 38, 0.12)",
            color: "#dc2626",
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: 0.4,
            textTransform: "uppercase",
          }}
        >
          <span style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#dc2626",
          }} />
          Paused
        </span>
      ) : null}
      <button
        type="button"
        onClick={onToggle}
        disabled={busy !== null}
        aria-pressed={state.paused}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 10px",
          borderRadius: 6,
          background: busy !== null ? "#9ca3af" : buttonColor,
          color: "#fff",
          border: "1px solid transparent",
          fontSize: 12,
          fontWeight: 600,
          cursor: busy !== null ? "wait" : "pointer",
          transition: "background 120ms ease",
          whiteSpace: "nowrap",
        }}
        onMouseEnter={(e) => {
          if (busy === null) (e.currentTarget as HTMLButtonElement).style.background = buttonHover;
        }}
        onMouseLeave={(e) => {
          if (busy === null) (e.currentTarget as HTMLButtonElement).style.background = buttonColor;
        }}
      >
        {busy === "pause" ? "Pausing…" : busy === "run" ? "Resuming…" : buttonLabel}
      </button>
      {subtitle ? (
        <span style={{ fontSize: 11, color: "var(--muted-foreground, #6b7280)" }}>
          {subtitle}
        </span>
      ) : null}
      {error ? (
        <span
          role="alert"
          style={{ fontSize: 11, color: "#dc2626", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
          title={error}
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}

export default PauseRunButton;
