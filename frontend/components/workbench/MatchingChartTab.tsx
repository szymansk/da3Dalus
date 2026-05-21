"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, AlertTriangle, Info, X } from "lucide-react";
import {
  useMatchingChart,
  type AircraftMode,
  type MatchingChartData,
  type ConstraintLine,
} from "@/hooks/useMatchingChart";
import { useDesignAssumptions } from "@/hooks/useDesignAssumptions";
import { useComputationContext } from "@/hooks/useComputationContext";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  readonly aeroplaneId: string;
}

interface DragPoint {
  ws_n_m2: number;
  t_w: number;
}

interface CurrentDesignPoint {
  readonly ws_n_m2: number;
  readonly t_w: number;
  readonly mass_kg: number;
  readonly s_m2: number;
  readonly t_n: number;
  readonly w_n: number;
  readonly ar: number | null;
}

const G_MPS2 = 9.80665;

// ---------------------------------------------------------------------------
// Mode labels
// ---------------------------------------------------------------------------

const MODE_LABELS: Record<AircraftMode, string> = {
  rc_runway: "RC Runway",
  rc_hand_launch: "RC Hand Launch",
  uav_runway: "UAV Runway",
  uav_belly_land: "UAV Belly Land",
};

const MODE_DEFAULTS: Record<AircraftMode, { sRunway: number; vSTarget: number; gamma: number }> = {
  rc_runway: { sRunway: 50, vSTarget: 7, gamma: 5 },
  rc_hand_launch: { sRunway: 0, vSTarget: 7, gamma: 5 },
  uav_runway: { sRunway: 200, vSTarget: 12, gamma: 4 },
  uav_belly_land: { sRunway: 200, vSTarget: 12, gamma: 4 },
};

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/** Format a number to N significant figures.
 *
 * gh-606: per Scholz review (minor finding), the T value in the readout
 * panel should be 3 sig figs, not toFixed(1). Examples: 123.456 → "123",
 * 1234.56 → "1.23e+3", 0.01234 → "0.0123". Exported for unit testing.
 */
export function formatSigFigs(value: number, sigFigs: number): string {
  if (!isFinite(value)) return "—";
  if (value === 0) return "0";
  return value.toPrecision(sigFigs);
}

// ---------------------------------------------------------------------------
// Plotly trace / shape builders (extracted to reduce function nesting depth)
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyTrace = Record<string, any>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyShape = Record<string, any>;

function buildHullFill(ws: number[], data: MatchingChartData): PlotlyTrace {
  const hullY = ws.map((_, i) => {
    let maxTw = 0;
    for (const c of data.constraints) {
      if (c.t_w_points) maxTw = Math.max(maxTw, c.t_w_points[i]);
    }
    return maxTw;
  });
  return {
    x: [...ws, ...ws.slice().reverse()],
    y: [...hullY, ...ws.map(() => 0)],
    fill: "toself",
    fillcolor: "rgba(231,70,58,0.08)",
    line: { color: "transparent" },
    type: "scatter",
    mode: "none",
    showlegend: false,
    hoverinfo: "skip",
    name: "infeasible region",
  };
}

function buildDesignPointTrace(
  ws_n_m2: number,
  t_w: number,
  feasibility: string,
  isDragging: boolean,
): PlotlyTrace {
  const dpColor = feasibility === "feasible" ? "#30A46C" : "#E5484D";
  return {
    x: [ws_n_m2],
    y: [t_w],
    type: "scatter",
    mode: "markers",
    name: "Design Point",
    marker: {
      symbol: "circle",
      size: isDragging ? 14 : 12,
      color: dpColor,
      line: { color: isDragging ? "#FF8400" : "#fff", width: isDragging ? 3 : 2 },
    },
    hovertemplate: (
      `<b>Design Point</b><br>W/S = ${ws_n_m2.toFixed(0)} N/m²<br>` +
      `T/W = ${t_w.toFixed(4)}<br><i>y-axis: T_TO/W_TO (RC airframes: t_static_N proxy)</i><extra></extra>`
    ),
  };
}

/** Build the static current-design-point marker trace.
 *
 * gh-606: this is a separate trace from the (existing, draggable) "Design
 * Point" — it visualises where the current aircraft (mass, s_ref, t_static)
 * actually sits on the chart. Colour: teal (`#22dd99`) to distinguish from
 * the orange explored point. Symbol: filled diamond.
 *
 * Tooltip labels W explicitly as `m_MTO·g` (per Scholz review substantive
 * finding) and T as the user's *assumed* static thrust (RC proxy for
 * T_TO at sea level). Exported for unit testing.
 */
export function buildCurrentDesignPointTrace(cdp: CurrentDesignPoint): PlotlyTrace {
  const arStr = cdp.ar != null ? cdp.ar.toFixed(2) : "—";
  return {
    x: [cdp.ws_n_m2],
    y: [cdp.t_w],
    type: "scatter",
    mode: "markers",
    name: "Current Design Point",
    marker: {
      symbol: "diamond",
      size: 12,
      color: "#22dd99",
      line: { color: "#0a0a0a", width: 1.5 },
    },
    hovertemplate: (
      `<b>Current Design Point</b><br>` +
      `W/S = ${cdp.ws_n_m2.toFixed(1)} N/m²<br>` +
      `T/W = ${cdp.t_w.toFixed(3)}<br>` +
      `S = ${cdp.s_m2.toFixed(2)} m²<br>` +
      `T = ${formatSigFigs(cdp.t_n, 3)} N (your assumed static thrust)<br>` +
      `W = m_MTO·g = ${cdp.w_n.toFixed(1)} N<br>` +
      `AR = ${arStr}` +
      `<extra></extra>`
    ),
  };
}

function buildConstraintTraces(
  ws: number[],
  data: MatchingChartData,
  dragBindingName: string | null,
): { traces: PlotlyTrace[]; shapes: PlotlyShape[] } {
  const traces: PlotlyTrace[] = [];
  const shapes: PlotlyShape[] = [];
  const dp = data.design_point;

  const yMax =
    Math.max(
      ...data.constraints.flatMap((c) => c.t_w_points?.filter((v) => isFinite(v)) ?? []),
      dp.t_w * 2,
    ) * 1.1;

  for (const c of data.constraints) {
    // During drag: highlight constraint that would bind at drag position
    const isBinding = dragBindingName !== null ? c.name === dragBindingName : c.binding;
    const lineWidth = isBinding ? 3 : 1.5;
    const dash = isBinding ? "solid" : "dot";

    if (c.t_w_points) {
      traces.push({
        x: ws,
        y: c.t_w_points,
        type: "scatter",
        mode: "lines",
        name: c.name,
        line: { color: c.color, width: lineWidth, dash },
        hovertemplate: (
          `<b>${c.name}</b><br>W/S: %{x:.0f} N/m²<br>T/W_min: %{y:.4f}` +
          `<br><i>${c.hover_text ?? ""}</i><extra></extra>`
        ),
      });
    } else if (c.ws_max != null) {
      shapes.push({
        type: "line",
        x0: c.ws_max, x1: c.ws_max, y0: 0, y1: yMax,
        line: { color: c.color, width: lineWidth, dash },
      });
      traces.push({
        x: [c.ws_max, c.ws_max],
        y: [0, yMax],
        type: "scatter",
        mode: "lines",
        name: c.name,
        line: { color: c.color, width: lineWidth, dash },
        hovertemplate: (
          `<b>${c.name}</b><br>W/S_max: ${c.ws_max.toFixed(0)} N/m²` +
          `<br><i>${c.hover_text ?? ""}</i><extra></extra>`
        ),
        showlegend: true,
      });
    }
  }

  return { traces, shapes };
}

function buildLayout(
  ws: number[],
  data: MatchingChartData,
  displayDp: DragPoint,
  isDragging: boolean,
) {
  const dpColor = data.feasibility === "feasible" ? "#30A46C" : "#E5484D";
  const allTw = data.constraints.flatMap((c) => c.t_w_points?.filter((v) => isFinite(v)) ?? []);
  const yMax = allTw.length > 0 ? Math.max(...allTw, displayDp.t_w) * 1.15 : displayDp.t_w * 2;

  return {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
    margin: { l: 55, r: 15, t: 30, b: 50 },
    xaxis: {
      title: { text: "W/S [N/m²]", font: { size: 11 } },
      gridcolor: "#27272A",
      zerolinecolor: "#3F3F46",
      range: [0, Math.max(...ws) * 1.02],
    },
    yaxis: {
      title: { text: "T/W [-]", font: { size: 11 } },
      gridcolor: "#27272A",
      zerolinecolor: "#3F3F46",
      range: [0, yMax],
    },
    legend: {
      x: 0.99, y: 0.99, xanchor: "right", yanchor: "top",
      bgcolor: "rgba(0,0,0,0.4)", bordercolor: "#3F3F46", borderwidth: 1,
      font: { size: 10, color: "#A1A1AA" },
    },
    showlegend: true,
    autosize: true,
    dragmode: isDragging ? false : "zoom",
    annotations: [
      {
        x: 0.01, y: 0.99, xref: "paper", yref: "paper",
        xanchor: "left", yanchor: "top", showarrow: false,
        font: { color: "#52525B", size: 9 },
        // gh-606: Scholz review critical #1 — y-axis is T_TO/W_TO (sea-level
        // take-off thrust); t_static_N is only an RC-airframe proxy.
        text: "y-axis: T_TO/W_TO · RC airframes use static thrust as proxy · AR is a chart input",
      },
      {
        x: displayDp.ws_n_m2, y: displayDp.t_w, xref: "x", yref: "y",
        text: `  W/S=${displayDp.ws_n_m2.toFixed(0)}, T/W=${displayDp.t_w.toFixed(3)}`,
        showarrow: false, xanchor: "left", yanchor: "middle",
        font: { color: isDragging ? "#FF8400" : dpColor, size: 10 },
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Analytical binding constraint check (local, no API call)
// ---------------------------------------------------------------------------

/** Find the nearest index in a sorted ws range array for a given ws value. */
function _nearestWsIdx(ws: number, wsRange: number[]): number {
  let idx = 0;
  let minDist = Infinity;
  for (let i = 0; i < wsRange.length; i++) {
    const d = Math.abs(wsRange[i] - ws);
    if (d < minDist) { minDist = d; idx = i; }
  }
  return idx;
}

/** Compute violation ratio for a single constraint at the given design point.
 * Positive ratio = constraint is violated (T/W or W/S exceeded).
 */
function _constraintViolationRatio(
  c: ConstraintLine,
  ws: number,
  tw: number,
  nearestIdx: number,
): number {
  if (c.t_w_points) {
    const twReq = c.t_w_points[nearestIdx];
    if (twReq > 0) return (twReq - tw) / twReq;
  } else if (c.ws_max != null && isFinite(c.ws_max)) {
    return (ws - c.ws_max) / c.ws_max;
  }
  return -Infinity;
}

/** Find which constraint is nearest-limiting at a given (ws, tw) position.
 *
 * Returns the name of the most-violated or tightest constraint, or null if
 * no constraint data is available.
 *
 * Exported for unit testing.
 */
export function findBindingConstraintAtPoint(
  ws: number,
  tw: number,
  wsRange: number[],
  constraints: ConstraintLine[],
): string | null {
  if (!wsRange.length) return null;
  const nearestIdx = _nearestWsIdx(ws, wsRange);
  let bindingName: string | null = null;
  let maxRatio = -Infinity;
  for (const c of constraints) {
    const ratio = _constraintViolationRatio(c, ws, tw, nearestIdx);
    if (ratio > maxRatio) { maxRatio = ratio; bindingName = c.name; }
  }
  return bindingName;
}

/** Pattern matching CS-25-only constraint names that don't apply to
 * single-engine RC / UAV aircraft: Second-Segment Climb (OEI), Missed-Approach.
 *
 * gh-613 Phase A: these CS-25 multi-engine bands are still drawn on the chart
 * for conformance-band reference, but they must not trigger the
 * "insufficient T/W" warning for single-engine designs.
 */
const CS25_ONLY_CONSTRAINT_PATTERN = /segment.?2|second.?segment|missed.?approach|oei/i;

/** Return the name of the most-violated **t_w_points** constraint at the
 * given (ws, tw) point, or null if none is violated.
 *
 * Unlike `findBindingConstraintAtPoint`, this does NOT report ws_max
 * constraints (we only care about climb/takeoff insufficient-thrust
 * diagnostics for the current-design-point callout). Exported for unit
 * testing.
 *
 * gh-606: Scholz review substantive finding — turn the chart from
 * decorative to diagnostic by flagging insufficient T/W.
 *
 * gh-613 Phase A: when `skipOei` is true, constraints whose name matches
 * the CS-25-only pattern (Second-Segment Climb, Missed-Approach, generic
 * OEI bands) are excluded from the binding-selection logic. The constraint
 * curves are still drawn on the chart — only the warning text is gated.
 */
export function findInsufficientThrustConstraint(
  ws: number,
  tw: number,
  wsRange: number[],
  constraints: ConstraintLine[],
  skipOei: boolean = false,
): string | null {
  if (!wsRange.length) return null;
  const nearestIdx = _nearestWsIdx(ws, wsRange);
  let bindingName: string | null = null;
  let maxRatio = 0;
  for (const c of constraints) {
    if (!c.t_w_points) continue;
    if (skipOei && CS25_ONLY_CONSTRAINT_PATTERN.test(c.name)) continue;
    const twReq = c.t_w_points[nearestIdx];
    if (twReq <= 0) continue;
    const ratio = (twReq - tw) / twReq;
    if (ratio > maxRatio) {
      maxRatio = ratio;
      bindingName = c.name;
    }
  }
  return bindingName;
}

// ---------------------------------------------------------------------------
// Derived value helpers (pure, exported for unit testing)
// ---------------------------------------------------------------------------

/** Compute S [m²] from weight [N] and wing loading [N/m²]. */
export function computeWingArea(weightN: number, wsNm2: number): number {
  if (wsNm2 <= 0) return NaN;
  return weightN / wsNm2;
}

/** Compute T [N] from weight [N] and thrust-to-weight ratio. */
export function computeThrust(weightN: number, tw: number): number {
  return tw * weightN;
}

/** Compute aspect ratio from reference span [m] and reference area [m²]. */
export function computeAspectRatio(bRefM: number | null | undefined, sRefM2: number | null | undefined): number | null {
  if (bRefM == null || sRefM2 == null || sRefM2 <= 0) return null;
  return (bRefM * bRefM) / sRefM2;
}

// ---------------------------------------------------------------------------
// Info modal — Scholz/Sadraey sizing methodology explainer
// ---------------------------------------------------------------------------

interface InfoModalProps {
  readonly open: boolean;
  readonly onClose: () => void;
}

// ---------------------------------------------------------------------------
// gh-613 Phase A — CS-25 honesty: per-constraint relevance badges
// ---------------------------------------------------------------------------

type ConstraintRelevance = "universal" | "conditional" | "cs25-only";

const RELEVANCE_LABEL: Record<ConstraintRelevance, string> = {
  universal: "✅ Universal",
  conditional: "⚠️ Conditional",
  "cs25-only": "❌ CS-25-only",
};

const RELEVANCE_CLASS: Record<ConstraintRelevance, string> = {
  universal:
    "inline-flex items-center gap-1 rounded bg-green-500/15 px-1.5 py-0.5 text-[10px] text-green-400",
  conditional:
    "inline-flex items-center gap-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] text-amber-400",
  "cs25-only":
    "inline-flex items-center gap-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] text-red-400",
};

/** Small inline badge tagging each constraint row in the info modal with its
 * relevance to single-engine RC / UAV designs.
 *
 * gh-613 Phase A: helps the user separate "CS-25 conformance band" curves
 * (Second-Segment OEI, Missed-Approach) from RC-applicable constraints.
 */
function RelevanceBadge({
  relevance,
  tooltip,
  testId,
}: Readonly<{
  relevance: ConstraintRelevance;
  tooltip: string;
  testId: string;
}>) {
  return (
    <span
      className={RELEVANCE_CLASS[relevance]}
      title={tooltip}
      data-relevance={relevance}
      data-testid={testId}
    >
      {RELEVANCE_LABEL[relevance]}
    </span>
  );
}

/** Modal explaining the matching-chart methodology per Loftin / Scholz §5 /
 * Sadraey §4.3.1. English-only. Vault concepts referenced:
 * `[[matching-chart-optimization]]`, `[[exam-matching-chart-design-point]]`,
 * `[[preliminary-sizing-overview]]`. */
function InfoModal({ open, onClose }: InfoModalProps) {
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      data-testid="matching-chart-info-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="matching-chart-info-title"
    >
      <div className="max-h-[85vh] w-[680px] overflow-y-auto rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3
            id="matching-chart-info-title"
            className="font-[family-name:var(--font-geist-sans)] text-[15px] font-medium text-foreground"
          >
            Matching Chart — sizing methodology
          </h3>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Close sizing methodology help"
            data-testid="info-modal-close"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-4 font-[family-name:var(--font-geist-sans)] text-[12px] leading-relaxed text-foreground">

          {/* 1. What you're doing */}
          <section data-testid="info-section-overview">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              What you&apos;re doing
            </h4>
            <p>
              Preliminary sizing per Loftin / Scholz §5 / Sadraey §4.3.1. The goal is to find the
              smallest (T, S) pair that satisfies every performance constraint. The chart visualises
              the *feasible region* in (W/S, T/W)-space, and the optimum design point typically sits
              at the intersection of the take-off requirement and the binding climb constraint.
            </p>
            <p className="mt-2 text-muted-foreground">
              <strong>SI units throughout.</strong> Sizing is a <strong>3&ndash;5 iteration outer loop</strong>: a
              single chart read is one pass. Each pass refines the polar (C<sub>D0</sub>,
              C<sub>L,max</sub>) and the mass estimate; the chart is re-plotted; design point is
              re-picked. Convergence comes from the loop, not from a single read.
            </p>
          </section>

          {/* 2. Glossary */}
          <section data-testid="info-section-glossary">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Glossary
            </h4>
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th scope="col" className="py-0.5 pr-3 font-normal">Symbol</th>
                  <th scope="col" className="py-0.5 font-normal">Meaning [units]</th>
                </tr>
              </thead>
              <tbody>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">S</td><td className="py-0.5">wing reference area [m²]</td></tr>
                <tr>
                  <td className="py-0.5 pr-3 font-mono text-foreground">T</td>
                  <td className="py-0.5">
                    take-off thrust at sea level [N] (approximated by your static-thrust input for RC airframes)
                  </td>
                </tr>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">W</td><td className="py-0.5">total weight m<sub>MTO</sub>·g [N]</td></tr>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">AR</td><td className="py-0.5">aspect ratio b²/S [-]</td></tr>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">W/S</td><td className="py-0.5">wing loading [N/m²] — sets stall speed, landing distance, cruise efficiency</td></tr>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">T/W</td><td className="py-0.5">thrust-to-weight ratio [-] — sets climb gradient, take-off distance, acceleration</td></tr>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">L/D</td><td className="py-0.5">lift-to-drag ratio at the operating point [-] — drives cruise constraint</td></tr>
                <tr><td className="py-0.5 pr-3 font-mono text-foreground">C<sub>L,max</sub></td><td className="py-0.5">maximum lift coefficient (clean, take-off, landing) [-] — drives stall and field-length constraints</td></tr>
              </tbody>
            </table>
          </section>

          {/* 3. Axes */}
          <section data-testid="info-section-axes">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Axes
            </h4>
            <p>
              <strong>x-axis:</strong> W/S [N/m²]. <strong>y-axis:</strong> T<sub>TO</sub>/W<sub>TO</sub>
              (take-off thrust over take-off weight at ISA sea level). For electric / prop RC
              airframes the lapse from static thrust to lift-off is a few percent, so your
              <span className="font-mono"> t_static_N</span> assumption is used as a proxy &mdash; the chart equates them, but
              that is a <em>convention</em>, not a definition.
            </p>
            <p className="mt-2">
              <strong>AR is a chart INPUT, not a slider.</strong> AR enters the Oswald factor
              <span className="font-mono"> e</span>, the induced-drag term, and therefore every climb and cruise curve directly.
              Changing AR upstream requires <em>re-plotting</em>; the chart does not auto-update from
              the readout panel. AR adjustment lives in the 3&ndash;5-iteration outer loop.
            </p>
          </section>

          {/* 4. Constraints */}
          <section data-testid="info-section-constraints">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Constraints (curves)
            </h4>
            {/* gh-613 Phase A: CS-25 provenance callout — drawn BEFORE the
                constraint list so the user knows the methodology pedigree
                before scanning the per-row badges. */}
            <div
              className="mb-2 border-l-4 border-amber-500/50 bg-amber-500/5 p-3 text-[12px]"
              data-testid="info-section-cs25-callout"
            >
              <em>
                This chart&apos;s constraint curves follow the Scholz/Loftin CS-25
                methodology, originally calibrated for multi-engine transport
                aircraft. For single-engine RC and UAV applications, the chart
                format (W/S vs T/W, feasibility region, design-point derivation)
                translates directly, but some constraints &mdash; specifically
                Second-Segment Climb (OEI) and Missed-Approach Climb &mdash; assume
                an engine-out condition that single-engine aircraft cannot
                experience. Read those curves as CS-25 conformance bands, not RC
                requirements.
              </em>
            </div>
            <ul className="flex list-disc flex-col gap-1.5 pl-5">
              <li className="flex flex-wrap items-center gap-2">
                <span><strong>Stall</strong> &mdash; vertical line at maximum W/S that still hits V<sub>s</sub> target.</span>
                <RelevanceBadge
                  relevance="universal"
                  tooltip="Universal — pure aerodynamics"
                  testId="constraint-badge-stall"
                />
              </li>
              <li className="flex flex-wrap items-center gap-2">
                <span><strong>Take-off field</strong> &mdash; rising-with-W/S curve; binds at small fields and high W/S.</span>
                <RelevanceBadge
                  relevance="conditional"
                  tooltip="Wheeled takeoff only"
                  testId="constraint-badge-takeoff"
                />
              </li>
              <li className="flex flex-wrap items-center gap-2">
                <span><strong>Second-segment climb (OEI)</strong> &mdash; CS-25 / FAR-25-style climb-gradient floor.</span>
                <RelevanceBadge
                  relevance="cs25-only"
                  tooltip="CS-25 multi-engine — single-engine N/A"
                  testId="constraint-badge-second-segment"
                />
              </li>
              <li className="flex flex-wrap items-center gap-2">
                <span><strong>Missed-approach climb</strong> &mdash; landing-config climb-gradient floor.</span>
                <RelevanceBadge
                  relevance="cs25-only"
                  tooltip="CS-25 multi-engine — single-engine N/A"
                  testId="constraint-badge-missed-approach"
                />
              </li>
              <li className="flex flex-wrap items-center gap-2">
                <span>
                  <strong>Cruise</strong> <em>(typically slack)</em> &mdash; matched iteratively via fuel mass, not enforced
                  on the chart per Sadraey §4.3. Drawn for reference, not selection.
                </span>
                <RelevanceBadge
                  relevance="universal"
                  tooltip="Universal — slack constraint, iterated via fuel mass"
                  testId="constraint-badge-cruise"
                />
              </li>
              <li className="flex flex-wrap items-center gap-2">
                <span><strong>Landing field</strong> &mdash; landing distance constraint; vertical W/S limit at the runway.</span>
                <RelevanceBadge
                  relevance="conditional"
                  tooltip="Runway landing only"
                  testId="constraint-badge-landing"
                />
              </li>
            </ul>
          </section>

          {/* 5. Red area */}
          <section data-testid="info-section-red-area">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Red area = infeasible
            </h4>
            <p>
              The shaded red region marks combinations of (W/S, T/W) where <strong>at least one
              constraint is violated</strong>. The unshaded region above all constraint curves
              (and to the left of the stall line) is feasible. A larger feasible region is a
              <em> permissible</em> design space, not yet an <em>optimum</em>.
            </p>
          </section>

          {/* 6. Design point selection */}
          <section data-testid="info-section-design-point">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Picking the design point (Scholz Fig. 5.9)
            </h4>
            <p>
              Scholz preference: <strong>primary</strong> &mdash; minimise T/W (engine cost / weight
              drops). <strong>Secondary</strong> &mdash; maximise W/S (smaller wing, lighter
              structure). The optimum is therefore at the <strong>intersection of the take-off line
              and the binding climb constraint</strong> &mdash; then W/S is pushed rightward to the
              landing / stall limit.
            </p>
            <pre
              aria-hidden="true"
              className="mt-2 rounded bg-card-muted p-2 font-mono text-[10px] leading-tight text-muted-foreground"
            >
{`  T/W ▲
      │  climb (binding)
      │  ╲
      │   ╲ take-off
      │    ╲╲
      │   ★ ◀─── optimum
      │     ──────────  cruise (slack)
      │
      └────────────▶  W/S
                 ▲
                 │ stall / landing limit`}
            </pre>
          </section>

          {/* 7. Reading off results */}
          <section data-testid="info-section-readoff">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              How to read off results
            </h4>
            <p>
              Once the design point (W/S)<sub>d</sub> and (T/W)<sub>d</sub> is chosen:
            </p>
            <ul className="mt-1 list-disc pl-5">
              <li><span className="font-mono">S = W / (W/S)<sub>d</sub></span> &mdash; wing reference area follows from the current MTOW estimate.</li>
              <li><span className="font-mono">T = (T/W)<sub>d</sub> · W</span> &mdash; required sea-level take-off thrust.</li>
              <li>AR is held during the read-off but it was an <em>input</em> to the chart construction.</li>
            </ul>
          </section>

          {/* 8. Iteration disclosure */}
          <section data-testid="info-section-iteration">
            <h4 className="mb-1 text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Iteration (3&ndash;5 passes)
            </h4>
            <p>
              The matching chart is one step inside a larger sizing loop. Re-plot after each
              update to mass, polar, AR, or cruise altitude until the design point converges.
              Single-pass numbers from the readout are useful for orientation, not final sizing.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Plotly chart renderer with drag support
// ---------------------------------------------------------------------------

interface MatchingChartPlotProps {
  readonly data: MatchingChartData;
  readonly dragPoint: DragPoint | null;
  readonly isDragging: boolean;
  readonly currentDp: CurrentDesignPoint | null;
  readonly onDragStart: (ws: number, tw: number) => void;
  readonly onDragMove: (ws: number, tw: number) => void;
  readonly onDragEnd: () => void;
}

function MatchingChartPlot({
  data,
  dragPoint,
  isDragging,
  currentDp,
  onDragStart,
  onDragMove,
  onDragEnd,
}: MatchingChartPlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plotlyRef = useRef<any>(null);
  // Track whether pointer is down on the design point marker
  const draggingRef = useRef(false);

  const displayDp = dragPoint ?? data.design_point;
  const dragBindingName = isDragging && dragPoint
    ? findBindingConstraintAtPoint(dragPoint.ws_n_m2, dragPoint.t_w, data.ws_range_n_m2, data.constraints)
    : null;

  // Convert pixel position to data coordinates using Plotly's _fullLayout
  const pixelToDataCoords = useCallback((clientX: number, clientY: number): { ws: number; tw: number } | null => {
    const node = containerRef.current;
    if (!node || !plotlyRef.current) return null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gd = node as any;
    if (!gd._fullLayout) return null;
    const rect = node.getBoundingClientRect();
    const xaxis = gd._fullLayout.xaxis;
    const yaxis = gd._fullLayout.yaxis;
    if (!xaxis || !yaxis) return null;

    const l = gd._fullLayout.margin.l;
    const t = gd._fullLayout.margin.t;
    const plotWidth = rect.width - gd._fullLayout.margin.l - gd._fullLayout.margin.r;
    const plotHeight = rect.height - gd._fullLayout.margin.t - gd._fullLayout.margin.b;

    const px = clientX - rect.left - l;
    const py = clientY - rect.top - t;

    // Map pixel to data: xaxis range
    const xRange = xaxis.range;
    const yRange = yaxis.range;
    const ws = xRange[0] + (px / plotWidth) * (xRange[1] - xRange[0]);
    const tw = yRange[0] + (1 - py / plotHeight) * (yRange[1] - yRange[0]);

    return {
      ws: Math.max(0, ws),
      tw: Math.max(0, tw),
    };
  }, []);

  // Hit-test whether a pointer event is near the design point marker
  const isNearDesignPoint = useCallback((clientX: number, clientY: number): boolean => {
    const node = containerRef.current;
    if (!node || !plotlyRef.current) return false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gd = node as any;
    if (!gd._fullLayout) return false;
    const rect = node.getBoundingClientRect();
    const xaxis = gd._fullLayout.xaxis;
    const yaxis = gd._fullLayout.yaxis;
    if (!xaxis || !yaxis) return false;

    const l = gd._fullLayout.margin.l;
    const t = gd._fullLayout.margin.t;
    const plotWidth = rect.width - gd._fullLayout.margin.l - gd._fullLayout.margin.r;
    const plotHeight = rect.height - gd._fullLayout.margin.t - gd._fullLayout.margin.b;
    const xRange = xaxis.range;
    const yRange = yaxis.range;

    const dpPixelX = l + ((displayDp.ws_n_m2 - xRange[0]) / (xRange[1] - xRange[0])) * plotWidth;
    const dpPixelY = t + (1 - (displayDp.t_w - yRange[0]) / (yRange[1] - yRange[0])) * plotHeight;

    const dx = clientX - rect.left - dpPixelX;
    const dy = clientY - rect.top - dpPixelY;
    const distPx = Math.sqrt(dx * dx + dy * dy);
    return distPx < 18; // 18px hit radius (larger than the 12px marker radius)
  }, [displayDp]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      plotlyRef.current = Plotly;
      if (disposed || !node) return;

      const ws = data.ws_range_n_m2;
      const { traces: constraintTraces, shapes } = buildConstraintTraces(ws, data, dragBindingName);
      const allTraces: PlotlyTrace[] = [
        buildHullFill(ws, data),
        ...constraintTraces,
        buildDesignPointTrace(displayDp.ws_n_m2, displayDp.t_w, data.feasibility, isDragging),
      ];
      // gh-606: include current-design-point trace when available (powered
      // aircraft only — gliders are suppressed upstream in MatchingChartTab).
      if (currentDp) {
        allTraces.push(buildCurrentDesignPointTrace(currentDp));
      }
      const layout = { ...buildLayout(ws, data, displayDp, isDragging), shapes };

      await Plotly.react(node, allTraces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, displayDp.ws_n_m2, displayDp.t_w, isDragging, dragBindingName, currentDp]);

  // Cleanup Plotly on unmount
  useEffect(() => {
    const node = containerRef.current;
    return () => {
      if (node && plotlyRef.current) {
        plotlyRef.current.purge(node);
      }
    };
  }, []);

  // Attach drag listeners to the plot div
  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    function handleMouseDown(e: MouseEvent) {
      if (isNearDesignPoint(e.clientX, e.clientY)) {
        e.preventDefault();
        e.stopPropagation();
        draggingRef.current = true;
        const coords = pixelToDataCoords(e.clientX, e.clientY);
        if (coords) onDragStart(coords.ws, coords.tw);
      }
    }

    function handleMouseMove(e: MouseEvent) {
      if (!draggingRef.current) return;
      e.preventDefault();
      const coords = pixelToDataCoords(e.clientX, e.clientY);
      if (coords) onDragMove(coords.ws, coords.tw);
    }

    function handleMouseUp(e: MouseEvent) {
      if (!draggingRef.current) return;
      e.preventDefault();
      draggingRef.current = false;
      onDragEnd();
    }

    node.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      node.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isNearDesignPoint, pixelToDataCoords, onDragStart, onDragMove, onDragEnd]);

  return (
    <div className="flex flex-1 flex-col">
      <div
        ref={containerRef}
        className="h-full min-h-0 w-full"
        style={{ height: 340, cursor: isDragging ? "grabbing" : "default" }}
        data-testid="matching-chart-plot"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Design-point summary row (extracted to reduce MatchingChartTab complexity)
// ---------------------------------------------------------------------------

interface DesignPointSummaryProps {
  readonly data: MatchingChartData;
  readonly isDragging: boolean;
  readonly displayDp: { ws_n_m2: number; t_w: number } | undefined;
  readonly liveDragBinding: string | null;
  readonly weightN: number | null;
  readonly aspectRatio: number | null;
}

/** Single readout cell with optional title (tooltip) and testid. */
function SummaryCell({
  label,
  value,
  title,
  color,
  testId,
}: Readonly<{
  label: string;
  value: string;
  title?: string;
  color?: string;
  testId?: string;
}>) {
  return (
    <div className="flex flex-col gap-0.5">
      <span
        className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground"
        title={title}
      >
        {label}
      </span>
      <span
        className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] font-semibold"
        style={color ? { color } : undefined}
        data-testid={testId}
      >
        {value}
      </span>
    </div>
  );
}

/** Format helpers — pulled out to flatten the JSX. */
function fmtWs(displayDp: { ws_n_m2: number } | undefined): string {
  return displayDp ? `${displayDp.ws_n_m2.toFixed(0)} N/m²` : "—";
}
function fmtTw(displayDp: { t_w: number } | undefined): string {
  return displayDp ? displayDp.t_w.toFixed(3) : "—";
}
function fmtArea(area: number | null): string {
  return area != null && isFinite(area) ? `${area.toFixed(3)} m²` : "—";
}
function fmtThrust(thrust: number | null): string {
  return thrust != null && isFinite(thrust) ? `${formatSigFigs(thrust, 3)} N` : "—";
}
function fmtWeight(w: number | null): string {
  return w != null && isFinite(w) ? `${w.toFixed(1)} N` : "—";
}
function fmtAr(ar: number | null): string {
  return ar != null && isFinite(ar) ? ar.toFixed(2) : "—";
}

function BindingCells({
  data,
  isDragging,
  liveDragBinding,
}: Readonly<{
  data: MatchingChartData;
  isDragging: boolean;
  liveDragBinding: string | null;
}>) {
  if (isDragging) {
    if (!liveDragBinding) return null;
    const color = data.constraints.find((c) => c.name === liveDragBinding)?.color ?? "#FF8400";
    return (
      <div className="flex flex-col gap-0.5">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">Binding</span>
        <span
          className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold"
          style={{ color }}
          data-testid="drag-binding"
        >
          {liveDragBinding}
        </span>
      </div>
    );
  }
  return (
    <>
      {data.constraints.filter((c) => c.binding).map((c) => (
        <div key={c.name} className="flex flex-col gap-0.5">
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">Binding</span>
          <span
            className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold"
            style={{ color: c.color }}
          >
            {c.name}
          </span>
        </div>
      ))}
    </>
  );
}

function DesignPointSummary({
  data,
  isDragging,
  displayDp,
  liveDragBinding,
  weightN,
  aspectRatio,
}: DesignPointSummaryProps) {
  const activeColor = isDragging ? "#FF8400" : undefined;
  const hasMass = weightN != null && weightN > 0;
  // gh-606: live-derived S = W/(W/S), T = T/W·W using the held W and AR.
  const derivedS = displayDp && hasMass ? computeWingArea(weightN!, displayDp.ws_n_m2) : null;
  const derivedT = displayDp && hasMass ? computeThrust(weightN!, displayDp.t_w) : null;

  return (
    <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-card px-4 py-3">
      <SummaryCell
        label={isDragging ? "Drag W/S" : "Design Point W/S"}
        value={fmtWs(displayDp)}
        color={activeColor}
        testId="dp-ws"
      />
      <SummaryCell
        label={isDragging ? "Drag T/W" : "Design Point T/W"}
        value={fmtTw(displayDp)}
        color={activeColor}
        testId="dp-tw"
      />
      <SummaryCell
        label="S = W / (W/S)"
        title="S = W / (W/S)"
        value={fmtArea(derivedS)}
        color={activeColor}
        testId="dp-derived-s"
      />
      <SummaryCell
        label="T = (T/W)·W"
        title="T = (T/W) · W"
        value={fmtThrust(derivedT)}
        color={activeColor}
        testId="dp-derived-t"
      />
      <SummaryCell
        label="W (m_MTO · g)"
        title="W = m_MTO · g, treated as constant during this chart read"
        value={fmtWeight(weightN)}
        testId="dp-w"
      />
      <SummaryCell
        label="AR (input — see info modal)"
        title="AR is a chart input — changing it requires re-plotting"
        value={fmtAr(aspectRatio)}
        testId="dp-ar"
      />
      <BindingCells data={data} isDragging={isDragging} liveDragBinding={liveDragBinding} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feasibility badge
// ---------------------------------------------------------------------------

function FeasibilityBadge({ feasibility }: Readonly<{ feasibility: string }>) {
  const ok = feasibility === "feasible";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${
        ok ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"
      }`}
    >
      {ok ? "Feasible" : "Infeasible"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Chart + drag state (extracted to enable key-based reset when data changes)
// ---------------------------------------------------------------------------

interface MatchingChartContentProps {
  readonly data: MatchingChartData;
  readonly currentDp: CurrentDesignPoint | null;
  readonly weightN: number | null;
  readonly aspectRatio: number | null;
  readonly isGlider: boolean;
  readonly insufficientConstraintName: string | null;
}

/** Internal component that owns drag state for a given snapshot of chart data.
 * Rendered with key={data.design_point.ws_n_m2 + data.design_point.t_w} so that
 * when fresh server data arrives the drag state resets automatically via re-mount.
 */
function MatchingChartContent({
  data,
  currentDp,
  weightN,
  aspectRatio,
  isGlider,
  insufficientConstraintName,
}: MatchingChartContentProps) {
  const [dragPoint, setDragPoint] = useState<DragPoint | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragStart = useCallback((ws: number, tw: number) => {
    setIsDragging(true);
    setDragPoint({ ws_n_m2: ws, t_w: tw });
  }, []);

  const handleDragMove = useCallback((ws: number, tw: number) => {
    setDragPoint({ ws_n_m2: ws, t_w: tw });
  }, []);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  const displayDp = dragPoint ?? data.design_point;

  const liveDragBinding = isDragging && dragPoint
    ? findBindingConstraintAtPoint(dragPoint.ws_n_m2, dragPoint.t_w, data.ws_range_n_m2, data.constraints)
    : null;

  return (
    <>
      <div className="relative rounded-xl border border-border bg-card p-2">
        <MatchingChartPlot
          data={data}
          dragPoint={dragPoint}
          isDragging={isDragging}
          currentDp={currentDp}
          onDragStart={handleDragStart}
          onDragMove={handleDragMove}
          onDragEnd={handleDragEnd}
        />
        {/* gh-606: glider suppression per Scholz review critical #3 */}
        {isGlider && (
          <div
            className="absolute left-3 top-3 max-w-[420px] rounded bg-card-muted/90 px-2 py-1 text-[10px] text-muted-foreground"
            data-testid="glider-callout"
          >
            Matching chart is jet/powered-only &mdash; gliders are sized by sink-rate polar, not T/W vs W/S.
          </div>
        )}
        {/* gh-606: insufficient-thrust callout per Scholz review substantive finding.
            gh-613 Phase A: warning excludes single-engine-irrelevant OEI bands. */}
        {!isGlider && currentDp && insufficientConstraintName && (
          <div
            className="absolute right-3 top-3 max-w-[360px] rounded bg-red-900/70 px-2 py-1 text-[10px] text-red-200"
            data-testid="insufficient-thrust-callout"
          >
            Your assumed T/W = {currentDp.t_w.toFixed(3)} is insufficient for the {insufficientConstraintName} constraint at the current W/S (excluding single-engine-irrelevant OEI bands).
          </div>
        )}
      </div>
      <DesignPointSummary
        data={data}
        isDragging={isDragging}
        displayDp={displayDp}
        liveDragBinding={liveDragBinding}
        weightN={weightN}
        aspectRatio={aspectRatio}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Main MatchingChartTab
// ---------------------------------------------------------------------------

export function MatchingChartTab({ aeroplaneId }: Props) {
  const [mode, setMode] = useState<AircraftMode>("rc_runway");
  const [sRunway, setSRunway] = useState<number>(MODE_DEFAULTS[mode].sRunway);
  const [vSTarget, setVSTarget] = useState<number>(MODE_DEFAULTS[mode].vSTarget);
  const [gamma, setGamma] = useState<number>(MODE_DEFAULTS[mode].gamma);
  const [infoOpen, setInfoOpen] = useState(false);

  function handleModeChange(newMode: AircraftMode) {
    setMode(newMode);
    setSRunway(MODE_DEFAULTS[newMode].sRunway);
    setVSTarget(MODE_DEFAULTS[newMode].vSTarget);
    setGamma(MODE_DEFAULTS[newMode].gamma);
  }

  const { data, isLoading, error } = useMatchingChart(aeroplaneId, {
    mode,
    sRunway: sRunway > 0 ? sRunway : undefined,
    vSTarget,
    gammaClimbDeg: gamma,
  });

  // gh-606: pull mass + t_static + s_ref + b_ref to compute the current
  // (W/S, T/W) point and the live readout's "held" W and AR.
  const { data: assumptionsData } = useDesignAssumptions(aeroplaneId);
  const { data: ctx } = useComputationContext(aeroplaneId);

  const massKg = useMemo(() => {
    const a = assumptionsData?.assumptions.find((x) => x.parameter_name === "mass");
    return a ? a.effective_value : null;
  }, [assumptionsData]);

  const tStaticN = useMemo(() => {
    const a = assumptionsData?.assumptions.find((x) => x.parameter_name === "t_static_N");
    return a ? a.effective_value : null;
  }, [assumptionsData]);

  const sRefM2 = ctx?.s_ref_m2 ?? null;
  const bRefM = ctx?.b_ref_m ?? null;
  const isGlider = ctx?.is_glider === true;

  const weightN = massKg != null && massKg > 0 ? massKg * G_MPS2 : null;
  const aspectRatio = computeAspectRatio(bRefM, sRefM2);

  // gh-606: glider suppression — Scholz review critical #3. Drawing a phantom
  // marker at T/W = 0 trains the user to misread the chart. Suppress entirely.
  const currentDp: CurrentDesignPoint | null = useMemo(() => {
    if (isGlider) return null;
    if (massKg == null || sRefM2 == null || tStaticN == null) return null;
    if (sRefM2 <= 0 || massKg <= 0 || tStaticN <= 0) return null;
    const w = massKg * G_MPS2;
    const ws = w / sRefM2;
    const tw = tStaticN / w;
    return {
      ws_n_m2: ws,
      t_w: tw,
      mass_kg: massKg,
      s_m2: sRefM2,
      t_n: tStaticN,
      w_n: w,
      ar: aspectRatio,
    };
  }, [isGlider, massKg, sRefM2, tStaticN, aspectRatio]);

  // gh-606: insufficient-thrust diagnostic (substantive finding in Scholz review).
  // gh-613 Phase A: skip CS-25-only OEI constraints when selecting the binding
  // constraint. Those curves are still drawn (as CS-25 conformance bands) but
  // do not raise a warning for single-engine RC / UAV designs.
  const insufficientConstraintName = useMemo(() => {
    if (!data || !currentDp) return null;
    return findInsufficientThrustConstraint(
      currentDp.ws_n_m2,
      currentDp.t_w,
      data.ws_range_n_m2,
      data.constraints,
      true, // skipOei
    );
  }, [data, currentDp]);

  // Stable key: changes only when the server returns a new design point.
  // This re-mounts MatchingChartContent and resets its internal drag state.
  const contentKey = data
    ? `${data.design_point.ws_n_m2}-${data.design_point.t_w}`
    : "loading";

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Sizing / Matching Chart
        </span>
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          Scholz §5.2–5.4 · Loftin 1980
        </span>
        {data && <FeasibilityBadge feasibility={data.feasibility} />}
        <span className="flex-1" />
      </div>

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
        <div className="flex flex-col gap-0.5">
          <label className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Mode
          </label>
          <select
            value={mode}
            onChange={(e) => handleModeChange(e.target.value as AircraftMode)}
            className="rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          >
            {Object.entries(MODE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-0.5">
          <label className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Runway [m]
          </label>
          <input
            type="number"
            value={sRunway}
            min={0}
            step={10}
            onChange={(e) => setSRunway(Number(e.target.value))}
            className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          />
        </div>

        <div className="flex flex-col gap-0.5">
          <label className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            V_s max [m/s]
          </label>
          <input
            type="number"
            value={vSTarget}
            min={1}
            step={1}
            onChange={(e) => setVSTarget(Number(e.target.value))}
            className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          />
        </div>

        <div className="flex flex-col gap-0.5">
          <label className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            γ climb [°]
          </label>
          <input
            type="number"
            value={gamma}
            min={0.5}
            max={30}
            step={0.5}
            onChange={(e) => setGamma(Number(e.target.value))}
            className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          />
        </div>

        {/* gh-606: Info button now opens the methodology modal. */}
        <div className="ml-auto flex items-center gap-2 text-[10px] text-muted-foreground">
          <button
            type="button"
            onClick={() => setInfoOpen(true)}
            aria-label="Open sizing methodology help"
            data-testid="info-modal-trigger"
            className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-1 hover:border-orange-400 hover:text-foreground"
          >
            <Info size={11} />
            <span className="font-[family-name:var(--font-geist-sans)]">
              How to read this chart
            </span>
          </button>
          <span className="font-[family-name:var(--font-geist-sans)] hidden md:inline">
            Drag the design point to explore S and T for the held W and AR
          </span>
        </div>
      </div>

      {/* gh-606: Modal */}
      <InfoModal open={infoOpen} onClose={() => setInfoOpen(false)} />

      {/* States */}
      {isLoading && (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 size={14} className="animate-spin text-muted-foreground" />
          <span className="ml-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
            Computing constraints…
          </span>
        </div>
      )}

      {error && !isLoading && (
        <div className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-card p-4">
          <AlertTriangle size={14} className="text-orange-400" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
            {(error as { status?: number }).status === 422
              ? "Run assumption recompute to enable matching chart (polar parameters needed)"
              : "Matching chart unavailable — set mass, thrust and polar parameters first"}
          </span>
        </div>
      )}

      {data && !isLoading && (
        <>
          {/* MatchingChartContent owns drag state; key forces reset on new server data */}
          <MatchingChartContent
            key={contentKey}
            data={data}
            currentDp={currentDp}
            weightN={weightN}
            aspectRatio={aspectRatio}
            isGlider={isGlider}
            insufficientConstraintName={insufficientConstraintName}
          />

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <div className="rounded-lg bg-orange-900/30 px-3 py-2">
              {data.warnings.map((w, i) => (
                <p
                  key={i}
                  className="font-[family-name:var(--font-geist-sans)] text-[10px] text-orange-400"
                >
                  ⚠ {w}
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
