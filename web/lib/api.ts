// Typed client for the Axiom FastAPI backend.
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type Band = "green" | "amber" | "red";

export interface QueueRow {
  order_id: string;
  risk_score: number;
  anomaly_score: number;
  band: Band;
  action: string;
  requires_human: boolean;
  order_value: number;
  rupee_at_risk: number;
  payment_method: string;
}

export interface Factor {
  feature: string;
  label: string;
  value: number;
  shap: number;
  direction: "raises" | "lowers";
}

export interface Decision {
  order_id: string;
  risk_score: number;
  anomaly_score: number;
  band: Band;
  action: string;
  action_detail: string;
  reason: string;
  confidence: number;
  requires_human: boolean;
  rule_id: string | null;
  policy_citations: string[];
  top_factors: Factor[];
}

export interface CaseDetail {
  order_id: string;
  risk_score: number;
  anomaly_score: number;
  decision: Decision;
  order: Record<string, string | number>;
}

export interface ToolCall {
  tool: string;
  output: Record<string, unknown>;
}

export interface Verification {
  verdict: "agree" | "veto";
  confidence: number;
  reason: string;
  verifier: string;
  independent?: boolean;
}

export interface AgentResult {
  decision_id: number;
  action: string;
  confidence: number;
  rationale: string;
  requires_human: boolean;
  policy_citations: string[];
  evidence: ToolCall[];
  retrieved_policy: string[];
  source: "llm" | "fallback";
  verification?: Verification | null;
}

export interface CopilotAnswer {
  answer: string;
  citations: string[];
  grounded: boolean;
}

export interface Interval {
  lo: number;
  hi: number;
}

export interface Metrics {
  n: number;
  prevalence: number;
  pr_auc: number;
  roc_auc: number;
  precision_at_10pct: number;
  tau_star: number;
  /** "val_frozen" when the threshold was fitted on validation (the only reportable case). */
  tau_source?: "val_frozen" | "test_oracle";
  at_tau_star: { cost: number; precision: number; recall: number; flag_rate: number; tp: number; fp: number; fn: number; tn: number };
  /** Best cost tuning the threshold ON the test split could have reached — never quoted as a result. */
  oracle?: { tau: number; cost: number; cost_per_1k: number; note: string };
  /** What that shortcut would have been worth, published so the reader can see we declined it. */
  optimism?: { cost_gap: number; cost_gap_per_1k: number; gap_pct_of_model_cost: number };
  ci?: {
    n_boot: number;
    pr_auc: Interval;
    roc_auc: Interval;
    cost_per_1k: Interval;
    saving_per_1k_vs_block_all_cod: Interval;
    precision: Interval;
    recall: Interval;
  };
  thresholds?: BandThresholds | null;
  band_policy?: BandPolicy;
  money: {
    model_cost_per_1k: number;
    block_all_cod_cost_per_1k: number;
    approve_all_cost_per_1k: number;
    savings_vs_block_all_cod_pct: number;
    savings_vs_approve_all_pct: number;
    rupees_saved_per_1k_vs_block_all_cod: number;
  };
}

export interface CostPoint {
  threshold: number;
  cost: number;
  precision: number | null;
  recall: number;
  flag_rate: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  fp_cost: number;
  fn_cost: number;
}

export interface CostCurve {
  points: CostPoint[];
  tau_star: number;
  tau_source?: "val_frozen" | "test_oracle";
  tau_low?: number;
  tau_high?: number;
  oracle_tau?: number;
  oracle_cost?: number;
  optimism_cost_gap_per_1k?: number;
  block_all_cod_cost: number;
  approve_all_cost: number;
  n: number;
}

/** The frozen operating point, fitted on validation at train time. */
export interface BandThresholds {
  tau_low: number;
  tau_high: number;
  tau_star: number;
  fitted_on: string;
  n_fitted: number;
  cost_model: Record<string, number>;
  action_model: Record<string, number>;
  note: string;
}

export interface BandPolicy {
  cost_per_1k: number;
  friction_cost: number;
  residual_rto_cost: number;
  n_green: number;
  n_amber: number;
  n_red: number;
  green_rto_rate: number | null;
  amber_rto_rate: number | null;
  red_rto_rate: number | null;
  tau_low: number;
  tau_high: number;
}

export interface ThresholdReport {
  thresholds: BandThresholds | null;
  band_policy: BandPolicy;
  legacy_hardcoded_band_policy: BandPolicy;
  saving_per_1k_vs_hardcoded: number;
  sensitivity: { amber_efficacy: number; red_efficacy: number; amber_friction_frac: number; tau_low: number; tau_high: number }[];
  note: string;
}

export interface BaselineRow {
  model: string;
  tau_val_fitted: number;
  pr_auc: number | null;
  roc_auc: number | null;
  brier: number;
  cost_per_1k: number;
  saving_per_1k_vs_block_all_cod: number;
  champion_gain_pr_auc_lo?: number | null;
  champion_gain_pr_auc_hi?: number | null;
  champion_beats_pr_auc?: boolean | null;
  champion_gain_cost_per_1k_lo?: number | null;
  champion_gain_cost_per_1k_hi?: number | null;
}
export interface BaselineReport {
  rows: BaselineRow[];
  note: string;
}

export interface SliceRow {
  dimension: string;
  slice: string;
  n: number;
  rto_rate: number;
  flag_rate: number;
  n_good: number;
  false_positives: number;
  fp_rate_on_good: number;
  recall: number | null;
  precision: number | null;
  fp_cost: number;
  fn_cost: number;
}
export interface DisparityRow {
  dimension: string;
  worst_slice: string;
  worst_fp_rate_on_good: number;
  best_slice: string;
  best_fp_rate_on_good: number;
  /** null when the safest slice had no false positives at all — an undefined ratio. */
  ratio: number | null;
  unbounded: boolean;
}
export interface SliceReport {
  tau: number;
  slices: SliceRow[];
  worst: SliceRow[];
  disparity: DisparityRow[];
  note: string;
}

export interface ModelMeta {
  model_version: string;
  algorithm: string;
  n_features: number;
  features: string[];
  data_provenance: string;
  n_orders: number;
  split: Record<string, string | number>;
  train_prior_rto: number;
  test_rto_rate_natural: number;
  outcome_lag_days: number;
  target_encoding_alpha: number;
  thresholds: BandThresholds | null;
  protected_attributes_used: string[];
  pii_used: string[];
  intended_use: string;
  out_of_scope: string[];
}

export interface LeakageMetrics {
  roc_auc: number;
  pr_auc: number;
  prevalence: number;
}
export interface Leakage {
  honest: LeakageMetrics;
  leaky: LeakageMetrics;
}

export interface ExecuteResult {
  executed: boolean;
  action?: string;
  message?: string;
  simulated?: boolean;
  short_url?: string;
  plink_id?: string;
  status?: string;
  amount_inr?: number;
  deposit_inr?: number | null;
  decision_id?: number;
}

export interface BatchAction {
  order_id: string;
  action: string;
  order_value: number;
  is_rto: number;
  intervened: boolean;
  recovered: number;
  friction_cost: number;
  source: "llm" | "fallback";
  decision_id: number;
}
export interface BatchResult {
  stopped: boolean;
  stop_reason: string;
  processed: number;
  amber_seen: number;
  interventions: number;
  rto_caught: number;
  good_frictioned: number;
  rto_missed: number;
  recovered_gross: number;
  friction_cost: number;
  net_recovered: number;
  missed_cost: number;
  actions: BatchAction[];
  basis: string;
}
export interface BatchOptions {
  max_orders?: number;
  budget_calls?: number;
  stop_after_low_value?: number;
  low_value_threshold?: number;
  quiet_hours?: [number, number] | null;
  scan_limit?: number;
  now_hour?: number;
}

export interface RingSummary {
  ring_id: string;
  n_buyers: number;
  n_devices: number;
  n_orders: number;
  ring_risk: number;
  band: Band;
  sample_devices: string[];
}
export interface RingValidation {
  precision: number;
  recall: number;
  tp: number;
  fp: number;
  fn: number;
  n_rings: number;
  n_flagged_buyers: number;
}
export interface RingsResponse {
  validation: RingValidation;
  rings: RingSummary[];
}
export interface RingNode {
  id: string;
  label: string;
  kind: "buyer" | "device";
}
export interface RingGraphData {
  ring_id: string;
  ring_risk: number;
  band: Band;
  n_buyers: number;
  n_devices: number;
  nodes: RingNode[];
  links: { source: string; target: string }[];
}

export interface AuditRow {
  id: number;
  order_id: string;
  ts: number;
  band: Band;
  action: string;
  reason: string;
  confidence: number;
  source: string;
  requires_human: boolean;
  overrides: { to_action: string; from_action: string; reviewer: string; reason: string; ts: number }[];
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}
async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

export const api = {
  orders: (limit = 60) => get<QueueRow[]>(`/orders?limit=${limit}`),
  detail: (id: string) => get<CaseDetail>(`/orders/${id}`),
  investigate: (id: string) => post<AgentResult>(`/orders/${id}/investigate`),
  runBatch: (opts: BatchOptions = {}) => post<BatchResult>(`/batch/run`, opts),
  ask: (id: string, question: string) => post<CopilotAnswer>(`/orders/${id}/ask`, { question }),
  execute: (id: string, action: string) => post<ExecuteResult>(`/orders/${id}/execute`, { action }),
  override: (decisionId: number, body: { reviewer: string; to_action: string; reason: string }) =>
    post<Record<string, unknown>>(`/decisions/${decisionId}/override`, body),
  audit: (limit = 40) => get<AuditRow[]>(`/audit?limit=${limit}`),
  metrics: () => get<Metrics>(`/metrics`),
  costcurve: () => get<CostCurve>(`/costcurve`),
  leakage: () => get<Leakage>(`/leakage`),
  thresholds: () => get<ThresholdReport>(`/thresholds`),
  baselines: () => get<BaselineReport>(`/baselines`),
  slices: () => get<SliceReport>(`/slices`),
  modelMeta: () => get<ModelMeta>(`/model_meta`),
  rings: () => get<RingsResponse>(`/rings`),
  ringGraph: (id: string) => get<RingGraphData>(`/rings/${id}`),
  health: () => get<{ status: string }>(`/`),
};

export { BASE as API_BASE };
