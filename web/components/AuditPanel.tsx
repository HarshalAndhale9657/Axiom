"use client";

import { useMemo, type ReactNode } from "react";
import { ArrowRight, Bot, Gavel, Lock, RefreshCw, Users, Zap } from "lucide-react";
import { api, type AuditRow } from "@/lib/api";
import { actionLabel, timeAgo } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { Async, BandPill, Button, Card, Skeleton } from "@/components/ui";

/**
 * Decode an audit `source` into something we can label truthfully.
 *
 * The stored values are `llm`, `fallback`, `batch:llm`, `batch:fallback` and `actuator` —
 * the batch runner prefixes its own decisions. A previous version compared
 * `source === "llm"` and therefore filed every autonomous batch decision under "rules",
 * which under-counted the agent and mislabelled the rows. It also hard-coded the vendor as
 * "Gemini", which stopped being true the moment the provider chain gained an OpenAI
 * fail-over.
 */
type Kind = "agent" | "rules" | "actuator";

function decodeSource(source: string): { kind: Kind; batch: boolean; label: string } {
  const batch = source.startsWith("batch:");
  const base = batch ? source.slice("batch:".length) : source;
  if (base === "actuator") return { kind: "actuator", batch, label: "actuator" };
  const kind: Kind = base === "llm" ? "agent" : "rules";
  return { kind, batch, label: kind === "agent" ? "LLM agent" : "rules" };
}

const SOURCE_STYLE: Record<Kind, string> = {
  agent: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  rules: "bg-surface2 text-muted",
  actuator: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
};

function SummaryChip({ icon, label, value, hint }: {
  icon: ReactNode; label: string; value: string | number; hint?: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-surface2 px-4 py-2.5">
      <span className="text-blue-500" aria-hidden="true">{icon}</span>
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</div>
        <div className="text-lg font-semibold leading-tight text-ink">{value}</div>
        {hint && <div className="truncate text-[10px] text-faint">{hint}</div>}
      </div>
    </div>
  );
}

export default function AuditPanel() {
  const state = useAsync<AuditRow[]>(() => api.audit(50), "audit");
  const rows = state.data;

  const summary = useMemo(() => {
    const r = rows ?? [];
    const decoded = r.map((x) => decodeSource(x.source));
    return {
      total: r.length,
      agent: decoded.filter((d) => d.kind === "agent").length,
      batch: decoded.filter((d) => d.batch).length,
      executed: decoded.filter((d) => d.kind === "actuator").length,
      overrides: r.reduce((a, x) => a + x.overrides.length, 0),
    };
  }, [rows]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryChip icon={<Lock className="h-5 w-5" />} label="Decisions logged" value={summary.total} />
        <SummaryChip
          icon={<Bot className="h-5 w-5" />}
          label="Agent decisions"
          value={summary.agent}
          hint={summary.batch ? `${summary.batch} from autonomous batch` : undefined}
        />
        <SummaryChip icon={<Zap className="h-5 w-5" />} label="Actions executed" value={summary.executed} hint="Razorpay test-mode" />
        <SummaryChip icon={<Users className="h-5 w-5" />} label="Human overrides" value={summary.overrides} />
      </div>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-faint" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-semibold text-ink">Immutable audit trail</h3>
              <p className="text-[11px] text-muted">
                Append-only, enforced by database triggers — <code className="font-mono">UPDATE</code> and{" "}
                <code className="font-mono">DELETE</code> are blocked at the storage layer, not by convention.
              </p>
            </div>
          </div>
          <Button variant="ghost" onClick={state.reload} disabled={state.loading}>
            <RefreshCw className={`h-4 w-4 ${state.loading ? "animate-spin" : ""}`} aria-hidden="true" /> Refresh
          </Button>
        </div>

        <Async
          state={state}
          skeleton={<div className="space-y-2 p-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}</div>}
        >
          {(data) =>
            data.length === 0 ? (
              <div className="flex flex-col items-center gap-2 px-5 py-12 text-center">
                <Gavel className="h-6 w-6 text-faint" aria-hidden="true" />
                <p className="text-sm font-medium text-ink">Nothing logged yet</p>
                <p className="max-w-xs text-xs text-muted">
                  Investigate an amber order, or run the autonomous batch — every decision and
                  override lands here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <caption className="sr-only">
                    Append-only log of every risk decision and human override
                  </caption>
                  <thead>
                    <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-faint">
                      <th scope="col" className="px-5 py-2 font-medium">Order</th>
                      <th scope="col" className="px-3 py-2 font-medium">Band</th>
                      <th scope="col" className="px-3 py-2 font-medium">Decision</th>
                      <th scope="col" className="px-3 py-2 font-medium">Source</th>
                      <th scope="col" className="px-3 py-2 font-medium">Human override</th>
                      <th scope="col" className="px-5 py-2 text-right font-medium">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((r) => {
                      const src = decodeSource(r.source);
                      return (
                        <tr key={r.id} className="border-b border-line/60 transition hover:bg-surface2">
                          <td className="px-5 py-2.5 font-mono text-xs text-ink">{r.order_id}</td>
                          <td className="px-3 py-2.5"><BandPill band={r.band} /></td>
                          <td className="px-3 py-2.5">
                            <div className="font-medium text-ink">{actionLabel(r.action)}</div>
                            <div className="max-w-xs truncate text-[11px] text-faint" title={r.reason}>{r.reason}</div>
                          </td>
                          <td className="px-3 py-2.5">
                            <span className={`inline-block rounded-md px-1.5 py-0.5 text-[10px] font-medium ${SOURCE_STYLE[src.kind]}`}>
                              {src.label}
                            </span>
                            {src.batch && (
                              <span className="ml-1 rounded-md bg-surface2 px-1.5 py-0.5 text-[10px] text-muted">batch</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5">
                            {r.overrides.length ? (
                              <span className="inline-flex items-center gap-1 text-xs text-muted">
                                <span className="text-faint">{actionLabel(r.overrides[0].from_action)}</span>
                                <ArrowRight className="h-3 w-3 text-faint" aria-hidden="true" />
                                <span className="font-medium text-emerald-600 dark:text-emerald-400">
                                  {actionLabel(r.overrides[0].to_action)}
                                </span>
                              </span>
                            ) : (
                              <span className="text-xs text-faint">—</span>
                            )}
                          </td>
                          <td className="px-5 py-2.5 text-right text-[11px] text-faint">{timeAgo(r.ts)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          }
        </Async>
      </Card>
    </div>
  );
}
