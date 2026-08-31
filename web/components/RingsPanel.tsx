"use client";

import { useState } from "react";
import { Network, ShieldCheck } from "lucide-react";
import { api, type RingGraphData, type RingsResponse } from "@/lib/api";
import { pct } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";
import { BandPill, Card, ErrorState, Skeleton } from "@/components/ui";
import RingGraph from "@/components/RingGraph";

export default function RingsPanel() {
  const rings = useAsync<RingsResponse>(() => api.rings(), "rings");
  const data = rings.data;

  // The selection defaults to the first ring, derived rather than pushed into state by
  // an effect — one less render, and no window where the header and the graph disagree.
  const [picked, setPicked] = useState<string | null>(null);
  const sel = picked ?? data?.rings[0]?.ring_id ?? null;

  const graphState = useAsync<RingGraphData | null>(
    () => (sel ? api.ringGraph(sel) : Promise.resolve(null)),
    `ring:${sel ?? "none"}`,
  );
  const graph = graphState.data;

  const v = data?.validation;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-ink">Fraud-ring detection — guilt by association</h3>
              <p className="max-w-2xl text-xs text-muted">
                Rings surfaced from <b className="text-ink">shared-device topology only</b> — the graph never sees the label
                or the hidden ring flag. Then we validate the discovered rings against that held-out flag.
              </p>
            </div>
          </div>
          {v ? (
            <div className="flex items-center gap-4">
              <Metric label="Rings" value={String(v.n_rings)} />
              <Metric label="Precision" value={pct(v.precision)} />
              <Metric label="Recall" value={pct(v.recall)} />
              <div className="rounded-lg bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="mr-1 inline h-3.5 w-3.5" />{v.tp} true · {v.fp} false
              </div>
            </div>
          ) : rings.error ? (
            <span className="text-xs text-muted">validation unavailable</span>
          ) : (
            <Skeleton className="h-10 w-64" />
          )}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(280px,340px)_1fr]">
        <Card>
          <div className="p-4">
            <h4 className="mb-2 text-sm font-semibold text-ink">Detected rings</h4>
            <div className="space-y-1">
              {rings.error ? (
                <ErrorState message={rings.error.message} onRetry={rings.reload} compact />
              ) : !data ? (
                [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)
              ) : data.rings.length === 0 ? (
                <p className="px-1 py-6 text-center text-xs text-faint">
                  No shared-device clusters of three or more buyers were found.
                </p>
              ) : (
                data.rings.map((r) => (
                    <button
                      key={r.ring_id}
                      onClick={() => setPicked(r.ring_id)}
                      aria-pressed={sel === r.ring_id}
                      className={`w-full rounded-xl border px-3 py-2.5 text-left transition ${
                        sel === r.ring_id
                          ? "border-blue-400/40 bg-blue-500/10 ring-1 ring-blue-400/30"
                          : "border-transparent hover:bg-surface2"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-medium text-ink">{r.ring_id}</span>
                        <BandPill band={r.band} />
                      </div>
                      <div className="mt-1 text-[11px] text-muted">
                        {r.n_buyers} buyers · {r.n_devices} device{r.n_devices > 1 ? "s" : ""} · {r.n_orders} orders
                      </div>
                      <div className="mt-0.5 text-[11px] text-faint">ring-risk {r.ring_risk.toFixed(2)}</div>
                    </button>
                  ))
              )}
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-semibold text-ink">{sel ?? "Ring"} · shared-device network</h4>
              <div className="flex items-center gap-3 text-[11px] text-muted">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-500" /> buyer</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-rose-500" /> device</span>
              </div>
            </div>
            {graphState.error ? (
              <div className="rounded-xl bg-surface2">
                <ErrorState message="The ring graph could not be loaded." onRetry={graphState.reload} compact />
              </div>
            ) : graph ? (
              <RingGraph data={graph} />
            ) : (
              <Skeleton className="h-[420px] w-full" />
            )}
            {graph && (
              <p className="mt-2 text-[11px] text-faint">
                {graph.n_buyers} buyer accounts sharing {graph.n_devices} device{graph.n_devices > 1 ? "s" : ""} —
                the fan-out pattern of a coordinated ring. Benign single-device buyers never enter a ring.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right">
      <div className="text-[10px] font-medium uppercase tracking-wide text-faint">{label}</div>
      <div className="text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}
