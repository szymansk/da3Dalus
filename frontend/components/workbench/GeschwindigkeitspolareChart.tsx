"use client";

import { useMemo } from "react";
import type { AircraftSpeedPolar } from "@/hooks/useSpeedPolar";

// ── Colors (consistent with existing airfoil viewer palette) ────
const COLOR_POLAR = "#FF8400";       // main curve — orange accent
const COLOR_BEST_GLIDE = "#38bdf8";  // best-glide marker — sky blue
const COLOR_MIN_SINK = "#a78bfa";    // min-sink marker — violet

// ── Chart geometry ───────────────────────────────────────────────
const W = 400;
const H = 200;
const PAD = { top: 14, right: 20, bottom: 36, left: 52 };
const PW = W - PAD.left - PAD.right;
const PH = H - PAD.top - PAD.bottom;

interface GeschwindigkeitspolareChartProps {
  /** Speed polar from the backend. null = empty state. */
  polar: AircraftSpeedPolar | null;
  /** Whether the speed polar data is being loaded. */
  isLoading?: boolean;
}

/** Marker on the speed polar: a named point with a dot + label. */
interface PolarMarker {
  v: number;
  sink: number;
  color: string;
  label: string;
  testId: string;
}

/** Format a float to N decimal places, removing trailing zeros. */
function fmt(x: number, decimals: number): string {
  // Parse back to number then to string to strip trailing zeros (no regex needed)
  return String(parseFloat(x.toFixed(decimals)));
}

/**
 * Aircraft speed polar chart (Geschwindigkeitspolare) — sink rate vs airspeed.
 *
 * Sink is plotted positive downward (y-axis inverted): fastest sink is at the
 * top, slowest (best soaring performance) at the bottom. This is the standard
 * aviation convention for speed polars.
 *
 * Best-glide and min-sink are shown as named markers.
 */
export function GeschwindigkeitspolareChart({
  polar,
  isLoading,
}: Readonly<GeschwindigkeitspolareChartProps>) {
  const plotData = useMemo(() => {
    if (!polar) return null;

    // Build valid (v, sink) pairs from the curve arrays
    const pairs: { v: number; sink: number }[] = [];
    for (let i = 0; i < polar.v_mps.length; i++) {
      const v = polar.v_mps[i];
      const s = polar.sink_mps[i];
      if (isFinite(v) && isFinite(s) && v > 0 && s >= 0) {
        pairs.push({ v, sink: s });
      }
    }
    if (pairs.length < 2) return null;

    // Axis ranges — sink is inverted (y=0 at bottom, y=PH at top)
    const vMin = Math.min(...pairs.map((p) => p.v));
    const vMax = Math.max(...pairs.map((p) => p.v));
    // Include marker V values in x-range to ensure they fit
    const allV = [
      ...pairs.map((p) => p.v),
      polar.best_glide.v_mps,
      polar.min_sink.v_mps,
    ];
    const xMin = Math.max(0, Math.min(...allV) * 0.95);
    const xMax = Math.max(...allV) * 1.05;
    const xRange = xMax - xMin || 1;

    const allSink = [
      ...pairs.map((p) => p.sink),
      polar.best_glide.sink_mps,
      polar.min_sink.sink_mps,
    ];
    // Ensure y axis starts near zero (minimum sink), ends a bit above max sink
    const yMin = 0;
    const yMax = Math.max(...allSink) * 1.15;
    const yRange = yMax - yMin || 1;

    // SVG coordinate transformations
    // x: V increases left→right
    function sx(v: number) { return PAD.left + ((v - xMin) / xRange) * PW; }
    // y: sink increases bottom→top (small sink = more lift = bottom)
    // Axis is inverted so high sink is "up" (top of plot)
    function sy(s: number) { return PAD.top + ((s - yMin) / yRange) * PH; }

    const pathD = pairs
      .map((p, i) => `${i === 0 ? "M" : "L"}${sx(p.v).toFixed(1)},${sy(p.sink).toFixed(1)}`)
      .join(" ");

    // Best-glide tangent line from origin to best-glide point
    // Tangent from (0,0) — in SVG coords: origin is the bottom-left corner
    const bgV = polar.best_glide.v_mps;
    const bgSink = polar.best_glide.sink_mps;
    // Extend the tangent line past the chart edge for visual clarity
    const tanX2 = xMax * 1.05;
    const tanY2 = (bgSink / bgV) * tanX2;

    const markers: PolarMarker[] = [
      {
        v: polar.best_glide.v_mps,
        sink: polar.best_glide.sink_mps,
        color: COLOR_BEST_GLIDE,
        label: `Best-Glide V=${fmt(polar.best_glide.v_mps, 1)} m/s`,
        testId: "speed-polar-best-glide-marker",
      },
      {
        v: polar.min_sink.v_mps,
        sink: polar.min_sink.sink_mps,
        color: COLOR_MIN_SINK,
        label: `Min-Sink V=${fmt(polar.min_sink.v_mps, 1)} m/s`,
        testId: "speed-polar-min-sink-marker",
      },
    ];

    // Axis tick generators
    const xTicks = Array.from({ length: 5 }, (_, i) => xMin + (xRange * i) / 4);
    const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);

    return {
      pathD, sx, sy, xTicks, yTicks, markers,
      tanX1: 0, tanY1: 0, tanX2, tanY2,
      xMin, xMax, yMin, yMax, vMin, vMax,
    };
  }, [polar]);

  if (isLoading) {
    return (
      <div
        className="flex h-full items-center justify-center font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground"
        data-testid="speed-polar-loading"
      >
        Loading{"…"}
      </div>
    );
  }

  if (!polar || !plotData) {
    return (
      <div
        className="flex h-full items-center justify-center font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground"
        data-testid="speed-polar-empty"
      >
        Keine Daten — Annahmen berechnen um die Polare zu sehen
      </div>
    );
  }

  const { pathD, sx, sy, xTicks, yTicks, markers, tanX2, tanY2 } = plotData;

  return (
    <div className="flex flex-col gap-2" data-testid="geschwindigkeitspolare-chart">
      {/* Chart title */}
      <div className="flex items-baseline gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
          Geschwindigkeitspolare
        </span>
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
          m={fmt(polar.inputs.mass_kg, 1)} kg · S={fmt(polar.inputs.s_ref_m2, 3)} m² ·
          AR={fmt(polar.inputs.ar, 1)} · e={fmt(polar.inputs.e_oswald, 2)} ·
          CD₀={fmt(polar.inputs.cd0, 4)}
        </span>
      </div>

      {/* SVG chart */}
      <div className="rounded-xl border border-border bg-card p-2">
        <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {yTicks.map((s) => (
            <line
              key={`yg${s}`}
              x1={PAD.left} x2={W - PAD.right}
              y1={sy(s)} y2={sy(s)}
              stroke="var(--color-border)" strokeWidth="0.5"
            />
          ))}
          {xTicks.map((v) => (
            <line
              key={`xg${v}`}
              x1={sx(v)} x2={sx(v)}
              y1={PAD.top} y2={PAD.top + PH}
              stroke="var(--color-border)" strokeWidth="0.5"
            />
          ))}

          {/* Axes */}
          <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + PH}
            stroke="var(--color-muted-foreground)" strokeWidth="1" />
          <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + PH} y2={PAD.top + PH}
            stroke="var(--color-muted-foreground)" strokeWidth="1" />

          {/* Y-axis labels (sink rate) */}
          {yTicks.map((s) => (
            <text key={`yl${s}`} x={PAD.left - 5} y={sy(s) + 3}
              textAnchor="end" fontSize="8" fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)">
              {s.toFixed(2)}
            </text>
          ))}

          {/* X-axis labels (speed) */}
          {xTicks.map((v) => (
            <text key={`xl${v}`} x={sx(v)} y={PAD.top + PH + 12}
              textAnchor="middle" fontSize="8" fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)">
              {v.toFixed(0)}
            </text>
          ))}

          {/* Axis labels */}
          <text x={W / 2} y={H - 3} textAnchor="middle" fontSize="9"
            fill="var(--color-muted-foreground)" fontFamily="var(--font-jetbrains-mono)">
            V [m/s]
          </text>
          <text x={12} y={H / 2} textAnchor="middle" fontSize="9"
            fill="var(--color-muted-foreground)" fontFamily="var(--font-jetbrains-mono)"
            transform={`rotate(-90, 12, ${H / 2})`}>
            Sinken [m/s]
          </text>

          {/* Best-glide tangent line (from origin of the plot axes, clipped) */}
          <line
            x1={sx(0)} y1={sy(0)}
            x2={sx(tanX2)} y2={sy(tanY2)}
            stroke={COLOR_BEST_GLIDE}
            strokeWidth="1"
            strokeDasharray="6 3"
            opacity="0.5"
            data-testid="speed-polar-best-glide-tangent"
          />

          {/* Speed polar curve */}
          <path
            d={pathD}
            fill="none"
            stroke={COLOR_POLAR}
            strokeWidth="2"
            strokeLinejoin="round"
            data-testid="speed-polar-curve"
          />

          {/* Markers */}
          {markers.map((m) => {
            if (!isFinite(m.v) || !isFinite(m.sink)) return null;
            return (
              <circle
                key={m.testId}
                data-testid={m.testId}
                cx={sx(m.v)}
                cy={sy(m.sink)}
                r="4"
                fill={m.color}
                stroke="white"
                strokeWidth="1.5"
                opacity="0.92"
              />
            );
          })}
        </svg>
      </div>

      {/* Marker legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-0.5">
        {markers.map((m) => (
          <span
            key={m.testId}
            className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[8px] text-muted-foreground"
          >
            <span className="inline-block size-[5px] rounded-full" style={{ backgroundColor: m.color }} />
            {m.label}
          </span>
        ))}
        <span className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[8px] text-muted-foreground">
          <span className="inline-block h-[5px] w-3 rounded" style={{ backgroundColor: COLOR_BEST_GLIDE, opacity: 0.5 }} />
          Best-Glide Tangente
        </span>
      </div>
    </div>
  );
}
