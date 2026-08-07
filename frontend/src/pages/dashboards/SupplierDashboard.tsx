import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Boxes, ClipboardList, Handshake, Timer, Truck } from "lucide-react";
import { analyticsApi } from "../../api/endpoints";
import { apiErrorMessage } from "../../api/client";
import type { MyDashboardData } from "../../types";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatCard } from "../../components/ui/StatCard";
import { Badge, statusTone } from "../../components/ui/Badge";
import { PageHeader, Skeleton, EmptyState } from "../../components/ui/Feedback";

export function SupplierDashboard() {
  const [data, setData] = useState<MyDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await analyticsApi.myDashboard();
      setData(res.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return (
      <div className="pt-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!data) return <EmptyState message="Unable to load your dashboard." />;

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Supplier Portal"
        description="Your shipments and purchase orders with this organization."
      />

      {!data.supplier ? (
        <EmptyState message="No supplier profile is linked to your account yet. Contact your account manager." />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard label="Your Shipments" value={data.shipments.total} icon={<Truck className="h-5 w-5" />} />
            <StatCard label="Your Purchase Orders" value={data.purchase_orders.total} icon={<Boxes className="h-5 w-5" />} />
            <StatCard
              label="On-Time Delivery Rate"
              value={`${data.supplier.on_time_delivery_rate}%`}
              icon={<Timer className="h-5 w-5" />}
            />
          </div>

          <GlassCard className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Handshake className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Your Partnership Snapshot</h3>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Supplier Name</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">{data.supplier.name}</p>
              </div>
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Avg. Lead Time</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">{data.supplier.avg_lead_time_days} days</p>
              </div>
            </div>
          </GlassCard>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <GlassCard className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Truck className="h-4 w-4 text-sky-400" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Shipments by Status</h3>
              </div>
              {Object.keys(data.shipments.by_status).length === 0 ? (
                <EmptyState message="No shipments recorded yet." />
              ) : (
                <div className="space-y-2">
                  {Object.entries(data.shipments.by_status).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between glass-panel rounded-xl px-4 py-2.5">
                      <Badge tone={statusTone(status)}>{status.replace(/_/g, " ")}</Badge>
                      <span className="text-sm font-medium text-[var(--text-primary)]">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>

            <GlassCard className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <ClipboardList className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Purchase Orders by Status</h3>
              </div>
              {Object.keys(data.purchase_orders.by_status).length === 0 ? (
                <EmptyState message="No purchase orders recorded yet." />
              ) : (
                <div className="space-y-2">
                  {Object.entries(data.purchase_orders.by_status).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between glass-panel rounded-xl px-4 py-2.5">
                      <Badge tone={statusTone(status)}>{status.replace(/_/g, " ")}</Badge>
                      <span className="text-sm font-medium text-[var(--text-primary)]">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          </div>
        </>
      )}
    </div>
  );
}
