import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { CheckCircle2, FileText, MessageSquare, Send, ShieldCheck, Upload, XCircle } from "lucide-react";
import { messagesApi, documentsApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";
import type { Message, Document } from "../types";
import { useAuthStore } from "../store/auth";
import { Modal } from "./ui/Modal";
import { Button } from "./ui/Button";
import { EmptyState } from "./ui/Feedback";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function EntityDetailsModal({
  open,
  onClose,
  entityType,
  entityId,
  entityLabel,
}: {
  open: boolean;
  onClose: () => void;
  entityType: "purchase_order" | "shipment";
  entityId: number;
  entityLabel: string;
}) {
  const [tab, setTab] = useState<"messages" | "documents">("messages");
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<Record<number, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const user = useAuthStore((s) => s.user);

  async function load() {
    setLoading(true);
    try {
      const [msgRes, docRes] = await Promise.all([
        messagesApi.list(entityType, entityId),
        documentsApi.list(entityType, entityId),
      ]);
      setMessages(msgRes.data);
      setDocuments(docRes.data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, entityType, entityId]);

  async function handleSend() {
    if (!draft.trim()) return;
    setSending(true);
    try {
      await messagesApi.create(entityType, entityId, draft.trim());
      setDraft("");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSending(false);
    }
  }

  async function handleUpload(file: File) {
    setUploading(true);
    try {
      await documentsApi.upload(entityType, entityId, file);
      toast.success(`'${file.name}' uploaded and anchored on the blockchain ledger.`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleVerify(doc: Document) {
    try {
      const res = await documentsApi.verify(doc.id);
      setVerifyResult((prev) => ({ ...prev, [doc.id]: res.data.is_verified }));
      toast[res.data.is_verified ? "success" : "error"](res.data.message);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function handleDownload(doc: Document) {
    try {
      const res = await documentsApi.download(doc.id);
      const url = URL.createObjectURL(res.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = doc.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={entityLabel} width="max-w-xl">
      <div className="flex gap-1.5 mb-4 border-b border-white/10">
        <button
          onClick={() => setTab("messages")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition ${
            tab === "messages" ? "border-indigo-500 text-[var(--text-primary)]" : "border-transparent text-[var(--text-muted)]"
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" /> Messages
        </button>
        <button
          onClick={() => setTab("documents")}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition ${
            tab === "documents" ? "border-indigo-500 text-[var(--text-primary)]" : "border-transparent text-[var(--text-muted)]"
          }`}
        >
          <FileText className="h-3.5 w-3.5" /> Documents
        </button>
      </div>

      {tab === "messages" ? (
        <div className="space-y-3">
          <div className="max-h-72 overflow-y-auto scrollbar-thin space-y-2.5 pr-1">
            {loading ? (
              <p className="text-sm text-[var(--text-muted)]">Loading...</p>
            ) : messages.length === 0 ? (
              <EmptyState message="No messages yet. Ask a question or leave an update below." />
            ) : (
              messages.map((m) => {
                const isMine = m.sender_user_id === user?.id;
                return (
                  <div key={m.id} className={`glass-panel rounded-xl px-3.5 py-2.5 ${isMine ? "border-indigo-400/40" : ""}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-[var(--text-primary)]">
                        {m.sender_name} <span className="font-normal text-[var(--text-muted)]">· {m.sender_role.replace(/_/g, " ")}</span>
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)]">{new Date(m.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap">{m.body}</p>
                  </div>
                );
              })
            )}
          </div>
          <div className="flex gap-2">
            <textarea
              className="glass-input flex-1 rounded-xl px-3.5 py-2.5 text-sm resize-none"
              rows={2}
              placeholder="Write a message..."
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <Button onClick={handleSend} loading={sending} disabled={!draft.trim()} size="sm" className="self-end">
              <Send className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <label className="glass-panel flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-white/15 px-4 py-6 cursor-pointer hover:border-indigo-400/40 transition">
            <Upload className="h-5 w-5 text-[var(--text-muted)]" />
            <span className="text-sm text-[var(--text-secondary)]">
              {uploading ? "Uploading..." : "Click to upload a document (cert, spec sheet, invoice...)"}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
              }}
            />
          </label>

          <div className="max-h-64 overflow-y-auto scrollbar-thin space-y-2 pr-1">
            {loading ? (
              <p className="text-sm text-[var(--text-muted)]">Loading...</p>
            ) : documents.length === 0 ? (
              <EmptyState message="No documents uploaded yet." />
            ) : (
              documents.map((d) => (
                <div key={d.id} className="glass-panel rounded-xl px-3.5 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[var(--text-primary)] truncate">{d.filename}</p>
                      <p className="text-[11px] text-[var(--text-muted)]">
                        {formatBytes(d.file_size)} · {d.uploaded_by_name} · {new Date(d.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => handleVerify(d)}
                        title="Verify against the blockchain-anchored hash"
                        className="rounded-lg p-1.5 text-[var(--text-muted)] hover:text-indigo-500 hover:bg-black/5 dark:hover:bg-white/5 transition"
                      >
                        <ShieldCheck className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDownload(d)}
                        title="Download"
                        className="rounded-lg p-1.5 text-[var(--text-muted)] hover:text-indigo-500 hover:bg-black/5 dark:hover:bg-white/5 transition"
                      >
                        <FileText className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  {verifyResult[d.id] !== undefined && (
                    <p className={`mt-1.5 flex items-center gap-1 text-xs ${verifyResult[d.id] ? "text-emerald-500" : "text-rose-500"}`}>
                      {verifyResult[d.id] ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                      {verifyResult[d.id] ? "Provenance verified against blockchain" : "Verification failed"}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
