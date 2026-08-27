"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type CostCurve } from "@/lib/api";
import { inr, pct } from "@/lib/format";
import { Card, Spinner, Stat } from "@/components/ui";

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

  if (!data || !nearest) {
    return <div className="flex h-64 items-center justify-center"><Spinner className="text-indigo-500" /></div>;
  }

  const per1k = (c: number) => (c / data.n) * 1000;
  const chart = data.points.map((p) => ({ threshold: p.threshold, cost: Math.round(per1k(p.cost)) }));

  return (
    <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
      <Card>
        <div className="p-5">
          <h3 className="text-sm font-semibold text-slate-800">BMR cost curve</h3>
          <p className="mb-3 text-xs text-slate-500">
            Total business cost (₹ per 1,000 orders) vs decision threshold. The cost-optimal
            <b className="text-indigo-600"> τ* = {data.tau_star.toFixed(2)}</b> sits far below the naive 0.50.
          </p>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="threshold" type="number" domain={[0, 1]} tick={{ fontSize: 11, fill: "#94a3b8" }}
                  tickFormatter={(v) => v.toFixed(1)} />
                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} width={44} />
                <Tooltip
                  formatter={(v) => [inr(Number(v)), "cost / 1k"]}
                  labelFormatter={(l) => `τ = ${Number(l).toFixed(2)}`}
                  contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
                />
                <ReferenceLine y={Math.round(per1k(data.block_all_cod_cost))} stroke="#fb7185" strokeDasharray="4 4"
                  label={{ value: "block-all-COD", position: "insideTopRight", fontSize: 10, fill: "#fb7185" }} />
                <ReferenceLine x={0.5} stroke="#cbd5e1" label={{ value: "naive 0.5", position: "top", fontSize: 10, fill: "#94a3b8" }} />
                <ReferenceLine x={data.tau_star} stroke="#4f46e5" strokeDasharray="5 3"
                  label={{ value: "τ*", position: "top", fontSize: 11, fill: "#4f46e5" }} />
                <ReferenceLine x={tau} stroke="#0f172a" />
                <Line type="monotone" dataKey="cost" stroke="#4f46e5" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-slate-500">
              <span>Drag the operating threshold</span>
              <span className="text-slate-700">τ = <span className="font-mono">{tau.toFixed(2)}</span></span>
            </div>
            <input type="range" min={0.02} max={0.98} step={0.01} value={tau}
              onChange={(e) => setTau(Number(e.target.value))} className="axiom-range w-full" />
          </div>
        </div>
      </Card>

      <Card>
        <div className="space-y-4 p-5">
          <h3 className="text-sm font-semibold text-slate-800">At τ = {tau.toFixed(2)}</h3>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Cost / 1k" value={inr(per1k(nearest.cost))} sub="lower is better" />
            <Stat label="Flag rate" value={pct(nearest.flag_rate)} />
            <Stat label="Precision" value={nearest.precision != null ? pct(nearest.precision) : "–"} />
            <Stat label="Recall" value={pct(nearest.recall)} />
          </div>
          <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
            {tau <= data.tau_star + 0.01 && tau >= data.tau_star - 0.01 ? (
              <>This is the cost-optimal operating point <b>τ*</b> — minimum total rupee cost.</>
            ) : tau > data.tau_star ? (
              <>Above τ*: fewer flags, but more missed RTOs → cost rises.</>
            ) : (
              <>Below τ*: more flags → more false-positive friction on good customers → cost rises.</>
            )}
          </div>
          <div className="flex items-center justify-between rounded-xl border border-rose-100 bg-rose-50 px-3 py-2 text-xs">
            <span className="text-rose-700">Naive “block all COD”</span>
            <span className="font-semibold text-rose-700">{inr(per1k(data.block_all_cod_cost))}/1k</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
