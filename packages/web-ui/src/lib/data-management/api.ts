import { get, post } from '@/lib/strategy-builder/api';
export type { DataGapCheckResult, DataTypeStatus } from '@/components/strategy-builder/DataUpdateModal';
import type { DataGapCheckResult } from '@/components/strategy-builder/DataUpdateModal';

export interface TimeframeFreshness {
  lastBarTs: string | null;
  ageSeconds: number | null;
  stale: boolean;
  error?: string;
}

export interface DataStatusResponse {
  currentTime: string;
  anyGaps: boolean;
  anyStale: boolean;
  allStatus: Record<string, { status: string; start?: string; end?: string; gap_days?: number; gap_minutes?: number; error?: string }>;
  timeframeFreshness: Record<string, TimeframeFreshness>;
}

export interface DataUpdateResult {
  success: boolean;
  message: string;
  results: Record<string, { success: boolean; bars_downloaded?: number; error?: string }>;
}

export interface DataGapEntry {
  gapStart: string | null;
  gapEnd: string | null;
  missingBars: number;
  repairable: boolean;
  reason?: string | null;
}

export interface TimeframeVerifyResult {
  timeframe: string;
  totalGaps: number;
  repairableCount: number;
  tooOldCount: number;
  totalMissingBars: number;
  repairableMissingBars: number;
  tooOldMissingBars: number;
  gaps: DataGapEntry[];
  lastCandleTs: string | null;
}

export interface DataRepairResult {
  success: boolean;
  message: string;
  summary: Record<string, {
    gapsFound: number;
    gapsRepaired: number;
    gapsTooOld: number;
    barsFetched: number;
    errors: string[];
  }>;
}

export async function fetchDataStatus(): Promise<DataStatusResponse> {
  return get<DataStatusResponse>('/data/status');
}

export async function fetchDataGapCheck(): Promise<DataGapCheckResult> {
  return get('/data/gap-check') as Promise<DataGapCheckResult>;
}

export async function triggerDataUpdate(startDate: string, endDate: string): Promise<DataUpdateResult> {
  return post<DataUpdateResult>('/data/update', { startDate, endDate });
}

export async function runDataVerify(): Promise<Record<string, TimeframeVerifyResult>> {
  return post<Record<string, TimeframeVerifyResult>>('/data/verify', {});
}

export async function runDataRepair(timeframe?: string): Promise<DataRepairResult> {
  return post<DataRepairResult>('/data/repair', { timeframe: timeframe ?? null });
}
