import type { Response } from "express";

const BTC_PREFIX_TOKEN_RE = /\bBTC-(\d{1,6})\b/g;
export const BTC_FULL_PREFIX = "BTCAAAAA";

export type BtcPrefixActorContext = {
  type?: string;
  companyId?: string | null;
  companyIds?: string[] | null;
};

export type BtcPrefixLookup = (
  fullIdentifier: string,
  companyId: string,
) => Promise<{ exists: boolean } | null>;

export type BtcPrefixGuardResult =
  | { ok: true }
  | {
      ok: false;
      offendingToken: string;
      suggestedFull: string;
      actorCompanyId: string;
    };

export function extractBtcPrefixTokens(text: string | null | undefined): string[] {
  if (typeof text !== "string" || text.length === 0) return [];
  const out: string[] = [];
  for (const match of text.matchAll(BTC_PREFIX_TOKEN_RE)) {
    out.push(match[0]);
  }
  return out;
}

export function pickActorCompanyId(actor: BtcPrefixActorContext | null | undefined): string | null {
  if (!actor) return null;
  if (typeof actor.companyId === "string" && actor.companyId.length > 0) return actor.companyId;
  if (Array.isArray(actor.companyIds) && actor.companyIds.length > 0) {
    const first = actor.companyIds[0];
    if (typeof first === "string" && first.length > 0) return first;
  }
  return null;
}

export function suggestedFullForm(token: string, fullPrefix: string = BTC_FULL_PREFIX): string | null {
  const numeric = /^BTC-(\d{1,6})$/.exec(token)?.[1];
  if (!numeric) return null;
  return `${fullPrefix}-${numeric}`;
}

export async function enforceBtcPrefixTokens(params: {
  text: string | null | undefined;
  /** Explicit company scope for validation. Takes precedence over actor when set. */
  companyId?: string | null;
  actor?: BtcPrefixActorContext | null | undefined;
  lookup: BtcPrefixLookup;
  fullPrefix?: string;
}): Promise<BtcPrefixGuardResult> {
  const { text, lookup } = params;
  const fullPrefix = params.fullPrefix ?? BTC_FULL_PREFIX;
  const tokens = extractBtcPrefixTokens(text);
  if (tokens.length === 0) return { ok: true };

  const companyId =
    typeof params.companyId === "string" && params.companyId.length > 0
      ? params.companyId
      : pickActorCompanyId(params.actor);
  if (!companyId) {
    return { ok: true };
  }

  const candidates: Array<{ token: string; candidate: string }> = [];
  for (const token of tokens) {
    const candidate = suggestedFullForm(token, fullPrefix);
    if (!candidate) continue;
    if (candidates.some((c) => c.candidate === candidate)) continue;
    candidates.push({ token, candidate });
  }
  if (candidates.length === 0) return { ok: true };

  const results = await Promise.all(
    candidates.map(async (c) => ({ c, res: await lookup(c.candidate, companyId) })),
  );
  for (const { c, res } of results) {
    if (!res || !res.exists) {
      return {
        ok: false,
        offendingToken: c.token,
        suggestedFull: c.candidate,
        actorCompanyId: companyId,
      };
    }
  }
  return { ok: true };
}

export function respondBtcPrefixGuardFailure(
  res: Response,
  result: Extract<BtcPrefixGuardResult, { ok: false }>,
) {
  res.status(422).json({
    error: "Truncated prefix",
    message: `Comment contains '${result.offendingToken}' which does not resolve to a real identifier in this company. Use the full '${result.suggestedFull}' form.`,
    details: {
      offendingToken: result.offendingToken,
      suggestedFull: result.suggestedFull,
      companyId: result.actorCompanyId,
    },
  });
}