"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Lock, RefreshCw } from "lucide-react";
import { api, type AuditRow } from "@/lib/api";
import { actionLabel, timeAgo } from "@/lib/format";
import { BandPill, Button, Card, Spinner } from "@/components/ui";

export default function AuditPanel() {
  const [rows, setRows] = useState<AuditRow[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    api.audit(50).then(setRows).finally(() => setLoading(false));
  };
  useEffect(load, []);

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-slate-400" />
          <div>
            <h3 className="text-sm font-semibold text-slate-800">Immutable audit trail</h3>
            <p className="text-[11px] text-slate-500">Append-only (DB-enforced). Every decision & human override is recorded.</p>
          </div>
        </div>
        <Button variant="ghost" onClick={load} disabled={loading}>
          {loading ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Refresh
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-400">
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
              <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50/60">
                <td className="px-5 py-2.5 font-mono text-xs text-slate-700">{r.order_id}</td>
                <td className="px-3 py-2.5"><BandPill band={r.band} /></td>
                <td className="px-3 py-2.5">
                  <div className="font-medium text-slate-800">{actionLabel(r.action)}</div>
                  <div className="max-w-xs truncate text-[11px] text-slate-400" title={r.reason}>{r.reason}</div>
                </td>
                <td className="px-3 py-2.5">
                  <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${r.source === "llm" ? "bg-indigo-50 text-indigo-600" : "bg-slate-100 text-slate-500"}`}>
                    {r.source === "llm" ? "Gemini" : "rules"}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  {r.overrides.length ? (
                    <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                      <span className="text-slate-400">{actionLabel(r.overrides[0].from_action)}</span>
                      <ArrowRight className="h-3 w-3 text-slate-400" />
                      <span className="font-medium text-emerald-700">{actionLabel(r.overrides[0].to_action)}</span>
                    </span>
                  ) : (
                    <span className="text-xs text-slate-300">—</span>
                  )}
                </td>
                <td className="px-5 py-2.5 text-right text-[11px] text-slate-400">{timeAgo(r.ts)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows && rows.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-slate-400">
            No decisions logged yet. Investigate an amber order to populate the trail.
          </p>
        )}
        {!rows && <div className="flex justify-center py-10"><Spinner className="text-indigo-500" /></div>}
      </div>
    </Card>
  );
}
