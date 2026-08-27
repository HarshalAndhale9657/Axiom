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

export const bandTheme: Record<Band, { text: string; bg: string; ring: string; dot: string; label: string }> = {
  green: { text: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200", dot: "bg-emerald-500", label: "Low risk" },
  amber: { text: "text-amber-700", bg: "bg-amber-50", ring: "ring-amber-200", dot: "bg-amber-500", label: "Borderline" },
  red: { text: "text-rose-700", bg: "bg-rose-50", ring: "ring-rose-200", dot: "bg-rose-500", label: "High risk" },
};

export const timeAgo = (ts: number) => {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
};
