/**
 * Pure adapter functions that map hook result types (ComputationContext,
 * TailSizingResult, EnduranceData) to the MetricsDashboard data shapes
 * (SpeedData, BalanceData, GaugeData[], MetricItem[]).
 *
 * No React, no SWR — these are deterministic transforms that can be tested
 * without a DOM. The gauge zone thresholds reuse the same values defined in
 * metricsMock.ts so the visual appearance stays identical after live wiring.
 */

import type { ComputationContext } from "@/hooks/useComputationContext";
import type { TailSizingResult, TailClassification } from "@/hooks/useTailSizing";
import type { EnduranceData } from "@/hooks/useEndurance";
import type {
  SpeedData,
  SpeedMarker,
  BalanceData,
  GaugeData,
  GaugeZone,
  MetricItem,
  Quality,
} from "@/components/workbench/metrics-dashboard/metricsTypes";
import {
  computeK,
  computeCLmd,
  computeEMax,
  computeRho,
  rhoThresholdsForProfile,
} from "@/lib/polar";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(v: number | null | undefined, dp: number): string {
  if (v == null || !Number.isFinite(v)) return "–";
  return v.toFixed(dp);
}

function fmtRe(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "–";
  return v.toExponential(1);
}

/** Determine which GaugeZone contains value and return its Quality. */
function zoneQuality(value: number, zones: readonly GaugeZone[]): Quality {
  for (const z of zones) {
    if (value >= z.from && value <= z.to) return z.quality;
  }
  // Clamp to nearest boundary
  if (value < zones[0].from) return zones[0].quality;
  return zones[zones.length - 1].quality;
}

// ---------------------------------------------------------------------------
// toSpeedData
// ---------------------------------------------------------------------------

/**
 * Map a ComputationContext to the SpeedData shape consumed by EnvelopeAxis.
 * Returns null when ctx is absent (loading / error state).
 */
export function toSpeedData(
  ctx: ComputationContext | null | undefined,
): SpeedData | null {
  if (ctx == null) return null;

  const isGlider = !!ctx.is_glider;

  // Build the ordered list of (symbol, value, kind, alpha?) tuples.
  // Null speeds are dropped — the axis only renders markers with real values.
  const candidates: Array<{
    symbol: string;
    label: string;
    value: number | null | undefined;
    kind: SpeedMarker["kind"];
    alpha?: number | null;
    gliderOnly?: boolean; // if true, include even for gliders
    powered?: boolean; // if true, hide for gliders
  }> = [
    { symbol: "V_stall", label: "Stall", value: ctx.v_stall_mps, kind: "stall", alpha: ctx.alpha_stall_deg },
    { symbol: "V_min_sink", label: "Min sink", value: ctx.v_min_sink_mps, kind: "normal", alpha: ctx.alpha_min_sink_deg },
    { symbol: "V_md", label: "Min drag (L/D)", value: ctx.v_md_mps, kind: "normal", alpha: ctx.alpha_best_glide_deg },
    { symbol: "V_cruise", label: "Cruise", value: ctx.v_cruise_mps, kind: "normal" },
    { symbol: "V_x", label: "Best climb angle", value: ctx.v_x_mps, kind: "normal", powered: true },
    { symbol: "V_y", label: "Best climb rate", value: ctx.v_y_mps, kind: "normal", powered: true },
    { symbol: "V_a", label: "Manoeuvring", value: ctx.v_a_mps, kind: "caution", powered: true },
    { symbol: "V_max", label: "Max operating", value: ctx.v_max_mps, kind: "caution", powered: true },
    { symbol: "V_dive", label: "Never exceed", value: ctx.v_dive_mps, kind: "ne", powered: true },
  ];

  const markers: SpeedMarker[] = [];
  for (const c of candidates) {
    if (c.powered && isGlider) continue;
    if (c.value == null || !Number.isFinite(c.value)) continue;
    const m: SpeedMarker = {
      symbol: c.symbol,
      label: c.label,
      value: c.value,
      kind: c.kind,
    };
    if (c.alpha != null && Number.isFinite(c.alpha)) {
      (m as { aoa?: number }).aoa = c.alpha;
    }
    markers.push(m as SpeedMarker);
  }

  return {
    markers,
    wMin: ctx.min_sink_rate_mps != null && Number.isFinite(ctx.min_sink_rate_mps)
      ? ctx.min_sink_rate_mps
      : 0,
    isGlider,
  };
}

// ---------------------------------------------------------------------------
// toGeometryItems
// ---------------------------------------------------------------------------

/**
 * Map ctx geometry fields to the compact MetricItem[] used in the Geometry
 * column tile and the geometryMock shape.
 */
export function toGeometryItems(
  ctx: ComputationContext | null | undefined,
): MetricItem[] {
  if (ctx == null) return [];

  const result: MetricItem[] = [];

  if (ctx.s_ref_m2 != null) {
    result.push({
      symbol: "S_ref",
      label: "Reference area",
      value: ctx.s_ref_m2.toFixed(3),
      unit: "m²",
      description: "Wing reference area.",
    });
  }

  // MAC is always present (required field on ComputationContext)
  result.push({
    symbol: "MAC",
    label: "Mean aero chord",
    value: ctx.mac_m.toFixed(3),
    unit: "m",
    description: "Reference chord for pitching moment.",
  });

  if (ctx.b_ref_m != null) {
    result.push({
      symbol: "B_ref",
      label: "Reference span",
      value: ctx.b_ref_m.toFixed(3),
      unit: "m",
      description: "Wing span.",
    });
  }

  if (ctx.aspect_ratio != null) {
    result.push({
      symbol: "AR",
      label: "Aspect ratio",
      value: ctx.aspect_ratio.toFixed(1),
      description: "Span² / area — higher ⇒ less induced drag.",
    });
  }

  return result;
}

// ---------------------------------------------------------------------------
// toBalanceData
// ---------------------------------------------------------------------------

/**
 * Map ctx stability fields to the BalanceData shape consumed by MacCgDiagram /
 * PlanformDiagram. Returns null when cg_agg_m is absent (design not balanced).
 *
 * @param cgComponent optional component-derived CG from the tree (metres)
 */
export function toBalanceData(
  ctx: ComputationContext | null | undefined,
  cgComponent?: number,
): BalanceData | null {
  if (ctx == null) return null;
  if (ctx.cg_agg_m == null) return null;

  const cg = ctx.cg_agg_m;
  const np = ctx.x_np_m;
  const mac = ctx.mac_m;
  const smPercent = ((np - cg) / mac) * 100;

  // Build a target SM range centred on target_static_margin.
  // target_static_margin is a dimensionless fraction (e.g. 0.081 = 8.1%).
  // We show a ±4% window around the target value (matches the "5–15%" defaults
  // in metricsMock for a ~10% target).
  const targetPct = ctx.target_static_margin * 100;
  const halfBand = 4.0;
  const targetSmMin = Math.max(0, targetPct - halfBand);
  const targetSmMax = targetPct + halfBand;

  // macStart: place MAC so that cg_agg_m is at smPercent along it.
  // We know: (np - cg) / mac = smPercent/100 → already consistent.
  // The MAC leading-edge position: macStart = cg - (smPercent/100 - SM_LE_fraction)*mac.
  // We don't have the LE fraction from the API, so use a reasonable approximation:
  // place the CG at 30% of MAC from the LE, consistent with typical aircraft.
  const cgFracInMac = 0.30;
  const macStart = cg - cgFracInMac * mac;

  return {
    cg,
    np,
    macStart,
    macLength: mac,
    smPercent,
    targetSmMin,
    targetSmMax,
    cgComponent,
  };
}

// ---------------------------------------------------------------------------
// toQualityGauges
// ---------------------------------------------------------------------------

// Fixed gauge zone definitions — mirrors metricsMock.ts exactly so the
// visual thresholds stay consistent when mock data is swapped for real data.

const LD_MAX_ZONES: readonly GaugeZone[] = [
  { from: 5, to: 12, quality: "bad" },
  { from: 12, to: 18, quality: "caution" },
  { from: 18, to: 35, quality: "good" },
];
const LD_MAX_MIN = 5;
const LD_MAX_MAX = 35;

const E_ZONES: readonly GaugeZone[] = [
  { from: 0.5, to: 0.7, quality: "bad" },
  { from: 0.7, to: 0.78, quality: "caution" },
  { from: 0.78, to: 0.95, quality: "good" },
  { from: 0.95, to: 1.0, quality: "caution" },
];
const E_MIN = 0.5;
const E_MAX = 1.0;

const RHO_MIN = 0;
const RHO_MAX = 1;

/** Build ρ gauge zones that mirror rhoThresholdsForProfile / rhoColorClassName. */
function buildRhoZones(isGlider: boolean): readonly GaugeZone[] {
  const { amber } = rhoThresholdsForProfile(isGlider);
  // Lower ρ is better (ρ→0 means plenty of lift margin at best-glide speed).
  // Colour mapping mirrors rhoColorClassName: [0, amber) → good, [amber, 1] → caution.
  // ρ ≥ 1 is physically degenerate (V_md = V_stall) — treat the [1.0, 1.0] edge as bad,
  // but since we clamp to [RHO_MIN, RHO_MAX=1] this appears at the very top of the gauge.
  return [
    { from: RHO_MIN, to: amber, quality: "good" },
    { from: amber, to: RHO_MAX, quality: "caution" },
  ];
}

const SM_ZONES: readonly GaugeZone[] = [
  { from: -5, to: 3, quality: "bad" },
  { from: 3, to: 5, quality: "caution" },
  { from: 5, to: 15, quality: "good" },
  { from: 15, to: 20, quality: "caution" },
  { from: 20, to: 25, quality: "bad" },
];
const SM_MIN = -5;
const SM_MAX = 25;

const L_LAND_ZONES: readonly GaugeZone[] = [
  { from: 0, to: 35, quality: "good" },
  { from: 35, to: 60, quality: "bad" },
];
const L_LAND_MIN = 0;
const L_LAND_MAX = 60;

const P_MARGIN_ZONES: readonly GaugeZone[] = [
  { from: -0.3, to: 0, quality: "bad" },
  { from: 0, to: 0.2, quality: "caution" },
  { from: 0.2, to: 0.6, quality: "good" },
];
const P_MARGIN_MIN = -0.3;
const P_MARGIN_MAX = 0.6;

/**
 * Build the array of GaugeData for the Quality column.
 * The sentinel value 0 is used when a polar-derived quantity is suppressed
 * (fallback used) so BulletGauge still renders but shows the bar at min
 * rather than a garbage value.
 */
export function toQualityGauges(
  ctx: ComputationContext | null | undefined,
): GaugeData[] {
  if (ctx == null) return [];

  const fallbackUsed = !!ctx.e_oswald_fallback_used;
  const ar = ctx.aspect_ratio ?? null;
  const cd0 = ctx.cd0 ?? null;
  const eFromCtx = ctx.e_oswald ?? null;
  const cleanPolar = ctx.polar_by_config?.clean ?? null;
  const clMax = cleanPolar?.cl_max ?? null;

  // Empirical (L/D)max from backend sweep takes priority; formula is fallback.
  const ldMaxRaw = cleanPolar?.ld_max ?? computeEMax(cd0, eFromCtx, fallbackUsed, ar);

  // ρ: stall-margin degeneracy ratio (lower is better)
  const rhoRaw = computeRho(cd0, eFromCtx, fallbackUsed, ar, clMax);

  // SM from ctx
  const smPercent = ctx.cg_agg_m != null
    ? ((ctx.x_np_m - ctx.cg_agg_m) / ctx.mac_m) * 100
    : null;

  const isGlider = !!ctx.is_glider;
  const rhoZones = buildRhoZones(isGlider);

  const gauges: GaugeData[] = [];

  // (L/D)_max — omitted when the polar fit was rejected (fallback) or unavailable;
  // the raw row dashes the underlying numbers rather than showing a bogus 0.0.
  if (!fallbackUsed && ldMaxRaw != null) {
    gauges.push({
      symbol: "(L/D)_max",
      label: "Max glide ratio",
      value: ldMaxRaw,
      min: LD_MAX_MIN,
      max: LD_MAX_MAX,
      zones: LD_MAX_ZONES,
      quality: zoneQuality(ldMaxRaw, LD_MAX_ZONES),
      description: "Best lift-to-drag ratio — the headline efficiency number.",
      format: (v) => v.toFixed(1),
    });
  }

  // e (Oswald efficiency)
  if (eFromCtx != null) {
    const eVal = Math.min(Math.max(eFromCtx, E_MIN), E_MAX);
    gauges.push({
      symbol: "e",
      label: "Oswald efficiency",
      value: eVal,
      min: E_MIN,
      max: E_MAX,
      zones: E_ZONES,
      quality: zoneQuality(eVal, E_ZONES),
      description: "Span efficiency factor from the Trefftz-plane analysis.",
      format: (v) => v.toFixed(2),
    });
  }

  // ρ (polar health) — degeneracy ratio; omitted on fallback like (L/D)_max.
  // Zones derive from rhoThresholdsForProfile so the colouring matches PolarChipRow
  // / rhoColorClassName for both powered and glider profiles.
  if (!fallbackUsed && rhoRaw != null) {
    gauges.push({
      symbol: "ρ",
      label: "Polar health",
      value: rhoRaw,
      min: RHO_MIN,
      max: RHO_MAX,
      zones: rhoZones,
      quality: zoneQuality(Math.max(rhoRaw, RHO_MIN), rhoZones),
      description:
        "ρ = C_D0·π·e·AR / C_L,max² — stall-margin degeneracy (Anderson §6.7.2). Lower is better: ρ=1/3 ⇔ min-sink at stall, ρ=1 ⇔ best glide at stall.",
      format: (v) => v.toFixed(2),
    });
  }

  // SM
  if (smPercent != null) {
    const smClamped = Math.min(Math.max(smPercent, SM_MIN), SM_MAX);
    gauges.push({
      symbol: "SM",
      label: "Static margin",
      value: smClamped,
      min: SM_MIN,
      max: SM_MAX,
      zones: SM_ZONES,
      quality: zoneQuality(smClamped, SM_ZONES),
      description:
        "Longitudinal stability margin as % of MAC — too low is unstable, too high is sluggish.",
      format: (v) => `${v.toFixed(1)}%`,
    });
  }

  // L_land (optional)
  if (ctx.landing_field_length_m != null) {
    const l = ctx.landing_field_length_m;
    const lClamped = Math.min(Math.max(l, L_LAND_MIN), L_LAND_MAX);
    const sufficient = ctx.landing_field_sufficient;
    // Quality derives from the real sufficiency flag when present; fall back to
    // the threshold-based zone only when the flag is absent (null / undefined).
    let lQuality: Quality;
    if (sufficient === true) {
      lQuality = "good";
    } else if (sufficient === false) {
      lQuality = "bad";
    } else {
      lQuality = zoneQuality(lClamped, L_LAND_ZONES);
    }
    const formatFn = (v: number): string => {
      if (sufficient === true) return `${v.toFixed(0)} m ✓`;
      if (sufficient === false) return `${v.toFixed(0)} m ✗`;
      return `${v.toFixed(0)} m`;
    };
    gauges.push({
      symbol: "L_land",
      label: "Landing field",
      value: lClamped,
      min: L_LAND_MIN,
      max: L_LAND_MAX,
      zones: L_LAND_ZONES,
      quality: lQuality,
      description: "Required landing field length — ✓/✗ when available field length is known.",
      format: formatFn,
    });
  }

  // P_margin (from endurance hook — not on ctx, so handled in toPowertrainItems)
  // We include it here if p_margin is somehow surfaced via the context.
  // Currently it lives in EnduranceData, not ComputationContext. The gauge
  // is therefore added by wiring code after calling both adapters. Keeping
  // it out here is correct.

  return gauges;
}

// ---------------------------------------------------------------------------
// toQualityRaw
// ---------------------------------------------------------------------------

/**
 * Build the "raw polar numbers" MetricItem[] shown inline in the Quality
 * column's large view (Re, C_D0, k, C_L_max, C_L_md).
 */
export function toQualityRaw(
  ctx: ComputationContext | null | undefined,
): MetricItem[] {
  if (ctx == null) return [];

  const fallbackUsed = !!ctx.e_oswald_fallback_used;
  const ar = ctx.aspect_ratio ?? null;
  const cd0 = ctx.cd0 ?? null;
  const eFromCtx = ctx.e_oswald ?? null;
  const cleanPolar = ctx.polar_by_config?.clean ?? null;
  const clMax = cleanPolar?.cl_max ?? null;

  const k = computeK(eFromCtx, fallbackUsed, ar);
  // Prefer empirical C_L_md from backend over formula
  const clMdBackend = cleanPolar?.cl_at_ld_max ?? null;
  const clMd = clMdBackend ?? computeCLmd(cd0, eFromCtx, fallbackUsed, ar);

  return [
    {
      symbol: "Re",
      label: "Reynolds (cruise)",
      value: fmtRe(ctx.reynolds),
      description: "MAC-based Reynolds number at cruise.",
    },
    {
      symbol: "C_D0",
      label: "Zero-lift drag",
      value: fmt(cd0, 4),
      description: "Parasite drag coefficient.",
    },
    {
      symbol: "k",
      label: "Induced factor",
      value: fmt(k, 4),
      description: "k = 1/(π·e·AR).",
    },
    {
      symbol: "C_L_max",
      label: "Max lift",
      value: fmt(clMax, 2),
      description: "Max lift coefficient (AeroBuildup).",
    },
    {
      symbol: "C_L_md",
      label: "C_L best glide",
      value: fmt(clMd, 2),
      description: "Lift coefficient at best L/D.",
    },
  ];
}

// ---------------------------------------------------------------------------
// Tail result shape
// ---------------------------------------------------------------------------

export interface TailAdapterResult {
  readonly gauge: GaugeData;
  readonly items: readonly MetricItem[];
  readonly mission: string;
  readonly bandsNote: string;
}

// Classification → Quality mapping
function classificationToQuality(c: TailClassification): Quality {
  switch (c) {
    case "in_range":
      return "good";
    case "below_range":
    case "above_range":
      return "bad";
    case "out_of_physical_range":
      return "bad";
    case "not_applicable":
    default:
      return "caution";
  }
}

/**
 * Build the TailAdapterResult for the Geometry column's tail panel.
 * Returns null when:
 *   - tailSizing is absent (loading)
 *   - classification is "not_applicable" (tailless aircraft)
 *   - v_h_current is null (no geometry yet)
 */
export function toTail(
  tailSizing: TailSizingResult | null | undefined,
  _ctx?: ComputationContext | null,
): TailAdapterResult | null {
  if (tailSizing == null) return null;
  if (tailSizing.classification === "not_applicable") return null;
  if (tailSizing.v_h_current == null) return null;

  const vhMin = tailSizing.v_h_target_min ?? 0.4;
  const vhMax = tailSizing.v_h_target_max ?? 0.7;

  // Build zones from target band:
  //   [0.3, vhMin): caution (too low)
  //   [vhMin, vhMax]: good (in range)
  //   (vhMax, 0.8]: caution (too high — oversized tail is sluggish)
  const GAUGE_MIN = 0.3;
  const GAUGE_MAX = 0.8;

  const zones: GaugeZone[] = [];
  if (vhMin > GAUGE_MIN) {
    zones.push({ from: GAUGE_MIN, to: vhMin, quality: "bad" });
  }
  zones.push({ from: vhMin, to: vhMax, quality: "good" });
  if (vhMax < GAUGE_MAX) {
    zones.push({ from: vhMax, to: GAUGE_MAX, quality: "caution" });
  }

  const vhVal = tailSizing.v_h_current;
  const quality = classificationToQuality(tailSizing.classification_h);

  const gauge: GaugeData = {
    symbol: "V_H",
    label: "H-tail volume coef.",
    value: vhVal,
    min: GAUGE_MIN,
    max: GAUGE_MAX,
    zones,
    quality,
    description: `V_H = S_HT·l_HT/(S_W·MAC). Band shown for ${tailSizing.aircraft_class_used} (${vhMin.toFixed(2)}–${vhMax.toFixed(2)}). ${tailSizing.v_h_citation}.`,
    format: (v) => v.toFixed(2),
  };

  // Supplementary items: tail moment arm and V_V
  const items: MetricItem[] = [];

  if (tailSizing.l_h_m != null) {
    items.push({
      symbol: "l_HT",
      label: "Tail moment arm",
      value: tailSizing.l_h_m.toFixed(2),
      unit: "m",
      description: "Wing AC → tail AC distance.",
    });
  }

  if (tailSizing.v_v_current != null) {
    items.push({
      symbol: "V_V",
      label: "V-tail volume coef.",
      value: tailSizing.v_v_current.toFixed(3),
      description: `V_V = S_VT·l_VT/(S_W·b). ${tailSizing.v_v_citation}.`,
    });
  }

  const bandsNote =
    "V_H target band depends on aircraft type: trainer 0.60–0.70, sport 0.50–0.60, aerobatic 0.45–0.55, glider ~0.45–0.60. RC rule of thumb (rcplanedesigner / Lennon) — defer to Scholz for UAV / full-scale.";

  return {
    gauge,
    items,
    mission: tailSizing.aircraft_class_used,
    bandsNote,
  };
}

// ---------------------------------------------------------------------------
// Powertrain detail shape
// ---------------------------------------------------------------------------

export interface PowertrainDetail {
  readonly pReqVmd: number | null;
  readonly pReqVminSink: number | null;
  readonly pMarginClass: string | null;
  readonly batteryMassPredicted: number | null;
  readonly confidence: "computed" | "estimated";
}

export interface PowertrainAdapterResult {
  readonly items: readonly MetricItem[];
  readonly detail: PowertrainDetail;
}

/**
 * Map EnduranceData to the Powertrain column data shapes.
 */
export function toPowertrainItems(
  endurance: EnduranceData | null | undefined,
): PowertrainAdapterResult {
  if (endurance == null) {
    return {
      items: [],
      detail: {
        pReqVmd: null,
        pReqVminSink: null,
        pMarginClass: null,
        batteryMassPredicted: null,
        confidence: "estimated",
      },
    };
  }

  const enduranceMin =
    endurance.t_endurance_max_s != null
      ? Math.round(endurance.t_endurance_max_s / 60)
      : null;

  const rangeKm =
    endurance.range_max_m != null
      ? Math.round(endurance.range_max_m / 1000)
      : null;

  const items: MetricItem[] = [
    {
      symbol: "Endurance",
      label: "Endurance (min-sink)",
      value: enduranceMin != null ? String(enduranceMin) : "–",
      unit: "min",
      description: "Max endurance at V_min_sink.",
    },
    {
      symbol: "Range",
      label: "Range (V_md)",
      value: rangeKm != null ? String(rangeKm) : "–",
      unit: "km",
      description: "Max range at min-drag speed.",
    },
  ];

  return {
    items,
    detail: {
      pReqVmd: endurance.p_req_at_v_md_w,
      pReqVminSink: endurance.p_req_at_v_min_sink_w,
      pMarginClass: endurance.p_margin_class,
      batteryMassPredicted: endurance.battery_mass_g_predicted,
      confidence: endurance.confidence,
    },
  };
}

/**
 * Build the P_margin GaugeData from an EnduranceData payload.
 * Returned as a standalone gauge so the caller can append it to toQualityGauges().
 * Returns null when p_margin is absent.
 */
export function toPMarginGauge(
  endurance: EnduranceData | null | undefined,
): GaugeData | null {
  if (endurance == null || endurance.p_margin == null) return null;
  const v = Math.min(Math.max(endurance.p_margin, P_MARGIN_MIN), P_MARGIN_MAX);
  return {
    symbol: "P_margin",
    label: "Motor reserve",
    value: v,
    min: P_MARGIN_MIN,
    max: P_MARGIN_MAX,
    zones: P_MARGIN_ZONES,
    quality: zoneQuality(v, P_MARGIN_ZONES),
    description: "(P_motor − P_req@V_md) / P_motor — 'feasible but tight'.",
    format: (val) => `${(val * 100).toFixed(0)}%`,
  };
}
