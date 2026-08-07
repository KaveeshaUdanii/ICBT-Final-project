import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { Boxes, ClipboardCheck, Factory, PackageSearch, RefreshCcw, ShieldAlert, Sparkles, Truck } from "lucide-react";
import { analyticsApi, aiApi, purchaseOrdersApi, recommendationsApi } from "../../api/endpoints";
import { apiErrorMessage } from "../../api/client";
import type { DashboardData, DelayTrendPoint, PurchaseOrder, Recommendation, RiskHeatmapCell } from "../../types";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatCard } from "../../components/ui/StatCard";
import { Button } from "../../components/ui/Button";
import { PageHeader, Skeleton, EmptyState } from "../../components/ui/Feedback";
import { DelayTrendChart, RiskHeatmapList, ShipmentStatusBar, SupplierRiskPie } from "../../components/dashboard/charts";

export function ManagerDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [trend, setTrend] = useState<DelayTrendPoint[]>([]);
  const [heatmap, setHeatmap] = useState<RiskHeatmapCell[]>([]);
  const [pendingPOs, setPendingPOs] = useState<PurchaseOrder[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, trendRes, heatRes, poRes, recRes] = await Promise.all([
        analyticsApi.dashboard(),
        analyticsApi.delayTrend(),
        analyticsApi.riskHeatmap(),
        purchaseOrdersApi.list({ status_filter: "pending_approval" }),
        recommendationsApi.list({ entity_type: "supplier" }),
      ]);
      setData(dash.data);
      setTrend(trendRes.data.points);
      setHeatmap(heatRes.data.cells);
      setPendingPOs(poRes.data);
      setRecommendations(recRes.data.slice(0, 5));
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runScoring() {
    setScoring(true);
    try {
      await Promise.all([aiApi.scoreAllSuppliers(), aiApi.predictAllShipments()]);
      toast.success("Supplier risk & shipment delay predictions refreshed.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setScoring(false);
    }
  }

  async function handleApprove(po: PurchaseOrder) {
    try {
      await purchaseOrdersApi.approve(po.id);
      toast.success(`PO ${po.po_number} approved.`);
      setPendingPOs((prev) => prev.filter((p) => p.id !== po.id));
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  if (loading && !data) {
    return (
      <div className="pt-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  if (!data) return <EmptyState message="Unable to load dashboard data." />;

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Supply Chain Manager Overview"
        description="Supplier risk, delay predictions, and the approvals that need your decision today."
        actions={
          <Button onClick={runScoring} loading={scoring} size="sm">
            <RefreshCcw className="h-4 w-4" /> Refresh Predictions
          </Button>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        <StatCard label="Suppliers" value={data.totals.suppliers} icon={<Factory className="h-5 w-5" />} sub={`Avg risk ${data.supplier_risk.average_risk_score}%`} />
        <StatCard label="High Risk Suppliers" value={data.supplier_risk.high} tone="danger" icon={<ShieldAlert className="h-5 w-5" />} />
        <StatCard label="Active Shipments" value={data.totals.shipments} icon={<Truck className="h-5 w-5" />} sub={`${data.shipments.average_delay_probability_pct}% avg delay risk`} />
        <StatCard label="Pending Approvals" value={data.purchase_orders.pending_approval} tone="warning" icon={<ClipboardCheck className="h-5 w-5" />} />
        <StatCard label="Purchase Orders" value={data.totals.purchase_orders} icon={<Boxes className="h-5 w-5" />} sub={`${data.purchase_orders.flagged_high_risk} flagged high-risk`} />
      </div>

      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <ClipboardCheck className="h-4 w-4 text-amber-400" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Purchase Orders Awaiting Your Approval</h3>
        </div>
        {pendingPOs.length === 0 ? (
          <EmptyState message="Nothing pending -- you're all caught up." />
        ) : (
          <div className="space-y-2">
            {pendingPOs.map((po) => (
              <div key={po.id} className="flex items-center justify-between gap-3 glass-panel rounded-xl px-4 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)] flex items-center gap-1.5">
                    {po.po_number}
                    {po.risk_flag && (
                      <span title={po.risk_notes}>
                        <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    ${po.total_value.toLocaleString()} · due {po.expected_delivery_date}
                  </p>
                </div>
                <Button size="sm" variant="secondary" onClick={() => handleApprove(po)}>
                  Approve
                </Button>
              </div>
            ))}
          </div>
        )}
        <Link to="/purchase-orders" className="mt-4 inline-block text-xs text-indigo-500 hover:text-indigo-400 font-medium">
          View all purchase orders →
        </Link>
      </GlassCard>

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

      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Latest Recommendations</h3>
          </div>
          <Link to="/recommendations" className="text-xs text-indigo-500 hover:text-indigo-400 font-medium">
            View all →
          </Link>
        </div>
        {recommendations.length === 0 ? (
          <EmptyState message="No active recommendations." icon={<PackageSearch className="h-9 w-9 opacity-60" />} />
        ) : (
          <div className="space-y-2">
            {recommendations.map((r) => (
              <p key={r.id} className="glass-panel rounded-xl px-4 py-2.5 text-sm text-[var(--text-secondary)]">
                {r.recommendation_text}
              </p>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
