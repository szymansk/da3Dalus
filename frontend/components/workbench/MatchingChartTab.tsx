"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, AlertTriangle, Info } from "lucide-react";
import {
  useMatchingChart,
  type AircraftMode,
  type MatchingChartData,
  type ConstraintLine,
} from "@/hooks/useMatchingChart";

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
      `T/W = ${t_w.toFixed(4)}<br><i>T/W = T_static_SL / W_MTOW</i><extra></extra>`
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
        text: "Convention: T/W = T_static_SL / W_MTOW · AR held constant",
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

// ---------------------------------------------------------------------------
// Plotly chart renderer with drag support
// ---------------------------------------------------------------------------

interface MatchingChartPlotProps {
  readonly data: MatchingChartData;
  readonly dragPoint: DragPoint | null;
  readonly isDragging: boolean;
  readonly onDragStart: (ws: number, tw: number) => void;
  readonly onDragMove: (ws: number, tw: number) => void;
  readonly onDragEnd: () => void;
}

function MatchingChartPlot({
  data,
  dragPoint,
  isDragging,
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
  }, [data, displayDp.ws_n_m2, displayDp.t_w, isDragging, dragBindingName]);

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
}

function DesignPointSummary({ data, isDragging, displayDp, liveDragBinding }: DesignPointSummaryProps) {
  const activeColor = isDragging ? "#FF8400" : undefined;

  return (
    <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-card px-4 py-3">
      <div className="flex flex-col gap-0.5">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          {isDragging ? "Drag W/S" : "Design Point W/S"}
        </span>
        <span
          className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] font-semibold"
          style={{ color: activeColor }}
          data-testid="dp-ws"
        >
          {displayDp ? `${displayDp.ws_n_m2.toFixed(0)} N/m²` : "—"}
        </span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          {isDragging ? "Drag T/W" : "Design Point T/W"}
        </span>
        <span
          className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] font-semibold"
          style={{ color: activeColor }}
          data-testid="dp-tw"
        >
          {displayDp ? displayDp.t_w.toFixed(3) : "—"}
        </span>
      </div>
      {isDragging && liveDragBinding && (
        <div className="flex flex-col gap-0.5">
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Binding
          </span>
          <span
            className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold"
            style={{ color: data.constraints.find((c) => c.name === liveDragBinding)?.color ?? "#FF8400" }}
            data-testid="drag-binding"
          >
            {liveDragBinding}
          </span>
        </div>
      )}
      {!isDragging && data.constraints.filter((c) => c.binding).map((c) => (
        <div key={c.name} className="flex flex-col gap-0.5">
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Binding
          </span>
          <span
            className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold"
            style={{ color: c.color }}
          >
            {c.name}
          </span>
        </div>
      ))}
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

/** Internal component that owns drag state for a given snapshot of chart data.
 * Rendered with key={data.design_point.ws_n_m2 + data.design_point.t_w} so that
 * when fresh server data arrives the drag state resets automatically via re-mount.
 */
function MatchingChartContent({ data }: Readonly<{ data: MatchingChartData }>) {
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
      <div className="rounded-xl border border-border bg-card p-2">
        <MatchingChartPlot
          data={data}
          dragPoint={dragPoint}
          isDragging={isDragging}
          onDragStart={handleDragStart}
          onDragMove={handleDragMove}
          onDragEnd={handleDragEnd}
        />
      </div>
      <DesignPointSummary
        data={data}
        isDragging={isDragging}
        displayDp={displayDp}
        liveDragBinding={liveDragBinding}
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

        <div className="ml-auto flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <Info size={11} />
          <span className="font-[family-name:var(--font-geist-sans)]">
            Drag design point to explore required S and T for fixed W and AR
          </span>
        </div>
      </div>

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
          <MatchingChartContent key={contentKey} data={data} />

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
