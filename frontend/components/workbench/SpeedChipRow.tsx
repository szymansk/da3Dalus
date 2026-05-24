"use client";

import {
  Wind, AlertTriangle, Plane, Gauge, TrendingUp, Zap,
} from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
  readonly rightSlot?: React.ReactNode;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

export function SpeedChipRow({ ctx, isRecomputing, rightSlot }: Props) {
  const stale = isRecomputing;
  return (
    <div
      data-testid="chip-row-speeds"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={AlertTriangle}
        symbol="V_stall"
        description="Stall speed in clean configuration at 1 g"
        value={fmt(ctx?.v_stall_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol="V_min_sink"
        description="Speed for minimum sink rate — best endurance / longest glide time"
        value={fmt(ctx?.v_min_sink_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol="w_min"
        description="Minimum sink rate — vertical speed at V_min_sink (best endurance descent)"
        value={fmt(ctx?.min_sink_rate_mps, 2, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol="V_md"
        description="Minimum-drag speed — best L/D, longest glide distance"
        value={fmt(ctx?.v_md_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol={ctx?.v_cruise_auto ? "V_cruise*" : "V_cruise"}
        description={
          ctx?.v_cruise_auto
            ? "Design cruise speed (auto-derived from cruise sizing — asterisk)"
            : "Design cruise speed"
        }
        value={fmt(ctx?.v_cruise_mps, 1, " m/s")}
        stale={stale}
      />
      {/* gh-692: V_x / V_y exist only with a motor. Pure gliders (P/W = 0
          → is_glider=true) get them hidden; Motorsegler (is_glider=false)
          still see them. Same guard pattern as V_a / V_max / V_dive below. */}
      {!ctx?.is_glider && (
        <Chip
          icon={TrendingUp}
          symbol="V_x"
          description="Best angle-of-climb speed — steepest altitude gain per unit ground distance"
          value={fmt(ctx?.v_x_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      {!ctx?.is_glider && (
        <Chip
          icon={Plane}
          symbol="V_y"
          description="Best rate-of-climb speed — fastest altitude gain per unit time"
          value={fmt(ctx?.v_y_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      {!ctx?.is_glider && (
        <Chip
          icon={Gauge}
          symbol="V_a"
          description="Design manoeuvring speed — structural limit at full control deflection"
          value={fmt(ctx?.v_a_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      {!ctx?.is_glider && (
        <Chip
          icon={Gauge}
          symbol="V_max"
          description="Maximum operating speed"
          value={fmt(ctx?.v_max_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      {!ctx?.is_glider && (
        <Chip
          icon={Zap}
          symbol="V_dive"
          description="Design dive speed (heuristic: 1.4 × V_max)"
          value={fmt(ctx?.v_dive_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      <div className="flex-1" />
      {rightSlot}
    </div>
  );
}
