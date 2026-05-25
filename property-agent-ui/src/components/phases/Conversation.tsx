import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Send, Lock, Bot, User as UserIcon, Check, X, Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { api, getClosedSessionReason, type ChatContext } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ThinkingBubble } from "./ThinkingBubble";
import { t, type Lang } from "@/lib/i18n";

const AUTO_REDIRECT_MS = 3000;

const FIELD_KEYS = [
  "budget", "target", "identity", "gender", "agent_style",
  "house_type", "location", "description", "bedrooms", "bathrooms",
] as const;

function fieldLabel(field: string, lang: Lang): string {
  return (FIELD_KEYS as readonly string[]).includes(field)
    ? t(`field.${field}`, lang)
    : field;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "number") return v.toLocaleString("en-MY");
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

export function Conversation() {
  const appState = useAppStore((s) => s.appState);
  const setAppState = useAppStore((s) => s.setAppState);
  const sessionId = useAppStore((s) => s.sessionId);
  const messages = useAppStore((s) => s.dialogueMessages);
  const appendMessage = useAppStore((s) => s.appendMessage);
  const pendingConflict = useAppStore((s) => s.pendingConflict);
  const setPendingConflict = useAppStore((s) => s.setPendingConflict);
  const phase1Form = useAppStore((s) => s.phase1Form);
  const semanticTags = useAppStore((s) => s.semanticTags);
  const lang = useAppStore((s) => s.lang);
  const resetAll = useAppStore((s) => s.resetAll);

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [readyPopup, setReadyPopup] = useState<{
    open: boolean;
    countdown: number;
    dismissed: boolean;
  }>({ open: false, countdown: AUTO_REDIRECT_MS / 1000, dismissed: false });
  const endRef = useRef<HTMLDivElement>(null);
  const openerStartedRef = useRef(false);

  const handleDeadSession = useCallback(
    (reason: "offline" | "restarted") => {
      const msg =
        reason === "offline"
          ? t("p2.deadsession.offline", lang)
          : t("p2.deadsession.restarted", lang);
      setInput("");
      setSending(false);
      setRetryCount(0);
      setReadyPopup({
        open: false,
        countdown: AUTO_REDIRECT_MS / 1000,
        dismissed: true,
      });
      openerStartedRef.current = false;
      try {
        window.alert(msg);
      } catch {
        /* ignore */
      }
      resetAll();
    },
    [resetAll, lang],
  );

  const locked =
    appState === "SEARCHING" ||
    appState === "SEMANTIC_ALIGNING" ||
    sending ||
    readyPopup.open;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pendingConflict, sending]);

  useEffect(() => {
    if (readyPopup.dismissed || readyPopup.open) return;
    if (appState !== "SEARCHING") return;
    setReadyPopup({
      open: true,
      countdown: AUTO_REDIRECT_MS / 1000,
      dismissed: false,
    });
  }, [appState, readyPopup]);

  useEffect(() => {
    if (!readyPopup.open) return;
    const tick = setInterval(() => {
      setReadyPopup((s) => {
        if (!s.open) return s;
        const next = s.countdown - 1;
        if (next <= 0) {
          void triggerSearch();
          return { open: false, countdown: 0, dismissed: true };
        }
        return { ...s, countdown: next };
      });
    }, 1000);
    return () => clearInterval(tick);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyPopup.open]);

  const chatContext: ChatContext | null = useMemo(() => {
    if (!phase1Form) return null;
    const userTurns = messages
      .filter((m) => m.role === "user")
      .map((m) => `- ${m.content}`);
    const confirmed_facts = [
      `budget: ${phase1Form.budget}`,
      `identity: ${phase1Form.identity}`,
      `target: ${phase1Form.target}`,
      `agent_style: ${phase1Form.agent_style}`,
      `gender: ${phase1Form.gender}`,
      `phase1_description: ${phase1Form.description}`,
      ...(semanticTags.length
        ? [`semantic_tags: ${semanticTags.join(", ")}`]
        : []),
      ...(userTurns.length ? ["user_said_in_phase2:", ...userTurns] : []),
    ];
    return {
      phase1: phase1Form,
      semantic_tags: semanticTags,
      confirmed_facts,
      lang,
      instruction:
        "Do NOT re-ask any fact in confirmed_facts. Actively grill the user " +
        "for missing ideal-property details (specific area, bedrooms, " +
        "bathrooms, must-haves, dealbreakers, timeline, financing). Ask one " +
        "focused question per turn. Trigger search only when essentials are " +
        "covered.",
    };
  }, [phase1Form, semanticTags, messages, lang]);

  useEffect(() => {
    if (openerStartedRef.current) return;
    if (appState !== "CHATTING") return;
    if (!sessionId) return;
    if (messages.length > 0) return;
    if (!chatContext) return;
    if (sending) return;

    openerStartedRef.current = true;
    setSending(true);
    (async () => {
      try {
        const res = await api.chatOpening(sessionId, chatContext);
        if (res?.reply) {
          appendMessage({ role: "assistant", content: res.reply });
        }
      } catch (e) {
        console.warn("[chat:opening] failed", e);
        const closedReason = getClosedSessionReason(e);
        if (closedReason) {
          handleDeadSession(closedReason);
          return;
        }
        openerStartedRef.current = false;
      } finally {
        setSending(false);
      }
    })();
  }, [appState, sessionId, messages.length, chatContext, sending, appendMessage, handleDeadSession]);

  const triggerSearch = async () => {
    if (!sessionId) return;
    try {
      const res = await api.chat(
        sessionId,
        t("p2.auto_search_request", lang),
        chatContext ?? undefined,
      );
      appendMessage({ role: "assistant", content: res.reply });
      setAppState("SEARCHING");
    } catch (e) {
      console.warn("[chat:auto-search] failed", e);
      const closedReason = getClosedSessionReason(e);
      if (closedReason) {
        handleDeadSession(closedReason);
        return;
      }
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || locked || !sessionId) return;
    appendMessage({ role: "user", content: text, timestamp: Date.now() });
    setInput("");
    setSending(true);
    setRetryCount(0);

    const maxRetries = 5;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await api.chat(sessionId, text, chatContext ?? undefined);
        appendMessage({ role: "assistant", content: res.reply });
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
        setRetryCount(0);
        setSending(false);
        return;
      } catch (e) {
        lastError = e instanceof Error ? e : new Error(String(e));
        const closedReason = getClosedSessionReason(e);
        if (closedReason) {
          handleDeadSession(closedReason);
          return;
        }
        const errorStatus = (lastError as { status?: number }).status;

        if (
          typeof errorStatus === "number" &&
          errorStatus >= 500 &&
          errorStatus < 600 &&
          attempt < maxRetries
        ) {
          const delayMs = Math.pow(2, attempt) * 1000;
          setRetryCount(attempt + 1);
          console.warn(
            `[chat] attempt ${attempt + 1} failed with status ${errorStatus}, retrying in ${delayMs / 1000}s:`,
            lastError.message,
          );
          await new Promise((resolve) => setTimeout(resolve, delayMs));
        } else {
          console.error("[chat] non-retryable error or max retries exhausted:", lastError);
          appendMessage({
            role: "assistant",
            content: t("p2.error.generic", lang),
          });
          setSending(false);
          return;
        }
      }
    }

    console.error("[chat] all retries exhausted:", lastError);
    handleDeadSession("offline");
  };

  const confirmConflict = async (accept: boolean) => {
    if (!pendingConflict || !sessionId) return;
    const field = pendingConflict.conflicting_field;
    const prev = (phase1Form as unknown as Record<string, unknown> | null)?.[field];
    const fLabel = fieldLabel(field, lang);
    if (accept) {
      try {
        await api.updateRequirements(sessionId, {
          [field]: pendingConflict.proposed_value,
        });
        appendMessage({
          role: "assistant",
          content: t("p2.conflict.msg.updated", lang, {
            field: fLabel,
            prev: formatValue(prev),
            next: formatValue(pendingConflict.proposed_value),
          }),
        });
      } catch (e) {
        console.warn(e);
      }
    } else {
      appendMessage({
        role: "assistant",
        content: t("p2.conflict.msg.kept", lang, {
          field: fLabel,
          prev: formatValue(prev),
        }),
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
            {t("p2.title", lang)}
          </h2>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {t("p2.subtitle", lang)}
          </p>
        </div>
      </div>

      <div className="glass-strong relative flex flex-1 flex-col overflow-hidden rounded-3xl border border-border shadow-[var(--shadow-elegant)]">
        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-6">
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} />
          ))}

          {sending && <ThinkingBubble retryCount={retryCount} />}

          {pendingConflict && (
            <ConflictCard
              field={pendingConflict.conflicting_field}
              previousValue={
                (phase1Form as unknown as Record<string, unknown> | null)?.[
                  pendingConflict.conflicting_field
                ]
              }
              proposedValue={pendingConflict.proposed_value}
              reply={pendingConflict.reply}
              onAccept={() => confirmConflict(true)}
              onReject={() => confirmConflict(false)}
              lang={lang}
            />
          )}

          <div ref={endRef} />
        </div>

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
              onChange={(e) => setInput(e.target.value.slice(0, 600))}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={locked}
              maxLength={600}
              placeholder={
                locked
                  ? t("p2.input.locked", lang)
                  : t("p2.input.placeholder", lang)
              }
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <span
              className={[
                "select-none font-mono text-[10px] tabular-nums",
                input.length >= 600
                  ? "text-destructive"
                  : input.length > 540
                    ? "text-amber-500"
                    : "text-muted-foreground/70",
              ].join(" ")}
              aria-label={t("p2.input.char_count_aria", lang)}
            >
              {input.length}/600
            </span>
            <Button
              size="icon"
              onClick={send}
              disabled={locked || !input.trim() || input.length > 600}
              className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-primary-glow text-primary-foreground"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {readyPopup.open && (
        <ReadyToSearchPopup
          countdown={readyPopup.countdown}
          onStayChat={() =>
            setReadyPopup({ open: false, countdown: 0, dismissed: true })
          }
          lang={lang}
        />
      )}
    </div>
  );
}

function ConflictCard({
  field,
  previousValue,
  proposedValue,
  reply,
  onAccept,
  onReject,
  lang,
}: {
  field: string;
  previousValue: unknown;
  proposedValue: unknown;
  reply: string;
  onAccept: () => void;
  onReject: () => void;
  lang: Lang;
}) {
  const label = fieldLabel(field, lang);
  const prev = formatValue(previousValue);
  const next = formatValue(proposedValue);
  return (
    <div className="flex animate-in fade-in slide-in-from-bottom-2 justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-warning/30 bg-warning/10 p-4">
        <div className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-warning">
          {t("p2.conflict.badge", lang)} : {label}
        </div>
        <p className="mb-3 text-sm text-foreground">{reply}</p>
        <div className="mb-4 rounded-lg border border-warning/20 bg-background/60 p-3 text-xs text-foreground/90">
          <div>
            <span className="font-mono uppercase tracking-wider text-muted-foreground">
              {t("p2.conflict.yes", lang)}
            </span>{" "}
            {t("p2.conflict.update.prefix", lang)} <strong>{label}</strong>{" "}
            {t("p2.conflict.update.from", lang)} <code>{prev}</code>{" "}
            {t("p2.conflict.update.to", lang)} <code>{next}</code>.
          </div>
          <div className="mt-1">
            <span className="font-mono uppercase tracking-wider text-muted-foreground">
              {t("p2.conflict.no", lang)}
            </span>{" "}
            {t("p2.conflict.keep.prefix", lang)} <strong>{label}</strong>{" "}
            {t("p2.conflict.keep.as", lang)} <code>{prev}</code>.
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={onAccept}
            className="h-8 rounded-lg bg-primary text-primary-foreground"
          >
            <Check className="mr-1 h-3.5 w-3.5" /> {t("p2.conflict.btn.accept", lang)}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onReject}
            className="h-8 rounded-lg"
          >
            <X className="mr-1 h-3.5 w-3.5" /> {t("p2.conflict.btn.reject", lang)}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ReadyToSearchPopup({
  countdown,
  onStayChat,
  lang,
}: {
  countdown: number;
  onStayChat: () => void;
  lang: Lang;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm">
      <div className="glass-strong w-[min(90vw,420px)] animate-in fade-in zoom-in-95 rounded-2xl border border-border p-6 shadow-[var(--shadow-elegant)]">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-glow text-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-primary">
            {t("p2.popup.badge", lang)}
          </div>
        </div>
        <h3 className="mb-2 text-lg font-semibold tracking-tight">
          {t("p2.popup.title", lang)}
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("p2.popup.redirect", lang)}{" "}
          <span className="font-mono font-semibold text-foreground">
            {countdown}{t("p2.popup.seconds", lang)}
          </span>
          …
        </p>
        <div className="flex justify-end">
          <Button
            size="sm"
            variant="outline"
            onClick={onStayChat}
            className="h-8 rounded-lg"
          >
            {t("p2.popup.stay", lang)}
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  role,
  content,
}: {
  role: "user" | "assistant";
  content: string;
}) {
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
