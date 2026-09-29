export type ModelId = "weather_corr_v1" | "water_ridge_v1" | "persistence" | "climatology";

/** [pred, pi90_low, pi90_high, watch(0|1)] */
export type Cell = [number, number | null, number | null, number] | null;

export interface Contingency {
  tp: number; fp: number; fn: number; tn: number;
  precision: number | null; recall: number | null;
  false_alarm_ratio: number | null; false_positive_rate: number | null;
}

export interface ModelMetrics {
  mae: number; rmse: number; bias: number; skill: number | null;
  coverage: number; width: number; watch: Contingency;
}

export interface Alert {
  alert_id: string;
  station_id: string;
  origin_date: string;
  target_dates: string[];
  forecast_refs: number[];
  action: string;
  status: "open" | "acknowledged";
  ack: { by: string; at: string; note: string } | null;
}

export interface GateCriterion { id: number; name: string; value: unknown; passed: boolean }

export interface Replay {
  generated_at: string;
  synthetic: boolean;
  site: { id: string; name: string; commune: string; lat: number; lon: number; framing: string };
  timing: { issuance_hour_utc: number; product_leads: number[]; exploratory_leads: number[]; primary_lead: number };
  followup: { action_code: string; action_text: string };
  product_model: ModelId;
  model_version: string;
  hashes: { contract: string; frozen: string; daily_water: string };
  frozen_at: string;
  test_opened_at: string;
  obs: { start: string; values: (number | null)[] };
  clim: { mean: (number | null)[]; p90: (number | null)[]; period: [string, string] };
  origins: string[];
  leads: number[];
  forecasts: Record<ModelId, Cell[][]>;
  meta: { inputs: string[]; run: string | null }[];
  alerts: Alert[];
  metrics: Record<string, { n: number; n_may_aug: number; episodes: number; models: Partial<Record<ModelId, ModelMetrics>> }>;
  validation: { lead: number; rows: number; folds: string[]; mae: Record<string, number>; selected: string; coef: [number, number] | null };
  monthly: { month: string; n: number; mae: number; mae_persistence: number; skill: number }[];
  delay1: Partial<Record<ModelId, { mae: number; skill: number | null }>>;
  gate: { decision: string; passed: boolean; primary_lead: number; product_model: string; criteria: GateCriterion[];
          mae: { product: number; persistence: number; climatology: number } };
  chronology: { passed: boolean; checks: { check: string; passed: boolean; detail: string }[] };
  qc: {
    per_year: Record<string, { calendar_days: number; days_with_data: number; eligible_days: number }>;
    dropped: Record<string, number>; conflicting_duplicates_quarantined: number;
    eligible_days: number; days: number; first_date: string; last_date: string;
    air_runs: { runs: number; first_run: string; last_run: string };
  };
  fhir: null | { errors: number; warnings: number; validator: string; fhir: string; [k: string]: unknown };
}
