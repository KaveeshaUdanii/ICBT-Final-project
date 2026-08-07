import { NavLink } from "react-router-dom";
import clsx from "clsx";
import {
  LayoutDashboard,
  Truck,
  Package,
  ClipboardList,
  BrainCircuit,
  Sparkles,
  Blocks,
  ScrollText,
  FlaskConical,
  Users,
  Factory,
  Bell,
} from "lucide-react";
import { useAuthStore } from "../../store/auth";
import type { UserRole } from "../../types";

const NAV_ITEMS: { to: string; label: string; icon: typeof LayoutDashboard; end?: boolean; roles?: UserRole[] }[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/suppliers", label: "Suppliers", icon: Factory, roles: ["admin", "supply_chain_manager"] },
  {
    to: "/raw-materials",
    label: "Raw Materials",
    icon: Package,
    roles: ["admin", "supply_chain_manager", "warehouse_manager"],
  },
  {
    to: "/shipments",
    label: "Shipments",
    icon: Truck,
    roles: ["admin", "supply_chain_manager", "warehouse_manager", "supplier"],
  },
  {
    to: "/purchase-orders",
    label: "Purchase Orders",
    icon: ClipboardList,
    roles: ["admin", "supply_chain_manager", "supplier"],
  },
  { to: "/ai-risk-center", label: "AI Risk Center", icon: BrainCircuit, roles: ["admin", "supply_chain_manager"] },
  { to: "/recommendations", label: "Recommendations", icon: Sparkles, roles: ["admin", "supply_chain_manager"] },
  { to: "/blockchain", label: "Blockchain Explorer", icon: Blocks, roles: ["admin", "supply_chain_manager"] },
  { to: "/audit-trail", label: "Audit Trail", icon: ScrollText, roles: ["admin", "supply_chain_manager"] },
  { to: "/scenarios", label: "Scenario Simulation", icon: FlaskConical, roles: ["admin", "supply_chain_manager"] },
  { to: "/notifications", label: "Notifications", icon: Bell },
];

export function Sidebar({ mobileOpen, onNavigate }: { mobileOpen: boolean; onNavigate: () => void }) {
  const user = useAuthStore((s) => s.user);
  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role)));

  return (
    <aside
      className={clsx(
        "glass-panel-strong fixed top-0 left-0 z-40 h-screen w-72 shrink-0 flex flex-col rounded-none lg:rounded-r-3xl transition-transform duration-300 lg:translate-x-0",
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      )}
    >
      <div className="px-6 py-6 flex items-center gap-2.5">
        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
          <BrainCircuit className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)] leading-tight">SupplyChain AI</p>
          <p className="text-[11px] text-[var(--text-muted)] leading-tight">Blockchain Risk Platform</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-4 py-2 space-y-1">
        {visibleItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "bg-gradient-to-r from-indigo-500/20 to-violet-500/20 text-[var(--text-primary)] border border-indigo-400/30"
                  : "text-[var(--text-secondary)] hover:bg-white/10 hover:text-[var(--text-primary)] border border-transparent"
              )
            }
          >
            <Icon className="h-4.5 w-4.5 shrink-0" />
            {label}
          </NavLink>
        ))}

        {user?.role === "admin" && (
          <NavLink
            to="/users"
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "bg-gradient-to-r from-indigo-500/20 to-violet-500/20 text-[var(--text-primary)] border border-indigo-400/30"
                  : "text-[var(--text-secondary)] hover:bg-white/10 hover:text-[var(--text-primary)] border border-transparent"
              )
            }
          >
            <Users className="h-4.5 w-4.5 shrink-0" />
            User Management
          </NavLink>
        )}
      </nav>

      <div className="px-6 py-4 text-[11px] text-[var(--text-muted)] border-t border-white/10">
        AI-Driven Blockchain Supply Chain Platform
      </div>
    </aside>
  );
}
