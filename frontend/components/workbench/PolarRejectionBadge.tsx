"use client";

import { AlertTriangle } from "lucide-react";

import type { PolarRejection } from "@/hooks/useComputationContext";

export interface PolarRejectionBadgeProps {
  // gh-634: legacy aeroplanes (pre-gh-630) store polar_by_config without
  // the `rejection` key, so the runtime value can be `undefined` even
  // though Pydantic's model_dump() emits `null` for new records.
  rejection: PolarRejection | null | undefined;
}

/**
 * gh-630: surface aerodynamically implausible polar-fit rejections
 * (k <= 0, e_oswald outside (0.4, 1.0]) to the user as a design warning.
 *
 * Renders nothing for `null`/`undefined` or for non-`design` categories —
 * sweep, data, and consistency rejections are internal-only. Callers
 * should pass `rejection` directly without category-routing.
 */
export function PolarRejectionBadge({ rejection }: PolarRejectionBadgeProps) {
  if (!rejection || rejection.category !== "design") {
    return null;
  }
  return (
    <div
      role="alert"
      className="inline-flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/15 px-2.5 py-1 text-xs leading-tight text-amber-200"
    >
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className="font-medium">Design issue:</span>
      <span>{rejection.hint}</span>
    </div>
  );
}
