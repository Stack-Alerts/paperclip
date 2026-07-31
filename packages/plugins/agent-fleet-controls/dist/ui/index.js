// src/ui/index.tsx
import { useState } from "react";
import { useHostContext, usePluginToast } from "@paperclipai/plugin-sdk/ui";

// src/fleet.ts
function errorMessage(value) {
  if (value instanceof Error) return value.message;
  return String(value);
}
var browserRequest = async (path, init) => {
  const headers = new Headers(init?.headers);
  if (init?.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`/api${path}`, {
    ...init,
    headers,
    credentials: "include"
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = typeof body?.error === "string" ? body.error : `Request failed: ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) return void 0;
  return response.json();
};
function planFleetAction(agents, operation, scope) {
  const selected = [];
  const skipped = [];
  for (const agent of agents) {
    const isCeo = agent.role === "ceo";
    const isLeadership = isCeo || agent.role === "cto";
    const isInScope = scope === "all" || scope === "without-leadership" && !isLeadership || scope === "ceo-only" && isCeo || scope === "leadership-only" && isLeadership;
    if (!isInScope) {
      skipped.push({
        id: agent.id,
        name: agent.name,
        reason: scope === "without-leadership" ? "leadership-excluded" : "outside-scope"
      });
      continue;
    }
    if (operation === "pause") {
      if (agent.status === "paused") {
        skipped.push({ id: agent.id, name: agent.name, reason: "already-paused" });
      } else if (agent.status === "terminated") {
        skipped.push({ id: agent.id, name: agent.name, reason: "terminated" });
      } else if (agent.status === "pending_approval") {
        skipped.push({ id: agent.id, name: agent.name, reason: "pending-approval" });
      } else {
        selected.push(agent);
      }
      continue;
    }
    if (agent.status === "paused") {
      selected.push(agent);
    } else {
      skipped.push({
        id: agent.id,
        name: agent.name,
        reason: agent.status === "terminated" ? "terminated" : "not-paused"
      });
    }
  }
  return { selected, skipped };
}
async function executeFleetAction(companyId, operation, scope, request = browserRequest, concurrency = 8) {
  const agents = await request(`/companies/${encodeURIComponent(companyId)}/agents`);
  const plan = planFleetAction(agents, operation, scope);
  const failed = [];
  let succeeded = 0;
  const batchSize = Math.max(1, Math.floor(concurrency));
  for (let index = 0; index < plan.selected.length; index += batchSize) {
    const batch = plan.selected.slice(index, index + batchSize);
    const results = await Promise.allSettled(
      batch.map((agent) => request(
        `/agents/${encodeURIComponent(agent.id)}/${operation}?companyId=${encodeURIComponent(companyId)}`,
        { method: "POST", body: "{}" }
      ))
    );
    results.forEach((result, resultIndex) => {
      const agent = batch[resultIndex];
      if (result.status === "fulfilled") {
        succeeded += 1;
      } else {
        failed.push({ id: agent.id, name: agent.name, error: errorMessage(result.reason) });
      }
    });
  }
  return {
    operation,
    scope,
    attempted: plan.selected.length,
    succeeded,
    skipped: plan.skipped,
    failed
  };
}

// src/ui/index.tsx
import { jsx, jsxs } from "react/jsx-runtime";
var controls = [
  {
    operation: "pause",
    scope: "all",
    label: "Pause all",
    detail: "Include CEO and CTO",
    confirmation: "Pause every eligible agent, including CEO and CTO, and cancel active runs?"
  },
  {
    operation: "resume",
    scope: "all",
    label: "Resume all",
    detail: "Include CEO and CTO",
    confirmation: "Resume every paused agent, including CEO and CTO?"
  },
  {
    operation: "pause",
    scope: "without-leadership",
    label: "Pause except CEO/CTO",
    detail: "Keep leadership available",
    confirmation: "Pause every eligible agent except the CEO and CTO, and cancel their active runs?"
  },
  {
    operation: "resume",
    scope: "without-leadership",
    label: "Resume except CEO/CTO",
    detail: "Leave leadership unchanged",
    confirmation: "Resume every paused agent except the CEO and CTO?"
  },
  {
    operation: "resume",
    scope: "ceo-only",
    label: "Resume only CEO",
    detail: "Leave everyone else unchanged",
    confirmation: "Resume the paused CEO and leave every other agent unchanged?"
  },
  {
    operation: "resume",
    scope: "leadership-only",
    label: "Resume only CEO + CTO",
    detail: "Leave all other agents unchanged",
    confirmation: "Resume the paused CEO and CTO and leave every other agent unchanged?"
  }
];
var stackStyle = {
  display: "grid",
  gap: "0.75rem",
  minWidth: "min(22rem, calc(100vw - 3rem))",
  color: "var(--foreground)"
};
function resultSummary(result) {
  const verb = result.operation === "pause" ? "Paused" : "Resumed";
  const failureSuffix = result.failed.length > 0 ? `; ${result.failed.length} failed` : "";
  return `${verb} ${result.succeeded} of ${result.attempted} targeted agents${failureSuffix}. ${result.skipped.length} skipped.`;
}
function AgentFleetControlsPopover() {
  const context = useHostContext();
  const toast = usePluginToast();
  const [pending, setPending] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
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
        tone: nextResult.failed.length > 0 ? "warn" : "success"
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
    return /* @__PURE__ */ jsx("div", { style: stackStyle, children: "Select a company to use agent fleet controls." });
  }
  return /* @__PURE__ */ jsxs("div", { className: "pc-agent-fleet-root", style: stackStyle, children: [
    /* @__PURE__ */ jsx("style", { children: `
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
      ` }),
    /* @__PURE__ */ jsxs("div", { children: [
      /* @__PURE__ */ jsx("div", { style: { fontSize: "0.875rem", fontWeight: 600 }, children: "Agent fleet controls" }),
      /* @__PURE__ */ jsx("div", { style: { marginTop: "2px", fontSize: "0.75rem", color: "var(--muted-foreground)" }, children: "Company-wide pause and resume controls" })
    ] }),
    pending ? /* @__PURE__ */ jsxs("div", { style: { display: "grid", gap: "0.75rem", padding: "0.75rem", border: "1px solid var(--border)", borderRadius: "var(--radius, 0.625rem)", background: "var(--muted)" }, children: [
      /* @__PURE__ */ jsxs("div", { children: [
        /* @__PURE__ */ jsx("div", { style: { fontSize: "0.875rem", fontWeight: 600 }, children: pending.label }),
        /* @__PURE__ */ jsx("div", { style: { marginTop: "4px", fontSize: "0.75rem", lineHeight: 1.45, color: "var(--muted-foreground)" }, children: pending.confirmation })
      ] }),
      error ? /* @__PURE__ */ jsx("div", { role: "alert", style: { fontSize: "0.75rem", color: "var(--destructive)" }, children: error }) : null,
      /* @__PURE__ */ jsxs("div", { style: { display: "flex", justifyContent: "flex-end", gap: "0.5rem" }, children: [
        /* @__PURE__ */ jsx("button", { className: "pc-fleet-confirm", type: "button", disabled: busy, onClick: () => setPending(null), children: "Cancel" }),
        /* @__PURE__ */ jsx("button", { className: "pc-fleet-confirm", "data-primary": "true", type: "button", disabled: busy, onClick: () => void confirmAction(), children: busy ? "Applying\u2026" : "Confirm" })
      ] })
    ] }) : /* @__PURE__ */ jsx("div", { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.5rem" }, children: controls.map((control) => /* @__PURE__ */ jsxs(
      "button",
      {
        className: "pc-fleet-option",
        type: "button",
        onClick: () => {
          setError(null);
          setResult(null);
          setPending(control);
        },
        children: [
          /* @__PURE__ */ jsx("span", { style: { fontSize: "0.75rem", fontWeight: 600 }, children: control.label }),
          /* @__PURE__ */ jsx("span", { style: { fontSize: "0.6875rem", color: "var(--muted-foreground)" }, children: control.detail })
        ]
      },
      `${control.operation}:${control.scope}`
    )) }),
    result ? /* @__PURE__ */ jsxs("div", { "aria-live": "polite", style: { padding: "0.625rem", border: "1px solid var(--border)", borderRadius: "var(--radius, 0.625rem)", fontSize: "0.75rem", background: "var(--muted)" }, children: [
      /* @__PURE__ */ jsx("div", { children: resultSummary(result) }),
      result.failed.length > 0 ? /* @__PURE__ */ jsx("div", { style: { marginTop: "4px", color: "var(--destructive)" }, children: result.failed.slice(0, 3).map((failure) => `${failure.name}: ${failure.error}`).join(" \xB7 ") }) : null
    ] }) : null
  ] });
}
export {
  AgentFleetControlsPopover
};
//# sourceMappingURL=index.js.map
