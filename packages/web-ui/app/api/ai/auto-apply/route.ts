import {
  runAutoApply,
  type AutoApplyRec,
  type AutoApplyRequest,
} from './orchestrator';

// Server-side proxy — must run on Node so the global fetch can reach
// the FastAPI service on the host network.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const DEFAULT_BASE_URL = 'http://localhost:8765';

interface IncomingBody {
  strategyId?: unknown;
  recs?: unknown;
  optInDestructiveIds?: unknown;
}

function isRecArray(value: unknown): value is AutoApplyRec[] {
  if (!Array.isArray(value)) return false;
  return value.every(
    (item) =>
      item &&
      typeof item === 'object' &&
      typeof (item as { rec_id?: unknown }).rec_id === 'string' &&
      typeof (item as { type?: unknown }).type === 'string',
  );
}

function isStringArrayOrNull(value: unknown): value is string[] | null {
  if (value === null) return true;
  if (!Array.isArray(value)) return false;
  return value.every((item) => typeof item === 'string');
}

export async function POST(request: Request): Promise<Response> {
  let body: IncomingBody;
  try {
    body = (await request.json()) as IncomingBody;
  } catch {
    return Response.json(
      { ok: false, error: 'Invalid request body.' },
      { status: 400 },
    );
  }

  if (typeof body.strategyId !== 'string' || body.strategyId.length === 0) {
    return Response.json(
      { ok: false, error: 'Missing strategyId.' },
      { status: 400 },
    );
  }

  let recs: AutoApplyRec[];
  if (!Array.isArray(body.recs)) {
    recs = [];
  } else if (isRecArray(body.recs)) {
    recs = body.recs;
  } else {
    return Response.json(
      { ok: false, error: 'recs must be an array of { rec_id, type, ... }.' },
      { status: 400 },
    );
  }

  if (
    body.optInDestructiveIds !== undefined &&
    body.optInDestructiveIds !== null &&
    !isStringArrayOrNull(body.optInDestructiveIds)
  ) {
    return Response.json(
      { ok: false, error: 'optInDestructiveIds must be string[] | null.' },
      { status: 400 },
    );
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_BASE_URL;
  const req: AutoApplyRequest = {
    strategyId: body.strategyId,
    recs,
    optInDestructiveIds:
      body.optInDestructiveIds === undefined
        ? null
        : (body.optInDestructiveIds as string[] | null),
  };

  // Forward the caller's JWT so FastAPI's Depends(require_jwt) accepts the
  // request. We pass the raw header through unchanged — Next.js hands us
  // whatever the client sent (typically "Bearer eyJ...").
  const authHeader = request.headers.get('authorization');

  const result = await runAutoApply(req, { fetch, baseUrl, authHeader });
  return Response.json(result);
}
