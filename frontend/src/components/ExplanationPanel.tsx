import { useState } from "react";
import { ChevronDown, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import clsx from "clsx";
import type { ExplanationResult } from "../types";

export function ExplanationPanel({ explanation }: { explanation: ExplanationResult }) {
  const [showMethodology, setShowMethodology] = useState(false);
  const maxAbs = Math.max(...explanation.top_factors.map((f) => Math.abs(f.contribution)), 0.001);

  return (
    <div className="space-y-5">
      <div className="flex gap-3 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/15 p-4">
        <div className="h-8 w-8 shrink-0 rounded-xl bg-indigo-500/15 flex items-center justify-center">
          <Sparkles className="h-4 w-4 text-indigo-500" />
        </div>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-indigo-500/80 mb-0.5">
            Why this prediction
          </p>
          <p className="text-sm text-[var(--text-primary)] leading-relaxed">{explanation.plain_language_summary}</p>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide mb-3">
          Contributing factors
        </p>
        <div className="space-y-2.5">
          {explanation.top_factors.map((factor) => {
            const isUp = factor.direction === "increases_risk";
            const widthPct = Math.max((Math.abs(factor.contribution) / maxAbs) * 100, 6);
            return (
              <div key={factor.feature} className="glass-panel rounded-xl px-3.5 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">{factor.label}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{factor.explanation}</p>
                  </div>
                  <span
                    className={clsx(
                      "shrink-0 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
                      isUp
                        ? "bg-rose-500/15 text-rose-700 dark:text-rose-300"
                        : "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                    )}
                  >
                    {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {isUp ? "Raises risk" : "Lowers risk"}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-black/5 dark:bg-white/10 overflow-hidden mt-2.5">
                  <div
                    className={clsx("h-full rounded-full", isUp ? "bg-rose-500" : "bg-emerald-500")}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="border-t border-white/10 pt-3">
        <button
          onClick={() => setShowMethodology((v) => !v)}
          className="flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition"
        >
          <ChevronDown className={clsx("h-3.5 w-3.5 transition-transform", showMethodology && "rotate-180")} />
          How this explanation is calculated
        </button>
        {showMethodology && (
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mt-2">
            A LIME-style local surrogate model ({explanation.model_name}): the instance is perturbed with nearby
            samples, the real model scores each one, and a weighted linear model fit to those samples yields each
            feature's local contribution to this specific prediction.
          </p>
        )}
      </div>
    </div>
  );
}
