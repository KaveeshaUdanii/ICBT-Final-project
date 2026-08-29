import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { AlertTriangle, Boxes, Gauge, Sparkles, Timer, Truck } from "lucide-react";
import { aiApi, materialsApi, shipmentsApi, suppliersApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type {
  DelayPredictionResult,
  RawMaterial,
  Shipment,
  StockoutRiskResult,
  Supplier,
  SupplierRiskResult,
} from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { StatCard } from "../components/ui/StatCard";
import { Field, Select } from "../components/ui/Input";
import { PageHeader, EmptyState, Skeleton } from "../components/ui/Feedback";
import { ExplanationPanel } from "../components/ExplanationPanel";

type ModelType = "risk" | "delay" | "stockout";

const MODEL_TABS: { id: ModelType; label: string; description: string }[] = [
  { id: "risk", label: "Supplier Risk", description: "Logistic Regression + Random Forest ensemble" },
  { id: "delay", label: "Delay Prediction", description: "XGBoost classifier" },
  { id: "stockout", label: "Stockout Risk", description: "Gradient Boosting classifier" },
];

export function ModelDashboardPage() {
  const [modelType, setModelType] = useState<ModelType>("risk");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [loadingLists, setLoadingLists] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [scoring, setScoring] = useState(false);
  const [riskResult, setRiskResult] = useState<SupplierRiskResult | null>(null);
  const [delayResult, setDelayResult] = useState<DelayPredictionResult | null>(null);
  const [stockoutResult, setStockoutResult] = useState<StockoutRiskResult | null>(null);

  useEffect(() => {
    async function loadLists() {
      setLoadingLists(true);
      try {
        const [s, sh, m] = await Promise.all([suppliersApi.list(), shipmentsApi.list(), materialsApi.list()]);
        setSuppliers(s.data);
        setShipments(sh.data);
        setMaterials(m.data);
      } catch (err) {
        toast.error(apiErrorMessage(err));
      } finally {
        setLoadingLists(false);
      }
    }
    loadLists();
  }, []);

  useEffect(() => {
    setSelectedId(null);
    setRiskResult(null);
    setDelayResult(null);
    setStockoutResult(null);
  }, [modelType]);

  const supplierName = (id: number) => suppliers.find((s) => s.id === id)?.name ?? `#${id}`;

  async function handleSelect(id: number) {
    setSelectedId(id);
    setScoring(true);
    try {
      if (modelType === "risk") {
        const res = await aiApi.scoreSupplier(id);
        setRiskResult(res.data);
      } else if (modelType === "delay") {
        const res = await aiApi.predictShipment(id);
        setDelayResult(res.data);
      } else {
        const res = await aiApi.predictStockout(id);
        setStockoutResult(res.data);
      }
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setScoring(false);
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Model Explorer"
        description="Pick any real supplier, shipment, or material to see a live prediction from the AI Risk Prediction Engine, explained factor-by-factor."
      />

      <div className="flex gap-2 flex-wrap">
        {MODEL_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setModelType(tab.id)}
            className={`glass-panel rounded-xl px-4 py-2.5 text-left transition ${
              modelType === tab.id ? "border-indigo-400/50 ring-1 ring-indigo-400/30" : "hover:border-indigo-400/30"
            }`}
          >
            <p className="text-sm font-medium text-[var(--text-primary)]">{tab.label}</p>
            <p className="text-[11px] text-[var(--text-muted)]">{tab.description}</p>
          </button>
        ))}
      </div>

      <GlassCard className="p-6">
        {loadingLists ? (
          <Skeleton className="h-10 w-full max-w-md" />
        ) : (
          <div className="max-w-md">
            {modelType === "risk" && (
              <Field label="Supplier">
                <Select value={selectedId ?? ""} onChange={(e) => handleSelect(Number(e.target.value))}>
                  <option value="" disabled>
                    Choose a supplier...
                  </option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.country}, {s.category})
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            {modelType === "delay" && (
              <Field label="Shipment">
                <Select value={selectedId ?? ""} onChange={(e) => handleSelect(Number(e.target.value))}>
                  <option value="" disabled>
                    Choose a shipment...
                  </option>
                  {shipments.map((sh) => (
                    <option key={sh.id} value={sh.id}>
                      {sh.shipment_code} — {supplierName(sh.supplier_id)} (due {sh.expected_delivery_date})
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            {modelType === "stockout" && (
              <Field label="Raw material">
                <Select value={selectedId ?? ""} onChange={(e) => handleSelect(Number(e.target.value))}>
                  <option value="" disabled>
                    Choose a raw material...
                  </option>
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({m.category})
                    </option>
                  ))}
                </Select>
              </Field>
            )}
          </div>
        )}
      </GlassCard>

      {scoring && (
        <div className="space-y-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-64" />
        </div>
      )}

      {!scoring && !selectedId && !loadingLists && (
        <EmptyState message="Pick a record above to see a live prediction and its explanation." icon={<Sparkles className="h-9 w-9 opacity-60" />} />
      )}

      {!scoring && modelType === "risk" && riskResult && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard label="Risk Score" value={`${riskResult.risk_score.toFixed(1)}%`} icon={<Gauge className="h-5 w-5" />} />
            <StatCard label="Risk Level" value={riskResult.risk_level} icon={<AlertTriangle className="h-5 w-5" />} />
          </div>
          <GlassCard className="p-6">
            <ExplanationPanel explanation={riskResult.explanation} />
          </GlassCard>
        </>
      )}

      {!scoring && modelType === "delay" && delayResult && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard
              label="Delay Probability"
              value={`${(delayResult.delay_probability * 100).toFixed(1)}%`}
              icon={<Timer className="h-5 w-5" />}
            />
            <StatCard
              label="Predicted Delay"
              value={`${delayResult.predicted_delay_days.toFixed(1)} days`}
              icon={<Truck className="h-5 w-5" />}
            />
            <StatCard
              label="Anomaly"
              value={delayResult.is_anomaly ? "Flagged" : "Normal"}
              tone={delayResult.is_anomaly ? "danger" : "success"}
              icon={<AlertTriangle className="h-5 w-5" />}
            />
          </div>
          <GlassCard className="p-6">
            <ExplanationPanel explanation={delayResult.explanation} />
          </GlassCard>
        </>
      )}

      {!scoring && modelType === "stockout" && stockoutResult && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard
              label="Stockout Probability"
              value={`${(stockoutResult.stockout_risk_probability * 100).toFixed(1)}%`}
              icon={<Gauge className="h-5 w-5" />}
            />
            <StatCard
              label="Forecasted 30-Day Demand"
              value={stockoutResult.predicted_demand_next_30_days.toFixed(1)}
              icon={<Boxes className="h-5 w-5" />}
            />
          </div>
          <GlassCard className="p-6">
            <ExplanationPanel explanation={stockoutResult.explanation} />
          </GlassCard>
        </>
      )}
    </div>
  );
}
