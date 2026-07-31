export type FleetOperation = "pause" | "resume";
export type FleetScope = "all" | "without-leadership" | "ceo-only" | "leadership-only";

export interface FleetAgent {
  id: string;
  name: string;
  role: string;
  status: string;
}

export interface FleetSkip {
  id: string;
  name: string;
  reason: "leadership-excluded" | "outside-scope" | "already-paused" | "not-paused" | "pending-approval" | "terminated";
}

export interface FleetFailure {
  id: string;
  name: string;
  error: string;
}

export interface FleetActionPlan {
  selected: FleetAgent[];
  skipped: FleetSkip[];
}

export interface FleetActionResult {
  operation: FleetOperation;
  scope: FleetScope;
  attempted: number;
  succeeded: number;
  skipped: FleetSkip[];
  failed: FleetFailure[];
}

export type FleetRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

function errorMessage(value: unknown): string {
  if (value instanceof Error) return value.message;
  return String(value);
}

export const browserRequest: FleetRequest = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const headers = new Headers(init?.headers);
  if (init?.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: unknown } | null;
    const message = typeof body?.error === "string" ? body.error : `Request failed: ${response.status}`;
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
};

export function planFleetAction(
  agents: FleetAgent[],
  operation: FleetOperation,
  scope: FleetScope,
): FleetActionPlan {
  const selected: FleetAgent[] = [];
  const skipped: FleetSkip[] = [];

  for (const agent of agents) {
    const isCeo = agent.role === "ceo";
    const isLeadership = isCeo || agent.role === "cto";
    const isInScope = scope === "all"
      || (scope === "without-leadership" && !isLeadership)
      || (scope === "ceo-only" && isCeo)
      || (scope === "leadership-only" && isLeadership);

    if (!isInScope) {
      skipped.push({
        id: agent.id,
        name: agent.name,
        reason: scope === "without-leadership" ? "leadership-excluded" : "outside-scope",
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
        reason: agent.status === "terminated" ? "terminated" : "not-paused",
      });
    }
  }

  return { selected, skipped };
}

export async function executeFleetAction(
  companyId: string,
  operation: FleetOperation,
  scope: FleetScope,
  request: FleetRequest = browserRequest,
  concurrency = 8,
): Promise<FleetActionResult> {
  const agents = await request<FleetAgent[]>(`/companies/${encodeURIComponent(companyId)}/agents`);
  const plan = planFleetAction(agents, operation, scope);
  const failed: FleetFailure[] = [];
  let succeeded = 0;
  const batchSize = Math.max(1, Math.floor(concurrency));

  for (let index = 0; index < plan.selected.length; index += batchSize) {
    const batch = plan.selected.slice(index, index + batchSize);
    const results = await Promise.allSettled(
      batch.map((agent) => request(
        `/agents/${encodeURIComponent(agent.id)}/${operation}?companyId=${encodeURIComponent(companyId)}`,
        { method: "POST", body: "{}" },
      )),
    );

    results.forEach((result, resultIndex) => {
      const agent = batch[resultIndex]!;
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
    failed,
  };
}
