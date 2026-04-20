"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { Wind, SlidersHorizontal, Activity, Maximize2, Minimize2, Settings } from "lucide-react";
import type { AnalysisResult } from "@/hooks/useAnalysis";
import type { StripForcesResult } from "@/hooks/useStripForces";

const TABS = ["Polar", "Trefftz Plane", "Streamlines"] as const;
export type Tab = (typeof TABS)[number];
export { TABS };

interface Props {
  result: AnalysisResult | null;
  aeroplaneId: string | null;
  lastRunTime?: Date | null;
  lastRunDurationMs?: number | null;
  stripForces?: StripForcesResult | null;
  stripForcesLoading?: boolean;
  streamlinesFigure?: unknown;
  streamlinesLoading?: boolean;
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  onConfigureClick?: () => void;
}

// -- Plotly Chart (dynamic import) ----------------------------------------

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
}: {
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
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || xData.length === 0) return;
    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed || !containerRef.current) return;

      const trace = {
        x: xData,
        y: yData,
        type: "scatter" as const,
        mode: "lines" as const,
        line: { color, width: 2 },
        hovertemplate: `${xLabel}: %{x}<br>${yLabel}: %{y}<extra></extra>`,
      };

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
        margin: { l: 50, r: 15, t: 5, b: 40 },
        xaxis: {
          title: { text: xLabel, font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
          tickformat: xFormat ? undefined : undefined,
        },
        yaxis: {
          title: { text: yLabel, font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        showlegend: false,
        autosize: true,
      };

      // @ts-expect-error -- plotly.js types incomplete for scatter
      await Plotly.react(containerRef.current, [trace], layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
    };
  }, [xData, yData, xLabel, yLabel, color, xFormat]);

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

function StreamlinesRenderer({ figure }: { figure: unknown }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!figure || !containerRef.current) return;
    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed || !containerRef.current) return;

      const figData = figure as {
        data?: unknown[];
        layout?: Record<string, unknown>;
      };
      const sceneFromLayout =
        (figData.layout?.scene as Record<string, unknown>) || {};

      const layout = {
        paper_bgcolor: "#09090B",
        plot_bgcolor: "#09090B",
        font: { color: "#A1A1AA" },
        margin: { l: 0, r: 0, t: 0, b: 0 },
        scene: {
          ...sceneFromLayout,
          bgcolor: "#09090B",
          xaxis: {
            ...((sceneFromLayout.xaxis as object) || {}),
            gridcolor: "#27272A",
            color: "#71717A",
          },
          yaxis: {
            ...((sceneFromLayout.yaxis as object) || {}),
            gridcolor: "#27272A",
            color: "#71717A",
          },
          zaxis: {
            ...((sceneFromLayout.zaxis as object) || {}),
            gridcolor: "#27272A",
            color: "#71717A",
          },
        },
        showlegend: false,
        autosize: true,
      };

      // @ts-expect-error -- plotly types
      await Plotly.react(containerRef.current, figData.data || [], layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      });
    })();

    return () => {
      disposed = true;
    };
  }, [figure]);

  return <div ref={containerRef} className="h-full w-full" />;
}

// -- Main Component -------------------------------------------------------

export function AnalysisViewerPanel({
  result,
  aeroplaneId,
  lastRunTime,
  lastRunDurationMs,
  stripForces,
  stripForcesLoading,
  streamlinesFigure,
  streamlinesLoading,
  activeTab,
  onTabChange,
  onConfigureClick,
}: Props) {
  const [maximizedChart, setMaximizedChart] = useState<string | null>(null);

  function toggleChart(id: string) {
    setMaximizedChart((prev) => (prev === id ? null : id));
  }

  const charts = useMemo(() => {
    if (!result || !result.CL || result.CL.length === 0) return null;

    const { CL, CD, Cm, alpha } = result;
    const clOverCd = CL.map((cl, i) => (CD[i] !== 0 ? cl / CD[i] : 0));

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
          {stripForcesLoading ? (
            <div className="flex flex-1 items-center justify-center">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
                Running AVL strip-force analysis...
              </span>
            </div>
          ) : stripForces && stripForces.surfaces.length > 0 ? (
            (() => {
              const primary = stripForces.surfaces.filter(
                (s) => !s.surface_name.includes("YDUP"),
              );
              const allStrips = primary.flatMap((s) => s.strips);
              if (allStrips.length === 0)
                return (
                  <span className="text-[12px] text-muted-foreground">
                    No strip data
                  </span>
                );

              const ySpan = allStrips.map((s) => s.Yle);
              const cl = allStrips.map((s) => s.cl);
              const cd = allStrips.map((s) => s.cd);
              const cCl = allStrips.map((s) => s.c_cl);
              const cmC4 = allStrips.map((s) => s["cm_c/4"]);
              const ai = allStrips.map((s) => s.ai);
              const xFmt = (v: number) => v.toFixed(2);

              const distCharts = [
                {
                  id: "sf-cl",
                  xData: ySpan,
                  yData: cl,
                  xLabel: "y [m]",
                  yLabel: "Cl",
                  title: "Cl vs span",
                  color: "#FF8400",
                  xFormat: xFmt,
                },
                {
                  id: "sf-ccl",
                  xData: ySpan,
                  yData: cCl,
                  xLabel: "y [m]",
                  yLabel: "c\u00B7Cl",
                  title: "c\u00B7Cl vs span",
                  color: "#30A46C",
                  xFormat: xFmt,
                },
                {
                  id: "sf-cd",
                  xData: ySpan,
                  yData: cd,
                  xLabel: "y [m]",
                  yLabel: "Cd",
                  title: "Cd vs span",
                  color: "#E5484D",
                  xFormat: xFmt,
                },
                {
                  id: "sf-cm",
                  xData: ySpan,
                  yData: cmC4,
                  xLabel: "y [m]",
                  yLabel: "Cm c/4",
                  title: "Cm c/4 vs span",
                  color: "#A78BFA",
                  xFormat: xFmt,
                },
                {
                  id: "sf-ai",
                  xData: ySpan,
                  yData: ai,
                  xLabel: "y [m]",
                  yLabel: "\u03B1i [rad]",
                  title: "Induced AoA vs span",
                  color: "#F59E0B",
                  xFormat: xFmt,
                },
              ];

              if (maximizedChart) {
                const chart = distCharts.find(
                  (c) => c.id === maximizedChart,
                );
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
                    {distCharts.slice(0, 3).map((c) => (
                      <PlotlyChart
                        key={c.id}
                        {...c}
                        onToggleMaximize={() => toggleChart(c.id)}
                      />
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {distCharts.slice(3).map((c) => (
                      <PlotlyChart
                        key={c.id}
                        {...c}
                        onToggleMaximize={() => toggleChart(c.id)}
                      />
                    ))}
                  </div>
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    {"\u03B1"} = {stripForces.alpha.toFixed(1)}{"\u00B0"}{" "}
                    {"\u00B7"} Mach = {stripForces.mach.toFixed(3)}{" "}
                    {"\u00B7"} Sref = {stripForces.sref.toFixed(4)} m{"\u00B2"}{" "}
                    {"\u00B7"}{" "}
                    {primary.map((s) => s.surface_name).join(", ")}
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
                Run an analysis to see strip-force distributions
              </span>
            </div>
          )}
        </div>
      )}

      {activeTab === "Streamlines" && (
        <div className="flex flex-1 overflow-hidden bg-card-muted">
          {streamlinesLoading ? (
            <div className="flex flex-1 items-center justify-center">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
                Computing streamlines...
              </span>
            </div>
          ) : streamlinesFigure ? (
            <StreamlinesRenderer figure={streamlinesFigure} />
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
                Run an analysis to see streamlines
              </span>
            </div>
          )}
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
