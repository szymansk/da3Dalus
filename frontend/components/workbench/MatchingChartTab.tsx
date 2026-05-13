"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, AlertTriangle, Info } from "lucide-react";
import {
  useMatchingChart,
  type AircraftMode,
  type MatchingChartData,
} from "@/hooks/useMatchingChart";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  readonly aeroplaneId: string;
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

function buildDesignPointTrace(data: MatchingChartData): PlotlyTrace {
  const dp = data.design_point;
  const dpColor = data.feasibility === "feasible" ? "#30A46C" : "#E5484D";
  return {
    x: [dp.ws_n_m2],
    y: [dp.t_w],
    type: "scatter",
    mode: "markers",
    name: "Design Point",
    marker: { symbol: "circle", size: 12, color: dpColor, line: { color: "#fff", width: 2 } },
    hovertemplate: (
      `<b>Design Point</b><br>W/S = ${dp.ws_n_m2.toFixed(0)} N/m²<br>` +
      `T/W = ${dp.t_w.toFixed(4)}<br><i>T/W = T_static_SL / W_MTOW</i><extra></extra>`
    ),
  };
}

function buildConstraintTraces(
  ws: number[],
  data: MatchingChartData,
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
    const lineWidth = c.binding ? 3 : 1.5;
    const dash = c.binding ? "solid" : "dot";

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

function buildLayout(ws: number[], data: MatchingChartData) {
  const dp = data.design_point;
  const dpColor = data.feasibility === "feasible" ? "#30A46C" : "#E5484D";
  const allTw = data.constraints.flatMap((c) => c.t_w_points?.filter((v) => isFinite(v)) ?? []);
  const yMax = allTw.length > 0 ? Math.max(...allTw, dp.t_w) * 1.15 : dp.t_w * 2;

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
    annotations: [
      {
        x: 0.01, y: 0.99, xref: "paper", yref: "paper",
        xanchor: "left", yanchor: "top", showarrow: false,
        font: { color: "#52525B", size: 9 },
        text: "Convention: T/W = T_static_SL / W_MTOW · AR held constant",
      },
      {
        x: dp.ws_n_m2, y: dp.t_w, xref: "x", yref: "y",
        text: `  W/S=${dp.ws_n_m2.toFixed(0)}, T/W=${dp.t_w.toFixed(3)}`,
        showarrow: false, xanchor: "left", yanchor: "middle",
        font: { color: dpColor, size: 10 },
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Plotly chart renderer
// ---------------------------------------------------------------------------

function MatchingChartPlot({ data }: Readonly<{ data: MatchingChartData }>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    let disposed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const ws = data.ws_range_n_m2;
      const { traces: constraintTraces, shapes } = buildConstraintTraces(ws, data);
      const allTraces: PlotlyTrace[] = [
        buildHullFill(ws, data),
        ...constraintTraces,
        buildDesignPointTrace(data),
      ];
      const layout = { ...buildLayout(ws, data), shapes };

      await PlotlyRef.react(node, allTraces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [data]);

  return (
    <div className="flex flex-1 flex-col">
      <div ref={containerRef} className="h-full min-h-0 w-full" style={{ height: 340 }} />
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
            Drag to find required S and T for fixed W and AR
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
          <div className="rounded-xl border border-border bg-card p-2">
            <MatchingChartPlot data={data} />
          </div>

          {/* Design point summary */}
          <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-card px-4 py-3">
            <div className="flex flex-col gap-0.5">
              <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                Design Point W/S
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] font-semibold text-foreground">
                {data.design_point.ws_n_m2.toFixed(0)} N/m²
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
                Design Point T/W
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] font-semibold text-foreground">
                {data.design_point.t_w.toFixed(3)}
              </span>
            </div>
            {data.constraints.filter((c) => c.binding).map((c) => (
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
