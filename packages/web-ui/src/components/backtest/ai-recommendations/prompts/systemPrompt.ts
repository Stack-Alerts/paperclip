import { BlockType, type Block, type Strategy } from '@/lib/strategy-builder/types';
import { ALL_BLOCK_TYPES } from '@/lib/strategy-builder/blockTypeVocabulary';

// BTC/crypto context line — anchored so snapshot tests and history entries
// can detect "did the prompt include domain context?" without parsing prose.
const BTC_CRYPTO_CONTEXT =
  'You are analyzing a BTC (Bitcoin) and broader crypto-market trading strategy backtest.';

// Hard cap on the number of recommendations the AI should return.
// Stream 4 (BTC-36465 / BTC-38465): keep the user-facing recs grid to <= 3
// actionable items so the Approve & Apply flow stays reviewable.
const MAX_RECOMMENDATIONS = 3;

// The canonical block-type vocabulary lives in
// `@/lib/strategy-builder/blockTypeVocabulary` (sourced from the BlockType
// enum). Both this dynamic prompt and the static analyze SYSTEM_PROMPT draw
// from that one list so ADD_BLOCK suggestions always name a matchable type
// (BTCAAAAA-38730). We list every supported type so the AI knows the universe
// of building blocks it can recommend; the runtime strategy may only use a
// subset — those get surfaced as the "actually-used" list further down.
const ALL_SUPPORTED_BLOCK_TYPES: readonly BlockType[] = ALL_BLOCK_TYPES;

// BlockLibrary entries come back from `/api/strategy-builder/block-library` as
// `unknown[]` in the panel (deliberately loosely typed); we only need the
// `type` and `name` fields for the prompt. We accept `unknown[]` so callers
// don't have to pre-narrow the catalog before constructing the prompt.
interface BlockCatalogEntry {
  type?: unknown;
  name?: unknown;
}

function extractUsedBlockTypes(strategy: Strategy | null | undefined): BlockType[] {
  if (!strategy?.blocks || strategy.blocks.length === 0) return [];
  const seen = new Set<BlockType>();
  for (const block of strategy.blocks as Block[]) {
    if (block && typeof block === 'object' && 'type' in block) {
      const t = (block as { type: unknown }).type;
      if (typeof t === 'string' && (ALL_SUPPORTED_BLOCK_TYPES as string[]).includes(t)) {
        seen.add(t as BlockType);
      }
    }
  }
  return Array.from(seen);
}

function extractParameterKeys(strategy: Strategy | null | undefined): string[] {
  if (!strategy?.blocks || strategy.blocks.length === 0) return [];
  const seen = new Set<string>();
  for (const block of strategy.blocks as Block[]) {
    const data = (block as Block | undefined)?.data;
    if (data && typeof data === 'object') {
      for (const key of Object.keys(data as Record<string, unknown>)) {
        if (key.length > 0) seen.add(key);
      }
    }
  }
  return Array.from(seen);
}

function extractCatalogBlockTypes(blockCatalog: unknown[] | null | undefined): string[] {
  if (!Array.isArray(blockCatalog)) return [];
  const seen = new Set<string>();
  for (const entry of blockCatalog as BlockCatalogEntry[]) {
    const t = entry?.type;
    if (typeof t === 'string' && t.length > 0) seen.add(t);
  }
  return Array.from(seen);
}

function unique<T>(items: T[]): T[] {
  return Array.from(new Set(items));
}

export interface BuildAiRecsSystemPromptOptions {
  strategy: Strategy | null | undefined;
  blockCatalog: unknown[] | null | undefined;
}

/**
 * Build the system prompt that frames the AI's analysis of a backtest.
 *
 * Stream 4 (BTC-36465 / BTC-38465) improvements over the previous
 * constant string:
 *   1. Anchors the AI in the BTC / crypto trading domain so generic
 *      "stocks" framing does not leak into the diagnosis.
 *   2. Lists every supported building-block type so the AI knows the
 *      full vocabulary it can recommend (and we surface the catalog
 *      and currently-used subset).
 *   3. Requires parameter names to be spelled EXACTLY as they appear
 *      in the strategy's `blocks[].data` keys — no synonyms, no
 *      re-casing — so the auto-apply path can match them.
 *   4. Caps the recommendation list at `MAX_RECOMMENDATIONS` (3) so
 *      the recs grid stays reviewable.
 *
 * Pure / deterministic — no I/O, no time, no randomness — so the
 * snapshot tests can pin the exact output.
 */
export function buildAiRecsSystemPrompt({
  strategy,
  blockCatalog,
}: BuildAiRecsSystemPromptOptions): string {
  const supportedTypes = unique([
    ...ALL_SUPPORTED_BLOCK_TYPES,
    ...extractCatalogBlockTypes(blockCatalog),
  ]);
  const usedTypes = extractUsedBlockTypes(strategy);
  const parameterKeys = extractParameterKeys(strategy);

  const supportedList = supportedTypes.length > 0 ? supportedTypes.join(', ') : '(none)';
  const usedList = usedTypes.length > 0 ? usedTypes.join(', ') : '(none)';
  const paramList = parameterKeys.length > 0 ? parameterKeys.join(', ') : '(none)';

  return [
    BTC_CRYPTO_CONTEXT,
    '',
    'Analyze the strategy backtest below and return:',
    '  1) A short DIAGNOSIS explaining the dominant behaviour, the strongest',
    '     weakness, and the most important risk in the backtest.',
    `  2) Up to ${MAX_RECOMMENDATIONS} RECOMMENDATIONS ranked by impact. Each`,
    '     recommendation must be a single concrete change.',
    '',
    'Constraints:',
    '- Recommend only building blocks from this supported vocabulary:',
    `    ${supportedList}`,
    '- When recommending a parameter change, spell the parameter name',
    '  EXACTLY as it appears in the strategy\'s `data` keys below. Do not',
    '  re-case, abbreviate, or use synonyms — the auto-apply path keys off',
    '  the literal parameter name.',
    '- Parameter names available in this strategy:',
    `    ${paramList}`,
    '- Building blocks actually used by this strategy:',
    `    ${usedList}`,
    '- When the payload includes a performance_attribution object, base your',
    '  diagnosis and recommendations on it: cite metric_divergence when the',
    '  reported and per-entry numbers disagree, and target the entry signal,',
    '  block, or exit reason that gated the most trades or drove the most PnL',
    '  rather than defaulting to generic "widen SL / reduce hold" advice.',
    `- Return at most ${MAX_RECOMMENDATIONS} recommendations.`,
  ].join('\n');
}