import { BlockType } from './types';

// Canonical, ordered list of every building-block type the strategy builder
// supports. The `BlockType` enum in ./types is the single source of truth for
// block-type identifiers (they are the literal `type` field on every block and
// on the /api/strategy-builder/block-library catalog entries). Both AI-recs
// prompts — the static analyze SYSTEM_PROMPT and the dynamic
// buildAiRecsSystemPrompt — MUST draw their block vocabulary from this one
// list so an ADD_BLOCK suggestion always names a type the auto-apply path can
// match (BTCAAAAA-38730).
export const ALL_BLOCK_TYPES: readonly BlockType[] = [
  BlockType.ENTRY_CONDITION,
  BlockType.EXIT_CONDITION,
  BlockType.RISK_MANAGEMENT,
  BlockType.TIME_CONSTRAINT,
  BlockType.FILTER,
  BlockType.INDICATOR,
  BlockType.POSITION_SIZING,
];

// Comma-joined canonical vocabulary for embedding directly in an AI prompt.
export const BLOCK_TYPE_VOCABULARY = ALL_BLOCK_TYPES.join(', ');
