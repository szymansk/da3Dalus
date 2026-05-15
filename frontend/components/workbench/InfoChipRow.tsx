"use client";

import {
  Wind,
  Ruler,
  Target,
  Navigation,
  Gauge,
  AlertTriangle,
  Loader2,
  Plane,
  TrendingUp,
  Zap,
} from "lucide-react";
import { useComputationContext } from "@/hooks/useComputationContext";
import { renderSymbol } from "@/components/workbench/renderSymbol";

interface Props {
  readonly aeroplaneId: string | null;
  readonly cgAero: number | null;
  readonly isRecomputing?: boolean;
  readonly rightSlot?: React.ReactNode;
}

function Chip({
  icon: Icon,
  symbol,
  value,
  description,
  stale = false,
}: {
  readonly icon: React.ComponentType<{ size: number; className: string }>;
  readonly symbol: string;
  readonly value: string;
  readonly description?: string;
  readonly stale?: boolean;
}) {
  const valueClass = stale ? "text-red-400" : "text-foreground";
  const ariaLabel = description ? `${symbol}: ${description}` : symbol;
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className="group/chip relative flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5"
    >
      <Icon size={12} className="text-muted-foreground" />
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
        {renderSymbol(symbol)}
        {" = "}
        <span className={valueClass}>{value}</span>
      </span>
      {description && (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-max max-w-[240px] -translate-x-1/2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/chip:block"
        >
          {description}
        </span>
      )}
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
  const cgDescription =
    "Centre of gravity — aerodynamic balance value; component-derived value in parentheses when available";

  // Values that depend on the geometry-driven recompute. While a job is
  // in flight these are stale → render in red so the user knows not to
  // trust them until the recompute settles.
  const stale = !!isRecomputing;

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-border bg-card px-4 py-3">
      {/* Envelope speeds (gh-476: extended chip set) */}
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
      <Chip
        icon={TrendingUp}
        symbol="V_x"
        description="Best angle-of-climb speed — steepest altitude gain per unit ground distance"
        value={fmt(ctx?.v_x_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Plane}
        symbol="V_y"
        description="Best rate-of-climb speed — fastest altitude gain per unit time"
        value={fmt(ctx?.v_y_mps, 1, " m/s")}
        stale={stale}
      />
      {/* V_a hidden for gliders — they use V_RA per CS-22 (separate ticket). */}
      {!ctx?.is_glider && (
        <Chip
          icon={Gauge}
          symbol="V_a"
          description="Design manoeuvring speed — structural limit at full control deflection"
          value={fmt(ctx?.v_a_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      <Chip
        icon={Gauge}
        symbol={ctx?.is_glider ? "V_NE" : "V_max"}
        description={
          ctx?.is_glider
            ? "Never-exceed speed (CS-22 placard speed for gliders)"
            : "Maximum operating speed"
        }
        value={fmt(ctx?.v_max_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Zap}
        symbol="V_dive"
        description="Design dive speed (heuristic: 1.4 × V_max)"
        value={fmt(ctx?.v_dive_mps, 1, " m/s")}
        stale={stale}
      />
      {/* Divider between envelope speeds and aero geometry */}
      <div className="h-5 w-px bg-border" />
      <Chip
        icon={Wind}
        symbol="Re"
        description="Reynolds number at cruise, characteristic length = MAC"
        value={fmtRe(ctx?.reynolds)}
        stale={stale}
      />
      <Chip
        icon={Ruler}
        symbol="MAC"
        description="Mean Aerodynamic Chord — reference length for force and moment coefficients"
        value={fmt(ctx?.mac_m, 2, " m")}
        stale={stale}
      />
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
      <div
        role="group"
        aria-label={`CG: ${cgDescription}`}
        className="group/chip relative flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5"
      >
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
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-max max-w-[240px] -translate-x-1/2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/chip:block"
        >
          {cgDescription}
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
