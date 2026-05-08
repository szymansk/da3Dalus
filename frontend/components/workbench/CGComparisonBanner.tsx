"use client";

import { useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { useCGComparison } from "@/hooks/useCGComparison";

interface Props {
  readonly aeroplaneId: string;
  readonly onCGSynced: () => void;
}

export function CGComparisonBanner({ aeroplaneId, onCGSynced }: Props) {
  const { data, isLoading, syncDesignCG } = useCGComparison(aeroplaneId);
  const [syncing, setSyncing] = useState(false);

  // Don't render if loading, no data, no component CG, or within tolerance
  if (isLoading || !data || data.component_cg_x == null || data.delta_x == null || data.within_tolerance !== false) {
    return null;
  }

  const deltaM = data.delta_x;
  const deltaCm = Math.abs(deltaM * 100);
  const isSevere = deltaCm > 5;

  const borderColor = isSevere ? "border-red-500/30" : "border-orange-500/30";
  const bgColor = isSevere ? "bg-red-500/10" : "bg-orange-500/10";
  const textColor = isSevere ? "text-red-400" : "text-orange-400";

  async function handleSync() {
    setSyncing(true);
    try {
      await syncDesignCG(data.component_cg_x!);
      onCGSynced();
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div
      className={`mx-4 mb-2 flex items-center gap-3 rounded-lg border ${borderColor} ${bgColor} px-4 py-2`}
      data-testid="cg-comparison-banner"
    >
      <AlertTriangle size={14} className={textColor} />
      <div className="flex flex-1 flex-col gap-0.5">
        <span className={`font-[family-name:var(--font-jetbrains-mono)] text-[12px] ${textColor}`}>
          Component CG ({data.component_cg_x.toFixed(3)}m) differs from design CG ({data.design_cg_x.toFixed(3)}m) by {deltaCm.toFixed(1)}cm
        </span>
      </div>
      <button
        onClick={handleSync}
        disabled={syncing}
        className={`flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-[11px] ${textColor} hover:bg-sidebar-accent disabled:opacity-50`}
        data-testid="sync-cg-button"
      >
        <RefreshCw size={10} className={syncing ? "animate-spin" : ""} />
        {syncing ? "Syncing..." : "Update design CG"}
      </button>
    </div>
  );
}
