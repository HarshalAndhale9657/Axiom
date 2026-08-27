import { ShieldCheck } from "lucide-react";
import type { Metrics } from "@/lib/api";
import { inr } from "@/lib/format";

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl bg-white/10 px-4 py-2.5 ring-1 ring-white/15 backdrop-blur">
      <div className="text-[10px] font-medium uppercase tracking-wider text-indigo-200/80">{label}</div>
      <div className="text-lg font-semibold leading-tight text-white">{value}</div>
      {sub && <div className="text-[11px] text-indigo-200/70">{sub}</div>}
    </div>
  );
}

export default function TopBar({ metrics }: { metrics: Metrics | null }) {
  const m = metrics;
  const lift = m ? (m.pr_auc / m.prevalence).toFixed(1) : "–";
  return (
    <header className="bg-gradient-to-r from-indigo-950 via-slate-900 to-slate-900">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 px-6 py-5 md:flex-row md:items-center md:justify-between">
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

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Kpi label="PR-AUC" value={m ? m.pr_auc.toFixed(3) : "–"} sub={m ? `${lift}× baseline` : "loading"} />
          <Kpi label="Cost-optimal τ*" value={m ? m.tau_star.toFixed(2) : "–"} sub="vs naive 0.50" />
          <Kpi
            label="Saved / 1k orders"
            value={m ? inr(m.money.rupees_saved_per_1k_vs_block_all_cod, true) : "–"}
            sub="vs block-all-COD"
          />
          <Kpi
            label="Cost reduction"
            value={m ? `${m.money.savings_vs_block_all_cod_pct.toFixed(0)}%` : "–"}
            sub="lower total cost"
          />
        </div>
      </div>
    </header>
  );
}
