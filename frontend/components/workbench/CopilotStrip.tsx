"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Send, ChevronUp, ChevronDown, Bot, User, AlertCircle } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useCopilot } from "@/hooks/useCopilot";
import type { CopilotMessageRead } from "@/hooks/useCopilot";
import { Streamdown } from "streamdown";
import type { MathPlugin, PluginConfig, UrlTransform } from "streamdown";
import remarkMath from "remark-math";
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
// CopilotStrip
// ---------------------------------------------------------------------------

export function CopilotStrip() {
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
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        void handleSend();
      }
    },
    [handleSend],
  );

  const noAeroplane = !aeroplaneId;
  const messages = history?.messages ?? [];
  const hasContent =
    messages.length > 0 || streamingText.length > 0 || !!activeToolLabel;

  return (
    <footer className="shrink-0 border-t border-border bg-sidebar">
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

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground">
                {isSending ? "Copilot is responding…" : "Cmd+Enter to send"}
              </span>
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
    </footer>
  );
}
