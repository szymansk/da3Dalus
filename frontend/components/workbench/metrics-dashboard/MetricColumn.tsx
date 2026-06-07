"use client";

// Click-dummy (#881, v2) — a single column inside the fixed-height metrics band.
// Three presentations: "tab" (collapsed, narrow vertical strip) · "tile"
// (compact, equal-width column) · "large" (full width). The band height stays
// constant (~20vh) in every mode; content scrolls if it overflows.

import { Maximize2, X } from "lucide-react";

export type ColumnMode = "tab" | "tile" | "large";

export function MetricColumn({
  title,
  icon: Icon,
  mode,
  onActivate,
  onCollapse,
  headline,
  tile,
  large,
}: {
  readonly title: string;
  readonly icon: React.ComponentType<{ size: number; className: string }>;
  readonly mode: ColumnMode;
  readonly onActivate: () => void;
  readonly onCollapse: () => void;
  readonly headline: string;
  readonly tile: React.ReactNode;
  readonly large: React.ReactNode;
}) {
  // ── collapsed narrow tab ──────────────────────────────────────
  if (mode === "tab") {
    return (
      <button
        type="button"
        onClick={onActivate}
        title={`${title} — ${headline}`}
        className="flex h-full w-9 shrink-0 flex-col items-center gap-2 rounded-lg border border-border bg-card py-2 text-subtle-foreground transition-colors hover:border-border-strong hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-primary"
      >
        <Icon size={14} className="text-primary" />
        <span className="text-[11px] font-semibold uppercase tracking-wide [writing-mode:vertical-rl]">{title}</span>
      </button>
    );
  }

  const isLarge = mode === "large";
  return (
    <section
      className={`flex h-full min-w-0 flex-col rounded-lg border bg-card ${isLarge ? "flex-1 border-border-strong" : "flex-1 cursor-pointer hover:border-border-strong"} border-border transition-colors`}
      data-testid={`metric-col-${title.toLowerCase()}`}
      data-mode={mode}
      onClick={isLarge ? undefined : onActivate}
    >
      <header className="flex shrink-0 items-center gap-1.5 px-2.5 py-1.5">
        <Icon size={13} className="text-primary" />
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-foreground">{title}</h3>
        {isLarge ? (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onCollapse(); }}
            title="Collapse"
            aria-label={`Collapse ${title}`}
            className="ml-auto rounded p-0.5 text-subtle-foreground hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-primary"
          >
            <X size={13} className="" />
          </button>
        ) : (
          <Maximize2 size={11} className="ml-auto text-subtle-foreground" />
        )}
      </header>
      {/* overflow-visible so hover tooltips aren't clipped (real impl: render via portal) */}
      <div className="min-h-0 flex-1 overflow-visible px-2.5 pb-2">
        {isLarge ? large : tile}
      </div>
    </section>
  );
}
