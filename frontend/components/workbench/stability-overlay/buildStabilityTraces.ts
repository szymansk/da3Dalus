import { cgDivergenceColor } from "./divergence-color";
import { makeIcosphere } from "./sphereGeometry";

/** Loose Plotly trace shape — keeps this module Plotly-import-free. */
export type PlotlyTrace = Record<string, unknown>;

export interface StabilityCtx {
  x_np_m: number | null;
  mac_m: number | null;
  cg_agg_m: number | null;
  target_static_margin: number | null;
}

export interface BuildStabilityTracesOpts {
  /** y-coordinate for all markers, in metres. Default 0 (centreline). */
  referenceY?: number;
  /** z-coordinate for all markers, in metres. Default 0.
   *  Pass the root LE z of the main wing so markers sit on the wing
   *  rather than floating at z=0 (relevant for high-wing aircraft). */
  referenceZ?: number;
}

// Link is rendered when |Δ| / MAC strictly exceeds this percentage threshold.
const DELTA_LINK_THRESHOLD_PCT = 1;

const COLOR_NP = "#3b82f6";        // tailwind blue-500
const COLOR_CG_SOLL = "#FF8400";   // project theme accent
const COLOR_CG_IST_FALLBACK = "#9ca3af"; // tailwind gray-400
const COLOR_SM_BAND = "#a3e635";   // tailwind lime-400

// Marker radii expressed as a fraction of MAC — markers scale with the
// aircraft size so they stay visually proportional. When MAC is unknown
// we fall back to a fixed metre radius tuned for small RC models.
const NP_RADIUS_FRAC = 0.020;       // 2.0 % of MAC
const CG_SOLL_RADIUS_FRAC = 0.035;  // 3.5 % of MAC (primary, larger)
const CG_IST_RADIUS_FRAC = 0.022;   // 2.2 % of MAC
const RADIUS_FALLBACK_M = 0.05;     // 5 cm when MAC unavailable

const SM_BAND_WIDTH = 4;
const DELTA_LINK_WIDTH = 2;
const CG_IST_OPACITY = 0.55;

function radiusFromMac(mac: number | null, frac: number): number {
  return mac != null && mac > 0 ? mac * frac : RADIUS_FALLBACK_M;
}

/** Map cgDivergenceColor's Tailwind class string to a hex for Plotly. */
function tailwindToHex(cls: string): string {
  if (cls.includes("emerald")) return "#4ade80";
  if (cls.includes("orange")) return "#fb923c";
  if (cls.includes("red")) return "#f87171";
  return COLOR_CG_IST_FALLBACK;
}

/** Resolved positional snapshot in metres + derived flags. */
interface Resolved {
  xNp: number;
  macM: number | null;
  hasMac: boolean;
  hasSoll: boolean;
  xSoll: number | null;
  xIst: number | null;
  targetSm: number | null;
}

function resolve(ctx: StabilityCtx): Resolved | null {
  if (ctx.x_np_m == null) return null;
  const xNp = ctx.x_np_m;
  const macM = ctx.mac_m;
  const hasMac = macM != null && macM > 0;
  const hasSoll = hasMac && ctx.target_static_margin != null;
  const xSoll = hasSoll ? xNp - (ctx.target_static_margin as number) * (macM as number) : null;
  return {
    xNp,
    macM: hasMac ? (macM as number) : null,
    hasMac,
    hasSoll,
    xSoll,
    xIst: ctx.cg_agg_m,
    targetSm: ctx.target_static_margin,
  };
}

function buildNpTrace(r: Resolved, refY: number, refZ: number): PlotlyTrace {
  const macLine = r.hasMac ? `<br>MAC = ${(r.macM as number).toFixed(2)} m` : "";
  const sphere = makeIcosphere(r.xNp, refY, refZ, radiusFromMac(r.macM, NP_RADIUS_FRAC));
  return {
    type: "mesh3d",
    name: "NP",
    x: sphere.x,
    y: sphere.y,
    z: sphere.z,
    i: sphere.i,
    j: sphere.j,
    k: sphere.k,
    color: COLOR_NP,
    flatshading: true,
    hovertext: `Neutral Point<br>x = ${r.xNp.toFixed(3)} m` + macLine,
    hoverinfo: "text",
    showlegend: false,
  };
}

function buildCgSollTrace(r: Resolved, refY: number, refZ: number): PlotlyTrace {
  const targetSmPct = ((r.targetSm as number) * 100).toFixed(1);
  const sphere = makeIcosphere(
    r.xSoll as number,
    refY,
    refZ,
    radiusFromMac(r.macM, CG_SOLL_RADIUS_FRAC),
  );
  return {
    type: "mesh3d",
    name: "CG (design)",
    x: sphere.x,
    y: sphere.y,
    z: sphere.z,
    i: sphere.i,
    j: sphere.j,
    k: sphere.k,
    color: COLOR_CG_SOLL,
    flatshading: true,
    hovertext:
      `CG (design target)<br>x = ${(r.xSoll as number).toFixed(3)} m` +
      `<br>target SM = ${targetSmPct} % MAC`,
    hoverinfo: "text",
    showlegend: false,
  };
}

function buildSmBandTrace(r: Resolved, refY: number, refZ: number): PlotlyTrace {
  const targetSmPct = ((r.targetSm as number) * 100).toFixed(1);
  return {
    type: "scatter3d",
    mode: "lines",
    name: "Static Margin",
    x: [r.xSoll as number, r.xNp],
    y: [refY, refY],
    z: [refZ, refZ],
    line: { color: COLOR_SM_BAND, width: SM_BAND_WIDTH },
    hovertext: `Target Static Margin = ${targetSmPct} % MAC`,
    hoverinfo: "text",
    showlegend: false,
  };
}

function resolveIstColor(r: Resolved): string {
  if (!(r.hasSoll && r.hasMac)) return COLOR_CG_IST_FALLBACK;
  return tailwindToHex(
    cgDivergenceColor(r.xSoll as number, r.xIst as number, r.macM as number),
  );
}

function buildIstHovertext(r: Resolved): string {
  const lines = [`CG (component aggregate)`, `x = ${(r.xIst as number).toFixed(3)} m`];
  if (r.hasMac) {
    const resultingSmPct = ((r.xNp - (r.xIst as number)) / (r.macM as number)) * 100;
    lines.push(`resulting SM = ${resultingSmPct.toFixed(1)} % MAC`);
  }
  if (r.hasSoll && r.hasMac) {
    const deltaPct = (((r.xIst as number) - (r.xSoll as number)) / (r.macM as number)) * 100;
    const sign = deltaPct >= 0 ? "+" : "";
    lines.push(`Δ to target = ${sign}${deltaPct.toFixed(1)} % MAC`);
  }
  return lines.join("<br>");
}

function buildCgIstTrace(r: Resolved, color: string, refY: number, refZ: number): PlotlyTrace {
  const sphere = makeIcosphere(
    r.xIst as number,
    refY,
    refZ,
    radiusFromMac(r.macM, CG_IST_RADIUS_FRAC),
  );
  return {
    type: "mesh3d",
    name: "CG (actual)",
    x: sphere.x,
    y: sphere.y,
    z: sphere.z,
    i: sphere.i,
    j: sphere.j,
    k: sphere.k,
    color,
    flatshading: true,
    opacity: CG_IST_OPACITY,
    hovertext: buildIstHovertext(r),
    hoverinfo: "text",
    showlegend: false,
  };
}

function buildDeltaLinkTrace(
  r: Resolved,
  color: string,
  refY: number,
  refZ: number,
): PlotlyTrace | null {
  if (!(r.hasSoll && r.hasMac) || r.xIst == null || r.xSoll == null) return null;
  const deltaPct = (((r.xIst as number) - (r.xSoll as number)) / (r.macM as number)) * 100;
  if (Math.abs(deltaPct) <= DELTA_LINK_THRESHOLD_PCT) return null;
  return {
    type: "scatter3d",
    mode: "lines",
    name: "Δ SOLL→IST",
    x: [r.xSoll, r.xIst as number],
    y: [refY, refY],
    z: [refZ, refZ],
    line: { color, width: DELTA_LINK_WIDTH, dash: "dash" },
    hoverinfo: "skip",
    showlegend: false,
  };
}

/**
 * Pure factory: build the Plotly traces for the stability overlay.
 *
 * Markers (NP / CG SOLL / CG IST) are `mesh3d` icospheres sized in world
 * units (as a fraction of MAC) so they scale naturally with zoom. Lines
 * (SM band, delta link) are `scatter3d` line traces — their pixel
 * line-width is unaffected by overlap.
 *
 * Coordinate convention: metres in, metres out (matches WingOutlineViewer's
 * coordinate frame — wing outline positions are passed through unchanged).
 *
 * Returns an empty array when there is no NP — the overlay cannot
 * meaningfully render anything without it.
 */
export function buildStabilityTraces(
  ctx: StabilityCtx,
  opts?: BuildStabilityTracesOpts,
): PlotlyTrace[] {
  const r = resolve(ctx);
  if (r == null) return [];

  const refY = opts?.referenceY ?? 0;
  const refZ = opts?.referenceZ ?? 0;

  const traces: PlotlyTrace[] = [buildNpTrace(r, refY, refZ)];

  if (r.hasSoll && r.xSoll != null) {
    traces.push(buildCgSollTrace(r, refY, refZ));
    traces.push(buildSmBandTrace(r, refY, refZ));
  }

  if (r.xIst != null) {
    const istColor = resolveIstColor(r);
    traces.push(buildCgIstTrace(r, istColor, refY, refZ));
    const link = buildDeltaLinkTrace(r, istColor, refY, refZ);
    if (link != null) traces.push(link);
  }

  return traces;
}
