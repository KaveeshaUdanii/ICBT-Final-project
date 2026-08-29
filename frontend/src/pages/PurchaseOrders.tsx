import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { AlertTriangle, Check, DollarSign, MessageSquare, Plus, Search, ShieldAlert, Upload, X } from "lucide-react";
import { purchaseOrdersApi, suppliersApi, materialsApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { PurchaseOrder, RawMaterial, Supplier } from "../types";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge, statusTone } from "../components/ui/Badge";
import { Field, Input, Select } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";
import { CsvImportModal } from "../components/CsvImportModal";
import { EntityDetailsModal } from "../components/EntityDetailsModal";

function emptyForm(supplierId?: number, materialId?: number) {
  return {
    po_number: "",
    supplier_id: supplierId ?? 0,
    raw_material_id: materialId ?? 0,
    quantity: 200,
    unit_price: 2,
    expected_delivery_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
    penalty_rate_pct: 0,
  };
}

function responseTone(response: string) {
  if (response === "accepted") return "success" as const;
  if (response === "declined") return "danger" as const;
  return "neutral" as const;
}

export function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [declineTarget, setDeclineTarget] = useState<PurchaseOrder | null>(null);
  const [declineReason, setDeclineReason] = useState("");
  const [responding, setResponding] = useState(false);
  const [detailsTarget, setDetailsTarget] = useState<PurchaseOrder | null>(null);
  const user = useAuthStore((s) => s.user);
  const isSupplier = user?.role === "supplier";
  // Purchase orders are a procurement decision -- Admin and Supply Chain Manager only.
  // Warehouse Manager gets read-only visibility (to know what's incoming); Supplier sees
  // only their own orders (enforced server-side) and can accept/decline them, but never
  // creates/approves.
  const canManage = user?.role === "admin" || user?.role === "supply_chain_manager";
  const canApprove = canManage;
  const [importOpen, setImportOpen] = useState(false);

  async function load() {
    setLoading(true);
    try {
      // Raw Materials is a staff-only endpoint (require_staff excludes Supplier accounts --
      // it's the internal inventory catalog, not something an external party needs). Fetching
      // it unconditionally here used to 403 the whole Promise.all for a Supplier account,
      // silently breaking their own Purchase Orders list along with it.
      const [poRes, supRes, matRes] = await Promise.all([
        purchaseOrdersApi.list(),
        suppliersApi.list(),
        user?.role === "supplier" ? Promise.resolve({ data: [] as RawMaterial[] }) : materialsApi.list(),
      ]);
      setOrders(poRes.data);
      setSuppliers(supRes.data);
      setMaterials(matRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function supplierName(id: number) {
    return suppliers.find((s) => s.id === id)?.name ?? `#${id}`;
  }

  const filteredOrders = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return orders;
    return orders.filter(
      (po) =>
        po.po_number.toLowerCase().includes(q) ||
        supplierName(po.supplier_id).toLowerCase().includes(q) ||
        po.raw_material_name.toLowerCase().includes(q) ||
        po.status.toLowerCase().includes(q)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, search, suppliers]);

  function openCreate() {
    setForm(emptyForm(suppliers[0]?.id, materials[0]?.id));
    setModalOpen(true);
  }

  async function handleSave() {
    if (!form.supplier_id || !form.raw_material_id) {
      toast.error("Please select a supplier and raw material.");
      return;
    }
    setSaving(true);
    try {
      const res = await purchaseOrdersApi.create(form);
      if (res.data.data_entry_flag) {
        toast(res.data.data_entry_warning, { icon: "⚠️", duration: 8000 });
      }
      toast.success(
        res.data.risk_flag
          ? `PO created and auto-flagged for review (high-risk supplier).`
          : "Purchase order created."
      );
      setModalOpen(false);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove(po: PurchaseOrder) {
    try {
      await purchaseOrdersApi.approve(po.id);
      toast.success(`PO ${po.po_number} approved.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleReject(po: PurchaseOrder) {
    const reason = prompt("Reason for rejection:") ?? "";
    try {
      await purchaseOrdersApi.reject(po.id, reason);
      toast.success(`PO ${po.po_number} rejected.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleAccept(po: PurchaseOrder) {
    try {
      await purchaseOrdersApi.respond(po.id, "accepted");
      toast.success(`You accepted PO '${po.po_number}'.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleDecline() {
    if (!declineTarget) return;
    setResponding(true);
    try {
      await purchaseOrdersApi.respond(declineTarget.id, "declined", declineReason);
      toast.success(`You declined PO '${declineTarget.po_number}'.`);
      setDeclineTarget(null);
      setDeclineReason("");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setResponding(false);
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Purchase Order Management"
        description="Create purchase orders and manage the manager approval workflow."
        actions={
          <>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <Input
                placeholder="Search purchase orders..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 w-56"
              />
            </div>
            {canManage && (
              <Button variant="secondary" onClick={() => setImportOpen(true)} size="sm">
                <Upload className="h-4 w-4" /> Import CSV
              </Button>
            )}
            {canManage && (
              <Button onClick={openCreate} size="sm">
                <Plus className="h-4 w-4" /> New Purchase Order
              </Button>
            )}
          </>
        }
      />

      <GlassCard className="overflow-hidden">
        {loading ? (
          <LoadingState message="Loading purchase orders..." />
        ) : filteredOrders.length === 0 ? (
          <EmptyState message="No purchase orders found." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">PO Number</th>
                  <th className="px-5 py-3 font-medium">Supplier</th>
                  <th className="px-5 py-3 font-medium">Material</th>
                  <th className="px-5 py-3 font-medium">Value</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  {isSupplier && <th className="px-5 py-3 font-medium">Your Response</th>}
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((po) => (
                  <tr key={po.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--text-primary)] flex items-center gap-1.5">
                        {po.po_number}
                        {po.risk_flag && (
                          <span title={po.risk_notes}>
                            <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
                          </span>
                        )}
                        {po.data_entry_flag && (
                          <span title={po.data_entry_warning}>
                            <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                          </span>
                        )}
                        {!!po.penalty_exposure && (
                          <span title={`SLA penalty exposure: $${po.penalty_exposure.toLocaleString()} (${po.penalty_rate_pct}%/day late)`}>
                            <DollarSign className="h-3.5 w-3.5 text-orange-500" />
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">{po.expected_delivery_date}</p>
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{supplierName(po.supplier_id)}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{po.raw_material_name}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">${po.total_value.toLocaleString()}</td>
                    <td className="px-5 py-3">
                      <Badge tone={statusTone(po.status)}>{po.status.replace(/_/g, " ")}</Badge>
                    </td>
                    {isSupplier && (
                      <td className="px-5 py-3">
                        <Badge tone={responseTone(po.supplier_response)}>{po.supplier_response}</Badge>
                      </td>
                    )}
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        {canApprove && po.status === "pending_approval" && (
                          <>
                            <Button variant="secondary" size="sm" onClick={() => handleApprove(po)}>
                              <Check className="h-3.5 w-3.5" /> Approve
                            </Button>
                            <Button variant="danger" size="sm" onClick={() => handleReject(po)}>
                              <X className="h-3.5 w-3.5" /> Reject
                            </Button>
                          </>
                        )}
                        {isSupplier && po.supplier_response === "pending" && po.status !== "rejected" && (
                          <>
                            <Button variant="secondary" size="sm" onClick={() => handleAccept(po)}>
                              <Check className="h-3.5 w-3.5" /> Accept
                            </Button>
                            <Button variant="danger" size="sm" onClick={() => setDeclineTarget(po)}>
                              <X className="h-3.5 w-3.5" /> Decline
                            </Button>
                          </>
                        )}
                        <Button variant="secondary" size="sm" onClick={() => setDetailsTarget(po)} title="Messages & documents">
                          <MessageSquare className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Purchase Order">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="PO Number" className="sm:col-span-2">
            <Input
              value={form.po_number}
              onChange={(e) => setForm({ ...form, po_number: e.target.value })}
              placeholder="PO-2001"
              required
            />
          </Field>
          <Field label="Supplier">
            <Select
              value={form.supplier_id}
              onChange={(e) => setForm({ ...form, supplier_id: Number(e.target.value) })}
            >
              <option value={0} disabled>
                Select supplier
              </option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Raw Material">
            <Select
              value={form.raw_material_id}
              onChange={(e) => setForm({ ...form, raw_material_id: Number(e.target.value) })}
            >
              <option value={0} disabled>
                Select material
              </option>
              {materials
                .filter((m) => !form.supplier_id || m.supplier_id === form.supplier_id)
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="Quantity">
            <Input
              type="number"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
            />
          </Field>
          <Field label="Unit Price (USD)">
            <Input
              type="number"
              step="0.01"
              value={form.unit_price}
              onChange={(e) => setForm({ ...form, unit_price: Number(e.target.value) })}
            />
          </Field>
          <Field label="Expected Delivery Date">
            <Input
              type="date"
              value={form.expected_delivery_date}
              onChange={(e) => setForm({ ...form, expected_delivery_date: e.target.value })}
            />
          </Field>
          <Field label="SLA Penalty Rate (%/day late)" hint="0 = no penalty clause">
            <Input
              type="number"
              step="0.1"
              min={0}
              max={100}
              value={form.penalty_rate_pct}
              onChange={(e) => setForm({ ...form, penalty_rate_pct: Number(e.target.value) })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} loading={saving}>
            Create Purchase Order
          </Button>
        </div>
      </Modal>

      <Modal open={!!declineTarget} onClose={() => setDeclineTarget(null)} title="Decline Purchase Order">
        <p className="text-sm text-[var(--text-secondary)] mb-4">
          Declining '{declineTarget?.po_number}'. Let procurement know why (optional but helpful).
        </p>
        <Field label="Reason">
          <Input value={declineReason} onChange={(e) => setDeclineReason(e.target.value)} placeholder="e.g. capacity fully booked that week" />
        </Field>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="secondary" onClick={() => setDeclineTarget(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDecline} loading={responding}>
            <X className="h-4 w-4" /> Decline
          </Button>
        </div>
      </Modal>

      {detailsTarget && (
        <EntityDetailsModal
          open={!!detailsTarget}
          onClose={() => setDetailsTarget(null)}
          entityType="purchase_order"
          entityId={detailsTarget.id}
          entityLabel={detailsTarget.po_number}
        />
      )}

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import Purchase Orders from CSV"
        description="Bulk-add purchase orders from a CSV export. Use either the *_id columns or supplier_name / raw_material_name columns (each matched by exact name)."
        templateFilename="purchase_orders_template.csv"
        templateColumns={["po_number", "supplier_name", "raw_material_name", "quantity", "unit_price", "expected_delivery_date"]}
        templateExampleRow={["PO-2001", "Acme Textiles Ltd", "Cotton Poplin", 200, 3.5, "2026-10-15"]}
        importFn={purchaseOrdersApi.importCsv}
        onImported={load}
      />
    </div>
  );
}
