import type { ReactNode } from "react";
import clsx from "clsx";
import { GlassCard } from "./GlassCard";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "accent";
  sub?: ReactNode;
}

const toneRing: Record<string, string> = {
  neutral: "from-slate-400/30 to-slate-500/10",
  success: "from-emerald-400/30 to-emerald-500/10",
  warning: "from-amber-400/30 to-amber-500/10",
  danger: "from-rose-400/30 to-rose-500/10",
  accent: "from-indigo-400/30 to-violet-500/10",
};

export function StatCard({ label, value, icon, tone = "accent", sub }: StatCardProps) {
  return (
    <GlassCard className="p-5 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-medium">{label}</p>
        <p className="mt-1.5 text-2xl font-semibold text-[var(--text-primary)] truncate">{value}</p>
        {sub && <p className="mt-1 text-xs text-[var(--text-muted)]">{sub}</p>}
      </div>
      {icon && (
        <div
          className={clsx(
            "shrink-0 rounded-2xl p-2.5 bg-gradient-to-br text-[var(--text-primary)]",
            toneRing[tone]
          )}
        >
          {icon}
        </div>
      )}
    </GlassCard>
  );
}
