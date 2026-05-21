"use client";

import { HelpCircle } from "lucide-react";

interface Props {
  readonly label: string;
  readonly description?: string;
  readonly htmlFor?: string;
}

/**
 * Form-field label with an optional info-icon that reveals a dark-themed
 * tooltip on hover or keyboard focus. Mirrors the InfoChipRow chip-tooltip
 * pattern (`group-hover/info:block group-focus-within/info:block`) for
 * visual consistency across the workbench.
 *
 * The icon is keyboard-focusable (`tabIndex={0}`) so the tooltip is
 * surfaceable without a pointing device.
 */
export function InfoLabel({ label, description, htmlFor }: Props) {
  if (!description) {
    return (
      <label
        htmlFor={htmlFor}
        className="block text-xs text-muted-foreground mb-1"
      >
        {label}
      </label>
    );
  }
  return (
    <label
      htmlFor={htmlFor}
      className="group/info relative mb-1 flex items-center gap-1 text-xs text-muted-foreground"
    >
      <span>{label}</span>
      <span
        tabIndex={0}
        data-testid="info-icon"
        className="inline-flex cursor-help items-center focus:outline-none focus-visible:text-foreground"
      >
        <HelpCircle
          size={11}
          className="text-muted-foreground/60"
          aria-hidden="true"
        />
        <span className="sr-only">Info</span>
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-50 mb-1.5 hidden w-max max-w-[280px] -translate-y-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/info:block group-focus-within/info:block"
      >
        {description}
      </span>
    </label>
  );
}
