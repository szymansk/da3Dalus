"use client";

import { X } from "lucide-react";

interface NpMarker {
  type: "np";
  neutral_point_x: number;
  Cma: number | null;
  stability_class: string | null;
  solver: string;
}

interface CgMarker {
  type: "cg";
  cg_x_used: number;
  static_margin_pct: number | null;
  source: string;
}

interface RangeMarker {
  type: "range";
  cg_range_forward: number;
  cg_range_aft: number;
}

export type MarkerInfo = NpMarker | CgMarker | RangeMarker;

interface Props {
  readonly marker: MarkerInfo;
  readonly onClose: () => void;
}

function Row({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
        {value}
      </span>
    </div>
  );
}

function resolveTitle(type: MarkerInfo["type"]): string {
  if (type === "np") return "Neutral Point";
  if (type === "cg") return "Center of Gravity";
  return "CG Range";
}

export function MarkerDetailBox({ marker, onClose }: Props) {
  const title = resolveTitle(marker.type);

  return (
    <div className="flex min-w-[180px] flex-col gap-2 rounded-xl border border-border bg-card p-3 shadow-lg">
      <div className="flex items-center justify-between">
        <span className="font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-foreground">
          {title}
        </span>
        <button
          onClick={onClose}
          aria-label="close"
          className="flex size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
        >
          <X size={12} />
        </button>
      </div>
      <div className="flex flex-col gap-1">
        {marker.type === "np" && (
          <>
            <Row label="Position" value={`${marker.neutral_point_x.toFixed(3)} m`} />
            <Row label="Cm_alpha" value={marker.Cma != null ? marker.Cma.toFixed(3) : "—"} />
            <Row label="Stability" value={marker.stability_class ?? "—"} />
            <Row label="Solver" value={marker.solver} />
          </>
        )}
        {marker.type === "cg" && (
          <>
            <Row label="Position" value={`${marker.cg_x_used.toFixed(3)} m`} />
            <Row
              label="Static margin"
              value={marker.static_margin_pct != null ? `${marker.static_margin_pct.toFixed(1)}%` : "—"}
            />
            <Row label="Source" value={marker.source} />
          </>
        )}
        {marker.type === "range" && (
          <>
            <Row label="Forward limit" value={`${marker.cg_range_forward.toFixed(3)} m`} />
            <Row label="Aft limit" value={`${marker.cg_range_aft.toFixed(3)} m`} />
            <Row
              label="Range width"
              value={`${(marker.cg_range_aft - marker.cg_range_forward).toFixed(3)} m`}
            />
          </>
        )}
      </div>
    </div>
  );
}
