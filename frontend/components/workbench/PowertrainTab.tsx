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
  return {
    x: [row.capacity_mah_min],
    y: [row.c_min],
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
      `Capacity: ${row.capacity_mah_min.toFixed(0)} mAh<br>` +
      `Min C-rate: ${row.c_min.toFixed(1)}C<extra></extra>`,
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
    margin: { l: 55, r: 15, t: 45, b: 50 },
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

      // Click listener to select cell count from marker.
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
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions, rows, selectedCellCount, vCruiseMps, vTopMps, tTargetMin]);

  // Cleanup
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
      className="h-full min-h-0 w-full"
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
}: Readonly<{ spec: ShoppingSpec | undefined }>) {
  if (!spec) return null;
  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card px-4 py-3 font-[family-name:var(--font-jetbrains-mono)] text-[12px]"
      data-testid="shopping-spec-line"
    >
      <span className="text-muted-foreground">
        Shopping spec ({spec.cell_count}S @ {spec.battery_v_nom.toFixed(1)} V):
      </span>
      <span className="text-orange-400">
        ESC ≥ {spec.esc_min_a.toFixed(0)} A
      </span>
      <span className="text-muted-foreground">·</span>
      <span className="text-blue-400">
        Battery ≥ {spec.battery_min_mah.toFixed(0)} mAh @ ≥{spec.battery_min_c.toFixed(1)}C
      </span>
      <span className="text-muted-foreground">·</span>
      <span className="text-emerald-400">
        Motor ≥ {spec.motor_min_peak_w.toFixed(0)} W
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
}

function SolutionTable({
  rows,
  filters,
  selectedCellCount,
  onSelectRow,
}: SolutionTableProps) {
  const maxPeakA = filters.maxPeakA !== "" ? parseFloat(filters.maxPeakA) : null;
  const maxMah = filters.maxMah !== "" ? parseFloat(filters.maxMah) : null;
  const maxEscA = filters.maxEscA !== "" ? parseFloat(filters.maxEscA) : null;

  const filtered = rows.filter((r) => {
    if (filters.catalogOnly && !r.has_motor_match && !r.has_battery_match && !r.has_esc_match)
      return false;
    if (maxPeakA != null && r.i_peak_a > maxPeakA) return false;
    if (maxMah != null && r.capacity_mah_min > maxMah) return false;
    if (maxEscA != null && r.esc_min_a > maxEscA) return false;
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
            <th scope="col" className="py-2 pr-3">ESC ≥A</th>
            <th scope="col" className="py-2 pr-3">mAh min</th>
            <th scope="col" className="py-2 pr-3">C min</th>
            <th scope="col" className="py-2 pr-3">Wh</th>
            <th scope="col" className="py-2 pr-3">KV</th>
            <th scope="col" className="py-2">Catalog</th>
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
                  {row.motor_peak_w.toFixed(0)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {row.i_peak_a.toFixed(1)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {row.esc_min_a.toFixed(0)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {row.capacity_mah_min.toFixed(0)}
                </td>
                <td className="py-2 pr-3 text-foreground">
                  {row.c_min.toFixed(1)}
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
                  {hasCatalog ? "✓" : "—"}
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
}

function AssumptionControls({ assumptions, onChange }: AssumptionControlsProps) {
  const cellCounts = assumptions.cell_counts ?? DEFAULT_CELL_COUNTS;

  function toggleCellCount(s: number) {
    const next = cellCounts.includes(s)
      ? cellCounts.filter((c) => c !== s)
      : [...cellCounts, s].sort((a, b) => a - b);
    onChange({ ...assumptions, cell_counts: next });
  }

  function numField(
    key: keyof SolutionSpaceAssumptions,
    value: number | undefined,
    defaultVal: number
  ) {
    return (
      <input
        type="number"
        value={value ?? defaultVal}
        step={0.01}
        onChange={(e) =>
          onChange({ ...assumptions, [key]: parseFloat(e.target.value) })
        }
        className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
      />
    );
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
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          η_prop [lo / hi]
        </span>
        <div className="flex items-center gap-1">
          {numField("eta_prop_lo", assumptions.eta_prop_lo, 0.65)}
          <span className="text-muted-foreground">/</span>
          {numField("eta_prop_hi", assumptions.eta_prop_hi, 0.78)}
        </div>
      </div>

      {/* DoD */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          DoD
        </span>
        {numField("dod", assumptions.dod, 0.8)}
      </div>

      {/* ESC margin */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          ESC margin ×
        </span>
        {numField("esc_margin", assumptions.esc_margin, 1.4)}
      </div>

      {/* C margin */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          C margin ×
        </span>
        {numField("c_margin", assumptions.c_margin, 1.25)}
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
          onChange={(e) =>
            onChange({ ...assumptions, t_target_min: parseFloat(e.target.value) })
          }
          className="w-20 rounded border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-foreground"
          data-testid="t-target-input"
        />
      </div>

      {/* v_top_mps */}
      <div className="flex flex-col gap-1">
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          V_top (m/s)
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
    <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-card px-4 py-3">
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

  // Auto-select the first row when data arrives and nothing is selected yet
  const firstCellCount = data?.rows[0]?.cell_count ?? null;
  const effectiveSelection = selectedCellCount ?? firstCellCount;

  const selectedSpec = useMemo(
    () => data?.shopping_specs.find((s) => s.cell_count === effectiveSelection),
    [data, effectiveSelection]
  );

  return (
    <div
      className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-4"
      data-testid="powertrain-tab"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Powertrain Solution Space
        </span>
        <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-muted-foreground">
          Capacity × C-rate feasible region · Shopping specs per cell count
        </span>
      </div>

      {/* Assumption controls */}
      <AssumptionControls assumptions={assumptions} onChange={setAssumptions} />

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
              {data.warnings.map((w, i) => (
                <p
                  key={i}
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

          {/* Filter bar + solution table */}
          <FilterBar filters={filters} onChange={setFilters} />
          <SolutionTable
            rows={data.rows}
            filters={filters}
            selectedCellCount={effectiveSelection}
            onSelectRow={setSelectedCellCount}
          />

          {/* Shopping spec for selected row */}
          <ShoppingSpecLine spec={selectedSpec} />
        </>
      )}
    </div>
  );
}
