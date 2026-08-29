import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BrainCircuit, UserPlus } from "lucide-react";
import toast from "react-hot-toast";
import { authApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Field, Input, Select } from "../components/ui/Input";

export function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("supply_chain_manager");
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await authApi.register({ name, email, password, role });
      setAuth(res.data.access_token, res.data.user);
      toast.success("Account created!");
      navigate("/");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <GlassCard strong className="w-full max-w-md p-8">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-600 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-3">
            <BrainCircuit className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">Create your account</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Join the supply chain platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Full name">
            <Input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
          </Field>
          <Field label="Email">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </Field>
          <Field label="Password" hint="At least 6 characters">
            <Input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </Field>
          <Field label="Role">
            <Select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="supply_chain_manager">Supply Chain Manager</option>
              <option value="warehouse_manager">Warehouse Manager</option>
              <option value="supplier">Supplier</option>
              <option value="admin">Administrator</option>
            </Select>
          </Field>
          <Button type="submit" className="w-full" loading={loading}>
            <UserPlus className="h-4 w-4" /> Create Account
          </Button>
        </form>

        <p className="text-center text-sm text-[var(--text-secondary)] mt-5">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-500 hover:text-indigo-400 font-medium">
            Sign in
          </Link>
        </p>
      </GlassCard>
    </div>
  );
}
