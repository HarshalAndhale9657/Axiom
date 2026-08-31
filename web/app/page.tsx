"use client";

import { useRef, useState, type ReactNode } from "react";
import { AlertTriangle, Bot, LineChart as LineChartIcon, ListChecks, Microscope, Network, ScrollText } from "lucide-react";
import { api, API_BASE, type CaseDetail as Detail, type Metrics, type QueueRow } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import TopBar from "@/components/TopBar";
import RiskQueue from "@/components/RiskQueue";
import CaseDetail from "@/components/CaseDetail";
import BatchPanel from "@/components/BatchPanel";
import CostEconomics from "@/components/CostEconomics";
import RingsPanel from "@/components/RingsPanel";
import RigorPanel from "@/components/RigorPanel";
import AuditPanel from "@/components/AuditPanel";
import { Button, Card } from "@/components/ui";

type Tab = "queue" | "batch" | "economics" | "rigor" | "rings" | "audit";
const TABS: { key: Tab; label: string; icon: ReactNode }[] = [
  { key: "queue", label: "Risk Queue", icon: <ListChecks className="h-4 w-4" /> },
  { key: "batch", label: "Batch", icon: <Bot className="h-4 w-4" /> },
  { key: "economics", label: "Economics", icon: <LineChartIcon className="h-4 w-4" /> },
  { key: "rigor", label: "Evidence", icon: <Microscope className="h-4 w-4" /> },
  { key: "rings", label: "Fraud Rings", icon: <Network className="h-4 w-4" /> },
  { key: "audit", label: "Audit Trail", icon: <ScrollText className="h-4 w-4" /> },
];

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export default function Page() {
  const [tab, setTab] = useState<Tab>("queue");
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoTick, setDemoTick] = useState(0);
  const abortRef = useRef(false);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const shell = useAsync<[Metrics, QueueRow[]]>(
    () => Promise.all([api.metrics(), api.orders(60)]),
    "shell",
  );
  const metrics = shell.data?.[0] ?? null;
  const orders = shell.data?.[1] ?? [];
  const loading = shell.loading;
  const error = Boolean(shell.error);

  // The selected order defaults to the first amber one — derived, so the queue and the
  // case pane can never briefly disagree about which order is open.
  const [picked, setPicked] = useState<string | null>(null);
  const selectedId = picked ?? orders.find((o) => o.band === "amber")?.order_id ?? orders[0]?.order_id ?? null;

  const caseState = useAsync<Detail | null>(
    () => (selectedId ? api.detail(selectedId) : Promise.resolve(null)),
    `case:${selectedId ?? "none"}`,
  );

  async function runDemo() {
    abortRef.current = false;
    setDemoRunning(true);
    try {
      setTab("queue");
      const amber = orders.find((o) => o.band === "amber") ?? orders[0];
      if (amber) setPicked(amber.order_id);
      await sleep(1900); if (abortRef.current) return;
      setDemoTick((t) => t + 1); // CaseDetail auto-investigates + overrides
      await sleep(6800); if (abortRef.current) return;
      setTab("economics");
      await sleep(4600); if (abortRef.current) return;
      setTab("rigor");
      await sleep(5200); if (abortRef.current) return;
      setTab("audit");
      await sleep(3600);
    } finally {
      setDemoRunning(false);
    }
  }
  const onRunDemo = () => { if (demoRunning) abortRef.current = true; else runDemo(); };

  // Roving-focus arrow navigation, which is what a tablist is expected to do. Without it a
  // keyboard user has to tab through all six tabs to reach the panel.
  function onTabKeyDown(e: React.KeyboardEvent, index: number) {
    const delta = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!delta && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const next = e.key === "Home" ? 0
      : e.key === "End" ? TABS.length - 1
      : (index + delta + TABS.length) % TABS.length;
    setTab(TABS[next].key);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className="min-h-full">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>

      <TopBar metrics={metrics} onRunDemo={onRunDemo} demoRunning={demoRunning} />

      <main id="main" className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6">
        {error ? (
          <Card className="mx-auto max-w-lg">
            <div className="flex flex-col items-center gap-3 p-8 text-center">
              <AlertTriangle className="h-8 w-8 text-amber-500" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">Can’t reach the Axiom API</h2>
              <p className="text-sm text-muted">Start the backend, then retry:</p>
              <code className="rounded-lg bg-slate-900 px-3 py-2 text-xs text-slate-100">uvicorn src.api.main:app --reload</code>
              <p className="text-[11px] text-faint">Expected at {API_BASE}</p>
              <Button variant="ghost" onClick={shell.reload} className="mt-1">Retry</Button>
            </div>
          </Card>
        ) : (
          <>
            {/* Six tabs overflow a phone; scroll them rather than letting the bar wrap or clip. */}
            <div className="-mx-4 mb-5 overflow-x-auto px-4 sm:mx-0 sm:px-0">
              <div
                role="tablist"
                aria-label="Console sections"
                className="inline-flex rounded-xl border border-line bg-surface p-1 shadow-sm"
              >
                {TABS.map((tb, i) => (
                  <button
                    key={tb.key}
                    ref={(el) => { tabRefs.current[i] = el; }}
                    role="tab"
                    id={`tab-${tb.key}`}
                    aria-selected={tab === tb.key}
                    aria-controls={`panel-${tb.key}`}
                    tabIndex={tab === tb.key ? 0 : -1}
                    onKeyDown={(e) => onTabKeyDown(e, i)}
                    onClick={() => setTab(tb.key)}
                    className={`inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition sm:px-4 ${
                      tab === tb.key ? "bg-blue-600 text-white" : "text-muted hover:bg-surface2 hover:text-ink"
                    }`}
                  >
                    <span aria-hidden="true">{tb.icon}</span> {tb.label}
                  </button>
                ))}
              </div>
            </div>

            <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} tabIndex={-1}>
              {tab === "queue" && (
                // On a phone the two panes stack, so pinning both to the viewport height would
                // create two nested scroll areas. Full height only from lg upward.
                <div className="grid gap-4 lg:grid-cols-[minmax(320px,380px)_1fr]">
                  <Card className="max-h-[70vh] overflow-hidden lg:h-[calc(100vh-240px)] lg:max-h-none lg:min-h-[560px]">
                    <RiskQueue orders={orders} selectedId={selectedId} onSelect={setPicked} loading={loading} />
                  </Card>
                  <Card className="overflow-hidden lg:h-[calc(100vh-240px)] lg:min-h-[560px]">
                    <CaseDetail
                      key={selectedId ?? "none"}
                      detail={caseState.data}
                      loading={caseState.loading}
                      error={Boolean(caseState.error)}
                      demoTick={demoTick}
                    />
                  </Card>
                </div>
              )}

              {tab === "batch" && <BatchPanel />}
              {tab === "economics" && <CostEconomics />}
              {tab === "rigor" && <RigorPanel />}
              {tab === "rings" && <RingsPanel />}
              {tab === "audit" && <AuditPanel />}
            </div>
          </>
        )}
      </main>

      <footer className="mx-auto max-w-[1400px] px-6 pb-8 pt-2 text-center text-[11px] text-faint">
        Axiom · defense-only · built for the Razorpay AI Buildathon (Track 2) · a calibrated LightGBM +
        a bounded agent on a $0 free tier. Orders shown are the held-out test split — data the model never trained on.
      </footer>
    </div>
  );
}
