"use client";

import { useMemo } from "react";
import type { AirfoilGeometry } from "@/hooks/useAirfoilGeometry";
import type { AirfoilAnalysisResult } from "@/hooks/useAirfoilAnalysis";
import { interpolateY } from "@/hooks/useAirfoilGeometry";

interface AirfoilPreviewViewerPanelProps {
  airfoilName: string;
  geometry: AirfoilGeometry | null;
  geometryLoading: boolean;
  analysisResult: AirfoilAnalysisResult | null;
  re: number;
  ma: number;
  onReChange: (re: number) => void;
  onMaChange: (ma: number) => void;
}

// ── SVG Line Chart (follows AnalysisViewerPanel pattern) ────────

function LineChart({
  xData,
  yData,
  xLabel,
  yLabel,
  title,
  annotation,
  color = "var(--color-primary)",
}: {
  xData: number[];
  yData: (number | null)[];
  xLabel: string;
  yLabel: string;
  title: string;
  annotation?: string;
  color?: string;
}) {
  const W = 400;
  const H = 200;
  const PAD = { top: 10, right: 15, bottom: 30, left: 45 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  // Filter to valid pairs only
  const valid = useMemo(() => {
    const pairs: { x: number; y: number }[] = [];
    for (let i = 0; i < xData.length; i++) {
      const y = yData[i];
      if (y != null && isFinite(y)) pairs.push({ x: xData[i], y });
    }
    return pairs;
  }, [xData, yData]);

  if (valid.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-[--radius-s] border border-border bg-card p-4">
        <span className="text-[12px] text-muted-foreground">No data</span>
      </div>
    );
  }

  const xMin = Math.min(...valid.map((p) => p.x));
  const xMax = Math.max(...valid.map((p) => p.x));
  const yMin = Math.min(...valid.map((p) => p.y));
  const yMax = Math.max(...valid.map((p) => p.y));
  const xRange = xMax - xMin || 1;
  const yRange = yMax - yMin || 1;

  function sx(v: number) {
    return PAD.left + ((v - xMin) / xRange) * plotW;
  }
  function sy(v: number) {
    return PAD.top + plotH - ((v - yMin) / yRange) * plotH;
  }

  const pathD = valid
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`,
    )
    .join(" ");

  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);
  const xTicks = Array.from({ length: 5 }, (_, i) => xMin + (xRange * i) / 4);

  return (
    <div className="flex flex-1 flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
          {title}
        </span>
        {annotation && (
          <>
            <span className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              {annotation}
            </span>
          </>
        )}
      </div>
      <div className="rounded-[--radius-s] border border-border bg-card p-2">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-full w-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Grid lines */}
          {yTicks.map((v, i) => (
            <line
              key={`yg${i}`}
              x1={PAD.left}
              x2={W - PAD.right}
              y1={sy(v)}
              y2={sy(v)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}
          {xTicks.map((v, i) => (
            <line
              key={`xg${i}`}
              x1={sx(v)}
              x2={sx(v)}
              y1={PAD.top}
              y2={PAD.top + plotH}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}

          {/* Axes */}
          <line
            x1={PAD.left}
            x2={PAD.left}
            y1={PAD.top}
            y2={PAD.top + plotH}
            stroke="var(--color-muted-foreground)"
            strokeWidth="1"
          />
          <line
            x1={PAD.left}
            x2={W - PAD.right}
            y1={PAD.top + plotH}
            y2={PAD.top + plotH}
            stroke="var(--color-muted-foreground)"
            strokeWidth="1"
          />

          {/* Y-axis labels */}
          {yTicks.map((v, i) => (
            <text
              key={`yl${i}`}
              x={PAD.left - 5}
              y={sy(v) + 3}
              textAnchor="end"
              fontSize="8"
              fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)"
            >
              {v.toFixed(2)}
            </text>
          ))}

          {/* X-axis labels */}
          {xTicks.map((v, i) => (
            <text
              key={`xl${i}`}
              x={sx(v)}
              y={PAD.top + plotH + 14}
              textAnchor="middle"
              fontSize="8"
              fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)"
            >
              {`${v.toFixed(0)}\u00B0`}
            </text>
          ))}

          {/* Axis titles */}
          <text
            x={W / 2}
            y={H - 3}
            textAnchor="middle"
            fontSize="9"
            fill="var(--color-muted-foreground)"
            fontFamily="var(--font-jetbrains-mono)"
          >
            {xLabel}
          </text>
          <text
            x={12}
            y={H / 2}
            textAnchor="middle"
            fontSize="9"
            fill="var(--color-muted-foreground)"
            fontFamily="var(--font-jetbrains-mono)"
            transform={`rotate(-90, 12, ${H / 2})`}
          >
            {yLabel}
          </text>

          {/* Data line */}
          <path
            d={pathD}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}

// ── Airfoil SVG ─────────────────────────────────────────────────

function AirfoilSvg({ geometry }: { geometry: AirfoilGeometry }) {
  const { upper, lower, maxThicknessPct, maxCamberPct, maxThicknessX } =
    geometry;

  // Build SVG paths from coordinate arrays
  // Scale: x in [0,1], y typically [-0.1, 0.1] range
  // We use viewBox that accommodates the airfoil shape
  const allY = [...upper.map((p) => p[1]), ...lower.map((p) => p[1])];
  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const yPad = (yMax - yMin) * 0.2;

  const vbX = -0.05;
  const vbW = 1.15;
  const vbY = yMin - yPad;
  const vbH = yMax - yMin + 2 * yPad;

  function pathFromCoords(coords: [number, number][]): string {
    if (coords.length === 0) return "";
    return coords
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]},${-p[1]}`)
      .join(" ");
  }

  // Build camber line by interpolating at sample points
  const camberPoints: [number, number][] = [];
  const sampleXs = Array.from({ length: 40 }, (_, i) => i / 39);
  for (const x of sampleXs) {
    const yU = interpolateY(upper, x);
    const yL = interpolateY(lower, x);
    if (yU !== null && yL !== null) {
      camberPoints.push([x, (yU + yL) / 2]);
    }
  }
  const camberPath = pathFromCoords(camberPoints);

  // Max thickness y-values at maxThicknessX
  const yUpperAtMax = interpolateY(upper, maxThicknessX);
  const yLowerAtMax = interpolateY(lower, maxThicknessX);

  return (
    <svg
      viewBox={`${vbX} ${-(yMax + yPad)} ${vbW} ${vbH}`}
      className="h-full w-full max-h-[200px]"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Chord line (dashed) */}
      <line
        x1="0"
        y1="0"
        x2="1"
        y2="0"
        stroke="currentColor"
        className="text-subtle-foreground"
        strokeWidth={vbH * 0.008}
        strokeDasharray={`${vbW * 0.018} ${vbW * 0.009}`}
      />

      {/* Upper surface */}
      <path
        d={pathFromCoords(upper)}
        fill="rgba(255, 132, 0, 0.12)"
        stroke="#FF8400"
        strokeWidth={vbH * 0.015}
        strokeLinejoin="round"
      />

      {/* Lower surface */}
      <path
        d={pathFromCoords(lower)}
        fill="rgba(255, 132, 0, 0.12)"
        stroke="#FF8400"
        strokeWidth={vbH * 0.015}
        strokeLinejoin="round"
      />

      {/* Camber line */}
      {camberPath && (
        <path
          d={camberPath}
          fill="none"
          stroke="currentColor"
          className="text-foreground"
          strokeWidth={vbH * 0.006}
          opacity="0.3"
        />
      )}

      {/* Max t/c annotation line */}
      {yUpperAtMax !== null && yLowerAtMax !== null && (
        <>
          <line
            x1={maxThicknessX}
            y1={-yUpperAtMax}
            x2={maxThicknessX}
            y2={-yLowerAtMax}
            stroke="currentColor"
            className="text-muted-foreground"
            strokeWidth={vbH * 0.006}
            strokeDasharray={`${vbH * 0.03} ${vbH * 0.02}`}
          />
          <text
            x={maxThicknessX + 0.02}
            y={-(yMax + yPad * 0.3)}
            className="fill-muted-foreground"
            fontSize={vbH * 0.1}
            fontFamily="var(--font-jetbrains-mono), monospace"
          >
            max t/c
          </text>
        </>
      )}

      {/* LE label */}
      <text
        x={-0.02}
        y={vbH * 0.08}
        className="fill-muted-foreground"
        fontSize={vbH * 0.08}
        fontFamily="var(--font-jetbrains-mono), monospace"
        textAnchor="end"
      >
        LE
      </text>

      {/* TE label */}
      <text
        x={1.02}
        y={vbH * 0.08}
        className="fill-muted-foreground"
        fontSize={vbH * 0.08}
        fontFamily="var(--font-jetbrains-mono), monospace"
      >
        TE
      </text>
    </svg>
  );
}

// ── Main Panel ──────────────────────────────────────────────────

export function AirfoilPreviewViewerPanel({
  airfoilName,
  geometry,
  geometryLoading,
  analysisResult,
  re,
  ma,
  onReChange,
  onMaChange,
}: AirfoilPreviewViewerPanelProps) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-hidden p-4">
      {/* Header Row */}
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Airfoil Preview
        </span>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-primary">
          {airfoilName}
        </span>

        {/* Re input */}
        <div className="flex items-center gap-1.5">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            Re
          </span>
          <input
            type="number"
            value={re}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v)) onReChange(v);
            }}
            className="w-20 rounded-[--radius-s] border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
        </div>

        {/* Ma input */}
        <div className="flex items-center gap-1.5">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            Ma
          </span>
          <input
            type="number"
            step="0.01"
            value={ma}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v)) onMaChange(v);
            }}
            className="w-16 rounded-[--radius-s] border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
        </div>
      </div>

      {/* Geometry Section */}
      <div className="flex flex-1 flex-col rounded-[--radius-m] border border-border bg-card p-4">
        {/* Geometry header */}
        <div className="mb-3 flex items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
            Airfoil Geometry &mdash; {airfoilName}
          </span>
          <div className="flex-1" />
          {geometry && (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
              t/c = {geometry.maxThicknessPct}% &middot; camber ={" "}
              {geometry.maxCamberPct}%
            </span>
          )}
        </div>

        {/* SVG airfoil shape */}
        <div className="flex flex-1 items-center justify-center">
          {geometryLoading ? (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              Loading&hellip;
            </span>
          ) : geometry ? (
            <AirfoilSvg geometry={geometry} />
          ) : (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              No airfoil selected
            </span>
          )}
        </div>
      </div>

      {/* Polars Section */}
      <div className="flex gap-4">
        {analysisResult ? (
          <>
            <LineChart
              xData={analysisResult.alphaDeg}
              yData={analysisResult.cl}
              xLabel={"\u03B1 [\u00B0]"}
              yLabel="C_L"
              title="C_L vs \u03B1"
              annotation={
                analysisResult.clMax != null && analysisResult.alphaAtClMax != null
                  ? `C_L,max \u2248 ${analysisResult.clMax.toFixed(2)} @ ${analysisResult.alphaAtClMax.toFixed(0)}\u00B0`
                  : undefined
              }
              color="var(--color-primary)"
            />
            <LineChart
              xData={analysisResult.alphaDeg}
              yData={analysisResult.clOverCd}
              xLabel={"\u03B1 [\u00B0]"}
              yLabel="C_L / C_D"
              title="C_L / C_D vs \u03B1"
              annotation={
                analysisResult.ldMax != null && analysisResult.alphaAtLdMax != null
                  ? `L/D,max \u2248 ${analysisResult.ldMax.toFixed(1)} @ ${analysisResult.alphaAtLdMax.toFixed(0)}\u00B0`
                  : undefined
              }
              color="var(--color-success)"
            />
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center rounded-[--radius-m] border border-border bg-card p-8">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
              Run Analysis to see polars
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
