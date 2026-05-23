"use client";

import { Square, Ruler, ArrowLeftRight, Gauge } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

export function GeometryChipRow({ ctx, isRecomputing }: Props) {
  const stale = isRecomputing;
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
      <div className="flex-1" />
    </div>
  );
}
