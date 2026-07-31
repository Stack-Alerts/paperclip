import { useState, type CSSProperties } from "react";
import { useHostContext, usePluginToast } from "@paperclipai/plugin-sdk/ui";
import {
  executeFleetAction,
  type FleetActionResult,
  type FleetOperation,
  type FleetScope,
} from "../fleet.js";

type ControlOption = {
  operation: FleetOperation;
  scope: FleetScope;
  label: string;
  detail: string;
  confirmation: string;
};

const controls: ControlOption[] = [
  {
    operation: "pause",
    scope: "all",
    label: "Pause all",
    detail: "Include CEO and CTO",
    confirmation: "Pause every eligible agent, including CEO and CTO, and cancel active runs?",
  },
  {
    operation: "resume",
    scope: "all",
    label: "Resume all",
    detail: "Include CEO and CTO",
    confirmation: "Resume every paused agent, including CEO and CTO?",
  },
  {
    operation: "pause",
    scope: "without-leadership",
    label: "Pause except CEO/CTO",
    detail: "Keep leadership available",
    confirmation: "Pause every eligible agent except the CEO and CTO, and cancel their active runs?",
  },
  {
    operation: "resume",
    scope: "without-leadership",
    label: "Resume except CEO/CTO",
    detail: "Leave leadership unchanged",
    confirmation: "Resume every paused agent except the CEO and CTO?",
  },
  {
    operation: "resume",
    scope: "ceo-only",
    label: "Resume only CEO",
    detail: "Leave everyone else unchanged",
    confirmation: "Resume the paused CEO and leave every other agent unchanged?",
  },
  {
    operation: "resume",
    scope: "leadership-only",
    label: "Resume only CEO + CTO",
    detail: "Leave all other agents unchanged",
    confirmation: "Resume the paused CEO and CTO and leave every other agent unchanged?",
  },
];

const stackStyle: CSSProperties = {
  display: "grid",
  gap: "0.75rem",
  minWidth: "min(22rem, calc(100vw - 3rem))",
  color: "var(--foreground)",
};

function resultSummary(result: FleetActionResult): string {
  const verb = result.operation === "pause" ? "Paused" : "Resumed";
  const failureSuffix = result.failed.length > 0 ? `; ${result.failed.length} failed` : "";
  return `${verb} ${result.succeeded} of ${result.attempted} targeted agents${failureSuffix}. ${result.skipped.length} skipped.`;
}

export function AgentFleetControlsPopover() {
  const context = useHostContext();
  const toast = usePluginToast();
  const [pending, setPending] = useState<ControlOption | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<FleetActionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function confirmAction() {
    if (!context.companyId || !pending || busy) return;
    setBusy(true);
    setError(null);

    try {
      const nextResult = await executeFleetAction(context.companyId, pending.operation, pending.scope);
      const summary = resultSummary(nextResult);
      setResult(nextResult);
      setPending(null);
      toast({
        title: nextResult.failed.length > 0 ? "Agent controls partially applied" : "Agent controls applied",
        body: summary,
        tone: nextResult.failed.length > 0 ? "warn" : "success",
      });
    } catch (value) {
      const message = value instanceof Error ? value.message : String(value);
      setError(message);
      toast({ title: "Agent controls failed", body: message, tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  if (!context.companyId) {
    return <div style={stackStyle}>Select a company to use agent fleet controls.</div>;
  }

  return (
    <div className="pc-agent-fleet-root" style={stackStyle}>
      <style>{`
        div[role="dialog"]:has(.pc-agent-fleet-root) {
          left: auto !important;
          right: 1rem !important;
          max-width: calc(100vw - 2rem);
        }
        .pc-fleet-option {
          display: grid;
          gap: 2px;
          width: 100%;
          padding: 8px 10px;
          border: 1px solid var(--border);
          border-radius: calc(var(--radius, 0.625rem) - 2px);
          background: var(--background);
          color: var(--foreground);
          text-align: left;
          cursor: pointer;
        }
        .pc-fleet-option:hover { background: var(--accent); color: var(--accent-foreground); }
        .pc-fleet-option:focus-visible, .pc-fleet-confirm:focus-visible {
          outline: 3px solid var(--ring);
          outline-offset: 1px;
        }
        .pc-fleet-confirm {
          min-height: 32px;
          padding: 6px 10px;
          border: 1px solid var(--border);
          border-radius: calc(var(--radius, 0.625rem) - 2px);
          background: var(--background);
          color: var(--foreground);
          cursor: pointer;
        }
        .pc-fleet-confirm[data-primary="true"] { background: var(--primary); color: var(--primary-foreground); }
        .pc-fleet-confirm:disabled { pointer-events: none; opacity: 0.5; }
      `}</style>

      <div>
        <div style={{ fontSize: "0.875rem", fontWeight: 600 }}>Agent fleet controls</div>
        <div style={{ marginTop: "2px", fontSize: "0.75rem", color: "var(--muted-foreground)" }}>
          Company-wide pause and resume controls
        </div>
      </div>

      {pending ? (
        <div style={{ display: "grid", gap: "0.75rem", padding: "0.75rem", border: "1px solid var(--border)", borderRadius: "var(--radius, 0.625rem)", background: "var(--muted)" }}>
          <div>
            <div style={{ fontSize: "0.875rem", fontWeight: 600 }}>{pending.label}</div>
            <div style={{ marginTop: "4px", fontSize: "0.75rem", lineHeight: 1.45, color: "var(--muted-foreground)" }}>
              {pending.confirmation}
            </div>
          </div>
          {error ? <div role="alert" style={{ fontSize: "0.75rem", color: "var(--destructive)" }}>{error}</div> : null}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
            <button className="pc-fleet-confirm" type="button" disabled={busy} onClick={() => setPending(null)}>
              Cancel
            </button>
            <button className="pc-fleet-confirm" data-primary="true" type="button" disabled={busy} onClick={() => void confirmAction()}>
              {busy ? "Applying…" : "Confirm"}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.5rem" }}>
          {controls.map((control) => (
            <button
              className="pc-fleet-option"
              key={`${control.operation}:${control.scope}`}
              type="button"
              onClick={() => {
                setError(null);
                setResult(null);
                setPending(control);
              }}
            >
              <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>{control.label}</span>
              <span style={{ fontSize: "0.6875rem", color: "var(--muted-foreground)" }}>{control.detail}</span>
            </button>
          ))}
        </div>
      )}

      {result ? (
        <div aria-live="polite" style={{ padding: "0.625rem", border: "1px solid var(--border)", borderRadius: "var(--radius, 0.625rem)", fontSize: "0.75rem", background: "var(--muted)" }}>
          <div>{resultSummary(result)}</div>
          {result.failed.length > 0 ? (
            <div style={{ marginTop: "4px", color: "var(--destructive)" }}>
              {result.failed.slice(0, 3).map((failure) => `${failure.name}: ${failure.error}`).join(" · ")}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
