"use client";

import {
  type FormEvent,
  type KeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  createSession,
  submitQuery,
  type QueryResponse,
  type RelatedTopic,
  type Source,
} from "@/lib/api";

// ── Message type used in local state ──

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  urgency?: "emergency" | "normal" | "clarification_needed";
  followUpQuestions?: string[];
  sources?: Source[];
  relatedTopics?: RelatedTopic[];
};

// ── Main component ──

export function ChatWorkspace() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── create session on mount ──
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await createSession("New conversation");
        if (!cancelled) setSessionId(s.id);
      } catch {
        if (!cancelled)
          setError("Could not connect to the backend. Is it running on :8000?");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── auto-scroll on new content ──
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

  // ── submit handler ──
  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      const q = input.trim();
      if (!q || !sessionId || isLoading) return;

      setInput("");
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: q }]);
      setIsLoading(true);

      try {
        const data: QueryResponse = await submitQuery(sessionId, q);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.answer,
            urgency: data.urgency,
            followUpQuestions: data.follow_up_questions,
            sources: data.sources,
            relatedTopics: data.related_topics,
          },
        ]);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Something went wrong",
        );
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [input, sessionId, isLoading],
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // ── new chat ──
  const startNewChat = async () => {
    try {
      const s = await createSession("New conversation");
      setSessionId(s.id);
      setMessages([]);
      setError(null);
      setIsSidebarOpen(false);
    } catch {
      setError("Failed to create new session");
    }
  };

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      {/* ── Desktop sidebar ── */}
      <aside className="hidden w-64 shrink-0 flex-col bg-surface-sidebar shadow-[2px_0_8px_0_rgba(0,0,0,0.35)] md:flex">
        <div className="shrink-0 px-4 pb-2 pt-4">
          <button
            type="button"
            onClick={startNewChat}
            className="w-full rounded-lg bg-surface-elevated px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            + New chat
          </button>
        </div>
        <div className="px-4 py-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Current session
          </h2>
          {sessionId && (
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {sessionId.slice(0, 8)}…
            </p>
          )}
        </div>
      </aside>

      {/* ── Chat area ── */}
      <div className="relative flex min-w-0 flex-1 flex-col bg-background">
        {/* Mobile sidebar toggle */}
        <div className="flex items-center gap-2 px-4 py-2 md:hidden">
          <button
            type="button"
            onClick={() => setIsSidebarOpen(true)}
            className="rounded-md bg-surface-elevated px-3 py-1.5 text-sm text-foreground shadow-sm hover:bg-muted"
          >
            Menu
          </button>
          <button
            type="button"
            onClick={startNewChat}
            className="rounded-md bg-surface-elevated px-3 py-1.5 text-sm text-foreground shadow-sm hover:bg-muted"
          >
            + New
          </button>
        </div>

        {/* Message area */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div
            ref={scrollRef}
            className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5 sm:px-6 lg:px-8"
          >
            <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-5">
              {/* Empty state */}
              {messages.length === 0 && !isLoading && (
                <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
                  <h2 className="text-lg font-semibold text-foreground">
                    Medical Symptom Assistant
                  </h2>
                  <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
                    Ask a health-related question and get informational answers
                    grounded in sources from MedlinePlus, WHO, and CDC.
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Not a substitute for professional medical advice.
                  </p>
                </div>
              )}

              {/* Messages */}
              {messages.map((msg, i) => (
                <MessageBubble
                  key={i}
                  message={msg}
                  onFollowUp={(q) => {
                    setInput(q);
                    setTimeout(() => inputRef.current?.focus(), 0);
                  }}
                />
              ))}

              {/* Loading indicator */}
              {isLoading && <TypingIndicator />}

              {/* Error */}
              {error && (
                <div className="rounded-lg border border-red-800/50 bg-red-950/30 px-4 py-3 text-sm text-red-300">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Input area */}
          <div className="border-t border-border px-4 pb-5 pt-3 sm:px-6 sm:pb-6 sm:pt-4">
            <form
              onSubmit={handleSubmit}
              className="mx-auto flex max-w-2xl items-end gap-2"
            >
              <label className="sr-only" htmlFor="chat-input">
                Message
              </label>
              <textarea
                ref={inputRef}
                id="chat-input"
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  sessionId
                    ? "Ask a health information question…"
                    : "Connecting…"
                }
                disabled={!sessionId || isLoading}
                className="max-h-40 min-h-[42px] w-full resize-none rounded-xl bg-surface-elevated px-3 py-2.5 text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || !sessionId || isLoading}
                className="h-[42px] shrink-0 rounded-xl bg-foreground px-5 text-sm font-medium text-background shadow-sm transition-opacity hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send
              </button>
            </form>
            <p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-muted-foreground">
              Informational only — not a diagnosis. Seek professional care for
              urgent or worsening symptoms.
            </p>
          </div>
        </div>

        {/* Mobile sidebar overlay */}
        {isSidebarOpen && (
          <div className="absolute inset-0 z-20 flex md:hidden">
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setIsSidebarOpen(false)}
              className="h-full flex-1 bg-black/60"
            />
            <aside className="flex h-full w-64 flex-col bg-surface-sidebar shadow-[-2px_0_8px_0_rgba(0,0,0,0.35)]">
              <div className="flex shrink-0 items-center justify-between px-4 pb-2 pt-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Menu
                </h2>
                <button
                  type="button"
                  onClick={() => setIsSidebarOpen(false)}
                  className="rounded-md bg-muted px-2 py-1 text-xs text-foreground hover:bg-surface-elevated"
                >
                  Close
                </button>
              </div>
              <div className="px-4 py-2">
                <button
                  type="button"
                  onClick={startNewChat}
                  className="w-full rounded-lg bg-surface-elevated px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
                >
                  + New chat
                </button>
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ──

function MessageBubble({
  message,
  onFollowUp,
}: {
  message: ChatMessage;
  onFollowUp?: (q: string) => void;
}) {
  const [showSources, setShowSources] = useState(false);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[#1d82f5] px-4 py-2.5 text-sm text-white sm:max-w-[70%]">
          {message.content}
        </div>
      </div>
    );
  }

  const isEmergency = message.urgency === "emergency";
  const isClarification = message.urgency === "clarification_needed";

  return (
    <div className="flex flex-col gap-2">
      {/* Urgency banner */}
      {isEmergency && (
        <div className="rounded-lg border border-red-700/60 bg-red-950/40 px-4 py-2.5 text-sm font-medium text-red-300">
          Urgent — This query mentions symptoms that may require immediate
          medical attention. If you are experiencing a medical emergency, call
          your local emergency number.
        </div>
      )}

      {/* Assistant bubble */}
      <div className="flex justify-start">
        <div
          className={`max-w-[90%] rounded-2xl rounded-bl-md px-4 py-3 text-sm leading-relaxed shadow-sm sm:max-w-[78%] ${
            isEmergency
              ? "border border-red-800/40 bg-red-950/20 text-foreground"
              : "bg-surface-elevated text-foreground"
          }`}
        >
          {message.content.split("\n").map((line, i) => (
            <p key={i} className={i > 0 ? "mt-2" : ""}>
              {line}
            </p>
          ))}
        </div>
      </div>

      {/* Follow-up question chips (for vague queries) */}
      {isClarification &&
        message.followUpQuestions &&
        message.followUpQuestions.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <p className="text-xs text-muted-foreground">Try answering:</p>
            <div className="flex flex-wrap gap-1.5">
              {message.followUpQuestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => onFollowUp?.(q)}
                  className="rounded-lg border border-border bg-surface px-3 py-1.5 text-left text-xs text-foreground transition-colors hover:bg-muted"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

      {/* Related conditions with confidence */}
      {message.relatedTopics && message.relatedTopics.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.relatedTopics.map((t) => (
            <span
              key={t.name}
              title={t.reason || undefined}
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs ${
                t.confidence === "moderate"
                  ? "border-blue-800/40 bg-blue-950/20 text-blue-300"
                  : "border-border bg-surface text-muted-foreground"
              }`}
            >
              {t.name}
              {t.confidence && (
                <span className="opacity-60">({t.confidence})</span>
              )}
            </span>
          ))}
        </div>
      )}

      {/* Sources toggle */}
      {message.sources && message.sources.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowSources((s) => !s)}
            className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >
            {showSources
              ? "Hide sources"
              : `${message.sources.length} source${message.sources.length > 1 ? "s" : ""}`}
          </button>

          {showSources && (
            <div className="mt-2 space-y-2">
              {message.sources.map((s) => (
                <div
                  key={s.id}
                  className="rounded-lg border border-border bg-surface p-3"
                >
                  <p className="text-xs font-medium text-foreground">
                    {s.title}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {s.snippet}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-md bg-surface-elevated px-4 py-3 shadow-sm">
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
      </div>
    </div>
  );
}
