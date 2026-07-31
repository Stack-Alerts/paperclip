import { describe, expect, it } from "vitest";
import manifest from "../src/manifest.js";
import {
  executeFleetAction,
  planFleetAction,
  type FleetAgent,
  type FleetRequest,
} from "../src/fleet.js";

const agents: FleetAgent[] = [
  { id: "ceo-1", name: "CEO", role: "ceo", status: "running" },
  { id: "cto-1", name: "CTO", role: "cto", status: "idle" },
  { id: "eng-1", name: "Engineer", role: "engineer", status: "running" },
  { id: "qa-1", name: "QA", role: "qa", status: "paused" },
  { id: "old-1", name: "Former Agent", role: "general", status: "terminated" },
  { id: "new-1", name: "Pending Agent", role: "general", status: "pending_approval" },
];

describe("agent fleet controls", () => {
  it("registers a compact global toolbar popover", () => {
    expect(manifest.version).toBe("0.1.2");
    expect(manifest.capabilities).toEqual(["ui.action.register"]);
    expect(manifest.ui?.launchers).toEqual([
      expect.objectContaining({
        placementZone: "globalToolbarButton",
        action: { type: "openPopover", target: "AgentFleetControlsPopover" },
        render: { environment: "hostOverlay", bounds: "compact" },
      }),
    ]);
  });

  it("includes CEO and CTO in all-agent pause actions", () => {
    const plan = planFleetAction(agents, "pause", "all");
    expect(plan.selected.map((agent) => agent.id)).toEqual(["ceo-1", "cto-1", "eng-1"]);
    expect(plan.skipped.map((agent) => agent.reason)).toEqual([
      "already-paused",
      "terminated",
      "pending-approval",
    ]);
  });

  it("excludes CEO and CTO while still selecting paused workers for resume", () => {
    const plan = planFleetAction(agents, "resume", "without-leadership");
    expect(plan.selected.map((agent) => agent.id)).toEqual(["qa-1"]);
    expect(plan.skipped.filter((agent) => agent.reason === "leadership-excluded").map((agent) => agent.id)).toEqual([
      "ceo-1",
      "cto-1",
    ]);
  });

  it("can resume only the CEO or only the CEO and CTO", () => {
    const pausedLeadership = agents.map((agent) =>
      agent.role === "ceo" || agent.role === "cto" ? { ...agent, status: "paused" } : agent,
    );

    const ceoPlan = planFleetAction(pausedLeadership, "resume", "ceo-only");
    const leadershipPlan = planFleetAction(pausedLeadership, "resume", "leadership-only");

    expect(ceoPlan.selected.map((agent) => agent.id)).toEqual(["ceo-1"]);
    expect(leadershipPlan.selected.map((agent) => agent.id)).toEqual(["ceo-1", "cto-1"]);
    expect(leadershipPlan.skipped.filter((agent) => agent.reason === "outside-scope")).toHaveLength(4);
  });

  it("continues a mass action after individual failures", async () => {
    const paths: string[] = [];
    const request: FleetRequest = async <T>(path: string, init?: RequestInit): Promise<T> => {
      paths.push(`${init?.method ?? "GET"} ${path}`);
      if (init?.method == null) return agents as T;
      if (path.includes("eng-1")) throw new Error("cancel timed out");
      return { ok: true } as T;
    };

    const result = await executeFleetAction("company-1", "pause", "all", request, 2);

    expect(paths).toEqual([
      "GET /companies/company-1/agents",
      "POST /agents/ceo-1/pause?companyId=company-1",
      "POST /agents/cto-1/pause?companyId=company-1",
      "POST /agents/eng-1/pause?companyId=company-1",
    ]);
    expect(result).toMatchObject({ attempted: 3, succeeded: 2 });
    expect(result.failed).toEqual([{ id: "eng-1", name: "Engineer", error: "cancel timed out" }]);
  });
});
