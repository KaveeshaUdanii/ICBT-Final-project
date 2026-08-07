import { useEffect, useRef, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";
import { notificationsApi } from "../../api/endpoints";
import type { Notification } from "../../types";

const severityDot: Record<string, string> = {
  critical: "bg-rose-500",
  warning: "bg-amber-500",
  info: "bg-sky-500",
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  const refreshCount = () => {
    notificationsApi
      .unreadCount()
      .then((res) => setUnread(res.data.unread_count))
      .catch(() => {});
  };

  useEffect(() => {
    refreshCount();
    const interval = setInterval(refreshCount, 20000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const toggleOpen = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      notificationsApi.list({ limit: 12 }).then((res) => setItems(res.data));
    }
  };

  const markAllRead = async () => {
    await notificationsApi.markAllRead();
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnread(0);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={toggleOpen}
        className="relative rounded-full p-2.5 glass-panel hover:border-indigo-400/40 transition"
        aria-label="Notifications"
      >
        <Bell className="h-4.5 w-4.5 text-[var(--text-secondary)]" />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="glass-panel-strong absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl p-3 z-50 max-h-[70vh] overflow-y-auto scrollbar-thin">
          <div className="flex items-center justify-between px-2 pb-2">
            <p className="text-sm font-semibold text-[var(--text-primary)]">Notifications</p>
            <button
              onClick={markAllRead}
              className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-400 font-medium"
            >
              <CheckCheck className="h-3.5 w-3.5" /> Mark all read
            </button>
          </div>
          {items.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)] px-2 py-6 text-center">No notifications yet.</p>
          ) : (
            <div className="space-y-1">
              {items.map((n) => (
                <div
                  key={n.id}
                  className={clsx(
                    "flex items-start gap-2.5 rounded-xl px-3 py-2.5 text-xs transition",
                    n.is_read ? "opacity-60" : "bg-white/10"
                  )}
                >
                  <span className={clsx("mt-1 h-2 w-2 shrink-0 rounded-full", severityDot[n.severity])} />
                  <div className="min-w-0">
                    <p className="font-medium text-[var(--text-primary)] truncate">{n.title}</p>
                    <p className="text-[var(--text-secondary)] mt-0.5 line-clamp-2">{n.message}</p>
                    <p className="text-[var(--text-muted)] mt-1">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
