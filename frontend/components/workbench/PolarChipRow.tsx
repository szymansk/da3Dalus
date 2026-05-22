"use client";

import { Wind, Gauge, Activity, Target, TrendingUp, AlertTriangle } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import {
  computeK, computeCLmd, computeEMax, computeRho,
  qualityColorClassName, rhoColorClassName,
} from "@/lib/polar";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
}

function fmt(v: number | null, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}
function fmtRe(v: number | null | undefined) {
  return v == null ? "–" : v.toExponential(1);
}

const BAIL_TOOLTIP =
  "Parabolic polar fit was rejected (see e*). Derived polar quantities are not meaningful when the polar is non-parabolic.";

const INTUITIVE_FORM = " ρ = (C_L,md/C_L,max)²";

function rhoTooltip(rho: number | null, isGlider: boolean): string {
  if (rho == null) return BAIL_TOOLTIP;
  if (rho >= 1.0) {
    return (
      "Polar health: L/D-max coincident with or past stall — polar is degenerate. " +
      "Resize wing: raise AR or improve C_L,max — see Matching Chart." +
      INTUITIVE_FORM
    );
  }
  const amber = isGlider ? 2 / 3 : 1 / 3;
  if (rho >= amber) {
    return isGlider
      ? "Polar health: tightening sailplane optimum. Still healthy for glider regime." +
          INTUITIVE_FORM
      : "Polar health: min-sink point at/below stall. L/D-max still reachable. " +
          "Consider raising AR or lowering W/S — see Matching Chart." +
          INTUITIVE_FORM;
  }
  return (
    "Polar health: healthy. L/D-max sits comfortably above stall." + INTUITIVE_FORM
  );
}

export function PolarChipRow({ ctx, isRecomputing }: Props) {
  const stale = isRecomputing;

  const cd0 = ctx?.cd0 ?? null;
  const eFromCtx = ctx?.e_oswald ?? null;
  const fallbackUsed = !!ctx?.e_oswald_fallback_used;
  const ar = ctx?.aspect_ratio ?? null;
  const clMax = ctx?.polar_by_config?.clean?.cl_max ?? null;
  const isGlider = !!ctx?.is_glider;
  const quality = ctx?.e_oswald_quality ?? "unknown";

  const k = computeK(eFromCtx, fallbackUsed, ar);
  const clMd = computeCLmd(cd0, eFromCtx, fallbackUsed, ar);
  const eMax = computeEMax(cd0, eFromCtx, fallbackUsed, ar);
  const rho = computeRho(cd0, eFromCtx, fallbackUsed, ar, clMax);

  // Displayed e: when fallback used, show the 0.80 fallback explicitly
  // with the asterisk; otherwise the real fit value. Fallback always
  // renders muted (quality necessarily 'unknown').
  const eDisplayValue = fallbackUsed ? 0.8 : eFromCtx;
  const eSymbol = fallbackUsed ? "e*" : "e";
  const eTooltip = fallbackUsed
    ? "Polar fit was rejected — fallback 0.80 used (regime-naive). All derived polar quantities (k, C_L,md, L/D-max, ρ) are therefore suppressed."
    : "Oswald efficiency — combined non-elliptical-lift-distribution loss and parasite-drag-with-lift. Typical 0.70–0.95. Colour reflects fit quality.";
  const eQualityColour = fallbackUsed
    ? qualityColorClassName("unknown")
    : qualityColorClassName(quality);

  return (
    <div
      data-testid="chip-row-polar"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={Wind}
        symbol="Re"
        description="Reynolds number at cruise (characteristic length = MAC). Polar shape is Re-dependent; this row's metrics describe cruise-Re behaviour."
        value={fmtRe(ctx?.reynolds)}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="C_D0"
        description="Zero-lift drag coefficient (parasite drag). Lower is better. ρ uses this together with e and AR. Source: stability run (single-CL eval)."
        value={fmt(cd0, 4)}
        stale={stale}
      />
      <Chip
        icon={Activity}
        symbol={eSymbol}
        description={eTooltip}
        value={fmt(eDisplayValue, 2)}
        valueColorClassName={eQualityColour}
        stale={stale}
      />
      <Chip
        icon={Activity}
        symbol="k"
        description={k == null
          ? BAIL_TOOLTIP
          : "Induced-drag factor k = 1/(πeAR). Drag rises as k·C_L². Lower k = less induced drag at the same lift."}
        value={fmt(k, 4)}
        stale={stale}
      />
      <Chip
        icon={Target}
        symbol="C_L,md"
        description={clMd == null
          ? BAIL_TOOLTIP
          : "Lift coefficient where L/D is maximum (best glide). Should sit well below C_L,max. If C_L,md ≥ C_L,max your wing must stall to reach best glide."}
        value={fmt(clMd, 2)}
        stale={stale}
      />
      <Chip
        icon={AlertTriangle}
        symbol="C_L,max"
        description="Maximum lift coefficient (clean configuration, no flaps). From AeroBuildup — known to underestimate at Re < 3×10⁵; treat as conservative for RC."
        value={fmt(clMax, 2)}
        stale={stale}
      />
      <Chip
        icon={TrendingUp}
        symbol="(L/D)_max"
        description={eMax == null
          ? BAIL_TOOLTIP
          : "Maximum lift-to-drag ratio. The headline polar number. Sailplane > 30 · GA 10–18 · jet transport 16–22 · trainer 8–12. Formula: ½·√(πeAR/C_D0)."}
        value={fmt(eMax, 1)}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="ρ"
        description={rhoTooltip(rho, isGlider)}
        value={fmt(rho, 2)}
        valueColorClassName={rhoColorClassName(rho, isGlider)}
        stale={stale}
      />
      <div className="flex-1" />
    </div>
  );
}
