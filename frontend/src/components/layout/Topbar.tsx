import { useState, useRef, useEffect } from "react";
import { Menu, Moon, Sun, LogOut, ChevronDown } from "lucide-react";
import { useThemeStore } from "../../store/theme";
import { useAuthStore } from "../../store/auth";
import { NotificationBell } from "./NotificationBell";

const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  supply_chain_manager: "Supply Chain Manager",
  warehouse_manager: "Warehouse Manager",
  supplier: "Supplier",
};

export function Topbar({ onMenuClick, title }: { onMenuClick: () => void; title: string }) {
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [menuOpen, setMenuOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <header className="app-topbar sticky top-0 z-30 flex items-center justify-between gap-4 px-4 sm:px-8 h-16">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden rounded-xl p-2 text-[var(--text-secondary)] hover:bg-black/5 dark:hover:bg-white/5 transition"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h1 className="text-lg font-semibold text-[var(--text-primary)] truncate">{title}</h1>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={toggle}
          className="rounded-full p-2.5 text-[var(--text-secondary)] hover:bg-black/5 dark:hover:bg-white/5 transition"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
        </button>

        <NotificationBell />

        <div className="h-6 w-px bg-[var(--glass-border)] mx-1 hidden sm:block" />

        <div className="relative" ref={ref}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-full pl-1.5 pr-2.5 py-1.5 hover:bg-black/5 dark:hover:bg-white/5 transition"
          >
            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-indigo-600 to-blue-600 flex items-center justify-center text-xs font-semibold text-white">
              {user?.name?.charAt(0).toUpperCase() ?? "?"}
            </div>
            <div className="hidden sm:block text-left leading-tight">
              <p className="text-xs font-medium text-[var(--text-primary)]">{user?.name}</p>
              <p className="text-[10px] text-[var(--text-muted)]">{ROLE_LABELS[user?.role ?? ""] ?? user?.role}</p>
            </div>
            <ChevronDown className={`h-3.5 w-3.5 text-[var(--text-muted)] transition-transform ${menuOpen ? "rotate-180" : ""}`} />
          </button>

          {menuOpen && (
            <div className="glass-panel-strong absolute right-0 mt-2 w-48 rounded-2xl p-2 z-50">
              <button
                onClick={clearAuth}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-rose-500 hover:bg-rose-500/10 transition"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
