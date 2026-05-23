import { useEffect, useRef, useState } from "react";
import { Send, Lock, Bot, User as UserIcon, Check, X } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function Conversation() {
  const appState = useAppStore((s) => s.appState);
  const setAppState = useAppStore((s) => s.setAppState);
  const sessionId = useAppStore((s) => s.sessionId);
  const messages = useAppStore((s) => s.dialogueMessages);
  const appendMessage = useAppStore((s) => s.appendMessage);
  const pendingConflict = useAppStore((s) => s.pendingConflict);
  const setPendingConflict = useAppStore((s) => s.setPendingConflict);

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const locked =
    appState === "SEARCHING" || appState === "SEMANTIC_ALIGNING" || sending;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pendingConflict]);

  // Seed with greeting once
  useEffect(() => {
    if (messages.length === 0) {
      appendMessage({
        role: "agent",
        content:
          "Hi — I have your profile ready. Tell me a little more about the home you have in mind. Anything specific about location, layout, or lifestyle?",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = async () => {
    const text = input.trim();
    if (!text || locked || !sessionId) return;
    appendMessage({ role: "user", content: text, timestamp: Date.now() });
    setInput("");
    setSending(true);
    try {
      const res = await api.chat(sessionId, text);
      appendMessage({ role: "agent", content: res.reply });
      if (res.status === "pending_confirmation") {
        setPendingConflict({
          conflicting_field: res.conflicting_field ?? "",
          proposed_value: res.proposed_value,
          reply: res.reply,
        });
        setAppState("PENDING_CONFIRMATION");
      } else if (res.status === "searching") {
        setAppState("SEARCHING");
      }
    } catch (e) {
      console.warn("[chat] failed", e);
    } finally {
      setSending(false);
    }
  };

  const confirmConflict = async (accept: boolean) => {
    if (!pendingConflict || !sessionId) return;
    if (accept) {
      try {
        await api.updateRequirements(sessionId, {
          [pendingConflict.conflicting_field]: pendingConflict.proposed_value,
        });
        appendMessage({
          role: "system",
          content: `Updated ${pendingConflict.conflicting_field}.`,
        });
      } catch (e) {
        console.warn(e);
      }
    } else {
      appendMessage({
        role: "system",
        content: "Kept original requirement.",
      });
    }
    setPendingConflict(null);
    setAppState("CHATTING");
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-220px)] max-w-3xl flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">
            Live consultation
          </h2>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            phase 2 · adaptive dialogue
          </p>
        </div>
      </div>

      <div className="glass-strong relative flex flex-1 flex-col overflow-hidden rounded-3xl border border-border shadow-[var(--shadow-elegant)]">
        {/* Message list */}
        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-6">
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} />
          ))}

          {pendingConflict && (
            <div className="flex animate-in fade-in slide-in-from-bottom-2 justify-start">
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-warning/30 bg-warning/10 p-4">
                <div className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-warning">
                  field conflict · {pendingConflict.conflicting_field}
                </div>
                <p className="mb-4 text-sm text-foreground">
                  {pendingConflict.reply}
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => confirmConflict(true)}
                    className="h-8 rounded-lg bg-primary text-primary-foreground"
                  >
                    <Check className="mr-1 h-3.5 w-3.5" /> Yes, update
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => confirmConflict(false)}
                    className="h-8 rounded-lg"
                  >
                    <X className="mr-1 h-3.5 w-3.5" /> Keep original
                  </Button>
                </div>
              </div>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* Composer */}
        <div className="border-t border-border/60 bg-surface/40 p-4">
          <div
            className={[
              "flex items-center gap-2 rounded-xl border px-3 py-2 transition-all",
              locked
                ? "border-border bg-muted/40 opacity-60"
                : "border-border-strong bg-surface-raised focus-within:ring-focus",
            ].join(" ")}
          >
            {locked && <Lock className="h-4 w-4 text-muted-foreground" />}
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={locked}
              placeholder={
                locked
                  ? "Input locked while the agent works…"
                  : "Type your message…"
              }
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <Button
              size="icon"
              onClick={send}
              disabled={locked || !input.trim()}
              className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-primary-glow text-primary-foreground"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  role,
  content,
}: {
  role: "user" | "agent" | "system";
  content: string;
}) {
  if (role === "system") {
    return (
      <div className="flex justify-center">
        <span className="rounded-full border border-border bg-surface-raised/60 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {content}
        </span>
      </div>
    );
  }
  const isUser = role === "user";
  return (
    <div
      className={[
        "flex animate-in fade-in slide-in-from-bottom-1 gap-3",
        isUser ? "justify-end" : "justify-start",
      ].join(" ")}
    >
      {!isUser && (
        <div className="mt-1 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-glow text-primary-foreground shadow-[var(--shadow-glow)]">
          <Bot className="h-3.5 w-3.5" />
        </div>
      )}
      <div
        className={[
          "max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "rounded-tr-sm bg-primary text-primary-foreground shadow-[var(--shadow-soft)]"
            : "rounded-tl-sm border border-border bg-surface-raised text-foreground",
        ].join(" ")}
      >
        {content}
      </div>
      {isUser && (
        <div className="mt-1 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-border bg-surface-raised text-muted-foreground">
          <UserIcon className="h-3.5 w-3.5" />
        </div>
      )}
    </div>
  );
}
