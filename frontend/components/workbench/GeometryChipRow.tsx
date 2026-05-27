"use client";

import { Square, Ruler, ArrowLeftRight, Gauge, MapPin } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

// gh-477: format the landing-field chip value with a "/ NN m available"
// suffix when the mission spec has an ``available_field_length_m``. The
// suffix and the ``sufficient`` flag drive the green / red / neutral
// styling below — keep them in lock-step.
function fmtLandingField(ctx: ComputationContext | null | undefined): string {
  const l = ctx?.landing_field_length_m;
  if (l == null) return "–";
  const sufficient = ctx?.landing_field_sufficient;
  // We don't have the raw available_field_length_m on the context (only
  // the boolean comparison result), so the chip shows the L_landing
  // number and uses the sufficient flag for colour. The mission page
  // surfaces the available length for the user to verify directly.
  if (sufficient === null || sufficient === undefined) {
    return `${l.toFixed(0)} m`;
  }
  return sufficient ? `${l.toFixed(0)} m ✓` : `${l.toFixed(0)} m ✗`;
}

export function GeometryChipRow({ ctx, isRecomputing }: Props) {
  const stale = isRecomputing;
  const landingSurface = ctx?.landing_surface_used ?? null;
  // gh-477: green when the planned field is long enough, red when not,
  // default (no class) when the user hasn't set ``available_field_length_m``.
  let landingFieldClassName: string | undefined;
  if (ctx?.landing_field_sufficient === true) {
    landingFieldClassName = "text-emerald-400";
  } else if (ctx?.landing_field_sufficient === false) {
    landingFieldClassName = "text-red-400";
  }
  return (
    <div
      data-testid="chip-row-geometry"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={Square}
        symbol="S_ref"
        description="Reference area — projected wing area used to non-dimensionalize forces (C_L = L / (q · S_ref))"
        value={fmt(ctx?.s_ref_m2, 3, " m²")}
        stale={stale}
      />
      <Chip
        icon={Ruler}
        symbol="MAC"
        description="Mean Aerodynamic Chord (= C_ref in AVL/ASB) — reference chord for pitching moment coefficient (C_m = M_pitch / (q · S_ref · C_ref))"
        value={fmt(ctx?.mac_m, 2, " m")}
        stale={stale}
      />
      <Chip
        icon={ArrowLeftRight}
        symbol="B_ref"
        description="Reference span — wingspan used to non-dimensionalize roll and yaw moments (C_l = M_roll / (q · S_ref · B_ref))"
        value={fmt(ctx?.b_ref_m, 2, " m")}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="AR"
        description="Aspect ratio = b² / S_ref (main wing). Higher AR ⇒ less induced drag."
        value={fmt(ctx?.aspect_ratio, 2)}
        stale={stale}
      />
      <Chip
        icon={MapPin}
        symbol="L_landing"
        description={
          "Required landing field length — safety · (15 m flare + V_TD² / (2·g·μ_eff))" +
          (landingSurface ? `. Surface used: ${landingSurface}.` : "")
        }
        value={fmtLandingField(ctx)}
        stale={stale}
        valueColorClassName={landingFieldClassName}
      />
      <div className="flex-1" />
    </div>
  );
}
