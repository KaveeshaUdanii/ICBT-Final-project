import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { BrainCircuit, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import { suppliersApi, aiApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Supplier } from "../types";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge, riskTone } from "../components/ui/Badge";
import { Field, Input, Select } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { CsvImportModal } from "../components/CsvImportModal";
import type { ExplanationResult } from "../types";

const CATEGORIES = ["fabric", "buttons", "zippers", "thread", "packaging", "trims", "dye_chemicals"];

const emptyForm = {
  name: "",
  contact_email: "",
  contact_phone: "",
  country: "Sri Lanka",
  category: "fabric",
  on_time_delivery_rate: 0.9,
  defect_rate: 0.02,
  cancellation_rate: 0.02,
  avg_lead_time_days: 14,
  order_volume_last_year: 50,
};

export function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [scoringId, setScoringId] = useState<number | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResult | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const user = useAuthStore((s) => s.user);
  const canManage = user?.role === "admin" || user?.role === "supply_chain_manager";

  async function load() {
    setLoading(true);
    try {
      const res = await suppliersApi.list(search ? { q: search } : undefined);
      setSuppliers(res.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timeout = setTimeout(load, 250);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEdit(supplier: Supplier) {
    setEditing(supplier);
    setForm({
      name: supplier.name,
      contact_email: supplier.contact_email,
      contact_phone: supplier.contact_phone,
      country: supplier.country,
      category: supplier.category,
      on_time_delivery_rate: supplier.on_time_delivery_rate,
      defect_rate: supplier.defect_rate,
      cancellation_rate: supplier.cancellation_rate,
      avg_lead_time_days: supplier.avg_lead_time_days,
      order_volume_last_year: supplier.order_volume_last_year,
    });
    setModalOpen(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (editing) {
        await suppliersApi.update(editing.id, form);
        toast.success("Supplier updated.");
      } else {
        await suppliersApi.create(form);
        toast.success("Supplier created.");
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(supplier: Supplier) {
    if (!confirm(`Delete supplier "${supplier.name}"? This cannot be undone.`)) return;
    try {
      await suppliersApi.remove(supplier.id);
      toast.success("Supplier deleted.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleScore(supplier: Supplier) {
    setScoringId(supplier.id);
    try {
      const res = await aiApi.scoreSupplier(supplier.id);
      toast.success(`${supplier.name} scored: ${res.data.risk_score}% (${res.data.risk_level} risk)`);
      setExplanation(res.data.explanation);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setScoringId(null);
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Supplier Management"
        description="Manage supplier records, performance metrics, and AI-driven risk scoring."
        actions={
          <>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <Input
                placeholder="Search suppliers..."
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
                <Plus className="h-4 w-4" /> Add Supplier
              </Button>
            )}
          </>
        }
      />

      <GlassCard className="overflow-hidden">
        {loading ? (
          <LoadingState message="Loading suppliers..." />
        ) : suppliers.length === 0 ? (
          <EmptyState message="No suppliers found. Add your first supplier to get started." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">Supplier</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 font-medium">Country</th>
                  <th className="px-5 py-3 font-medium">On-Time %</th>
                  <th className="px-5 py-3 font-medium">Risk Score</th>
                  <th className="px-5 py-3 font-medium">Risk Level</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((supplier) => (
                  <tr key={supplier.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--text-primary)]">{supplier.name}</p>
                      <p className="text-xs text-[var(--text-muted)]">{supplier.contact_email}</p>
                    </td>
                    <td className="px-5 py-3 capitalize text-[var(--text-secondary)]">{supplier.category}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{supplier.country}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {(supplier.on_time_delivery_rate * 100).toFixed(0)}%
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {supplier.last_scored_at && supplier.risk_score !== undefined
                        ? `${supplier.risk_score.toFixed(0)}%`
                        : "—"}
                    </td>
                    <td className="px-5 py-3">
                      {supplier.risk_level && (
                        <Badge tone={riskTone(supplier.risk_level)}>{supplier.risk_level}</Badge>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        {canManage && (
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={scoringId === supplier.id}
                            onClick={() => handleScore(supplier)}
                            title="Run AI Risk Scoring"
                          >
                            <BrainCircuit className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {canManage && (
                          <Button variant="secondary" size="sm" onClick={() => openEdit(supplier)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {canManage && (
                          <Button variant="danger" size="sm" onClick={() => handleDelete(supplier)}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Supplier" : "Add Supplier"}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Name" className="sm:col-span-2">
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </Field>
          <Field label="Contact Email">
            <Input
              type="email"
              value={form.contact_email}
              onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
              required
            />
          </Field>
          <Field label="Contact Phone">
            <Input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
          </Field>
          <Field label="Country">
            <Input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
          </Field>
          <Field label="Category">
            <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="On-Time Delivery Rate (0-1)">
            <Input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.on_time_delivery_rate}
              onChange={(e) => setForm({ ...form, on_time_delivery_rate: Number(e.target.value) })}
            />
          </Field>
          <Field label="Defect Rate (0-1)">
            <Input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.defect_rate}
              onChange={(e) => setForm({ ...form, defect_rate: Number(e.target.value) })}
            />
          </Field>
          <Field label="Cancellation Rate (0-1)">
            <Input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.cancellation_rate}
              onChange={(e) => setForm({ ...form, cancellation_rate: Number(e.target.value) })}
            />
          </Field>
          <Field label="Avg Lead Time (days)">
            <Input
              type="number"
              value={form.avg_lead_time_days}
              onChange={(e) => setForm({ ...form, avg_lead_time_days: Number(e.target.value) })}
            />
          </Field>
          <Field label="Order Volume (last year)">
            <Input
              type="number"
              value={form.order_volume_last_year}
              onChange={(e) => setForm({ ...form, order_volume_last_year: Number(e.target.value) })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} loading={saving}>
            {editing ? "Save Changes" : "Create Supplier"}
          </Button>
        </div>
      </Modal>

      <Modal open={!!explanation} onClose={() => setExplanation(null)} title="Why This Risk Score?" width="max-w-xl">
        {explanation && <ExplanationPanel explanation={explanation} />}
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import Suppliers from CSV"
        description="Bulk-add suppliers from a CSV export, the way most ERP systems bring data in."
        templateFilename="suppliers_template.csv"
        templateColumns={[
          "name",
          "contact_email",
          "contact_phone",
          "country",
          "category",
          "on_time_delivery_rate",
          "defect_rate",
          "cancellation_rate",
          "avg_lead_time_days",
          "order_volume_last_year",
        ]}
        templateExampleRow={["Acme Textiles Ltd", "contact@acme.example", "+94 11 234 5678", "Sri Lanka", "fabric", 0.92, 0.02, 0.01, 12, 80]}
        importFn={suppliersApi.importCsv}
        onImported={load}
      />
    </div>
  );
}
