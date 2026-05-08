"use client";

import type { AnalysisStatus } from "@/hooks/useAnalysisStatus";
import { Loader2 } from "lucide-react";

interface Props {
  readonly status: AnalysisStatus;
}

export function AnalysisStatusIndicator({ status }: Props) {
  const { op_counts, total_ops, retrim_active, retrim_debouncing } = status;

  if (total_ops === 0) return null;

  const dirtyCount = op_counts["DIRTY"] ?? 0;
  const computingCount = op_counts["COMPUTING"] ?? 0;
  const trimmedCount = op_counts["TRIMMED"] ?? 0;

  if (computingCount > 0 || (retrim_active && trimmedCount < total_ops)) {
    const done = trimmedCount;
    return (
      <span
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="inline-flex items-center gap-1.5 text-xs text-orange-400"
      >
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
        Re-trimming {done}/{total_ops}…
      </span>
    );
  }

  if (retrim_debouncing) {
    return (
      <span
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="inline-flex items-center gap-1.5 text-xs text-zinc-400"
      >
        <span className="h-2 w-2 rounded-full bg-zinc-500" aria-hidden="true" />
        Waiting for changes…
      </span>
    );
  }

  if (dirtyCount > 0) {
    return (
      <span
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="inline-flex items-center gap-1.5 text-xs text-orange-400"
      >
        <span className="h-2 w-2 rounded-full bg-orange-500" aria-hidden="true" />
        {dirtyCount} point{dirtyCount !== 1 ? "s" : ""} outdated
      </span>
    );
  }

  return (
    <span
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="inline-flex items-center gap-1.5 text-xs text-emerald-400"
    >
      <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden="true" />
      All trimmed
    </span>
  );
}
