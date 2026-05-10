"use client";

import { AlertTriangle, Loader2, Plus } from "lucide-react";
import { useDesignAssumptions } from "@/hooks/useDesignAssumptions";
import { useRecomputeStatus } from "@/hooks/useRecomputeStatus";
import { AssumptionRow } from "@/components/workbench/AssumptionRow";
import { CGComparisonBanner } from "@/components/workbench/CGComparisonBanner";

interface Props {
  readonly aeroplaneId: string;
}

export function AssumptionsPanel({ aeroplaneId }: Props) {
  const {
    data,
    isLoading,
    error,
    seedDefaults,
    updateEstimate,
    switchSource,
    mutate,
  } = useDesignAssumptions(aeroplaneId);
  const { isRecomputing } = useRecomputeStatus(aeroplaneId);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 size={16} className="animate-spin text-muted-foreground" />
        <span className="ml-2 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
          Loading assumptions...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-red-400">
          Failed to load assumptions
        </span>
      </div>
    );
  }

  const assumptions = data?.assumptions ?? [];
  const warningsCount = data?.warnings_count ?? 0;

  if (assumptions.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
          No design assumptions yet
        </span>
        <button
          onClick={seedDefaults}
          className="flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-2 text-[12px] text-foreground hover:bg-sidebar-accent"
          data-testid="seed-defaults-button"
        >
          <Plus size={12} />
          Seed Defaults
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Design Assumptions
        </span>
        {warningsCount > 0 && (
          <span
            className="flex items-center gap-1 rounded-full bg-orange-900/40 px-2 py-0.5 text-[10px] text-orange-400"
            data-testid="warnings-badge"
          >
            <AlertTriangle size={10} />
            {warningsCount}
          </span>
        )}
        {isRecomputing && (
          <span
            className="flex items-center gap-1 rounded-full bg-orange-500/15 px-2 py-0.5 text-[10px] text-orange-400"
            data-testid="recomputing-indicator"
          >
            <Loader2 size={10} className="animate-spin" />
            Recomputing…
          </span>
        )}
      </div>

      {/* CG comparison warning */}
      <CGComparisonBanner aeroplaneId={aeroplaneId} onCGSynced={() => mutate()} />

      {/* Rows */}
      <div className="rounded-xl border border-border bg-card">
        {assumptions.map((a) => (
          <AssumptionRow
            key={a.id}
            assumption={a}
            onUpdateEstimate={updateEstimate}
            onSwitchSource={switchSource}
          />
        ))}
      </div>
    </div>
  );
}
