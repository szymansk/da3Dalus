"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Send, ChevronUp, ChevronDown, Bot, User, AlertCircle, Settings, Star, Trash2, CornerDownLeft } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useCopilot } from "@/hooks/useCopilot";
import type { CopilotMessageRead } from "@/hooks/useCopilot";
import { useCopilotProposal } from "@/hooks/useCopilotProposal";
import { Streamdown, defaultRemarkPlugins } from "streamdown";
import type { MathPlugin, PluginConfig, UrlTransform } from "streamdown";
import type { PluggableList } from "unified";
import remarkMath from "remark-math";
import remarkBreaks from "remark-breaks";
import rehypeKatex from "rehype-katex";

// ---------------------------------------------------------------------------
// Streamdown math plugin + security config (module-level — never recreated)
// ---------------------------------------------------------------------------

const mathPlugin: MathPlugin = {
  name: "katex",
  type: "math",
  remarkPlugin: remarkMath,
  rehypePlugin: rehypeKatex,
};

const streamdownPlugins: PluginConfig = { math: mathPlugin };

// Keep streamdown's GFM defaults (tables, etc.) but add remark-breaks so a
// single newline renders as a line break. The copilot often emits key figures
// one per line without list markers; without this they collapse into one run.
const copilotRemarkPlugins: PluggableList = [
  defaultRemarkPlugins.gfm,
  defaultRemarkPlugins.codeMeta,
  remarkBreaks,
];

/** Block images entirely; allow only https links. */
const copilotUrlTransform: UrlTransform = (url, key) => {
  if (key === "src") return null; // block all images
  if (url.startsWith("https://")) return url;
  return null;
};

// ---------------------------------------------------------------------------
// Message bubble helpers
// ---------------------------------------------------------------------------

function UserBubble({ message }: Readonly<{ message: CopilotMessageRead }>) {
  return (
    <div className="flex items-start gap-2 justify-end" data-testid="user-bubble">
      <div className="max-w-[80%] rounded-lg rounded-tr-sm bg-primary/10 px-3 py-2 text-[13px] text-foreground">
        {message.content}
      </div>
      <User size={16} className="mt-0.5 shrink-0 text-muted-foreground" />
    </div>
  );
}

function AssistantBubble({
  content,
  isStreaming = false,
}: Readonly<{ content: string; isStreaming?: boolean }>) {
  return (
    <div className="flex items-start gap-2" data-testid="assistant-bubble">
      <Bot size={16} className="mt-0.5 shrink-0 text-primary" />
      <div className="max-w-[80%] rounded-lg rounded-tl-sm bg-card px-3 py-2 text-[13px] text-foreground">
        <Streamdown
          plugins={streamdownPlugins}
          remarkPlugins={copilotRemarkPlugins}
          urlTransform={copilotUrlTransform}
          parseIncompleteMarkdown
          linkSafety={{ enabled: false }}
        >
          {content}
        </Streamdown>
        {isStreaming && (
          <span className="ml-0.5 inline-block h-3 w-0.5 animate-pulse bg-current" aria-hidden />
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }: Readonly<{ message: CopilotMessageRead }>) {
  if (message.role === "user") {
    return <UserBubble message={message} />;
  }
  if (message.role === "assistant") {
    return <AssistantBubble content={message.content} />;
  }
  return null;
}

function ToolChip({ label }: Readonly<{ label: string }>) {
  return (
    <div
      className="flex items-center gap-1.5 self-start rounded-full border border-border bg-card-muted px-2.5 py-1 text-[11px] text-muted-foreground"
      data-testid="tool-chip"
      role="status"
      aria-live="polite"
    >
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
      {label}
    </div>
  );
}

function ErrorBanner({
  message,
  onDismiss,
}: Readonly<{ message: string; onDismiss: () => void }>) {
  return (
    <div
      className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive"
      role="alert"
      data-testid="copilot-error"
    >
      <AlertCircle size={14} className="mt-0.5 shrink-0" />
      <span className="flex-1">{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        className="shrink-0 text-destructive/70 hover:text-destructive"
        aria-label="Dismiss error"
      >
        ×
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CopilotProposalBanner
// ---------------------------------------------------------------------------

interface CopilotProposalBannerProps {
  branchName: string;
  onReview?: () => void;
  onAdopt: () => void;
  onDiscard: () => void;
  busy: boolean;
}

function CopilotProposalBanner({
  branchName,
  onReview,
  onAdopt,
  onDiscard,
  busy,
}: CopilotProposalBannerProps) {
  return (
    <div
      className="flex items-center gap-2 border-t border-primary/30 bg-primary/5 px-6 py-1.5"
      role="status"
      aria-label="Copilot proposal pending"
      data-testid="copilot-proposal-banner"
    >
      <Settings size={12} className="shrink-0 text-primary" aria-hidden />
      <span className="flex-1 truncate text-[11px] font-medium text-primary">
        Copilot proposal pending
      </span>
      <span className="hidden max-w-[120px] truncate text-[10px] text-muted-foreground sm:block">
        {branchName}
      </span>
      <div className="flex shrink-0 items-center gap-1">
        {onReview && (
          <button
            type="button"
            onClick={onReview}
            disabled={busy}
            aria-label="Review copilot proposal"
            className="rounded px-2 py-0.5 text-[10px] font-medium text-primary ring-1 ring-primary/40 hover:bg-primary/10 disabled:opacity-50"
          >
            Review
          </button>
        )}
        <button
          type="button"
          onClick={() => { void onAdopt(); }}
          disabled={busy}
          aria-label="Adopt copilot proposal"
          className="flex items-center gap-1 rounded bg-primary px-2 py-0.5 text-[10px] font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Star size={9} aria-hidden />
          Adopt
        </button>
        <button
          type="button"
          onClick={() => { void onDiscard(); }}
          disabled={busy}
          aria-label="Discard copilot proposal"
          className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] text-destructive ring-1 ring-destructive/30 hover:bg-destructive/10 disabled:opacity-50"
        >
          <Trash2 size={9} aria-hidden />
          Discard
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// useEnterToSend — persists the "Enter sends" vs "Enter = newline" preference
// ---------------------------------------------------------------------------

const ENTER_TO_SEND_KEY = "copilot:enter-to-send";

function readEnterToSend(): boolean {
  if (typeof window === "undefined") return true;
  try {
    const stored = localStorage.getItem(ENTER_TO_SEND_KEY);
    if (stored !== null) return stored === "true";
  } catch {
    // localStorage unavailable (SSR, private mode, etc.)
  }
  return true;
}

function useEnterToSend() {
  // Lazy initializer: reads localStorage once on mount. SSR-safe because the
  // guard is inside readEnterToSend(). No useEffect needed → no set-state-in-effect lint.
  const [enterToSend, setEnterToSend] = useState<boolean>(readEnterToSend);

  const toggle = useCallback(() => {
    setEnterToSend((prev) => {
      const next = !prev;
      try {
        if (typeof window !== "undefined") {
          localStorage.setItem(ENTER_TO_SEND_KEY, String(next));
        }
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  return { enterToSend, toggle };
}

// ---------------------------------------------------------------------------
// CopilotStrip
// ---------------------------------------------------------------------------

interface CopilotStripProps {
  /**
   * Called when the user clicks "Review" on a pending copilot proposal.
   * If not provided, the Review button is hidden.
   */
  onOpenHistory?: () => void;
}

export function CopilotStrip({ onOpenHistory }: CopilotStripProps = {}) {
  const { aeroplaneId } = useAeroplaneContext();
  const {
    history,
    streamingText,
    activeToolLabel,
    errorMessage,
    isSending,
    sendMessage,
    clearError,
  } = useCopilot(aeroplaneId);

  const { enterToSend, toggle: toggleEnterToSend } = useEnterToSend();

  const { proposal } = useCopilotProposal(aeroplaneId);

  const [proposalBusy, setProposalBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [inputText, setInputText] = useState("");
  const threadEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom whenever the thread or streaming text changes
  useEffect(() => {
    if (open && threadEndRef.current) {
      threadEndRef.current.scrollIntoView?.({ behavior: "smooth" });
    }
  }, [open, history?.messages.length, streamingText, activeToolLabel]);

  const handleSend = useCallback(async () => {
    const text = inputText.trim();
    if (!text || isSending || !aeroplaneId) return;
    setInputText("");
    await sendMessage(text);
  }, [inputText, isSending, aeroplaneId, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key !== "Enter") return;
      // Never interfere with IME composition (CJK, etc.)
      if (e.nativeEvent.isComposing) return;
      // Shift+Enter always inserts newline — let browser handle it
      if (e.shiftKey) return;
      // Cmd/Ctrl+Enter sends in both modes; plain Enter sends only in default mode
      if (e.metaKey || e.ctrlKey || enterToSend) {
        e.preventDefault();
        void handleSend();
      }
      // Alt mode: plain Enter falls through to browser default (newline)
    },
    [handleSend, enterToSend],
  );

  const handleProposalAdopt = useCallback(async () => {
    if (!proposal) return;
    setProposalBusy(true);
    try {
      await proposal.adopt();
    } finally {
      setProposalBusy(false);
    }
  }, [proposal]);

  const handleProposalDiscard = useCallback(async () => {
    if (!proposal) return;
    setProposalBusy(true);
    try {
      await proposal.discard();
    } finally {
      setProposalBusy(false);
    }
  }, [proposal]);

  const noAeroplane = !aeroplaneId;
  const messages = history?.messages ?? [];
  const hasContent =
    messages.length > 0 || streamingText.length > 0 || !!activeToolLabel;

  // Hint text depends on current mode; "responding" takes precedence
  let inputHint = enterToSend
    ? "Enter to send · Shift+Enter for newline"
    : "Shift+Enter / Enter for newline · Ctrl/Cmd+Enter to send";
  if (isSending) inputHint = "Copilot is responding…";

  return (
    <footer className="shrink-0 border-t border-border bg-sidebar">
      {/* Copilot proposal pending banner (gh-939) */}
      {proposal && (
        <CopilotProposalBanner
          branchName={proposal.branch.name}
          onReview={onOpenHistory}
          onAdopt={handleProposalAdopt}
          onDiscard={handleProposalDiscard}
          busy={proposalBusy}
        />
      )}
      {/* Slim handle bar — always visible */}
      <div className="flex h-10 items-center gap-3 px-6">
        <span className="text-[13px] text-subtle-foreground">
          {noAeroplane ? "Select an aeroplane to use the copilot" : "Ask the copilot…"}
        </span>
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => { void handleSend(); }}
          disabled={noAeroplane || isSending || !inputText.trim()}
          aria-label="Send"
          className="flex h-7 w-7 items-center justify-center rounded-xl border border-border bg-card-muted hover:bg-sidebar-accent disabled:opacity-40"
        >
          <Send size={14} className="text-muted-foreground" />
        </button>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls="copilot-panel"
          aria-label={open ? "Collapse copilot panel" : "Expand copilot panel"}
          className="flex h-7 w-7 items-center justify-center rounded-xl border border-border bg-card-muted hover:bg-sidebar-accent"
        >
          {open ? (
            <ChevronDown size={14} className="text-muted-foreground" />
          ) : (
            <ChevronUp size={14} className="text-muted-foreground" />
          )}
        </button>
      </div>

      {/* Collapsible panel */}
      <div
        className={`grid transition-[grid-template-rows] duration-300 ease-out ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div
            id="copilot-panel"
            data-testid="copilot-panel"
            className="flex flex-col gap-3 px-6 pb-4 pt-2"
          >
            {/* Thread */}
            {hasContent && (
              <div
                className="flex max-h-72 flex-col gap-2 overflow-y-auto py-1"
                data-testid="copilot-thread"
              >
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}

                {/* Streaming in-progress assistant text */}
                {streamingText && (
                  <AssistantBubble content={streamingText} isStreaming />
                )}

                {/* Tool activity chip */}
                {activeToolLabel && <ToolChip label={activeToolLabel} />}

                <div ref={threadEndRef} />
              </div>
            )}

            {/* Error banner */}
            {errorMessage && (
              <ErrorBanner message={errorMessage} onDismiss={clearError} />
            )}

            {/* Input area */}
            <textarea
              className="w-full resize-none rounded-lg border border-border bg-card px-3 py-2 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
              rows={4}
              placeholder={noAeroplane ? "Select an aeroplane" : "Ask a design question…"}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={noAeroplane || isSending}
              aria-label="Copilot input"
            />

            <div className="flex items-center justify-between gap-2">
              {/* suppressHydrationWarning: initial value is read from localStorage
                  on the client, so it intentionally differs from the server's
                  default render for users who switched to alt mode. */}
              <span className="text-[11px] text-muted-foreground" suppressHydrationWarning>
                {inputHint}
              </span>
              <div className="flex shrink-0 items-center gap-1.5">
                <button
                  type="button"
                  onClick={toggleEnterToSend}
                  aria-pressed={enterToSend}
                  aria-label={enterToSend ? "Enter sends message" : "Enter inserts newline"}
                  title={enterToSend ? "Enter sends message (click to switch)" : "Enter inserts newline (click to switch)"}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card-muted text-muted-foreground hover:bg-sidebar-accent aria-pressed:text-primary"
                  suppressHydrationWarning
                >
                  <CornerDownLeft size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => { void handleSend(); }}
                  disabled={noAeroplane || isSending || !inputText.trim()}
                  aria-label="Send message"
                  className="flex items-center gap-1.5 rounded-lg border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent disabled:opacity-40"
                >
                  <Send size={12} />
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
