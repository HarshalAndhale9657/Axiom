"use client";

import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, LineChart as LineChartIcon, ListChecks, ScrollText } from "lucide-react";
import { api, API_BASE, type CaseDetail as Detail, type Metrics, type QueueRow } from "@/lib/api";
import TopBar from "@/components/TopBar";
import RiskQueue from "@/components/RiskQueue";
import CaseDetail from "@/components/CaseDetail";
import CostEconomics from "@/components/CostEconomics";
import AuditPanel from "@/components/AuditPanel";
import { Card } from "@/components/ui";

type Tab = "queue" | "economics" | "audit";
const TABS: { key: Tab; label: string; icon: ReactNode }[] = [
  { key: "queue", label: "Risk Queue", icon: <ListChecks className="h-4 w-4" /> },
  { key: "economics", label: "Economics", icon: <LineChartIcon className="h-4 w-4" /> },
  { key: "audit", label: "Audit Trail", icon: <ScrollText className="h-4 w-4" /> },
];

export default function Page() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [orders, setOrders] = useState<QueueRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("queue");
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([api.metrics(), api.orders(60)])
      .then(([m, o]) => {
        setMetrics(m);
        setOrders(o);
        const first = o.find((x) => x.band === "amber") ?? o[0];
        if (first) setSelectedId(first.order_id);
      })
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setDetailLoading(true);
    api.detail(selectedId).then(setDetail).catch(() => setDetail(null)).finally(() => setDetailLoading(false));
  }, [selectedId]);

  return (
    <div className="min-h-full">
      <TopBar metrics={metrics} />

      <main className="mx-auto max-w-[1400px] px-6 py-6">
        {error ? (
          <Card className="mx-auto max-w-lg">
            <div className="flex flex-col items-center gap-3 p-8 text-center">
              <AlertTriangle className="h-8 w-8 text-amber-500" />
              <h2 className="text-lg font-semibold text-slate-800">Can’t reach the Axiom API</h2>
              <p className="text-sm text-slate-500">Start the backend, then reload:</p>
              <code className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-100">
                uvicorn src.api.main:app --reload
              </code>
              <p className="text-[11px] text-slate-400">Expected at {API_BASE}</p>
            </div>
          </Card>
        ) : (
          <>
            <div className="mb-5 inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                    tab === t.key ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {t.icon} {t.label}
                </button>
              ))}
            </div>

            {tab === "queue" && (
              <div className="grid gap-4 lg:grid-cols-[minmax(320px,380px)_1fr]">
                <Card className="h-[calc(100vh-240px)] min-h-[560px] overflow-hidden">
                  <RiskQueue orders={orders} selectedId={selectedId} onSelect={setSelectedId} />
                </Card>
                <Card className="h-[calc(100vh-240px)] min-h-[560px] overflow-hidden">
                  <CaseDetail detail={detail} loading={detailLoading} />
                </Card>
              </div>
            )}

            {tab === "economics" && <CostEconomics />}
            {tab === "audit" && <AuditPanel />}
          </>
        )}
      </main>

      <footer className="mx-auto max-w-[1400px] px-6 pb-8 pt-2 text-center text-[11px] text-slate-400">
        Axiom · defense-only · built for the Razorpay AI Buildathon (Track 2) · a calibrated LightGBM +
        a bounded Gemini agent on a $0 free tier.
      </footer>
    </div>
  );
}
