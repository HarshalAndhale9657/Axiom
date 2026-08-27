"use client";

import { Bot, Gauge, Lock, Package, ShieldCheck, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";

const NODES: { icon: ReactNode; title: string; sub: string; accent: string }[] = [
  { icon: <Package className="h-4 w-4" />, title: "Order", sub: "COD checkout, scored pre-dispatch", accent: "text-slate-500" },
  { icon: <Gauge className="h-4 w-4" />, title: "Detector", sub: "calibrated LightGBM + SHAP + anomaly", accent: "text-blue-500" },
  { icon: <SlidersHorizontal className="h-4 w-4" />, title: "Decision core", sub: "deterministic rules → cost-optimal band", accent: "text-blue-500" },
  { icon: <Bot className="h-4 w-4" />, title: "Agent (amber)", sub: "typed tools → policy RAG → structured decision", accent: "text-blue-500" },
  { icon: <ShieldCheck className="h-4 w-4" />, title: "Action", sub: "bounded, tiered dynamic friction", accent: "text-emerald-500" },
  { icon: <Lock className="h-4 w-4" />, title: "Audit", sub: "immutable log + human override", accent: "text-slate-500" },
];

export default function DecisionFlow() {
  return (
    <div>
      {NODES.map((n, i) => (
        <div key={n.title} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-surface2 ${n.accent}`}>
              {n.icon}
            </div>
            {i < NODES.length - 1 && (
              <div className="relative my-1 h-7 w-px bg-line">
                <span
                  className="flow-dot-v absolute left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-blue-500"
                  style={{ animationDelay: `${i * 0.25}s` }}
                />
              </div>
            )}
          </div>
          <div className={i < NODES.length - 1 ? "pb-3 pt-1" : "pt-1"}>
            <div className="text-sm font-semibold text-ink">{n.title}</div>
            <div className="text-xs text-muted">{n.sub}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
