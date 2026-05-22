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
  RefreshCw,
  TrendingUp,
  Zap,
  Square,
  ArrowLeftRight,
} from "lucide-react";
import { useComputationContext } from "@/hooks/useComputationContext";
import { Chip } from "@/components/workbench/Chip";
import { cgDivergenceColor } from "./stability-overlay/divergence-color";
import { TaillessBanner } from "./TaillessBanner";

interface Props {
  readonly aeroplaneId: string | null;
  readonly cgAero: number | null;
  readonly isRecomputing?: boolean;
  readonly rightSlot?: React.ReactNode;
}

export function InfoChipRow({ aeroplaneId, cgAero, isRecomputing, rightSlot }: Props) {
  const { data: ctx, mutate } = useComputationContext(aeroplaneId, { isRecomputing });

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

  // gh-581: surface the tailless UX banner above the chip rows when
  // backend-derived `is_tailless = true` (no horizontal-tail wing). The
  // banner explains that tail-volume sizing is not applicable and the
  // SM corridor is tighter (see #579 + Apogee hybrid-strategy guidance).
  const isTailless = !!ctx?.is_tailless;

  // gh-575: split the chips into two rows (envelope speeds + aero geometry)
  // with a user-triggered refresh button on row 1.
  return (
    <div className="flex flex-col gap-2 border-t border-border bg-card px-4 py-3">
      {isTailless && (
        <div className="flex">
          <TaillessBanner />
        </div>
      )}
      {/* Row 1 — envelope speeds (gh-476: extended chip set) */}
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
        {/* V_max hidden for gliders — gh-563: no powertrain to define V_max, and
            V_NE is a CS-22 placard speed with no user input. */}
        {!ctx?.is_glider && (
          <Chip
            icon={Gauge}
            symbol="V_max"
            description="Maximum operating speed"
            value={fmt(ctx?.v_max_mps, 1, " m/s")}
            stale={stale}
          />
        )}
        {/* V_dive hidden for gliders — gh-573: the 1.4 × V_max heuristic is invalid
            without V_max (hidden by gh-563); CS-22 V_D is a placard value. */}
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
        {/* gh-575: Recomputing pill kept next to the refresh button so users see
            the in-flight state co-located with the action that triggered it. */}
        {isRecomputing && (
          <span
            className="flex items-center gap-1 rounded-full bg-orange-500/15 px-2 py-1 text-[11px] text-orange-400"
            data-testid="recomputing-chip"
          >
            <Loader2 size={11} className="animate-spin" />
            Recomputing…
          </span>
        )}
        {/* gh-575: refresh button revalidates the SWR-cached computation context. */}
        <button
          type="button"
          aria-label="Refresh computation context"
          onClick={() => mutate()}
          disabled={isRecomputing}
          className="flex items-center gap-1 rounded-full bg-card-muted px-2.5 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {/* Row 2 — aero geometry */}
      <div
        data-testid="chip-row-geometry"
        className="flex flex-wrap items-center gap-2"
      >
        <Chip
          icon={Wind}
          symbol="Re"
          description="Reynolds number at cruise, characteristic length = MAC"
          value={fmtRe(ctx?.reynolds)}
          stale={stale}
        />
        {/* gh-593: reference triplet S_ref · MAC · B_ref grouped for visual
            cohesion. All three are the AVL/ASB non-dimensionalisation
            references for force and moment coefficients. */}
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
    </div>
  );
}
