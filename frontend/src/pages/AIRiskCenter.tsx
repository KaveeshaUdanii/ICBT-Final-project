import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { BrainCircuit, RefreshCcw, Target } from "lucide-react";
import { aiApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { ModelPerformanceReport, RiskPrediction } from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { EmptyState, PageHeader, Skeleton } from "../components/ui/Feedback";

function MetricPill({ label, value }: { label: string; value: number | string }) {
  const isFraction = typeof value === "number" && value >= 0 && value <= 1;
  return (
    <div className="glass-panel rounded-xl px-3 py-2 text-center">
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="text-sm font-semibold text-[var(--text-primary)]">{isFraction ? `${(value * 100).toFixed(1)}%` : value}</p>
    </div>
  );
}

function ModelCard({ title, description, data }: { title: string; description: string; data: Record<string, unknown> }) {
  const metricsKey = Object.keys(data).find((k) => k.includes("metrics") || k === "ensemble");
  const metrics = (metricsKey ? data[metricsKey] : data) as Record<string, number> | undefined;

  return (
    <GlassCard className="p-6">
      <div className="flex items-start justify-between gap-2 mb-1">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      </div>
      <p className="text-xs text-[var(--text-muted)] mb-4">{description}</p>
      <p className="text-xs text-[var(--text-secondary)] mb-3">
        <span className="font-medium">Algorithm:</span> {String(data.algorithm ?? "—")}
      </p>
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          {Object.entries(metrics)
            .filter(([k]) => typeof metrics[k] === "number")
            .slice(0, 4)
            .map(([k, v]) => (
              <MetricPill key={k} label={k.replace(/_/g, " ")} value={v} />
            ))}
        </div>
      )}
      <p className="text-xs text-[var(--text-muted)]">
        Trained on {String(data.training_samples ?? "—")} samples
        {data.test_samples ? ` · tested on ${data.test_samples}` : ""}
      </p>
      {typeof data.note === "string" && <p className="text-[11px] text-[var(--text-muted)] mt-2 italic">{data.note}</p>}
    </GlassCard>
  );
}

export function AIRiskCenterPage() {
  const [report, setReport] = useState<ModelPerformanceReport | null>(null);
  const [predictions, setPredictions] = useState<RiskPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [perfRes, predRes] = await Promise.all([aiApi.modelPerformance(), aiApi.predictions({})]);
      setReport(perfRes.data);
      setPredictions(predRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function runAll() {
    setRunning(true);
    try {
      const [s, p] = await Promise.all([aiApi.scoreAllSuppliers(), aiApi.predictAllShipments()]);
      toast.success(`Scored ${s.data.length} suppliers and predicted ${p.data.length} shipments.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return (
      <div className="pt-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="AI Risk Prediction Engine"
        description="Model performance, explainability, and live prediction logs across the three AI models: Delay Prediction, Supplier Risk Scoring, and Anomaly Detection."
        actions={
          <Button onClick={runAll} loading={running} size="sm">
            <RefreshCcw className="h-4 w-4" /> Run All Predictions
          </Button>
        }
      />

      {report ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <ModelCard
              title="Delay Prediction Model"
              description="XGBoost classifier + regressor predicting shipment delay probability and magnitude."
              data={report.delay_prediction_model}
            />
            <ModelCard
              title="Supplier Risk Scoring Model"
              description="Logistic Regression + Random Forest ensemble producing a 0-100 supplier risk score."
              data={report.supplier_risk_scoring_model}
            />
            <ModelCard
              title="Anomaly Detection Model"
              description="Unsupervised Isolation Forest flagging unusual shipment patterns."
              data={report.anomaly_detection_model}
            />
          </div>
          <p className="text-xs text-[var(--text-muted)] flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5" /> Dataset: {report.dataset} · Last trained{" "}
            {new Date(report.generated_at).toLocaleString()}
          </p>
        </>
      ) : (
        <EmptyState message="Model performance report unavailable." />
      )}

      <GlassCard className="overflow-hidden">
        <div className="px-6 pt-5 pb-1 flex items-center gap-2">
          <BrainCircuit className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Recent AI Predictions</h3>
        </div>
        {predictions.length === 0 ? (
          <EmptyState message="No predictions have been run yet." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin mt-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">Model</th>
                  <th className="px-5 py-3 font-medium">Entity</th>
                  <th className="px-5 py-3 font-medium">Prediction</th>
                  <th className="px-5 py-3 font-medium">Probability</th>
                  <th className="px-5 py-3 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {predictions.slice(0, 30).map((p) => (
                  <tr key={p.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <Badge tone="accent">{p.model_name.replace(/_/g, " ")}</Badge>
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)] capitalize">
                      {p.entity_type} #{p.entity_id}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{p.prediction_value.toFixed(2)}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {p.probability !== null ? `${(p.probability * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-muted)] text-xs">
                      {new Date(p.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
