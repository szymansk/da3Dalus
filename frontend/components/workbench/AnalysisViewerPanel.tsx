"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { Wind, SlidersHorizontal, Activity, Maximize2, Minimize2, Settings } from "lucide-react";
import type { AnalysisResult } from "@/hooks/useAnalysis";
import type { StripForcesResult } from "@/hooks/useStripForces";

const TABS = ["Polar", "Trefftz Plane", "Streamlines"] as const;
export type Tab = (typeof TABS)[number];
export { TABS };

interface WingXSec {
  readonly xyz_le: readonly number[];
  readonly chord: number;
}

interface Props {
  readonly result: AnalysisResult | null;
  readonly aeroplaneId: string | null;
  readonly lastRunTime?: Date | null;
  readonly lastRunDurationMs?: number | null;
  readonly stripForces?: StripForcesResult | null;
  readonly stripForcesLoading?: boolean;
  readonly streamlinesFigure?: unknown;
  readonly streamlinesLoading?: boolean;
  readonly activeTab: Tab;
  readonly onTabChange: (tab: Tab) => void;
  readonly onConfigureClick?: () => void;
  readonly wingXSecs?: WingXSec[] | null;
  readonly wingSymmetric?: boolean;
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
  xData: number[];
  yData: number[];
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
    if (!containerRef.current || xData.length === 0) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !containerRef.current) return;

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
      if (shapes && shapes.length > 0) {
        layout.shapes = shapes;
      }

      await PlotlyRef.react(containerRef.current, allTraces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (containerRef.current && PlotlyRef) PlotlyRef.purge(containerRef.current);
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

// -- Streamlines Renderer -------------------------------------------------

function StreamlinesRenderer({ figure }: Readonly<{ figure: unknown }>) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!figure || !containerRef.current) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !containerRef.current) return;

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

      await PlotlyRef.react(containerRef.current, figData.data || [], layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      });
    })();

    return () => {
      disposed = true;
      if (containerRef.current && PlotlyRef) PlotlyRef.purge(containerRef.current);
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
    const baseName = surface.surface_name.replace(/\s*\(YDUP\)$/, "");
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
    if (!containerRef.current || stripForces.surfaces.length === 0) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !containerRef.current) return;

      const surfaceGroups = groupSurfaceStrips(stripForces.surfaces);
      const traces: PlotlyTrace[] = buildSurfaceTraces(surfaceGroups);

      if (wingXSecs && wingXSecs.length > 0) {
        traces.push(buildSegmentMarkerTrace(wingXSecs, wingSymmetric));
      }

      const shapes: PlotlyShape[] = [];
      const annotations = [{
        x: 0.01, y: 0.98, xref: "paper", yref: "paper",
        xanchor: "left", yanchor: "top", showarrow: false,
        font: { color: "#71717A", family: "JetBrains Mono, monospace", size: 10 },
        text: [
          `\u03B1 = ${stripForces.alpha.toFixed(2)}\u00B0`,
          `Mach = ${stripForces.mach.toFixed(3)}`,
          `Sref = ${stripForces.sref.toFixed(4)} m\u00B2`,
          `Cref = ${stripForces.cref.toFixed(4)} m`,
          `Bref = ${stripForces.bref.toFixed(4)} m`,
        ].join("  \u00B7  "),
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

      await PlotlyRef.react(containerRef.current, traces, layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"] as string[],
      });
    })();

    return () => {
      disposed = true;
      if (containerRef.current && PlotlyRef) PlotlyRef.purge(containerRef.current);
    };
  }, [stripForces, wingXSecs, wingSymmetric]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-card-muted">
      <div ref={containerRef} className="min-h-0 flex-1" />
    </div>
  );
}

// -- Tab Content Helpers --------------------------------------------------

function TrefftzPlaneTabContent({
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
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
          Running AVL strip-force analysis...
        </span>
      </div>
    );
  }
  if (stripForces && stripForces.surfaces.length > 0) {
    return (
      <TrefftzPlaneChart
        stripForces={stripForces}
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
  aeroplaneId: _aeroplaneId,
  lastRunTime,
  lastRunDurationMs,
  stripForces,
  stripForcesLoading,
  streamlinesFigure,
  streamlinesLoading,
  activeTab,
  onTabChange,
  onConfigureClick,
  wingXSecs,
  wingSymmetric,
}: Readonly<Props>) {
  const [maximizedChart, setMaximizedChart] = useState<string | null>(null);

  function toggleChart(id: string) {
    setMaximizedChart((prev) => (prev === id ? null : id));
  }

  const charts = useMemo(() => {
    if (!result || !result.CL || result.CL.length === 0) return null;

    const { CL, CD, Cm, alpha } = result;
    const clOverCd = CL.map((cl, i) => (CD[i] === 0 ? 0 : cl / CD[i]));

    const maxCLIdx = CL.indexOf(Math.max(...CL));
    const maxLDIdx = clOverCd.indexOf(Math.max(...clOverCd));

    return {
      alpha,
      CL,
      CD,
      Cm: Cm.length > 0 ? Cm : null,
      clOverCd,
      clMax: CL[maxCLIdx],
      alphaClMax: alpha[maxCLIdx],
      ldMax: clOverCd[maxLDIdx],
      alphaLdMax: alpha[maxLDIdx],
    };
  }, [result]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-border">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Aerodynamic Analysis
        </span>
        <div className="flex-1" />
        {onConfigureClick && (
          <button
            onClick={onConfigureClick}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
          >
            <Settings size={12} />
            Configure & Run
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
      </div>

      {/* Tab Body */}
      {activeTab === "Polar" && (
        <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
          {charts ? (
            (() => {
              const allCharts = [
                {
                  id: "cl",
                  xData: charts.alpha,
                  yData: charts.CL,
                  xLabel: "\u03B1 [\u00B0]",
                  yLabel: "C_L",
                  title: "C_L vs \u03B1",
                  annotation: `C_L,max \u2248 ${charts.clMax.toFixed(2)} @ ${charts.alphaClMax.toFixed(0)}\u00B0`,
                  color: "#FF8400",
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
                  annotation: `L/D,max \u2248 ${charts.ldMax.toFixed(1)} @ ${charts.alphaLdMax.toFixed(0)}\u00B0`,
                  color: "#30A46C",
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
        </div>
      )}

      {activeTab === "Trefftz Plane" && (
        <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
          <TrefftzPlaneTabContent
            stripForcesLoading={stripForcesLoading}
            stripForces={stripForces}
            wingXSecs={wingXSecs}
            wingSymmetric={wingSymmetric}
          />
        </div>
      )}

      {activeTab === "Streamlines" && (
        <div className="flex flex-1 overflow-hidden bg-card-muted">
          <StreamlinesTabContent
            streamlinesLoading={streamlinesLoading}
            streamlinesFigure={streamlinesFigure}
          />
        </div>
      )}

      {/* Info Chip Row */}
      <div className="flex items-center gap-2 border-t border-border bg-card px-4 py-3">
        <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
          <Wind size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Flight profile: cruise
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
          <SlidersHorizontal size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Trim: elevator {"\u2212"}2.1{"\u00B0"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
          <Activity size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Re {"\u2248"} 4.2e5
          </span>
        </div>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
          {charts ? `${charts.alpha.length} points` : "No data"}
          {lastRunTime && lastRunDurationMs != null && (
            <>
              {" "}
              {"\u00B7"} Last run:{" "}
              {lastRunTime.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                hour12: false,
              })}{" "}
              {"\u00B7"} {lastRunDurationMs} ms
            </>
          )}
        </span>
      </div>
    </div>
  );
}
