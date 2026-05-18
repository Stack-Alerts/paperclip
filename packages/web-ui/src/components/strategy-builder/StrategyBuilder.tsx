'use client';

import { StrategyBuilderMainWindow } from './StrategyBuilderMainWindow';

export interface StrategyBuilderProps {
  strategyId?: string;
}

export function StrategyBuilder({ strategyId }: StrategyBuilderProps) {
  return <StrategyBuilderMainWindow strategyId={strategyId} />;
}

export default StrategyBuilder;
