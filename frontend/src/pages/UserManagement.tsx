import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { ShieldCheck, Users } from "lucide-react";
import { usersApi, suppliersApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Supplier, User, UserRole } from "../types";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Badge } from "../components/ui/Badge";
import { Select } from "../components/ui/Input";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";

const ROLES: UserRole[] = ["admin", "supply_chain_manager", "warehouse_manager", "supplier"];

const ROLE_TONE: Record<UserRole, "accent" | "success" | "warning" | "neutral"> = {
  admin: "accent",
  supply_chain_manager: "success",
  warehouse_manager: "warning",
  supplier: "neutral",
};

export function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const currentUser = useAuthStore((s) => s.user);

  async function load() {
    setLoading(true);
    try {
      const [usersRes, suppliersRes] = await Promise.all([usersApi.list(), suppliersApi.list()]);
      setUsers(usersRes.data);
      setSuppliers(suppliersRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRoleChange(user: User, role: string) {
    try {
      await usersApi.updateRole(user.id, role);
      toast.success(`${user.name}'s role updated to ${role}.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleToggleActive(user: User) {
    try {
      await usersApi.toggleActive(user.id, !user.is_active);
      toast.success(`${user.name} is now ${!user.is_active ? "active" : "deactivated"}.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleLinkSupplier(user: User, value: string) {
    const supplierId = value === "" ? null : Number(value);
    try {
      await usersApi.linkSupplier(user.id, supplierId);
      const supplier = suppliers.find((s) => s.id === supplierId);
      toast.success(
        supplier ? `${user.name} linked to ${supplier.name}.` : `${user.name} unlinked from their supplier record.`
      );
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="User & Role Management"
        description="Manage platform users and role-based access control (Admin, Supply Chain Manager, Warehouse Manager, Supplier)."
      />

      <GlassCard className="overflow-hidden">
        <div className="px-6 pt-5 pb-1 flex items-center gap-2">
          <Users className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Platform Users</h3>
        </div>
        {loading ? (
          <LoadingState message="Loading users..." />
        ) : users.length === 0 ? (
          <EmptyState message="No users found." />
        ) : (
          <div className="overflow-x-auto scrollbar-thin mt-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)] border-b border-white/10">
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Role</th>
                  <th className="px-5 py-3 font-medium">Linked Supplier</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-[var(--text-primary)]">{user.name}</p>
                      <p className="text-xs text-[var(--text-muted)]">{user.email}</p>
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={ROLE_TONE[user.role]}>{user.role.replace(/_/g, " ")}</Badge>
                    </td>
                    <td className="px-5 py-3">
                      {user.role === "supplier" ? (
                        <Select
                          value={user.supplier_id ?? ""}
                          onChange={(e) => handleLinkSupplier(user, e.target.value)}
                          className="py-1.5 text-xs w-48"
                        >
                          <option value="">— not linked —</option>
                          {suppliers.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        <span className="text-[var(--text-muted)]">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={user.is_active ? "success" : "danger"}>
                        {user.is_active ? "Active" : "Deactivated"}
                      </Badge>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <Select
                          value={user.role}
                          onChange={(e) => handleRoleChange(user, e.target.value)}
                          disabled={user.id === currentUser?.id}
                          className="py-1.5 text-xs w-40"
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r.replace(/_/g, " ")}
                            </option>
                          ))}
                        </Select>
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={user.id === currentUser?.id}
                          className="rounded-xl glass-panel px-3 py-1.5 text-xs disabled:opacity-40 hover:border-indigo-400/40 transition flex items-center gap-1"
                          title="Toggle active status"
                        >
                          <ShieldCheck className="h-3.5 w-3.5" />
                          {user.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
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
