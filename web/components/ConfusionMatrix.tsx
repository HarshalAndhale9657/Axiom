"use client";

import type { CostPoint } from "@/lib/api";
import { inr } from "@/lib/format";

function Cell({
  title, count, cost, tone,
}: {
  title: string; count: number; cost?: number; tone: "good" | "cost";
}) {
  const styles =
    tone === "good"
      ? "border-emerald-500/20 bg-emerald-500/5"
      : "border-rose-500/25 bg-rose-500/5";
  return (
    <div className={`rounded-xl border p-3 ${styles}`}>
      <div className="text-[11px] font-medium text-muted">{title}</div>
      <div className="mt-0.5 text-xl font-semibold text-ink">{count.toLocaleString("en-IN")}</div>
      {cost !== undefined ? (
        <div className="text-xs font-medium text-rose-500">{inr(cost)} cost</div>
      ) : (
        <div className="text-xs text-emerald-600 dark:text-emerald-400">no loss</div>
      )}
    </div>
  );
}

export default function ConfusionMatrix({ point }: { point: CostPoint }) {
  const total = point.fp_cost + point.fn_cost;
  return (
    <div>
      <div className="mb-2 grid grid-cols-[70px_1fr_1fr] items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-faint">
        <span />
        <span className="text-center">Actual RTO</span>
        <span className="text-center">Actual good</span>
      </div>
      <div className="grid grid-cols-[70px_1fr_1fr] gap-2">
        <span className="self-center text-[10px] font-semibold uppercase tracking-wide text-faint">Flagged</span>
        <Cell title="Caught RTO" count={point.tp} tone="good" />
        <Cell title="Blocked good" count={point.fp} cost={point.fp_cost} tone="cost" />

        <span className="self-center text-[10px] font-semibold uppercase tracking-wide text-faint">Approved</span>
        <Cell title="Missed RTO" count={point.fn} cost={point.fn_cost} tone="cost" />
        <Cell title="Clean approve" count={point.tn} tone="good" />
      </div>
      <div className="mt-3 flex items-center justify-between rounded-xl bg-surface2 px-3 py-2">
        <span className="text-xs text-muted">Total cost of errors at this threshold</span>
        <span className="text-sm font-semibold text-ink">{inr(total)}</span>
      </div>
    </div>
  );
}
