import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { AlertTriangle, Pencil, Plus, Search, Sparkles, Trash2, Upload } from "lucide-react";
import { aiApi, materialsApi, suppliersApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { MaterialCategory, RawMaterial, Supplier } from "../types";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Field, Input, Select } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";
import { CsvImportModal } from "../components/CsvImportModal";

function stockoutTone(prob: number | null): "success" | "warning" | "danger" | "neutral" {
  if (prob === null) return "neutral";
  if (prob >= 0.66) return "danger";
  if (prob >= 0.33) return "warning";
  return "success";
}

const CATEGORIES: MaterialCategory[] = ["fabric", "buttons", "zippers", "thread", "packaging", "trims", "dye_chemicals"];

function emptyForm(supplierId?: number) {
  return {
    name: "",
    category: "fabric" as MaterialCategory,
    unit: "kg",
    quantity_on_hand: 100,
    reorder_level: 50,
    unit_cost: 2,
    lead_time_days: 14,
    supplier_id: supplierId ?? 0,
  };
}

export function RawMaterialsPage() {
  const [materials, setMaterials] = useState<RawMaterial[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [onlyReorder, setOnlyReorder] = useState(false);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RawMaterial | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const user = useAuthStore((s) => s.user);
  const canManage = user?.role !== "supplier";
  const [forecastingId, setForecastingId] = useState<number | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [matRes, supRes] = await Promise.all([
        materialsApi.list(onlyReorder ? { needs_reorder: true } : undefined),
        suppliersApi.list(),
      ]);
      setMaterials(matRes.data);
      setSuppliers(supRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyReorder]);

  function supplierName(id: number) {
    return suppliers.find((s) => s.id === id)?.name ?? `#${id}`;
  }

  const filteredMaterials = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return materials;
    return materials.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        m.category.toLowerCase().includes(q) ||
        supplierName(m.supplier_id).toLowerCase().includes(q)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [materials, search, suppliers]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm(suppliers[0]?.id));
    setModalOpen(true);
  }

  function openEdit(material: RawMaterial) {
    setEditing(material);
    setForm({
      name: material.name,
      category: material.category,
      unit: material.unit,
      quantity_on_hand: material.quantity_on_hand,
      reorder_level: material.reorder_level,
      unit_cost: material.unit_cost,
      lead_time_days: material.lead_time_days,
      supplier_id: material.supplier_id,
    });
    setModalOpen(true);
  }

  async function handleSave() {
    if (!form.supplier_id) {
      toast.error("Please select a supplier.");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await materialsApi.update(editing.id, form);
        toast.success("Raw material updated.");
      } else {
        await materialsApi.create(form);
        toast.success("Raw material created.");
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(material: RawMaterial) {
    if (!confirm(`Delete "${material.name}"?`)) return;
    try {
      await materialsApi.remove(material.id);
      toast.success("Raw material deleted.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleForecast(material: RawMaterial) {
    setForecastingId(material.id);
    try {
      await Promise.all([aiApi.forecastDemand(material.id), aiApi.predictStockout(material.id)]);
      toast.success(`Demand & stockout risk refreshed for ${material.name}.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setForecastingId(null);
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Raw Material Management"
        description="Track inventory levels, reorder thresholds, and supplier-linked lead times."
        actions={
          <>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <Input
                placeholder="Search materials..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 w-52"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)] glass-panel rounded-xl px-3 py-2">
              <input type="checkbox" checked={onlyReorder} onChange={(e) => setOnlyReorder(e.target.checked)} />
              Needs reorder only
            </label>
            {canManage && (
              <Button variant="secondary" onClick={() => setImportOpen(true)} size="sm">
                <Upload className="h-4 w-4" /> Import CSV
              </Button>
            )}
            {canManage && (
              <Button onClick={openCreate} size="sm">
                <Plus className="h-4 w-4" /> Add Material
              </Button>
            )}
          </>
        }
      />

      <GlassCard className="overflow-hidden">
        {loading ? (
          <LoadingState message="Loading raw materials..." />
        ) : filteredMaterials.length === 0 ? (
          <EmptyState message="No raw materials found." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">Material</th>
                  <th className="px-5 py-3 font-medium">Supplier</th>
                  <th className="px-5 py-3 font-medium">Stock</th>
                  <th className="px-5 py-3 font-medium">Reorder Level</th>
                  <th className="px-5 py-3 font-medium">Lead Time</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Forecast Demand (30d)</th>
                  <th className="px-5 py-3 font-medium">Stockout Risk</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredMaterials.map((material) => (
                  <tr key={material.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--text-primary)]">{material.name}</p>
                      <p className="text-xs text-[var(--text-muted)] capitalize">{material.category}</p>
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{supplierName(material.supplier_id)}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {material.quantity_on_hand.toFixed(0)} {material.unit}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {material.reorder_level.toFixed(0)} {material.unit}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{material.lead_time_days} days</td>
                    <td className="px-5 py-3">
                      {material.needs_reorder ? (
                        <Badge tone="warning">
                          <AlertTriangle className="h-3 w-3" /> Reorder now
                        </Badge>
                      ) : (
                        <Badge tone="success">Healthy</Badge>
                      )}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {material.predicted_demand_next_30_days !== null
                        ? `${Math.round(material.predicted_demand_next_30_days)} ${material.unit}`
                        : "—"}
                    </td>
                    <td className="px-5 py-3">
                      {material.stockout_risk_probability !== null ? (
                        <Badge tone={stockoutTone(material.stockout_risk_probability)}>
                          {Math.round(material.stockout_risk_probability * 100)}%
                        </Badge>
                      ) : (
                        <span className="text-[var(--text-muted)]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      {canManage && (
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={forecastingId === material.id}
                            onClick={() => handleForecast(material)}
                            title="Refresh demand forecast & stockout risk"
                          >
                            <Sparkles className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="secondary" size="sm" onClick={() => openEdit(material)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="danger" size="sm" onClick={() => handleDelete(material)}>
                            <Trash2 className="h-3.5 w-3.5" />
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit Material" : "Add Raw Material"}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Name" className="sm:col-span-2">
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
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
          <Field label="Category">
            <Select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value as MaterialCategory })}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Unit">
            <Select value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
              <option value="kg">kg</option>
              <option value="meters">meters</option>
              <option value="units">units</option>
              <option value="rolls">rolls</option>
            </Select>
          </Field>
          <Field label="Quantity on Hand">
            <Input
              type="number"
              value={form.quantity_on_hand}
              onChange={(e) => setForm({ ...form, quantity_on_hand: Number(e.target.value) })}
            />
          </Field>
          <Field label="Reorder Level">
            <Input
              type="number"
              value={form.reorder_level}
              onChange={(e) => setForm({ ...form, reorder_level: Number(e.target.value) })}
            />
          </Field>
          <Field label="Unit Cost (USD)">
            <Input
              type="number"
              step="0.01"
              value={form.unit_cost}
              onChange={(e) => setForm({ ...form, unit_cost: Number(e.target.value) })}
            />
          </Field>
          <Field label="Lead Time (days)">
            <Input
              type="number"
              value={form.lead_time_days}
              onChange={(e) => setForm({ ...form, lead_time_days: Number(e.target.value) })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="secondary" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} loading={saving}>
            {editing ? "Save Changes" : "Create Material"}
          </Button>
        </div>
      </Modal>

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import Raw Materials from CSV"
        description="Bulk-add raw materials from a CSV export. Use either a supplier_id column or a supplier_name column (matched by exact name)."
        templateFilename="raw_materials_template.csv"
        templateColumns={["name", "category", "unit", "quantity_on_hand", "reorder_level", "unit_cost", "lead_time_days", "supplier_name"]}
        templateExampleRow={["Cotton Poplin", "fabric", "meters", 500, 100, 3.5, 14, "Acme Textiles Ltd"]}
        importFn={materialsApi.importCsv}
        onImported={load}
      />
    </div>
  );
}
