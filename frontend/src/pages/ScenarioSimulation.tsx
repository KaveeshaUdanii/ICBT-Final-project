import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FlaskConical, History, Play } from "lucide-react";
import { scenariosApi, suppliersApi, materialsApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { RawMaterial, ScenarioResult, ScenarioType, Supplier } from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Field, Input, Select } from "../components/ui/Input";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";

const SCENARIOS: { value: ScenarioType; label: string; description: string }[] = [
  {
    value: "supplier_failure",
    label: "Supplier Failure",
    description: "Simulate a supplier's performance collapsing and see the risk-score impact.",
  },
  {
    value: "demand_spike",
    label: "Demand Spike",
    description: "Simulate a sudden increase in consumption of a raw material.",
  },
  {
    value: "lead_time_increase",
    label: "Lead Time Increase",
    description: "Simulate a supplier's lead time extending and see delay/production impact.",
  },
  {
    value: "raw_material_shortage",
    label: "Raw Material Shortage",
    description: "Simulate a partial shortage of a raw material and its production impact.",
  },
];

export function ScenarioSimulationPage() {
  const [scenarioType, setScenarioType] = useState<ScenarioType>("supplier_failure");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [supplierId, setSupplierId] = useState(0);
  const [materialId, setMaterialId] = useState(0);
  const [severity, setSeverity] = useState(0.6);
  const [spikePct, setSpikePct] = useState(30);
  const [addedDays, setAddedDays] = useState(7);
  const [shortagePct, setShortagePct] = useState(40);
  const [orderQuantity, setOrderQuantity] = useState(500);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [history, setHistory] = useState<ScenarioResult[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    Promise.all([suppliersApi.list(), materialsApi.list(), scenariosApi.list(20)])
      .then(([supRes, matRes, histRes]) => {
        setSuppliers(supRes.data);
        setMaterials(matRes.data);
        setSupplierId(supRes.data[0]?.id ?? 0);
        setMaterialId(matRes.data[0]?.id ?? 0);
        setHistory(histRes.data);
      })
      .catch((err) => toast.error(apiErrorMessage(err)))
      .finally(() => setLoadingHistory(false));
  }, []);

  function buildParams(): Record<string, unknown> {
    switch (scenarioType) {
      case "supplier_failure":
        return { supplier_id: supplierId, severity };
      case "demand_spike":
        return { raw_material_id: materialId, spike_percentage: spikePct };
      case "lead_time_increase":
        return { supplier_id: supplierId, added_days: addedDays, order_quantity: orderQuantity };
      case "raw_material_shortage":
        return { raw_material_id: materialId, shortage_percentage: shortagePct, order_quantity: orderQuantity };
    }
  }

  async function handleRun() {
    setRunning(true);
    try {
      const res = await scenariosApi.simulate({
        name: `${SCENARIOS.find((s) => s.value === scenarioType)?.label} — ${new Date().toLocaleString()}`,
        scenario_type: scenarioType,
        input_params: buildParams(),
      });
      setResult(res.data);
      setHistory((prev) => [res.data, ...prev]);
      toast.success("Scenario simulated.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  const activeScenario = SCENARIOS.find((s) => s.value === scenarioType)!;

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Scenario Simulation"
        description="What-if analysis for supplier failure, demand spikes, lead-time changes, and raw-material shortages — re-runs the real trained AI models on hypothetical inputs."
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <GlassCard className="p-6 xl:col-span-1">
          <div className="flex items-center gap-2 mb-4">
            <FlaskConical className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Configure Scenario</h3>
          </div>

          <div className="space-y-4">
            <Field label="Scenario Type">
              <Select value={scenarioType} onChange={(e) => setScenarioType(e.target.value as ScenarioType)}>
                {SCENARIOS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </Field>
            <p className="text-xs text-[var(--text-muted)] -mt-2">{activeScenario.description}</p>

            {(scenarioType === "supplier_failure" || scenarioType === "lead_time_increase") && (
              <Field label="Supplier">
                <Select value={supplierId} onChange={(e) => setSupplierId(Number(e.target.value))}>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}

            {(scenarioType === "demand_spike" || scenarioType === "raw_material_shortage") && (
              <Field label="Raw Material">
                <Select value={materialId} onChange={(e) => setMaterialId(Number(e.target.value))}>
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}

            {scenarioType === "supplier_failure" && (
              <Field label={`Failure severity: ${(severity * 100).toFixed(0)}%`}>
                <input
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={severity}
                  onChange={(e) => setSeverity(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </Field>
            )}

            {scenarioType === "demand_spike" && (
              <Field label="Demand spike (%)">
                <Input type="number" value={spikePct} onChange={(e) => setSpikePct(Number(e.target.value))} />
              </Field>
            )}

            {scenarioType === "lead_time_increase" && (
              <>
                <Field label="Added lead time (days)">
                  <Input type="number" value={addedDays} onChange={(e) => setAddedDays(Number(e.target.value))} />
                </Field>
                <Field label="Order quantity">
                  <Input type="number" value={orderQuantity} onChange={(e) => setOrderQuantity(Number(e.target.value))} />
                </Field>
              </>
            )}

            {scenarioType === "raw_material_shortage" && (
              <>
                <Field label="Shortage (%)">
                  <Input type="number" value={shortagePct} onChange={(e) => setShortagePct(Number(e.target.value))} />
                </Field>
                <Field label="Order quantity">
                  <Input type="number" value={orderQuantity} onChange={(e) => setOrderQuantity(Number(e.target.value))} />
                </Field>
              </>
            )}

            <Button className="w-full" onClick={handleRun} loading={running}>
              <Play className="h-4 w-4" /> Run Simulation
            </Button>
          </div>
        </GlassCard>

        <GlassCard className="p-6 xl:col-span-2">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Simulation Result</h3>
          {!result ? (
            <EmptyState message="Configure and run a scenario to see AI-driven what-if results." />
          ) : (
            <div className="space-y-4">
              <div className="glass-panel rounded-2xl p-4">
                <p className="text-sm text-[var(--text-primary)]">{String(result.result.recommendation ?? "")}</p>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(result.result)
                  .filter(([k, v]) => k !== "recommendation" && typeof v !== "object")
                  .map(([k, v]) => (
                    <div key={k} className="glass-panel rounded-xl px-3 py-2.5">
                      <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
                        {k.replace(/_/g, " ")}
                      </p>
                      <p className="text-sm font-semibold text-[var(--text-primary)]">{String(v)}</p>
                    </div>
                  ))}
              </div>
              {typeof result.result.production_impact === "object" && result.result.production_impact !== null && (
                <div className="glass-panel rounded-2xl p-4">
                  <p className="text-xs font-medium text-[var(--text-secondary)] mb-2">Production Impact Analysis</p>
                  <p className="text-sm text-[var(--text-primary)]">
                    {String((result.result.production_impact as Record<string, unknown>).explanation ?? "")}
                  </p>
                </div>
              )}
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <History className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Simulation History</h3>
        </div>
        {loadingHistory ? (
          <LoadingState message="Loading history..." />
        ) : history.length === 0 ? (
          <EmptyState message="No scenarios simulated yet." />
        ) : (
          <div className="space-y-2 max-h-80 overflow-y-auto scrollbar-thin">
            {history.map((h) => (
              <div key={h.id} className="flex items-center justify-between gap-3 glass-panel rounded-xl px-4 py-2.5 text-sm">
                <span className="text-[var(--text-primary)] truncate">{h.name}</span>
                <span className="text-xs text-[var(--text-muted)] shrink-0">
                  {new Date(h.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
