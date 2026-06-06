"use client";

import { useState, useMemo } from "react";
import { Maximize2, Minimize2, AlertTriangle } from "lucide-react";
import type { AirfoilGeometry } from "@/hooks/useAirfoilGeometry";
import type { AirfoilAnalysisResult } from "@/hooks/useAirfoilAnalysis";
import type { SuitabilityItem } from "@/hooks/useAirfoilSuitability";
import { interpolateY } from "@/hooks/useAirfoilGeometry";
import type { AircraftSpeedPolar } from "@/hooks/useSpeedPolar";
import { GeschwindigkeitspolareChart } from "@/components/workbench/GeschwindigkeitspolareChart";
import { AirfoilProxyChart } from "@/components/workbench/AirfoilProxyChart";

/** gh-839 ADDITIVE: a single operating point for alpha-diagram markers. */
export interface OperatingPoint {
  /** alpha in degrees — used as the x-coordinate on alpha-based charts */
  alpha: number;
  /** human-readable label for the legend */
  label: string;
}

/** gh-839 ADDITIVE: operating points for the three design-speed lenses. */
export interface OperatingPoints {
  cruise?: OperatingPoint;
  bestGlide?: OperatingPoint;
  minSink?: OperatingPoint;
}

interface AirfoilPreviewViewerPanelProps {
  rootAirfoilName: string;
  tipAirfoilName: string | null;
  rootGeometry: AirfoilGeometry | null;
  tipGeometry: AirfoilGeometry | null;
  geometryLoading: boolean;
  rootAnalysisResult: AirfoilAnalysisResult | null;
  tipAnalysisResult: AirfoilAnalysisResult | null;
  rootRe: number;
  tipRe: number | null;
  ma: number;
  onMaChange: (ma: number) => void;
  /** gh-822 ADDITIVE: operating α for the polar marker (degrees) */
  operatingAlphaDeg?: number;
  /**
   * gh-822 ADDITIVE: suitability item for the tip airfoil.
   * When present, tip_re_flag is the AUTHORITATIVE trigger for the tip-Re warning banner.
   * The arithmetic fallback (tipRe < rootRe) is only used when no suitability item is available.
   */
  tipSuitabilityItem?: SuitabilityItem;
  /**
   * gh-839 ADDITIVE: operating points for cruise/best-glide/min-sink.
   * Each point maps a target CL to an alpha via the analysis CL-alpha curve.
   * When provided, markers and a legend are added to the L/D and CL/CD charts.
   */
  operatingPoints?: OperatingPoints;
  /**
   * gh-841 ADDITIVE: aircraft speed polar from the backend (closed-form).
   * When provided, renders the Geschwindigkeitspolare chart with best-glide
   * and min-sink markers.
   */
  speedPolar?: AircraftSpeedPolar | null;
  /** gh-841 ADDITIVE: true while speed polar is loading from the backend. */
  speedPolarLoading?: boolean;
  /**
   * gh-840 ADDITIVE: as-built effective AoA from LiftingLine for the current
   * wing section.  When provided, a marker is added to the C_L-vs-α and
   * C_L/C_D-vs-α charts labelled 'As-built (Einstellwinkel+Schränkung+Trimm)'.
   */
  asBuiltAlphaDeg?: number | null;
}

const COLOR_ROOT = "#FF8400";
const COLOR_TIP = "#22D3EE";

// ── SVG Line Chart (follows AnalysisViewerPanel pattern) ────────

/** gh-839: a named marker on the chart (x, y in data coords) */
interface ChartMarker {
  x: number;
  y: number;
  color: string;
  testId: string;
  label?: string;
}

function LineChart({
  xData,
  yData,
  xData2,
  yData2,
  color2,
  label,
  label2,
  xLabel,
  yLabel,
  xFormat,
  title,
  annotation,
  color = "var(--color-primary)",
  onToggleMaximize,
  isMaximized,
  operatingX,
  operatingY,
  markers,
  showMarkersLegend,
}: Readonly<{
  xData: (number | null)[];
  yData: (number | null)[];
  xData2?: (number | null)[];
  yData2?: (number | null)[];
  color2?: string;
  label?: string;
  label2?: string;
  xLabel: string;
  yLabel: string;
  title: string;
  annotation?: string;
  color?: string;
  xFormat?: (v: number) => string;
  onToggleMaximize?: () => void;
  isMaximized?: boolean;
  /** gh-822: operating point marker x value (α in degrees for L/D chart) */
  operatingX?: number;
  /** gh-822: operating point marker y value (L/D at operating α) */
  operatingY?: number;
  /** gh-839: additional named markers (CL_max, L/D_max, operating points) */
  markers?: ChartMarker[];
  /** gh-839: when true, render a compact legend for markers */
  showMarkersLegend?: boolean;
}>) {
  const W = 400;
  const H = 200;
  const PAD = { top: 10, right: 15, bottom: 30, left: 45 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  // Filter to valid pairs only
  const valid = useMemo(() => {
    const pairs: { x: number; y: number }[] = [];
    for (let i = 0; i < xData.length; i++) {
      const x = xData[i];
      const y = yData[i];
      if (x != null && Number.isFinite(x) && y != null && Number.isFinite(y)) pairs.push({ x, y });
    }
    return pairs;
  }, [xData, yData]);

  const valid2 = useMemo(() => {
    if (!xData2 || !yData2) return [];
    const pairs: { x: number; y: number }[] = [];
    for (let i = 0; i < xData2.length; i++) {
      const x = xData2[i];
      const y = yData2[i];
      if (x != null && Number.isFinite(x) && y != null && Number.isFinite(y)) pairs.push({ x, y });
    }
    return pairs;
  }, [xData2, yData2]);

  if (valid.length === 0 && valid2.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-xl border border-border bg-card p-4">
        <span className="text-[12px] text-muted-foreground">No data</span>
      </div>
    );
  }

  const allPoints = [...valid, ...valid2];
  const xMin = Math.min(...allPoints.map((p) => p.x));
  const xMax = Math.max(...allPoints.map((p) => p.x));
  const yMin = Math.min(...allPoints.map((p) => p.y));
  const yMax = Math.max(...allPoints.map((p) => p.y));
  const xRange = xMax - xMin || 1;
  const yRange = yMax - yMin || 1;

  function sx(v: number) {
    return PAD.left + ((v - xMin) / xRange) * plotW;
  }
  function sy(v: number) {
    return PAD.top + plotH - ((v - yMin) / yRange) * plotH;
  }

  function buildPath(pts: { x: number; y: number }[]) {
    return pts
      .map(
        (p, i) =>
          `${i === 0 ? "M" : "L"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`,
      )
      .join(" ");
  }

  const pathD = buildPath(valid);
  const pathD2 = valid2.length > 0 ? buildPath(valid2) : null;

  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);
  const xTicks = Array.from({ length: 5 }, (_, i) => xMin + (xRange * i) / 4);

  const hasLegend = label && label2 && valid2.length > 0;

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
        {hasLegend && (
          <>
            <span className="ml-1 flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              <span
                className="inline-block size-[6px] rounded-full"
                style={{ backgroundColor: color }}
              />
              {label}
            </span>
            <span className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              <span
                className="inline-block size-[6px] rounded-full"
                style={{ backgroundColor: color2 }}
              />
              {label2}
            </span>
          </>
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
      <div className="rounded-xl border border-border bg-card p-2">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-full w-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Grid lines */}
          {yTicks.map((v) => (
            <line
              key={`yg${v}`}
              x1={PAD.left}
              x2={W - PAD.right}
              y1={sy(v)}
              y2={sy(v)}
              stroke="var(--color-border)"
              strokeWidth="0.5"
            />
          ))}
          {xTicks.map((v) => (
            <line
              key={`xg${v}`}
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
          {yTicks.map((v) => (
            <text
              key={`yl${v}`}
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
          {xTicks.map((v) => (
            <text
              key={`xl${v}`}
              x={sx(v)}
              y={PAD.top + plotH + 14}
              textAnchor="middle"
              fontSize="8"
              fill="var(--color-muted-foreground)"
              fontFamily="var(--font-jetbrains-mono)"
            >
              {xFormat ? xFormat(v) : `${v.toFixed(0)}\u00B0`}
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

          {/* Secondary data line (behind primary) */}
          {pathD2 && (
            <path
              d={pathD2}
              fill="none"
              stroke={color2 ?? COLOR_TIP}
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeDasharray="6 3"
            />
          )}

          {/* Primary data line */}
          {valid.length > 0 && (
            <path
              d={pathD}
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeLinejoin="round"
            />
          )}

          {/* gh-822: Operating point marker (legacy single-marker) */}
          {operatingX != null && operatingY != null && (
            <circle
              data-testid="operating-point-marker"
              cx={sx(operatingX)}
              cy={sy(operatingY)}
              r="4"
              fill={COLOR_ROOT}
              stroke="white"
              strokeWidth="1.5"
              opacity="0.9"
            />
          )}

          {/* gh-839: named markers (CL_max, L/D_max, operating points) */}
          {markers?.map((m) => {
            // Guard: only render when within the chart range
            if (!Number.isFinite(m.x) || !Number.isFinite(m.y)) return null;
            return (
              <circle
                key={m.testId}
                data-testid={m.testId}
                cx={sx(m.x)}
                cy={sy(m.y)}
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

      {/* gh-839: markers legend */}
      {showMarkersLegend && markers && markers.length > 0 && (
        <div
          data-testid="chart-markers-legend"
          className="flex flex-wrap items-center gap-x-3 gap-y-0.5 pt-1"
        >
          {markers.map((m) =>
            m.label ? (
              <span
                key={m.testId}
                className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[8px] text-muted-foreground"
              >
                <span
                  className="inline-block size-[5px] rounded-full"
                  style={{ backgroundColor: m.color }}
                />
                {m.label}
              </span>
            ) : null,
          )}
        </div>
      )}
    </div>
  );
}

// ── Airfoil SVG helpers ─────────────────────────────────────────

function pathFromCoords(coords: [number, number][]): string {
  if (coords.length === 0) return "";
  return coords
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]},${-p[1]}`)
    .join(" ");
}

function AirfoilSvg({
  rootGeometry,
  tipGeometry,
}: Readonly<{
  rootGeometry: AirfoilGeometry;
  tipGeometry: AirfoilGeometry | null;
}>) {
  const { upper, lower, maxThicknessX } = rootGeometry;

  // Compute viewbox from all geometries
  const allY = [
    ...upper.map((p) => p[1]),
    ...lower.map((p) => p[1]),
    ...(tipGeometry ? tipGeometry.upper.map((p) => p[1]) : []),
    ...(tipGeometry ? tipGeometry.lower.map((p) => p[1]) : []),
  ];
  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const yPad = (yMax - yMin) * 0.2;

  const vbX = -0.05;
  const vbW = 1.15;
  const vbH = yMax - yMin + 2 * yPad;

  // Build camber line for root only
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

  // Max thickness y-values at maxThicknessX (root only)
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

      {/* Tip airfoil (rendered behind root) */}
      {tipGeometry && (
        <>
          <path
            d={pathFromCoords(tipGeometry.upper)}
            fill="rgba(34, 211, 238, 0.06)"
            stroke={COLOR_TIP}
            strokeWidth={vbH * 0.012}
            strokeLinejoin="round"
            strokeDasharray={`${vbH * 0.04} ${vbH * 0.02}`}
          />
          <path
            d={pathFromCoords(tipGeometry.lower)}
            fill="rgba(34, 211, 238, 0.06)"
            stroke={COLOR_TIP}
            strokeWidth={vbH * 0.012}
            strokeLinejoin="round"
            strokeDasharray={`${vbH * 0.04} ${vbH * 0.02}`}
          />
        </>
      )}

      {/* Root upper surface */}
      <path
        d={pathFromCoords(upper)}
        fill="rgba(255, 132, 0, 0.12)"
        stroke={COLOR_ROOT}
        strokeWidth={vbH * 0.015}
        strokeLinejoin="round"
      />

      {/* Root lower surface */}
      <path
        d={pathFromCoords(lower)}
        fill="rgba(255, 132, 0, 0.12)"
        stroke={COLOR_ROOT}
        strokeWidth={vbH * 0.015}
        strokeLinejoin="round"
      />

      {/* Camber line (root only) */}
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

      {/* Max t/c annotation line (root) */}
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

// ── Helpers ─────────────────────────────────────────────────────

/** Marker colors (gh-839, gh-840) */
const COLOR_CLMAX = "#ef4444";
const COLOR_LDMAX = "#22c55e";
const COLOR_CRUISE = "#FF8400";
const COLOR_BEST_GLIDE = "#38bdf8";
const COLOR_MIN_SINK = "#a78bfa";
/** gh-840: as-built world AoA (LiftingLine result) — bright gold */
const COLOR_AS_BUILT = "#eab308";

/** Look up y-value at alpha x from two parallel arrays */
function lookupYAtX(
  xs: (number | null)[],
  ys: (number | null)[],
  targetX: number,
): number | null {
  if (xs.length === 0) return null;
  let closestIdx = 0;
  let closestDist = Math.abs((xs[0] ?? 0) - targetX);
  for (let i = 1; i < xs.length; i++) {
    const x = xs[i];
    if (x == null) continue;
    const d = Math.abs(x - targetX);
    if (d < closestDist) {
      closestDist = d;
      closestIdx = i;
    }
  }
  return ys[closestIdx] ?? null;
}

/** gh-839: build CL-alpha chart markers from analysis + optional operating points */
function buildClChartMarkers(
  result: AirfoilAnalysisResult,
  pts?: OperatingPoints,
  asBuiltAlphaDeg?: number | null,
): ChartMarker[] {
  const markers: ChartMarker[] = [];
  if (result.clMax != null && result.alphaAtClMax != null) {
    markers.push({
      x: result.alphaAtClMax,
      y: result.clMax,
      color: COLOR_CLMAX,
      testId: "clmax-marker",
      label: `C_L,max≈${result.clMax.toFixed(2)}`,
    });
  }
  if (pts?.cruise != null) {
    const y = lookupYAtX(result.alphaDeg, result.cl, pts.cruise.alpha);
    if (y != null) markers.push({ x: pts.cruise.alpha, y, color: COLOR_CRUISE, testId: "op-marker-cruise", label: pts.cruise.label });
  }
  if (pts?.bestGlide != null) {
    const y = lookupYAtX(result.alphaDeg, result.cl, pts.bestGlide.alpha);
    if (y != null) markers.push({ x: pts.bestGlide.alpha, y, color: COLOR_BEST_GLIDE, testId: "op-marker-best-glide", label: pts.bestGlide.label });
  }
  if (pts?.minSink != null) {
    const y = lookupYAtX(result.alphaDeg, result.cl, pts.minSink.alpha);
    if (y != null) markers.push({ x: pts.minSink.alpha, y, color: COLOR_MIN_SINK, testId: "op-marker-min-sink", label: pts.minSink.label });
  }
  // gh-840: as-built world AoA from LiftingLine
  if (asBuiltAlphaDeg != null && Number.isFinite(asBuiltAlphaDeg)) {
    const y = lookupYAtX(result.alphaDeg, result.cl, asBuiltAlphaDeg);
    if (y != null) {
      markers.push({
        x: asBuiltAlphaDeg,
        y,
        color: COLOR_AS_BUILT,
        testId: "as-built-aoa-marker-cl",
        label: `As-built (Einstellwinkel+Schränkung+Trimm) α=${asBuiltAlphaDeg.toFixed(1)}°`,
      });
    }
  }
  return markers;
}

/** gh-839: build L/D-alpha chart markers from analysis + optional operating points */
function buildLdChartMarkers(
  result: AirfoilAnalysisResult,
  pts?: OperatingPoints,
  asBuiltAlphaDeg?: number | null,
): ChartMarker[] {
  const markers: ChartMarker[] = [];
  if (result.ldMax != null && result.alphaAtLdMax != null) {
    markers.push({
      x: result.alphaAtLdMax,
      y: result.ldMax,
      color: COLOR_LDMAX,
      testId: "ldmax-marker",
      label: `L/D,max≈${result.ldMax.toFixed(1)}`,
    });
  }
  if (pts?.cruise != null) {
    const y = lookupYAtX(result.alphaDeg, result.clOverCd, pts.cruise.alpha);
    if (y != null) markers.push({ x: pts.cruise.alpha, y, color: COLOR_CRUISE, testId: "op-marker-cruise", label: pts.cruise.label });
  }
  if (pts?.bestGlide != null) {
    const y = lookupYAtX(result.alphaDeg, result.clOverCd, pts.bestGlide.alpha);
    if (y != null) markers.push({ x: pts.bestGlide.alpha, y, color: COLOR_BEST_GLIDE, testId: "op-marker-best-glide", label: pts.bestGlide.label });
  }
  if (pts?.minSink != null) {
    const y = lookupYAtX(result.alphaDeg, result.clOverCd, pts.minSink.alpha);
    if (y != null) markers.push({ x: pts.minSink.alpha, y, color: COLOR_MIN_SINK, testId: "op-marker-min-sink", label: pts.minSink.label });
  }
  // gh-840: as-built world AoA from LiftingLine
  if (asBuiltAlphaDeg != null && Number.isFinite(asBuiltAlphaDeg)) {
    const y = lookupYAtX(result.alphaDeg, result.clOverCd, asBuiltAlphaDeg);
    if (y != null) {
      markers.push({
        x: asBuiltAlphaDeg,
        y,
        color: COLOR_AS_BUILT,
        testId: "as-built-aoa-marker-ld",
        label: `As-built α=${asBuiltAlphaDeg.toFixed(1)}°`,
      });
    }
  }
  return markers;
}

export function AirfoilPreviewViewerPanel({
  rootAirfoilName,
  tipAirfoilName,
  rootGeometry,
  tipGeometry,
  geometryLoading,
  rootAnalysisResult,
  tipAnalysisResult,
  rootRe,
  tipRe,
  ma,
  onMaChange,
  operatingAlphaDeg,
  tipSuitabilityItem,
  operatingPoints,
  speedPolar,
  speedPolarLoading,
  asBuiltAlphaDeg,
}: Readonly<AirfoilPreviewViewerPanelProps>) {
  const [maximizedChart, setMaximizedChart] = useState<string | null>(null);

  function toggleChart(id: string) {
    setMaximizedChart((prev) => (prev === id ? null : id));
  }

  const hasTip = tipAirfoilName !== null && tipAirfoilName !== rootAirfoilName;

  // Build geometry stats string
  const geoStats = useMemo(() => {
    const parts: string[] = [];
    if (rootGeometry) {
      const prefix = hasTip ? "root: " : "";
      parts.push(
        `${prefix}t/c = ${rootGeometry.maxThicknessPct}% \u00B7 camber = ${rootGeometry.maxCamberPct}%`,
      );
    }
    if (hasTip && tipGeometry) {
      parts.push(
        `tip: t/c = ${tipGeometry.maxThicknessPct}% \u00B7 camber = ${tipGeometry.maxCamberPct}%`,
      );
    }
    return parts.join("  |  ");
  }, [rootGeometry, tipGeometry, hasTip]);

  // gh-822: tip-Re warning banner.
  // AUTHORITATIVE trigger: tipSuitabilityItem.tip_re_flag (set by the backend suitability scorer).
  // FALLBACK (no suitability data): arithmetic tipRe < rootRe check.
  const showTipReBanner = hasTip && (
    tipSuitabilityItem != null
      ? tipSuitabilityItem.tip_re_flag
      : (tipRe != null && tipRe < rootRe)
  );

  return (
    <div data-testid="airfoil-preview-charts" className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
      {/* gh-822: Tip-Re < Root-Re warning banner */}
      {showTipReBanner && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-[12px] text-red-300"
        >
          <AlertTriangle size={13} className="shrink-0" aria-hidden="true" />
          <span>
            Tip Re ({tipRe != null ? `${Math.round(tipRe / 1000)}k` : "—"}) &lt; Root Re ({Math.round(rootRe / 1000)}k) — tapered chord reduces effective Re at the tip.
          </span>
        </div>
      )}

      {/* Header Row */}
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Airfoil Preview
        </span>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px]" style={{ color: COLOR_ROOT }}>
          {rootAirfoilName}
        </span>
        {hasTip && (
          <>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
              /
            </span>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px]" style={{ color: COLOR_TIP }}>
              {tipAirfoilName}
            </span>
          </>
        )}

        {/* Re display (read-only, editing is in config panel) */}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          Re <span style={{ color: COLOR_ROOT }}>{(rootRe / 1000).toFixed(0)}k</span>
          {hasTip && tipRe != null && (
            <>{" / "}<span style={{ color: COLOR_TIP }}>{(tipRe / 1000).toFixed(0)}k</span></>
          )}
        </span>

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
              const v = Number.parseFloat(e.target.value);
              if (!Number.isNaN(v)) onMaChange(v);
            }}
            className="w-16 rounded-xl border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
        </div>
      </div>

      {/* Geometry Section */}
      <div className="flex flex-1 flex-col rounded-xl border border-border bg-card p-4">
        {/* Geometry header */}
        <div className="mb-3 flex items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
            Airfoil Geometry {"\u2014"}{" "}
            <span style={{ color: COLOR_ROOT }}>{rootAirfoilName}</span>
            {hasTip && (
              <>
                {" / "}
                <span style={{ color: COLOR_TIP }}>{tipAirfoilName}</span>
              </>
            )}
          </span>
          <div className="flex-1" />
          {geoStats && (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
              {geoStats}
            </span>
          )}
        </div>

        {/* SVG airfoil shape */}
        <div className="flex flex-1 items-center justify-center">
          {geometryLoading && (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              Loading{"\u2026"}
            </span>
          )}
          {!geometryLoading && rootGeometry && (
            <AirfoilSvg
              rootGeometry={rootGeometry}
              tipGeometry={hasTip ? tipGeometry : null}
            />
          )}
          {!geometryLoading && !rootGeometry && (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
              No airfoil selected
            </span>
          )}
        </div>
      </div>

      {/* Polars Section */}
      {rootAnalysisResult ? (
        (() => {
          const tip = hasTip ? tipAnalysisResult : null;
          const seriesLabel = hasTip ? "root" : undefined;
          const seriesLabel2 = hasTip ? "tip" : undefined;

          // gh-822: Find L/D value at operating alpha for the marker
          const operatingLdAtAlpha: number | undefined = (() => {
            if (operatingAlphaDeg == null) return undefined;
            // Guard: empty alphaDeg array yields no marker
            const alphas = rootAnalysisResult.alphaDeg;
            if (alphas.length === 0) return undefined;
            let closestIdx = 0;
            let closestDist = Math.abs((alphas[0] ?? 0) - operatingAlphaDeg);
            for (let i = 1; i < alphas.length; i++) {
              const d = Math.abs(alphas[i] - operatingAlphaDeg);
              if (d < closestDist) {
                closestDist = d;
                closestIdx = i;
              }
            }
            const ld = rootAnalysisResult.clOverCd[closestIdx];
            return ld != null ? ld : undefined;
          })();

          // gh-839/840: build named markers (design-speed OPs + as-built world AoA)
          const clChartMarkers = buildClChartMarkers(rootAnalysisResult, operatingPoints, asBuiltAlphaDeg);
          const ldChartMarkers = buildLdChartMarkers(rootAnalysisResult, operatingPoints, asBuiltAlphaDeg);
          const hasAnyOperatingPoints =
            operatingPoints?.cruise != null ||
            operatingPoints?.bestGlide != null ||
            operatingPoints?.minSink != null;

          const allCharts = [
            {
              id: "cl",
              xData: rootAnalysisResult.alphaDeg,
              yData: rootAnalysisResult.cl,
              xData2: tip?.alphaDeg,
              yData2: tip?.cl,
              xLabel: "\u03B1 [\u00B0]",
              yLabel: "C_L",
              title: "C_L vs \u03B1",
              annotation:
                rootAnalysisResult.clMax != null && rootAnalysisResult.alphaAtClMax != null
                  ? `C_L,max \u2248 ${rootAnalysisResult.clMax.toFixed(2)} @ ${rootAnalysisResult.alphaAtClMax.toFixed(0)}\u00B0`
                  : undefined,
              color: COLOR_ROOT,
              color2: COLOR_TIP,
              label: seriesLabel,
              label2: seriesLabel2,
              markers: clChartMarkers.length > 0 ? clChartMarkers : undefined,
            },
            {
              id: "cd",
              xData: rootAnalysisResult.alphaDeg,
              yData: rootAnalysisResult.cd,
              xData2: tip?.alphaDeg,
              yData2: tip?.cd,
              xLabel: "\u03B1 [\u00B0]",
              yLabel: "C_D",
              title: "C_D vs \u03B1",
              color: "var(--color-destructive)",
              color2: COLOR_TIP,
              label: seriesLabel,
              label2: seriesLabel2,
            },
            {
              id: "ld",
              xData: rootAnalysisResult.alphaDeg,
              yData: rootAnalysisResult.clOverCd,
              xData2: tip?.alphaDeg,
              yData2: tip?.clOverCd,
              xLabel: "\u03B1 [\u00B0]",
              yLabel: "C_L / C_D",
              title: "C_L / C_D vs \u03B1",
              annotation:
                rootAnalysisResult.ldMax != null && rootAnalysisResult.alphaAtLdMax != null
                  ? `L/D,max \u2248 ${rootAnalysisResult.ldMax.toFixed(1)} @ ${rootAnalysisResult.alphaAtLdMax.toFixed(0)}\u00B0`
                  : undefined,
              color: "var(--color-success)",
              color2: COLOR_TIP,
              label: seriesLabel,
              label2: seriesLabel2,
              // gh-822: operating point marker on L/D chart (legacy single marker)
              operatingX: operatingAlphaDeg,
              operatingY: operatingLdAtAlpha,
              // gh-839: named markers + legend
              markers: ldChartMarkers.length > 0 ? ldChartMarkers : undefined,
              showMarkersLegend: hasAnyOperatingPoints && ldChartMarkers.length > 0,
            },
            {
              id: "polar",
              xData: rootAnalysisResult.cd,
              yData: rootAnalysisResult.cl,
              xData2: tip?.cd,
              yData2: tip?.cl,
              xLabel: "C_D",
              yLabel: "C_L",
              title: "C_L vs C_D (drag polar)",
              color: COLOR_ROOT,
              color2: COLOR_TIP,
              label: seriesLabel,
              label2: seriesLabel2,
              xFormat: (v: number) => v.toFixed(3),
            },
            {
              id: "cm",
              xData: rootAnalysisResult.alphaDeg,
              yData: rootAnalysisResult.cm,
              xData2: tip?.alphaDeg,
              yData2: tip?.cm,
              xLabel: "\u03B1 [\u00B0]",
              yLabel: "C_m",
              title: "C_m vs \u03B1",
              color: "#A78BFA",
              color2: COLOR_TIP,
              label: seriesLabel,
              label2: seriesLabel2,
            },
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
        <div className="flex flex-1 items-center justify-center rounded-xl border border-border bg-card p-8">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Run Analysis to see polars
          </span>
        </div>
      )}

      {/* gh-841: Geschwindigkeitspolare + 2D airfoil proxy charts */}
      <div className="grid grid-cols-2 gap-4 rounded-xl border border-border bg-card p-4">
        <div className="flex flex-col">
          <GeschwindigkeitspolareChart
            polar={speedPolar ?? null}
            isLoading={speedPolarLoading}
          />
        </div>
        <div className="flex flex-col">
          <AirfoilProxyChart analysisResult={rootAnalysisResult} />
        </div>
      </div>
    </div>
  );
}
