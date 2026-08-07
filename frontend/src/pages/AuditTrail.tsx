import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { ScrollText } from "lucide-react";
import { auditApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { AuditLog } from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { Select } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";

const ENTITY_TYPES = ["supplier", "shipment", "raw_material", "purchase_order"];

export function AuditTrailPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [entityType, setEntityType] = useState("");

  useEffect(() => {
    setLoading(true);
    auditApi
      .list({ entity_type: entityType || undefined, limit: 200 })
      .then((res) => setLogs(res.data))
      .catch((err) => toast.error(apiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [entityType]);

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Blockchain Audit Trail"
        description="A human-readable view of every action recorded on the blockchain ledger — full traceability of system activity."
        actions={
          <Select value={entityType} onChange={(e) => setEntityType(e.target.value)} className="w-48">
            <option value="">All entity types</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        }
      />

      <GlassCard className="overflow-hidden">
        <div className="px-6 pt-5 pb-1 flex items-center gap-2">
          <ScrollText className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Audit Log</h3>
        </div>
        {loading ? (
          <LoadingState message="Loading audit trail..." />
        ) : logs.length === 0 ? (
          <EmptyState message="No audit events found." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin mt-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">Action</th>
                  <th className="px-5 py-3 font-medium">Entity</th>
                  <th className="px-5 py-3 font-medium">Performed By</th>
                  <th className="px-5 py-3 font-medium">Block</th>
                  <th className="px-5 py-3 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3 font-medium text-[var(--text-primary)]">{log.action}</td>
                    <td className="px-5 py-3 text-[var(--text-secondary)] capitalize">
                      {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ""}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-secondary)]">
                      {log.performed_by === "ai_engine" ? (
                        <Badge tone="accent">AI Engine</Badge>
                      ) : log.performed_by === "system" ? (
                        <Badge tone="neutral">System</Badge>
                      ) : (
                        log.performed_by
                      )}
                    </td>
                    <td className="px-5 py-3 text-[var(--text-muted)]">#{log.block_id}</td>
                    <td className="px-5 py-3 text-[var(--text-muted)] text-xs">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
