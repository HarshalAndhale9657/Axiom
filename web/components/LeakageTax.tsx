"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { api, type Leakage, type LeakageMetrics } from "@/lib/api";
import { Card, Skeleton } from "@/components/ui";

function MetricCol({
  m, tone, badge, icon, note,
}: {
  m: LeakageMetrics; tone: "safe" | "invalid"; badge: string; icon: React.ReactNode; note: string;
}) {
  const safe = tone === "safe";
  const lift = m.pr_auc / m.prevalence;
  return (
    <div className={`rounded-xl border p-4 ${safe ? "border-blue-500/25 bg-blue-500/5" : "border-rose-500/30 bg-rose-500/5"}`}>
      <div className={`mb-2 inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold ${safe ? "bg-blue-500/15 text-blue-600 dark:text-blue-400" : "bg-rose-500/15 text-rose-600 dark:text-rose-400"}`}>
        {icon} {badge}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wide text-faint">ROC-AUC</div>
          <div className={`text-2xl font-semibold ${safe ? "text-ink" : "text-rose-600 dark:text-rose-400 line-through decoration-rose-400/50"}`}>{m.roc_auc.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wide text-faint">PR-AUC</div>
          <div className={`text-2xl font-semibold ${safe ? "text-ink" : "text-rose-600 dark:text-rose-400 line-through decoration-rose-400/50"}`}>{m.pr_auc.toFixed(2)}</div>
          <div className="text-[11px] text-muted">{safe ? `${lift.toFixed(1)}× baseline` : "impossibly good"}</div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">{note}</p>
    </div>
  );
}

export default function LeakageTax() {
  const [d, setD] = useState<Leakage | null>(null);
  useEffect(() => { api.leakage().then(setD).catch(() => {}); }, []);

  return (
    <Card>
      <div className="p-5">
        <h3 className="text-sm font-semibold text-ink">The leakage tax — why our 0.80 beats a “0.99”</h3>
        <p className="mb-3 text-xs text-muted">
          Public RTO models online brag ~0.99 ROC-AUC. That’s almost always <b className="text-ink">label leakage</b>.
          Here it is on our own data — we built the fake, then chose the true, lower number.
        </p>
        {!d ? (
          <div>
            <Skeleton className="h-28 w-full" />
            <p className="mt-2 text-[11px] text-faint">training the leaky model live to show the tax…</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <MetricCol
              m={d.honest} tone="safe" badge="Axiom · leakage-safe"
              icon={<ShieldCheck className="h-3.5 w-3.5" />}
              note="As-of / out-of-fold target encoding, time-split, natural-rate test. Believable and true."
            />
            <MetricCol
              m={d.leaky} tone="invalid" badge="Leaky model · INVALID"
              icon={<AlertTriangle className="h-3.5 w-3.5" />}
              note="Same pipeline, label leaked into the pincode/buyer encodings. For illustration only — never shipped."
            />
          </div>
        )}
      </div>
    </Card>
  );
}
