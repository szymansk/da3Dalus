"use client";

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { PowertrainTab } from "@/components/workbench/PowertrainTab";

/**
 * Top-level "Powertrain" workbench step (between Analysis and Components).
 * Promoted out of the Analysis sub-tabs (gh-976/gh-977) to a first-class tab.
 */
export default function PowertrainPage() {
  const { aeroplaneId } = useAeroplaneContext();

  if (!aeroplaneId) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="text-[13px] text-muted-foreground">No aeroplane selected</span>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-auto">
      <PowertrainTab aeroplaneId={aeroplaneId} />
    </div>
  );
}
