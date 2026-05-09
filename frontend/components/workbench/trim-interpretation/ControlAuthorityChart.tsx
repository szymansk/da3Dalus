"use client";

import { useRef, useEffect } from "react";
import type { TrimEnrichment, DeflectionReserve } from "@/hooks/useOperatingPoints";

function authorityColor(fraction: number): string {
  if (fraction > 0.8) return "#EF4444";
  if (fraction > 0.6) return "#F59E0B";
  return "#30A46C";
}

function displaySurfaceName(encoded: string): string {
  const match = encoded.match(/^\[(\w+)\](.+)$/);
  return match ? match[2] : encoded;
}

function formatLabel(name: string, reserve: DeflectionReserve): string {
  const displayName = displaySurfaceName(name);
  const limit = reserve.deflection_deg >= 0 ? reserve.max_pos_deg : reserve.max_neg_deg;
  const reservePct = Math.round((1 - reserve.usage_fraction) * 100);
  return `${displayName}: ${reserve.deflection_deg.toFixed(1)}° / ±${limit.toFixed(0)}° (${reservePct}% reserve)`;
}

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function ControlAuthorityChart({ enrichment }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || !enrichment) return;

    const entries = Object.entries(enrichment.deflection_reserves);
    if (entries.length === 0) return;

    let disposed = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const surfaceNames = entries.map(([name]) => displaySurfaceName(name));
      const usagePcts = entries.map(([, r]) => Math.round(r.usage_fraction * 100));
      const colors = entries.map(([, r]) => authorityColor(r.usage_fraction));
      const hoverTexts = entries.map(([name, r]) => formatLabel(name, r));

      const trace = {
        type: "bar",
        orientation: "h",
        y: surfaceNames,
        x: usagePcts,
        marker: { color: colors },
        text: usagePcts.map((p: number) => `${p}%`),
        textposition: "outside",
        textfont: { color: "#A1A1AA", size: 11, family: "JetBrains Mono" },
        hovertext: hoverTexts,
        hoverinfo: "text",
      };

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#A1A1AA", size: 11, family: "JetBrains Mono" },
        margin: { l: 120, r: 50, t: 10, b: 30 },
        xaxis: {
          range: [0, 110],
          dtick: 25,
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
          title: { text: "Authority Used (%)", font: { size: 10 } },
        },
        yaxis: {
          automargin: true,
          tickfont: { size: 11 },
        },
        shapes: [
          {
            type: "line",
            x0: 80,
            x1: 80,
            y0: -0.5,
            y1: entries.length - 0.5,
            line: { color: "#F59E0B", width: 1, dash: "dot" },
          },
        ],
        height: Math.max(120, entries.length * 40 + 50),
        autosize: true,
      };

      await PlotlyRef.react(node, [trace], layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
      if (node && PlotlyRef) PlotlyRef.purge(node);
    };
  }, [enrichment]);

  if (!enrichment || Object.keys(enrichment.deflection_reserves).length === 0) return null;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card-muted p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        Control Authority
      </span>
      <div ref={containerRef} data-testid="authority-chart-container" className="min-h-[120px]" />
    </div>
  );
}
