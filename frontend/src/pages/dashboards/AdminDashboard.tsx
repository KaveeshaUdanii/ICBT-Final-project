import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Blocks,
  BoxesIcon,
  BrainCircuit,
  Factory,
  PackageSearch,
  RefreshCcw,
  ShieldAlert,
  ShieldCheck,
  Truck,
  Users,
} from "lucide-react";
import { analyticsApi, aiApi, usersApi } from "../../api/endpoints";
import { apiErrorMessage } from "../../api/client";
import type { DashboardData, DelayTrendPoint, ModelPerformanceReport, RiskHeatmapCell, User } from "../../types";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatCard } from "../../components/ui/StatCard";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { PageHeader, Skeleton, EmptyState } from "../../components/ui/Feedback";
import { DelayTrendChart, RiskHeatmapList, ShipmentStatusBar, SupplierRiskPie } from "../../components/dashboard/charts";

export function AdminDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [trend, setTrend] = useState<DelayTrendPoint[]>([]);
  const [heatmap, setHeatmap] = useState<RiskHeatmapCell[]>([]);
  const [report, setReport] = useState<ModelPerformanceReport | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, trendRes, heatRes, perfRes, usersRes] = await Promise.all([
        analyticsApi.dashboard(),
        analyticsApi.delayTrend(),
        analyticsApi.riskHeatmap(),
        aiApi.modelPerformance().catch(() => null),
        usersApi.list(),
      ]);
      setData(dash.data);
      setTrend(trendRes.data.points);
      setHeatmap(heatRes.data.cells);
      setReport(perfRes?.data ?? null);
      setUsers(usersRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runFullScoring() {
    setScoring(true);
    try {
      await Promise.all([
        aiApi.scoreAllSuppliers(),
        aiApi.predictAllShipments(),
        aiApi.forecastAllDemand(),
        aiApi.predictAllStockout(),
      ]);
      toast.success("All 5 AI models refreshed across suppliers, shipments, and materials.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setScoring(false);
    }
  }

  if (loading && !data) {
    return (
      <div className="pt-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  if (!data) return <EmptyState message="Unable to load dashboard data." />;

  const activeUsers = users.filter((u) => u.is_active).length;
  const roleCounts = users.reduce<Record<string, number>>((acc, u) => {
    acc[u.role] = (acc[u.role] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Admin Overview"
        description="Full system visibility: every module, every model, every user -- plus platform health."
        actions={
          <Button onClick={runFullScoring} loading={scoring} size="sm">
            <RefreshCcw className="h-4 w-4" /> Refresh All AI Models
          </Button>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard label="Suppliers" value={data.totals.suppliers} icon={<Factory className="h-5 w-5" />} sub={`Avg risk ${data.supplier_risk.average_risk_score}%`} />
        <StatCard label="High Risk Suppliers" value={data.supplier_risk.high} tone="danger" icon={<ShieldAlert className="h-5 w-5" />} />
        <StatCard label="Active Shipments" value={data.totals.shipments} icon={<Truck className="h-5 w-5" />} sub={`${data.shipments.average_delay_probability_pct}% avg delay risk`} />
        <StatCard label="Reorder Alerts" value={data.inventory.materials_needing_reorder} tone="warning" icon={<PackageSearch className="h-5 w-5" />} />
        <StatCard label="Purchase Orders" value={data.totals.purchase_orders} icon={<BoxesIcon className="h-5 w-5" />} sub={`${data.purchase_orders.pending_approval} awaiting approval`} />
        <StatCard label="Blockchain Ledger" value={data.blockchain.total_blocks} tone={data.blockchain.chain_valid ? "success" : "danger"} icon={<Blocks className="h-5 w-5" />} sub={data.blockchain.chain_valid ? "Chain intact" : "Integrity broken!"} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-1">
          <SupplierRiskPie low={data.supplier_risk.low} medium={data.supplier_risk.medium} high={data.supplier_risk.high} />
        </div>
        <div className="xl:col-span-2">
          <DelayTrendChart trend={trend} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2">
          <ShipmentStatusBar byStatus={data.shipments.by_status} />
        </div>
        <div className="xl:col-span-1">
          <RiskHeatmapList cells={heatmap} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">System Health</h3>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Blockchain integrity</span>
              <Badge tone={data.blockchain.chain_valid ? "success" : "danger"}>
                {data.blockchain.chain_valid ? "Verified intact" : "TAMPERED"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">AI models trained</span>
              <Badge tone={report ? "success" : "danger"}>{report ? "Yes" : "Not trained"}</Badge>
            </div>
            {report && (
              <div className="flex items-center justify-between">
                <span className="text-[var(--text-secondary)]">Last trained</span>
                <span className="text-[var(--text-muted)] text-xs">{new Date(report.generated_at).toLocaleString()}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Unread notifications</span>
              <span className="text-[var(--text-primary)] font-medium">{data.notifications.unread_count}</span>
            </div>
          </div>
          <Link to="/ai-risk-center" className="mt-4 inline-flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-400 font-medium">
            <BrainCircuit className="h-3.5 w-3.5" /> View full AI Risk Center
          </Link>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Platform Users</h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-panel rounded-xl px-3 py-2.5">
              <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Total users</p>
              <p className="text-lg font-semibold text-[var(--text-primary)]">{users.length}</p>
            </div>
            <div className="glass-panel rounded-xl px-3 py-2.5">
              <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Active</p>
              <p className="text-lg font-semibold text-[var(--text-primary)]">{activeUsers}</p>
            </div>
            {Object.entries(roleCounts).map(([role, count]) => (
              <div key={role} className="glass-panel rounded-xl px-3 py-2.5 col-span-1">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] truncate">
                  {role.replace(/_/g, " ")}
                </p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">{count}</p>
              </div>
            ))}
          </div>
          <Link to="/users" className="mt-4 inline-flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-400 font-medium">
            <Users className="h-3.5 w-3.5" /> Manage users & roles
          </Link>
        </GlassCard>
      </div>
    </div>
  );
}
