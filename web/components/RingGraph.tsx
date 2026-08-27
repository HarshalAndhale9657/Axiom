"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { RingGraphData } from "@/lib/api";

// react-force-graph-2d is client-only (canvas) — load without SSR. Typed loosely on purpose.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false }) as any;

export default function RingGraph({ data }: { data: RingGraphData }) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 480, h: 420 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const gd = {
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.links.map((l) => ({ ...l })),
  };

  return (
    <div ref={ref} className="h-[420px] w-full overflow-hidden rounded-xl bg-surface2">
      <ForceGraph2D
        graphData={gd}
        width={size.w}
        height={size.h}
        backgroundColor="rgba(0,0,0,0)"
        nodeRelSize={4}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeColor={(n: any) => (n.kind === "device" ? "#f43f5e" : "#3b82f6")}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeVal={(n: any) => (n.kind === "device" ? 6 : 2)}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeLabel={(n: any) => `${n.kind}: ${n.label}`}
        linkColor={() => "rgba(148,163,184,0.35)"}
        linkWidth={1}
        cooldownTicks={80}
        d3VelocityDecay={0.35}
      />
    </div>
  );
}
