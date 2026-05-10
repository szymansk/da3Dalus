"use client";

import { Wind, Ruler, Target, Navigation, Gauge, AlertTriangle, Loader2 } from "lucide-react";
import { useComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly aeroplaneId: string | null;
  readonly cgAero: number | null;
  readonly isRecomputing?: boolean;
  readonly rightSlot?: React.ReactNode;
}

function Chip({
  icon: Icon,
  prefix,
  value,
  stale = false,
}: {
  readonly icon: React.ComponentType<{ size: number; className: string }>;
  readonly prefix: string;
  readonly value: string;
  readonly stale?: boolean;
}) {
  const valueClass = stale ? "text-red-400" : "text-foreground";
  return (
    <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
      <Icon size={12} className="text-muted-foreground" />
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
        {prefix}<span className={valueClass}>{value}</span>
      </span>
    </div>
  );
}

function cgDivergenceColor(cgAero: number, cgAgg: number, mac: number): string {
  const deltaPct = (Math.abs(cgAgg - cgAero) / mac) * 100;
  if (deltaPct < 5) return "text-emerald-400";
  if (deltaPct <= 15) return "text-orange-400";
  return "text-red-400";
}

export function InfoChipRow({ aeroplaneId, cgAero, isRecomputing, rightSlot }: Props) {
  const { data: ctx } = useComputationContext(aeroplaneId, { isRecomputing });

  const fmt = (v: number | null | undefined, decimals: number, suffix = "") =>
    v != null ? `${v.toFixed(decimals)}${suffix}` : "–";

  const fmtRe = (v: number | null | undefined) => (v == null ? "–" : v.toExponential(1));

  const cgValue = cgAero != null ? `${cgAero.toFixed(3)} m` : "–";

  // Values that depend on the geometry-driven recompute. While a job is
  // in flight these are stale → render in red so the user knows not to
  // trust them until the recompute settles.
  const stale = !!isRecomputing;

  return (
    <div className="flex items-center gap-2 border-t border-border bg-card px-4 py-3">
      <Chip icon={AlertTriangle} prefix="V_stall = " value={fmt(ctx?.v_stall_mps, 1, " m/s")} stale={stale} />
      <Chip icon={Wind} prefix="V_cruise = " value={fmt(ctx?.v_cruise_mps, 1, " m/s")} stale={stale} />
      <Chip icon={Gauge} prefix="V_max = " value={fmt(ctx?.v_max_mps, 1, " m/s")} stale={stale} />
      <Chip icon={Wind} prefix="Re ≈ " value={fmtRe(ctx?.reynolds)} stale={stale} />
      <Chip icon={Ruler} prefix="MAC = " value={fmt(ctx?.mac_m, 2, " m")} stale={stale} />
      <Chip icon={Target} prefix="NP = " value={fmt(ctx?.x_np_m, 3, " m")} stale={stale} />
      <Chip
        icon={Navigation}
        prefix="SM = "
        value={
          ctx?.target_static_margin != null
            ? (ctx.target_static_margin * 100).toFixed(0) + "%"
            : "–"
        }
        stale={stale}
      />
      <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
        <Navigation size={12} className="text-muted-foreground" />
        <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
          {"CG = "}
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
        </span>
      </div>
      <div className="flex-1" />
      {isRecomputing && (
        <span
          className="flex items-center gap-1 rounded-full bg-orange-500/15 px-2 py-1 text-[11px] text-orange-400"
          data-testid="recomputing-chip"
        >
          <Loader2 size={11} className="animate-spin" />
          Recomputing…
        </span>
      )}
      {rightSlot}
    </div>
  );
}
