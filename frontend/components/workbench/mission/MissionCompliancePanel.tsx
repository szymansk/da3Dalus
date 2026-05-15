"use client";

import React, { useState } from "react";
import { MissionRadarChart } from "./MissionRadarChart";
import { MissionToggleGrid } from "./MissionToggleGrid";
import { useMissionKpis } from "@/hooks/useMissionKpis";
import { useMissionPresets, type AxisName } from "@/hooks/useMissionPresets";
import { useMissionObjectives } from "@/hooks/useMissionObjectives";

interface Props {
  readonly aeroplaneId: string;
  readonly onAxisClick: (axis: AxisName) => void;
}

export function MissionCompliancePanel({ aeroplaneId, onAxisClick }: Props) {
  const { data: objective } = useMissionObjectives(aeroplaneId);
  const { data: presets } = useMissionPresets();
  const [comparisons, setComparisons] = useState<string[]>([]);

  const activeId = objective?.mission_type ?? "trainer";
  const missionIds = [activeId, ...comparisons.filter((c) => c !== activeId)];
  const { data: kpis } = useMissionKpis(aeroplaneId, missionIds);

  if (!presets || !kpis) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  const activePreset = presets.find((p) => p.id === activeId);
  if (!activePreset) {
    return (
      <div className="text-sm text-muted-foreground">
        Mission preset &ldquo;{activeId}&rdquo; not found.
      </div>
    );
  }

  const comparisonPresets = comparisons
    .map((c) => presets.find((p) => p.id === c))
    .filter((p): p is NonNullable<typeof p> => Boolean(p));

  const toggle = (id: string) =>
    setComparisons((cs) =>
      cs.includes(id) ? cs.filter((x) => x !== id) : [...cs, id],
    );

  return (
    <div className="flex h-full flex-col">
      <h3 className="text-sm font-semibold text-orange-500 mb-2">
        ⊙ Mission Compliance
      </h3>
      <MissionRadarChart
        kpis={kpis}
        activeMissions={[activePreset, ...comparisonPresets]}
        onAxisClick={onAxisClick}
      />
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-3">
        Vergleichs-Profile
      </div>
      <MissionToggleGrid
        presets={presets}
        activeId={activeId}
        comparisonIds={comparisons}
        onToggle={toggle}
      />
    </div>
  );
}
