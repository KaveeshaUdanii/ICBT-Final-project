import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Blocks, CheckCircle2, ChevronDown, ChevronUp, ShieldCheck, XCircle, Zap } from "lucide-react";
import { blockchainApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Block, ChainVerificationResult, SmartContractRule } from "../types";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { EmptyState, LoadingState, PageHeader } from "../components/ui/Feedback";

function BlockRow({ block }: { block: Block }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="glass-panel rounded-2xl p-4">
      <button className="flex w-full items-center justify-between gap-3 text-left" onClick={() => setExpanded((v) => !v)}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-9 w-9 shrink-0 rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 flex items-center justify-center text-xs font-semibold text-indigo-400">
            #{block.block_index}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-[var(--text-primary)] truncate">{block.event_type}</p>
            <p className="text-xs text-[var(--text-muted)]">
              {block.performed_by} · {new Date(block.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
        {expanded ? <ChevronUp className="h-4 w-4 shrink-0" /> : <ChevronDown className="h-4 w-4 shrink-0" />}
      </button>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-white/10 space-y-2 text-xs">
          <p className="text-[var(--text-muted)]">
            <span className="font-medium text-[var(--text-secondary)]">Hash:</span>{" "}
            <span className="font-mono break-all">{block.hash}</span>
          </p>
          <p className="text-[var(--text-muted)]">
            <span className="font-medium text-[var(--text-secondary)]">Previous Hash:</span>{" "}
            <span className="font-mono break-all">{block.previous_hash}</span>
          </p>
          <pre className="glass-panel rounded-xl p-3 overflow-x-auto scrollbar-thin text-[11px] text-[var(--text-secondary)]">
            {JSON.stringify(block.payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export function BlockchainExplorerPage() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [verification, setVerification] = useState<ChainVerificationResult | null>(null);
  const [rules, setRules] = useState<SmartContractRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [blocksRes, verifyRes, rulesRes] = await Promise.all([
        blockchainApi.blocks({ limit: 100 }),
        blockchainApi.verify(),
        blockchainApi.rules(),
      ]);
      setBlocks(blocksRes.data);
      setVerification(verifyRes.data);
      setRules(rulesRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleVerify() {
    setVerifying(true);
    try {
      const res = await blockchainApi.verify();
      setVerification(res.data);
      if (res.data.is_valid) {
        toast.success("Chain integrity verified — all blocks are intact.");
      } else {
        toast.error(`Tampering detected at block #${res.data.broken_at_index}!`);
      }
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="pt-6 space-y-6">
      <PageHeader
        title="Blockchain Trust Module"
        description="A permissioned, SHA-256 hash-chained ledger recording every critical supply-chain event, plus the smart-contract rules that automate responses."
        actions={
          <Button onClick={handleVerify} loading={verifying} size="sm">
            <ShieldCheck className="h-4 w-4" /> Verify Chain Integrity
          </Button>
        }
      />

      {verification && (
        <GlassCard
          className={`p-5 flex items-center gap-4 ${
            verification.is_valid ? "" : "border-rose-500/50"
          }`}
        >
          {verification.is_valid ? (
            <CheckCircle2 className="h-8 w-8 text-emerald-500 shrink-0" />
          ) : (
            <XCircle className="h-8 w-8 text-rose-500 shrink-0" />
          )}
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              {verification.is_valid ? "Chain Intact" : "Chain Integrity Violated"}
            </p>
            <p className="text-xs text-[var(--text-secondary)]">{verification.message}</p>
          </div>
          <div className="ml-auto text-right">
            <p className="text-2xl font-semibold text-[var(--text-primary)]">{verification.total_blocks}</p>
            <p className="text-xs text-[var(--text-muted)]">total blocks</p>
          </div>
        </GlassCard>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <GlassCard className="p-6 xl:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <Blocks className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Ledger (newest first)</h3>
          </div>
          {loading ? (
            <LoadingState message="Loading blocks..." />
          ) : blocks.length === 0 ? (
            <EmptyState message="No blocks recorded yet." />
          ) : (
            <div className="space-y-2 max-h-[560px] overflow-y-auto scrollbar-thin pr-1">
              {blocks.map((block) => (
                <BlockRow key={block.id} block={block} />
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-4 w-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Smart Contract Automation</h3>
          </div>
          <div className="space-y-3 max-h-[560px] overflow-y-auto scrollbar-thin pr-1">
            {rules.map((rule) => (
              <div key={rule.id} className="glass-panel rounded-2xl p-4">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{rule.name}</p>
                  <Badge tone={rule.times_triggered > 0 ? "warning" : "neutral"}>
                    {rule.times_triggered}× fired
                  </Badge>
                </div>
                <p className="text-xs text-[var(--text-muted)]">
                  <span className="font-medium text-[var(--text-secondary)]">If:</span> {rule.condition_description}
                </p>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  <span className="font-medium text-[var(--text-secondary)]">Then:</span> {rule.action_description}
                </p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
