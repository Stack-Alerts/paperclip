import {
  runAutoApply,
  type AutoApplyRec,
  type AutoApplyRequest,
} from './orchestrator';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface IncomingBody {
  strategyId?: unknown;
  recs?: unknown;
  optInDestructiveIds?: unknown;
  strategy?: unknown;
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

  const req: AutoApplyRequest = {
    strategyId: body.strategyId,
    recs,
    optInDestructiveIds:
      body.optInDestructiveIds === undefined
        ? null
        : (body.optInDestructiveIds as string[] | null),
    strategy: (body.strategy as AutoApplyRequest['strategy']) ?? null,
  };

  const result = await runAutoApply(req);
  return Response.json(result);
}
