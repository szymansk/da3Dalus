"use client";

import { Target, Navigation } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import { cgDivergenceColor } from "./stability-overlay/divergence-color";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly cgAero: number | null;
  readonly isRecomputing: boolean;
  readonly rightSlot?: React.ReactNode;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

export function StabilityChipRow({ ctx, cgAero, isRecomputing, rightSlot }: Props) {
  const stale = isRecomputing;
  const cgValue = cgAero != null ? `${cgAero.toFixed(3)} m` : "–";
  const cgDescription =
    "Centre of gravity — aerodynamic balance value; component-derived value in parentheses when available";
  const cgValueNode = (
    <>
      <span className={stale ? "text-red-400" : ""}>{cgValue}</span>
      {cgAero != null && ctx?.cg_agg_m != null && ctx?.mac_m != null && (
        <span
          className={`ml-1 ${
            stale
              ? "text-red-400"
              : cgDivergenceColor(cgAero, ctx.cg_agg_m, ctx.mac_m)
          }`}
        >
          ({ctx.cg_agg_m.toFixed(3)})
        </span>
      )}
    </>
  );

  return (
    <div
      data-testid="chip-row-stability"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={Target}
        symbol="NP"
        description="Neutral point — aerodynamic centre of the whole aircraft"
        value={fmt(ctx?.x_np_m, 3, " m")}
        stale={stale}
      />
      <Chip
        icon={Navigation}
        symbol="SM"
        description="Static margin = (NP − CG) / MAC — target value used for trim balancing"
        value={
          ctx?.target_static_margin != null
            ? (ctx.target_static_margin * 100).toFixed(0) + "%"
            : "–"
        }
        stale={stale}
      />
      <Chip
        icon={Navigation}
        symbol="CG"
        description={cgDescription}
        valueNode={cgValueNode}
        stale={stale}
      />
      <div className="flex-1" />
      {rightSlot}
    </div>
  );
}
