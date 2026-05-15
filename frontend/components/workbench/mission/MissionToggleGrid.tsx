"use client";

import React from "react";
import type { MissionPreset } from "@/hooks/useMissionPresets";

interface Props {
  readonly presets: MissionPreset[];
  readonly activeId: string;
  readonly comparisonIds: string[];
  readonly onToggle: (id: string) => void;
}

export function MissionToggleGrid({
  presets,
  activeId,
  comparisonIds,
  onToggle,
}: Props) {
  return (
    <div className="mt-3 rounded bg-card-muted p-2 grid grid-cols-2 gap-x-3 gap-y-1">
      {presets.map((p) => {
        const isActive = p.id === activeId;
        const isComparison = comparisonIds.includes(p.id);

        let textClass: string;
        if (isActive) textClass = "text-orange-500 font-semibold cursor-default";
        else if (isComparison) textClass = "text-sky-400";
        else textClass = "text-muted-foreground hover:text-foreground";

        let chipClass: string;
        if (isActive) chipClass = "bg-orange-500 border-orange-500";
        else if (isComparison) chipClass = "bg-sky-400 border-sky-400";
        else chipClass = "border border-border";

        return (
          <button
            key={p.id}
            type="button"
            disabled={isActive}
            onClick={() => onToggle(p.id)}
            className={`flex items-center gap-2 text-left text-xs py-1 ${textClass}`}
          >
            <span className={`inline-block w-3 h-3 rounded-sm ${chipClass}`} />
            {p.label}
            {isActive && (
              <span className="ml-auto text-[10px] text-muted-foreground">
                aktiv
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
