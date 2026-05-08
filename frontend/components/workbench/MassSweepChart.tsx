"use client";

import { useRef, useEffect } from "react";
import type { MassSweepPoint } from "@/hooks/useMassSweep";

interface Props {
  readonly points: MassSweepPoint[];
  readonly currentMassKg: number | null;
}

export function MassSweepChart({ points, currentMassKg }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || points.length === 0) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const masses = points.map((p) => p.mass_kg);
      const firstNegIdx = points.findIndex((p) => p.cl_margin < 0);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const traces: Record<string, any>[] = [
        {
          x: masses,
          y: points.map((p) => p.stall_speed_ms),
          type: "scatter",
          mode: "lines",
          name: "Stall Speed",
          line: { color: "#E5484D", width: 2 },
          hovertemplate: "Mass: %{x:.1f} kg<br>V_stall: %{y:.1f} m/s<extra></extra>",
        },
        {
          x: masses,
          y: points.map((p) => p.wing_loading_pa),
          type: "scatter",
          mode: "lines",
          name: "Wing Loading",
          line: { color: "#FF8400", width: 2 },
          hovertemplate: "Mass: %{x:.1f} kg<br>W/S: %{y:.1f} Pa<extra></extra>",
        },
        {
          x: masses,
          y: points.map((p) => p.cl_margin),
          type: "scatter",
          mode: "lines",
          name: "CL Margin",
          yaxis: "y2",
          line: { color: "#30A46C", width: 2 },
          hovertemplate: "Mass: %{x:.1f} kg<br>CL margin: %{y:.2f}<extra></extra>",
        },
      ];

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const shapes: Record<string, any>[] = [];

      // Infeasible region (CL margin < 0)
      if (firstNegIdx !== -1) {
        const xStart = firstNegIdx > 0
          ? masses[firstNegIdx - 1] + (masses[firstNegIdx] - masses[firstNegIdx - 1]) *
            (points[firstNegIdx - 1].cl_margin / (points[firstNegIdx - 1].cl_margin - points[firstNegIdx].cl_margin))
          : masses[firstNegIdx];
        shapes.push({
          type: "rect",
          x0: xStart,
          x1: masses[masses.length - 1],
          y0: 0,
          y1: 1,
          yref: "paper",
          fillcolor: "rgba(229, 72, 77, 0.08)",
          line: { width: 0 },
        });
      }

      // Current mass marker
      if (currentMassKg !== null && currentMassKg > 0) {
        shapes.push({
          type: "line",
          x0: currentMassKg,
          x1: currentMassKg,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: { color: "#A78BFA", width: 2, dash: "dash" },
        });
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const annotations: Record<string, any>[] = [];
      if (currentMassKg !== null && currentMassKg > 0) {
        annotations.push({
          x: currentMassKg,
          y: 1.02,
          yref: "paper" as const,
          text: `m = ${currentMassKg.toFixed(1)} kg`,
          showarrow: false,
          font: { size: 10, color: "#A78BFA", family: "JetBrains Mono, monospace" },
        });
      }
      if (firstNegIdx !== -1) {
        annotations.push({
          x: masses[masses.length - 1],
          y: 0.95,
          yref: "paper" as const,
          xanchor: "right" as const,
          text: "Infeasible",
          showarrow: false,
          font: { size: 10, color: "#E5484D", family: "JetBrains Mono, monospace" },
        });
      }

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
        margin: { l: 55, r: 55, t: 30, b: 45 },
        xaxis: {
          title: { text: "Mass [kg]", font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        yaxis: {
          title: { text: "Stall Speed [m/s] / Wing Loading [Pa]", font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        yaxis2: {
          title: { text: "CL Margin", font: { size: 11, color: "#30A46C" } },
          overlaying: "y",
          side: "right",
          gridcolor: "transparent",
          zerolinecolor: "#3F3F46",
          tickfont: { color: "#30A46C" },
        },
        showlegend: true,
        legend: {
          x: 0.02,
          y: 0.98,
          xanchor: "left",
          yanchor: "top",
          bgcolor: "rgba(0,0,0,0.4)",
          bordercolor: "#3F3F46",
          borderwidth: 1,
          font: { size: 10, color: "#A1A1AA" },
        },
        autosize: true,
        shapes,
        annotations,
      };

      await PlotlyRef.react(node, traces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [points, currentMassKg]);

  if (points.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-xl border border-border bg-card p-4">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          No mass sweep data
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden" data-testid="mass-sweep-chart">
      <div ref={containerRef} className="min-h-0 flex-1" style={{ minHeight: 280 }} />
    </div>
  );
}
