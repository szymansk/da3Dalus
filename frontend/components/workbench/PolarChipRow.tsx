"use client";

import { Wind, Gauge, Activity, Target, TrendingUp, AlertTriangle } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import {
  computeK, computeCLmd, computeEMax, computeRho,
  qualityColorClassName, rhoColorClassName, rhoThresholdsForProfile,
} from "@/lib/polar";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  if (v == null || !Number.isFinite(v)) return "–";
  return `${v.toFixed(decimals)}${suffix}`;
}
function fmtRe(v: number | null | undefined) {
  if (v == null || !Number.isFinite(v)) return "–";
  return v.toExponential(1);
}

const BAIL_TOOLTIP =
  "Parabolic polar fit was rejected (see e*). Derived polar quantities are not meaningful when the polar is non-parabolic.";

const INTUITIVE_FORM = " ρ = (C_L,md/C_L,max)²";

/**
 * Returns the human-readable reason a derived chip rendered `—`.
 *
 * Three cases are distinguished so we never blame the parabolic-fit
 * rejection for a problem that is actually a missing/non-physical
 * input (gh-626 review #2 + #3):
 *
 *   1. fallbackUsed         → BAIL_TOOLTIP (fit rejected)
 *   2. ar / clMax / cd0 / e missing or non-physical → enumerate which
 *   3. value computed fine  → caller passes the normal description
 */
function derivedChipTooltip(
  fallbackUsed: boolean,
  inputs: {
    cd0: number | null;
    e: number | null;
    ar: number | null;
    needsClMax: boolean;
    clMax: number | null;
  },
  normalDescription: string,
): string {
  if (fallbackUsed) return BAIL_TOOLTIP;
  const isBadNum = (v: number | null) =>
    v == null || !Number.isFinite(v) || v <= 0;
  const missing: string[] = [];
  if (isBadNum(inputs.cd0)) missing.push("C_D0");
  if (isBadNum(inputs.e)) missing.push("e");
  if (isBadNum(inputs.ar)) missing.push("AR");
  if (inputs.needsClMax && isBadNum(inputs.clMax)) missing.push("C_L,max");
  if (missing.length > 0) {
    return (
      `Cannot compute — missing or non-physical input(s): ${missing.join(", ")}. ` +
      "Trigger an assumption recompute or check the wing geometry."
    );
  }
  return normalDescription;
}

function rhoTooltip(
  rho: number | null,
  isGlider: boolean,
  fallbackUsed: boolean,
  inputs: {
    cd0: number | null;
    e: number | null;
    ar: number | null;
    clMax: number | null;
  },
): string {
  if (rho == null) {
    return derivedChipTooltip(
      fallbackUsed,
      { ...inputs, needsClMax: true },
      // Should not normally surface — rho==null implies one of the
      // branches above. Defensive fallback string.
      "Polar health metric not computable from current inputs.",
    );
  }
  const { amber } = rhoThresholdsForProfile(isGlider);
  if (rho >= 1.0) {
    return (
      "Polar health: L/D-max coincident with or past stall — polar is degenerate. " +
      "Resize wing: raise AR or improve C_L,max — see Matching Chart." +
      INTUITIVE_FORM
    );
  }
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
  const cleanPolar = ctx?.polar_by_config?.clean;
  const clMax = cleanPolar?.cl_max ?? null;
  const isGlider = !!ctx?.is_glider;
  const quality = ctx?.e_oswald_quality ?? "unknown";

  // gh-636: e provenance distinguishes the AeroBuildup-Trefftz path
  // (`aerobuildup_trefftz`) from the legacy parabolic-fit path (`fit`) and the
  // 0.8 regime-naive default (`fallback`). The asterisk marker is only shown
  // when the e value is the regime-naive default — fit-based and AB-Trefftz
  // values are both real measurements.
  const eProvenance = cleanPolar?.e_oswald_provenance ?? null;
  const eIsRealMeasurement =
    eProvenance === "aerobuildup_trefftz" || eProvenance === "fit";
  // Backwards-compat: when polar_by_config lacks provenance (legacy data),
  // fall back to the gh-626 `e_oswald_fallback_used` flag.
  const eShowsFallbackMarker = eProvenance ? !eIsRealMeasurement : fallbackUsed;

  // gh-636: empirical (L/D)max + CL,md straight from the AeroBuildup sweep
  // — `max(CL/CD)` over the sweep, no fit required. Formula-derived values
  // remain as legacy fallback for pre-gh-636 recomputes.
  const ldMaxBackend = cleanPolar?.ld_max ?? null;
  const clMdBackend = cleanPolar?.cl_at_ld_max ?? null;

  const k = computeK(eFromCtx, fallbackUsed, ar);
  const clMd = clMdBackend ?? computeCLmd(cd0, eFromCtx, fallbackUsed, ar);
  const eMax = ldMaxBackend ?? computeEMax(cd0, eFromCtx, fallbackUsed, ar);
  const rho = computeRho(cd0, eFromCtx, fallbackUsed, ar, clMax);

  // Displayed e: when fallback used, show the 0.80 fallback explicitly
  // with the asterisk; otherwise the real fit value. Fallback always
  // renders muted (quality necessarily 'unknown').
  const eDisplayValue: number | null = eShowsFallbackMarker ? 0.8 : eFromCtx;
  const eSymbol = eShowsFallbackMarker ? "e*" : "e";
  const eTooltip = eShowsFallbackMarker
    ? "Polar fit was rejected — fallback 0.80 used (regime-naive). All derived polar quantities (k, C_L,md, L/D-max, ρ) are therefore suppressed."
    : eProvenance === "aerobuildup_trefftz"
      ? "Oswald efficiency from AeroBuildup's Trefftz-plane induced drag at (L/D)max (gh-636). Typical 0.70–0.95."
      : "Oswald efficiency — combined non-elliptical-lift-distribution loss and parasite-drag-with-lift. Typical 0.70–0.95. Colour reflects fit quality.";
  const eQualityColour = fallbackUsed
    ? qualityColorClassName("unknown")
    : qualityColorClassName(quality);

  // Shared input bundle for the cause-distinguishing tooltip helpers.
  const derivedInputs = { cd0, e: eFromCtx, ar };

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
        description={derivedChipTooltip(
          fallbackUsed,
          { ...derivedInputs, needsClMax: false, clMax: null },
          "Induced-drag factor k = 1/(πeAR). Drag rises as k·C_L². Lower k = less induced drag at the same lift.",
        )}
        value={fmt(k, 4)}
        stale={stale}
      />
      <Chip
        icon={Target}
        symbol="C_L_md"
        description={derivedChipTooltip(
          fallbackUsed,
          { ...derivedInputs, needsClMax: false, clMax: null },
          "Lift coefficient where L/D is maximum (best glide). Should sit well below C_L,max. If C_L,md ≥ C_L,max your wing must stall to reach best glide.",
        )}
        value={fmt(clMd, 2)}
        stale={stale}
      />
      <Chip
        icon={AlertTriangle}
        symbol="C_L_max"
        description="Maximum lift coefficient (clean configuration, no flaps). From AeroBuildup — known to underestimate at Re < 3×10⁵; treat as conservative for RC."
        value={fmt(clMax, 2)}
        stale={stale}
      />
      <Chip
        icon={TrendingUp}
        symbol="(L/D)_max"
        description={derivedChipTooltip(
          fallbackUsed,
          { ...derivedInputs, needsClMax: false, clMax: null },
          "Maximum lift-to-drag ratio. The headline polar number. Sailplane > 30 · GA 10–18 · jet transport 16–22 · trainer 8–12. Formula: ½·√(πeAR/C_D0).",
        )}
        value={fmt(eMax, 1)}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="ρ"
        description={rhoTooltip(rho, isGlider, fallbackUsed, {
          cd0, e: eFromCtx, ar, clMax,
        })}
        value={fmt(rho, 2)}
        valueColorClassName={rhoColorClassName(rho, isGlider)}
        stale={stale}
      />
      <div className="flex-1" />
    </div>
  );
}
