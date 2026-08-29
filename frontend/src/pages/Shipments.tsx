import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { AlertOctagon, AlertTriangle, BrainCircuit, CheckCircle2, MessageSquare, Plus, Search, Truck, Upload } from "lucide-react";
import { shipmentsApi, suppliersApi, aiApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Shipment, ShipmentStatus, Supplier, ExplanationResult } from "../types";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge, statusTone } from "../components/ui/Badge";
import { Field, Input, Select } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { CsvImportModal } from "../components/CsvImportModal";
import { EntityDetailsModal } from "../components/EntityDetailsModal";

const STATUSES: ShipmentStatus[] = ["pending", "in_transit", "delivered", "delayed", "cancelled"];

function emptyForm(supplierId?: number) {
  return {
    shipment_code: "",
    supplier_id: supplierId ?? 0,
    origin: "",
    destination: "Colombo, Sri Lanka",
    quantity: 500,
    expected_delivery_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
  };
}

export function ShipmentsPage() {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [predictingId, setPredictingId] = useState<number | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResult | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [shipTarget, setShipTarget] = useState<Shipment | null>(null);
  const [shipForm, setShipForm] = useState({ carrier: "", tracking_number: "" });
  const [shipping, setShipping] = useState(false);
  const [detailsTarget, setDetailsTarget] = useState<Shipment | null>(null);
  const user = useAuthStore((s) => s.user);
  const isSupplier = user?.role === "supplier";
  // Creating a shipment is a procurement decision (Admin / Supply Chain Manager); updating
  // status and running delay predictions is normal receiving work for any internal staff
  // member. A Supplier account can mark its own shipments shipped/delivered-confirmed, but
  // never touch the free-form status dropdown or trigger predictions.
  const canCreate = user?.role === "admin" || user?.role === "supply_chain_manager";
  const canUpdate = !isSupplier;
  // Delay risk and anomaly flags are the AI Risk Engine's internal read on this shipment --
  // the backend never even sends these fields to a Supplier account (see ShipmentExternalRead),
  // so this also drops the now-empty column rather than showing a column of "—".
  const showRisk = !isSupplier;

  async function load() {
    setLoading(true);
    try {
      const [shipRes, supRes] = await Promise.all([
        shipmentsApi.list(statusFilter ? { status_filter: statusFilter } : undefined),
        suppliersApi.list(),
      ]);
      setShipments(shipRes.data);
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
  }, [statusFilter]);

  function supplierName(id: number) {
    return suppliers.find((s) => s.id === id)?.name ?? `#${id}`;
  }

  const filteredShipments = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return shipments;
    return shipments.filter(
      (s) =>
        s.shipment_code.toLowerCase().includes(q) ||
        supplierName(s.supplier_id).toLowerCase().includes(q) ||
        s.status.toLowerCase().includes(q) ||
        (s.tracking_number || "").toLowerCase().includes(q)
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipments, search, suppliers]);

  function openCreate() {
    setForm(emptyForm(suppliers[0]?.id));
    setModalOpen(true);
  }

  async function handleSave() {
    if (!form.supplier_id) {
      toast.error("Please select a supplier.");
      return;
    }
    setSaving(true);
    try {
      const res = await shipmentsApi.create(form);
      if (res.data.data_entry_flag) {
        toast(res.data.data_entry_warning, { icon: "⚠️", duration: 8000 });
      }
      toast.success("Shipment created.");
      setModalOpen(false);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(shipment: Shipment, status: ShipmentStatus) {
    try {
      await shipmentsApi.update(shipment.id, {
        status,
        actual_delivery_date: status === "delivered" ? new Date().toISOString().slice(0, 10) : undefined,
      });
      toast.success(`Shipment ${shipment.shipment_code} marked as ${status.replace(/_/g, " ")}.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handlePredict(shipment: Shipment) {
    setPredictingId(shipment.id);
    try {
      const res = await aiApi.predictShipment(shipment.id);
      toast.success(
        `${shipment.shipment_code}: ${(res.data.delay_probability * 100).toFixed(0)}% delay risk, ` +
          `${res.data.predicted_delay_days.toFixed(1)} days predicted delay.`
      );
      setExplanation(res.data.explanation);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setPredictingId(null);
    }
  }

  async function handleShip() {
    if (!shipTarget) return;
    setShipping(true);
    try {
      await shipmentsApi.ship(shipTarget.id, shipForm.carrier, shipForm.tracking_number);
      toast.success(`'${shipTarget.shipment_code}' marked in transit.`);
      setShipTarget(null);
      setShipForm({ carrier: "", tracking_number: "" });
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setShipping(false);
    }
  }

  async function handleConfirmDelivery(shipment: Shipment) {
    setConfirmingId(shipment.id);
    try {
      const res = await shipmentsApi.confirmDelivery(shipment.id);
      toast.success(
        res.data.status === "delivered"
          ? `Both sides confirmed -- '${shipment.shipment_code}' is now delivered.`
          : `Your confirmation for '${shipment.shipment_code}' is recorded. Waiting on the other side to confirm too.`
      );
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setConfirmingId(null);
    }
  }

  const myConfirmed = (s: Shipment) => (isSupplier ? s.supplier_confirmed_delivery : s.staff_confirmed_delivery);

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Shipment Management"
        description="Track shipments and run the AI Delay Prediction Model & Anomaly Detection Model."
        actions={
          <>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-muted)]" />
              <Input
                placeholder="Search shipments..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 w-48"
              />
            </div>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-44">
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
            {canCreate && (
              <Button variant="secondary" onClick={() => setImportOpen(true)} size="sm">
                <Upload className="h-4 w-4" /> Import CSV
              </Button>
            )}
            {canCreate && (
              <Button onClick={openCreate} size="sm">
                <Plus className="h-4 w-4" /> New Shipment
              </Button>
            )}
          </>
        }
      />

      <GlassCard className="overflow-hidden">
        {loading ? (
          <LoadingState message="Loading shipments..." />
        ) : filteredShipments.length === 0 ? (
          <EmptyState message="No shipments found." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">Shipment</th>
                  <th className="px-5 py-3 font-medium">Supplier</th>
                  <th className="px-5 py-3 font-medium">Expected Delivery</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  {showRisk && <th className="px-5 py-3 font-medium">Delay Risk</th>}
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredShipments.map((shipment) => (
                  <tr key={shipment.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--text-primary)] flex items-center gap-1.5">
                        {shipment.shipment_code}
                        {shipment.is_anomaly && (
                          <span title="Flagged as anomaly by the Anomaly Detection Model">
                            <AlertOctagon className="h-3.5 w-3.5 text-rose-500" />
                          </span>
                        )}
                        {shipment.data_entry_flag && (
                          <span title={shipment.data_entry_warning}>
                            <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {shipment.quantity} units
                        {shipment.tracking_number && ` · ${shipment.carrier || "carrier n/a"}: ${shipment.tracking_number}`}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{supplierName(shipment.supplier_id)}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">{shipment.expected_delivery_date}</td>
                    <td className="px-5 py-3">
                      {canUpdate ? (
                        <Select
                          value={shipment.status}
                          onChange={(e) => handleStatusChange(shipment, e.target.value as ShipmentStatus)}
                          className="py-1.5 text-xs"
                        >
                          {STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {s.replace(/_/g, " ")}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        <Badge tone={statusTone(shipment.status)}>{shipment.status.replace(/_/g, " ")}</Badge>
                      )}
                    </td>
                    {showRisk && (
                      <td className="px-5 py-3 text-[var(--text-secondary)]">
                        {shipment.delay_probability !== null && shipment.delay_probability !== undefined ? (
                          <span>
                            {(shipment.delay_probability * 100).toFixed(0)}% ·{" "}
                            {shipment.predicted_delay_days?.toFixed(1)}d
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    )}
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        {isSupplier && (shipment.status === "pending" || shipment.status === "delayed") && (
                          <Button variant="secondary" size="sm" onClick={() => setShipTarget(shipment)} title="Mark as shipped">
                            <Truck className="h-3.5 w-3.5" /> Ship
                          </Button>
                        )}
                        {shipment.status === "in_transit" && !myConfirmed(shipment) && (
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={confirmingId === shipment.id}
                            onClick={() => handleConfirmDelivery(shipment)}
                            title="Confirm this shipment was delivered"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" /> Confirm
                          </Button>
                        )}
                        {canUpdate && (
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={predictingId === shipment.id}
                            onClick={() => handlePredict(shipment)}
                            title="Run AI Delay Prediction"
                          >
                            <BrainCircuit className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setDetailsTarget(shipment)}
                          title="Messages & documents"
                        >
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Shipment">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Shipment Code" className="sm:col-span-2">
            <Input
              value={form.shipment_code}
              onChange={(e) => setForm({ ...form, shipment_code: e.target.value })}
              placeholder="SHP-1001"
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
          <Field label="Quantity">
            <Input
              type="number"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
            />
          </Field>
          <Field label="Origin">
            <Input value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value })} />
          </Field>
          <Field label="Destination">
            <Input value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })} />
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
            Create Shipment
          </Button>
        </div>
      </Modal>

      <Modal open={!!shipTarget} onClose={() => setShipTarget(null)} title="Mark Shipment as Shipped">
        <p className="text-sm text-[var(--text-secondary)] mb-4">
          Marking '{shipTarget?.shipment_code}' in transit. Add carrier details so the buyer can track it (optional).
        </p>
        <div className="grid grid-cols-1 gap-4">
          <Field label="Carrier">
            <Input
              value={shipForm.carrier}
              onChange={(e) => setShipForm({ ...shipForm, carrier: e.target.value })}
              placeholder="e.g. DHL, Maersk"
            />
          </Field>
          <Field label="Tracking Number">
            <Input
              value={shipForm.tracking_number}
              onChange={(e) => setShipForm({ ...shipForm, tracking_number: e.target.value })}
              placeholder="e.g. 1Z999AA10123456784"
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="secondary" onClick={() => setShipTarget(null)}>
            Cancel
          </Button>
          <Button onClick={handleShip} loading={shipping}>
            <Truck className="h-4 w-4" /> Mark Shipped
          </Button>
        </div>
      </Modal>

      <Modal open={!!explanation} onClose={() => setExplanation(null)} title="Why This Delay Prediction?" width="max-w-xl">
        {explanation && <ExplanationPanel explanation={explanation} />}
      </Modal>

      {detailsTarget && (
        <EntityDetailsModal
          open={!!detailsTarget}
          onClose={() => setDetailsTarget(null)}
          entityType="shipment"
          entityId={detailsTarget.id}
          entityLabel={detailsTarget.shipment_code}
        />
      )}

      <CsvImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import Shipments from CSV"
        description="Bulk-add shipments from a CSV export. Use either a supplier_id column or a supplier_name column (matched by exact name)."
        templateFilename="shipments_template.csv"
        templateColumns={["shipment_code", "supplier_name", "origin", "destination", "quantity", "expected_delivery_date"]}
        templateExampleRow={["SHP-2001", "Acme Textiles Ltd", "Ho Chi Minh City", "Colombo, Sri Lanka", 500, "2026-10-01"]}
        importFn={shipmentsApi.importCsv}
        onImported={load}
      />
    </div>
  );
}
