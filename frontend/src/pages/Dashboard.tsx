import { useAuthStore } from "../store/auth";
import { AdminDashboard } from "./dashboards/AdminDashboard";
import { ManagerDashboard } from "./dashboards/ManagerDashboard";
import { WarehouseDashboard } from "./dashboards/WarehouseDashboard";
import { SupplierDashboard } from "./dashboards/SupplierDashboard";

export function DashboardPage() {
  const role = useAuthStore((s) => s.user?.role);

  switch (role) {
    case "admin":
      return <AdminDashboard />;
    case "supply_chain_manager":
      return <ManagerDashboard />;
    case "warehouse_manager":
      return <WarehouseDashboard />;
    case "supplier":
      return <SupplierDashboard />;
    default:
      return null;
  }
}
