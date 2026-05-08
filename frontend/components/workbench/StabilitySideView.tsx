"use client";

import { useRef, useEffect, useState } from "react";
import type { StabilityData } from "@/hooks/useStability";
import { MarkerDetailBox, type MarkerInfo } from "./MarkerDetailBox";

interface Props {
  readonly data: StabilityData;
}

function Badge({
  label,
  value,
  color,
}: Readonly<{ label: string; value: string; color: string }>) {
  return (
    <div
      className="flex items-center gap-1.5 rounded-full px-2.5 py-1"
      style={{ backgroundColor: `${color}15`, border: `1px solid ${color}30` }}
    >
      <span className="text-[10px] text-muted-foreground">{label}</span>
      <span
        className="font-[family-name:var(--font-jetbrains-mono)] text-[11px]"
        style={{ color }}
      >
        {value}
      </span>
    </div>
  );
}

const STABILITY_COLORS: Record<string, string> = {
  stable: "#30A46C",
  neutral: "#F5A623",
  unstable: "#E5484D",
};

export function StabilitySideView({ data }: Props) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [selectedMarker, setSelectedMarker] = useState<MarkerInfo | null>(null);

  const stabilityColor = STABILITY_COLORS[data.stability_class ?? "neutral"] ?? "#888";

  useEffect(() => {
    const node = plotRef.current;
    if (!node) return;

    let cancelled = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (cancelled) return;

      const np = data.neutral_point_x;
      const cg = data.cg_x_used;
      const mac = data.mac;
      const fwd = data.cg_range_forward;
      const aft = data.cg_range_aft;

      if (np == null || cg == null || mac == null) return;

      const xMin = Math.min(np - mac * 1.2, fwd ?? np - mac, cg) - 0.02;
      const xMax = Math.max(np + mac * 0.3, aft ?? np, cg) + 0.02;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const traces: any[] = [];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const shapes: any[] = [];

      // MAC bar
      const macLeX = np - mac;
      shapes.push({
        type: "rect",
        x0: macLeX,
        x1: np,
        y0: -0.15,
        y1: 0.15,
        fillcolor: "rgba(136,136,136,0.12)",
        line: { color: "rgba(136,136,136,0.3)", width: 1 },
      });

      // CG range band
      if (fwd != null && aft != null) {
        const rangeColor = STABILITY_COLORS[data.stability_class ?? "neutral"] ?? "#888";
        shapes.push({
          type: "rect",
          x0: fwd,
          x1: aft,
          y0: -0.3,
          y1: 0.3,
          fillcolor: `${rangeColor}18`,
          line: { color: `${rangeColor}50`, width: 1, dash: "dot" },
        });
      }

      // NP marker (blue diamond)
      traces.push({
        x: [np],
        y: [0],
        mode: "markers+text",
        marker: { symbol: "diamond", size: 14, color: "#3B82F6" },
        text: ["NP"],
        textposition: "top center",
        textfont: { size: 11, color: "#3B82F6", family: "JetBrains Mono" },
        name: "Neutral Point",
        hovertemplate: `NP: ${np.toFixed(3)} m<extra></extra>`,
        showlegend: false,
      });

      // CG marker (orange circle)
      traces.push({
        x: [cg],
        y: [0],
        mode: "markers+text",
        marker: { symbol: "circle", size: 14, color: "#FF8400" },
        text: ["CG"],
        textposition: "top center",
        textfont: { size: 11, color: "#FF8400", family: "JetBrains Mono" },
        name: "Center of Gravity",
        hovertemplate: `CG: ${cg.toFixed(3)} m<extra></extra>`,
        showlegend: false,
      });

      // Annotations
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const annotations: any[] = [];

      // Static margin label between CG and NP
      if (data.static_margin_pct != null) {
        annotations.push({
          x: (cg + np) / 2,
          y: -0.45,
          text: `SM: ${data.static_margin_pct.toFixed(1)}% MAC`,
          showarrow: false,
          font: { size: 12, color: stabilityColor, family: "JetBrains Mono" },
        });
      }

      // MAC label
      annotations.push({
        x: macLeX + mac / 2,
        y: 0.25,
        text: `MAC: ${(mac * 1000).toFixed(0)} mm`,
        showarrow: false,
        font: { size: 10, color: "#888", family: "JetBrains Mono" },
      });

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        margin: { t: 30, b: 50, l: 60, r: 30 },
        xaxis: {
          title: { text: "x [m]", font: { size: 11, color: "#888" } },
          range: [xMin, xMax],
          gridcolor: "rgba(136,136,136,0.15)",
          zerolinecolor: "rgba(136,136,136,0.3)",
          tickfont: { size: 10, color: "#888", family: "JetBrains Mono" },
        },
        yaxis: {
          visible: false,
          range: [-0.7, 0.5],
          fixedrange: true,
        },
        shapes,
        annotations,
        dragmode: false as const,
        hovermode: "closest" as const,
        font: { color: "#ccc" },
      };

      const config = {
        displayModeBar: false,
        responsive: true,
      };

      await Plotly.newPlot(node, traces, layout, config);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (node as any).on("plotly_click", (eventData: { points: Array<{ curveNumber: number }> }) => {
        const pt = eventData.points[0];
        if (!pt) return;
        if (pt.curveNumber === 0) {
          setSelectedMarker({
            type: "np",
            neutral_point_x: np,
            Cma: data.Cma,
            stability_class: data.stability_class,
            solver: data.solver,
          });
        } else if (pt.curveNumber === 1) {
          setSelectedMarker({
            type: "cg",
            cg_x_used: cg,
            static_margin_pct: data.static_margin_pct,
            source: "estimate",
          });
        }
      });
    })();

    return () => {
      cancelled = true;
      if (node) {
        import("plotly.js-gl3d-dist-min").then((Plotly) => Plotly.purge(node));
      }
    };
  }, [data, stabilityColor]);

  return (
    <div className="flex flex-1 flex-col gap-3">
      {/* KPI badges */}
      <div className="flex flex-wrap items-center gap-2">
        {data.static_margin_pct != null && (
          <Badge label="Static Margin" value={`${data.static_margin_pct.toFixed(1)}%`} color={stabilityColor} />
        )}
        {data.stability_class && (
          <Badge label="Class" value={data.stability_class} color={stabilityColor} />
        )}
        {data.Cma != null && (
          <Badge label="Cm.α" value={data.Cma.toFixed(3)} color="#A78BFA" />
        )}
        {data.Cnb != null && (
          <Badge label="Cn.β" value={data.Cnb.toFixed(3)} color="#3B82F6" />
        )}
        {data.Clb != null && (
          <Badge label="Cl.β" value={data.Clb.toFixed(3)} color="#30A46C" />
        )}
        {data.status === "DIRTY" && (
          <Badge label="" value="outdated — geometry changed" color="#F5A623" />
        )}
      </div>

      {/* Plotly chart */}
      <div className="relative flex-1">
        <div ref={plotRef} data-testid="stability-plot" className="h-full w-full" />
        {selectedMarker && (
          <div className="absolute right-4 top-4 z-10">
            <MarkerDetailBox marker={selectedMarker} onClose={() => setSelectedMarker(null)} />
          </div>
        )}
      </div>
    </div>
  );
}
