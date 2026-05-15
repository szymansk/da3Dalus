"use client";

import React, { useEffect, useState } from "react";
import { WorkbenchTwoPanel } from "@/components/workbench/WorkbenchTwoPanel";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { MissionCompliancePanel } from "@/components/workbench/mission/MissionCompliancePanel";
import { MissionObjectivesPanel } from "@/components/workbench/mission/MissionObjectivesPanel";
import type { AxisName } from "@/hooks/useMissionPresets";
import { AxisDrawer } from "@/components/workbench/mission/AxisDrawer";

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
        <AxisDrawer
          aeroplaneId={aeroplaneId}
          axis={drawerAxis}
          onClose={() => setDrawerAxis(null)}
        />
      )}
    </>
  );
}
