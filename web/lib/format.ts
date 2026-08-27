import type { Band } from "./api";

export const inr = (n: number, compact = false) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
    notation: compact ? "compact" : "standard",
  }).format(n);

export const pct = (n: number, digits = 0) => `${(n * 100).toFixed(digits)}%`;

const ACTION_LABELS: Record<string, string> = {
  approve: "Approve",
  step_up_verification: "Step-up Verification",
  part_pay_cod: "Part-Pay COD",
  convert_cod_to_prepaid: "Convert COD → Prepaid",
  hold_for_review: "Hold for Review",
  escalate_to_human: "Escalate to Human",
};

export const actionLabel = (a: string) =>
  ACTION_LABELS[a] ?? a.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// Theme-agnostic band styling (opacity fills read well on both light and dark surfaces).
export const bandTheme: Record<Band, { text: string; chip: string; dot: string; bar: string; label: string }> = {
  green: {
    text: "text-emerald-600 dark:text-emerald-400",
    chip: "bg-emerald-500/10 ring-emerald-500/25 text-emerald-600 dark:text-emerald-400",
    dot: "bg-emerald-500", bar: "bg-emerald-500", label: "Low risk",
  },
  amber: {
    text: "text-amber-600 dark:text-amber-400",
    chip: "bg-amber-500/10 ring-amber-500/25 text-amber-600 dark:text-amber-400",
    dot: "bg-amber-500", bar: "bg-amber-500", label: "Borderline",
  },
  red: {
    text: "text-rose-600 dark:text-rose-400",
    chip: "bg-rose-500/10 ring-rose-500/25 text-rose-600 dark:text-rose-400",
    dot: "bg-rose-500", bar: "bg-rose-500", label: "High risk",
  },
};

export const timeAgo = (ts: number) => {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
};
