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
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-600 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-3">
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
      </GlassCard>
    </div>
  );
}
