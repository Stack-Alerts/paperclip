import { Strategy, Trade } from '@/lib/strategy-builder/types';
import { BacktestResult } from '@/lib/strategy-builder/types';

export function formatStrategyConfig(strategy: Strategy | null | undefined): string {
  if (!strategy) return 'No strategy loaded.';
  return JSON.stringify(
    {
      id: strategy.id,
      name: strategy.name,
      status: strategy.status,
      strategyType: strategy.strategyType,
      blocks: strategy.blocks?.map((b) => ({
        id: b.id,
        type: b.type,
        index: b.index,
        data: b.data,
      })) ?? [],
      settings: strategy.settings,
    },
    null,
    2,
  );
}

export function formatBacktestConfig(config: Record<string, unknown> | null | undefined): string {
  if (!config) return 'No backtest configuration available.';
  return JSON.stringify(config, null, 2);
}

export function formatTrades(trades: Trade[] | undefined): string {
  if (!trades || trades.length === 0) return '⚠ NO TRADES — AI cannot analyze 0 trades.';
  const preview = trades.slice(0, 10).map((t, i) => `Trade #${i + 1}:\n${JSON.stringify(t, null, 2)}`).join('\n\n');
  const suffix = trades.length > 10 ? `\n\n...and ${trades.length - 10} more trades` : '';
  return `Total Trades: ${trades.length}\n\n${preview}${suffix}`;
}

export function formatMetrics(result: BacktestResult | null | undefined): string {
  if (!result) return 'No results yet.';
  return JSON.stringify(
    {
      totalTrades: result.totalTrades,
      winningTrades: result.winningTrades,
      losingTrades: result.losingTrades,
      winRate: result.winRate,
      returnPercentage: result.returnPercentage,
      profitFactor: result.profitFactor,
      sharpeRatio: result.sharpeRatio,
      sortino_ratio: result.sortino_ratio,
      calmar_ratio: result.calmar_ratio,
      maxDrawdown: result.maxDrawdown,
      averageWin: result.averageWin,
      averageLoss: result.averageLoss,
      initialCapital: result.initialCapital,
      finalCapital: result.finalCapital,
    },
    null,
    2,
  );
}

interface ActiveRec {
  id: string;
  title: string;
  raw: string;
  confidence?: string;
  rationale?: string;
  suggestedParams: Array<{ key: string; value: string }>;
}

export function buildRequestPayload(
  result: BacktestResult | null | undefined,
  strategy: Strategy | null | undefined,
  backtestConfig: Record<string, unknown> | null | undefined,
  activeRec: ActiveRec | null = null,
  optimizationGoal: string | null = null,
  blockCatalog: unknown[] | null = null,
): string {
  // Cap trades to 20 (first 10 + last 10) to avoid blowing provider token limits.
  const allTrades = result?.trades ?? [];
  const sampledTrades =
    allTrades.length <= 20
      ? allTrades
      : [...allTrades.slice(0, 10), ...allTrades.slice(-10)];

  return JSON.stringify(
    {
      strategy_config: strategy
        ? {
            id: strategy.id,
            name: strategy.name,
            strategyType: strategy.strategyType,
            blocks: strategy.blocks ?? [],
            settings: strategy.settings,
          }
        : null,
      available_blocks: blockCatalog ?? [],
      backtest_config: backtestConfig ?? null,
      trades: sampledTrades,
      trades_total_count: allTrades.length,
      metrics: result
        ? {
            totalTrades: result.totalTrades,
            winRate: result.winRate,
            returnPercentage: result.returnPercentage,
            profitFactor: result.profitFactor,
            sharpeRatio: result.sharpeRatio,
            sortino_ratio: result.sortino_ratio,
            maxDrawdown: result.maxDrawdown,
            averageWin: result.averageWin,
            averageLoss: result.averageLoss,
          }
        : {},
      ...(activeRec
        ? {
            active_recommendation: {
              id: activeRec.id,
              title: activeRec.title,
              raw: activeRec.raw,
              confidence: activeRec.confidence ?? null,
              rationale: activeRec.rationale ?? null,
              suggested_params: activeRec.suggestedParams,
            },
          }
        : {}),
      ...(optimizationGoal
        ? { optimization_goal: optimizationGoal }
        : {}),
    },
    null,
    2,
  );
}

/** Split a model response into DIAGNOSIS / RECOMMENDATIONS sections.
 *
 * Handles the expected plain format as well as common AI deviations:
 * - Markdown bold: **DIAGNOSIS:** / **RECOMMENDATIONS:**
 * - Markdown headings: ## DIAGNOSIS / ## RECOMMENDATIONS
 * - No section headers: falls back to numbered-list split
 */
export function parseAnalysisResponse(text: string): {
  diagnosis: string;
  recommendations: string;
  raw: string;
} {
  // Normalise markdown bold/italic/header decoration so the regex below only
  // needs to handle the plain-text `DIAGNOSIS:` / `RECOMMENDATIONS:` form.
  const normalized = text
    .replace(/\*{1,2}\s*(DIAGNOSIS)\s*\*{1,2}/gi, '$1:')
    .replace(/\*{1,2}\s*(RECOMMENDATIONS)\s*\*{1,2}/gi, '$1:')
    // BTCAAAAA-37771: models often bold a synonym heading instead of the exact
    // word RECOMMENDATIONS (e.g. `**Recommended Changes:**`). Without this the
    // section was never split out and the box rendered blank after a completed
    // re-analyze.
    .replace(
      /\*{1,2}\s*(?:Recommended|Suggested)\s+(?:Changes|Improvements)\s*\*{0,2}\s*:?/gi,
      'RECOMMENDATIONS:',
    )
    .replace(/^#{1,6}\s+(DIAGNOSIS)\s*[:\-]?\s*$/gim, 'DIAGNOSIS:')
    // BTCAAAAA-37067: DeepSeek emits `## Actionable Recommendations`; the prior
    // regex required the heading to start exactly with RECOMMENDATIONS, so the
    // RECOMMENDATIONS section was never split out and zero cards rendered.
    .replace(
      /^#{1,6}\s+(?:Actionable\s+|Optimization\s+)?RECOMMENDATIONS?\s*[:\-]?\s*$/gim,
      'RECOMMENDATIONS:',
    )
    // BTCAAAAA-37771: also accept `## Recommended Changes` /
    // `## Suggested Improvements` heading variants.
    .replace(
      /^#{1,6}\s+(?:Recommended|Suggested)\s+(?:Changes|Improvements)\s*[:\-]?\s*$/gim,
      'RECOMMENDATIONS:',
    );

  const diagnosisMatch = normalized.match(
    /DIAGNOSIS\s*:\s*([\s\S]*?)(?=\n\s*RECOMMENDATIONS\s*:|$)/i,
  );
  const recommendationsMatch = normalized.match(
    /RECOMMENDATIONS\s*:\s*([\s\S]*?)$/i,
  );

  let diagnosis = diagnosisMatch?.[1]?.trim() ?? '';
  let recommendations = recommendationsMatch?.[1]?.trim() ?? '';

  // Fallback A: neither header found — split at the first numbered list item.
  if (!diagnosis && !recommendations) {
    const idx = text.search(/(?:^|\n)\s*1[.)]\s+/);
    if (idx > 0) {
      diagnosis = text.slice(0, idx).trim();
      recommendations = text.slice(idx).trim();
    } else {
      diagnosis = text.trim();
    }
  }

  // Fallback B: DIAGNOSIS found but no RECOMMENDATIONS header — check if the
  // captured diagnosis text itself contains a numbered list and split it out.
  if (diagnosis && !recommendations) {
    const idx = diagnosis.search(/\n\s*1[.)]\s+/);
    if (idx > 0) {
      recommendations = diagnosis.slice(idx).trim();
      diagnosis = diagnosis.slice(0, idx).trim();
    } else {
      // BTCAAAAA-37771: no numbered list — the model may have bulleted its
      // recommendations (- / * / •) directly under the diagnosis with no
      // RECOMMENDATIONS header, which previously left the box blank. Promote a
      // trailing bulleted list to the recommendations section, but only when
      // there are at least two bullet lines so an incidental dash in prose is
      // not mistaken for a rec list.
      const bulletIdx = diagnosis.search(/\n\s*[-*•]\s+/);
      if (bulletIdx > 0) {
        const tail = diagnosis.slice(bulletIdx);
        const bulletCount = (tail.match(/\n\s*[-*•]\s+/g) ?? []).length;
        if (bulletCount >= 2) {
          recommendations = tail.trim();
          diagnosis = diagnosis.slice(0, bulletIdx).trim();
        }
      }
    }
  }

  return { diagnosis, recommendations, raw: text };
}

/**
 * A4 (BTCAAAAA-37777): map a model-emitted confidence label to a synthetic
 * uplift number used only to rank the top-quartile bucket. The numeric scale
 * is internal to the reverse-view banner — it never surfaces to the user.
 */
export function confidenceToUplift(confidence: string | undefined): number {
  if (!confidence) return 0;
  switch (confidence.trim().toLowerCase()) {
    case 'high':
      return 3;
    case 'medium':
    case 'med':
      return 2;
    case 'low':
      return 1;
    default:
      return 0;
  }
}
