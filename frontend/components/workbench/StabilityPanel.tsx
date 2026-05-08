"use client";

import type { StabilityData } from "@/hooks/useStability";
import { StabilitySideView } from "@/components/workbench/StabilitySideView";

interface Props {
  readonly data: StabilityData | null;
  readonly isComputing: boolean;
  readonly error: string | null;
  readonly onCompute: () => void;
}

export function StabilityPanel({ data, isComputing, error, onCompute }: Props) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <div className="flex-1" />
        <button
          onClick={onCompute}
          disabled={isComputing}
          className="flex items-center gap-1.5 rounded-full bg-[#FF8400] px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isComputing ? "Computing..." : "Compute Stability"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-red-400">
            {error}
          </span>
        </div>
      )}

      {/* Empty state */}
      {!data && !isComputing && !error && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
            No stability data. Click Compute Stability to analyze.
          </span>
        </div>
      )}

      {/* Computing spinner */}
      {isComputing && !data && (
        <div className="flex flex-1 items-center justify-center">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Running stability analysis...
          </span>
        </div>
      )}

      {/* Content */}
      {data && <StabilitySideView data={data} />}
    </div>
  );
}
