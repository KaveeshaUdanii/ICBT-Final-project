import type { ReactNode } from "react";
import clsx from "clsx";

type Tone = "neutral" | "success" | "warning" | "danger" | "info" | "accent";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/25",
  success: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/25",
  warning: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/25",
  danger: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/25",
  info: "bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/25",
  accent: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/25",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function riskTone(level: string): Tone {
  if (level === "high") return "danger";
  if (level === "medium") return "warning";
  return "success";
}

export function severityTone(severity: string): Tone {
  if (severity === "critical") return "danger";
  if (severity === "warning") return "warning";
  return "info";
}

export function statusTone(status: string): Tone {
  switch (status) {
    case "delivered":
    case "completed":
    case "approved":
      return "success";
    case "delayed":
    case "rejected":
    case "cancelled":
      return "danger";
    case "in_transit":
    case "pending_approval":
      return "warning";
    default:
      return "neutral";
  }
}
