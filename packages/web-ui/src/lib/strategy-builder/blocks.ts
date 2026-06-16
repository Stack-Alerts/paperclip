import { Block, BlockType, PersistedExitCondition } from './types';

// RawDBBlock represents the backend's canonical block shape (raw DB format)
export interface RawDBSignal {
  name: string;
  logic?: string;
  timing_constraint?: {
    withinCandles?: number;
    ofSignal?: string;
  };
  recheck_config?: {
    enabled: boolean;
    bar_delay: number;
  };
  exit_conditions?: Array<{
    signal_name?: string;
    percentage?: number;
    exit_mode?: string;
    binding_level?: string;
    tp_proximity_threshold?: number;
    reversal_trigger?: number;
    recheck_config?: {
      enabled: boolean;
      bar_delay: number;
    };
  }>;
}

export interface RawDBBlock {
  name: string;
  logic?: string;
  signals?: RawDBSignal[];
}

/**
 * Denormalize frontend Block[] back to raw DB shape (RawDBBlock[]).
 * Inverts the normalization done in StrategyBuilderMainWindow:546-642.
 *
 * Key inversions:
 * - Drop all synthetic EXIT_CONDITION blocks (projections of signal.exit_conditions)
 * - For INDICATOR blocks, fold recheckEnabled + recheckBarDelay back into recheck_config
 * - Collect exit_conditions from the flattened EXIT_CONDITION blocks back into each signal
 *
 * Throws if any block has an unknown type (safety: never silently drop blocks).
 */
export function denormalizeBlocks(blocks: Block[]): RawDBBlock[] {
  // Map of "blockName::signalName" -> exit conditions from EXIT_CONDITION blocks
  const exitsByKey = new Map<
    string,
    Array<{
      signal_name?: string;
      percentage?: number;
      exit_mode?: string;
      binding_level?: string;
      tp_proximity_threshold?: number;
      reversal_trigger?: number;
      recheck_config?: {
        enabled: boolean;
        bar_delay: number;
      };
    }>
  >();

  // First pass: collect all exit_conditions from EXIT_CONDITION blocks
  for (const block of blocks) {
    if (block.type === BlockType.EXIT_CONDITION) {
      const exitConfig = (block.data?.exitConfig as Record<string, unknown>) ?? {};
      const blockName = exitConfig.blockName as string | undefined ?? '';
      const parentSignalName = exitConfig.parentSignalName as string | undefined ?? '';
      const key = `${blockName}::${parentSignalName}`;

      const exitCondition: {
        signal_name?: string;
        percentage?: number;
        exit_mode?: string;
        binding_level?: string;
        tp_proximity_threshold?: number;
        reversal_trigger?: number;
        recheck_config?: {
          enabled: boolean;
          bar_delay: number;
        };
      } = {
        signal_name: exitConfig.signalName as string | undefined,
        percentage: exitConfig.percentage as number | undefined,
        exit_mode: exitConfig.exitMode as string | undefined,
        binding_level: exitConfig.bindingLevel as string | undefined,
        tp_proximity_threshold: exitConfig.tpProximityThreshold as number | undefined,
        reversal_trigger: exitConfig.reversalTrigger as number | undefined,
      };

      // Fold back recheckEnabled + recheckBarDelay into recheck_config
      const recheckEnabled = exitConfig.recheckEnabled as boolean | undefined;
      const recheckBarDelay = exitConfig.recheckBarDelay as number | undefined;
      if (typeof recheckEnabled === 'boolean' || typeof recheckBarDelay === 'number') {
        exitCondition.recheck_config = {
          enabled: typeof recheckEnabled === 'boolean' ? recheckEnabled : false,
          bar_delay: typeof recheckBarDelay === 'number' ? recheckBarDelay : 0,
        };
      }

      const existing = exitsByKey.get(key) ?? [];
      existing.push(exitCondition);
      exitsByKey.set(key, existing);
    }
  }

  // Second pass: build raw blocks, only from INDICATOR blocks
  const result: RawDBBlock[] = [];
  for (const block of blocks) {
    if (block.type === BlockType.INDICATOR) {
      const data = block.data ?? {};
      const blockName = data.name as string | undefined ?? '';
      const signals = data.signals as Array<Record<string, unknown>> | undefined ?? [];

      const denormalizedSignals: RawDBSignal[] = signals.map((sig) => {
        const sigName = sig.name as string | undefined ?? '';
        const key = `${blockName}::${sigName}`;

        // Fold recheckEnabled + recheckBarDelay back into recheck_config
        const recheckEnabled = sig.recheckEnabled as boolean | undefined;
        const recheckBarDelay = sig.recheckBarDelay as number | undefined;
        const recheckConfig = (typeof recheckEnabled === 'boolean' || typeof recheckBarDelay === 'number')
          ? {
              enabled: typeof recheckEnabled === 'boolean' ? recheckEnabled : false,
              bar_delay: typeof recheckBarDelay === 'number' ? recheckBarDelay : 0,
            }
          : undefined;

        const denormalizedSignal: RawDBSignal = {
          name: sigName,
          logic: sig.logic as string | undefined,
          timing_constraint: sig.timing_constraint as RawDBSignal['timing_constraint'],
          exit_conditions: exitsByKey.get(key) ?? [],
        };

        if (recheckConfig) {
          denormalizedSignal.recheck_config = recheckConfig;
        }

        return denormalizedSignal;
      });

      const rawBlock: RawDBBlock = {
        name: blockName,
        logic: data.logic as string | undefined,
        signals: denormalizedSignals,
      };

      result.push(rawBlock);
    } else if (block.type === BlockType.EXIT_CONDITION) {
      // Already handled in first pass; skip
      continue;
    } else {
      // Unknown block type — never silently drop
      throw new Error(
        `denormalizeBlocks: unknown block type '${block.type}'. ` +
        `Only INDICATOR blocks round-trip to the backend; EXIT_CONDITION blocks ` +
        `are synthetic projections and should be filtered by the caller.`
      );
    }
  }

  return result;
}

/**
 * Extract strategy-level exit conditions (bindingLevel === 'STRATEGY') from
 * the in-memory block list. Strategy-level exits are materialized as
 * synthetic EXIT_CONDITION blocks in StrategyBuilderMainWindow with empty
 * blockName and parentSignalName — `denormalizeBlocks` cannot fold them
 * onto any owning signal (the key would be `"::"`), so they round-trip as
 * a separate top-level `exitConditions` array on the strategy.
 *
 * Caller passes the result as `exitConditions` in the PUT
 * `/strategy-builder/strategies/{id}` body; the backend persists it to
 * the `strategy_versions.exit_conditions` JSONB column (BTCAAAAA-36755).
 *
 * Mirrors the persisted shape used by
 * `src/strategy_builder/persistence/strategy_persistence.py:_exit_condition_to_dict`
 * and surfaces in the API as `strategy.exitConditions` (camelCase list).
 */
export function extractStrategyLevelExits(blocks: Block[]): PersistedExitCondition[] {
  const out: PersistedExitCondition[] = [];
  for (const block of blocks) {
    if (block.type !== BlockType.EXIT_CONDITION) continue;
    const exitConfig = (block.data?.exitConfig as Record<string, unknown>) ?? {};
    if ((exitConfig.bindingLevel as string | undefined) !== 'STRATEGY') continue;

    const persisted: PersistedExitCondition = {
      signal_name: exitConfig.signalName as string | undefined ?? '',
      percentage: exitConfig.percentage as number | undefined,
      exit_mode: exitConfig.exitMode as string | undefined,
      tp_proximity_threshold: exitConfig.tpProximityThreshold as number | undefined,
      reversal_trigger: exitConfig.reversalTrigger as boolean | undefined,
      binding_level: 'STRATEGY',
    };

    // Recheck chain / recheck config — fold the editor-side `recheckEnabled`
    // and `recheckBarDelay` fields into the persisted `recheck_config`
    // shape so the server-side exit engine can re-validate without a
    // second schema translation.
    const recheckEnabled = exitConfig.recheckEnabled as boolean | undefined;
    const recheckBarDelay = exitConfig.recheckBarDelay as number | undefined;
    if (typeof recheckEnabled === 'boolean' || typeof recheckBarDelay === 'number') {
      persisted.recheck_config = {
        enabled: typeof recheckEnabled === 'boolean' ? recheckEnabled : false,
        bar_delay: typeof recheckBarDelay === 'number' ? recheckBarDelay : 0,
      };
    }

    out.push(persisted);
  }
  return out;
}
