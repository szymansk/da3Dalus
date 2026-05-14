"use client";

import { useRef, useEffect } from "react";
import {
  isGustCriticalWarning,
  isGustValidityWarning,
  type AnyGustWarning,
  type VnCurve,
  type VnMarker,
} from "@/hooks/useFlightEnvelope";

const STATUS_COLORS: Record<string, string> = {
  TRIMMED: "#30A46C",
  NOT_TRIMMED: "#F59E0B",
  LIMIT_REACHED: "#E5484D",
};

interface Props {
  readonly vnCurve: VnCurve;
  readonly operatingPoints: VnMarker[];
  readonly gustWarnings?: AnyGustWarning[];
}

export function VnDiagram({ vnCurve, operatingPoints, gustWarnings }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || vnCurve.positive.length === 0) return;
    let disposed = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let PlotlyRef: any = null;

    (async () => {
      PlotlyRef = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const traces: Record<string, any>[] = [];

      // Positive g boundary — Maneuver envelope
      traces.push({
        x: vnCurve.positive.map((p) => p.velocity_mps),
        y: vnCurve.positive.map((p) => p.load_factor),
        type: "scatter",
        mode: "lines",
        name: "Manöver +g / Maneuver +g",
        line: { color: "#FF8400", width: 2 },
        hovertemplate: "V: %{x:.1f} m/s<br>n: %{y:.2f}<extra>Maneuver</extra>",
      });

      // Negative g boundary — Maneuver envelope
      traces.push({
        x: vnCurve.negative.map((p) => p.velocity_mps),
        y: vnCurve.negative.map((p) => p.load_factor),
        type: "scatter",
        mode: "lines",
        name: "Manöver −g / Maneuver −g",
        line: { color: "#FF8400", width: 2, dash: "dash" },
        hovertemplate: "V: %{x:.1f} m/s<br>n: %{y:.2f}<extra>Maneuver</extra>",
      });

      // Gust envelope — positive line (Pratt-Walker, CS-VLA.333)
      const gustPos = vnCurve.gust_lines_positive ?? [];
      const gustNeg = vnCurve.gust_lines_negative ?? [];

      if (gustPos.length > 0) {
        traces.push({
          x: gustPos.map((p) => p.velocity_mps),
          y: gustPos.map((p) => p.load_factor),
          type: "scatter",
          mode: "lines",
          name: "Böen +g / Gust +g",
          line: { color: "#7DD3FC", width: 1.5, dash: "dot" },
          hovertemplate:
            "V: %{x:.1f} m/s<br>n: %{y:.2f}<extra>Gust (CS-VLA.333)</extra>",
        });
      }

      if (gustNeg.length > 0) {
        traces.push({
          x: gustNeg.map((p) => p.velocity_mps),
          y: gustNeg.map((p) => p.load_factor),
          type: "scatter",
          mode: "lines",
          name: "Böen −g / Gust −g",
          line: { color: "#7DD3FC", width: 1.5, dash: "dashdot" },
          hovertemplate:
            "V: %{x:.1f} m/s<br>n: %{y:.2f}<extra>Gust (CS-VLA.333)</extra>",
        });
      }

      // Operating point markers grouped by status
      const grouped = new Map<string, VnMarker[]>();
      for (const op of operatingPoints) {
        const arr = grouped.get(op.status) ?? [];
        arr.push(op);
        grouped.set(op.status, arr);
      }

      for (const [status, ops] of grouped) {
        traces.push({
          x: ops.map((o) => o.velocity_mps),
          y: ops.map((o) => o.load_factor),
          type: "scatter",
          mode: "markers+text",
          name: status,
          marker: {
            color: STATUS_COLORS[status] ?? "#A1A1AA",
            size: 9,
            symbol: "circle",
          },
          text: ops.map((o) => o.label),
          textposition: "top center",
          textfont: {
            size: 9,
            color: "#A1A1AA",
            family: "JetBrains Mono, monospace",
          },
          hovertemplate: ops.map(
            (o) =>
              `${o.name}<br>V: ${o.velocity_mps.toFixed(1)} m/s<br>n: ${o.load_factor.toFixed(2)}<extra>${status}</extra>`,
          ),
        });
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const shapes: Record<string, any>[] = [
        // V_dive vertical line
        {
          type: "line",
          x0: vnCurve.dive_speed_mps,
          x1: vnCurve.dive_speed_mps,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: { color: "#71717A", width: 1, dash: "dot" },
        },
        // V_stall vertical line
        {
          type: "line",
          x0: vnCurve.stall_speed_mps,
          x1: vnCurve.stall_speed_mps,
          y0: 0,
          y1: 1,
          yref: "paper",
          line: { color: "#71717A", width: 1, dash: "dot" },
        },
      ];

      const annotations = [
        {
          x: vnCurve.dive_speed_mps,
          y: 1.02,
          yref: "paper" as const,
          text: "V<sub>dive</sub>",
          showarrow: false,
          font: {
            size: 10,
            color: "#71717A",
            family: "JetBrains Mono, monospace",
          },
        },
        {
          x: vnCurve.stall_speed_mps,
          y: 1.02,
          yref: "paper" as const,
          text: "V<sub>stall</sub>",
          showarrow: false,
          font: {
            size: 10,
            color: "#71717A",
            family: "JetBrains Mono, monospace",
          },
        },
      ];

      const layout = {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: {
          color: "#A1A1AA",
          family: "JetBrains Mono, monospace",
          size: 10,
        },
        margin: { l: 55, r: 20, t: 30, b: 45 },
        xaxis: {
          title: { text: "Airspeed [m/s]", font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        yaxis: {
          title: { text: "Load Factor (n)", font: { size: 11 } },
          gridcolor: "#27272A",
          zerolinecolor: "#3F3F46",
        },
        showlegend: true,
        legend: {
          x: 0.98,
          y: 0.02,
          xanchor: "right",
          yanchor: "bottom",
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
  }, [vnCurve, operatingPoints]);

  if (vnCurve.positive.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-xl border border-border bg-card p-4">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          No V-n data
        </span>
      </div>
    );
  }

  const warnings = gustWarnings ?? vnCurve.gust_warnings ?? [];
  const criticalWarnings = warnings.filter(isGustCriticalWarning);
  const validityWarnings = warnings.filter(isGustValidityWarning);

  return (
    <div className="flex flex-1 flex-col gap-2 overflow-hidden bg-card-muted">
      {criticalWarnings.length > 0 && (
        <div
          role="alert"
          aria-live="polite"
          className="rounded-lg border border-sky-500/40 bg-sky-500/10 px-4 py-2"
        >
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-medium text-sky-300">
            Gust-critical: structure sized by gust loads, not maneuver loads
          </p>
          <p className="mt-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-sky-400/70">
            Böen-Hülle überschreitet Manöver-g-Limit — Böenlasten maßgebend
            (CS-VLA.333 / FAR-25.341)
          </p>
        </div>
      )}
      {validityWarnings.length > 0 && (
        <div
          role="alert"
          aria-live="polite"
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2"
        >
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] font-medium text-amber-300">
            Pratt-Walker validity: gust loads may be optimistic
          </p>
          <p className="mt-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-amber-400/70">
            {validityWarnings[0].message}
          </p>
        </div>
      )}
      <div ref={containerRef} className="min-h-0 flex-1" />
    </div>
  );
}
