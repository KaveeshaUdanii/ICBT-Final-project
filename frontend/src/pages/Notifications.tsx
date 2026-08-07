import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";
import { AlertTriangle, Bell, CheckCheck, Info, ShieldAlert } from "lucide-react";
import { notificationsApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Notification, NotificationSeverity } from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge, severityTone } from "../components/ui/Badge";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";

const SEVERITY_ICON: Record<NotificationSeverity, typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  critical: ShieldAlert,
};

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await notificationsApi.list({ unread_only: unreadOnly, limit: 100 });
      setNotifications(res.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unreadOnly]);

  async function handleMarkRead(n: Notification) {
    if (n.is_read) return;
    await notificationsApi.markRead(n.id);
    setNotifications((prev) => prev.map((item) => (item.id === n.id ? { ...item, is_read: true } : item)));
  }

  async function handleMarkAllRead() {
    await notificationsApi.markAllRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    toast.success("All notifications marked as read.");
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Notification System"
        description="Alerts for delays, high risks, anomalies, and reorder thresholds, raised automatically by the smart-contract rule engine."
        actions={
          <>
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)] glass-panel rounded-xl px-3 py-2">
              <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
              Unread only
            </label>
            <Button variant="secondary" size="sm" onClick={handleMarkAllRead}>
              <CheckCheck className="h-4 w-4" /> Mark all read
            </Button>
          </>
        }
      />

      <GlassCard className="p-2">
        {loading ? (
          <LoadingState message="Loading notifications..." />
        ) : notifications.length === 0 ? (
          <EmptyState message="No notifications." icon={<Bell className="h-9 w-9 opacity-60" />} />
        ) : (
          <div className="divide-y divide-white/5">
            {notifications.map((n) => {
              const Icon = SEVERITY_ICON[n.severity];
              return (
                <button
                  key={n.id}
                  onClick={() => handleMarkRead(n)}
                  className={clsx(
                    "flex w-full items-start gap-3 px-4 py-3.5 text-left rounded-2xl transition hover:bg-white/5",
                    !n.is_read && "bg-white/5"
                  )}
                >
                  <Icon
                    className={clsx(
                      "h-5 w-5 shrink-0 mt-0.5",
                      n.severity === "critical" ? "text-rose-500" : n.severity === "warning" ? "text-amber-500" : "text-sky-500"
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{n.title}</p>
                      <Badge tone={severityTone(n.severity)}>{n.severity}</Badge>
                      {n.source === "smart_contract" && <Badge tone="accent">Smart Contract</Badge>}
                      {!n.is_read && <span className="h-2 w-2 rounded-full bg-indigo-500" />}
                    </div>
                    <p className="text-sm text-[var(--text-secondary)] mt-0.5">{n.message}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
