"use client";

import React, { useEffect, useState } from "react";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { MissionCompliancePanel } from "@/components/workbench/mission/MissionCompliancePanel";
import { MissionObjectivesPanel } from "@/components/workbench/mission/MissionObjectivesPanel";
import type { AxisName } from "@/hooks/useMissionPresets";

export default function MissionPage() {
  const { aeroplaneId, hydrated, openPicker } = useAeroplaneContext();
  const [drawerAxis, setDrawerAxis] = useState<AxisName | null>(null);

  useEffect(() => {
    if (hydrated && !aeroplaneId) openPicker();
  }, [hydrated, aeroplaneId, openPicker]);

  if (!aeroplaneId) {
    return (
      <WorkbenchTwoPanel leftWidth={480}>
        <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
          Select an aeroplane to view Mission compliance.
        </div>
        <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
          Select an aeroplane to edit its Mission objectives.
        </div>
      </WorkbenchTwoPanel>
    );
  }

  return (
    <>
      <WorkbenchTwoPanel leftWidth={480}>
        <div className="flex h-full flex-col rounded-2xl border border-border bg-card p-6">
          <MissionCompliancePanel
            aeroplaneId={aeroplaneId}
            onAxisClick={(axis) => setDrawerAxis(axis)}
          />
        </div>
        <div className="flex flex-col overflow-y-auto rounded-2xl border border-border bg-card p-6">
          <MissionObjectivesPanel aeroplaneId={aeroplaneId} />
        </div>
      </WorkbenchTwoPanel>

      {drawerAxis && (
        <div className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded border border-orange-500/40 bg-card px-4 py-2 text-xs text-muted-foreground">
          <span>
            Axis drilldown for{" "}
            <span className="font-mono text-orange-500">{drawerAxis}</span> —
            coming in Phase 7
          </span>
          <button
            type="button"
            onClick={() => setDrawerAxis(null)}
            aria-label="Close drilldown placeholder"
            className="text-muted-foreground hover:text-foreground"
          >
            ×
          </button>
        </div>
      )}
    </>
  );
}
