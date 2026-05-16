// ITM Live Dashboard — WebSocket message contracts for panels B1–B6

export interface CycleMessage {
  timestamp: string;
  phase: 'bar_close' | 'feature_extraction' | 'model_inference' | 'decision' | 'idle';
  elapsed_ms: number;
  phase_durations: {
    bar_close?: number;
    feature_extraction?: number;
    model_inference?: number;
    decision?: number;
  };
  cycle_number: number;
  bar_ts: string;
}

export interface Position {
  instrument_id: string;
  side: 'LONG' | 'SHORT';
  quantity: number;
  avg_open_price: number;
  unrealized_pnl: number;
  stop_loss?: number;
  take_profit?: number;
  opened_at: string;
}

export interface PositionsMessage {
  timestamp: string;
  positions: Position[];
  total_unrealized_pnl: number;
}

export interface CapitalMessage {
  timestamp: string;
  total_equity: number;
  free_margin: number;
  used_margin: number;
  daily_pnl: number;
  drawdown_pct: number;
  risk_utilization_pct: number;
  max_drawdown_limit_pct: number;
}

export interface Signal {
  id: string;
  instrument_id: string;
  direction: 'LONG' | 'SHORT' | 'FLAT';
  strength: number;
  model: string;
  features: Record<string, number>;
  generated_at: string;
}

export interface SignalsMessage {
  timestamp: string;
  signals: Signal[];
}

export type AlertSeverity = 'INFO' | 'WARN' | 'CRITICAL';

export interface Alert {
  id: string;
  severity: AlertSeverity;
  message: string;
  source: string;
  raised_at: string;
  acknowledged: boolean;
}

export interface AlertsMessage {
  timestamp: string;
  active_alerts: Alert[];
}

export interface ShapValue {
  feature: string;
  value: number;
}

export interface Decision {
  id: string;
  instrument_id: string;
  action: 'ENTER_LONG' | 'ENTER_SHORT' | 'EXIT' | 'HOLD';
  confidence: number;
  rationale: string;
  shap_values?: ShapValue[];
  decided_at: string;
  cycle_number: number;
}

export interface DecisionsMessage {
  timestamp: string;
  decisions: Decision[];
}
