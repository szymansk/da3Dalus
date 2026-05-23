"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useComputationContext } from "@/hooks/useComputationContext";
import { SpeedChipRow } from "@/components/workbench/SpeedChipRow";
import { GeometryChipRow } from "@/components/workbench/GeometryChipRow";
import { PolarChipRow } from "@/components/workbench/PolarChipRow";
import { StabilityChipRow } from "@/components/workbench/StabilityChipRow";
import { TaillessBanner } from "./TaillessBanner";

interface Props {
  readonly aeroplaneId: string | null;
  readonly cgAero: number | null;
  readonly isRecomputing?: boolean;
  readonly rightSlot?: React.ReactNode;
}

export function InfoChipRow({ aeroplaneId, cgAero, isRecomputing, rightSlot }: Props) {
  const { data: ctx, mutate } = useComputationContext(aeroplaneId, { isRecomputing });
  const recomputing = !!isRecomputing;
  const isTailless = !!ctx?.is_tailless;

  // gh-575: Recomputing pill + refresh button live in Row 1's rightSlot
  // so the in-flight state is co-located with the action that triggered it.
  const refreshSlot = (
    <>
      {recomputing && (
        <span
          className="flex items-center gap-1 rounded-full bg-orange-500/15 px-2 py-1 text-[11px] text-orange-400"
          data-testid="recomputing-chip"
        >
          <Loader2 size={11} className="animate-spin" />
          Recomputing…
        </span>
      )}
      <button
        type="button"
        aria-label="Refresh computation context"
        onClick={() => mutate()}
        disabled={recomputing}
        className="flex items-center gap-1 rounded-full bg-card-muted px-2.5 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw size={12} />
      </button>
    </>
  );

  return (
    <div className="flex flex-col gap-2 border-t border-border bg-card px-4 py-3">
      {isTailless && (
        <div className="flex">
          <TaillessBanner />
        </div>
      )}
      <SpeedChipRow ctx={ctx} isRecomputing={recomputing} rightSlot={refreshSlot} />
      <GeometryChipRow ctx={ctx} isRecomputing={recomputing} />
      <PolarChipRow ctx={ctx} isRecomputing={recomputing} />
      <StabilityChipRow
        ctx={ctx}
        cgAero={cgAero}
        isRecomputing={recomputing}
        rightSlot={rightSlot}
      />
    </div>
  );
}
