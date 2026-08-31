"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { AlertTriangle, Moon, RefreshCw, Sun } from "lucide-react";
import type { Band } from "@/lib/api";
import { bandTheme } from "@/lib/format";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`themed rounded-2xl border border-line bg-surface shadow-sm ${className}`}>
      {children}
    </div>
  );
}

type Variant = "primary" | "ghost" | "subtle" | "danger";
const variants: Record<Variant, string> = {
  primary: "bg-blue-600 text-white hover:bg-blue-500 shadow-sm shadow-blue-600/25",
  ghost: "bg-surface text-ink border border-line hover:bg-surface2",
  subtle: "bg-surface2 text-ink hover:brightness-95 dark:hover:brightness-125",
  danger: "bg-rose-600 text-white hover:bg-rose-500",
};

export function Button({
  children, onClick, variant = "primary", disabled, className = "", type = "button",
}: {
  children: ReactNode; onClick?: () => void; variant?: Variant; disabled?: boolean;
  className?: string; type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  );
}

export function BandPill({ band, className = "" }: { band: Band; className?: string }) {
  const t = bandTheme[band];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset transition-colors ${t.chip} ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} />
      {band}
    </span>
  );
}

export function ScoreMeter({ score, band }: { score: number; band: Band }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-surface2">
      <div
        className={`h-full rounded-full ${bandTheme[band].bar} transition-all duration-500`}
        style={{ width: `${Math.min(100, Math.max(3, score * 100))}%` }}
      />
    </div>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-surface2">
        <div className="h-full rounded-full bg-blue-500 transition-all duration-700" style={{ width: `${value * 100}%` }} />
      </div>
      <span className="text-xs font-medium text-muted">{Math.round(value * 100)}%</span>
    </div>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-medium uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-ink">{value}</div>
      {sub && <div className="text-xs text-muted">{sub}</div>}
    </div>
  );
}

export function KeyVal({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="text-xs text-muted">{k}</span>
      <span className="text-right text-sm font-medium text-ink">{v}</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} aria-hidden="true" />;
}

/**
 * What a panel shows when its request failed.
 *
 * The old behaviour was `.catch(() => {})`, which leaves a skeleton shimmering forever —
 * the panel looks like it is still working, so nobody realises the backend is down. On a
 * live demo that is the difference between "one moment, let me restart the API" and
 * standing in silence. Says what broke and offers the retry.
 */
export function ErrorState({
  message, onRetry, compact = false,
}: {
  message?: string; onRetry?: () => void; compact?: boolean;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center gap-2 text-center ${compact ? "p-5" : "p-10"}`}
    >
      <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden="true" />
      <p className="text-sm font-medium text-ink">Could not load this panel</p>
      <p className="max-w-sm text-xs text-muted">
        {message || "The Axiom API did not respond. Check that the backend is running."}
      </p>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry} className="mt-1">
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </Button>
      )}
    </div>
  );
}

/**
 * Renders exactly one of loading / error / content, so no panel can invent a fourth state
 * (the "shimmering forever" one). `skeleton` lets each panel keep its own shaped loader.
 */
export function Async<T>({
  state, skeleton, children, compact,
}: {
  state: { data: T | null; error: Error | null; loading: boolean; reload: () => void };
  skeleton: ReactNode;
  children: (data: T) => ReactNode;
  compact?: boolean;
}) {
  if (state.error) return <ErrorState message={state.error.message} onRetry={state.reload} compact={compact} />;
  if (state.data === null) return <>{skeleton}</>;
  return <>{children(state.data)}</>;
}

/* ---- animated number ---- */
function useCountUp(target: number, duration = 900) {
  const [v, setV] = useState(0);
  const prev = useRef(0);
  useEffect(() => {
    const from = prev.current;
    prev.current = target;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setV(from + (target - from) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return v;
}

export function CountUp({ value, format }: { value: number; format: (n: number) => string }) {
  const v = useCountUp(value);
  return <>{format(v)}</>;
}

/* The active theme lives on <html>, which is an external store as far as React is
   concerned: an inline script in the document head sets it before first paint so there
   is no flash. useSyncExternalStore is the sanctioned way to read that — it gives the
   server the light default, the client the real value, and no mount effect. */
const themeStore = {
  subscribe(onChange: () => void) {
    const observer = new MutationObserver(onChange);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  },
  get: () => document.documentElement.classList.contains("dark"),
  getServer: () => false, // light is the default
};

export function ThemeToggle() {
  const dark = useSyncExternalStore(themeStore.subscribe, themeStore.get, themeStore.getServer);

  const toggle = useCallback(() => {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("axiom-theme", next ? "dark" : "light"); } catch {}
  }, []);

  return (
    <button
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      aria-pressed={dark}
      title={dark ? "Light theme" : "Dark theme"}
      className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 text-slate-200 ring-1 ring-white/15 transition hover:bg-white/20"
    >
      {dark ? <Sun className="h-4 w-4" aria-hidden="true" /> : <Moon className="h-4 w-4" aria-hidden="true" />}
    </button>
  );
}
