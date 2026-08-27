"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowRight, Bot, Lock, RefreshCw, Users } from "lucide-react";
import { api, type AuditRow } from "@/lib/api";
import { actionLabel, timeAgo } from "@/lib/format";
import { BandPill, Button, Card, Skeleton } from "@/components/ui";

function SummaryChip({ icon, label, value }: { icon: ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-surface2 px-4 py-2.5">
      <span className="text-blue-500">{icon}</span>
      <div>
        <div className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</div>
        <div className="text-lg font-semibold text-ink">{value}</div>
      </div>
    </div>
  );
}

export default function AuditPanel() {
  const [rows, setRows] = useState<AuditRow[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    api.audit(50).then(setRows).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const summary = useMemo(() => {
    const r = rows ?? [];
    return {
      total: r.length,
      gemini: r.filter((x) => x.source === "llm").length,
      overrides: r.reduce((a, x) => a + x.overrides.length, 0),
    };
  }, [rows]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <SummaryChip icon={<Lock className="h-5 w-5" />} label="Decisions logged" value={summary.total} />
        <SummaryChip icon={<Bot className="h-5 w-5" />} label="Agent (Gemini)" value={summary.gemini} />
        <SummaryChip icon={<Users className="h-5 w-5" />} label="Human overrides" value={summary.overrides} />
      </div>

      <Card>
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-faint" />
            <div>
              <h3 className="text-sm font-semibold text-ink">Immutable audit trail</h3>
              <p className="text-[11px] text-muted">Append-only (DB-enforced). Every decision & human override is recorded.</p>
            </div>
          </div>
          <Button variant="ghost" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-faint">
                <th className="px-5 py-2 font-medium">Order</th>
                <th className="px-3 py-2 font-medium">Band</th>
                <th className="px-3 py-2 font-medium">Agent decision</th>
                <th className="px-3 py-2 font-medium">Source</th>
                <th className="px-3 py-2 font-medium">Human override</th>
                <th className="px-5 py-2 text-right font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {rows?.map((r) => (
                <tr key={r.id} className="border-b border-line/60 transition hover:bg-surface2">
                  <td className="px-5 py-2.5 font-mono text-xs text-ink">{r.order_id}</td>
                  <td className="px-3 py-2.5"><BandPill band={r.band} /></td>
                  <td className="px-3 py-2.5">
                    <div className="font-medium text-ink">{actionLabel(r.action)}</div>
                    <div className="max-w-xs truncate text-[11px] text-faint" title={r.reason}>{r.reason}</div>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${r.source === "llm" ? "bg-blue-500/10 text-blue-500" : "bg-surface2 text-muted"}`}>
                      {r.source === "llm" ? "Gemini" : "rules"}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    {r.overrides.length ? (
                      <span className="inline-flex items-center gap-1 text-xs text-muted">
                        <span className="text-faint">{actionLabel(r.overrides[0].from_action)}</span>
                        <ArrowRight className="h-3 w-3 text-faint" />
                        <span className="font-medium text-emerald-600 dark:text-emerald-400">{actionLabel(r.overrides[0].to_action)}</span>
                      </span>
                    ) : (
                      <span className="text-xs text-faint">—</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-right text-[11px] text-faint">{timeAgo(r.ts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows && <div className="space-y-2 p-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}</div>}
          {rows && rows.length === 0 && (
            <p className="px-5 py-10 text-center text-sm text-faint">No decisions logged yet. Investigate an amber order to populate the trail.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
