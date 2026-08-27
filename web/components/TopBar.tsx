"use client";

import type { ReactNode } from "react";
import { Play, ShieldCheck, Square } from "lucide-react";
import type { Metrics } from "@/lib/api";
import { inr } from "@/lib/format";
import { CountUp, Skeleton, ThemeToggle } from "@/components/ui";

function Kpi({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) {
  return (
    <div className="rounded-xl bg-white/[0.04] px-4 py-2.5 ring-1 ring-white/10">
      <div className="text-[10px] font-medium uppercase tracking-wider text-slate-400">{label}</div>
      <div className="text-lg font-semibold leading-tight text-white">{value}</div>
      {sub && <div className="text-[11px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function TopBar({
  metrics, onRunDemo, demoRunning,
}: {
  metrics: Metrics | null; onRunDemo: () => void; demoRunning: boolean;
}) {
  const m = metrics;
  const lift = m ? (m.pr_auc / m.prevalence).toFixed(1) : "–";
  return (
    <header className="border-b border-slate-800/60 bg-gradient-to-b from-slate-900 to-slate-950">
      <div className="mx-auto max-w-[1400px] px-6 py-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/20 ring-1 ring-indigo-400/30">
              <ShieldCheck className="h-6 w-6 text-indigo-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-semibold tracking-tight text-white">Axiom</h1>
                <span className="rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-medium text-indigo-200 ring-1 ring-white/15">
                  AI Risk Manager
                </span>
              </div>
              <p className="text-xs text-slate-400">
                COD / RTO fraud · <span className="italic">Risk decisions you can prove.</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onRunDemo}
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium ring-1 transition ${
                demoRunning
                  ? "bg-rose-500/20 text-rose-200 ring-rose-400/30 hover:bg-rose-500/30"
                  : "bg-indigo-500/20 text-indigo-100 ring-indigo-400/30 hover:bg-indigo-500/30"
              }`}
            >
              {demoRunning ? <><Square className="h-4 w-4" /> Stop</> : <><Play className="h-4 w-4" /> Play demo</>}
            </button>
            <ThemeToggle />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {m ? (
            <>
              <Kpi label="PR-AUC" value={<CountUp value={m.pr_auc} format={(n) => n.toFixed(3)} />} sub={`${lift}× baseline`} />
              <Kpi label="Cost-optimal threshold" value={<CountUp value={m.tau_star} format={(n) => n.toFixed(2)} />} sub="τ* · vs naive 0.50" />
              <Kpi label="Saved / 1k orders" value={<CountUp value={m.money.rupees_saved_per_1k_vs_block_all_cod} format={(n) => inr(n, true)} />} sub="vs block-all-COD" />
              <Kpi label="Cost reduction" value={<CountUp value={m.money.savings_vs_block_all_cod_pct} format={(n) => `${n.toFixed(0)}%`} />} sub="lower total cost" />
            </>
          ) : (
            [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[62px] rounded-xl" />)
          )}
        </div>
      </div>
    </header>
  );
}
