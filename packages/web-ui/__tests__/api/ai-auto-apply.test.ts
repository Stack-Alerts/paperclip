/**
 * Tests for the client-side auto-apply orchestrator (BTCAAAAA-36465).
 *
 * The orchestrator is now fully in-process: it receives the current strategy
 * from the panel, parses structured fields (Type/Block/Parameter/Suggested Value)
 * from the rec's raw text, mutates a deep copy, and returns the updated strategy.
 *
 * Replaces the prior tests that exercised the now-removed backend HTTP proxy path.
 */

import { runAutoApply, AutoApplyRequest } from '../../app/api/ai/auto-apply/orchestrator';

const baseStrategy = {
  id: 's-1',
  name: 'Test Strategy',
  strategyType: 'Bullish',
  blocks: [
    {
      id: 'b-1',
      type: 'RISK_MANAGEMENT',
      index: 0,
      // findBlock matches on data.name, not block.type
      data: { name: 'RISK_MANAGEMENT', riskPerTradePct: 2, maxLeverage: 10 },
    },
    {
      id: 'b-2',
      type: 'TREND',
      index: 1,
      data: { name: 'TREND', ema_window: 50, threshold: 0.5 },
    },
  ],
  settings: {
    commissionPercentage: 0.05,
    confluenceThreshold: 2,
  },
};

function makeReq(overrides: Partial<AutoApplyRequest> = {}): AutoApplyRequest {
  return {
    strategyId: 's-1',
    recs: [],
    optInDestructiveIds: null,
    strategy: JSON.parse(JSON.stringify(baseStrategy)),
    ...overrides,
  };
}

describe('runAutoApply — client-side orchestrator (BTCAAAAA-36465)', () => {
  describe('no-op cases', () => {
    it('returns ok:false when no strategy is provided', async () => {
      const result = await runAutoApply({ ...makeReq(), strategy: null });
      expect(result.ok).toBe(false);
      expect(result.error).toMatch(/no strategy provided/i);
    });

    it('returns ok:true with unchanged strategy when recs is empty', async () => {
      const result = await runAutoApply(makeReq({ recs: [] }));
      expect(result.ok).toBe(true);
      expect(result.apply?.applied_count).toBe(0);
    });
  });

  describe('ADJUST_PARAM — block-level change', () => {
    it('updates an existing block parameter and returns the mutated strategy', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r1',
              type: 'ADJUST_PARAM',
              block: 'RISK_MANAGEMENT',
              parameter: 'riskPerTradePct',
              suggestedValue: '1',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.strategy?.blocks?.[0].data.riskPerTradePct).toBe(1);
      expect(result.apply?.applied_count).toBe(1);
      expect(result.apply?.applied[0].rec_id).toBe('r1');
    });

    it('parses Block/Parameter/Suggested Value from raw text when structured fields absent', async () => {
      const raw = `Lower risk per trade
   Type: ADJUST_PARAM
   Block: RISK_MANAGEMENT
   Parameter: riskPerTradePct
   Suggested Value: 0.5
   Rationale: Too much capital at risk per trade.`;

      const result = await runAutoApply(
        makeReq({
          recs: [{ rec_id: 'r2', type: 'ADJUST_PARAM', raw }],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.strategy?.blocks?.[0].data.riskPerTradePct).toBe(0.5);
    });

    it('converts numeric string values to numbers', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r3',
              type: 'ADJUST_PARAM',
              block: 'TREND',
              parameter: 'ema_window',
              suggestedValue: '100',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.strategy?.blocks?.[1].data.ema_window).toBe(100);
    });

    it('keeps string values as strings when not numeric', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r4',
              type: 'ADJUST_PARAM',
              block: 'TREND',
              parameter: 'ema_window',
              suggestedValue: 'disabled',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.strategy?.blocks?.[1].data.ema_window).toBe('disabled');
    });

    it('handles dot-notation nested parameter paths', async () => {
      const strat = {
        ...JSON.parse(JSON.stringify(baseStrategy)),
        blocks: [
          {
            id: 'b-3',
            type: 'RISK_MANAGEMENT',
            index: 0,
            data: { name: 'RISK_MANAGEMENT', adaptiveSL: { volatilityMultiplier: 2.0 } },
          },
        ],
      };

      const result = await runAutoApply({
        strategyId: 's-1',
        recs: [
          {
            rec_id: 'r5',
            type: 'ADJUST_PARAM',
            block: 'RISK_MANAGEMENT',
            parameter: 'adaptiveSL.volatilityMultiplier',
            suggestedValue: '1.5',
          },
        ],
        optInDestructiveIds: null,
        strategy: strat,
      });

      expect(result.ok).toBe(true);
      const blk = result.strategy?.blocks?.[0].data as Record<string, unknown>;
      expect((blk.adaptiveSL as Record<string, unknown>).volatilityMultiplier).toBe(1.5);
    });
  });

  describe('ADJUST_PARAM — settings-level change', () => {
    it('updates a settings key when Block is "settings"', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r6',
              type: 'ADJUST_PARAM',
              block: 'settings',
              parameter: 'confluenceThreshold',
              suggestedValue: '3',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.strategy?.settings?.confluenceThreshold).toBe(3);
    });
  });

  describe('ADJUST_PARAM — error cases', () => {
    it('returns error when Parameter field is missing', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r7',
              type: 'ADJUST_PARAM',
              block: 'RISK_MANAGEMENT',
              suggestedValue: '1',
              // parameter intentionally absent
            },
          ],
        }),
      );

      expect(result.ok).toBe(false);
      expect(result.error).toMatch(/no Parameter field/i);
    });

    it('returns error when Suggested Value is missing', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r8',
              type: 'ADJUST_PARAM',
              block: 'RISK_MANAGEMENT',
              parameter: 'riskPerTradePct',
              // suggestedValue intentionally absent
            },
          ],
        }),
      );

      expect(result.ok).toBe(false);
      expect(result.error).toMatch(/no Suggested Value/i);
    });

    it('returns error when the named block does not exist in the strategy', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r9',
              type: 'ADJUST_PARAM',
              block: 'NONEXISTENT_BLOCK',
              parameter: 'someParam',
              suggestedValue: '5',
            },
          ],
        }),
      );

      expect(result.ok).toBe(false);
      expect(result.error).toMatch(/block.*not found/i);
    });
  });

  describe('Structural types — manual instruction path', () => {
    it('ADD_BLOCK returns ok:true with a manualInstruction instead of mutating strategy', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r10',
              type: 'ADD_BLOCK',
              block: 'VOLATILITY',
              raw: 'Add a VOLATILITY block\n   Type: ADD_BLOCK\n   Block: VOLATILITY\n   Rationale: Filter low-ATR periods.',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.manualInstruction).toMatch(/VOLATILITY/i);
      expect(result.manualInstruction).toMatch(/Strategy Builder/i);
      expect(result.apply?.applied_count).toBe(1);
    });

    it('REMOVE_BLOCK returns ok:true with a manualInstruction', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r11',
              type: 'REMOVE_BLOCK',
              block: 'TREND',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.manualInstruction).toBeDefined();
    });
  });

  describe('multi-rec batch', () => {
    it('applies multiple recs sequentially, threading strategy state', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r12a',
              type: 'ADJUST_PARAM',
              block: 'RISK_MANAGEMENT',
              parameter: 'riskPerTradePct',
              suggestedValue: '1',
            },
            {
              rec_id: 'r12b',
              type: 'ADJUST_PARAM',
              block: 'TREND',
              parameter: 'ema_window',
              suggestedValue: '100',
            },
          ],
        }),
      );

      expect(result.ok).toBe(true);
      expect(result.apply?.applied_count).toBe(2);
      expect(result.strategy?.blocks?.[0].data.riskPerTradePct).toBe(1);
      expect(result.strategy?.blocks?.[1].data.ema_window).toBe(100);
    });

    it('stops at first failing rec and returns its error', async () => {
      const result = await runAutoApply(
        makeReq({
          recs: [
            {
              rec_id: 'r13a',
              type: 'ADJUST_PARAM',
              block: 'RISK_MANAGEMENT',
              parameter: 'riskPerTradePct',
              suggestedValue: '1',
            },
            {
              rec_id: 'r13b',
              type: 'ADJUST_PARAM',
              block: 'RISK_MANAGEMENT',
              // missing parameter — should fail
              suggestedValue: '5',
            },
          ],
        }),
      );

      expect(result.ok).toBe(false);
      expect(result.error).toMatch(/no Parameter field/i);
    });
  });

  describe('immutability', () => {
    it('does not mutate the original strategy passed in the request', async () => {
      const original = JSON.parse(JSON.stringify(baseStrategy));
      const req = makeReq({
        recs: [
          {
            rec_id: 'r14',
            type: 'ADJUST_PARAM',
            block: 'RISK_MANAGEMENT',
            parameter: 'riskPerTradePct',
            suggestedValue: '1',
          },
        ],
        strategy: original,
      });

      await runAutoApply(req);

      // Original object must be unchanged.
      expect(original.blocks[0].data.riskPerTradePct).toBe(2);
    });
  });
});
