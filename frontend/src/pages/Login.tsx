import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BrainCircuit, LogIn } from "lucide-react";
import toast from "react-hot-toast";
import { authApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import { useAuthStore } from "../store/auth";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Field, Input } from "../components/ui/Input";

const DEMO_ACCOUNTS = [
  { label: "Admin", email: "admin@supplychain.ai", password: "admin123" },
  { label: "Supply Chain Manager", email: "manager@supplychain.ai", password: "manager123" },
  { label: "Warehouse Manager", email: "warehouse@supplychain.ai", password: "warehouse123" },
  { label: "Supplier Portal", email: "supplier@supplychain.ai", password: "supplier123" },
];

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      setAuth(res.data.access_token, res.data.user);
      toast.success(`Welcome back, ${res.data.user.name.split(" ")[0]}!`);
      navigate("/");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <GlassCard strong className="w-full max-w-md p-8">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-3">
            <BrainCircuit className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">SupplyChain AI</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            AI-Driven Blockchain Supply Chain Risk Platform
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Email">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </Field>
          <Button type="submit" className="w-full" loading={loading}>
            <LogIn className="h-4 w-4" /> Sign In
          </Button>
        </form>

        <p className="text-center text-sm text-[var(--text-secondary)] mt-5">
          Don't have an account?{" "}
          <Link to="/register" className="text-indigo-500 hover:text-indigo-400 font-medium">
            Create one
          </Link>
        </p>

        <div className="mt-6 pt-5 border-t border-white/10">
          <p className="text-xs text-[var(--text-muted)] mb-2 text-center">Quick demo login</p>
          <div className="flex flex-wrap justify-center gap-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                onClick={() => {
                  setEmail(acc.email);
                  setPassword(acc.password);
                }}
                className="text-xs px-2.5 py-1 rounded-full glass-panel hover:border-indigo-400/40 transition text-[var(--text-secondary)]"
              >
                {acc.label}
              </button>
            ))}
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
