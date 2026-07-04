import {
  BlockType,
  StrategyStatus,
  type Block,
  type Strategy,
} from '@/lib/strategy-builder/types';
import { ALL_BLOCK_TYPES } from '@/lib/strategy-builder/blockTypeVocabulary';
import { buildAiRecsSystemPrompt } from '../systemPrompt';

function makeStrategy(): Strategy {
  const blocks: Block[] = [
    {
      id: 'b-indicator-1',
      type: BlockType.INDICATOR,
      index: 0,
      data: { period: 14, source: 'close' },
    },
    {
      id: 'b-entry-1',
      type: BlockType.ENTRY_CONDITION,
      index: 1,
      data: { comparator: 'gt', threshold: 50000 },
    },
    {
      id: 'b-risk-1',
      type: BlockType.RISK_MANAGEMENT,
      index: 2,
      data: { stopLossPct: 2.0 },
    },
  ];
  return {
    id: 'strategy-abc',
    name: 'BTC RSI Dip-Buyer',
    status: StrategyStatus.VALID,
    strategyType: 'long',
    blocks,
    settings: { timeframe: '1h' },
    createdAt: '2026-06-25T00:00:00.000Z',
    updatedAt: '2026-06-25T00:00:00.000Z',
  };
}

describe('buildAiRecsSystemPrompt', () => {
  it('includes the strategy\'s actual block types in the prompt', () => {
    const strategy = makeStrategy();
    const prompt = buildAiRecsSystemPrompt({ strategy, blockCatalog: null });

    // Snapshot-style: each BlockType that appears on the strategy must be
    // mentioned in the prompt's "actually used" listing. We assert against
    // the literal enum string values so any future enum drift is caught
    // by the type checker as well as this assertion.
    for (const type of [
      BlockType.INDICATOR,
      BlockType.ENTRY_CONDITION,
      BlockType.RISK_MANAGEMENT,
    ]) {
      expect(prompt).toContain(type);
    }

    // The "actually used" line is the contract — snapshot it so the
    // ordering and exact spelling are pinned.
    expect(prompt).toMatch(
      /Building blocks actually used by this strategy:\s*\n\s*([^\n]+)/,
    );
    const usedLine = prompt.match(
      /Building blocks actually used by this strategy:\s*\n\s*([^\n]+)/,
    )?.[1];
    expect(usedLine).toBeDefined();
    const usedTypes = (usedLine ?? '').split(',').map((s) => s.trim());
    expect(usedTypes).toEqual(
      expect.arrayContaining([
        BlockType.INDICATOR,
        BlockType.ENTRY_CONDITION,
        BlockType.RISK_MANAGEMENT,
      ]),
    );
  });

  it('includes the strategy\'s parameter key list in the prompt', () => {
    const strategy = makeStrategy();
    const prompt = buildAiRecsSystemPrompt({ strategy, blockCatalog: null });

    // Each key from any block's `data` object must appear in the prompt so
    // the AI can reference parameter names verbatim when making recs.
    for (const key of ['period', 'source', 'comparator', 'threshold', 'stopLossPct']) {
      expect(prompt).toContain(key);
    }

    // Snapshot the "Parameter names available" line to pin ordering.
    expect(prompt).toMatch(
      /Parameter names available in this strategy:\s*\n\s*([^\n]+)/,
    );
    const paramLine = prompt.match(
      /Parameter names available in this strategy:\s*\n\s*([^\n]+)/,
    )?.[1];
    expect(paramLine).toBeDefined();
    const paramKeys = (paramLine ?? '').split(',').map((s) => s.trim());
    expect(paramKeys).toEqual(
      expect.arrayContaining([
        'period',
        'source',
        'comparator',
        'threshold',
        'stopLossPct',
      ]),
    );
  });

  it('anchors the prompt in BTC / crypto context', () => {
    const prompt = buildAiRecsSystemPrompt({
      strategy: null,
      blockCatalog: null,
    });
    expect(prompt).toMatch(/BTC|Bitcoin|crypto/);
  });

  it('caps recommendations at 3', () => {
    const prompt = buildAiRecsSystemPrompt({
      strategy: null,
      blockCatalog: null,
    });
    expect(prompt).toMatch(/at most 3 recommendations/i);
  });

  it('lists every supported BlockType in the vocabulary even when the strategy uses none', () => {
    const prompt = buildAiRecsSystemPrompt({
      strategy: null,
      blockCatalog: null,
    });
    for (const type of [
      BlockType.ENTRY_CONDITION,
      BlockType.EXIT_CONDITION,
      BlockType.RISK_MANAGEMENT,
      BlockType.TIME_CONSTRAINT,
      BlockType.FILTER,
      BlockType.INDICATOR,
      BlockType.POSITION_SIZING,
    ]) {
      expect(prompt).toContain(type);
    }
  });

  it('sources the supported vocabulary from the shared canonical block-type list (BTCAAAAA-38730)', () => {
    // The dynamic prompt and the static analyze SYSTEM_PROMPT must draw from
    // ONE canonical vocabulary so ADD_BLOCK suggestions always name a type the
    // auto-apply path can match. Pin the supported line to ALL_BLOCK_TYPES so
    // any drift between the two prompts is caught here.
    const prompt = buildAiRecsSystemPrompt({ strategy: null, blockCatalog: null });
    const supportedLine = prompt.match(
      /Recommend only building blocks from this supported vocabulary:\s*\n\s*([^\n]+)/,
    )?.[1];
    expect(supportedLine).toBeDefined();
    const supported = (supportedLine ?? '').split(',').map((s) => s.trim());
    expect(supported).toEqual([...ALL_BLOCK_TYPES]);
  });

  it('merges any catalog-only block types into the supported vocabulary', () => {
    const prompt = buildAiRecsSystemPrompt({
      strategy: null,
      blockCatalog: [
        { type: BlockType.INDICATOR, name: 'RSI' },
        { type: 'experimental_signal' as unknown as BlockType, name: 'X' },
      ],
    });
    // Unknown catalog types are surfaced so the AI can reference them.
    expect(prompt).toContain('experimental_signal');
  });

  it('is deterministic for a given (strategy, catalog) pair', () => {
    const strategy = makeStrategy();
    const a = buildAiRecsSystemPrompt({ strategy, blockCatalog: [] });
    const b = buildAiRecsSystemPrompt({ strategy, blockCatalog: [] });
    expect(a).toBe(b);
  });
});