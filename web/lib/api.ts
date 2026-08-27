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

export interface Metrics {
  n: number;
  prevalence: number;
  pr_auc: number;
  roc_auc: number;
  precision_at_10pct: number;
  tau_star: number;
  at_tau_star: { precision: number; recall: number; flag_rate: number };
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
  block_all_cod_cost: number;
  approve_all_cost: number;
  n: number;
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
  rings: () => get<RingsResponse>(`/rings`),
  ringGraph: (id: string) => get<RingGraphData>(`/rings/${id}`),
  health: () => get<{ status: string }>(`/`),
};

export { BASE as API_BASE };
