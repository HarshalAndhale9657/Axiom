"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Bot, CheckCircle2, ExternalLink, FileSearch, Gavel, MessagesSquare, ScrollText, Send, ShieldAlert, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { api, type AgentResult, type CaseDetail as Detail, type ExecuteResult, type Factor } from "@/lib/api";
import { actionLabel, bandTheme, inr, pct } from "@/lib/format";
import { BandPill, Button, ConfidenceBar, Card, ErrorState, KeyVal, Skeleton, Spinner } from "@/components/ui";

const ORDER_FACTS: [string, string, (v: string | number) => string][] = [
  ["payment_method", "Payment", (v) => String(v)],
  ["order_value", "Order value", (v) => inr(Number(v))],
  ["product_category", "Category", (v) => String(v)],
  ["city", "City", (v) => String(v)],
  ["city_tier", "City tier", (v) => `Tier ${v}`],
  ["pincode", "Pincode", (v) => String(v)],
  ["distance_km", "Warehouse distance", (v) => `${Number(v).toFixed(0)} km`],
  ["account_age_days", "Account age", (v) => `${v} days`],
  ["is_first_time_buyer", "First-time buyer", (v) => (Number(v) ? "Yes" : "No")],
  ["phone_verified", "Phone", (v) => (Number(v) ? "Verified" : "Unverified")],
  ["address_completeness", "Address quality", (v) => pct(Number(v))],
];

const OVERRIDE_ACTIONS = [
  "approve", "step_up_verification", "part_pay_cod", "convert_cod_to_prepaid",
  "hold_for_review", "escalate_to_human",
];

function FactorBar({ f, max }: { f: Factor; max: number }) {
  const w = (Math.abs(f.shap) / max) * 50;
  const raises = f.direction === "raises";
  return (
    <div
      className="flex items-center gap-2 py-1"
      title={`${f.label}: ${raises ? "raises" : "lowers"} risk by ${Math.abs(f.shap).toFixed(2)}`}
    >
      <div className="w-44 truncate text-xs text-muted">{f.label}</div>
      <div className="relative h-3.5 flex-1 rounded bg-surface2">
        <div className="absolute left-1/2 top-0 h-full w-px bg-line" />
        <div
          className={`absolute top-0 h-full rounded transition-all duration-500 ${raises ? "bg-rose-400" : "bg-emerald-400"}`}
          style={raises ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
        />
      </div>
      <div className={`w-12 text-right font-mono text-[11px] ${raises ? "text-rose-500" : "text-emerald-500"}`}>
        {raises ? "+" : "−"}{Math.abs(f.shap).toFixed(2)}
      </div>
    </div>
  );
}

export default function CaseDetail({
  detail, loading, error, demoTick,
}: {
  detail: Detail | null; loading: boolean; error?: boolean; demoTick?: number;
}) {
  const [agent, setAgent] = useState<AgentResult | null>(null);
  const [investigating, setInvestigating] = useState(false);
  const [ovAction, setOvAction] = useState("approve");
  const [ovReason, setOvReason] = useState("");
  const [ovDone, setOvDone] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [execRes, setExecRes] = useState<ExecuteResult | null>(null);
  const [executing, setExecuting] = useState(false);
  const [chat, setChat] = useState<{ role: "user" | "bot"; text: string; citations?: string[]; grounded?: boolean }[]>([]);
  const [askQ, setAskQ] = useState("");
  const [asking, setAsking] = useState(false);
  // Action-level failures (agent, override, execute) surface inline rather than vanishing
  // into a swallowed promise — on a live demo a silent no-op is the worst outcome.
  const [actionError, setActionError] = useState<string | null>(null);

  // NOTE: per-case state is reset by remounting — the parent passes `key={order_id}`.
  // Clearing it in an effect instead would render one frame of the previous order's
  // agent trace against the new order's header, which on a demo looks like a bug.

  // Demo auto-run: investigate, then override.
  // Seeded from the tick at mount: this component is keyed by order id, so it remounts
  // whenever the analyst selects a different case. Without this, every later selection
  // would replay the demo's auto-investigate.
  const handledTick = useRef(demoTick);
  useEffect(() => {
    if (!demoTick || demoTick === handledTick.current || !detail) return;
    handledTick.current = demoTick;
    let cancelled = false;
    (async () => {
      setInvestigating(true);
      let res: AgentResult | null = null;
      try { res = await api.investigate(detail.order_id); }
      catch { setActionError("The agent could not be reached during the demo run."); }
      finally { setInvestigating(false); }
      if (!res || cancelled) return;
      setAgent(res);
      await new Promise((r) => setTimeout(r, 1700));
      if (cancelled) return;
      setSaving(true);
      try {
        await api.override(res.decision_id, { reviewer: "analyst_1", to_action: "approve", reason: "Verified returning customer (demo)." });
        if (!cancelled) setOvDone("approve");
      } catch { /* surfaced by the inline banner below */ }
      finally { setSaving(false); }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoTick]);

  if (loading) {
    return (
      <div className="space-y-4 p-5">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-44 w-full" />
      </div>
    );
  }
  if (error) return <ErrorState message="This case could not be loaded. The Axiom API may be down." />;
  if (!detail) return <Placeholder icon={<FileSearch className="h-8 w-8 text-faint" aria-hidden="true" />} text="Select an order from the queue to inspect it." />;

  const d = detail.decision;
  const t = bandTheme[d.band];
  const maxShap = Math.max(...d.top_factors.map((f) => Math.abs(f.shap)), 0.01);
  const PAY_ACTIONS = ["convert_cod_to_prepaid", "part_pay_cod"];
  const execAction = agent && PAY_ACTIONS.includes(agent.action) ? agent.action
    : PAY_ACTIONS.includes(d.action) ? d.action : null;

  async function runAgent() {
    if (!detail) return;
    setInvestigating(true);
    setActionError(null);
    try { setAgent(await api.investigate(detail.order_id)); }
    catch { setActionError("The agent could not be reached. Check the Axiom API and try again."); }
    finally { setInvestigating(false); }
  }
  async function submitOverride() {
    if (!agent) return;
    setSaving(true);
    setActionError(null);
    try {
      await api.override(agent.decision_id, { reviewer: "analyst_1", to_action: ovAction, reason: ovReason || "manual review" });
      setOvDone(ovAction);
    } catch { setActionError("The override was not logged — nothing was written to the audit trail."); }
    finally { setSaving(false); }
  }
  async function executeAction(action: string) {
    if (!detail) return;
    setExecuting(true);
    setActionError(null);
    try { setExecRes(await api.execute(detail.order_id, action)); }
    catch { setActionError("Could not create the payment link. No action was taken."); }
    finally { setExecuting(false); }
  }
  async function ask(question: string) {
    if (!detail || !question.trim() || asking) return;
    setAskQ("");
    setChat((c) => [...c, { role: "user", text: question }]);
    setAsking(true);
    try {
      const r = await api.ask(detail.order_id, question);
      setChat((c) => [...c, { role: "bot", text: r.answer, citations: r.citations, grounded: r.grounded }]);
    } catch {
      setChat((c) => [...c, { role: "bot", text: "The copilot is unavailable right now.", grounded: false }]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="animate-in flex h-full flex-col overflow-y-auto">
      <div className="sticky top-0 z-10 border-b border-line bg-surface px-5 py-4 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold text-ink">{detail.order_id}</span>
              <BandPill band={d.band} />
            </div>
            <p className="mt-0.5 text-xs text-muted">{t.label} · {String(detail.order.payment_method)} · {inr(Number(detail.order.order_value))}</p>
          </div>
          <div className="text-right">
            <div className={`text-2xl font-semibold ${t.text}`}>{detail.risk_score.toFixed(2)}</div>
            <div className="text-[11px] text-faint">RTO risk · anomaly {detail.anomaly_score.toFixed(2)}</div>
          </div>
        </div>
      </div>

      <div className="space-y-4 p-5">
        {actionError && (
          <div role="alert" className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-ink">
            <ShieldAlert className="mt-px h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden="true" />
            <span>{actionError}</span>
            <button onClick={() => setActionError(null)} className="ml-auto text-faint hover:text-ink" aria-label="Dismiss">×</button>
          </div>
        )}

        <Card className={`${t.chip} ring-1`}>
          <div className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">Recommended action</span>
              {d.rule_id && <span className="rounded-md bg-surface px-1.5 py-0.5 text-[10px] font-medium text-muted ring-1 ring-line">{d.rule_id}</span>}
            </div>
            <div className={`mt-1 text-lg font-semibold ${t.text}`}>{actionLabel(d.action)}</div>
            <p className="mt-1 text-sm text-muted">{d.action_detail}</p>
            <p className="mt-2 text-sm text-ink">{d.reason}</p>
            {d.policy_citations.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {d.policy_citations.map((c) => (
                  <span key={c} className="rounded-md bg-surface/70 px-1.5 py-0.5 font-mono text-[10px] text-muted ring-1 ring-line">{c}</span>
                ))}
              </div>
            )}
          </div>
        </Card>

        {execAction && (
          <Card>
            <div className="p-4">
              <div className="mb-1 flex items-center gap-2">
                <Zap className="h-4 w-4 text-blue-500" />
                <h3 className="text-sm font-semibold text-ink">Execute the action — on Razorpay</h3>
              </div>
              {execRes && execRes.executed ? (
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink">{actionLabel(execRes.action || execAction)}</span>
                    <span className={`rounded-md px-2 py-0.5 text-[10px] font-medium ${execRes.simulated ? "bg-surface2 text-muted" : "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"}`}>
                      {execRes.simulated ? "simulated (offline)" : "REAL Razorpay test-mode"}
                    </span>
                  </div>
                  <a href={execRes.short_url} target="_blank" rel="noreferrer"
                    className="mt-2 inline-flex items-center gap-1.5 break-all text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">
                    <ExternalLink className="h-3.5 w-3.5 shrink-0" /> {execRes.short_url}
                  </a>
                  <div className="mt-1 font-mono text-[10px] text-faint">
                    {execRes.plink_id} · {execRes.status}
                    {execRes.deposit_inr ? ` · deposit ${inr(execRes.deposit_inr)}` : ""}
                  </div>
                  <p className="mt-1 text-[11px] text-faint">Real Razorpay test-mode link — no real money moves.</p>
                </div>
              ) : (
                <>
                  <p className="mb-2 text-xs text-muted">
                    Create a real Razorpay <b className="text-ink">test-mode</b> payment link for this bounded action.
                  </p>
                  <Button onClick={() => executeAction(execAction)} disabled={executing}>
                    {executing ? <><Spinner /> Creating link…</> : <><Zap className="h-4 w-4" /> Execute on Razorpay (test)</>}
                  </Button>
                </>
              )}
            </div>
          </Card>
        )}

        <Card>
          <div className="p-4">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-500" />
              <h3 className="text-sm font-semibold text-ink">Why — top risk drivers (SHAP)</h3>
            </div>
            {d.top_factors.map((f) => <FactorBar key={f.feature} f={f} max={maxShap} />)}
            <div className="mt-2 flex gap-4 text-[11px] text-faint">
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-rose-400" /> raises risk</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-400" /> lowers risk</span>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <h3 className="mb-1 text-sm font-semibold text-ink">Order</h3>
            <div className="grid grid-cols-2 gap-x-6">
              {ORDER_FACTS.map(([key, label, fmt]) => <KeyVal key={key} k={label} v={fmt(detail.order[key])} />)}
            </div>
            <div className="mt-2 rounded-lg bg-surface2 p-2 text-xs text-muted">{String(detail.order.address_text)}</div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-blue-500" />
                <h3 className="text-sm font-semibold text-ink">Agent investigation</h3>
              </div>
              <Button onClick={runAgent} disabled={investigating} variant={agent ? "ghost" : "primary"}>
                {investigating ? <><Spinner /> Investigating…</> : agent ? "Re-run" : <><Sparkles className="h-4 w-4" /> Investigate</>}
              </Button>
            </div>

            {!agent && !investigating && (
              <p className="text-xs text-muted">Run the bounded agent: it plans typed tools, retrieves policy, and recommends a schema-checked action — grounded and auditable.</p>
            )}
            {investigating && !agent && <Skeleton className="h-40 w-full" />}

            {agent && (
              <div className="animate-in space-y-3">
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-semibold text-blue-500">{actionLabel(agent.action)}</span>
                    <span
                      className={`rounded-md px-2 py-0.5 text-[10px] font-medium ${agent.source === "llm" ? "bg-blue-500/15 text-blue-500" : "bg-surface2 text-muted"}`}
                      title={agent.served_by ?? undefined}
                    >
                      {agent.source === "llm" ? (agent.served_by ?? "LLM agent") : "Rule fallback"}
                    </span>
                  </div>
                  <div className="mt-1"><ConfidenceBar value={agent.confidence} /></div>
                  <p className="mt-2 text-sm text-ink">{agent.rationale}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {agent.policy_citations.map((c) => (
                      <span key={c} className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-[10px] text-muted ring-1 ring-line">{c}</span>
                    ))}
                  </div>
                </div>

                {agent.verification && (
                  <div className={`rounded-xl border p-3 ${agent.verification.verdict === "veto" ? "border-amber-500/30 bg-amber-500/5" : "border-emerald-500/25 bg-emerald-500/5"}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {agent.verification.verdict === "veto"
                          ? <ShieldAlert className="h-4 w-4 text-amber-500" />
                          : <ShieldCheck className="h-4 w-4 text-emerald-500" />}
                        <span className="text-xs font-semibold text-ink">
                          {agent.verification.independent === false ? "Second-pass check" : "Independent verifier"} — {agent.verification.verdict === "veto" ? "vetoed" : "agrees"}
                        </span>
                      </div>
                      <span className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-[10px] text-muted ring-1 ring-line">{agent.verification.verifier}</span>
                    </div>
                    <p className="mt-1.5 text-[13px] text-ink">{agent.verification.reason}</p>
                    <p className="mt-1 text-[11px] text-faint">
                      {agent.verification.independent === false
                        ? "A same-vendor second pass reviewed the same evidence & policy"
                        : "A different-vendor model independently reviewed the same evidence & policy"} · confidence {pct(agent.verification.confidence)}
                      {agent.verification.verdict === "veto" && " · routed to a human"}
                    </p>
                  </div>
                )}

                <div>
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted"><FileSearch className="h-3.5 w-3.5" /> Evidence gathered</div>
                  <div className="grid grid-cols-2 gap-2">
                    {agent.evidence.map((e) => (
                      <div key={e.tool} className="rounded-lg border border-line bg-surface p-2">
                        <div className="font-mono text-[10px] text-blue-500">{e.tool}</div>
                        <div className="mt-0.5 space-y-0.5">
                          {Object.entries(e.output).map(([k, v]) => (
                            <div key={k} className="flex justify-between gap-2 text-[11px]">
                              <span className="text-faint">{k}</span>
                              <span className="font-medium text-ink">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted"><ScrollText className="h-3.5 w-3.5" /> Retrieved policy</div>
                  <ul className="space-y-1">
                    {agent.retrieved_policy.slice(0, 3).map((p, i) => (
                      <li key={i} className="rounded-lg bg-surface2 px-2 py-1 text-[11px] text-muted">{p}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl border border-line p-3">
                  <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted"><Gavel className="h-3.5 w-3.5" /> Human override</div>
                  {ovDone ? (
                    <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400"><CheckCircle2 className="h-4 w-4" /> Logged override → <b>{actionLabel(ovDone)}</b> (immutable audit).</div>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        value={ovAction}
                        onChange={(e) => setOvAction(e.target.value)}
                        aria-label="Override action"
                        className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-ink"
                      >
                        {OVERRIDE_ACTIONS.map((a) => <option key={a} value={a}>{actionLabel(a)}</option>)}
                      </select>
                      <input
                        value={ovReason}
                        onChange={(e) => setOvReason(e.target.value)}
                        placeholder="reason…"
                        aria-label="Reason for the override"
                        className="min-w-40 flex-1 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-ink"
                      />
                      <Button variant="subtle" onClick={submitOverride} disabled={saving}>{saving ? <Spinner /> : "Log override"}</Button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="mb-2 flex items-center gap-2">
              <MessagesSquare className="h-4 w-4 text-blue-500" />
              <h3 className="text-sm font-semibold text-ink">Analyst copilot</h3>
              <span className="text-[10px] text-faint">grounded in this case + policy</span>
            </div>

            {chat.length === 0 && !asking && (
              <p className="mb-2 text-xs text-muted">
                Ask about this order. The copilot answers <b className="text-ink">only</b> from the case record and
                retrieved policy — and says so when something isn’t on file.
              </p>
            )}

            {chat.length > 0 && (
              <div className="mb-2 space-y-2" aria-live="polite">
                {chat.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-[13px] ${
                      m.role === "user" ? "bg-blue-600 text-white" : "border border-line bg-surface text-ink"
                    }`}>
                      {m.text}
                      {m.role === "bot" && m.citations && m.citations.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {m.citations.map((c) => (
                            <span key={c} className="rounded bg-surface2 px-1.5 py-0.5 font-mono text-[10px] text-muted">{c}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {asking && (
                  <div className="flex justify-start">
                    <div className="inline-flex items-center gap-2 rounded-2xl border border-line bg-surface px-3 py-2 text-[13px] text-muted"><Spinner /> thinking…</div>
                  </div>
                )}
              </div>
            )}

            {chat.length === 0 && !asking && (
              <div className="mb-1 flex flex-wrap gap-1.5">
                {["Why was this flagged?", "What if the buyer verifies their phone?", "Is a hard block justified here?"].map((q) => (
                  <button key={q} onClick={() => ask(q)}
                    className="rounded-full border border-line bg-surface px-2.5 py-1 text-[11px] text-muted transition hover:bg-surface2">
                    {q}
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={(e) => { e.preventDefault(); ask(askQ); }} className="mt-2 flex items-center gap-2">
              <input
                value={askQ}
                onChange={(e) => setAskQ(e.target.value)}
                placeholder="Ask about this case…"
                aria-label="Ask the analyst copilot about this case"
                className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
              />
              <Button type="submit" disabled={asking || !askQ.trim()} className="shrink-0">
                <Send className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">Send question</span>
              </Button>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Placeholder({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-10 text-center">
      {icon}
      <p className="max-w-xs text-sm text-faint">{text}</p>
    </div>
  );
}
