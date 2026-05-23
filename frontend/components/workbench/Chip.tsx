"use client";

import { renderSymbol } from "@/components/workbench/renderSymbol";

// Replace underscores with spaces so screen readers say
// "V min sink" instead of "V underscore min underscore sink".
function humanize(symbol: string): string {
  return symbol.replace(/_/g, " ");
}

export function Chip({
  icon: Icon,
  symbol,
  value,
  valueNode,
  description,
  stale = false,
  valueColorClassName,
}: {
  readonly icon: React.ComponentType<{ size: number; className: string }>;
  readonly symbol: string;
  readonly value?: string;
  readonly valueNode?: React.ReactNode;
  readonly description?: string;
  readonly stale?: boolean;
  readonly valueColorClassName?: string;
}) {
  // Stale (recompute in flight) always wins over caller-supplied colour:
  // the chip's value is provisional and that fact dominates any quality
  // / traffic-light signal.
  const valueClass = stale
    ? "text-red-400"
    : (valueColorClassName ?? "text-foreground");
  const ariaLabel = description
    ? `${humanize(symbol)}: ${description}`
    : humanize(symbol);
  return (
    <div
      role="group"
      tabIndex={0}
      aria-label={ariaLabel}
      className="group/chip relative flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5 focus:outline-none focus-visible:ring-1 focus-visible:ring-primary"
    >
      <Icon size={12} className="text-muted-foreground" />
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
        {renderSymbol(symbol)}
        {" = "}
        {valueNode ?? <span className={valueClass}>{value}</span>}
      </span>
      {description && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-max max-w-[240px] -translate-x-1/2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/chip:block group-focus-within/chip:block"
        >
          {description}
        </span>
      )}
    </div>
  );
}
