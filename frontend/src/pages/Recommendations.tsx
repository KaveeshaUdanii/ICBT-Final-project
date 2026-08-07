import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Sparkles, X } from "lucide-react";
import { recommendationsApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Recommendation } from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { Badge } from "../components/ui/Badge";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";

const ENTITY_LABELS: Record<string, string> = {
  supplier: "Alternative Supplier",
  raw_material: "Reorder Alert",
};

export function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const res = await recommendationsApi.list();
      setRecommendations(res.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDismiss(rec: Recommendation) {
    try {
      await recommendationsApi.dismiss(rec.id);
      setRecommendations((prev) => prev.filter((r) => r.id !== rec.id));
      toast.success("Recommendation dismissed.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Intelligent Recommendation Engine"
        description="Evidence-based suggestions generated automatically when a supplier is flagged high-risk or stock falls below the reorder level."
      />

      {loading ? (
        <LoadingState message="Loading recommendations..." />
      ) : recommendations.length === 0 ? (
        <GlassCard className="p-4">
          <EmptyState message="No active recommendations. Score suppliers or check raw material stock to generate some." />
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recommendations.map((rec) => (
            <GlassCard key={rec.id} className="p-5">
              <div className="flex items-start justify-between gap-3 mb-2">
                <Badge tone="accent">
                  <Sparkles className="h-3 w-3" /> {ENTITY_LABELS[rec.entity_type] ?? rec.entity_type}
                </Badge>
                <button
                  onClick={() => handleDismiss(rec)}
                  className="text-[var(--text-muted)] hover:text-rose-500 transition"
                  title="Dismiss"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="text-sm text-[var(--text-primary)]">{rec.recommendation_text}</p>
              <div className="flex items-center justify-between mt-4">
                <span className="text-xs text-[var(--text-muted)]">
                  Confidence: {(rec.confidence * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  {new Date(rec.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
                  style={{ width: `${rec.confidence * 100}%` }}
                />
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
