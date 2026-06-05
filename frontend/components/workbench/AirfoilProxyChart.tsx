"use client";

import { useMemo } from "react";
import type { AirfoilAnalysisResult } from "@/hooks/useAirfoilAnalysis";
import {
  buildAirfoilProxyChartData,
  findPeakClOverCd,
  findPeakCl15OverCd,
} from "@/lib/airfoilProxyChartData";

// ── Colors ───────────────────────────────────────────────────────
const COLOR_CL_OVER_CD = "#22c55e";    // cl/cd — green (range/glide)
const COLOR_CL15_OVER_CD = "#a78bfa"; // cl^1.5/cd — violet (endurance)

// ── Chart geometry ───────────────────────────────────────────────
const W = 400;
const H = 200;
const PAD = { top: 14, right: 20, bottom: 36, left: 52 };
const PW = W - PAD.left - PAD.right;
const PH = H - PAD.top - PAD.bottom;

interface AirfoilProxyChartProps {
  /** Root airfoil analysis result.  null = empty state. */
  analysisResult: AirfoilAnalysisResult | null;
}

/**
 * 2D airfoil proxy chart — cl/cd and cl^1.5/cd vs cl.
 *
 * IMPORTANT: These are SECTION-level (2D) metrics from the NeuralFoil polar,
 * NOT the aircraft polar.  The chart is labelled clearly to avoid confusion
 * with the aircraft Geschwindigkeitspolare.
 *
 * - cl/cd: range / glide indicator (section best-glide proxy)
 * - cl^1.5/cd: endurance indicator (section best-endurance proxy)
 */
export function AirfoilProxyChart({
  analysisResult,
}: Readonly<AirfoilProxyChartProps>) {
  const plotData = useMemo(() => {
    if (!analysisResult) return null;

    const proxyData = buildAirfoilProxyChartData(
      analysisResult.cl,
      analysisResult.cd,
    );
    if (proxyData.length < 2) return null;

    const cls = proxyData.map((p) => p.cl);
    const clovercds = proxyData.map((p) => p.clOverCd);
    const cl15overcds = proxyData.map((p) => p.cl15OverCd);

    const xMin = Math.max(0, Math.min(...cls) * 0.95);
    const xMax = Math.max(...cls) * 1.05;
    const xRange = xMax - xMin || 1;

    const allY = [...clovercds, ...cl15overcds];
    const yMin = 0;
    const yMax = Math.max(...allY) * 1.15;
    const yRange = yMax - yMin || 1;

    function sx(cl: number) { return PAD.left + ((cl - xMin) / xRange) * PW; }
    function sy(y: number) { return PAD.top + PH - ((y - yMin) / yRange) * PH; }

    function buildPath(xs: number[], ys: number[]) {
      return xs
        .map((x, i) => `${i === 0 ? "M" : "L"}${sx(x).toFixed(1)},${sy(ys[i]).toFixed(1)}`)
        .join(" ");
    }

    const pathClOverCd = buildPath(cls, clovercds);
    const pathCl15OverCd = buildPath(cls, cl15overcds);

    const peakClOverCd = findPeakClOverCd(proxyData);
    const peakCl15OverCd = findPeakCl15OverCd(proxyData);

    const xTicks = Array.from({ length: 5 }, (_, i) => xMin + (xRange * i) / 4);
    const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);

    return {
      pathClOverCd, pathCl15OverCd,
      peakClOverCd, peakCl15OverCd,
      sx, sy, xTicks, yTicks,
    };
  }, [analysisResult]);

  if (!analysisResult || !plotData) {
    return (
      <div
        className="flex h-full items-center justify-center font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground"
        data-testid="airfoil-proxy-chart-empty"
      >
        Analyse ausf{"ü"}hren um Profil-Indikator zu sehen
      </div>
    );
  }

  const {
    pathClOverCd, pathCl15OverCd,
    peakClOverCd, peakCl15OverCd,
    sx, sy, xTicks, yTicks,
  } = plotData;

  return (
    <div className="flex flex-col gap-2" data-testid="airfoil-proxy-chart">
      {/* Chart title + disclaimer */}
      <div className="flex items-baseline gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
          Profil-Indikator (2D)
        </span>
        <span
          className="rounded border border-amber-500/40 bg-amber-500/10 px-1 font-[family-name:var(--font-jetbrains-mono)] text-[8px] text-amber-400"
          data-testid="airfoil-proxy-disclaimer"
        >
          kein Flugzeug — Profil-Indikator
        </span>
      </div>

      {/* SVG chart */}
      <div className="rounded-xl border border-border bg-card p-2">
        <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" preserveAspectRatio="xMidYMid meet">
          {/* Grid */}
          {yTicks.map((y) => (
            <line key={`yg${y}`} x1={PAD.left} x2={W - PAD.right}
              y1={sy(y)} y2={sy(y)} stroke="var(--color-border)" strokeWidth="0.5" />
          ))}
          {xTicks.map((x) => (
            <line key={`xg${x}`} x1={sx(x)} x2={sx(x)}
              y1={PAD.top} y2={PAD.top + PH} stroke="var(--color-border)" strokeWidth="0.5" />
          ))}

          {/* Axes */}
          <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + PH}
            stroke="var(--color-muted-foreground)" strokeWidth="1" />
          <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + PH} y2={PAD.top + PH}
            stroke="var(--color-muted-foreground)" strokeWidth="1" />

          {/* Y-axis labels */}
          {yTicks.map((y) => (
            <text key={`yl${y}`} x={PAD.left - 5} y={sy(y) + 3}
              textAnchor="end" fontSize="8" fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)">
              {y.toFixed(0)}
            </text>
          ))}

          {/* X-axis labels */}
          {xTicks.map((x) => (
            <text key={`xl${x}`} x={sx(x)} y={PAD.top + PH + 12}
              textAnchor="middle" fontSize="8" fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)">
              {x.toFixed(2)}
            </text>
          ))}

          {/* Axis labels */}
          <text x={W / 2} y={H - 3} textAnchor="middle" fontSize="9"
            fill="var(--color-muted-foreground)" fontFamily="var(--font-jetbrains-mono)">
            C_L
          </text>
          <text x={12} y={H / 2} textAnchor="middle" fontSize="9"
            fill="var(--color-muted-foreground)" fontFamily="var(--font-jetbrains-mono)"
            transform={`rotate(-90, 12, ${H / 2})`}>
            [–]
          </text>

          {/* cl^1.5/cd curve (endurance) — dashed */}
          <path d={pathCl15OverCd} fill="none" stroke={COLOR_CL15_OVER_CD}
            strokeWidth="1.5" strokeLinejoin="round" strokeDasharray="6 3"
            data-testid="airfoil-proxy-cl15-line" />

          {/* cl/cd curve (range/glide) — solid */}
          <path d={pathClOverCd} fill="none" stroke={COLOR_CL_OVER_CD}
            strokeWidth="2" strokeLinejoin="round"
            data-testid="airfoil-proxy-clovercd-line" />

          {/* Peak markers */}
          {peakClOverCd && isFinite(peakClOverCd.cl) && isFinite(peakClOverCd.clOverCd) && (
            <circle
              data-testid="airfoil-proxy-peak-clovercd"
              cx={sx(peakClOverCd.cl)}
              cy={sy(peakClOverCd.clOverCd)}
              r="4" fill={COLOR_CL_OVER_CD} stroke="white" strokeWidth="1.5" opacity="0.92"
            />
          )}
          {peakCl15OverCd && isFinite(peakCl15OverCd.cl) && isFinite(peakCl15OverCd.cl15OverCd) && (
            <circle
              data-testid="airfoil-proxy-peak-cl15overcd"
              cx={sx(peakCl15OverCd.cl)}
              cy={sy(peakCl15OverCd.cl15OverCd)}
              r="4" fill={COLOR_CL15_OVER_CD} stroke="white" strokeWidth="1.5" opacity="0.92"
            />
          )}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-0.5">
        <span className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[8px] text-muted-foreground">
          <span className="inline-block size-[5px] rounded-full" style={{ backgroundColor: COLOR_CL_OVER_CD }} />
          c_l / c_d (Gleitzahl)
          {peakClOverCd && (
            <span className="ml-0.5 text-muted-foreground/60">
              max≈{peakClOverCd.clOverCd.toFixed(1)} @ c_l={peakClOverCd.cl.toFixed(2)}
            </span>
          )}
        </span>
        <span className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[8px] text-muted-foreground">
          <span className="inline-block h-[5px] w-3 rounded" style={{
            background: `repeating-linear-gradient(90deg, ${COLOR_CL15_OVER_CD} 0 6px, transparent 6px 9px)`,
          }} />
          c_l^1.5 / c_d (Ausdauer)
          {peakCl15OverCd && (
            <span className="ml-0.5 text-muted-foreground/60">
              max≈{peakCl15OverCd.cl15OverCd.toFixed(1)} @ c_l={peakCl15OverCd.cl.toFixed(2)}
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
