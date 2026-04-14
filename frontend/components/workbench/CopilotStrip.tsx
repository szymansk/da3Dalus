"use client";

import { Send, ChevronUp } from "lucide-react";

export function CopilotStrip() {
  return (
    <footer className="flex h-10 shrink-0 items-center gap-3 border-t border-border bg-sidebar px-6">
      <span className="text-[13px] text-subtle-foreground">
        Ask the copilot…
      </span>
      <div className="flex-1" />
      <button className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card-muted hover:bg-sidebar-accent">
        <Send size={14} className="text-muted-foreground" />
      </button>
      <button className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card-muted hover:bg-sidebar-accent">
        <ChevronUp size={14} className="text-muted-foreground" />
      </button>
    </footer>
  );
}
