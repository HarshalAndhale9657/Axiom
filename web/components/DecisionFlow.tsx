"use client";

import { Bot, Gauge, Lock, Package, ShieldCheck, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";

const NODES: { icon: ReactNode; title: string; sub: string; accent: string }[] = [
  { icon: <Package className="h-4 w-4" />, title: "Order", sub: "COD checkout", accent: "text-slate-500" },
  { icon: <Gauge className="h-4 w-4" />, title: "Detector", sub: "calibrated LightGBM", accent: "text-indigo-500" },
  { icon: <SlidersHorizontal className="h-4 w-4" />, title: "Decision core", sub: "rules → band", accent: "text-violet-500" },
  { icon: <Bot className="h-4 w-4" />, title: "Agent", sub: "tools + policy RAG", accent: "text-fuchsia-500" },
  { icon: <ShieldCheck className="h-4 w-4" />, title: "Action", sub: "bounded, tiered", accent: "text-emerald-500" },
  { icon: <Lock className="h-4 w-4" />, title: "Audit", sub: "immutable log", accent: "text-slate-500" },
];

function Connector() {
  return (
    <div className="relative mx-1 hidden h-px min-w-6 flex-1 self-center bg-line sm:block">
      <span className="flow-dot absolute -top-[3px] h-1.5 w-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_2px_rgba(99,102,241,0.5)]" />
    </div>
  );
}

export default function DecisionFlow() {
  return (
    <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
      {NODES.map((n, i) => (
        <div key={n.title} className="flex items-center gap-2 sm:contents">
          <div className="pulse-node flex flex-1 items-center gap-2 rounded-xl border border-line bg-surface2 px-3 py-2" style={{ animationDelay: `${i * 0.2}s` }}>
            <span className={n.accent}>{n.icon}</span>
            <div className="leading-tight">
              <div className="text-xs font-semibold text-ink">{n.title}</div>
              <div className="text-[10px] text-muted">{n.sub}</div>
            </div>
          </div>
          {i < NODES.length - 1 && <Connector />}
        </div>
      ))}
    </div>
  );
}
