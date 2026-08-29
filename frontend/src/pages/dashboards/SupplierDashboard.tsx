import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  Boxes,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Download,
  Handshake,
  LineChart as LineChartIcon,
  Package,
  Pencil,
  Receipt,
  Timer,
  Truck,
  XCircle,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsApi, purchaseOrdersApi, shipmentsApi, suppliersApi } from "../../api/endpoints";
import { apiErrorMessage } from "../../api/client";
import type { MyDashboardData } from "../../types";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatCard } from "../../components/ui/StatCard";
import { Badge, statusTone } from "../../components/ui/Badge";
import { PageHeader, Skeleton, EmptyState } from "../../components/ui/Feedback";
import { Button } from "../../components/ui/Button";
import { Field, Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";

const tooltipStyle = { background: "var(--glass-bg-strong)", border: "1px solid var(--glass-border)", borderRadius: 12 };

function downloadCsv(filename: string, columns: string[], rows: (string | number)[][]) {
  const escape = (v: string | number) => {
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [columns.join(","), ...rows.map((r) => r.map(escape).join(","))].join("\n") + "\n";
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function SupplierDashboard() {
  const [data, setData] = useState<MyDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileForm, setProfileForm] = useState({ contact_email: "", contact_phone: "" });
  const [savingProfile, setSavingProfile] = useState(false);
  const [respondingId, setRespondingId] = useState<number | null>(null);
  const [exporting, setExporting] = useState<"shipments" | "purchase_orders" | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await analyticsApi.myDashboard();
      setData(res.data);
      if (res.data.supplier) {
        setProfileForm({
          contact_email: res.data.supplier.contact_email ?? "",
          contact_phone: res.data.supplier.contact_phone ?? "",
        });
      }
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSaveProfile() {
    setSavingProfile(true);
    try {
      await suppliersApi.updateMyProfile(profileForm);
      toast.success("Company profile updated.");
      setProfileOpen(false);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleRespond(id: number, response: "accepted" | "declined") {
    if (response === "declined") {
      const reason = window.prompt("Reason for declining this purchase order?") ?? "";
      if (reason.trim() === "") return;
      setRespondingId(id);
      try {
        await purchaseOrdersApi.respond(id, "declined", reason.trim());
        toast.success("Purchase order declined.");
        await load();
      } catch (err) {
        toast.error(apiErrorMessage(err));
      } finally {
        setRespondingId(null);
      }
      return;
    }
    setRespondingId(id);
    try {
      await purchaseOrdersApi.respond(id, "accepted");
      toast.success("Purchase order accepted.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setRespondingId(null);
    }
  }

  async function handleExport(kind: "shipments" | "purchase_orders") {
    setExporting(kind);
    try {
      if (kind === "shipments") {
        const res = await shipmentsApi.list();
        downloadCsv(
          "my_shipments.csv",
          ["shipment_code", "status", "quantity", "expected_delivery_date", "actual_delivery_date", "carrier", "tracking_number"],
          res.data.map((s) => [
            s.shipment_code,
            s.status,
            s.quantity,
            s.expected_delivery_date ?? "",
            s.actual_delivery_date ?? "",
            s.carrier ?? "",
            s.tracking_number ?? "",
          ])
        );
      } else {
        const res = await purchaseOrdersApi.list();
        downloadCsv(
          "my_purchase_orders.csv",
          ["po_number", "status", "supplier_response", "order_date", "expected_delivery_date", "total_value"],
          res.data.map((po) => [
            po.po_number,
            po.status,
            po.supplier_response ?? "",
            po.order_date,
            po.expected_delivery_date,
            po.total_value,
          ])
        );
      }
      toast.success("Export ready.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setExporting(null);
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
        actions={
          data.supplier && (
            <Button variant="secondary" size="sm" onClick={() => setProfileOpen(true)}>
              <Pencil className="h-3.5 w-3.5" /> Edit Company Profile
            </Button>
          )
        }
      />

      {!data.supplier ? (
        <EmptyState message="No supplier profile is linked to your account yet. Contact your account manager." />
      ) : (
        <>
          {data.pending_response_purchase_orders.length > 0 && (
            <GlassCard className="p-6 border-amber-400/30">
              <div className="flex items-center gap-2 mb-4">
                <Handshake className="h-4 w-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  Purchase Orders Awaiting Your Response ({data.pending_response_purchase_orders.length})
                </h3>
              </div>
              <div className="space-y-2">
                {data.pending_response_purchase_orders.map((po) => (
                  <div
                    key={po.id}
                    className="flex flex-wrap items-center justify-between gap-2 glass-panel rounded-xl px-4 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{po.po_number}</p>
                      <p className="text-xs text-[var(--text-muted)]">
                        ${po.total_value.toLocaleString()} · due {po.expected_delivery_date}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="primary"
                        loading={respondingId === po.id}
                        onClick={() => handleRespond(po.id, "accepted")}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        loading={respondingId === po.id}
                        onClick={() => handleRespond(po.id, "declined")}
                      >
                        <XCircle className="h-3.5 w-3.5" /> Decline
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatCard label="Your Shipments" value={data.shipments.total} icon={<Truck className="h-5 w-5" />} />
            <StatCard label="Your Purchase Orders" value={data.purchase_orders.total} icon={<Boxes className="h-5 w-5" />} />
            <StatCard
              label="On-Time Delivery Rate"
              value={`${(data.supplier.on_time_delivery_rate * 100).toFixed(1)}%`}
              icon={<Timer className="h-5 w-5" />}
            />
          </div>

          <GlassCard className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Handshake className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Your Partnership Snapshot</h3>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Supplier Name</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">{data.supplier.name}</p>
              </div>
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Avg. Lead Time</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">{data.supplier.avg_lead_time_days} days</p>
              </div>
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Orders Last Year</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">{data.supplier.order_volume_last_year}</p>
              </div>
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Defect Rate</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">
                  {(data.supplier.defect_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Cancellation Rate</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">
                  {(data.supplier.cancellation_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="glass-panel rounded-xl px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Total PO Value</p>
                <p className="text-lg font-semibold text-[var(--text-primary)]">
                  ${data.purchase_orders.total_value.toLocaleString()}
                </p>
              </div>
            </div>
            <p className="text-xs text-[var(--text-muted)] mt-3">
              These figures reflect your own delivery and order history with this organization.
            </p>
          </GlassCard>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <GlassCard className="p-6">
              <div className="flex items-center gap-2 mb-1">
                <LineChartIcon className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Your Performance Trend</h3>
              </div>
              <p className="text-xs text-[var(--text-muted)] mb-4">On-time delivery rate by month, from your own shipment history</p>
              {data.performance_trend.length === 0 ? (
                <EmptyState message="Not enough delivered shipment history yet to chart a trend." />
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={data.performance_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                    <XAxis dataKey="month" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis
                      stroke="var(--text-muted)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                    />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`, "On-time rate"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="on_time_rate"
                      name="on_time_rate"
                      stroke="#1baf7a"
                      strokeWidth={2}
                      dot={{ r: 3, fill: "#1baf7a" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </GlassCard>

            <GlassCard className="p-6">
              <div className="flex items-center gap-2 mb-1">
                <Package className="h-4 w-4 text-sky-400" />
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Forward Demand For Your Materials</h3>
              </div>
              <p className="text-xs text-[var(--text-muted)] mb-4">
                Expected order volume over the next 30 days, from the Demand Forecasting model
              </p>
              {data.materials_demand_forecast.by_material.length === 0 ? (
                <EmptyState message="No materials are linked to your supplier account yet." />
              ) : (
                <>
                  <div className="glass-panel rounded-xl px-4 py-3 mb-3">
                    <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Total Expected, All Materials</p>
                    <p className="text-xl font-semibold text-[var(--text-primary)]">
                      {data.materials_demand_forecast.total_next_30_days.toLocaleString()} units
                    </p>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin pr-1">
                    {data.materials_demand_forecast.by_material.map((m) => (
                      <div key={m.name} className="flex items-center justify-between glass-panel rounded-xl px-4 py-2.5">
                        <span className="text-sm text-[var(--text-secondary)]">{m.name}</span>
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          {m.predicted_demand_next_30_days.toLocaleString()} {m.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </GlassCard>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <GlassCard className="p-6">
              <div className="flex items-center justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <CalendarClock className="h-4 w-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">Upcoming Shipments</h3>
                </div>
                <Button size="sm" variant="ghost" loading={exporting === "shipments"} onClick={() => handleExport("shipments")}>
                  <Download className="h-3.5 w-3.5" /> Export CSV
                </Button>
              </div>
              {data.upcoming_shipments.length === 0 ? (
                <EmptyState message="No shipments currently in progress." />
              ) : (
                <div className="space-y-2">
                  {data.upcoming_shipments.map((s) => (
                    <div
                      key={s.shipment_code}
                      className="flex items-center justify-between glass-panel rounded-xl px-4 py-2.5"
                    >
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">{s.shipment_code}</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          {s.quantity} units · due {s.expected_delivery_date}
                        </p>
                      </div>
                      <Badge tone={statusTone(s.status)}>{s.status.replace(/_/g, " ")}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>

            <GlassCard className="p-6">
              <div className="flex items-center justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <Receipt className="h-4 w-4 text-amber-400" />
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">Recent Purchase Orders</h3>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  loading={exporting === "purchase_orders"}
                  onClick={() => handleExport("purchase_orders")}
                >
                  <Download className="h-3.5 w-3.5" /> Export CSV
                </Button>
              </div>
              {data.recent_purchase_orders.length === 0 ? (
                <EmptyState message="No purchase orders recorded yet." />
              ) : (
                <div className="space-y-2">
                  {data.recent_purchase_orders.map((po) => (
                    <div
                      key={po.po_number}
                      className="flex items-center justify-between glass-panel rounded-xl px-4 py-2.5"
                    >
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">{po.po_number}</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          ${po.total_value.toLocaleString()} · due {po.expected_delivery_date}
                        </p>
                      </div>
                      <Badge tone={statusTone(po.status)}>{po.status.replace(/_/g, " ")}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          </div>

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

      <Modal open={profileOpen} onClose={() => setProfileOpen(false)} title="Edit Company Profile">
        <div className="space-y-4">
          <Field label="Contact Email">
            <Input
              type="email"
              value={profileForm.contact_email}
              onChange={(e) => setProfileForm((f) => ({ ...f, contact_email: e.target.value }))}
              placeholder="contact@yourcompany.com"
            />
          </Field>
          <Field label="Contact Phone">
            <Input
              value={profileForm.contact_phone}
              onChange={(e) => setProfileForm((f) => ({ ...f, contact_phone: e.target.value }))}
              placeholder="+94 71 234 5678"
            />
          </Field>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setProfileOpen(false)}>
              Cancel
            </Button>
            <Button loading={savingProfile} onClick={handleSaveProfile}>
              Save Changes
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
