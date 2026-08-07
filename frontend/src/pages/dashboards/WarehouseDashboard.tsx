import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { AlertTriangle, Boxes, PackageSearch, RefreshCcw, TrendingUp, Truck, Warehouse } from "lucide-react";
import { analyticsApi, aiApi, materialsApi } from "../../api/endpoints";
import { apiErrorMessage } from "../../api/client";
import type { RawMaterial, WarehouseDashboardData } from "../../types";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatCard } from "../../components/ui/StatCard";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { PageHeader, Skeleton, EmptyState } from "../../components/ui/Feedback";

function stockoutTone(prob: number | null): "success" | "warning" | "danger" | "neutral" {
  if (prob === null) return "neutral";
  if (prob >= 0.66) return "danger";
  if (prob >= 0.33) return "warning";
  return "success";
}

export function WarehouseDashboard() {
  const [data, setData] = useState<WarehouseDashboardData | null>(null);
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [forecasting, setForecasting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, matRes] = await Promise.all([analyticsApi.warehouseDashboard(), materialsApi.list()]);
      setData(dash.data);
      setMaterials(matRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runForecast() {
    setForecasting(true);
    try {
      await Promise.all([aiApi.forecastAllDemand(), aiApi.predictAllStockout()]);
      toast.success("Demand forecast & stockout risk refreshed for all materials.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setForecasting(false);
    }
  }

  if (loading && !data) {
    return (
      <div className="pt-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  if (!data) return <EmptyState message="Unable to load dashboard data." />;

  const topStockoutRisk = [...materials]
    .filter((m) => m.stockout_risk_probability !== null)
    .sort((a, b) => (b.stockout_risk_probability ?? 0) - (a.stockout_risk_probability ?? 0))
    .slice(0, 8);

  const topDemand = [...materials]
    .filter((m) => m.predicted_demand_next_30_days !== null)
    .sort((a, b) => (b.predicted_demand_next_30_days ?? 0) - (a.predicted_demand_next_30_days ?? 0))
    .slice(0, 8);

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Warehouse Overview"
        description="Inventory levels, reorder alerts, and AI-forecasted demand & stockout risk for every material."
        actions={
          <Button onClick={runForecast} loading={forecasting} size="sm">
            <RefreshCcw className="h-4 w-4" /> Run Demand & Stockout Forecast
          </Button>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Raw Materials" value={data.totals.materials} icon={<Boxes className="h-5 w-5" />} />
        <StatCard
          label="Needing Reorder"
          value={data.totals.needing_reorder}
          tone="warning"
          icon={<AlertTriangle className="h-5 w-5" />}
        />
        <StatCard
          label="Incoming Shipments"
          value={data.totals.incoming_shipments}
          icon={<Truck className="h-5 w-5" />}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <PackageSearch className="h-4 w-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Reorder List</h3>
          </div>
          {data.reorder_list.length === 0 ? (
            <EmptyState message="Nothing needs reordering right now." />
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto scrollbar-thin pr-1">
              {data.reorder_list.map((m) => (
                <div key={m.id} className="flex items-center justify-between gap-3 glass-panel rounded-xl px-4 py-2.5">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">{m.name}</p>
                  <p className="text-xs text-[var(--text-muted)] shrink-0">
                    {m.quantity_on_hand} / {m.reorder_level} {m.unit}
                  </p>
                </div>
              ))}
            </div>
          )}
          <Link to="/raw-materials" className="mt-4 inline-block text-xs text-indigo-500 hover:text-indigo-400 font-medium">
            View all materials →
          </Link>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Warehouse className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Materials by Category</h3>
          </div>
          {Object.keys(data.materials_by_category).length === 0 ? (
            <EmptyState message="No materials yet." />
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(data.materials_by_category).map(([cat, count]) => (
                <div key={cat} className="glass-panel rounded-xl px-3 py-2.5">
                  <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] truncate">
                    {cat.replace(/_/g, " ")}
                  </p>
                  <p className="text-lg font-semibold text-[var(--text-primary)]">{count}</p>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Highest Stockout Risk</h3>
          </div>
          <p className="text-xs text-[var(--text-muted)] mb-4">Output of the Stockout Risk Model</p>
          {topStockoutRisk.length === 0 ? (
            <EmptyState message="Run the forecast to see stockout risk." />
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto scrollbar-thin pr-1">
              {topStockoutRisk.map((m) => (
                <div key={m.id} className="flex items-center justify-between gap-3 glass-panel rounded-xl px-4 py-2.5">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">{m.name}</p>
                  <Badge tone={stockoutTone(m.stockout_risk_probability)}>
                    {Math.round((m.stockout_risk_probability ?? 0) * 100)}%
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Highest Forecasted Demand (30d)</h3>
          </div>
          <p className="text-xs text-[var(--text-muted)] mb-4">Output of the Demand Forecasting Model</p>
          {topDemand.length === 0 ? (
            <EmptyState message="Run the forecast to see demand predictions." />
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto scrollbar-thin pr-1">
              {topDemand.map((m) => (
                <div key={m.id} className="flex items-center justify-between gap-3 glass-panel rounded-xl px-4 py-2.5">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">{m.name}</p>
                  <p className="text-xs text-[var(--text-muted)] shrink-0">
                    {Math.round(m.predicted_demand_next_30_days ?? 0)} {m.unit}
                  </p>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
