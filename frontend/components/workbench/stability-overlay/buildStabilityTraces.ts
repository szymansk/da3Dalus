import { cgDivergenceColor } from "./divergence-color";

/** Loose Plotly trace shape — keeps this module Plotly-import-free. */
export type PlotlyTrace = Record<string, unknown>;

export interface StabilityCtx {
  x_np_m: number | null;
  mac_m: number | null;
  cg_agg_m: number | null;
  target_static_margin: number | null;
}

// Link is rendered when |Δ| / MAC strictly exceeds this percentage threshold.
const DELTA_LINK_THRESHOLD_PCT = 1;

const COLOR_NP = "#3b82f6";        // tailwind blue-500
const COLOR_CG_SOLL = "#FF8400";   // project theme accent
const COLOR_CG_IST_FALLBACK = "#9ca3af"; // tailwind gray-400
const COLOR_SM_BAND = "#a3e635";   // tailwind lime-400

const SIZE_NP_PX = 8;
const SIZE_CG_SOLL_PX = 12;
const SIZE_CG_IST_PX = 6;

const SM_BAND_WIDTH = 4;
const DELTA_LINK_WIDTH = 2;
const CG_IST_OUTLINE_WIDTH = 2;
const CG_IST_OPACITY = 0.85;

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

function buildNpTrace(r: Resolved): PlotlyTrace {
  const macLine = r.hasMac ? `<br>MAC = ${(r.macM as number).toFixed(2)} m` : "";
  return {
    type: "scatter3d",
    mode: "markers",
    name: "NP",
    x: [r.xNp],
    y: [0],
    z: [0],
    marker: { size: SIZE_NP_PX, color: COLOR_NP, symbol: "circle" },
    hovertext: `Neutral Point<br>x = ${r.xNp.toFixed(3)} m` + macLine,
    hoverinfo: "text",
    showlegend: false,
  };
}

function buildCgSollTrace(r: Resolved): PlotlyTrace {
  const targetSmPct = ((r.targetSm as number) * 100).toFixed(1);
  return {
    type: "scatter3d",
    mode: "markers",
    name: "CG (design)",
    x: [r.xSoll as number],
    y: [0],
    z: [0],
    marker: { size: SIZE_CG_SOLL_PX, color: COLOR_CG_SOLL, symbol: "circle" },
    hovertext:
      `CG (design target)<br>x = ${(r.xSoll as number).toFixed(3)} m` +
      `<br>target SM = ${targetSmPct} % MAC`,
    hoverinfo: "text",
    showlegend: false,
  };
}

function buildSmBandTrace(r: Resolved): PlotlyTrace {
  const targetSmPct = ((r.targetSm as number) * 100).toFixed(1);
  return {
    type: "scatter3d",
    mode: "lines",
    name: "Static Margin",
    x: [r.xSoll as number, r.xNp],
    y: [0, 0],
    z: [0, 0],
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

function buildCgIstTrace(r: Resolved, color: string): PlotlyTrace {
  return {
    type: "scatter3d",
    mode: "markers",
    name: "CG (actual)",
    x: [r.xIst as number],
    y: [0],
    z: [0],
    marker: {
      size: SIZE_CG_IST_PX,
      color,
      symbol: "circle-open",
      line: { color, width: CG_IST_OUTLINE_WIDTH },
      opacity: CG_IST_OPACITY,
    },
    hovertext: buildIstHovertext(r),
    hoverinfo: "text",
    showlegend: false,
  };
}

function buildDeltaLinkTrace(r: Resolved, color: string): PlotlyTrace | null {
  if (!(r.hasSoll && r.hasMac) || r.xIst == null || r.xSoll == null) return null;
  const deltaPct = (((r.xIst as number) - (r.xSoll as number)) / (r.macM as number)) * 100;
  if (Math.abs(deltaPct) <= DELTA_LINK_THRESHOLD_PCT) return null;
  return {
    type: "scatter3d",
    mode: "lines",
    name: "Δ SOLL→IST",
    x: [r.xSoll, r.xIst as number],
    y: [0, 0],
    z: [0, 0],
    line: { color, width: DELTA_LINK_WIDTH, dash: "dash" },
    hoverinfo: "skip",
    showlegend: false,
  };
}

/**
 * Pure factory: build the Plotly scatter3d traces for the stability overlay.
 *
 * Coordinate convention: metres in, metres out (matches WingOutlineViewer's
 * coordinate frame — wing outline positions are passed through unchanged).
 *
 * Returns an empty array when there is no NP — the overlay cannot
 * meaningfully render anything without it.
 */
export function buildStabilityTraces(ctx: StabilityCtx): PlotlyTrace[] {
  const r = resolve(ctx);
  if (r == null) return [];

  const traces: PlotlyTrace[] = [buildNpTrace(r)];

  if (r.hasSoll && r.xSoll != null) {
    traces.push(buildCgSollTrace(r));
    traces.push(buildSmBandTrace(r));
  }

  if (r.xIst != null) {
    const istColor = resolveIstColor(r);
    traces.push(buildCgIstTrace(r, istColor));
    const link = buildDeltaLinkTrace(r, istColor);
    if (link != null) traces.push(link);
  }

  return traces;
}
