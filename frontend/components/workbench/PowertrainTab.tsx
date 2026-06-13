"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import {
  usePowertrainSolutionSpace,
  type SolutionSpaceAssumptions,
  type SolutionRow,
  type FeasibleRegion,
  type ShoppingSpec,
} from "@/hooks/usePowertrainSolutionSpace";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  readonly aeroplaneId: string;
}

// ---------------------------------------------------------------------------
// Column-filter state
// ---------------------------------------------------------------------------

interface ColumnFilters {
  maxPeakA: string;
  maxMah: string;
  maxEscA: string;
  catalogOnly: boolean;
}

// ---------------------------------------------------------------------------
// Plotly helpers
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type PlotlyTrace = Record<string, any>;

const CELL_COLORS = [
  "#FF8400",
  "#3B82F6",
  "#30A46C",
  "#E5484D",
  "#A78BFA",
  "#F59E0B",
  "#06B6D4",
];

function cellColor(idx: number): string {
  return CELL_COLORS[idx % CELL_COLORS.length];
}

// ---------------------------------------------------------------------------
// Conservative (worst-case, low-η) minimum specs
// ---------------------------------------------------------------------------
//
// The table / plot / shopping-spec columns are MINIMUM specs to buy: a part
// bought at the shown value must be guaranteed sufficient across the whole
// η_prop band. So we take the WORST case (the `_hi` band, which corresponds to
// low prop efficiency → more current / capacity / C-rate) and round UP, so a
// part chosen at the displayed number is never under-spec.
//
// NOTE on mAh: do NOT divide by DoD. DoD is already applied upstream in
// `energy_wh` (E = P·t / DoD), so `capacity_mah_min_hi` is already the rated
// pack capacity — dividing again would double-count it.

export interface ConservativeSpec {
  /** Worst-case peak current [A] (low-η end of the band); null if unavailable. */
  peakA: number | null;
  /** Minimum ESC current rating [A], rounded up; null if unavailable. */
  escMinA: number | null;
  /** Minimum battery C-rating, rounded up; null if unavailable. */
  minC: number | null;
  /** Minimum (rated pack) capacity [mAh], rounded up; null if unavailable. */
  mahMin: number | null;
  /** Conservative shaft (motor) power [W], rounded up; null if unavailable. */
  motorW: number | null;
}

/** First finite number from the candidates, or null if none is usable.
 *
 * Lets each conservative field degrade gracefully: prefer the worst-case `_hi`
 * band, fall back to the mid value if the band field is absent (contract
 * drift), then render "—" rather than crashing the tab.
 */
function firstFinite(...candidates: Array<number | null | undefined>): number | null {
  for (const v of candidates) {
    if (typeof v === "number" && Number.isFinite(v)) return v;
  }
  return null;
}

/** Math.ceil that tolerates null/undefined/non-finite, returning null. */
function ceilOrNull(value: number | null): number | null {
  return value == null ? null : Math.ceil(value);
}

/** Conservative shaft power [W] = aero power at top speed / lowest prop η.
 *
 * Returns null when the inputs are not usable so the caller can render "—".
 */
export function conservativeMotorW(
  pAeroTopW: number | null | undefined,
  etaPropLo: number | null | undefined
): number | null {
  if (pAeroTopW == null || !Number.isFinite(pAeroTopW)) return null;
  if (etaPropLo == null || !Number.isFinite(etaPropLo) || etaPropLo <= 0) {
    return Math.ceil(pAeroTopW);
  }
  return Math.ceil(pAeroTopW / etaPropLo);
}

/** Build the conservative, rounded-up minimum specs for one solution row.
 *
 * Band field names match the backend SolutionRow schema EXACTLY:
 *   i_peak_hi_a, esc_min_hi_a, c_min_hi, capacity_mah_min_hi.
 * Each access falls back to the mid value (i_peak_a, esc_min_a, …) and finally
 * to null, so a contract drift degrades to "—" instead of white-screening.
 */
export function conservativeSpec(
  row: SolutionRow,
  pAeroTopW: number | null | undefined,
  etaPropLo: number | null | undefined
): ConservativeSpec {
  return {
    peakA: firstFinite(row.i_peak_hi_a, row.i_peak_a),
    escMinA: ceilOrNull(firstFinite(row.esc_min_hi_a, row.esc_min_a)),
    minC: ceilOrNull(firstFinite(row.c_min_hi, row.c_min)),
    mahMin: ceilOrNull(firstFinite(row.capacity_mah_min_hi, row.capacity_mah_min)),
    motorW: conservativeMotorW(pAeroTopW, etaPropLo),
  };
}

/** Format a possibly-null conservative number, rendering "—" when missing. */
function fmtSpec(value: number | null, digits = 0): string {
  return value == null ? "—" : value.toFixed(digits);
}

// ---------------------------------------------------------------------------
// Trace builders (module-level to avoid sonar nested-functions violations)
// ---------------------------------------------------------------------------

function buildFloorCurveTrace(
  region: FeasibleRegion,
  color: string,
  isSelected: boolean
): PlotlyTrace {
  return {
    x: region.capacity_curve_mah,
    y: region.c_rate_curve,
    type: "scatter",
    mode: "lines",
    name: `${region.cell_count}S floor`,
    line: {
      color,
      width: isSelected ? 2.5 : 1.5,
      dash: isSelected ? "solid" : "dot",
    },
    legendgroup: `${region.cell_count}S`,
    hovertemplate:
      `<b>${region.cell_count}S</b><br>` +
      `Capacity: %{x:.0f} mAh<br>Min C-rate: %{y:.1f}C<extra></extra>`,
  };
}

function buildCapacityFloorLineTrace(
  region: FeasibleRegion,
  color: string,
  cMax: number
): PlotlyTrace {
  return {
    x: [region.capacity_floor_mah, region.capacity_floor_mah],
    y: [0, cMax],
    type: "scatter",
    mode: "lines",
    name: `${region.cell_count}S cap-floor`,
    line: { color, width: 1, dash: "dot" },
    legendgroup: `${region.cell_count}S`,
    showlegend: false,
    hovertemplate:
      `<b>${region.cell_count}S</b><br>` +
      `Min capacity: ${region.capacity_floor_mah.toFixed(0)} mAh<extra></extra>`,
  };
}

function buildMarkerTrace(
  region: FeasibleRegion,
  row: SolutionRow,
  color: string,
  isSelected: boolean
): PlotlyTrace {
  // Marker sits at the CONSERVATIVE worst-case point (ceil(capacity_mah_min_hi),
  // ceil(c_min_hi)) so it lines up with the rounded-up minimum specs in the
  // table and shopping spec. Shares conservativeSpec() so the correct backend
  // field names + null guards apply consistently. Plot inputs are not used here,
  // so motorW is irrelevant to the marker (null pAeroTopW is fine).
  const spec = conservativeSpec(row, null, null);
  const markerMah = spec.mahMin;
  const markerC = spec.minC;
  return {
    x: [markerMah],
    y: [markerC],
    type: "scatter",
    mode: "markers+text",
    name: `${region.cell_count}S`,
    text: [`${region.cell_count}S`],
    textposition: "top center",
    textfont: { size: 9, color },
    legendgroup: `${region.cell_count}S`,
    marker: {
      color,
      size: isSelected ? 14 : 9,
      symbol: isSelected ? "star" : "circle",
      line: { color: isSelected ? "#fff" : color, width: isSelected ? 2 : 1 },
    },
    hovertemplate:
      `<b>${region.cell_count}S</b><br>` +
      `Capacity ≥ ${fmtSpec(markerMah)} mAh<br>` +
      `Min C-rating ≥ ${fmtSpec(markerC)}C<extra></extra>`,
    customdata: [region.cell_count],
  };
}

function buildRegionAnnotations(
  vCruiseMps: number,
  vTopMps: number,
  tTargetMin: number
): PlotlyTrace[] {
  const titleText =
    `V_cruise = ${vCruiseMps.toFixed(1)} m/s  ·  ` +
    `V_top = ${vTopMps.toFixed(1)} m/s  ·  ` +
    `t = ${tTargetMin.toFixed(0)} min`;
  return [
    {
      x: 0.01, y: -0.13, xref: "paper", yref: "paper",
      xanchor: "left", yanchor: "top", showarrow: false,
      font: { color: "#71717A", size: 9 },
      text: titleText,
    },
    {
      x: 0.99, y: 0.01, xref: "paper", yref: "paper",
      xanchor: "right", yanchor: "bottom", showarrow: false,
      font: { color: "#52525B", size: 9 },
      text: "Feasible region: ↗ (more mAh or higher C-rate = OK)",
    },
    {
      x: 0.99, y: 0.10, xref: "paper", yref: "paper",
      xanchor: "right", yanchor: "bottom", showarrow: false,
      font: { color: "#52525B", size: 9 },
      text: "Feasible = on/above the curve (battery can supply enough current)",
    },
  ];
}

function buildFeasibleRegionTraces(
  regions: FeasibleRegion[],
  rows: SolutionRow[],
  selectedCellCount: number | null
): PlotlyTrace[] {
  const allCRates = regions.flatMap((r) => r.c_rate_curve).filter(isFinite);
  const cMax = allCRates.length > 0 ? Math.max(...allCRates) * 1.15 : 30;

  const traces: PlotlyTrace[] = [];
  regions.forEach((region, idx) => {
    const color = cellColor(idx);
    const isSelected = region.cell_count === selectedCellCount;
    const row = rows.find((r) => r.cell_count === region.cell_count);

    traces.push(buildFloorCurveTrace(region, color, isSelected));
    traces.push(buildCapacityFloorLineTrace(region, color, cMax));
    if (row) {
      traces.push(buildMarkerTrace(region, row, color, isSelected));
    }
  });
  return traces;
}

function buildFeasibleRegionLayout(
  vCruiseMps: number,
  vTopMps: number,
  tTargetMin: number
) {
  return {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#A1A1AA", family: "JetBrains Mono, monospace", size: 10 },
    // b:70 so the bottom mission-metadata annotation (y:-0.13) is fully visible.
    margin: { l: 55, r: 15, t: 45, b: 70 },
    title: {
      text: "Capacity × C-rate feasible region",
      font: { color: "#E4E4E7", size: 12 },
      x: 0.01,
      xanchor: "left",
    },
    xaxis: {
      title: { text: "Capacity [mAh]", font: { size: 11 } },
      gridcolor: "#27272A",
      zerolinecolor: "#3F3F46",
    },
    yaxis: {
      title: { text: "Min C-rate [C]", font: { size: 11 } },
      gridcolor: "#27272A",
      zerolinecolor: "#3F3F46",
      rangemode: "tozero",
    },
    legend: {
      x: 0.99, y: 0.99, xanchor: "right", yanchor: "top",
      bgcolor: "rgba(0,0,0,0.4)", bordercolor: "#3F3F46", borderwidth: 1,
      font: { size: 10, color: "#A1A1AA" },
    },
    showlegend: true,
    autosize: true,
    annotations: buildRegionAnnotations(vCruiseMps, vTopMps, tTargetMin),
  };
}

// ---------------------------------------------------------------------------
// Feasible-Region Plotly plot (gh-977)
// ---------------------------------------------------------------------------

interface FeasibleRegionPlotProps {
  readonly regions: FeasibleRegion[];
  readonly rows: SolutionRow[];
  readonly selectedCellCount: number | null;
  readonly onSelectCellCount: (s: number) => void;
  readonly vCruiseMps: number;
  readonly vTopMps: number;
  readonly tTargetMin: number;
}

function FeasibleRegionPlot({
  regions,
  rows,
  selectedCellCount,
  onSelectCellCount,
  vCruiseMps,
  vTopMps,
  tTargetMin,
}: FeasibleRegionPlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const plotlyRef = useRef<any>(null);

  // Draw effect: (re)render the figure. Depends on selectedCellCount so the
  // marker re-styles (star ↔ circle) on selection — but this effect must NOT
  // bind the click listener (that would accumulate handlers on every redraw).
  useEffect(() => {
    const node = containerRef.current;
    if (!node || regions.length === 0) return;

    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      plotlyRef.current = Plotly;
      if (disposed || !node) return;

      const traces = buildFeasibleRegionTraces(regions, rows, selectedCellCount);
      const layout = buildFeasibleRegionLayout(vCruiseMps, vTopMps, tTargetMin);

      await Plotly.react(node, traces, layout, {
        responsive: true,
        displayModeBar: false,
      });
    })();

    return () => {
      disposed = true;
    };
  }, [regions, rows, selectedCellCount, vCruiseMps, vTopMps, tTargetMin]);

  // Click effect: bind the marker → cell-count selection handler exactly once
  // per (rows, onSelectCellCount) identity. It deliberately does NOT depend on
  // selectedCellCount, so selecting a cell does not re-bind the listener.
  // Cleanup removes the listener to prevent accumulation / leaks.
  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    let disposed = false;

    (async () => {
      // Ensure Plotly has attached its event emitter to the node before we bind.
      const Plotly = plotlyRef.current ?? (await import("plotly.js-gl3d-dist-min"));
      plotlyRef.current = Plotly;
      if (disposed) return;

      // Plotly attaches `.on()` to the container div — guard for jsdom / SSR.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const plotNode = node as any;
      if (typeof plotNode.on === "function") {
        plotNode.on("plotly_click", (eventData: { points: Array<{ customdata: number }> }) => {
          const pt = eventData?.points?.[0];
          if (pt?.customdata != null) {
            onSelectCellCount(pt.customdata);
          }
        });
      }
    })();

    return () => {
      disposed = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const plotNode = node as any;
      if (typeof plotNode.removeAllListeners === "function") {
        plotNode.removeAllListeners("plotly_click");
      }
    };
  }, [rows, onSelectCellCount]);

  // Cleanup: purge the Plotly figure on unmount.
  useEffect(() => {
    const node = containerRef.current;
    return () => {
      if (node && plotlyRef.current) {
        plotlyRef.current.purge(node);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full"
      style={{ height: 320 }}
      data-testid="powertrain-feasible-region-plot"
    />
  );
}

// ---------------------------------------------------------------------------
// Shopping spec line
// ---------------------------------------------------------------------------

function ShoppingSpecLine({
  spec,
  conservative,
}: Readonly<{
  spec: ShoppingSpec | undefined;
  conservative: ConservativeSpec | undefined;
}>) {
  if (!spec || !conservative) return null;
  // ESC / battery mAh / C-rating / motor W all use the CONSERVATIVE worst-case,
  // rounded-up figures so a part bought at these values is never under-spec.
  // Cell count, nominal voltage and KV come from the matching shopping spec.
  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card px-4 py-3 font-[family-name:var(--font-jetbrains-mono)] text-[12px]"
      data-testid="shopping-spec-line"
    >
      <span className="text-muted-foreground">
        Shopping spec ({spec.cell_count}S @ {spec.battery_v_nom.toFixed(1)} V):
      </span>
      <span className="text-orange-400">
        ESC ≥ {fmtSpec(conservative.escMinA)} A
      </span>
      <span className="text-muted-foreground">·</span>
      <span className="text-blue-400">
        Battery ≥ {fmtSpec(conservative.mahMin)} mAh @ ≥{fmtSpec(conservative.minC)}C
      </span>
      <span className="text-muted-foreground">·</span>
      <span className="text-emerald-400">
        Motor ≥ {fmtSpec(conservative.motorW)} W
        {spec.kv_approx != null ? `, KV ≈ ${spec.kv_approx.toFixed(0)}` : ""}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Solution table
// ---------------------------------------------------------------------------

interface SolutionTableProps {
  readonly rows: SolutionRow[];
  readonly filters: ColumnFilters;
  readonly selectedCellCount: number | null;
  readonly onSelectRow: (cellCount: number) => void;
  /** Aero power at top speed [W] — feeds the conservative motor-W column. */
  readonly pAeroTopW: number;
  /** Low end of the prop-efficiency band — feeds the conservative motor-W. */
  readonly etaPropLo: number;
}

function SolutionTable({
  rows,
  filters,
  selectedCellCount,
  onSelectRow,
  pAeroTopW,
  etaPropLo,
}: SolutionTableProps) {
  const maxPeakA = filters.maxPeakA !== "" ? parseFloat(filters.maxPeakA) : null;
  const maxMah = filters.maxMah !== "" ? parseFloat(filters.maxMah) : null;
  const maxEscA = filters.maxEscA !== "" ? parseFloat(filters.maxEscA) : null;

  // Filters compare against the CONSERVATIVE displayed values (the same numbers
  // the user sees and shops against), not the mid-band internals. A null spec
  // value (missing band field) is treated as "not excluded" so the row still
  // shows (and renders "—") rather than silently vanishing.
  const filtered = rows.filter((r) => {
    if (filters.catalogOnly && !r.has_motor_match && !r.has_battery_match && !r.has_esc_match)
      return false;
    const spec = conservativeSpec(r, pAeroTopW, etaPropLo);
    if (maxPeakA != null && spec.peakA != null && spec.peakA > maxPeakA) return false;
    if (maxMah != null && spec.mahMin != null && spec.mahMin > maxMah) return false;
    if (maxEscA != null && spec.escMinA != null && spec.escMinA > maxEscA) return false;
    return true;
  });

  return (
    <div className="overflow-x-auto" data-testid="solution-table">
      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr className="border-b border-border text-left font-[family-name:var(--font-geist-sans)] text-[10px] uppercase tracking-wider text-muted-foreground">
            <th scope="col" className="py-2 pr-3">S</th>
            <th scope="col" className="py-2 pr-3">V_nom (V)</th>
            <th scope="col" className="py-2 pr-3">Motor (W)</th>
            <th scope="col" className="py-2 pr-3">Peak A</th>
            <th scope="col" className="py-2 pr-3">ESC min (A)</th>
            <th scope="col" className="py-2 pr-3">mAh min</th>
            <th
              scope="col"
              className="py-2 pr-3"
              title="minimum battery C-rating you need"
            >
              Min C-rating
            </th>
            <th scope="col" className="py-2 pr-3">Wh</th>
            <th scope="col" className="py-2 pr-3" title="(pick nearest standard KV)">
              KV
            </th>
            <th scope="col" className="py-2" title="(coming soon — parts DB)">
              Catalog
            </th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 && (
            <tr>
              <td
                colSpan={10}
                className="py-4 text-center font-[family-name:var(--font-geist-sans)] text-muted-foreground"
                data-testid="solution-table-empty"
              >
                No solutions match the current filters.
              </td>
            </tr>
          )}
          {filtered.map((row) => {
            const isSelected = row.cell_count === selectedCellCount;
            const hasCatalog =
              row.has_motor_match || row.has_battery_match || row.has_esc_match;
            const spec = conservativeSpec(row, pAeroTopW, etaPropLo);
            return (
              <tr
                key={row.cell_count}
                onClick={() => onSelectRow(row.cell_count)}
                className={`cursor-pointer border-b border-border/50 font-[family-name:var(--font-jetbrains-mono)] transition-colors hover:bg-sidebar-accent ${
                  isSelected ? "bg-orange-500/10" : ""
                }`}
                data-testid={`solution-row-${row.cell_count}`}
                aria-selected={isSelected}
              >
                <td className="py-2 pr-3 font-semibold text-orange-400">
                  {row.cell_count}S
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {row.v_nom_v.toFixed(1)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {fmtSpec(spec.motorW)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {fmtSpec(spec.peakA, 1)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {fmtSpec(spec.escMinA)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {fmtSpec(spec.mahMin)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {fmtSpec(spec.minC)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {row.energy_wh.toFixed(1)}
                </td>
                <td className="py-2 pr-3 text-muted-foreground">
                  {row.kv_approx != null ? row.kv_approx.toFixed(0) : "—"}
                </td>
                <td
                  className={`py-2 ${hasCatalog ? "text-emerald-400" : "text-muted-foreground"}`}
                >
                  {hasCatalog ? (
                    <span aria-label="catalog match available">✓</span>
                  ) : (
                    "—"
                  )}
                  {row.has_motor_match && (
                    <span
                      className="ml-1 text-[9px] text-emerald-400"
                      title="Motor match"
                    >
                      M
                    </span>
                  )}
                  {row.has_battery_match && (
                    <span
                      className="ml-1 text-[9px] text-emerald-400"
                      title="Battery match"
                    >
                      B
                    </span>
                  )}
                  {row.has_esc_match && (
                    <span
                      className="ml-1 text-[9px] text-emerald-400"
                      title="ESC match"
                    >
                      E
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Assumption controls
// ---------------------------------------------------------------------------

const DEFAULT_CELL_COUNTS = [2, 3, 4, 6];
const PROP_PD_PRESETS = [
  { label: "3D (0.50)", value: 0.5 },
  { label: "Trainer (0.65)", value: 0.65 },
  { label: "Soarer (0.80)", value: 0.8 },
  { label: "Speed (1.00)", value: 1.0 },
];

interface AssumptionControlsProps {
  readonly assumptions: SolutionSpaceAssumptions;
  readonly onChange: (next: SolutionSpaceAssumptions) => void;
  /** True when V_top is not user-set and is derived from the mission instead. */
  readonly vTopAutoDerived: boolean;
}

/** A single numeric assumption input.
 *
 * Module-level (not re-created each render) so React keeps a stable element
 * identity. Clearing the input yields `parseFloat("") === NaN`; we coerce that
 * to `undefined` so the key is omitted from the assumptions object rather than
 * serialized as `null` (which would mislead the backend into the "recompute
 * first" path). Same omission semantics as the v_top_mps field.
 */
function NumField({
  assumptions,
  fieldKey,
  value,
  defaultVal,
  onChange,
  testId,
}: Readonly<{
  assumptions: SolutionSpaceAssumptions;
  fieldKey: keyof SolutionSpaceAssumptions;
  value: number | undefined;
  defaultVal: number;
  onChange: (next: SolutionSpaceAssumptions) => void;
  testId?: string;
}>) {
  return (
    <input
      type="number"
      value={value ?? defaultVal}
      step={0.01}
      onChange={(e) => {
        const raw = e.target.value;
        const parsed = parseFloat(raw);
        const next: number | undefined =
          raw === "" || Number.isNaN(parsed) ? undefined : parsed;
        onChange({ ...assumptions, [fieldKey]: next });
      }}
      className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
      data-testid={testId}
    />
  );
}

function AssumptionControls({
  assumptions,
  onChange,
  vTopAutoDerived,
}: AssumptionControlsProps) {
  const cellCounts = assumptions.cell_counts ?? DEFAULT_CELL_COUNTS;

  function toggleCellCount(s: number) {
    const next = cellCounts.includes(s)
      ? cellCounts.filter((c) => c !== s)
      : [...cellCounts, s].sort((a, b) => a - b);
    onChange({ ...assumptions, cell_counts: next });
  }

  return (
    <div
      className="flex flex-wrap items-start gap-4 rounded-xl border border-border bg-card px-4 py-3"
      data-testid="assumption-controls"
    >
      {/* Cell count multi-select */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          Cell count S
        </span>
        <div className="flex gap-1">
          {[2, 3, 4, 5, 6, 7, 8].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => toggleCellCount(s)}
              className={`rounded px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[11px] transition-colors ${
                cellCounts.includes(s)
                  ? "bg-orange-500/20 text-orange-400"
                  : "bg-card-muted text-muted-foreground hover:text-foreground"
              }`}
              data-testid={`cell-count-btn-${s}`}
              aria-pressed={cellCounts.includes(s)}
            >
              {s}S
            </button>
          ))}
        </div>
      </div>

      {/* η_prop band */}
      <div className="flex flex-col gap-1">
        <span
          className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground"
          title="Propeller efficiency band (low / high). Conservative minimum specs use the low end."
        >
          Prop efficiency [lo / hi]
        </span>
        <div className="flex items-center gap-1">
          <NumField
            assumptions={assumptions}
            fieldKey="eta_prop_lo"
            value={assumptions.eta_prop_lo}
            defaultVal={0.65}
            onChange={onChange}
          />
          <span className="text-muted-foreground">/</span>
          <NumField
            assumptions={assumptions}
            fieldKey="eta_prop_hi"
            value={assumptions.eta_prop_hi}
            defaultVal={0.78}
            onChange={onChange}
          />
        </div>
      </div>

      {/* DoD */}
      <div className="flex flex-col gap-1">
        <span
          className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground"
          title="Depth of discharge — usable battery %"
        >
          DoD
        </span>
        <NumField
          assumptions={assumptions}
          fieldKey="dod"
          value={assumptions.dod}
          defaultVal={0.8}
          onChange={onChange}
        />
      </div>

      {/* ESC margin */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          ESC margin ×
        </span>
        <NumField
          assumptions={assumptions}
          fieldKey="esc_margin"
          value={assumptions.esc_margin}
          defaultVal={1.4}
          onChange={onChange}
        />
      </div>

      {/* C margin */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          C margin ×
        </span>
        <NumField
          assumptions={assumptions}
          fieldKey="c_margin"
          value={assumptions.c_margin}
          defaultVal={1.25}
          onChange={onChange}
        />
      </div>

      {/* Prop P/D preset */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          Prop P/D (mission)
        </span>
        <select
          value={String(assumptions.prop_pd ?? 0.65)}
          onChange={(e) =>
            onChange({ ...assumptions, prop_pd: parseFloat(e.target.value) })
          }
          className="rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          data-testid="prop-pd-select"
        >
          {PROP_PD_PRESETS.map((p) => (
            <option key={p.value} value={String(p.value)}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* t_target_min */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          Flight time (min)
        </span>
        <input
          type="number"
          value={assumptions.t_target_min ?? 15}
          min={1}
          step={1}
          onChange={(e) => {
            const raw = e.target.value;
            const parsed = parseFloat(raw);
            onChange({
              ...assumptions,
              t_target_min: raw === "" || Number.isNaN(parsed) ? undefined : parsed,
            });
          }}
          className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          data-testid="t-target-input"
        />
      </div>

      {/* v_top_mps */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          V_top (m/s)
          {vTopAutoDerived && (
            <span className="ml-1 text-[9px] text-subtle-foreground" data-testid="v-top-from-mission">
              (from Mission)
            </span>
          )}
        </span>
        <input
          type="number"
          value={assumptions.v_top_mps ?? ""}
          min={0}
          step={0.5}
          placeholder="auto"
          onChange={(e) => {
            const v = e.target.value;
            onChange({
              ...assumptions,
              v_top_mps: v === "" ? undefined : parseFloat(v),
            });
          }}
          className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          data-testid="v-top-input"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Column filter bar
// ---------------------------------------------------------------------------

interface FilterBarProps {
  readonly filters: ColumnFilters;
  readonly onChange: (next: ColumnFilters) => void;
}

function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-2"
      data-testid="filter-bar"
    >
      <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
        Filter:
      </span>
      <label className="flex items-center gap-1 font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
        Peak A ≤
        <input
          type="number"
          value={filters.maxPeakA}
          placeholder="—"
          min={0}
          step={1}
          onChange={(e) => onChange({ ...filters, maxPeakA: e.target.value })}
          className="ml-1 w-16 rounded border border-border bg-card-muted px-1 py-0.5 text-[11px] text-foreground"
          data-testid="filter-peak-a"
        />
      </label>
      <label className="flex items-center gap-1 font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
        mAh ≤
        <input
          type="number"
          value={filters.maxMah}
          placeholder="—"
          min={0}
          step={100}
          onChange={(e) => onChange({ ...filters, maxMah: e.target.value })}
          className="ml-1 w-20 rounded border border-border bg-card-muted px-1 py-0.5 text-[11px] text-foreground"
          data-testid="filter-mah"
        />
      </label>
      <label className="flex items-center gap-1 font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
        ESC ≤
        <input
          type="number"
          value={filters.maxEscA}
          placeholder="—"
          min={0}
          step={1}
          onChange={(e) => onChange({ ...filters, maxEscA: e.target.value })}
          className="ml-1 w-16 rounded border border-border bg-card-muted px-1 py-0.5 text-[11px] text-foreground"
          data-testid="filter-esc-a"
        />
      </label>
      <label className="flex cursor-pointer items-center gap-1.5 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground">
        <input
          type="checkbox"
          checked={filters.catalogOnly}
          onChange={(e) => onChange({ ...filters, catalogOnly: e.target.checked })}
          className="accent-orange-500"
          data-testid="filter-catalog-only"
        />
        Catalog matches only
      </label>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Invariants readout
// ---------------------------------------------------------------------------

interface InvariantsRowProps {
  readonly pAeroCruiseW: number;
  readonly pAeroTopW: number;
  readonly energyWh: number;
  readonly vCruiseMps: number;
  readonly vTopMps: number;
  readonly tTargetMin: number;
}

function InvariantsRow({
  pAeroCruiseW,
  pAeroTopW,
  energyWh,
  vCruiseMps,
  vTopMps,
  tTargetMin,
}: InvariantsRowProps) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card px-4 py-3">
      {/* Dim label so these read as derived values, not editable inputs. */}
      <span
        className="font-[family-name:var(--font-geist-sans)] text-[9px] uppercase tracking-wider text-subtle-foreground"
        data-testid="invariants-source-label"
      >
        Computed from mission
      </span>
      <div className="flex flex-wrap gap-4">
        {[
          { label: "V_cruise", value: `${vCruiseMps.toFixed(1)} m/s` },
          { label: "V_top", value: `${vTopMps.toFixed(1)} m/s` },
          { label: "t_target", value: `${tTargetMin.toFixed(0)} min` },
          { label: "P_aero cruise", value: `${pAeroCruiseW.toFixed(0)} W` },
          { label: "P_aero top", value: `${pAeroTopW.toFixed(0)} W` },
          { label: "Energy (DoD-adj)", value: `${energyWh.toFixed(1)} Wh` },
        ].map(({ label, value }) => (
          <div key={label} className="flex flex-col gap-0.5">
            <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
              {label}
            </span>
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] font-semibold text-foreground">
              {value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main PowertrainTab
// ---------------------------------------------------------------------------

export function PowertrainTab({ aeroplaneId }: Props) {
  const [assumptions, setAssumptions] = useState<SolutionSpaceAssumptions>({
    cell_counts: DEFAULT_CELL_COUNTS,
  });
  const [selectedCellCount, setSelectedCellCount] = useState<number | null>(null);
  const [filters, setFilters] = useState<ColumnFilters>({
    maxPeakA: "",
    maxMah: "",
    maxEscA: "",
    catalogOnly: false,
  });

  const { data, isLoading, error } = usePowertrainSolutionSpace(aeroplaneId, assumptions);

  // Reset an orphaned selection: if the selected cell-count no longer exists in
  // the new rows (e.g. after an assumptions change removed it), clear it so the
  // auto-select fallback (first row) takes over instead of pointing at nothing.
  // Done during render (not in a useEffect) per the React 19 "adjust state when
  // data changes" pattern — avoids the react-hooks/set-state-in-effect cascade.
  if (
    selectedCellCount != null &&
    data != null &&
    !data.rows.some((r) => r.cell_count === selectedCellCount)
  ) {
    setSelectedCellCount(null);
  }

  // Auto-select the first row when data arrives and nothing is selected yet
  const firstCellCount = data?.rows[0]?.cell_count ?? null;
  const effectiveSelection = selectedCellCount ?? firstCellCount;

  const selectedSpec = useMemo(
    () => data?.shopping_specs.find((s) => s.cell_count === effectiveSelection),
    [data, effectiveSelection]
  );

  // Conservative (worst-case, rounded-up) figures for the selected row — used by
  // the shopping-spec line so it shows the same minimums as the table/plot.
  const etaPropLo = data?.assumptions_used.eta_prop_lo ?? 0.65;
  const pAeroTopW = data?.p_aero_top_w ?? 0;
  const selectedConservative = useMemo(() => {
    const row = data?.rows.find((r) => r.cell_count === effectiveSelection);
    return row ? conservativeSpec(row, pAeroTopW, etaPropLo) : undefined;
  }, [data, effectiveSelection, pAeroTopW, etaPropLo]);

  // V_top is auto-derived from the mission when the user hasn't set it.
  const vTopAutoDerived = assumptions.v_top_mps == null;

  return (
    <div
      className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-4"
      data-testid="powertrain-tab"
    >
      {/* Header */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
            Powertrain Solution Space
          </span>
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
            Capacity × C-rate feasible region · Shopping specs per cell count
          </span>
        </div>
        {/* Scholz scope note — Phase 1 limitations are explicit, not implied. */}
        <span
          className="font-[family-name:var(--font-geist-sans)] text-[9px] text-subtle-foreground"
          data-testid="powertrain-scope-note"
        >
          Phase 1: peak sizing from top speed only (static-thrust &amp; climb not
          checked). Prop efficiency is an assumption band — APC prop model comes
          in Phase 2.
        </span>
      </div>

      {/* Assumption controls */}
      <AssumptionControls
        assumptions={assumptions}
        onChange={setAssumptions}
        vTopAutoDerived={vTopAutoDerived}
      />

      {/* Loading state */}
      {isLoading && (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 size={14} className="animate-spin text-muted-foreground" />
          <span className="ml-2 font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
            Computing powertrain solution space…
          </span>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div
          className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-card p-4"
          data-testid="powertrain-error"
        >
          <AlertTriangle size={14} className="text-orange-400" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
            {(error as { status?: number }).status === 422
              ? "Run assumption recompute first — mission/aero parameters are needed to compute the powertrain solution space."
              : "Powertrain solution space unavailable — set mass, mission speed and polar parameters first."}
          </span>
        </div>
      )}

      {/* Data state */}
      {data && !isLoading && (
        <>
          {/* Warnings banner — always visible per spec */}
          {data.warnings.length > 0 && (
            <div
              className="rounded-lg border border-orange-500/30 bg-orange-900/30 px-3 py-2"
              data-testid="powertrain-warnings"
            >
              {data.warnings.map((w) => (
                <p
                  key={w}
                  className="font-[family-name:var(--font-geist-sans)] text-[10px] text-orange-400"
                >
                  ⚠ {w}
                </p>
              ))}
            </div>
          )}

          {/* Mission invariants */}
          <InvariantsRow
            pAeroCruiseW={data.p_aero_cruise_w}
            pAeroTopW={data.p_aero_top_w}
            energyWh={data.energy_wh}
            vCruiseMps={data.v_cruise_mps}
            vTopMps={data.v_top_mps}
            tTargetMin={data.t_target_min}
          />

          {/* Feasible-region plot (gh-977) */}
          {data.feasible_regions.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-2">
              <FeasibleRegionPlot
                regions={data.feasible_regions}
                rows={data.rows}
                selectedCellCount={effectiveSelection}
                onSelectCellCount={setSelectedCellCount}
                vCruiseMps={data.v_cruise_mps}
                vTopMps={data.v_top_mps}
                tTargetMin={data.t_target_min}
              />
            </div>
          )}

          {/* Hobbyist how-to callout above the table. */}
          <p
            className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground"
            data-testid="powertrain-table-callout"
          >
            Pick a cell count, then shop: motor ≈ the KV shown, ESC ≥ ESC min (A),
            battery ≥ mAh min at ≥ Min C-rating.
          </p>

          {/* Filter bar + solution table */}
          <FilterBar filters={filters} onChange={setFilters} />
          <SolutionTable
            rows={data.rows}
            filters={filters}
            selectedCellCount={effectiveSelection}
            onSelectRow={setSelectedCellCount}
            pAeroTopW={data.p_aero_top_w}
            etaPropLo={etaPropLo}
          />

          {/* Shopping spec for selected row */}
          <ShoppingSpecLine spec={selectedSpec} conservative={selectedConservative} />
        </>
      )}
    </div>
  );
}
