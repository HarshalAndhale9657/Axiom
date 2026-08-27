"use client";

import { useMemo, useState } from "react";
import { UserCog } from "lucide-react";
import type { Band, QueueRow } from "@/lib/api";
import { actionLabel, inr } from "@/lib/format";
import { BandPill, ScoreMeter } from "@/components/ui";

const FILTERS: { key: "all" | Band; label: string }[] = [
  { key: "all", label: "All" },
  { key: "red", label: "Red" },
  { key: "amber", label: "Amber" },
  { key: "green", label: "Green" },
];

export default function RiskQueue({
  orders, selectedId, onSelect,
}: {
  orders: QueueRow[]; selectedId: string | null; onSelect: (id: string) => void;
}) {
  const [filter, setFilter] = useState<"all" | Band>("all");
  const counts = useMemo(() => {
    const c = { all: orders.length, green: 0, amber: 0, red: 0 } as Record<string, number>;
    orders.forEach((o) => (c[o.band] += 1));
    return c;
  }, [orders]);
  const rows = filter === "all" ? orders : orders.filter((o) => o.band === filter);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 pt-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Risk Queue</h2>
          <p className="text-xs text-slate-500">{orders.length} incoming orders scored pre-dispatch</p>
        </div>
      </div>

      <div className="flex gap-1 px-4 py-3">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              filter === f.key ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {f.label} <span className="opacity-60">{counts[f.key]}</span>
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {rows.map((o) => {
          const active = o.order_id === selectedId;
          return (
            <button
              key={o.order_id}
              onClick={() => onSelect(o.order_id)}
              className={`mb-1 w-full rounded-xl border px-3 py-2.5 text-left transition ${
                active
                  ? "border-indigo-300 bg-indigo-50/70 ring-1 ring-indigo-200"
                  : "border-transparent hover:border-slate-200 hover:bg-slate-50"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-medium text-slate-700">{o.order_id}</span>
                <div className="flex items-center gap-1.5">
                  {o.requires_human && <UserCog className="h-3.5 w-3.5 text-rose-500" />}
                  <BandPill band={o.band} />
                </div>
              </div>
              <div className="mt-2 flex items-center gap-3">
                <div className="flex-1">
                  <ScoreMeter score={o.risk_score} band={o.band} />
                </div>
                <span className="w-9 text-right font-mono text-xs text-slate-500">
                  {o.risk_score.toFixed(2)}
                </span>
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[11px]">
                <span className="text-slate-500">
                  {o.payment_method} · {actionLabel(o.action)}
                </span>
                <span className="font-medium text-slate-400">{inr(o.rupee_at_risk)} at risk</span>
              </div>
            </button>
          );
        })}
        {rows.length === 0 && (
          <p className="px-3 py-8 text-center text-sm text-slate-400">No orders in this band.</p>
        )}
      </div>
    </div>
  );
}
