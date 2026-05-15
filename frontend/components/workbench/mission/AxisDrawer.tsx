"use client";

import React from "react";
import { useMissionKpis } from "@/hooks/useMissionKpis";
import type { AxisName } from "@/hooks/useMissionPresets";
import type { Provenance } from "@/hooks/useMissionKpis";

interface Props {
  readonly aeroplaneId: string;
  readonly axis: AxisName;
  readonly onClose: () => void;
}

const LABEL: Record<AxisName, string> = {
  stall_safety: "Stall Safety",
  glide: "Glide",
  climb: "Climb",
  cruise: "Cruise",
  maneuver: "Maneuver",
  wing_loading: "Wing Loading",
  field_friendliness: "Field Friendliness",
};

function provenanceColor(p: Provenance): string {
  if (p === "computed") return "text-green-400";
  if (p === "estimated") return "text-yellow-400";
  return "text-muted-foreground";
}

export function AxisDrawer({ aeroplaneId, axis, onClose }: Props) {
  const { data: kpis } = useMissionKpis(aeroplaneId, []);
  if (!kpis) return null;
  const k = kpis.ist_polygon[axis];
  if (!k) return null;

  const valueText =
    k.value == null ? "–" : `${k.value.toFixed(3)} ${k.unit ?? ""}`;
  const scoreText =
    k.score_0_1 == null ? "–" : `${(k.score_0_1 * 100).toFixed(0)} %`;

  return (
    <div className="fixed right-4 top-20 w-80 rounded-lg border-l-2 border-orange-500 bg-card p-4 shadow-lg z-50">
      <div className="flex items-start justify-between">
        <h4 className="text-orange-500 font-semibold text-sm">{LABEL[axis]}</h4>
        <button
          type="button"
          onClick={onClose}
          aria-label="close"
          className="text-muted-foreground hover:text-foreground"
        >
          ×
        </button>
      </div>

      <div className="mt-3 space-y-2 text-xs">
        <Row label="Ist" value={valueText} />
        <Row label="Range" value={`${k.range_min.toFixed(2)} … ${k.range_max.toFixed(2)}`} />
        <Row label="Score" value={scoreText} />
        <Row
          label="Provenance"
          value={<span className={provenanceColor(k.provenance)}>{k.provenance}</span>}
        />
      </div>

      <div className="mt-3 rounded bg-background p-2 font-mono text-[10px] text-muted-foreground">
        {k.formula}
      </div>

      {k.warning && (
        <div className="mt-3 text-[11px] text-yellow-400">
          {`⚠ ${k.warning}`}
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  value,
}: {
  readonly label: string;
  readonly value: React.ReactNode;
}) {
  return (
    <div className="flex justify-between border-b border-border/30 py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
