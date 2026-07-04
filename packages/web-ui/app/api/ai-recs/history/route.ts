import {
  readRecords,
  writeRecords,
  SCHEMA_VERSION,
  type AiRecsHistoryEntry,
} from '@/lib/ai-recs/historyStore';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(): Promise<Response> {
  const records = await readRecords();
  return Response.json({ ok: true, schema_version: SCHEMA_VERSION, records });
}

interface IncomingBody {
  records?: unknown;
}

export async function PUT(request: Request): Promise<Response> {
  let body: IncomingBody;
  try {
    body = (await request.json()) as IncomingBody;
  } catch {
    return Response.json(
      { ok: false, error: 'Invalid request body.' },
      { status: 400 },
    );
  }

  if (!Array.isArray(body.records)) {
    return Response.json(
      { ok: false, error: 'records must be an array.' },
      { status: 400 },
    );
  }

  const records = await writeRecords(body.records as AiRecsHistoryEntry[]);
  return Response.json({ ok: true, schema_version: SCHEMA_VERSION, records });
}
