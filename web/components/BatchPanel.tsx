"use client";

import { useState, type ReactNode } from "react";
import { Bot, CircleSlash, Coins, Play, ShieldAlert, TriangleAlert } from "lucide-react";
import { api, type BatchResult } from "@/lib/api";
import { actionLabel, inr } from "@/lib/format";
import { Button, Card, Spinner } from "@/components/ui";

export default function BatchPanel() {
  const [maxOrders, setMaxOrders] = useState(25);
  const [running, setRunning] = useState(false);
  const [res, setRes] = useState<BatchResult | null>(null);

  async function run() {
    setRunning(true);
    setRes(null);
    try {
      setRes(await api.runBatch({ max_orders: maxOrders }));
    } finally {
      setRunning(false);
    }
  }

  const netPositive = (res?.net_recovered ?? 0) >= 0;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-ink">Autonomous batch — work the whole amber queue</h3>
              <p className="max-w-2xl text-xs text-muted">
                The agent investigates every borderline order unattended, under real stopping rules
                (max orders · LLM-call budget · consecutive-low-value cutoff · quiet hours). Rupees are
                measured <b className="text-ink">post-hoc on the labelled held-out test batch</b> — and we
                show the friction cost on genuine customers too, not just the wins.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-[11px] font-medium text-faint">Max orders</label>
            <input
              type="number"
              min={1}
              max={60}
              value={maxOrders}
              onChange={(e) => setMaxOrders(Math.max(1, Math.min(60, Number(e.target.value) || 1)))}
              className="w-16 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-ink"
            />
            <Button onClick={run} disabled={running}>
              {running ? <><Spinner /> Working the queue…</> : <><Play className="h-4 w-4" /> Run autonomous batch</>}
            </Button>
          </div>
        </div>
      </Card>

      {running && !res && (
        <Card><div className="p-8 text-center text-sm text-muted"><Spinner /> The agent is investigating amber orders one by one…</div></Card>
      )}

      {res && (
        <div className="animate-in space-y-4">
          {/* Hero: honest net, with the reconciling formula shown in the open. */}
          <Card>
            <div className="grid gap-4 p-5 md:grid-cols-[1.1fr_1fr]">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-wide text-faint">Net rupees protected</div>
                <div className={`mt-1 text-4xl font-semibold ${netPositive ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                  {inr(res.net_recovered)}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-muted">
                  <span className="font-medium text-emerald-600 dark:text-emerald-400">{inr(res.recovered_gross)} recovered</span>
                  <span className="text-faint">−</span>
                  <span className="font-medium text-amber-600 dark:text-amber-400">{inr(res.friction_cost)} friction on genuine customers</span>
                </div>
                <div className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-surface2 px-2.5 py-1 text-[11px] text-muted">
                  <CircleSlash className="h-3.5 w-3.5" /> Stopped: {res.stop_reason}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Stat icon={<Coins className="h-4 w-4" />} label="RTOs caught" value={String(res.rto_caught)}
                  sub="intervened · would have returned" tone="emerald" />
                <Stat icon={<ShieldAlert className="h-4 w-4" />} label="Genuine frictioned" value={String(res.good_frictioned)}
                  sub="the honest false-positive cost" tone="amber" />
                <Stat icon={<TriangleAlert className="h-4 w-4" />} label="RTOs missed" value={String(res.rto_missed)}
                  sub={`${inr(res.missed_cost)} let through`} tone="rose" />
                <Stat icon={<Bot className="h-4 w-4" />} label="Processed" value={String(res.processed)}
                  sub={`${res.interventions} interventions`} tone="blue" />
              </div>
            </div>
          </Card>

          {/* Per-order actions log — the receipts. */}
          <Card>
            <div className="p-4">
              <h4 className="mb-2 text-sm font-semibold text-ink">Actions log — every decision audited</h4>
              <div className="max-h-[420px] overflow-y-auto rounded-lg border border-line">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-surface2 text-[10px] uppercase tracking-wide text-faint">
                    <tr>
                      <th className="px-3 py-2 font-medium">Order</th>
                      <th className="px-3 py-2 font-medium">Action</th>
                      <th className="px-3 py-2 text-right font-medium">Value</th>
                      <th className="px-3 py-2 text-center font-medium">Outcome</th>
                      <th className="px-3 py-2 text-right font-medium">₹ effect</th>
                    </tr>
                  </thead>
                  <tbody>
                    {res.actions.map((a, i) => (
                      <tr key={a.decision_id} className="animate-in border-t border-line/60" style={{ animationDelay: `${Math.min(i * 35, 700)}ms` }}>
                        <td className="px-3 py-2 font-mono text-[11px] text-ink">{a.order_id}</td>
                        <td className="px-3 py-2">
                          <span className="text-ink">{actionLabel(a.action)}</span>
                          {a.source === "fallback" && <span className="ml-1 text-[10px] text-faint">(rule)</span>}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-muted">{inr(a.order_value)}</td>
                        <td className="px-3 py-2 text-center">
                          {a.is_rto ? (
                            <span className="rounded-md bg-rose-500/10 px-1.5 py-0.5 text-[10px] font-medium text-rose-600 dark:text-rose-400">would RTO</span>
                          ) : (
                            <span className="rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">genuine</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right font-mono">
                          {a.recovered > 0 ? (
                            <span className="text-emerald-600 dark:text-emerald-400">+{inr(a.recovered)}</span>
                          ) : a.friction_cost > 0 ? (
                            <span className="text-amber-600 dark:text-amber-400">−{inr(a.friction_cost)}</span>
                          ) : (
                            <span className="text-faint">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-[11px] text-faint">{res.basis}</p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

const TONE: Record<string, string> = {
  emerald: "text-emerald-600 dark:text-emerald-400",
  amber: "text-amber-600 dark:text-amber-400",
  rose: "text-rose-600 dark:text-rose-400",
  blue: "text-blue-600 dark:text-blue-400",
};

function Stat({ icon, label, value, sub, tone }: {
  icon: ReactNode; label: string; value: string; sub: string; tone: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <div className={`flex items-center gap-1.5 text-[11px] font-medium ${TONE[tone]}`}>{icon} {label}</div>
      <div className="mt-0.5 text-2xl font-semibold text-ink">{value}</div>
      <div className="text-[10px] text-faint">{sub}</div>
    </div>
  );
}
