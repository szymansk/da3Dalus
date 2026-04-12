"use client";

import { Play, Plus, Download } from "lucide-react";

export function ActionRow() {
  return (
    <div className="flex items-center gap-2">
      <button className="flex items-center gap-2 rounded-[--radius-pill] bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90">
        <Play size={14} />
        <span>Preview STL</span>
      </button>
      <button className="flex items-center gap-1.5 rounded-[--radius-pill] border border-border bg-card-muted px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent">
        <Plus size={14} />
        <span>Wing</span>
      </button>
      <button className="flex items-center gap-1.5 rounded-[--radius-pill] border border-border bg-card-muted px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent">
        <Plus size={14} />
        <span>Fuselage</span>
      </button>
      <button className="flex items-center gap-1.5 rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent">
        <Download size={14} />
        <span>Download STEP</span>
      </button>
    </div>
  );
}
