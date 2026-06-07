"use client";

import { useState } from "react";
import { Send, ChevronUp, ChevronDown } from "lucide-react";

export function CopilotStrip() {
  const [open, setOpen] = useState(false);

  return (
    <footer className="shrink-0 border-t border-border bg-sidebar">
      {/* Slim handle bar — always visible */}
      <div className="flex h-10 items-center gap-3 px-6">
        <span className="text-[13px] text-subtle-foreground">Ask the copilot…</span>
        <div className="flex-1" />
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-xl border border-border bg-card-muted hover:bg-sidebar-accent"
          aria-label="Send"
        >
          <Send size={14} className="text-muted-foreground" />
        </button>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
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

      {/* Collapsible panel — slides open/closed via the grid-rows trick */}
      <div
        className={`grid transition-[grid-template-rows] duration-300 ease-out ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div
            data-testid="copilot-panel"
            className="flex flex-col gap-3 px-6 pb-4 pt-2"
          >
            <textarea
              className="w-full resize-none rounded-lg border border-border bg-card px-3 py-2 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              rows={4}
              placeholder="Ask a design question…"
            />
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground">
                Copilot is in preview — responses are not yet connected to the backend.
              </span>
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-lg border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
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
