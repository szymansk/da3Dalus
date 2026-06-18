"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { AlertTriangle, Loader2, Maximize2, Minimize2, Settings } from "lucide-react";
import type { AnalysisResult } from "@/hooks/useAnalysis";
import type { StripForcesResult } from "@/hooks/useStripForces";
import type { SpeedPolar, SpeedPolarCurve } from "@/hooks/useAnalysis";
import type { FlightEnvelopeData } from "@/hooks/useFlightEnvelope";
import { EnvelopePanel } from "@/components/workbench/EnvelopePanel";
import { buildSpeedPolarLayout } from "@/lib/speedPolarLayout";
import type { StoredOperatingPoint, AVLTrimResult, AeroBuildupTrimResult, TrimConstraint, ControlSurface } from "@/hooks/useOperatingPoints";
import { OperatingPointsPanel } from "@/components/workbench/OperatingPointsPanel";
import { MatchingChartTab } from "@/components/workbench/MatchingChartTab";
import { AnalysisStatusIndicator } from "./AnalysisStatusIndicator";
import type { AnalysisStatus } from "@/hooks/useAnalysisStatus";
import type { SpanwiseLoadsResult } from "@/hooks/useSpanwiseLoads";
import { SparSizingPanel, toSizingParams } from "@/components/workbench/SparSizingPanel";
import type { SparSizingInputs } from "@/components/workbench/SparSizingPanel";
import { useSparSizing } from "@/hooks/useSparSizing";
import { useSparPlan, type SparPlanParams } from "@/hooks/useSparPlan";
import { buildMomentsFromLoads } from "@/lib/sparPlanHelpers";
import { useSWRConfig } from "swr";

const TABS = ["Assumptions", "Operating Points", "Polar", "Trefftz Plane", "Spanwise Loads", "Streamlines", "Envelope", "Sizing"] as const;
export type Tab = (typeof TABS)[number];
export { TABS };

// gh-575: build the chip-row rightSlot from optional analysis-run metadata.
// Returns null when neither segment is present, so the "No data" sentinel
// the previous implementation rendered is dropped entirely.
// Exported for direct unit testing.
export function buildAnalysisRightSlot(
  pointCount: number | null,
  lastRunTime: Date | null | undefined,
  lastRunDurationMs: number | null | undefined,
): React.ReactNode {
  const parts: string[] = [];
  if (pointCount != null) parts.push(`${pointCount} points`);
  if (lastRunTime && lastRunDurationMs != null) {
    const time = lastRunTime.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    parts.push(`Last run: ${time} · ${lastRunDurationMs} ms`);
  }
  if (parts.length === 0) return null;
  return (
    <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
      {parts.join(" · ")}
    </span>
  );
}

interface WingXSec {
  readonly xyz_le: readonly number[];
  readonly chord: number;
}

interface Props {
  readonly result: AnalysisResult | null;
  readonly speedPolar?: SpeedPolar | null;
  readonly aeroplaneId?: string | null;
  readonly lastRunTime?: Date | null;
  readonly lastRunDurationMs?: number | null;
  readonly stripForces?: StripForcesResult | null;
  readonly stripForcesLoading?: boolean;
  readonly spanwiseLoads?: SpanwiseLoadsResult | null;
  readonly spanwiseLoadsLoading?: boolean;
  readonly streamlinesFigure?: unknown;
  readonly streamlinesLoading?: boolean;
  readonly activeTab: Tab;
  readonly onTabChange: (tab: Tab) => void;
  readonly onConfigureClick?: () => void;
  readonly onEditAvlGeometry?: () => void;
  readonly showAvlGeometryButton?: boolean;
  readonly wingXSecs?: WingXSec[] | null;
  readonly wingSymmetric?: boolean;
  readonly assumptionsSlot?: React.ReactNode;
  readonly hasWings?: boolean;
  readonly envelope?: FlightEnvelopeData | null;
  readonly isComputingEnvelope?: boolean;
  readonly envelopeError?: string | null;
  readonly onComputeEnvelope?: () => void;
  readonly operatingPoints?: StoredOperatingPoint[];
  /** gh-865: live placeholder + solved rows during streaming generation. */
  readonly streamingOperatingPoints?: StoredOperatingPoint[] | null;
  readonly isLoadingOps?: boolean;
  readonly isGeneratingOps?: boolean;
  readonly isTrimmingOps?: boolean;
  readonly opsError?: string | null;
  readonly onGenerateOps?: () => void;
  readonly onTrimWithAvl?: (point: StoredOperatingPoint, constraints: TrimConstraint[]) => Promise<AVLTrimResult | null>;
  readonly onTrimWithAerobuildup?: (point: StoredOperatingPoint, trimVariable: string, targetCoefficient: string, targetValue: number) => Promise<AeroBuildupTrimResult | null>;
  readonly controlSurfaces?: ControlSurface[];
  readonly onUpdateDeflections?: (opId: number, deflections: Record<string, number> | null) => Promise<void>;
  readonly onDeleteOp?: (opId: number) => Promise<void>;
  readonly onDeleteAllOps?: () => Promise<void>;
  readonly onCreateOp?: (payload: {
    name: string;
    velocity: number;
    alpha: number;
    beta?: number;
    altitude?: number;
    config?: string;
  }) => Promise<void>;
  readonly analysisStatus?: AnalysisStatus;
}

// -- Plotly Chart (dynamic import) ----------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyTrace = Record<string, any>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyShape = Record<string, any>;

function PlotlyChart({
  xData,
  yData,
  xLabel,
  yLabel,
  title,
  annotation,
  color = "#FF8400",
  xFormat,
  onToggleMaximize,
  isMaximized,
  extraTraces,
  shapes,
}: Readonly<{
  // null entries are rendered by Plotly as gaps (degenerate/sanitized
  // coefficients from gh-815); see derivePolarCharts.
  xData: (number | null)[];
  yData: (number | null)[];
  xLabel: string;
  yLabel: string;
  title: string;
  annotation?: string;
  color?: string;
  xFormat?: (v: number) => string;
  onToggleMaximize?: () => void;
  isMaximized?: boolean;
  extraTraces?: PlotlyTrace[];
  shapes?: PlotlyShape[];
}>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || xData.length === 0) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const mainTrace: PlotlyTrace = {
        x: xData,
        y: yData,
        type: "scatter",
        mode: "lines",
        line: { color, width: 2 },
        hovertemplate: `${xLabel}: %{x}<br>${yLabel}: %{y}<extra></extra>`,
      };

      const allTraces = [mainTrace, ...(extraTraces || [])];

      const layout: Record<string, unknown> = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
        margin: { l: 50, r: 15, t: 5, b: 40 },
        xaxis: {
          title: { text: xLabel, font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        yaxis: {
          title: { text: yLabel, font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        showlegend: false,
        autosize: true,
        yaxis2: {
          overlaying: "y", side: "right",
          showgrid: false, showticklabels: false, zeroline: false,
        },
      };
      if ((shapes?.length ?? 0) > 0) {
        layout.shapes = shapes;
      }

      await PlotlyRef.react(node, allTraces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [xData, yData, xLabel, yLabel, color, xFormat, extraTraces, shapes]);

  if (xData.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-xl border border-border bg-card p-4">
        <span className="text-[12px] text-muted-foreground">No data</span>
      </div>
    );
  }

  return (
    <div className="group/chart flex flex-1 flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
          {title}
        </span>
        {annotation && (
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
            {annotation}
          </span>
        )}
        <span className="flex-1" />
        {onToggleMaximize && (
          <button
            onClick={onToggleMaximize}
            className="flex size-5 items-center justify-center rounded-[2px] text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover/chart:opacity-100"
            title={isMaximized ? "Restore" : "Maximize"}
          >
            {isMaximized ? <Minimize2 size={10} /> : <Maximize2 size={10} />}
          </button>
        )}
      </div>
      <div
        className="rounded-xl border border-border bg-card"
        style={{ height: isMaximized ? "100%" : 220 }}
      >
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </div>
  );
}

// -- Speed Polar (Geschwindigkeitspolare) ---------------------------------

const SPEED_POLAR_COLORS = [
  "#3B82F6", "#30A46C", "#E5484D", "#A78BFA", "#F59E0B", "#06B6D4",
];

/** Format a mass for German-style display ("1.5" -> "1,5"). */
function fmtMassKg(m: number): string {
  return String(m).replace(".", ",");
}

/** Negate one sink-rate value (plotted downward). Hoisted to avoid deep nesting. */
function negate(w: number): number {
  return -w;
}

/** Build the line trace for one mass curve. */
function speedPolarLineTrace(c: SpeedPolarCurve, i: number): PlotlyTrace {
  return {
    x: c.V,
    y: c.w.map(negate),
    customdata: c.w,
    type: "scatter",
    mode: "lines",
    name: `${fmtMassKg(c.mass_kg)} kg${c.is_base ? " (Basis)" : ""}`,
    line: {
      color: c.is_base ? "#FF8400" : SPEED_POLAR_COLORS[i % SPEED_POLAR_COLORS.length],
      width: c.is_base ? 2.5 : 1.5,
    },
    hovertemplate: `${fmtMassKg(c.mass_kg)} kg<br>V: %{x:.1f} m/s<br>w: %{customdata:.2f} m/s<extra></extra>`,
  };
}

/** Marker trace for min-sink / best-glide on the base curve, or null if absent. */
function speedPolarMarkerTrace(base: SpeedPolarCurve): PlotlyTrace | null {
  const mX: number[] = [];
  const mY: number[] = [];
  const mT: string[] = [];
  if (base.v_min_sink != null && base.w_min != null) {
    mX.push(base.v_min_sink);
    mY.push(-base.w_min);
    mT.push("min sink");
  }
  if (base.v_best_glide != null && base.ld_max && base.ld_max > 0) {
    mX.push(base.v_best_glide);
    mY.push(-(base.v_best_glide / base.ld_max));
    mT.push("best glide");
  }
  if (mX.length === 0) return null;
  return {
    x: mX,
    y: mY,
    text: mT,
    type: "scatter",
    mode: "markers+text",
    name: "Punkte",
    textposition: "top center",
    textfont: { size: 9, color: "#FAFAFA" },
    marker: { color: "#FAFAFA", size: 7, symbol: "circle" },
    hovertemplate: "%{text}<br>V: %{x:.1f} m/s<extra></extra>",
  };
}

function speedPolarTraces(curves: SpeedPolarCurve[]): PlotlyTrace[] {
  const traces = curves.map(speedPolarLineTrace);
  const base = curves.find((c) => c.is_base) ?? curves[0];
  const markers = speedPolarMarkerTrace(base);
  if (markers) traces.push(markers);
  return traces;
}

const SPEED_POLAR_LAYOUT: Record<string, unknown> = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
  margin: { l: 55, r: 15, t: 5, b: 40 },
  xaxis: {
    title: { text: "V [m/s]", font: { size: 11 } },
    gridcolor: "#27272A",
    zerolinecolor: "#3F3F46",
  },
  yaxis: {
    title: { text: "w [m/s] (Sinken)", font: { size: 11 } },
    gridcolor: "#27272A",
    zerolinecolor: "#3F3F46",
  },
  showlegend: true,
  legend: { font: { size: 9 }, bgcolor: "transparent", orientation: "h", y: 1.14 },
  autosize: true,
};

/**
 * Glider speed polar: sink rate w over forward speed V, one curve per mass.
 * Sink is plotted downward (y = -w). The base (effective design) mass is
 * highlighted; min-sink and best-glide points are marked on it.
 */
function SpeedPolarChart({ speedPolar }: Readonly<{ speedPolar: SpeedPolar }>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    const curves = speedPolar.curves.filter((c) => c.V.length > 0);
    if (!node || curves.length === 0) return;
    let disposed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;
    const traces = speedPolarTraces(curves);

    const { v_axis_min, v_axis_max } = speedPolar;
    const layout = buildSpeedPolarLayout(SPEED_POLAR_LAYOUT, v_axis_min, v_axis_max);

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;
      await PlotlyRef.react(node, traces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [speedPolar]);

  if (speedPolar.curves.every((c) => c.V.length === 0)) {
    return null;
  }

  return (
    <div className="flex flex-col gap-1">
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
        Geschwindigkeitspolare (w über V)
      </span>
      <div className="rounded-xl border border-border bg-card" style={{ height: 280 }}>
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </div>
  );
}

// -- Streamlines Renderer -------------------------------------------------

function StreamlinesRenderer({ figure }: Readonly<{ figure: unknown }>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!figure || !node) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const figData = figure as {
        data?: unknown[];
        layout?: Record<string, unknown>;
      };
      const sceneFromLayout =
        (figData.layout?.scene as Record<string, unknown>) ?? {};

      const layout = {
        paper_bgcolor: "#09090B",
        plot_bgcolor: "#09090B",
        font: { color: "#A1A1AA" },
        margin: { l: 0, r: 0, t: 0, b: 0 },
        scene: {
          ...sceneFromLayout,
          bgcolor: "#09090B",
          xaxis: {
            ...(sceneFromLayout.xaxis as object),
            gridcolor: "#27272A",
            color: "#71717A",
          },
          yaxis: {
            ...(sceneFromLayout.yaxis as object),
            gridcolor: "#27272A",
            color: "#71717A",
          },
          zaxis: {
            ...(sceneFromLayout.zaxis as object),
            gridcolor: "#27272A",
            color: "#71717A",
          },
        },
        showlegend: false,
        autosize: true,
      };

      await PlotlyRef.react(node, figData.data || [], layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [figure]);

  return <div ref={containerRef} className="h-full w-full" />;
}

// -- Trefftz Plane Trace Builder ------------------------------------------

const SURFACE_COLORS = [
  { cl: "#E5484D", ccl: "#FF8400", clnorm: "#30A46C", ai: "#3B82F6" },
  { cl: "#D946EF", ccl: "#F59E0B", clnorm: "#06B6D4", ai: "#8B5CF6" },
  { cl: "#F97316", ccl: "#EF4444", clnorm: "#10B981", ai: "#6366F1" },
  { cl: "#EC4899", ccl: "#F59E0B", clnorm: "#14B8A6", ai: "#A78BFA" },
];

function groupSurfaceStrips(surfaces: StripForcesResult["surfaces"]) {
  const groups = new Map<string, { strips: typeof surfaces[0]["strips"] }>();
  for (const surface of surfaces) {
    const baseName = surface.surface_name.endsWith("(YDUP)")
      ? surface.surface_name.slice(0, -6).trimEnd()
      : surface.surface_name;
    const existing = groups.get(baseName);
    if (existing) {
      existing.strips = [...existing.strips, ...surface.strips];
    } else {
      groups.set(baseName, { strips: [...surface.strips] });
    }
  }
  return groups;
}

function buildSurfaceTraces(
  surfaceGroups: Map<string, { strips: StripForcesResult["surfaces"][0]["strips"] }>,
): PlotlyTrace[] {
  const traces: PlotlyTrace[] = [];
  let surfIdx = 0;

  for (const [surfaceName, group] of surfaceGroups) {
    const sorted = group.strips.toSorted((a, b) => a.Yle - b.Yle);

    const yMin = Math.min(...sorted.map((s) => s.Yle));
    const yMax = Math.max(...sorted.map((s) => s.Yle));
    if (Math.abs(yMax - yMin) < 0.001) continue;

    const ySpan = sorted.map((s) => s.Yle);
    const cl = sorted.map((s) => s.cl);
    const clNorm = sorted.map((s) => s.cl_norm);
    const cCl = sorted.map((s) => s.c_cl);
    const aiDeg = sorted.map((s) => s.ai);
    const colors = SURFACE_COLORS[surfIdx % SURFACE_COLORS.length];
    const maxAbsCl = Math.max(...cl.map(Math.abs));
    const isNegligible = maxAbsCl < 0.01;
    const defaultVisible = isNegligible ? "legendonly" as const : true;

    traces.push(
      {
        x: ySpan, y: cl, type: "scatter", mode: "lines",
        name: `Cl (${surfaceName})`, legendgroup: surfaceName,
        line: { color: colors.cl, width: 2, dash: "dash" },
        showlegend: true, visible: defaultVisible,
        hovertemplate: `${surfaceName}<br>y: %{x:.3f} m<br>Cl: %{y:.4f}<extra></extra>`,
      },
      {
        x: ySpan, y: cCl, type: "scatter", mode: "lines",
        name: `c\u00B7Cl (${surfaceName})`, legendgroup: surfaceName,
        line: { color: colors.ccl, width: 2, dash: "dash" },
        showlegend: true, visible: defaultVisible,
        hovertemplate: `${surfaceName}<br>y: %{x:.3f} m<br>c\u00B7Cl: %{y:.4f}<extra></extra>`,
      },
      {
        x: ySpan, y: clNorm, type: "scatter", mode: "lines",
        name: `Cl\u00B7C/Cref (${surfaceName})`, legendgroup: surfaceName,
        line: { color: colors.clnorm, width: 2 },
        showlegend: true, visible: defaultVisible,
        hovertemplate: `${surfaceName}<br>y: %{x:.3f} m<br>Cl\u00B7C/Cref: %{y:.4f}<extra></extra>`,
      },
      {
        x: ySpan, y: aiDeg, type: "scatter", mode: "lines",
        name: `\u03B1i (${surfaceName})`, legendgroup: surfaceName,
        line: { color: colors.ai, width: 2, dash: "dot" },
        yaxis: "y2", showlegend: true, visible: (isNegligible || surfIdx !== 0) ? "legendonly" as const : true,
        hovertemplate: `${surfaceName}<br>y: %{x:.3f} m<br>\u03B1i: %{y:.2f}\u00B0<extra></extra>`,
      },
    );
    surfIdx++;
  }

  return traces;
}

function buildSegmentMarkerTrace(
  wingXSecs: WingXSec[],
  wingSymmetric?: boolean,
): PlotlyTrace {
  const segY: number[] = [];
  for (const xs of wingXSecs) {
    segY.push(xs.xyz_le[1]);
    if (wingSymmetric) segY.push(-xs.xyz_le[1]);
  }
  return {
    x: segY, y: segY.map(() => 0),
    type: "scatter", mode: "markers",
    marker: { symbol: "triangle-up", size: 8, color: "#FF8400" },
    showlegend: false, hoverinfo: "skip",
  };
}

// -- Trefftz Plane Compute-Parameter Annotation (gh-592) ------------------

// gh-592: build the multi-line metadata text the Trefftz Plotly annotation
// renders in the top-left of the figure. All compute parameters live INSIDE
// the figure — no surrounding chrome. `<br>` is Plotly's line-break in
// annotation text. Exported for direct unit testing.
export function buildTrefftzAnnotationText(stripForces: StripForcesResult): string {
  const fmtFixed = (value: number | undefined | null, digits: number, fallback = "—") =>
    value == null || Number.isNaN(value) ? fallback : value.toFixed(digits);
  const fmtExp = (value: number | undefined | null, digits: number, fallback = "—") =>
    value == null || Number.isNaN(value) || value === 0 ? fallback : value.toExponential(digits);
  const xyz = stripForces.xyz_ref_m ?? [];
  const xyzStr = xyz.length >= 3
    ? `(${fmtFixed(xyz[0], 3)}, ${fmtFixed(xyz[1], 3)}, ${fmtFixed(xyz[2], 3)}) m`
    : "—";
  const opLabel = stripForces.operating_point_label
    ? `  ·  OP: ${stripForces.operating_point_label}`
    : "";
  const lines = [
    `Flow      α = ${fmtFixed(stripForces.alpha, 2)}°  ·  ` +
      `β = ${fmtFixed(stripForces.beta, 2)}°  ·  ` +
      `V = ${fmtFixed(stripForces.velocity_mps, 1)} m/s  ·  ` +
      `Mach = ${fmtFixed(stripForces.mach, 3)}  ·  ` +
      `Alt = ${fmtFixed(stripForces.altitude_m, 0)} m`,
    `Geometry  Wing: ${stripForces.wing_name ?? "—"}  ·  ` +
      `S_ref = ${fmtFixed(stripForces.sref, 4)} m²  ·  ` +
      `C_ref = ${fmtFixed(stripForces.cref, 4)} m  ·  ` +
      `B_ref = ${fmtFixed(stripForces.bref, 4)} m`,
    `Reference x_cg = ${xyzStr}  ·  ` +
      `Re = ${fmtExp(stripForces.reynolds, 2)}  ·  ` +
      `Model: ${stripForces.aero_model ?? "AVL"}`,
    `Run       ${stripForces.computed_at ?? "—"}${opLabel}`,
  ];
  return lines.join("<br>");
}

// -- Polar chart derivation (null-safe) -----------------------------------

// gh-817: coefficient arrays may contain null where the backend sanitized a
// non-finite solver value (gh-815). These helpers derive the polar
// characteristic points without being fooled by null->0 coercion in
// Math.max(...), and format them with a null-safe fallback. Exported for tests.

export interface PolarCharts {
  alpha: number[];
  CL: (number | null)[];
  CD: (number | null)[];
  Cm: (number | null)[] | null;
  clOverCd: (number | null)[];
  clMax: number | null;
  alphaClMax: number | null;
  ldMax: number | null;
  alphaLdMax: number | null;
}

/** Index of the largest finite value, or -1 if none is finite. */
export function finiteArgMax(values: ReadonlyArray<number | null | undefined>): number {
  let bestIdx = -1;
  let bestVal = -Infinity;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v != null && Number.isFinite(v) && v > bestVal) {
      bestVal = v;
      bestIdx = i;
    }
  }
  return bestIdx;
}

/** toFixed that renders a fallback for null / undefined / non-finite values. */
export function safeToFixed(
  value: number | null | undefined,
  digits: number,
  fallback = "n/a",
): string {
  return value == null || !Number.isFinite(value) ? fallback : value.toFixed(digits);
}

/** True if any coefficient series holds at least one finite value to plot. */
export function polarHasFiniteData(charts: PolarCharts): boolean {
  const series = [charts.CL, charts.CD, charts.clOverCd, charts.Cm ?? []];
  return series.some((arr) => arr.some((v) => v != null && Number.isFinite(v)));
}

/**
 * gh-870: Build a Plotly marker trace for a characteristic point on one of
 * the Analysis-Polar charts. Returns null when the relevant values are absent
 * or non-finite (null-safe, never throws).
 *
 * Supported chart ids:
 *   "cl"  → C_L,max marker on the CL-α chart
 *   "ld"  → (L/D),max marker on the L/D-α chart
 *   all others → null (no characteristic point defined)
 *
 * The marker style mirrors the speed-polar markers (white, circle, size 7).
 * Exported for direct unit testing.
 */
export function buildAnalysisPolarMarkerTrace(
  chartId: string,
  polar: Pick<PolarCharts, "clMax" | "alphaClMax" | "ldMax" | "alphaLdMax">,
): PlotlyTrace | null {
  let x: number;
  let y: number;
  let label: string;

  if (chartId === "cl") {
    const { clMax, alphaClMax } = polar;
    if (clMax == null || !Number.isFinite(clMax)) return null;
    if (alphaClMax == null || !Number.isFinite(alphaClMax)) return null;
    x = alphaClMax;
    y = clMax;
    label = `CL,max = ${clMax.toFixed(2)}`;
  } else if (chartId === "ld") {
    const { ldMax, alphaLdMax } = polar;
    if (ldMax == null || !Number.isFinite(ldMax)) return null;
    if (alphaLdMax == null || !Number.isFinite(alphaLdMax)) return null;
    x = alphaLdMax;
    y = ldMax;
    label = `L/D,max = ${ldMax.toFixed(1)}`;
  } else {
    return null;
  }

  return {
    x: [x],
    y: [y],
    text: [label],
    type: "scatter",
    mode: "markers+text",
    name: label,
    textposition: "top center",
    textfont: { size: 9, color: "#FAFAFA" },
    marker: { color: "#FAFAFA", size: 7, symbol: "circle" },
    hovertemplate: `${label}<extra></extra>`,
  };
}

/** Derive polar series + characteristic points, tolerating null coefficients. */
export function derivePolarCharts(result: AnalysisResult | null): PolarCharts | null {
  if (!result?.CL || result.CL.length === 0) return null;

  const { CL, CD, Cm, alpha } = result;
  const clOverCd = CL.map((cl, i) => {
    const cd = CD[i];
    // null for any non-computable L/D — including cd === 0 (degenerate), so it
    // renders as a gap and is never picked as the L/D max.
    if (cl == null || cd == null || !Number.isFinite(cl) || !Number.isFinite(cd) || cd === 0)
      return null;
    return cl / cd;
  });

  const maxCLIdx = finiteArgMax(CL);
  const maxLDIdx = finiteArgMax(clOverCd);

  return {
    alpha,
    CL,
    CD,
    Cm: Cm.length > 0 ? Cm : null,
    clOverCd,
    clMax: maxCLIdx >= 0 ? (CL[maxCLIdx] as number) : null,
    alphaClMax: maxCLIdx >= 0 ? alpha[maxCLIdx] : null,
    ldMax: maxLDIdx >= 0 ? (clOverCd[maxLDIdx] as number) : null,
    alphaLdMax: maxLDIdx >= 0 ? alpha[maxLDIdx] : null,
  };
}

// -- Trefftz Plane Combined Chart -----------------------------------------

function TrefftzPlaneChart({
  stripForces,
  wingXSecs,
  wingSymmetric,
}: Readonly<{
  stripForces: StripForcesResult;
  wingXSecs?: WingXSec[] | null;
  wingSymmetric?: boolean;
}>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || stripForces.surfaces.length === 0) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const surfaceGroups = groupSurfaceStrips(stripForces.surfaces);
      const traces: PlotlyTrace[] = buildSurfaceTraces(surfaceGroups);

      if ((wingXSecs?.length ?? 0) > 0) {
        traces.push(buildSegmentMarkerTrace(wingXSecs!, wingSymmetric));
      }

      const shapes: PlotlyShape[] = [];
      // gh-592: multi-line, structured compute-parameter readout. All metadata
      // (flow / geometry / reference / run) stays INSIDE the Plotly figure \u2014
      // no surrounding chrome (sidebar, header, footer).
      const annotations = [{
        x: 0.01, y: 0.98, xref: "paper", yref: "paper",
        xanchor: "left", yanchor: "top", showarrow: false,
        align: "left",
        font: { color: "#71717A", family: "JetBrains Mono, monospace", size: 10 },
        text: buildTrefftzAnnotationText(stripForces),
      }];

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
        margin: { l: 55, r: 55, t: 30, b: 45 },
        xaxis: {
          title: { text: "Y [m]", font: { size: 11 } },
          gridcolor: "#27272A", zerolinecolor: "#3F3F46",
        },
        yaxis: {
          title: { text: "Cl, c\u00B7Cl, Cl\u00B7C/Cref", font: { size: 11, color: "#A1A1AA" } },
          gridcolor: "#27272A", zerolinecolor: "#3F3F46",
        },
        yaxis2: {
          title: { text: "\u03B1i [\u00B0]", font: { size: 11, color: "#3B82F6" } },
          overlaying: "y", side: "right",
          gridcolor: "transparent", zerolinecolor: "#3F3F46",
          tickfont: { color: "#3B82F6" },
        },
        legend: {
          x: 0.98, y: 0.98, xanchor: "right", yanchor: "top",
          bgcolor: "rgba(0,0,0,0.4)", bordercolor: "#3F3F46", borderwidth: 1,
          font: { size: 10, color: "#A1A1AA" },
        },
        showlegend: true,
        autosize: true,
        shapes,
        annotations,
      };

      await PlotlyRef.react(node, traces, layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [stripForces, wingXSecs, wingSymmetric]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-card-muted">
      <div ref={containerRef} className="min-h-0 flex-1" />
    </div>
  );
}

// -- Tab Content Helpers --------------------------------------------------

// Exported for direct unit testing (gh-592).
export function TrefftzPlaneTabContent({
  stripForcesLoading,
  stripForces,
  wingXSecs,
  wingSymmetric,
}: Readonly<{
  stripForcesLoading?: boolean;
  stripForces?: StripForcesResult | null;
  wingXSecs?: WingXSec[] | null;
  wingSymmetric?: boolean;
}>) {
  if (stripForcesLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div
          className="flex items-center gap-2 text-muted-foreground"
          data-testid="trefftz-spinner"
        >
          <Loader2 size={14} className="animate-spin" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px]">
            Running strip-force analysis…
          </span>
        </div>
      </div>
    );
  }
  if ((stripForces?.surfaces.length ?? 0) > 0) {
    return (
      <TrefftzPlaneChart
        stripForces={stripForces!}
        wingXSecs={wingXSecs}
        wingSymmetric={wingSymmetric}
      />
    );
  }
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
        Run an analysis to see strip-force distributions
      </span>
    </div>
  );
}

// -- Spanwise Loads Chart (gh-1002) ----------------------------------------

/**
 * Build the Plotly annotation text for the spanwise-loads chart.
 * Echoes all compute inputs inside the figure (per project Plotly-metadata convention).
 * Exported for direct unit testing.
 */
export function buildSpanwiseLoadsAnnotationText(loads: SpanwiseLoadsResult): string {
  const fmtFixed = (value: number | undefined | null, digits: number, fallback = "—") =>
    value == null || Number.isNaN(value) ? fallback : value.toFixed(digits);
  return [
    `α = ${fmtFixed(loads.alpha, 2)}°  V = ${fmtFixed(loads.velocity_mps, 1)} m/s  Alt = ${fmtFixed(loads.altitude_m, 0)} m`,
    `q = ${fmtFixed(loads.dynamic_pressure_Pa, 1)} Pa`,
  ].join("<br>");
}

/**
 * Pure transform: spanwise-loads response → Plotly traces + annotations.
 *
 * For each surface it emits two line traces (V(y) on the primary y-axis,
 * M(y) on the secondary y-axis), mirroring the port half to negative Y so
 * the full span is plotted left-to-right. The first surface (main wing)
 * also gets root bending-moment / shear arrow annotations anchored at the
 * innermost plotted strip, plus the compute-parameter annotation.
 *
 * Exported and Plotly-free so it can be unit-tested directly in jsdom.
 */
export function buildSpanwiseLoadsTracesAndAnnotations(
  loads: SpanwiseLoadsResult,
): { traces: unknown[]; annotations: unknown[] } {
  const traces: unknown[] = [];

  for (const surf of loads.surfaces) {
    const sbEntries = [...surf.starboard].sort((a, b) => a.y_m - b.y_m);
    const ptEntries = [...surf.port].sort((a, b) => a.y_m - b.y_m).map((e) => ({ ...e, y_m: -e.y_m }));
    const allEntries = [...ptEntries.reverse(), ...sbEntries];
    const ys = allEntries.map((e) => e.y_m);
    const shears = allEntries.map((e) => e.shear_N);
    const bms = allEntries.map((e) => e.bending_moment_Nm);

    traces.push({
      x: ys,
      y: shears,
      type: "scatter",
      mode: "lines",
      name: `V(y) — ${surf.surface_name}`,
      line: { color: "#FF8400", width: 2 },
      yaxis: "y",
    });
    traces.push({
      x: ys,
      y: bms,
      type: "scatter",
      mode: "lines",
      name: `M(y) — ${surf.surface_name}`,
      line: { color: "#3B82F6", width: 2 },
      yaxis: "y2",
    });
  }

  // Root BM annotation from the first surface (main wing)
  const mainSurf = loads.surfaces[0];
  const annotations: unknown[] = [];
  if (mainSurf) {
    const rootBm = mainSurf.root_bending_moment_Nm_starboard;
    const rootShear = mainSurf.root_shear_N_starboard;
    // Anchor the root annotations at the innermost plotted strip rather than
    // x=0 — surfaces that don't reach the centreline (e.g. boom-mounted tail)
    // would otherwise have the arrow point off-chart into blank space.
    const innerX = mainSurf.starboard.length
      ? Math.min(...mainSurf.starboard.map((p) => p.y_m))
      : 0.0;
    annotations.push({
      x: innerX,
      y: rootBm,
      xref: "x",
      yref: "y2",
      text: `Root BM: ${rootBm.toFixed(0)} N·m`,
      showarrow: true,
      arrowhead: 2,
      arrowcolor: "#3B82F6",
      font: { color: "#3B82F6", family: "JetBrains Mono, monospace", size: 11 },
      bgcolor: "rgba(0,0,0,0.5)",
      bordercolor: "#3B82F6",
      borderwidth: 1,
    });
    annotations.push({
      x: innerX,
      y: rootShear,
      xref: "x",
      yref: "y",
      text: `Root V: ${rootShear.toFixed(0)} N`,
      showarrow: true,
      arrowhead: 2,
      arrowcolor: "#FF8400",
      font: { color: "#FF8400", family: "JetBrains Mono, monospace", size: 11 },
      bgcolor: "rgba(0,0,0,0.5)",
      bordercolor: "#FF8400",
      borderwidth: 1,
    });
  }
  // Compute-parameter annotation (per project convention: inputs inside figure)
  annotations.push({
    x: 0.01,
    y: 0.98,
    xref: "paper",
    yref: "paper",
    xanchor: "left",
    yanchor: "top",
    showarrow: false,
    align: "left",
    font: { color: "#71717A", family: "JetBrains Mono, monospace", size: 10 },
    text: buildSpanwiseLoadsAnnotationText(loads),
  });

  return { traces, annotations };
}

function SpanwiseLoadsChart({
  loads,
}: Readonly<{ loads: SpanwiseLoadsResult }>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || loads.surfaces.length === 0) return;
    let disposed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const { traces, annotations } = buildSpanwiseLoadsTracesAndAnnotations(loads);

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
        margin: { l: 60, r: 60, t: 30, b: 45 },
        xaxis: {
          title: { text: "Y [m]", font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        yaxis: {
          title: { text: "Shear V(y) [N]", font: { size: 11, color: "#FF8400" } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
          tickfont: { color: "#FF8400" },
        },
        yaxis2: {
          title: { text: "Bending Moment M(y) [N·m]", font: { size: 11, color: "#3B82F6" } },
          overlaying: "y",
          side: "right",
          gridcolor: "transparent",
          zerolinecolor: "#3F3F46",
          tickfont: { color: "#3B82F6" },
        },
        legend: {
          x: 0.98,
          y: 0.98,
          xanchor: "right",
          yanchor: "top",
          bgcolor: "rgba(0,0,0,0.4)",
          bordercolor: "#3F3F46",
          borderwidth: 1,
          font: { size: 10, color: "#A1A1AA" },
        },
        showlegend: true,
        autosize: true,
        annotations,
      };

      await PlotlyRef.react(node, traces, layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [loads]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-card-muted">
      <div ref={containerRef} className="min-h-0 flex-1" />
    </div>
  );
}

/** Tab content for the Spanwise Loads tab (gh-1002, gh-1008). Exported for unit testing. */
export function SpanwiseLoadsTabContent({
  spanwiseLoadsLoading,
  spanwiseLoads,
  aeroplaneId,
}: Readonly<{
  spanwiseLoadsLoading?: boolean;
  spanwiseLoads?: SpanwiseLoadsResult | null;
  aeroplaneId?: string | null;
}>) {
  const { result: sizingResult, isRunning: sizingRunning, error: sizingError, run: runSizing } =
    useSparSizing(aeroplaneId ?? null);

  // gh-1050: buildable two-spar plan + preview→commit insert into the wing.
  const { plan, run: runPlan, insert: insertPlan } = useSparPlan(aeroplaneId ?? null);
  const { mutate } = useSWRConfig();
  // Remember the sizing inputs the user last computed with so the plan + insert
  // reuse the SAME material / safety / packing / sigma knobs.
  const lastSizingParamsRef = useRef<SparPlanParams | null>(null);

  // g_limit comes from the first spar sizing result (after first compute)
  const firstSizing = sizingResult?.spar_sizing?.[0] ?? null;
  const gLimit = firstSizing?.g_limit ?? null;
  const gLimitFallback = firstSizing?.g_limit_fallback ?? false;
  // The wing the plan/insert targets — the first surface (main wing).
  const planWingName = spanwiseLoads?.surfaces?.[0]?.surface_name ?? null;

  const handleSparCompute = (inputs: SparSizingInputs) => {
    if (!spanwiseLoads) return;
    const sizingParams = toSizingParams(inputs);
    if (!sizingParams) return;
    // Use the SAME op that produced the displayed loads so the spar is sized on
    // the same M(y). beta matters (sideslip changes the spanwise lift
    // distribution); xyz_ref does NOT (root bending moment is referenced to the
    // wing root via |Yle|, and cl(y) is independent of the moment ref point).
    const opParams = {
      velocity: spanwiseLoads.velocity_mps,
      alpha: spanwiseLoads.alpha,
      beta: spanwiseLoads.beta,
      altitude: spanwiseLoads.altitude_m,
      xyz_ref: [0, 0, 0],
    };
    runSizing(opParams, sizingParams);

    // gh-1050: also compute the buildable plan from the SAME inputs. The
    // moments distribution comes from the already-displayed spanwise loads
    // M(y) — normalised to a 0..1 span fraction (buildMomentsFromLoads).
    const moments = buildMomentsFromLoads(spanwiseLoads);
    if (moments) {
      const planParams: SparPlanParams = {
        material_id: sizingParams.material_id,
        moments,
        wing_name: planWingName,
        safety_factor_j: sizingParams.safety_factor_j,
        packing_factor: sizingParams.packing_factor,
        sigma_allow_mpa_override: sizingParams.sigma_allow_mpa_override ?? null,
      };
      lastSizingParamsRef.current = planParams;
      runPlan(planParams);
    }
  };

  const handleInsert = useCallback(
    (dryRun: boolean) => {
      const params = lastSizingParamsRef.current;
      if (!params) {
        return Promise.reject(new Error("Compute the spar plan first"));
      }
      return insertPlan(params, dryRun);
    },
    [insertPlan],
  );

  const handleSparInserted = useCallback(() => {
    // Refresh the wing construction so the new spares show in the tree / CAD.
    if (!aeroplaneId || !planWingName) return;
    mutate(`/aeroplanes/${aeroplaneId}/wings/${planWingName}/wingconfig`);
    mutate(`/aeroplanes/${aeroplaneId}/wings/${planWingName}`);
  }, [aeroplaneId, planWingName, mutate]);

  if (spanwiseLoadsLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div
          className="flex items-center gap-2 text-muted-foreground"
          data-testid="spanwise-loads-spinner"
        >
          <Loader2 size={14} className="animate-spin" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px]">
            Computing spanwise loads…
          </span>
        </div>
      </div>
    );
  }
  if ((spanwiseLoads?.surfaces.length ?? 0) > 0) {
    return (
      <div className="flex flex-1 flex-col gap-4">
        <SpanwiseLoadsChart loads={spanwiseLoads!} />
        {/* gh-1008: Spar Sizing collapsible panel below the V/M chart */}
        <SparSizingPanel
          sizingResults={sizingResult?.spar_sizing ?? null}
          isRunning={sizingRunning}
          error={sizingError}
          onCompute={handleSparCompute}
          gLimit={gLimit}
          gLimitFallback={gLimitFallback}
          plan={plan}
          onInsert={handleInsert}
          onSparInserted={handleSparInserted}
        />
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
        Run an analysis to see the spanwise load distribution
      </span>
      <span className="text-[12px] text-subtle-foreground">
        Configure parameters and click &quot;Configure &amp; Run&quot;
      </span>
    </div>
  );
}

// -- Streamlines Tab -------------------------------------------------------

function StreamlinesTabContent({
  streamlinesLoading,
  streamlinesFigure,
}: Readonly<{
  streamlinesLoading?: boolean;
  streamlinesFigure?: unknown;
}>) {
  if (streamlinesLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
          Computing streamlines...
        </span>
      </div>
    );
  }
  if (streamlinesFigure) {
    return <StreamlinesRenderer figure={streamlinesFigure} />;
  }
  return (
    <div className="flex flex-1 items-center justify-center">
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
        Run an analysis to see streamlines
      </span>
    </div>
  );
}

// -- Main Component -------------------------------------------------------

export function AnalysisViewerPanel({
  result,
  speedPolar,
  aeroplaneId,
  lastRunTime: _lastRunTime,
  lastRunDurationMs: _lastRunDurationMs,
  stripForces,
  stripForcesLoading,
  spanwiseLoads,
  spanwiseLoadsLoading,
  streamlinesFigure,
  streamlinesLoading,
  activeTab,
  onTabChange,
  onConfigureClick,
  onEditAvlGeometry,
  showAvlGeometryButton,
  wingXSecs,
  wingSymmetric,
  assumptionsSlot,
  hasWings = true,
  envelope,
  isComputingEnvelope,
  envelopeError,
  onComputeEnvelope,
  operatingPoints,
  streamingOperatingPoints,
  isLoadingOps,
  isGeneratingOps,
  isTrimmingOps,
  opsError,
  onGenerateOps,
  onTrimWithAvl,
  onTrimWithAerobuildup,
  controlSurfaces,
  onUpdateDeflections,
  onDeleteOp,
  onDeleteAllOps,
  onCreateOp,
  analysisStatus,
}: Readonly<Props>) {
  const [maximizedChart, setMaximizedChart] = useState<string | null>(null);

  function toggleChart(id: string) {
    setMaximizedChart((prev) => (prev === id ? null : id));
  }

  const COMPUTATION_TABS = new Set<Tab>([
    "Polar",
    "Trefftz Plane",
    "Streamlines",
    "Envelope",
    "Operating Points",
    "Sizing",
  ]);
  const showWingGate = !hasWings && COMPUTATION_TABS.has(activeTab);

  const charts = useMemo(() => derivePolarCharts(result), [result]);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Aerodynamic Analysis
        </span>
        <div className="flex-1" />
        {activeTab !== "Assumptions" && activeTab !== "Envelope" && onConfigureClick && (
          <button
            onClick={onConfigureClick}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
          >
            <Settings size={12} />
            Configure & Run
          </button>
        )}
        {activeTab !== "Assumptions" && activeTab !== "Envelope" && showAvlGeometryButton && onEditAvlGeometry && (
          <button
            onClick={onEditAvlGeometry}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
          >
            <Settings size={12} />
            Edit AVL Geometry
          </button>
        )}
        <div className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={`rounded-full px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
                tab === activeTab
                  ? "bg-primary text-primary-foreground"
                  : "bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        {analysisStatus && <AnalysisStatusIndicator status={analysisStatus} />}
      </div>

      {/* Tab Body */}
      {activeTab === "Assumptions" && (
        <div className="flex flex-1 flex-col overflow-auto bg-card-muted p-6">
          {assumptionsSlot}
        </div>
      )}

      {showWingGate && (
        <div className="flex flex-1 items-center justify-center bg-card-muted">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Add a wing to enable aerodynamic analysis
          </span>
        </div>
      )}

      {!showWingGate && activeTab === "Polar" && (
        <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
          {charts ? (
            (() => {
              // Degenerate sweep: coefficients all non-finite -> null (gh-815).
              // Surface it instead of rendering blank charts (gh-819).
              if (!polarHasFiniteData(charts)) {
                return (
                  <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
                    <AlertTriangle size={28} className="text-primary" />
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
                      Analysis produced no valid results
                    </span>
                    <span className="max-w-md text-[12px] text-subtle-foreground">
                      All coefficients are non-finite (NaN/Inf) for this sweep —
                      usually a sign of degenerate geometry, e.g. a zero-volume
                      fuselage from an incomplete import. Check the imported model
                      and re-run.
                    </span>
                  </div>
                );
              }
              const allCharts = [
                {
                  id: "cl",
                  xData: charts.alpha,
                  yData: charts.CL,
                  xLabel: "\u03B1 [\u00B0]",
                  yLabel: "C_L",
                  title: "C_L vs \u03B1",
                  annotation: `C_L,max \u2248 ${safeToFixed(charts.clMax, 2)} @ ${safeToFixed(charts.alphaClMax, 0)}\u00B0`,
                  color: "#FF8400",
                  extraTraces: [buildAnalysisPolarMarkerTrace("cl", charts)].filter(Boolean) as PlotlyTrace[],
                },
                {
                  id: "cd",
                  xData: charts.alpha,
                  yData: charts.CD,
                  xLabel: "\u03B1 [\u00B0]",
                  yLabel: "C_D",
                  title: "C_D vs \u03B1",
                  color: "#E5484D",
                },
                {
                  id: "ld",
                  xData: charts.alpha,
                  yData: charts.clOverCd,
                  xLabel: "\u03B1 [\u00B0]",
                  yLabel: "C_L / C_D",
                  title: "C_L / C_D vs \u03B1",
                  annotation: `L/D,max \u2248 ${safeToFixed(charts.ldMax, 1)} @ ${safeToFixed(charts.alphaLdMax, 0)}\u00B0`,
                  color: "#30A46C",
                  extraTraces: [buildAnalysisPolarMarkerTrace("ld", charts)].filter(Boolean) as PlotlyTrace[],
                },
                {
                  id: "polar",
                  xData: charts.CD,
                  yData: charts.CL,
                  xLabel: "C_D",
                  yLabel: "C_L",
                  title: "C_L vs C_D (drag polar)",
                  color: "#FF8400",
                  xFormat: (v: number) => v.toFixed(3),
                },
                ...(charts.Cm
                  ? [
                      {
                        id: "cm",
                        xData: charts.alpha,
                        yData: charts.Cm,
                        xLabel: "\u03B1 [\u00B0]",
                        yLabel: "C_m",
                        title: "C_m vs \u03B1",
                        color: "#A78BFA",
                      },
                    ]
                  : []),
              ];
              if (maximizedChart) {
                const chart = allCharts.find((c) => c.id === maximizedChart);
                if (!chart) return null;
                return (
                  <div className="flex flex-1">
                    <PlotlyChart
                      {...chart}
                      onToggleMaximize={() => toggleChart(chart.id)}
                      isMaximized
                    />
                  </div>
                );
              }
              return (
                <div className="flex flex-col gap-4">
                  <div className="grid grid-cols-3 gap-4">
                    {allCharts.slice(0, 3).map((c) => (
                      <PlotlyChart
                        key={c.id}
                        {...c}
                        onToggleMaximize={() => toggleChart(c.id)}
                      />
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {allCharts.slice(3).map((c) => (
                      <PlotlyChart
                        key={c.id}
                        {...c}
                        onToggleMaximize={() => toggleChart(c.id)}
                      />
                    ))}
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
                Run an analysis to see results
              </span>
              <span className="text-[12px] text-subtle-foreground">
                Configure parameters on the right and click {"\u201C"}Run
                Analysis{"\u201D"}
              </span>
            </div>
          )}
          {speedPolar && speedPolar.curves.some((c) => c.V.length > 0) && (
            <SpeedPolarChart speedPolar={speedPolar} />
          )}
        </div>
      )}

      {!showWingGate && activeTab === "Trefftz Plane" && (
        <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
          <TrefftzPlaneTabContent
            stripForcesLoading={stripForcesLoading}
            stripForces={stripForces}
            wingXSecs={wingXSecs}
            wingSymmetric={wingSymmetric}
          />
        </div>
      )}

      {!showWingGate && activeTab === "Spanwise Loads" && (
        <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
          <SpanwiseLoadsTabContent
            spanwiseLoadsLoading={spanwiseLoadsLoading}
            spanwiseLoads={spanwiseLoads}
            aeroplaneId={aeroplaneId}
          />
        </div>
      )}

      {!showWingGate && activeTab === "Streamlines" && (
        <div className="flex flex-1 overflow-hidden bg-card-muted">
          <StreamlinesTabContent
            streamlinesLoading={streamlinesLoading}
            streamlinesFigure={streamlinesFigure}
          />
        </div>
      )}

      {!showWingGate && activeTab === "Envelope" && (
        <EnvelopePanel
          envelope={envelope ?? null}
          isComputing={isComputingEnvelope ?? false}
          error={envelopeError ?? null}
          onCompute={onComputeEnvelope ?? (() => {})}
        />
      )}

      {!showWingGate && activeTab === "Operating Points" && (
        <OperatingPointsPanel
          points={operatingPoints ?? []}
          comparisonPoints={streamingOperatingPoints ?? undefined}
          isLoading={isLoadingOps ?? false}
          isGenerating={isGeneratingOps ?? false}
          isTrimming={isTrimmingOps ?? false}
          error={opsError ?? null}
          onGenerate={onGenerateOps ?? (() => {})}
          onTrimWithAvl={onTrimWithAvl ?? (() => Promise.resolve(null))}
          onTrimWithAerobuildup={onTrimWithAerobuildup ?? (() => Promise.resolve(null))}
          controlSurfaces={controlSurfaces ?? []}
          onUpdateDeflections={onUpdateDeflections ?? (async () => {})}
          onDeleteOp={onDeleteOp}
          onDeleteAll={onDeleteAllOps}
          onCreateOp={onCreateOp}
        />
      )}

      {!showWingGate && activeTab === "Sizing" && aeroplaneId && (
        <MatchingChartTab aeroplaneId={aeroplaneId} />
      )}

      {!showWingGate && activeTab === "Sizing" && !aeroplaneId && (
        <div className="flex flex-1 items-center justify-center bg-card-muted">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Select an aeroplane to show the matching chart
          </span>
        </div>
      )}

    </div>
  );
}
