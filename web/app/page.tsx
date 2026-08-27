"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { AlertTriangle, Bot, LineChart as LineChartIcon, ListChecks, Network, ScrollText } from "lucide-react";
import { api, API_BASE, type CaseDetail as Detail, type Metrics, type QueueRow } from "@/lib/api";
import TopBar from "@/components/TopBar";
import RiskQueue from "@/components/RiskQueue";
import CaseDetail from "@/components/CaseDetail";
import BatchPanel from "@/components/BatchPanel";
import CostEconomics from "@/components/CostEconomics";
import RingsPanel from "@/components/RingsPanel";
import AuditPanel from "@/components/AuditPanel";
import { Card } from "@/components/ui";

type Tab = "queue" | "batch" | "economics" | "rings" | "audit";
const TABS: { key: Tab; label: string; icon: ReactNode }[] = [
  { key: "queue", label: "Risk Queue", icon: <ListChecks className="h-4 w-4" /> },
  { key: "batch", label: "Batch", icon: <Bot className="h-4 w-4" /> },
  { key: "economics", label: "Economics", icon: <LineChartIcon className="h-4 w-4" /> },
  { key: "rings", label: "Fraud Rings", icon: <Network className="h-4 w-4" /> },
  { key: "audit", label: "Audit Trail", icon: <ScrollText className="h-4 w-4" /> },
];

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export default function Page() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [orders, setOrders] = useState<QueueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("queue");
  const [error, setError] = useState(false);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoTick, setDemoTick] = useState(0);
  const abortRef = useRef(false);

  useEffect(() => {
    Promise.all([api.metrics(), api.orders(60)])
      .then(([m, o]) => {
        setMetrics(m);
        setOrders(o);
        const first = o.find((x) => x.band === "amber") ?? o[0];
        if (first) setSelectedId(first.order_id);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setDetailLoading(true);
    api.detail(selectedId).then(setDetail).catch(() => setDetail(null)).finally(() => setDetailLoading(false));
  }, [selectedId]);

  async function runDemo() {
    abortRef.current = false;
    setDemoRunning(true);
    try {
      setTab("queue");
      const amber = orders.find((o) => o.band === "amber") ?? orders[0];
      if (amber) setSelectedId(amber.order_id);
      await sleep(1900); if (abortRef.current) return;
      setDemoTick((t) => t + 1); // CaseDetail auto-investigates + overrides
      await sleep(6800); if (abortRef.current) return;
      setTab("economics");
      await sleep(5000); if (abortRef.current) return;
      setTab("audit");
      await sleep(3800);
    } finally {
      setDemoRunning(false);
    }
  }
  const onRunDemo = () => { if (demoRunning) abortRef.current = true; else runDemo(); };

  return (
    <div className="min-h-full">
      <TopBar metrics={metrics} onRunDemo={onRunDemo} demoRunning={demoRunning} />

      <main className="mx-auto max-w-[1400px] px-6 py-6">
        {error ? (
          <Card className="mx-auto max-w-lg">
            <div className="flex flex-col items-center gap-3 p-8 text-center">
              <AlertTriangle className="h-8 w-8 text-amber-500" />
              <h2 className="text-lg font-semibold text-ink">Can’t reach the Axiom API</h2>
              <p className="text-sm text-muted">Start the backend, then reload:</p>
              <code className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-100">uvicorn src.api.main:app --reload</code>
              <p className="text-[11px] text-faint">Expected at {API_BASE}</p>
            </div>
          </Card>
        ) : (
          <>
            <div className="mb-5 inline-flex rounded-xl border border-line bg-surface p-1 shadow-sm">
              {TABS.map((tb) => (
                <button
                  key={tb.key}
                  onClick={() => setTab(tb.key)}
                  className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                    tab === tb.key ? "bg-blue-600 text-white" : "text-muted hover:bg-surface2"
                  }`}
                >
                  {tb.icon} {tb.label}
                </button>
              ))}
            </div>

            {tab === "queue" && (
              <div className="grid gap-4 lg:grid-cols-[minmax(320px,380px)_1fr]">
                <Card className="h-[calc(100vh-240px)] min-h-[560px] overflow-hidden">
                  <RiskQueue orders={orders} selectedId={selectedId} onSelect={setSelectedId} loading={loading} />
                </Card>
                <Card className="h-[calc(100vh-240px)] min-h-[560px] overflow-hidden">
                  <CaseDetail detail={detail} loading={detailLoading} demoTick={demoTick} />
                </Card>
              </div>
            )}

            {tab === "batch" && <BatchPanel />}
            {tab === "economics" && <CostEconomics />}
            {tab === "rings" && <RingsPanel />}
            {tab === "audit" && <AuditPanel />}
          </>
        )}
      </main>

      <footer className="mx-auto max-w-[1400px] px-6 pb-8 pt-2 text-center text-[11px] text-faint">
        Axiom · defense-only · built for the Razorpay AI Buildathon (Track 2) · a calibrated LightGBM +
        a bounded Gemini agent on a $0 free tier.
      </footer>
    </div>
  );
}
