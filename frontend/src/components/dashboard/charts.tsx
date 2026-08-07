import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Sparkles } from "lucide-react";
import type { DelayTrendPoint, RiskHeatmapCell } from "../../types";
import { GlassCard } from "../ui/GlassCard";
import { EmptyState } from "../ui/Feedback";

export const RISK_COLORS = { low: "#0ca30c", medium: "#fab219", high: "#d03b3b" };
export const STATUS_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"];
export const SEQUENTIAL = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#0d366b"];

export function heatColor(score: number): string {
  if (score < 20) return SEQUENTIAL[0];
  if (score < 40) return SEQUENTIAL[1];
  if (score < 60) return SEQUENTIAL[2];
  if (score < 80) return SEQUENTIAL[3];
  return SEQUENTIAL[4];
}

const tooltipStyle = { background: "var(--glass-bg-strong)", border: "1px solid var(--glass-border)", borderRadius: 12 };

export function SupplierRiskPie({ low, medium, high }: { low: number; medium: number; high: number }) {
  const data = [
    { name: "Low Risk", value: low, color: RISK_COLORS.low },
    { name: "Medium Risk", value: medium, color: RISK_COLORS.medium },
    { name: "High Risk", value: high, color: RISK_COLORS.high },
  ];
  const total = low + medium + high;
  return (
    <GlassCard className="p-6">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Supplier Risk Distribution</h3>
      <p className="text-xs text-[var(--text-muted)] mb-4">Output of the Supplier Risk Scoring Model</p>
      {total === 0 ? (
        <EmptyState message="No suppliers yet." />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} stroke="none" />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </GlassCard>
  );
}

export function DelayTrendChart({ trend }: { trend: DelayTrendPoint[] }) {
  return (
    <GlassCard className="p-6">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Predicted Delay Trend</h3>
      <p className="text-xs text-[var(--text-muted)] mb-4">Average predicted delay days by expected delivery month</p>
      {trend.length === 0 ? (
        <EmptyState message="Run AI predictions on shipments to see delay trends." />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
            <XAxis dataKey="month" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line
              type="monotone"
              dataKey="average_predicted_delay_days"
              name="Avg predicted delay (days)"
              stroke="#2a78d6"
              strokeWidth={2}
              dot={{ r: 3, fill: "#2a78d6" }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </GlassCard>
  );
}

export function ShipmentStatusBar({ byStatus }: { byStatus: Record<string, number> }) {
  const data = Object.entries(byStatus).map(([status, count]) => ({ status: status.replace(/_/g, " "), count }));
  return (
    <GlassCard className="p-6">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Shipments by Status</h3>
      <p className="text-xs text-[var(--text-muted)] mb-4">Current distribution across the shipment lifecycle</p>
      {data.length === 0 ? (
        <EmptyState message="No shipments yet." />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
            <XAxis dataKey="status" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {data.map((entry, i) => (
                <Cell key={entry.status} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </GlassCard>
  );
}

export function RiskHeatmapList({ cells }: { cells: RiskHeatmapCell[] }) {
  return (
    <GlassCard className="p-6">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-4 w-4 text-indigo-400" />
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Risk Heatmap</h3>
      </div>
      <p className="text-xs text-[var(--text-muted)] mb-4">Avg. risk score by material category & country</p>
      {cells.length === 0 ? (
        <EmptyState message="Score suppliers to populate the heatmap." />
      ) : (
        <div className="max-h-56 overflow-y-auto scrollbar-thin space-y-1.5 pr-1">
          {[...cells]
            .sort((a, b) => b.average_risk_score - a.average_risk_score)
            .map((cell) => (
              <div
                key={`${cell.category}-${cell.country}`}
                className="flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-xs"
                style={{ background: `${heatColor(cell.average_risk_score)}22` }}
              >
                <span className="text-[var(--text-secondary)] truncate">
                  {cell.category} · {cell.country}
                </span>
                <span className="font-semibold shrink-0" style={{ color: heatColor(cell.average_risk_score) }}>
                  {cell.average_risk_score}%
                </span>
              </div>
            ))}
        </div>
      )}
    </GlassCard>
  );
}
