import { Link } from "react-router-dom";
import { CompassIcon } from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <GlassCard strong className="p-10 text-center max-w-md">
        <CompassIcon className="h-10 w-10 mx-auto text-indigo-400 mb-4" />
        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Page not found</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-2">
          The page you're looking for doesn't exist or has moved.
        </p>
        <Link to="/">
          <Button className="mt-6">Back to Dashboard</Button>
        </Link>
      </GlassCard>
    </div>
  );
}
