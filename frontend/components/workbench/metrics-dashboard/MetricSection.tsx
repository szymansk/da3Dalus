"use client";

// Click-dummy (#881) — generic 3-state section chrome.
// States: collapsed (header + headline only) · compact · large.
// The "only one large at a time" invariant is owned by the parent dashboard.

import { ChevronRight, ChevronDown, Maximize2 } from "lucide-react";
import type { SectionState } from "./metricsMock";

const STATES: { key: SectionState; icon: typeof ChevronRight; title: string }[] = [
  { key: "collapsed", icon: ChevronRight, title: "Collapsed" },
  { key: "compact", icon: ChevronDown, title: "Compact" },
  { key: "large", icon: Maximize2, title: "Large" },
];

export function MetricSection({
  title,
  icon: Icon,
  state,
  onSetState,
  headline,
  compact,
  large,
}: {
  readonly title: string;
  readonly icon: React.ComponentType<{ size: number; className: string }>;
  readonly state: SectionState;
  readonly onSetState: (s: SectionState) => void;
  readonly headline: React.ReactNode;
  readonly compact: React.ReactNode;
  readonly large: React.ReactNode;
}) {
  return (
    <section
      className={`rounded-lg border border-border bg-card transition-colors ${state === "large" ? "border-border-strong" : ""}`}
      data-testid={`metric-section-${title.toLowerCase()}`}
      data-state={state}
    >
      <header className="flex items-center gap-2 px-3 py-2">
        <Icon size={14} className="text-primary" />
        <h3 className="text-[12px] font-semibold uppercase tracking-wide text-foreground">{title}</h3>
        {/* headline values stay visible in every state */}
        <div className="ml-2 min-w-0 flex-1 truncate font-[family-name:var(--font-geist-mono)] text-[11px] text-muted-foreground">
          {state === "collapsed" && headline}
        </div>
        <div className="flex items-center gap-0.5">
          {STATES.map(({ key, icon: SIcon, title: t }) => (
            <button
              key={key}
              type="button"
              title={t}
              aria-label={`${title}: ${t} view`}
              aria-pressed={state === key}
              onClick={() => onSetState(key)}
              className={`rounded p-1 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary ${
                state === key ? "bg-sidebar-accent text-primary" : "text-subtle-foreground hover:text-foreground"
              }`}
            >
              <SIcon size={13} className="" />
            </button>
          ))}
        </div>
      </header>
      {state !== "collapsed" && (
        <div className="border-t border-border px-3 py-2">
          {state === "large" ? large : compact}
        </div>
      )}
    </section>
  );
}
