"use client";

import { Info } from "lucide-react";

interface InfoTooltipProps {
  text: string;
  size?: number;
}

/**
 * Hoverable info icon that shows a styled tooltip.
 * Uses CSS group-hover instead of native `title` (which is unreliable inside buttons).
 */
export function InfoTooltip({ text, size = 11 }: Readonly<InfoTooltipProps>) {
  return (
    <span
      className="group/tip relative inline-flex shrink-0 text-muted-foreground hover:text-primary"
      onClick={(e) => e.stopPropagation()}
    >
      <Info size={size} />
      <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-max max-w-[240px] -translate-x-1/2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/tip:block">
        {text}
      </span>
    </span>
  );
}
