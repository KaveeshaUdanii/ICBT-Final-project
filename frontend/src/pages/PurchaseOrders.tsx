import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Check, Plus, ShieldAlert, X } from "lucide-react";
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

function emptyForm(supplierId?: number, materialId?: number) {
  return {
    po_number: "",
    supplier_id: supplierId ?? 0,
    raw_material_id: materialId ?? 0,
    quantity: 200,
    unit_price: 2,
    expected_delivery_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
  };
}

export function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const user = useAuthStore((s) => s.user);
  // Purchase orders are a procurement decision -- Admin and Supply Chain Manager only.
  // Warehouse Manager gets read-only visibility (to know what's incoming); Supplier sees
  // only their own orders (enforced server-side) and never creates/approves.
  const canManage = user?.role === "admin" || user?.role === "supply_chain_manager";
  const canApprove = canManage;

  async function load() {
    setLoading(true);
    try {
      const [poRes, supRes, matRes] = await Promise.all([
        purchaseOrdersApi.list(),
        suppliersApi.list(),
        materialsApi.list(),
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

  function materialName(id: number) {
    return materials.find((m) => m.id === id)?.name ?? `#${id}`;
  }

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

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Purchase Order Management"
        description="Create purchase orders and manage the manager approval workflow."
        actions={
          canManage && (
            <Button onClick={openCreate} size="sm">
              <Plus className="h-4 w-4" /> New Purchase Order
            </Button>
          )
        }
      />

      <GlassCard className="overflow-hidden">
        {loading ? (
          <LoadingState message="Loading purchase orders..." />
        ) : orders.length === 0 ? (
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
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((po) => (
                  <tr key={po.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--text-primary)] flex items-center gap-1.5">
                        {po.po_number}
                        {po.risk_flag && (
                          <span title={po.risk_notes}>
                            <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">{po.expected_delivery_date}</p>
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{supplierName(po.supplier_id)}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{materialName(po.raw_material_id)}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">${po.total_value.toLocaleString()}</td>
                    <td className="px-5 py-3">
                      <Badge tone={statusTone(po.status)}>{po.status.replace(/_/g, " ")}</Badge>
                    </td>
                    <td className="px-5 py-3">
                      {canApprove && po.status === "pending_approval" && (
                        <div className="flex items-center justify-end gap-1.5">
                          <Button variant="secondary" size="sm" onClick={() => handleApprove(po)}>
                            <Check className="h-3.5 w-3.5" /> Approve
                          </Button>
                          <Button variant="danger" size="sm" onClick={() => handleReject(po)}>
                            <X className="h-3.5 w-3.5" /> Reject
                          </Button>
                        </div>
                      )}
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
          <Field label="Expected Delivery Date" className="sm:col-span-2">
            <Input
              type="date"
              value={form.expected_delivery_date}
              onChange={(e) => setForm({ ...form, expected_delivery_date: e.target.value })}
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
    </div>
  );
}
