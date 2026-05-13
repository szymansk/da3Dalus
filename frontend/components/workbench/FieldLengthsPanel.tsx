"use client";

import { useState } from "react";
import { Loader2, Plane, ArrowDown } from "lucide-react";
import { useFieldLengths, type TakeoffMode, type LandingMode } from "@/hooks/useFieldLengths";

interface Props {
  readonly aeroplaneId: string;
}

const TAKEOFF_MODE_LABELS: Record<TakeoffMode, string> = {
  runway: "Runway",
  hand_launch: "Hand Launch",
  bungee: "Bungee",
  catapult: "Catapult",
};

const LANDING_MODE_LABELS: Record<LandingMode, string> = {
  runway: "Runway",
  belly_land: "Belly Land",
};

function DistanceCell({
  label,
  value,
}: {
  readonly label: string;
  readonly value: number | null | undefined;
}) {
  const formatted = value != null ? `${value.toFixed(0)} m` : "–";
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
        {label}
      </span>
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] font-semibold text-foreground">
        {formatted}
      </span>
    </div>
  );
}

export function FieldLengthsPanel({ aeroplaneId }: Props) {
  const [takeoffMode, setTakeoffMode] = useState<TakeoffMode>("runway");
  const [landingMode, setLandingMode] = useState<LandingMode>("runway");

  const { data, isLoading, error } = useFieldLengths(aeroplaneId, {
    takeoffMode,
    landingMode,
  });

  return (
    <div className="mt-6">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 pb-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Field Lengths
        </span>
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          Roskam §3.4 simplified ground-roll
        </span>
      </div>

      {/* Mode selectors */}
      <div className="mb-3 flex gap-3 px-4">
        <div className="flex flex-col gap-1">
          <label className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Takeoff mode
          </label>
          <select
            value={takeoffMode}
            onChange={(e) => setTakeoffMode(e.target.value as TakeoffMode)}
            className="rounded border border-border bg-card px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          >
            {Object.entries(TAKEOFF_MODE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Landing mode
          </label>
          <select
            value={landingMode}
            onChange={(e) => setLandingMode(e.target.value as LandingMode)}
            className="rounded border border-border bg-card px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          >
            {Object.entries(LANDING_MODE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results card */}
      <div className="rounded-xl border border-border bg-card px-4 py-3">
        {isLoading && (
          <div className="flex items-center gap-2">
            <Loader2 size={12} className="animate-spin text-muted-foreground" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
              Computing…
            </span>
          </div>
        )}
        {error && !isLoading && (
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
            {/* Show friendly message for missing thrust or stall speed */}
            {(error as { status?: number }).status === 422
              ? "Set t_static_N thrust assumption to enable takeoff distance"
              : "Field lengths unavailable (run assumption recompute first)"}
          </span>
        )}
        {data && !isLoading && (
          <div className="flex flex-col gap-4">
            {/* Takeoff row */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-1.5">
                <Plane size={11} className="text-orange-400" />
                <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-orange-400">
                  Takeoff
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <DistanceCell label="Ground roll" value={data.s_to_ground_m} />
                <DistanceCell label="To clear 50 ft" value={data.s_to_50ft_m} />
              </div>
              <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                V_LOF = {data.vto_obstacle_mps.toFixed(1)} m/s
              </span>
            </div>

            <div className="border-t border-border" />

            {/* Landing row */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-1.5">
                <ArrowDown size={11} className="text-blue-400" />
                <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-blue-400">
                  Landing
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <DistanceCell label="Ground roll" value={data.s_ldg_ground_m} />
                <DistanceCell label="From 50 ft" value={data.s_ldg_50ft_m} />
              </div>
              <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                V_app = {data.vapp_mps.toFixed(1)} m/s
              </span>
            </div>

            {/* Warnings */}
            {data.warnings.length > 0 && (
              <div className="rounded-lg bg-orange-900/30 px-3 py-2">
                {data.warnings.map((w, i) => (
                  <p
                    key={i}
                    className="font-[family-name:var(--font-geist-sans)] text-[10px] text-orange-400"
                  >
                    ⚠ {w}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
