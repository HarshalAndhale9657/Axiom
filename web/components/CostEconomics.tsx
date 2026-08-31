"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type CostCurve } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { Card, Skeleton, Stat } from "@/components/ui";
import ConfusionMatrix from "@/components/ConfusionMatrix";
import DecisionFlow from "@/components/DecisionFlow";
import LeakageTax from "@/components/LeakageTax";

export default function CostEconomics() {
  const [data, setData] = useState<CostCurve | null>(null);
  const [tau, setTau] = useState(0.21);

  useEffect(() => {
    api.costcurve().then((c) => { setData(c); setTau(c.tau_star); }).catch(() => {});
  }, []);

  const nearest = useMemo(() => {
    if (!data) return null;
    return data.points.reduce((a, b) => (Math.abs(b.threshold - tau) < Math.abs(a.threshold - tau) ? b : a));
  }, [data, tau]);

  const per1k = (c: number) => (data ? (c / data.n) * 1000 : 0);

  return (
    <div className="space-y-4">
      <LeakageTax />
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <div className="p-5">
            <h3 className="text-sm font-semibold text-ink">BMR cost curve</h3>
            <p className="mb-3 text-xs text-muted">
              Total business cost (₹ per 1,000 orders) vs decision threshold, on the held-out test split. The shipped
              threshold <b className="text-blue-500">τ = {data ? data.tau_star.toFixed(2) : "…"}</b> was fitted on the
              <b className="text-ink"> validation</b> split and frozen — it is deliberately <i>not</i> this curve&apos;s
              minimum. Both sit far below the naive 0.50.
            </p>
            <div className="h-72 w-full">
              {!data ? (
                <Skeleton className="h-full w-full" />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.points.map((p) => ({ threshold: p.threshold, cost: Math.round(per1k(p.cost)) }))}
                    margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                    <XAxis dataKey="threshold" type="number" domain={[0, 1]} tick={{ fontSize: 11, fill: "var(--faint)" }} tickFormatter={(v) => v.toFixed(1)} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--faint)" }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} width={44} />
                    <Tooltip
                      formatter={(v) => [inr(Number(v)), "cost / 1k"]}
                      labelFormatter={(l) => `τ = ${Number(l).toFixed(2)}`}
                      contentStyle={{ borderRadius: 12, border: "1px solid var(--line)", background: "var(--surface)", color: "var(--ink)", fontSize: 12 }}
                    />
                    <ReferenceLine y={Math.round(per1k(data.block_all_cod_cost))} stroke="#fb7185" strokeDasharray="4 4"
                      label={{ value: "block-all-COD", position: "insideTopRight", fontSize: 10, fill: "#fb7185" }} />
                    <ReferenceLine x={0.5} stroke="var(--faint)" label={{ value: "naive 0.5", position: "top", fontSize: 10, fill: "var(--faint)" }} />
                    {data.oracle_tau !== undefined && (
                      <ReferenceLine x={data.oracle_tau} stroke="#fca5a5" strokeDasharray="2 3"
                        label={{ value: "test-oracle (unused)", position: "insideBottomLeft", fontSize: 10, fill: "#fca5a5" }} />
                    )}
                    <ReferenceLine x={data.tau_star} stroke="#3b82f6" strokeDasharray="5 3" label={{ value: "τ (val)", position: "top", fontSize: 11, fill: "#3b82f6" }} />
                    <ReferenceLine x={tau} stroke="var(--ink)" />
                    <Line type="monotone" dataKey="cost" stroke="#3b82f6" strokeWidth={2.5} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs text-muted">
                <span>Drag the operating threshold</span>
                <span className="text-ink">τ = <span className="font-mono">{tau.toFixed(2)}</span></span>
              </div>
              <input type="range" min={0.02} max={0.98} step={0.01} value={tau}
                onChange={(e) => setTau(Number(e.target.value))} className="axiom-range w-full" disabled={!data} />
            </div>
          </div>
        </Card>

        <Card>
          <div className="space-y-4 p-5">
            <h3 className="text-sm font-semibold text-ink">At τ = {tau.toFixed(2)}</h3>
            {!nearest ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <Stat label="Cost / 1k" value={inr(per1k(nearest.cost))} sub="lower is better" />
                  <Stat label="Flag rate" value={pct(nearest.flag_rate)} />
                  <Stat label="Precision" value={nearest.precision != null ? pct(nearest.precision) : "–"} />
                  <Stat label="Recall" value={pct(nearest.recall)} />
                </div>
                <div className="rounded-xl bg-surface2 p-3 text-xs text-muted">
                  {data && Math.abs(tau - data.tau_star) <= 0.01 ? (
                    <>The shipped operating point, fitted on validation and frozen before this split was scored.</>
                  ) : data && tau > data.tau_star ? (
                    <>Above the shipped τ: fewer flags, but more missed RTOs → cost rises.</>
                  ) : (
                    <>Below the shipped τ: more flags → more false-positive friction on good customers → cost rises.</>
                  )}
                </div>
                {data?.optimism_cost_gap_per_1k !== undefined && (
                  <div className="flex items-center justify-between rounded-xl border border-line bg-surface2/50 px-3 py-2 text-xs">
                    <span className="text-muted">Optimism declined (tuning τ on test)</span>
                    <span className="font-semibold text-ink">{inr(data.optimism_cost_gap_per_1k)}/1k</span>
                  </div>
                )}
                <div className="flex items-center justify-between rounded-xl border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs">
                  <span className="text-rose-500">Naive “block all COD”</span>
                  <span className="font-semibold text-rose-500">{data ? inr(per1k(data.block_all_cod_cost)) : "…"}/1k</span>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="p-5">
            <h3 className="mb-3 text-sm font-semibold text-ink">Confusion matrix in ₹ · at τ = {tau.toFixed(2)}</h3>
            {nearest ? <ConfusionMatrix point={nearest} /> : <Skeleton className="h-56 w-full" />}
          </div>
        </Card>
        <Card>
          <div className="p-5">
            <h3 className="text-sm font-semibold text-ink">Live decision pipeline</h3>
            <p className="mb-4 text-xs text-muted">Every order flows through the same bounded, auditable path.</p>
            <DecisionFlow />
          </div>
        </Card>
      </div>
    </div>
  );
}
