import { useEffect, useRef, useState } from "react";
import { Bot, MessageCircle, Send, X } from "lucide-react";
import { chatbotApi } from "../../api/endpoints";
import { useAuthStore } from "../../store/auth";

interface ChatEntry {
  role: "user" | "bot";
  text: string;
}

const GREETING: ChatEntry = {
  role: "bot",
  text: "Hi! I'm your portal assistant. Ask me about a shipment or PO status (e.g. \"status of SHP-1042\"), your pending orders, or your delivery performance.",
};

export function ChatWidget() {
  const user = useAuthStore((s) => s.user);
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<ChatEntry[]>([GREETING]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [entries, open]);

  if (user?.role !== "supplier") return null;

  async function handleSend() {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    setEntries((prev) => [...prev, { role: "user", text }]);
    setSending(true);
    try {
      const res = await chatbotApi.send(text);
      setEntries((prev) => [...prev, { role: "bot", text: res.data.reply }]);
    } catch {
      setEntries((prev) => [
        ...prev,
        { role: "bot", text: "Sorry, something went wrong reaching the assistant. Please try again." },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {open && (
        <div className="glass-panel-strong mb-3 flex h-[26rem] w-80 flex-col rounded-3xl p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-600 to-blue-600">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">Portal Assistant</p>
                <p className="text-[10px] text-[var(--text-muted)]">Local AI · no data leaves this app</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="rounded-full p-1.5 text-[var(--text-muted)] hover:bg-white/10 hover:text-[var(--text-primary)] transition"
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-2.5 overflow-y-auto scrollbar-thin pr-1">
            {entries.map((e, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap ${
                  e.role === "user"
                    ? "ml-auto bg-gradient-to-r from-indigo-600 to-blue-600 text-white"
                    : "glass-panel text-[var(--text-secondary)]"
                }`}
              >
                {e.text}
              </div>
            ))}
            {sending && <div className="glass-panel max-w-[60%] rounded-2xl px-3.5 py-2 text-sm text-[var(--text-muted)]">Typing...</div>}
          </div>

          <div className="mt-3 flex gap-2">
            <input
              className="glass-input flex-1 rounded-xl px-3.5 py-2.5 text-sm"
              placeholder="Ask a question..."
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
            />
            <button
              onClick={handleSend}
              disabled={!draft.trim() || sending}
              className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 px-3 text-white shadow-lg shadow-indigo-500/25 transition hover:brightness-110 disabled:opacity-50"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-500/35 transition hover:brightness-110 active:scale-95"
        aria-label="Toggle assistant chat"
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
}
