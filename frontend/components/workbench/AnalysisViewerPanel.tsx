"use client";

import { useState, useMemo } from "react";
import { Wind, SlidersHorizontal, Activity, Maximize2, Minimize2 } from "lucide-react";
import type { AnalysisResult } from "@/hooks/useAnalysis";
import { StreamlinesViewer } from "@/components/workbench/StreamlinesViewer";

const TABS = ["Polar", "Three-View", "Streamlines", "Diagrams"] as const;
type Tab = (typeof TABS)[number];

interface Props {
  result: AnalysisResult | null;
  aeroplaneId: string | null;
  lastRunTime?: Date | null;
  lastRunDurationMs?: number | null;
}

// ── SVG Line Chart ──────────────────────────────────────────────

function LineChart({
  xData,
  yData,
  xLabel,
  yLabel,
  title,
  annotation,
  color = "var(--color-primary)",
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
  const W = 400;
  const H = 200;
  const PAD = { top: 10, right: 15, bottom: 30, left: 45 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  if (xData.length === 0 || yData.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-[--radius-s] border border-border bg-card p-4">
        <span className="text-[12px] text-muted-foreground">No data</span>
      </div>
    );
  }

  const xMin = Math.min(...xData);
  const xMax = Math.max(...xData);
  const yMin = Math.min(...yData);
  const yMax = Math.max(...yData);
  const xRange = xMax - xMin || 1;
  const yRange = yMax - yMin || 1;

  function sx(v: number) { return PAD.left + ((v - xMin) / xRange) * plotW; }
  function sy(v: number) { return PAD.top + plotH - ((v - yMin) / yRange) * plotH; }

  const pathD = xData.map((x, i) => `${i === 0 ? "M" : "L"}${sx(x).toFixed(1)},${sy(yData[i]).toFixed(1)}`).join(" ");

  // Y-axis ticks (5 ticks)
  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);
  // X-axis ticks (5 ticks)
  const xTicks = Array.from({ length: 5 }, (_, i) => xMin + (xRange * i) / 4);

  return (
    <div className="group/chart flex flex-1 flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">{title}</span>
        {annotation && (
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">{annotation}</span>
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
      <div className="rounded-[--radius-s] border border-border bg-card p-2">
        <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {yTicks.map((v, i) => (
            <line key={`yg${i}`} x1={PAD.left} x2={W - PAD.right} y1={sy(v)} y2={sy(v)}
              stroke="var(--color-border)" strokeWidth="0.5" />
          ))}
          {xTicks.map((v, i) => (
            <line key={`xg${i}`} x1={sx(v)} x2={sx(v)} y1={PAD.top} y2={PAD.top + plotH}
              stroke="var(--color-border)" strokeWidth="0.5" />
          ))}

          {/* Axes */}
          <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + plotH}
            stroke="var(--color-muted-foreground)" strokeWidth="1" />
          <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH} y2={PAD.top + plotH}
            stroke="var(--color-muted-foreground)" strokeWidth="1" />

          {/* Y-axis labels */}
          {yTicks.map((v, i) => (
            <text key={`yl${i}`} x={PAD.left - 5} y={sy(v) + 3}
              textAnchor="end" fontSize="8" fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)">
              {v.toFixed(2)}
            </text>
          ))}

          {/* X-axis labels */}
          {xTicks.map((v, i) => (
            <text key={`xl${i}`} x={sx(v)} y={PAD.top + plotH + 14}
              textAnchor="middle" fontSize="8" fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)">
              {xFormat ? xFormat(v) : `${v.toFixed(0)}°`}
            </text>
          ))}

          {/* Axis titles */}
          <text x={W / 2} y={H - 3} textAnchor="middle" fontSize="9"
            fill="var(--color-muted-foreground)" fontFamily="var(--font-jetbrains-mono)">
            {xLabel}
          </text>
          <text x={12} y={H / 2} textAnchor="middle" fontSize="9"
            fill="var(--color-muted-foreground)" fontFamily="var(--font-jetbrains-mono)"
            transform={`rotate(-90, 12, ${H / 2})`}>
            {yLabel}
          </text>

          {/* Data line */}
          <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────

export function AnalysisViewerPanel({ result, aeroplaneId, lastRunTime, lastRunDurationMs }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("Polar");
  const [maximizedChart, setMaximizedChart] = useState<string | null>(null);

  function toggleChart(id: string) {
    setMaximizedChart((prev) => (prev === id ? null : id));
  }

  const charts = useMemo(() => {
    if (!result || !result.CL || result.CL.length === 0) return null;

    const { CL, CD, Cm, alpha } = result;
    const clOverCd = CL.map((cl, i) => CD[i] !== 0 ? cl / CD[i] : 0);

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
    <div className="flex flex-1 flex-col overflow-hidden rounded-[--radius-m] border border-border">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Aerodynamic Analysis
        </span>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-[--radius-pill] px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
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
                { id: "cl", xData: charts.alpha, yData: charts.CL, xLabel: "α [°]", yLabel: "C_L", title: "C_L vs α", annotation: `C_L,max ≈ ${charts.clMax.toFixed(2)} @ ${charts.alphaClMax.toFixed(0)}°`, color: "var(--color-primary)" },
                { id: "cd", xData: charts.alpha, yData: charts.CD, xLabel: "α [°]", yLabel: "C_D", title: "C_D vs α", color: "var(--color-destructive)" },
                { id: "ld", xData: charts.alpha, yData: charts.clOverCd, xLabel: "α [°]", yLabel: "C_L / C_D", title: "C_L / C_D vs α", annotation: `L/D,max ≈ ${charts.ldMax.toFixed(1)} @ ${charts.alphaLdMax.toFixed(0)}°`, color: "var(--color-success)" },
                { id: "polar", xData: charts.CD, yData: charts.CL, xLabel: "C_D", yLabel: "C_L", title: "C_L vs C_D (drag polar)", color: "var(--color-primary)", xFormat: (v: number) => v.toFixed(3) },
                ...(charts.Cm ? [{ id: "cm", xData: charts.alpha, yData: charts.Cm, xLabel: "α [°]", yLabel: "C_m", title: "C_m vs α", color: "#A78BFA" }] : []),
              ];
              if (maximizedChart) {
                const chart = allCharts.find((c) => c.id === maximizedChart);
                if (!chart) return null;
                return (
                  <div className="flex flex-1">
                    <LineChart {...chart} onToggleMaximize={() => toggleChart(chart.id)} isMaximized />
                  </div>
                );
              }
              return (
                <div className="flex flex-col gap-4">
                  <div className="grid grid-cols-3 gap-4">
                    {allCharts.slice(0, 3).map((c) => (
                      <LineChart key={c.id} {...c} onToggleMaximize={() => toggleChart(c.id)} />
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {allCharts.slice(3).map((c) => (
                      <LineChart key={c.id} {...c} onToggleMaximize={() => toggleChart(c.id)} />
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
                Configure parameters on the right and click &ldquo;Run Analysis&rdquo;
              </span>
            </div>
          )}
        </div>
      )}
      {activeTab === "Streamlines" && (
        <StreamlinesViewer aeroplaneId={aeroplaneId} />
      )}
      {activeTab === "Three-View" && (
        <div className="flex flex-1 items-center justify-center bg-card-muted">
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-muted-foreground">
            Coming soon
          </span>
        </div>
      )}
      {activeTab === "Diagrams" && (
        <div className="flex flex-1 items-center justify-center bg-card-muted">
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-muted-foreground">
            Coming soon
          </span>
        </div>
      )}

      {/* Info Chip Row */}
      <div className="flex items-center gap-2 border-t border-border bg-card px-4 py-3">
        <div className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted px-3 py-1.5">
          <Wind size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Flight profile: cruise
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted px-3 py-1.5">
          <SlidersHorizontal size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Trim: elevator &minus;2.1&deg;
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted px-3 py-1.5">
          <Activity size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Re &asymp; 4.2e5
          </span>
        </div>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
          {charts ? `${charts.alpha.length} points` : "No data"}
          {lastRunTime && lastRunDurationMs != null && (
            <> &middot; Last run: {lastRunTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })} &middot; {lastRunDurationMs} ms</>
          )}
        </span>
      </div>
    </div>
  );
}
